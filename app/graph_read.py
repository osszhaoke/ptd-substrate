"""Bounded, opt-in evidence read projections; no ledger or schema writes.

SQLite event candidates are selected before observation payloads are decoded.
JSONL source metadata and authorization records still require whole-ledger
reads; the response declares this limitation rather than calling it SQL paging.
"""
from __future__ import annotations

from read_view import read_connection

import base64
from contextlib import closing
from datetime import datetime, timezone
import json
import threading
import time
import uuid

import custom_cards
import device_watch
import engines
import evidence_graph as graph
from cards import open_startrack
from h1_common import H1Error
from startorch_outbox import open_startorch

MAX_LIMIT = 200
CURSOR_TTL = 900
MAX_SNAPSHOTS = 16
MAX_SNAPSHOT_BYTES = 8 * 1024 * 1024
MAX_TOTAL_SNAPSHOT_BYTES = 32 * 1024 * 1024
MAX_ISSUED_POSITIONS = 4096
_LOCK = threading.RLock()
_SNAPSHOTS = {}
_CLEANUP_TIMER = None
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_INVALID_TIME = -(2 ** 63)
_FIRST_POSITION = (2 ** 63 - 1, 9, 2 ** 63 - 1)


def _stamp(value):
    try:
        delta = datetime.fromisoformat(value).astimezone(timezone.utc) - _EPOCH
        return (delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds
    except (ValueError, TypeError, OverflowError):
        return _INVALID_TIME


def _bad(code="GRAPH_CURSOR_INVALID"):
    raise H1Error(code, "读取位置无效或已过期，请刷新记录列表")


def _identity(inst):
    return id(inst), str(inst.ctx.root.resolve()), inst.ctx.instance_id


def _limit(value):
    if isinstance(value, bool):
        raise H1Error("GRAPH_LIMIT_INVALID", "每页条数应为 1 至 200")
    try:
        number = int(value)
    except (ValueError, TypeError):
        raise H1Error("GRAPH_LIMIT_INVALID", "每页条数应为 1 至 200") from None
    if str(number) != str(value) or not 1 <= number <= MAX_LIMIT:
        raise H1Error("GRAPH_LIMIT_INVALID", "每页条数应为 1 至 200")
    return number


def auth_context(inst):
    """Match snapshot's persisted push evidence, without reading observations."""
    alerts = []
    with read_connection(open_startrack, inst.ctx) as conn:
        where = "" if inst.sjia else " WHERE card_id LIKE 'threshold-%'"
        rows = conn.execute("SELECT dedupe_key, tp_date, title, created_at, channels "
                            "FROM alert_log" + where + " ORDER BY created_at, rowid")
        for key, tp, title, at, channels in rows:
            deliveries = [{"channel": channel, "outcome": outcome}
                          for channel, outcome in conn.execute(
                              "SELECT channel, outcome FROM alert_delivery WHERE dedupe_key=? ORDER BY id", (key,))]
            alert = {"dedupe_key": key, "tp": tp, "title": title,
                     "created_at": at, "deliveries": deliveries}
            if inst.sjia:
                attempted = {item["channel"] for item in deliveries}
                alert["pending_channels"] = [channel for channel in json.loads(channels)
                                             if channel not in attempted]
            alerts.append(alert)
        hidden = {value for value, in conn.execute("SELECT value FROM card_setting WHERE key='alert_hidden'")}
    return {"alerts": [item for item in alerts if item["dedupe_key"] not in hidden],
            "device_events": device_watch.DeviceEvents(inst.ctx.root).list()[-20:]}


# Public name used by trace/records routes; retained short internal name above.
audit_context = auth_context


def knowledge_context(inst):
    """Only persisted labels/bindings needed by knowledge(); no health series.

    Preserve snapshot's ObservationRead semantics, including any inbox prefix
    already present before a complete import cursor. This is deliberately not
    the data-read pagination contract, which is committed-prefix bound.
    """
    import vitals_cards
    cutoffs = {}
    for source, value in (inst.spec.get("archived_streams") or {}).items():
        if source != "DEVICE_SOMALOOP":
            raise ValueError("DISPLAY_RETENTION_SOURCE_INVALID")
        moment = datetime.fromisoformat(value)
        if moment.tzinfo is None:
            raise ValueError("DISPLAY_RETENTION_TIME_INVALID")
        cutoffs[source] = moment
    def visible(source, role, at):
        cutoff = cutoffs.get(source)
        return int(cutoff is None or role != "INSTANT" or
                   datetime.fromisoformat(at.replace("Z", "+00:00")) >= cutoff)
    with read_connection(open_startrack, inst.ctx) as conn:
        conn.create_function("kg_visible", 3, visible, deterministic=True)
        # Unit/value/time are not consumed by KG. Definitions retain their own
        # stored metadata; current metric labels/families come from the registry.
        available = conn.execute("SELECT DISTINCT json_extract(h.payload,'$.code') "
            "FROM h1_inbox h WHERE NOT EXISTS (SELECT 1 FROM h1_inbox n "
            "WHERE n.observation_id=h.observation_id AND n.revision>h.revision) "
            "AND json_extract(h.payload,'$.status')='ACTIVE' "
            "AND kg_visible(json_extract(h.payload,'$.source_kind'), "
            "json_extract(h.payload,'$.temporal.role'),json_extract(h.payload,'$.temporal.observed_at'))")
        codes = inst.app.registry.current.codes
        items = [{"code": code, "family": codes[code].family, "label_zh": codes[code].label_zh}
                 for code, in available if code in codes]
        items.sort(key=lambda item: (item["family"], item["code"]))
        setup = inst.setup().state()
        vitals, known = inst.vitals_view(conn, setup, vit={"items": items})
        snap = {"card_setup": setup, "vitals_all": {"items": items}, "vitals": vitals,
                "known_sources": known, "wall_prefs": inst.wall_preferences(conn)}
        snap["vitals_cards"] = vitals_cards.state(conn, snap)
    snap.update(audit_context(inst))
    return snap


def _latest_timepoints(conn, *, cid=None, definition=None):
    column, value = ("c.card_def_id", definition) if definition else ("c.card_id", cid)
    return conn.execute(
        "SELECT t.tp_date,t.status,t.level,t.result FROM run_tp t JOIN run r USING(run_id) "
        "JOIN card_def c USING(card_def_id) WHERE " + column + "=? AND (t.tp_date,t.run_id) IN ("
        "SELECT x.tp_date,max(x.run_id) FROM run_tp x JOIN run xr ON xr.run_id=x.run_id "
        "JOIN card_def c ON c.card_def_id=xr.card_def_id WHERE " + column + "=? GROUP BY x.tp_date) "
        "ORDER BY t.tp_date", (value, value)).fetchall()


def cards(inst):
    """Stored calculation timepoints only; never label EVALUATED as FRESH."""
    out, hidden = [], graph.hidden_cards(inst)
    with read_connection(open_startrack, inst.ctx) as conn:
        names = engines.card_names(conn)
        selected = []
        if inst.sjia and "sjia-mas" not in hidden:
            selected.append(("sjia-mas", "sJIA 关注卡", inst.card(conn).card_def_id, False))
        selected.extend((item["card_id"], item["definition"]["name"], item["card_def_id"], False)
                        for item in custom_cards.cards(conn) if item["card_id"] not in hidden)
        active = sorted(engines.active(conn).items(),
                        key=lambda pair: engines.ORDER.index(pair[0]) if pair[0] in engines.ORDER else 99)
        engine_ids = [engines.CARD_PREFIX + rule for tpl, item in active if tpl != "MAS"
                      for rule in item["conf"]["rules"]]
        engine_ids += [cid for cid, in conn.execute(
            "SELECT DISTINCT card_id FROM card_def WHERE json_extract(definition,'$.template')='LIVE' ORDER BY card_id")
                       if cid not in engine_ids]
        selected.extend((cid, names.get(cid, cid), None, True) for cid in engine_ids if cid not in hidden)
        for cid, name, definition, engine in selected:
            timepoints = []
            for tp, status, level, raw in _latest_timepoints(conn, cid=cid, definition=definition):
                if engine and status != "EVALUATED":
                    continue
                if cid != "sjia-mas" and not engine and not level:
                    continue
                row = {"tp": tp, "level": level, "level_zh": graph.LEVEL_ZH.get(level), "run_status": status}
                if engine:
                    result = json.loads(raw)
                    row.update(level_zh=result.get("text") or result.get("reason") or "算不了",
                               status=result.get("status"), value=result.get("value"), unit=result.get("unit"))
                timepoints.append(row)
            if engine and not timepoints:
                continue
            item = {"card_id": cid, "name": name, "timepoints": timepoints}
            if engine:
                item["engine"] = True
            out.append(item)
    return {"cards": out, "projection": "stored-calculation-timepoints/1"}


def _source_events(inst, receipts):
    # Readers are shared below the HTTP layer; keep lazy loading behavior.
    from instance_services import GeneReader as GeneStore, SourceReader as Sources
    events = []

    def add(identifier, at, text, ref):
        events.append({"id": identifier, "lane": "source", "at": at, "text": text, "ref": ref})

    for item in GeneStore(inst).list():
        add("gene:" + item["receipt_id"], item["received_at"],
            f"纳管基因数据 {item['file_name']} · 指纹 {item['sha256'][:12]}", {"gene": item["receipt_id"]})
    for index, item in enumerate(receipts):
        add("bridge:" + str(index), item.get("when") or item.get("at") or "",
            "苹果健康同步 · 收到 %s 条" % item.get("received", "?"), {})
    for index, item in enumerate(device_watch.DeviceEvents(inst.ctx.root).list()[-20:]):
        add("device:" + str(item.get("id", index)), item["at"],
            item["title"] + " · " + (item.get("reason") or item.get("body", "")), {})
    folder = inst.ctx.root / "startorch" / "originals"
    for path in sorted(folder.glob("*.recognition.json")) if folder.exists() else []:
        item = json.loads(path.read_text("utf-8"))
        add("recognition:" + path.name, item.get("recognized_at", ""),
            f"识别化验单 {item.get('name', '')} · {len(item.get('rows') or [])} 项候选 · 原件 {item.get('original', '')}",
            {"original": item.get("original")})
    source = (Sources(inst).read().get("oura") or {})
    for field, label in (("connected_at", "接入 Oura（官方授权）"), ("disconnected_at", "断开 Oura")):
        if source.get(field):
            add("oura:" + field, source[field], label, {})
    return events


def _sql_sources(lane):
    if lane == "data":
        return [("observation", "formal_observation", "saved_at", 0),
                ("commit", "h1_commit", "committed_at", 1)]
    if lane == "state":
        return [("run", "run", "started_at", 2), ("alert", "alert_log", "created_at", 3)]
    return []


def _conn_for(kind, torch, track):
    return torch if kind in ("observation", "commit") else track


def _where(kind, hidden):
    if kind == "run" and hidden:
        return " AND card_def_id NOT IN (SELECT card_def_id FROM card_def WHERE card_id IN (%s))" % ",".join("?" for _ in hidden), tuple(sorted(hidden))
    if kind == "alert" and hidden:
        return " AND card_id NOT IN (%s)" % ",".join("?" for _ in hidden), tuple(sorted(hidden))
    return "", ()


def _open_snapshot(inst, lane, receipts):
    hidden, anchors, count = graph.hidden_cards(inst), {}, 0
    with read_connection(open_startorch, inst.ctx) as torch, read_connection(open_startrack, inst.ctx) as track:
        for kind, table, _, _ in _sql_sources(lane):
            conn = _conn_for(kind, torch, track)
            anchors[kind] = conn.execute("SELECT coalesce(max(rowid),0) FROM " + table).fetchone()[0]
            where, args = _where(kind, hidden)
            count += conn.execute("SELECT count(*) FROM " + table + " WHERE rowid<=?" + where,
                                  (anchors[kind],) + args).fetchone()[0]
    hidden_count = 0
    if lane == "auth":
        all_rows = inst.cluster.records(auth_context(inst))
        extra = [row for row in all_rows if not row.get("hidden")]
        hidden_count = len(all_rows) - len(extra)
        # Existing records() already resolves ties in stable source order.
        extras = [((_stamp(row["at"]), 5, len(extra) - index), row) for index, row in enumerate(extra)]
    elif lane == "data":
        extra = _source_events(inst, receipts)
        extras = [((_stamp(row["at"]), 4, index), row) for index, row in enumerate(extra)]
    else:
        extras = []
    return {"identity": _identity(inst), "lane": lane, "anchors": anchors, "hidden": hidden,
            "extras": extras, "total": count + len(extras), "hidden_count": hidden_count,
            "created": time.monotonic(), "accessed": time.monotonic(), "issued": set()}


def _prune_expired(now):
    # Caller holds _LOCK; expiry and LRU only discard historical read snapshots.
    for token in list(_SNAPSHOTS):
        if now - _SNAPSHOTS[token]["created"] >= CURSOR_TTL:
            del _SNAPSHOTS[token]


def _schedule_cleanup():
    """At most one scheduled timer, independent of request/refresh frequency."""
    global _CLEANUP_TIMER
    if _CLEANUP_TIMER is not None or not _SNAPSHOTS:
        return
    earliest = min(snapshot["created"] for snapshot in _SNAPSHOTS.values()) + CURSOR_TTL
    _CLEANUP_TIMER = threading.Timer(max(.001, earliest - time.monotonic()), _expire_snapshots)
    _CLEANUP_TIMER.daemon = True
    _CLEANUP_TIMER.start()


def _expire_snapshots():
    global _CLEANUP_TIMER
    with _LOCK:
        _CLEANUP_TIMER = None
        _prune_expired(time.monotonic())
        _schedule_cleanup()


def _register(snapshot):
    with _LOCK:
        _prune_expired(time.monotonic())
        # Serialized UTF-8 metadata bytes, not a claim about Python heap size.
        size = len(json.dumps({k: v for k, v in snapshot.items() if k != "issued"},
                              ensure_ascii=False, default=list).encode("utf-8"))
        if size > MAX_SNAPSHOT_BYTES or size > MAX_TOTAL_SNAPSHOT_BYTES:
            _bad("GRAPH_CURSOR_EXPIRED")
        snapshot["retained_bytes"] = size
        while _SNAPSHOTS and (len(_SNAPSHOTS) >= MAX_SNAPSHOTS or
                sum(s["retained_bytes"] for s in _SNAPSHOTS.values()) + size > MAX_TOTAL_SNAPSHOT_BYTES):
            del _SNAPSHOTS[min(_SNAPSHOTS, key=lambda key: _SNAPSHOTS[key]["accessed"])]
        token = uuid.uuid4().hex
        _SNAPSHOTS[token] = snapshot
        _schedule_cleanup()
        return token


def _encode_cursor(token, snapshot, after):
    with _LOCK:
        position = tuple(after)
        if position not in snapshot["issued"] and len(snapshot["issued"]) >= MAX_ISSUED_POSITIONS:
            _SNAPSHOTS.pop(token, None)
            _bad("GRAPH_CURSOR_EXPIRED")
        snapshot["issued"].add(position)
    raw = json.dumps({"v": 1, "token": token, "instance": snapshot["identity"][-1],
                      "lane": snapshot["lane"], "after": after}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(inst, lane, cursor):
    if not isinstance(cursor, str) or not 1 <= len(cursor) <= 2048:
        _bad()
    try:
        data = json.loads(base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True))
        if set(data) != {"v", "token", "instance", "lane", "after"} or data["v"] != 1:
            _bad()
        if not isinstance(data["token"], str) or len(data["token"]) != 32:
            _bad()
        after = data["after"]
        if not isinstance(after, list) or len(after) != 3 or any(type(value) is not int for value in after):
            _bad()
        with _LOCK:
            snapshot = _SNAPSHOTS.get(data["token"])
            if snapshot is None or time.monotonic() - snapshot["created"] >= CURSOR_TTL:
                _bad("GRAPH_CURSOR_EXPIRED")
            if (snapshot["identity"] != _identity(inst) or data["instance"] != inst.ctx.instance_id
                    or snapshot["lane"] != lane or data["lane"] != lane or tuple(after) not in snapshot["issued"]):
                _bad()
            snapshot["accessed"] = time.monotonic()
        return data["token"], snapshot, tuple(after)
    except (ValueError, TypeError, KeyError, UnicodeDecodeError):
        _bad()


def _candidates(conn, kind, table, timestamp, rank, snapshot, after, limit):
    conn.create_function("graph_timestamp", 1, _stamp, deterministic=True)
    where, args = _where(kind, snapshot["hidden"])
    sql = "SELECT rowid,graph_timestamp(" + timestamp + ") AS stamp FROM " + table + " WHERE rowid<=?" + where
    params = (snapshot["anchors"][kind],) + args
    if after is not None:
        sql += " AND (graph_timestamp(" + timestamp + "),?,rowid)<(?,?,?)"
        params += (rank,) + after
    sql += " ORDER BY stamp DESC,rowid DESC LIMIT ?"
    return [((stamp, rank, rowid), kind, rowid) for rowid, stamp in conn.execute(sql, params + (limit + 1,))]


def _format_event(inst, conn, kind, rowid, names):
    if kind == "observation":
        oid, revision, payload, at = conn.execute(
            "SELECT observation_id,revision,payload,saved_at FROM formal_observation WHERE rowid=?", (rowid,)).fetchone()
        data = json.loads(payload)
        verb = "保存" if revision == 1 else ("撤回" if data.get("status") != "ACTIVE" else "更正")
        label = getattr(inst.app.registry.current.codes.get(data["code"]), "label_zh", data["code"])
        unit = " " + data["unit_raw"] if data.get("unit_raw") else ""
        text = f"{verb} {label} {data['value_raw']}{unit} · 第 {revision} 版 · {graph.SRC_ZH.get(data.get('source_kind'), data.get('source_kind'))}"
        ref = {"observation": oid, "revision": revision}
    elif kind == "commit":
        cid, batch, count, at = conn.execute(
            "SELECT commit_id,batch_id,count,committed_at FROM h1_commit WHERE rowid=?", (rowid,)).fetchone()
        text, ref = f"交给星轨 · 批次 {batch} · {count} 条", {"commit": cid}
    elif kind == "run":
        rid, trigger, at, cid = conn.execute(
            "SELECT r.run_id,r.trigger,r.started_at,c.card_id FROM run r JOIN card_def c USING(card_def_id) WHERE r.rowid=?",
            (rowid,)).fetchone()
        tps = [f"{tp} {graph.LEVEL_ZH.get(level, level)}" for tp, level in conn.execute(
            "SELECT tp_date,level FROM run_tp WHERE run_id=? ORDER BY tp_date", (rid,))]
        if cid == "VITALS":
            count = conn.execute("SELECT count(*) FROM run_input WHERE run_id=?", (rid,)).fetchone()[0]
            tps = [f"{tp.split()[0]} · 取最近读数 {count} 项" for tp in tps]
        shown = tps if len(tps) <= 6 else tps[:3] + [f"…共 {len(tps)} 个时点"]
        text = f"计算 #{rid} · {names.get(cid, cid)} · {graph.TRIGGER_ZH.get(trigger, trigger)} · " + "、".join(shown)
        ref = {"run": rid, "card": cid, "tps": [tp.split()[0] for tp in tps]}
    else:
        _, tp, level, title, at, cid = conn.execute(
            "SELECT dedupe_key,tp_date,level,title,created_at,card_id FROM alert_log WHERE rowid=?", (rowid,)).fetchone()
        text, ref = f"提醒 · {tp} {graph.LEVEL_ZH.get(level, level)} · {title}", {"tp": tp, "card": cid}
    return {"id": kind + ":" + str(rowid), "lane": "data" if kind in ("observation", "commit") else "state",
            "at": at, "text": text, "ref": ref}


def _events(inst, lane, cursor, limit, receipts):
    if cursor:
        token, snapshot, after = _decode_cursor(inst, lane, cursor)
    else:
        snapshot = _open_snapshot(inst, lane, receipts)
        token, after = _register(snapshot), None
    candidates = [(position, "extra", row) for position, row in snapshot["extras"]
                  if after is None or position < after]
    with read_connection(open_startorch, inst.ctx) as torch, read_connection(open_startrack, inst.ctx) as track:
        for kind, table, timestamp, rank in _sql_sources(lane):
            candidates.extend(_candidates(_conn_for(kind, torch, track), kind, table, timestamp, rank,
                                          snapshot, after, limit))
        candidates.sort(key=lambda item: item[0], reverse=True)
        selected = candidates[:limit]
        names = graph._card_names(track) if any(kind == "run" for _, kind, _ in selected) else {}
        items = [dict(row) if kind == "extra" else _format_event(inst, _conn_for(kind, torch, track), kind, row, names)
                 for _, kind, row in selected]
    more = len(candidates) > limit
    return {"items": items, "total": snapshot["total"], "hidden_count": snapshot["hidden_count"],
            "first_cursor": _encode_cursor(token, snapshot, _FIRST_POSITION),
            "has_more": more, "next_cursor": _encode_cursor(token, snapshot, selected[-1][0]) if more else None,
            "snapshot_anchor": token, "lane": lane,
            "read_scope": "authorization-ledger-snapshot" if lane == "auth" else "bounded-sql-with-source-metadata"}


def _summary(inst, receipts):
    # No events(), traceable(), or snapshot(): only SQL counts and source/audit projections.
    counts = {}
    hidden = graph.hidden_cards(inst)
    with read_connection(open_startorch, inst.ctx) as torch, read_connection(open_startrack, inst.ctx) as track:
        for lane in ("data", "state"):
            count = 0
            for kind, table, _, _ in _sql_sources(lane):
                where, args = _where(kind, hidden)
                count += _conn_for(kind, torch, track).execute("SELECT count(*) FROM " + table + " WHERE 1=1" + where, args).fetchone()[0]
            counts[lane] = count
    counts["data"] += len(_source_events(inst, receipts))
    records = inst.cluster.records(auth_context(inst))
    counts["auth"] = sum(not row.get("hidden") for row in records)
    return {"counts": counts, "hidden_auth": len(records) - counts["auth"],
            "read_scope": "sql-counts-with-source-and-authorization-ledger-scan"}


def read(inst, view, lane="", cursor="", limit=50, receipts=None):
    """Opt-in local read API. Cursor limits/binds paging, never authorizes access."""
    if view == "cards":
        if cursor:
            _bad()
        return cards(inst)
    if view == "summary":
        if cursor:
            _bad()
        return _summary(inst, receipts or [])
    if view != "events" or lane not in ("data", "state", "auth"):
        raise H1Error("GRAPH_VIEW_INVALID", "请选择有效的记录类型")
    return _events(inst, lane, cursor, _limit(limit), receipts or [])
