"""A-owned commit adapter. SQL and original units remain with their storage owners."""
from contextlib import closing
import cards, custom_cards, engines, card_thresholds, band_cards, vitals_ledger, device_watch
from compute_cycle import StaleCycle, validate, digest, freeze, Outcome
from h1_common import H1Error


class Guard:
    def __init__(self, revision):
        self.revision = revision

    def before(self, track):
        if not track.in_transaction or cards.compute_revision(track) != self.revision:
            raise StaleCycle()

    def advance(self, track):
        # Still inside our original unit, before COMMIT. Never absorb an outside write.
        if not track.in_transaction:
            raise StaleCycle()
        self.revision = cards.compute_revision(track)


def failure(inst, at, trigger, exc):
    code = exc.code if isinstance(exc, H1Error) else type(exc).__name__
    inst.app.log('sync_failed', inst.ctx.instance_id, code)
    return {'at': at, 'trigger': trigger, 'ok': False,
            'error': {'code': code, 'detail': str(exc)[:300]}}


def apply(inst, cycle, proposal):
    """Caller A. Return a detached summary; publication belongs to the task owner."""
    with closing(cards.open_startrack(inst.ctx)) as track:
        validate(inst, cycle, track)
        guard = Guard(cycle.revision)
        try:
            primary = cycle.primary.unwrap()
            if primary is not None:
                card, snap, _ = primary
                summary = cards.apply_prepared_sync(track, inst.ctx, card, snap, proposal.primary,
                                                     cycle.at, [n.channel for n in inst.app.notifiers], guard)
                cards.deliver_pending(track, inst.app.notifiers, cycle.at)
            else:
                summary = {'new': [], 'updated': [], 'run_id': None, 'alert': None}
            imported = cycle.imported
            result = {'at': cycle.at, 'trigger': cycle.trigger, 'ok': imported['error'] is None,
                      'inserted': imported['inserted'], 'pending_commits': imported['pending_commits'],
                      'error': imported['error'], **summary}
            if not cycle.replay:
                try:
                    groups = cycle.secondary.unwrap()[0]
                    custom = []
                    for card, planned in proposal.custom.unwrap():
                        item = custom_cards.apply_prepared_card(track, inst.ctx, card,
                            groups.get(card['definition']['code'], {}), planned, cycle.at, inst.app.notifiers, guard)
                        if item is not None:
                            custom.append(item)
                    result['custom'] = custom
                    computed = []
                    for tpl, prepared in proposal.engines.unwrap():
                        computed.extend(engines.apply_prepared_template(track, inst.ctx, tpl, prepared, cycle.at, guard))
                    result['engines'] = computed
                    result['thresholds'] = card_thresholds.apply_prepared_all(track, inst.ctx, cycle.at,
                                                                            proposal.thresholds.unwrap(), guard)
                    cards.deliver_pending(track, inst.app.notifiers, cycle.at)
                    band = []
                    for args in proposal.band.unwrap():
                        item = band_cards.apply_entry(track, *args, cycle.at, guard=guard)
                        if item is not None:
                            band.append(item)
                    result['band_cards'] = band
                    # D-only writers cannot change the dependency between check and BEGIN.
                    with device_watch.compute_settings(inst.ctx.root, inst.spec['cards']) as (settings, version):
                        if digest(Outcome((freeze(settings), version))) != digest(cycle.settings):
                            raise StaleCycle()
                        value = proposal.vitals.unwrap()
                        if value is not None:
                            items, prepared = value
                            result['vitals_run'] = vitals_ledger.record(track, inst.ctx, items,
                                day=cycle.at[:10], now=cycle.at, computed=prepared, guard=guard)
                except StaleCycle:
                    raise
                except Exception as exc:
                    result['custom_error'] = {'code': getattr(exc, 'code', type(exc).__name__), 'detail': str(exc)[:200]}
                    inst.app.log('custom_sync_failed', inst.ctx.instance_id, type(exc).__name__)
            return result
        except StaleCycle:
            raise
        except Exception as exc:
            return failure(inst, cycle.at, cycle.trigger, exc)
