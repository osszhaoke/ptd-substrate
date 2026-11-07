"""星轨 card runner for the sJIA slice: time points, runs, staleness, alerts (reference).

sync()      = deliver pending alerts -> import H1 commits -> evaluate time points never evaluated
              under the current card definition (results + alert intent in ONE transaction)
              -> deliver pending alerts.
              PTDS-local (DC-15): sync() also re-evaluates STALE time points (changed inputs) in the same
              run, trigger AUTO_UPDATE; every run is kept, so old and new results stay comparable.
recompute() = explicit re-evaluation ("再试一次" after a failure, or a chosen set of time points).
Delivery is at-least-once per channel: an intent survives any crash; a crash between a send and
its record can repeat that one send. A recorded FAILED is not retried automatically.
"""
from __future__ import annotations

from contextlib import contextmanager, nullcontext
from pathlib import Path
import threading

import subprocess
from dataclasses import dataclass
from datetime import timezone
from decimal import Decimal

from dynamic import SENSITIVITIES, DynamicConfig, change_word, evaluate_dynamic
from h1_common import (DictionaryRegistry, H1Error, InstanceContext, canonical_bytes, canonical_json,
                       local_day, parse_instant, sha256_hex, strict_loads)
from rules import BANNED_IN_ALERT, RulePack, Value, combine_level, eval_rule
from sqlite_util import append_only_ddl, open_main_db, transaction
from startrack_import import H1_DDL, h1_status, import_pending

ENGINE_VERSION = "slice-ref/0.2-static-only"
SCHEMA_ID = "startrack-slice/0.2"
LEVEL_RANK = {"NONE": 0, "UNDETERMINED": 0, "WATCH": 1, "ALERT": 2}
LEVEL_ZH = {"ALERT": "关注", "WATCH": "观察", "UNDETERMINED": "无法判定 · 建议补检", "NONE": "无"}
RESULT_ZH = {"MET": "达到", "NOT_MET": "未达到", "INDETERMINATE": "无法判定", "NOT_APPLICABLE": "不适用"}
DISCLAIMER = "关注信号，不构成诊断或治疗建议"
ALERT_TITLE = "PTDS 关注提醒"
ALERT_SUFFIX = "这不是诊断，请联系主治医生。"

CARD_DDL = """
CREATE TABLE card_setting (
  id      INTEGER PRIMARY KEY AUTOINCREMENT,
  card_id TEXT NOT NULL,
  key     TEXT NOT NULL,
  value   TEXT NOT NULL,
  set_at  TEXT NOT NULL
);
CREATE TABLE card_def (
  card_def_id   TEXT PRIMARY KEY,
  card_id       TEXT NOT NULL,
  definition    TEXT NOT NULL,
  registered_at TEXT NOT NULL
);
CREATE TABLE run (
  run_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  card_def_id TEXT NOT NULL REFERENCES card_def (card_def_id),
  trigger     TEXT NOT NULL CHECK (trigger IN ('SYNC', 'AUTO_UPDATE', 'RECOMPUTE')),
  started_at  TEXT NOT NULL
);
CREATE TABLE run_tp (
  run_id        INTEGER NOT NULL REFERENCES run (run_id),
  tp_date       TEXT NOT NULL,
  status        TEXT NOT NULL CHECK (status IN ('EVALUATED', 'VANISHED')),
  level         TEXT NOT NULL CHECK (level IN ('NONE', 'UNDETERMINED', 'WATCH', 'ALERT')),
  result        TEXT NOT NULL,
  result_sha256 TEXT NOT NULL,
  PRIMARY KEY (run_id, tp_date)
);
CREATE TABLE run_input (
  run_id         INTEGER NOT NULL,
  tp_date        TEXT NOT NULL,
  observation_id TEXT NOT NULL,
  revision       INTEGER NOT NULL,
  role           TEXT NOT NULL CHECK (role IN ('TP', 'HISTORY')),
  PRIMARY KEY (run_id, tp_date, observation_id),
  FOREIGN KEY (run_id, tp_date) REFERENCES run_tp (run_id, tp_date)
);
CREATE TABLE alert_state (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  card_id     TEXT NOT NULL,
  tp_date     TEXT NOT NULL,
  level       TEXT NOT NULL,
  run_id      INTEGER NOT NULL REFERENCES run (run_id),
  recorded_at TEXT NOT NULL
);
CREATE TABLE alert_log (
  dedupe_key TEXT PRIMARY KEY,
  card_id    TEXT NOT NULL,
  tp_date    TEXT NOT NULL,
  level      TEXT NOT NULL,
  run_id     INTEGER NOT NULL REFERENCES run (run_id),
  title      TEXT NOT NULL,
  body       TEXT NOT NULL,
  channels   TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE alert_delivery (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  dedupe_key   TEXT NOT NULL REFERENCES alert_log (dedupe_key),
  channel      TEXT NOT NULL,
  outcome      TEXT NOT NULL CHECK (outcome IN ('SENT', 'FAILED')),
  detail       TEXT NOT NULL,
  attempted_at TEXT NOT NULL
);
CREATE TABLE alert_ack (
  dedupe_key TEXT PRIMARY KEY REFERENCES alert_log (dedupe_key),
  acked_at   TEXT NOT NULL
);
""" + append_only_ddl(["card_setting", "card_def", "run", "run_tp", "run_input", "alert_state",
                       "alert_log", "alert_delivery", "alert_ack"])
DDL = H1_DDL + CARD_DDL


def open_startrack(ctx: InstanceContext, *, create=False):
    return open_main_db(ctx.startrack_db, SCHEMA_ID, DDL, root=ctx.root, create=create)


# ----------------------------------------------------------------------------- card definition

@dataclass(frozen=True, eq=False)
class Card:
    card_id: str
    rulepack: RulePack
    dynamic: DynamicConfig
    labels: dict
    definition: dict
    card_def_id: str

    @property
    def codes(self) -> frozenset:
        return frozenset(self.rulepack.codes) | self.dynamic.codes


def load_card(registry: DictionaryRegistry, ctx: InstanceContext, rulepack_doc: dict, dynamic_doc: dict,
              sensitivity: str) -> Card:
    rulepack = RulePack(rulepack_doc, registry)
    dynamic = DynamicConfig(dynamic_doc, registry, sensitivity)
    labels = {code: cdef.label_zh for code, cdef in registry.current.codes.items()}
    for code in dynamic.codes:
        if any(word in labels[code] for word in BANNED_IN_ALERT):
            raise H1Error("RULEPACK_COPY_UNSAFE", code)
    definition = {"card_id": rulepack.pack_id, "engine_version": ENGINE_VERSION, "instance_tz": ctx.tz,
                  "rulepack": rulepack_doc, "dynamic": dynamic_doc, "sensitivity": sensitivity}
    return Card(rulepack.pack_id, rulepack, dynamic, labels, definition,
                sha256_hex(canonical_bytes(definition)))


def current_sensitivity(conn, card_id: str, default: str) -> str:
    row = conn.execute("SELECT value FROM card_setting WHERE card_id = ? AND key = 'sensitivity' "
                       "ORDER BY id DESC LIMIT 1", (card_id,)).fetchone()
    return row[0] if row else default


def set_sensitivity(conn, card_id: str, value: str, *, set_at: str) -> None:
    if value not in SENSITIVITIES:
        raise H1Error("CONFIG_INVALID", "sensitivity")
    conn.execute("INSERT INTO card_setting (card_id, key, value, set_at) VALUES (?, 'sensitivity', ?, ?)",
                 (card_id, value, set_at))


# ----------------------------------------------------------------------------- snapshot & time points

@dataclass(frozen=True)
class Obs:
    observation_id: str
    revision: int
    code: str
    kind: str
    value: object          # Decimal | bool (canonical)
    comparator: str | None
    unit: str | None
    role: str              # INSTANT | DAY | UNKNOWN
    instant: object        # datetime | None
    day: str | None        # ISO date of the time point; None when the time is unknown
    payload: dict

    @property
    def ref(self) -> str:
        return f"{self.observation_id}@{self.revision}"


@dataclass
class Snapshot:
    observations: list     # current ACTIVE observations, every code
    tps: dict              # tp -> [Obs], card codes with a known time
    unknown_time: list     # card-code observations with unknown time (shown in K1, never in a tp)


def _obs(p: dict, tz: str) -> Obs:
    temporal = p["temporal"]
    instant, day = None, None
    if temporal["role"] == "INSTANT":
        instant = parse_instant(temporal["observed_at"])
        day = local_day(instant, tz).isoformat()  # time point = local calendar day of the instance
    elif temporal["role"] == "DAY":
        day = temporal["observed_date"]           # used as given; its tz is informational
    value = Decimal(p["value_canonical"]) if p["value_type"] == "DECIMAL" else p["value_canonical"] == "true"
    return Obs(p["observation_id"], p["revision"], p["code"], p["value_type"], value, p["comparator"],
               p["unit_canonical"], temporal["role"], instant, day, p)


def take_snapshot(conn, ctx: InstanceContext, card: Card, *, read=None) -> Snapshot:
    if read is not None:
        snap = Snapshot(list(read.observations), {}, [])
        for obs in snap.observations:
            if obs.code in card.codes:
                if obs.day is None:
                    snap.unknown_time.append(obs)
                else:
                    snap.tps.setdefault(obs.day, []).append(obs)
        return snap
    newest = {}
    for oid, rev, payload in conn.execute("SELECT observation_id, revision, payload FROM h1_inbox"):
        if oid not in newest or rev > newest[oid][0]:
            newest[oid] = (rev, payload)
    snap = Snapshot([], {}, [])
    for oid in sorted(newest):
        p = strict_loads(newest[oid][1])
        if p["status"] != "ACTIVE":
            continue
        obs = _obs(p, ctx.tz)
        snap.observations.append(obs)
        if obs.code in card.codes:
            if obs.day is None:
                snap.unknown_time.append(obs)
            else:
                snap.tps.setdefault(obs.day, []).append(obs)
    return snap


def _select(code: str, kind: str, cands: list, mode: str) -> Value:
    if len(cands) == 1:
        o = cands[0]
        return Value(code, kind, o.value, o.comparator, o.unit, False, (o.ref,))
    conflict = Value(code, kind, None, None, cands[0].unit, True, tuple(sorted(o.ref for o in cands)))
    if mode == "ANY_TRUE":
        value = any(o.value for o in cands)
        return Value(code, kind, value, None, None, False, tuple(sorted(o.ref for o in cands if o.value == value)))
    if mode == "MAX":
        if any(o.comparator is not None for o in cands):
            return conflict
        top = max(o.value for o in cands)
        return Value(code, kind, top, None, cands[0].unit, False,
                     tuple(sorted(o.ref for o in cands if o.value == top)))
    if any(o.role != "INSTANT" for o in cands):      # LATEST needs exact instants for every candidate
        return conflict
    ordered = sorted(cands, key=lambda o: o.instant)
    if ordered[-1].instant == ordered[-2].instant:
        return conflict
    o = ordered[-1]
    return Value(code, kind, o.value, o.comparator, o.unit, False, (o.ref,))


def values_at(card: Card, observations: list) -> dict:
    groups = {}
    for o in observations:
        groups.setdefault(o.code, []).append(o)
    return {code: _select(code, obs[0].kind, obs, card.rulepack.selection_mode(code, obs[0].kind))
            for code, obs in groups.items()}


def input_set(snap: Snapshot, card: Card, tp: str) -> frozenset:
    """Everything an evaluation of tp may read: its own observations + dynamic-code history."""
    pinned = {(o.observation_id, o.revision, "TP") for o in snap.tps.get(tp, [])}
    for day, observations in snap.tps.items():
        if day < tp:
            pinned |= {(o.observation_id, o.revision, "HISTORY") for o in observations
                       if o.code in card.dynamic.codes}
    return frozenset(pinned)


def evaluate_tp(card: Card, tp: str, values_cache: dict) -> tuple:
    from compute_snapshot import capture, core_point
    return core_point(*capture(card.rulepack.rules, card.rulepack.combine, ENGINE_VERSION, tp, values_cache),
                      eval_rule, combine_level)


# ----------------------------------------------------------------------------- runs

def latest_results(conn, card_def_id: str) -> dict:
    latest = {}
    for run_id, tp, status, level, result in conn.execute(
            "SELECT rt.run_id, rt.tp_date, rt.status, rt.level, rt.result FROM run_tp rt "
            "JOIN run r ON r.run_id = rt.run_id WHERE r.card_def_id = ? ORDER BY rt.run_id", (card_def_id,)):
        latest[tp] = {"run_id": run_id, "status": status, "level": level, "result": result}
    for tp, item in latest.items():
        item["inputs"] = frozenset(conn.execute(
            "SELECT observation_id, revision, role FROM run_input WHERE run_id = ? AND tp_date = ?",
            (item["run_id"], tp)).fetchall())
    return latest


def classify(conn, snap: Snapshot, card: Card) -> tuple:
    """NEW = never evaluated under this card definition; STALE = inputs changed; FRESH = up to date."""
    latest = latest_results(conn, card.card_def_id)
    return classify_values(latest, snap, card)


def classify_values(latest, snap, card):
    status = {}
    for tp in snap.tps:
        item = latest.get(tp)
        if item is None:
            status[tp] = "NEW"
        elif item["status"] == "VANISHED" or item["inputs"] != input_set(snap, card, tp):
            status[tp] = "STALE"
        else:
            status[tp] = "FRESH"
    for tp, item in latest.items():
        if tp not in snap.tps and item["status"] == "EVALUATED":
            status[tp] = "STALE"  # all its observations are gone; recompute records VANISHED
    return status, latest


def evaluate_run_point(card, snap, tp, values_cache):
    if tp in snap.tps:
        level, result = evaluate_tp(card, tp, values_cache)
        status = "EVALUATED"
    else:
        level, result, status = "NONE", {"tp": tp, "status": "VANISHED"}, "VANISHED"
    return status, level, result


def apply_run_point(conn, run_id, tp, status, level, result):
    text = canonical_json(result)
    conn.execute("INSERT INTO run_tp (run_id, tp_date, status, level, result, result_sha256) "
                 "VALUES (?, ?, ?, ?, ?, ?)", (run_id, tp, status, level, text, sha256_hex(text.encode())))


def run_evaluation(conn, ctx: InstanceContext, card: Card, snap: Snapshot, tps, trigger: str, started_at: str,
                   channels: list, *, prepared=None) -> tuple:
    """Results, pinned inputs, alert state and alert intent are committed together, or not at all."""
    values_cache = {tp: values_at(card, obs) for tp, obs in snap.tps.items()} if prepared is None else None
    with (nullcontext() if conn.in_transaction else transaction(conn)):
        conn.execute("INSERT OR IGNORE INTO card_def (card_def_id, card_id, definition, registered_at) "
                     "VALUES (?, ?, ?, ?)", (card.card_def_id, card.card_id, canonical_json(card.definition),
                                             started_at))
        run_id = conn.execute("INSERT INTO run (card_def_id, trigger, started_at) VALUES (?, ?, ?)",
                              (card.card_def_id, trigger, started_at)).lastrowid
        for tp in sorted(tps):
            status, level, result = (evaluate_run_point(card, snap, tp, values_cache)
                                     if prepared is None else prepared[tp].unwrap()[:3])
            apply_run_point(conn, run_id, tp, status, level, result)
            if status == "EVALUATED":
                conn.executemany(
                    "INSERT INTO run_input (run_id, tp_date, observation_id, revision, role) VALUES (?, ?, ?, ?, ?)",
                    [(run_id, tp, oid, rev, role) for oid, rev, role in sorted(
                        input_set(snap, card, tp) if prepared is None else prepared[tp].unwrap()[3])])
        alert = _record_alert_intent(conn, ctx, card, snap, run_id, started_at, channels)
    return run_id, alert


def sync(conn, ctx: InstanceContext, registry: DictionaryRegistry, card: Card, *, now: str, notifiers,
         read_provider=None, imported_summary=None, recover=True) -> dict:
    recovered = deliver_pending(conn, notifiers, now) if recover else []  # original pre-import collection
    imported = (import_pending(conn, ctx, registry, imported_at=now)
                if imported_summary is None else imported_summary)
    # The provider must run after import, including partial imports. Never reuse a
    # pre-import view or a view from another sync/instance.
    snap = take_snapshot(conn, ctx, card, read=read_provider() if read_provider is not None else None)
    with transaction(conn):
        status, _ = classify(conn, snap, card)
        targets = sorted(tp for tp, s in status.items() if s in ("NEW", "STALE"))
        new = [tp for tp in targets if status[tp] == "NEW"]
        updated = [tp for tp in targets if status[tp] == "STALE"]
        trigger = "AUTO_UPDATE" if updated else "SYNC"
        run_id, alert = (run_evaluation(conn, ctx, card, snap, targets, trigger, now, [n.channel for n in notifiers])
                         if targets else (None, None))
    deliveries = deliver_pending(conn, notifiers, now)
    status, _ = classify(conn, snap, card)
    return {"import": imported, "evaluated": targets, "new": new, "updated": updated, "run_id": run_id,
            "alert": alert,
            "deliveries": recovered + deliveries, "stale": sorted(tp for tp, s in status.items() if s == "STALE")}


def recompute(conn, ctx: InstanceContext, card: Card, *, now: str, notifiers, tps=None) -> dict:
    snap = take_snapshot(conn, ctx, card)
    status, _ = classify(conn, snap, card)
    targets = sorted(tps) if tps is not None else sorted(tp for tp, s in status.items() if s in ("STALE", "NEW"))
    if not targets:
        return {"evaluated": [], "run_id": None, "alert": None, "deliveries": deliver_pending(conn, notifiers, now)}
    run_id, alert = run_evaluation(conn, ctx, card, snap, targets, "RECOMPUTE", now, [n.channel for n in notifiers])
    return {"evaluated": targets, "run_id": run_id, "alert": alert,
            "deliveries": deliver_pending(conn, notifiers, now)}


def alert_message(card: Card, tp: str, level: str, drivers: list) -> tuple:
    changes = [card.labels[d["code"]] + change_word(d["direction"], d.get("measure"))
               for d in drivers if d["kind"] == "DYNAMIC"]
    rules = [card.rulepack.rules[d["rule"]]["short_zh"] for d in drivers
             if d["kind"] == "RULE" and d["result"] == "MET"]
    body = f"{tp} 综合关注等级：{LEVEL_ZH[level]}。"
    if changes:
        body += "需要关注的变化：" + "、".join(changes) + "。"
    if rules:
        body += "达到界值的规则：" + "、".join(rules) + "。"
    body += ALERT_SUFFIX
    check_alert_copy(ALERT_TITLE, body)
    return ALERT_TITLE, body


def check_alert_copy(title: str, body: str) -> None:
    if not body.endswith(ALERT_SUFFIX):
        raise H1Error("ALERT_COPY_UNSAFE", "fixed suffix missing")
    text = title + body[:-len(ALERT_SUFFIX)]
    for word in BANNED_IN_ALERT:
        if word in text:
            raise H1Error("ALERT_COPY_UNSAFE", "banned wording")


def _record_alert_intent(conn, ctx: InstanceContext, card: Card, snap: Snapshot, run_id: int, now: str,
                         channels: list):
    """Runs INSIDE run_evaluation's transaction. Edge trigger on the CURRENT state = level of the latest
    evaluated time point; an intent is recorded only when that level ranks higher than the previously
    recorded state. Dedupe key (instance, card, tp, level): the same tp reaching the same level alerts once.
    """
    latest = latest_results(conn, card.card_def_id)
    evaluated = [tp for tp, item in latest.items() if item["status"] == "EVALUATED" and tp in snap.tps]
    if not evaluated:
        return None
    tp = max(evaluated)
    level = latest[tp]["level"]
    previous = conn.execute("SELECT tp_date, level FROM alert_state WHERE card_id = ? ORDER BY id DESC LIMIT 1",
                            (card.card_id,)).fetchone()
    if previous is not None and tuple(previous) == (tp, level):
        return None
    conn.execute("INSERT INTO alert_state (card_id, tp_date, level, run_id, recorded_at) VALUES (?, ?, ?, ?, ?)",
                 (card.card_id, tp, level, run_id, now))
    if LEVEL_RANK[level] <= (LEVEL_RANK[previous[1]] if previous else 0):
        return None
    key = f"{ctx.instance_id}|{card.card_id}|{tp}|{level}"
    title, body = alert_message(card, tp, level, strict_loads(latest[tp]["result"])["drivers"])
    inserted = conn.execute(
        "INSERT OR IGNORE INTO alert_log (dedupe_key, card_id, tp_date, level, run_id, title, body, channels, "
        "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (key, card.card_id, tp, level, run_id, title, body, canonical_json(sorted(set(channels))), now)).rowcount
    if inserted != 1:
        return None
    return {"dedupe_key": key, "tp": tp, "level": level, "title": title, "body": body}


# Default retains the synchronous delivery path. Optional scopes are save-request local.
SAVE_DELIVERY_OUTSIDE_LOCK = True
_DELIVERY_GUARD = threading.Lock()
_DELIVERY_CLAIMS = set()
# Sent but not yet recorded (this process only): later collections record these without sending again.
_DELIVERY_UNRECORDED = {}
RECORD_ATTEMPTS = 3
_DELIVERY_LOCAL = threading.local()


@contextmanager
def save_delivery_scope(eligible, on_error):
    if not SAVE_DELIVERY_OUTSIDE_LOCK or not eligible or getattr(_DELIVERY_LOCAL, "jobs", None) is not None:
        yield
        return
    jobs = []
    _DELIVERY_LOCAL.jobs = jobs
    try:
        yield
    finally:
        del _DELIVERY_LOCAL.jobs
        _flush_deliveries(jobs, on_error=on_error)


def _record_delivery(conn, key, channel, outcome, detail, now):
    """Records one attempt; a transient storage error is retried because the send already happened."""
    for attempt in range(RECORD_ATTEMPTS):
        try:
            conn.execute("INSERT INTO alert_delivery (dedupe_key, channel, outcome, detail, attempted_at) "
                         "VALUES (?, ?, ?, ?, ?)", (key, channel, outcome, detail, now))
            return
        except Exception:
            if attempt + 1 == RECORD_ATTEMPTS:
                raise


def connect(path):
    """Open the existing delivery database through the checked main-store policy."""
    track = Path(path)
    return open_main_db(track, SCHEMA_ID, DDL, root=track.parent.parent)


def _flush_deliveries(jobs, on_error=None):
    out = []
    for claim, send, preparation_error, now in jobs:
        path, key, channel = claim
        conn = None
        try:
            conn = connect(path)
            with _DELIVERY_GUARD:
                sent = _DELIVERY_UNRECORDED.get(claim)
            if sent is not None:
                outcome, detail, now = sent  # already sent earlier in this process: record only, never send again
            else:
                try:
                    if preparation_error is not None:
                        raise preparation_error
                    send()
                    outcome, detail = "SENT", ""
                except Exception as exc:  # a failing channel does not fail the save
                    outcome, detail = "FAILED", type(exc).__name__
            try:
                _record_delivery(conn, key, channel, outcome, detail, now)
            except Exception:
                with _DELIVERY_GUARD:
                    _DELIVERY_UNRECORDED[claim] = (outcome, detail, now)
                raise
            with _DELIVERY_GUARD:
                _DELIVERY_UNRECORDED.pop(claim, None)
            out.append({"dedupe_key": key, "channel": channel, "outcome": outcome})
        except Exception as exc:
            if on_error is None:
                # Release any unattempted claims if this direct caller propagates the error.
                with _DELIVERY_GUARD:
                    _DELIVERY_CLAIMS.difference_update(job[0] for job in jobs)
                raise
            on_error(exc)
        finally:
            if conn is not None:
                conn.close()
            with _DELIVERY_GUARD:
                _DELIVERY_CLAIMS.discard(claim)
    return out


def deliver_pending(conn, notifiers, now: str) -> list:
    if not SAVE_DELIVERY_OUTSIDE_LOCK:
        return _deliver_pending_sync(conn, notifiers, now)
    path = next(row[2] for row in conn.execute("PRAGMA database_list") if row[1] == "main")
    if not path:
        # Non-persistent callers cannot outlive their connection; retain their old behavior.
        return _deliver_pending_sync(conn, notifiers, now)
    by_channel = {n.channel: n for n in notifiers}
    jobs = []
    try:
        for key, title, body, level, channels in conn.execute(
                "SELECT dedupe_key, title, body, level, channels FROM alert_log ORDER BY created_at, rowid").fetchall():
            for channel in strict_loads(channels):
                if channel not in by_channel:
                    continue
                claim = (path, key, channel)
                with _DELIVERY_GUARD:
                    if claim in _DELIVERY_CLAIMS:
                        continue
                    if conn.execute("SELECT 1 FROM alert_delivery WHERE dedupe_key=? AND channel=? LIMIT 1",
                                    (key, channel)).fetchone():
                        _DELIVERY_UNRECORDED.pop(claim, None)
                        continue
                    _DELIVERY_CLAIMS.add(claim)
                    resend_free = claim in _DELIVERY_UNRECORDED
                if resend_free:
                    jobs.append((claim, None, None, now))
                    continue
                notifier = by_channel[channel]
                try:
                    prepare = getattr(notifier, "prepare", None)
                    send = (prepare(title, body, level) if prepare else
                            lambda n=notifier, t=title, b=body, l=level: n.send(t, b, l))
                    error = None
                except Exception as exc:
                    send, error = None, exc
                jobs.append((claim, send, error, now))
    except BaseException:
        with _DELIVERY_GUARD:
            _DELIVERY_CLAIMS.difference_update(job[0] for job in jobs)
        raise
    queue = getattr(_DELIVERY_LOCAL, "jobs", None)
    if queue is not None:
        queue.extend(jobs)
        return []
    return _flush_deliveries(jobs)


def _deliver_pending_sync(conn, notifiers, now: str) -> list:
    """Sends every (alert, channel) that was intended but has no recorded attempt yet.

    A channel whose notifier is not connected right now stays pending (shown in the UI).
    """
    by_channel = {n.channel: n for n in notifiers}
    done = set(conn.execute("SELECT dedupe_key, channel FROM alert_delivery").fetchall())
    out = []
    for key, title, body, level, channels in conn.execute(
            "SELECT dedupe_key, title, body, level, channels FROM alert_log ORDER BY created_at, rowid").fetchall():
        for channel in strict_loads(channels):
            if (key, channel) in done or channel not in by_channel:
                continue
            try:
                by_channel[channel].send(title, body, level)
                outcome, detail = "SENT", ""
            except Exception as exc:  # noqa: BLE001 - a failing channel must not stop the others
                outcome, detail = "FAILED", type(exc).__name__
            conn.execute("INSERT INTO alert_delivery (dedupe_key, channel, outcome, detail, attempted_at) "
                         "VALUES (?, ?, ?, ?, ?)", (key, channel, outcome, detail, now))
            out.append({"dedupe_key": key, "channel": channel, "outcome": outcome})
    return out


def ack_alert(conn, dedupe_key: str, *, acked_at: str) -> None:
    conn.execute("INSERT OR IGNORE INTO alert_ack (dedupe_key, acked_at) VALUES (?, ?)", (dedupe_key, acked_at))


class RecordingNotifier:
    channel = "TEST"

    def __init__(self):
        self.sent = []

    def send(self, title: str, body: str, level: str) -> None:
        self.sent.append((title, body, level))


class BannerNotifier:
    """In-app banner is pull-based: the UI shows the newest un-acked alert_log row."""
    channel = "BANNER"

    def send(self, title: str, body: str, level: str) -> None:
        return None


class MacOSNotifier:
    channel = "MACOS"

    @staticmethod
    def argv(title: str, body: str) -> list:
        # Text travels as argv items, never spliced into AppleScript source (no injection).
        return ["osascript", "-e", "on run argv", "-e",
                "display notification (item 2 of argv) with title (item 1 of argv)", "-e", "end run",
                title, body]

    def send(self, title: str, body: str, level: str) -> None:
        subprocess.run(self.argv(title, body), check=True, timeout=10, capture_output=True)


class SomaLoopNotifier:
    """The SDK call is injected by the device owner: vibrate(pattern: str) -> None."""
    channel = "SOMALOOP"

    def __init__(self, vibrate, patterns=None):
        self._vibrate = vibrate
        self.patterns = patterns or {"WATCH": "SHORT", "ALERT": "LONG"}

    def send(self, title: str, body: str, level: str) -> None:
        self._vibrate(self.patterns[level])


# ----------------------------------------------------------------------------- UI state

def _obs_json(o: Obs, card: Card) -> dict:
    p = o.payload
    return {"ref": o.ref, "code": o.code, "label_zh": card.labels.get(o.code, o.code), "tp": o.day,
            "value_raw": p["value_raw"], "unit_raw": p["unit_raw"], "comparator": p["comparator"],
            "value_canonical": p["value_canonical"], "unit_canonical": p["unit_canonical"],
            "converted": p["conversion_rule"] != "IDENTITY", "conversion_rule": p["conversion_rule"],
            "temporal": p["temporal"], "source_kind": p["source_kind"], "trust_tier": p["trust_tier"],
            "source_ref": p["source_ref"]}


def card_state(conn, ctx: InstanceContext, card: Card, last_sync: dict | None = None, *, read=None, history=True) -> dict:
    """Everything the UI needs, as JSON-ready data. The UI renders; it never computes."""
    snap = take_snapshot(conn, ctx, card, read=read)
    status, latest = classify(conn, snap, card)
    h1 = h1_status(conn, ctx)

    def order(o: Obs):
        return (o.day or "~", o.instant.astimezone(timezone.utc).isoformat() if o.instant else "", o.code)

    timepoints = []
    for tp in sorted(set(snap.tps) | set(latest)):
        item = latest.get(tp)
        shown_status = status.get(tp, "VANISHED")
        if shown_status == "FRESH" and h1["outdated"]:
            shown_status = "UNVERIFIED"  # newer 星炬 commits exist but are not imported: never show as current
        timepoints.append({"tp": tp, "status": shown_status,
                           "run_id": item["run_id"] if item else None,
                           "level": item["level"] if item else None,
                           "level_zh": LEVEL_ZH[item["level"]] if item else None,
                           "result": strict_loads(item["result"]) if item else None})
    evaluated = [t for t in timepoints
                 if t["tp"] in snap.tps and t["tp"] in latest and latest[t["tp"]]["status"] == "EVALUATED"]
    current = evaluated[-1] if evaluated else None  # same definition as check_alert()
    alerts = []
    for key, tp, level, title, body, channels, created_at in conn.execute(
            "SELECT dedupe_key, tp_date, level, title, body, channels, created_at FROM alert_log "
            "ORDER BY created_at, rowid"):
        acked = conn.execute("SELECT 1 FROM alert_ack WHERE dedupe_key = ?", (key,)).fetchone() is not None
        deliveries = [dict(zip(("channel", "outcome", "detail"), row)) for row in conn.execute(
            "SELECT channel, outcome, detail FROM alert_delivery WHERE dedupe_key = ? ORDER BY id", (key,))]
        attempted = {d["channel"] for d in deliveries}
        alerts.append({"dedupe_key": key, "tp": tp, "level": level, "title": title, "body": body,
                       "created_at": created_at, "acked": acked, "deliveries": deliveries,
                       "pending_channels": [c for c in strict_loads(channels) if c not in attempted]})
    return {
        "instance": {"instance_id": ctx.instance_id, "kind": ctx.kind, "display_name": ctx.display_name,
                     "tz": ctx.tz},
        "disclaimer": DISCLAIMER,
        "card": {"card_id": card.card_id, "card_def_id": card.card_def_id, "engine_version": ENGINE_VERSION,
                 "rulepack_version": card.rulepack.version, "dynamic_version": card.dynamic.version,
                 "dynamic_provenance": card.dynamic.provenance, "sensitivity": card.dynamic.sensitivity,
                 "expert_review": {rid: r["expert_review"] for rid, r in card.rulepack.rules.items()}},
        "h1": dict(h1, last_sync=last_sync),
        "timeline": [_obs_json(o, card) for o in sorted(snap.observations, key=order)] if history else [],
        "unknown_time": [_obs_json(o, card) for o in snap.unknown_time] if history else [],
        "timepoints": timepoints,
        "current": None if current is None else {"tp": current["tp"], "level": current["level"],
                                                  "level_zh": current["level_zh"],
                                                  "stale": current["status"] == "STALE",
                                                  "outdated": h1["outdated"]},
        "stale_count": sum(1 for s in status.values() if s == "STALE"),
        "level_history": [dict(zip(("tp", "level", "run_id", "recorded_at"), row)) for row in conn.execute(
            "SELECT tp_date, level, run_id, recorded_at FROM alert_state WHERE card_id = ? ORDER BY id",
            (card.card_id,))] if history else [],
        "alerts": alerts,
        "banner": next((a for a in reversed(alerts) if not a["acked"]), None),
    }


def compute_revision(conn):
    """Append-only dependencies; delivery/ack/display-only entries are not inputs.

    Used only after open_db verified the append-only triggers. Arbitrary external
    mutation of a live SQLite file is outside this process's ownership contract.
    """
    result = []
    for table in ('h1_inbox', 'h1_import_log', 'card_def', 'run', 'run_tp', 'run_input', 'alert_state', 'alert_log'):
        result.append(tuple(conn.execute('SELECT COALESCE(MAX(rowid),0), COUNT(*) FROM ' + table).fetchone()))
    result.append(tuple(conn.execute("SELECT COALESCE(MAX(id),0),COUNT(*) FROM card_setting "
                                     "WHERE key NOT IN ('seen_run','wall_pin','wall_hide')").fetchone()))
    return tuple(result)


def apply_prepared_sync(conn, ctx, card, snap, planned, now, channels, guard):
    """Caller owns A; original sync unit owns BEGIN and result/intent atomicity."""
    with transaction(conn):
        guard.before(conn)
        status, targets, points = planned.unwrap()
        updated = [tp for tp in targets if status[tp] == 'STALE']
        new = [tp for tp in targets if status[tp] == 'NEW']
        trigger = 'AUTO_UPDATE' if updated else 'SYNC'
        run_id, alert = (run_evaluation(conn, ctx, card, snap, targets, trigger, now, channels, prepared=points)
                         if targets else (None, None))
        guard.advance(conn)
    return {'new': new, 'updated': updated, 'run_id': run_id, 'alert': alert}
