"""One in-memory computation cycle. No task payload is persisted here.

Capture/validate require caller A. Evaluation consumes detached values, with
no database, Instance, cache or notifier. Storage remains with each owner.
"""
from contextlib import closing
from dataclasses import dataclass, asdict, fields, is_dataclass
from datetime import datetime, timezone
import hashlib
import json

import cards, custom_cards, engines, card_thresholds, band_cards, vitals, bioage, device_watch
from compute_snapshot import freeze, custom_point, engine_plan, vitals_result
from h1_common import canonical_bytes
from sqlite_util import assert_inside
from startorch_outbox import open_startorch
from startrack_import import import_pending
from background_read import BackgroundRead
from observation_read import ObservationRead
from time_freshness import PresentationClock

MAX_ROWS = 150000
MAX_PAYLOAD_BYTES = 128 * 1024 * 1024
MAX_RESULT_BYTES = 128 * 1024 * 1024


class StaleCycle(Exception):
    """Internal control flow, mapped by the worker to its existing states."""


class CapacityFallback(Exception):
    """Discard values and use the unchanged synchronous path."""


@dataclass(frozen=True)
class Outcome:
    value: object = None
    error: Exception | None = None

    def unwrap(self):
        if self.error is not None:
            raise self.error
        return self.value


def attempt(call, *args, **kwargs):
    try:
        return Outcome(call(*args, **kwargs))
    except Exception as exc:
        # Do not deepcopy arbitrary exceptions. Release capture-frame resources.
        seen = set()
        item = exc
        while item is not None and id(item) not in seen:
            seen.add(id(item))
            item.__traceback__ = None
            item = item.__cause__ or item.__context__
        return Outcome(error=exc)


def digest(value):
    def encode(v):
        if isinstance(v, Outcome):
            return ({'error': [type(v.error).__module__, type(v.error).__qualname__, str(v.error)]}
                    if v.error is not None else {'value': v.value})
        if is_dataclass(v):
            return {f.name: getattr(v, f.name) for f in fields(v)}
        if isinstance(v, (set, frozenset)):
            return sorted(v)
        return str(v)
    return hashlib.sha256(json.dumps(value, default=encode, ensure_ascii=False,
                                     sort_keys=True, separators=(',', ':')).encode()).hexdigest()


@dataclass(frozen=True)
class RuleValues:
    rules: dict
    combine: dict
    selection: dict
    codes: frozenset

    def selection_mode(self, code, kind):
        return self.selection['overrides'].get(code, self.selection[kind])


@dataclass(frozen=True)
class DynamicValues:
    codes: frozenset


def card_values(card):
    rules = RuleValues(freeze(card.rulepack.rules), freeze(card.rulepack.combine),
                       freeze(card.rulepack.selection), freeze(card.rulepack.codes))
    return cards.Card(card.card_id, rules, DynamicValues(freeze(card.dynamic.codes)),
                      freeze(card.labels), freeze(card.definition), card.card_def_id)


@dataclass(frozen=True)
class SnapshotValues:
    observations: tuple
    tps: dict
    unknown_time: tuple


@dataclass(frozen=True)
class CodeValues:
    label_zh: str
    family: str


def node(root, path):
    assert_inside(root, path)
    try:
        s = path.stat()
    except FileNotFoundError:
        return None
    return s.st_dev, s.st_ino


def profile_input(inst):
    path = bioage.profile_path(inst.ctx.root)
    assert_inside(inst.ctx.root, path)
    def stamp():
        assert_inside(inst.ctx.root, path)
        try:
            s = path.stat()
        except FileNotFoundError:
            return None
        return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns
    before = stamp()
    result = bioage.load_profile(inst.ctx.root)
    if before != stamp():
        raise StaleCycle()
    return freeze(result), before


def settings_input(inst):
    with device_watch.compute_settings(inst.ctx.root, inst.spec['cards']) as (settings, version):
        return freeze(settings), version


def environment(inst):
    """A-owned dependencies excluding delivery/ack and private task status."""
    with closing(open_startorch(inst.ctx)) as c:
        seq = c.execute('SELECT COALESCE(MAX(seq_to),0) FROM h1_commit').fetchone()[0]
    registry = inst.app.registry
    return (id(inst), str(inst.ctx.root), inst.ctx.instance_id, inst.ctx.tz, tuple(inst.ctx.accept),
            id(registry), registry.versions, digest(asdict(registry.current)),
            digest(inst.app.rulepack), digest(inst.app.dynamic),
            digest({k: inst.spec.get(k) for k in ('cards', 'replay', 'default_nature')}),
            inst.sjia, tuple(n.channel for n in inst.app.notifiers), seq,
            node(inst.ctx.root, inst.ctx.startrack_db), node(inst.ctx.root, inst.ctx.startorch_db))


def eligible(inst):
    """Conservative history budget, before import/notification side effects.

    Count all retained revisions, not just ACTIVE rows. Exceeding eligibility
    never truncates data: it selects the original synchronous implementation.
    """
    for opener, table in ((open_startorch, 'formal_observation'), (cards.open_startrack, 'h1_inbox')):
        with closing(opener(inst.ctx)) as c:
            count, size = c.execute('SELECT COUNT(*),COALESCE(SUM(length(CAST(payload AS BLOB))),0) FROM ' + table).fetchone()
        if count > MAX_ROWS or size > MAX_PAYLOAD_BYTES:
            return False
    return True


@dataclass(frozen=True)
class Cycle:
    at: str
    trigger: str
    imported: dict
    primary: Outcome
    secondary: Outcome
    environment: tuple
    revision: tuple
    profile: Outcome
    settings: Outcome
    parameters: Outcome
    replay: bool


def capture(inst, trigger):
    """Caller holds A. All connections are closed before returning."""
    if not eligible(inst):
        raise CapacityFallback()
    at = inst.now()
    with closing(cards.open_startrack(inst.ctx)) as track:
        # Same pre-import historical delivery collection point as cards.sync.
        card = inst.card(track) if inst.sjia else None
        if card is not None:
            cards.deliver_pending(track, inst.app.notifiers, at)
        imported = import_pending(track, inst.ctx, inst.app.registry, imported_at=at)
        original_revision = cards.compute_revision(track)
        read = None
        def get_read():
            nonlocal read
            if read is None:
                if not hasattr(inst, '_background_read'):
                    inst._background_read = BackgroundRead(inst)
                read = inst._background_read.read_for_sync(lambda: ObservationRead(track, inst.ctx.tz))
            return read
        def primary():
            if card is None:
                return None
            value_card = card_values(card)
            snap = cards.take_snapshot(track, inst.ctx, value_card, read=get_read())
            snap = SnapshotValues(freeze(snap.observations), freeze(snap.tps), freeze(snap.unknown_time))
            latest = freeze(cards.latest_results(track, card.card_def_id))
            return value_card, snap, latest
        main = attempt(primary)
        profile = Outcome()
        settings = Outcome()
        parameters = Outcome()
        def secondary():
            nonlocal profile, settings, parameters
            if inst.spec.get('replay'):
                return None
            raw = get_read()
            groups = freeze(custom_cards.by_code(track, inst.ctx, read=raw))
            custom = []
            for c in custom_cards.cards(track):
                latest = attempt(lambda: freeze(cards.latest_results(track, c['card_def_id'])))
                custom.append((freeze(c), latest))
            profile = attempt(profile_input, inst)
            parameters = attempt(lambda: freeze(bioage.params()))
            def engine_inputs():
                prof, _ = profile.unwrap()
                entries = []
                for tpl, t in engines.active(track).items():
                    def template():
                        rules = []
                        for rid in t['conf']['rules']:
                            def one(rid=rid):
                                d = engines._definition(tpl, rid, prof)
                                did = hashlib.sha256(canonical_bytes(d)).hexdigest()
                                return freeze(d), did, freeze(cards.latest_results(track, did))
                            rules.append((rid, attempt(one)))
                        return freeze(t['conf']), tuple(rules)
                    entries.append((tpl, attempt(template)))
                return tuple(entries)
            eng = attempt(engine_inputs)
            def threshold_inputs():
                conf = card_thresholds.configs(track)
                states = {}
                if conf:
                    for cid, value in track.execute('SELECT card_id,value FROM card_setting WHERE key=? ORDER BY id', (card_thresholds.STATE,)):
                        states[cid] = json.loads(value)
                return freeze(conf), freeze(states)
            thresholds = attempt(threshold_inputs)
            # Late-owner preparation failures must not erase an earlier prefix.
            def band_inputs():
                now = band_cards.datetime.now(timezone.utc)
                return freeze(raw.observations), now
            band = attempt(band_inputs)
            settings = attempt(settings_input, inst)
            def vitals_inputs():
                setup, _ = settings.unwrap()
                if 'VITALS' not in setup['cards']:
                    return None
                now = vitals.datetime.now(timezone.utc)
                codes = freeze({k: {'label_zh': v.label_zh, 'family': v.family}
                                for k, v in inst.app.registry.current.codes.items()})
                return freeze(tuple(raw.payloads.values())), now, codes
            vital = attempt(vitals_inputs)
            return groups, tuple(custom), eng, thresholds, band, vital, inst.ctx.tz
        rest = attempt(secondary) if main.error is None else Outcome()
        revision = cards.compute_revision(track)
        if revision != original_revision:
            raise StaleCycle()
        env = environment(inst)
        return Cycle(at, trigger, freeze(asdict(imported)), main, rest, env, revision,
                     profile, settings, parameters, bool(inst.spec.get('replay')))


def point_outcomes(tps, evaluate):
    result = {}
    for tp in tps:
        outcome = attempt(evaluate, tp)
        result[tp] = outcome
        if outcome.error is not None:
            break
    return result


def primary_plan(value):
    if value is None:
        return None
    card, snap, latest = value
    status, _ = cards.classify_values(latest, snap, card)
    targets = sorted(tp for tp, state in status.items() if state in ('NEW', 'STALE'))
    if not targets:
        return status, targets, {}
    values = {tp: cards.values_at(card, obs) for tp, obs in snap.tps.items()}
    def point(tp):
        state, level, result = cards.evaluate_run_point(card, snap, tp, values)
        inputs = cards.input_set(snap, card, tp) if state == 'EVALUATED' else frozenset()
        return state, level, result, inputs
    return status, targets, point_outcomes(targets, point)


def custom_plan(card, latest, groups):
    days = groups.get(card['definition']['code'], {})
    status, _ = custom_cards.status_values(latest.unwrap(), card, days)
    targets = sorted(tp for tp, s in status.items() if s in ('NEW', 'STALE'))
    points = point_outcomes(targets, lambda tp: custom_point(card['definition'], tp, days, custom_cards.evaluate))
    return status, targets, points


@dataclass(frozen=True)
class Proposal:
    primary: Outcome
    custom: Outcome
    engines: Outcome
    thresholds: Outcome
    band: Outcome
    vitals: Outcome


def evaluate(cycle):
    """No storage, cache, lock or live instance is reachable from this phase."""
    main = attempt(lambda: primary_plan(cycle.primary.unwrap()))
    if main.error is not None or cycle.replay:
        return budget(Proposal(main, Outcome(), Outcome(), Outcome(), Outcome(), Outcome()))
    rest = cycle.secondary
    if rest.error is not None:
        return budget(Proposal(main, rest, Outcome(), Outcome(), Outcome(), Outcome()))
    groups, custom, eng, thresholds, band, vital, tz = rest.unwrap()
    custom_results = []
    for c, latest in custom:
        result = attempt(custom_plan, c, latest, groups)
        custom_results.append((c, result))
        if result.error is not None:
            break
    def engine_results():
        prof, _ = cycle.profile.unwrap()
        prof = dict(prof, _compute_parameters=cycle.parameters)
        results = []
        for tpl, inputs in eng.unwrap():
            def template():
                conf, rules = inputs.unwrap()
                planned = []
                for rid, prepared in rules:
                    def rule():
                        d, did, latest = prepared.unwrap()
                        days = engines.CALC[rid][0](groups)
                        todo, gone = engine_plan(rid, groups, prof, days, latest, engines.evaluate)
                        return d, did, todo, gone, not latest
                    result = attempt(rule)
                    planned.append((rid, result))
                    if result.error is not None:
                        break
                return conf, tuple(planned)
            result = attempt(template)
            results.append((tpl, result))
            if result.error is not None:
                break
        return tuple(results)
    def threshold_results():
        conf, states = thresholds.unwrap()
        return tuple((cid, d, attempt(card_thresholds.proposal, d, groups.get(d['code'], {}),
                                     cycle.at, states.get(cid), False)) for cid, d in conf.items())
    def band_values():
        observations, now = band.unwrap()
        return band_cards.compute_values(observations, tz, None, now)[1]
    def vitals_values():
        inputs = vital.unwrap()
        if inputs is None:
            return None
        payloads, vitals_now, code_values = inputs
        settings, _ = cycle.settings.unwrap()
        codes = {k: CodeValues(**v) for k, v in code_values.items()}
        vit = vitals.vitals_values(payloads, codes, PresentationClock(vitals_now, tz), vitals_now)
        items = vit['items']
        if settings['vitals_sources'] is not None:
            items = [i for i in items if settings['vitals_sources'].get(i.get('family'), False)
                     or i.get('family') not in device_watch.SOURCES]
        return items, attempt(vitals_result, items, cycle.at[:10])
    proposal = Proposal(main, Outcome(tuple(custom_results)), attempt(engine_results), attempt(threshold_results),
                        attempt(band_values), attempt(vitals_values))
    return budget(proposal)


def budget(proposal):
    # Byte budget for value data, not an assertion of the Python RSS footprint.
    def encode(v):
        if isinstance(v, Outcome):
            return {'error': type(v.error).__name__} if v.error is not None else v.value
        if is_dataclass(v):
            return {f.name: getattr(v, f.name) for f in fields(v)}
        if isinstance(v, (set, frozenset)):
            return sorted(v)
        return str(v)
    size = len(json.dumps(proposal, default=encode, ensure_ascii=False, separators=(',', ':')).encode())
    if size > MAX_RESULT_BYTES:
        raise CapacityFallback()
    return proposal


def validate(inst, cycle, track):
    if environment(inst) != cycle.environment or cards.compute_revision(track) != cycle.revision:
        raise StaleCycle()
    if not cycle.replay and cycle.secondary.error is None:
        if digest(attempt(profile_input, inst)) != digest(cycle.profile):
            raise StaleCycle()
        if digest(attempt(settings_input, inst)) != digest(cycle.settings):
            raise StaleCycle()
        if digest(attempt(lambda: freeze(bioage.params()))) != digest(cycle.parameters):
            raise StaleCycle()
