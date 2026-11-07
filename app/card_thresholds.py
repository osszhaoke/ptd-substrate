"""Per-card numeric bounds and edge-triggered notices, using the existing track ledger."""
from contextlib import nullcontext
import json
import re
from decimal import Decimal, InvalidOperation

import custom_cards
from h1_common import canonical_json, sha256_hex
from sqlite_util import transaction

KEY = 'card_threshold'
STATE = 'card_threshold_state'


def configs(track):
    out = {}
    for cid, value in track.execute('SELECT card_id, value FROM card_setting WHERE key=? ORDER BY id', (KEY,)):
        out[cid] = json.loads(value)
    return out


def save(track, ctx, registry, body, now):
    parent, code = str(body.get('card') or ''), str(body.get('code') or '')
    if not re.fullmatch(r'(grp:|cc:|card:|band:)[\w.:-]{1,80}|sleep', parent):
        raise ValueError('请选择状态卡片')
    item = registry.current.codes.get(code)
    if item is None or item.value_type != 'DECIMAL':
        raise ValueError('请选择数值指标')
    bounds = {}
    for k in ('lower', 'upper'):
        raw = body.get(k)
        if raw is None or str(raw).strip() == '':
            bounds[k] = None
            continue
        try:
            val = Decimal(str(raw))
            if not val.is_finite(): raise InvalidOperation
        except InvalidOperation:
            raise ValueError('上下限必须是有限数字') from None
        bounds[k] = format(val, 'f')
    if all(v is not None for v in bounds.values()) and Decimal(bounds['lower']) >= Decimal(bounds['upper']):
        raise ValueError('下限必须小于上限')
    for side in ('lower', 'upper'):
        if body.get('notify_' + side) and bounds[side] is None:
            raise ValueError('请先填写对应阈值，再启用通知')
    cid = 'threshold-' + sha256_hex((parent + '|' + code).encode())[:20]
    d = dict(bounds, card=parent, code=code, name=str(body.get('name') or parent)[:40],
             label=item.label_zh, unit=item.unit_canonical,
             notify_lower=bool(body.get('notify_lower')), notify_upper=bool(body.get('notify_upper')),
             mac=bool(body.get('mac')), kind='CARD_THRESHOLD', version=1)
    with transaction(track):
        existing = configs(track).get(cid)
        if existing == d: return d
        track.execute('INSERT INTO card_setting(card_id,key,value,set_at) VALUES(?,?,?,?)', (cid, KEY, canonical_json(d), now))
        # Saving sets a baseline. Existing out-of-range values do not send retrospective notices.
        evaluate_all(track, ctx, now, only=cid, prime=True)
    return d


def classify(d, o):
    if o is None: return 'UNKNOWN'
    if o.unit != d['unit']: return 'UNKNOWN'
    checks = [(side, custom_cards._cmp(o, op, Decimal(d[side]))) for side, op in [('upper', '>'), ('lower', '<')] if d[side] is not None]
    if not checks: return 'OFF'
    for side, result in checks:
        if result == 'MET': return side.upper()
    return 'UNKNOWN' if any(r == 'INDETERMINATE' for _, r in checks) else 'NORMAL'


def proposal(d, days, now, prev, prime):
    """Compute values only. SQL and dedup remain in evaluate_all's transaction."""
    tp = max(days) if days else now[:10]
    o = custom_cards._latest(days[tp]) if days else None
    status = classify(d, o)
    def_id = sha256_hex(canonical_json(d).encode())
    fingerprint = sha256_hex(canonical_json([def_id, o.ref if o else None, status]).encode())
    if prev and prev['fingerprint'] == fingerprint: return None
    baseline = prime or not prev or prev.get('def_id') != def_id
    last_zone = prev.get('zone', 'UNKNOWN') if prev else 'UNKNOWN'
    # An uncertain reading cannot clear a previous breach.
    zone = last_zone if status == 'UNKNOWN' and not baseline else status
    cursor = tp + '|' + (o.instant.isoformat() if o and o.instant else '')
    rolled_back = bool(prev and cursor < prev.get('cursor', ''))
    if rolled_back and not baseline: zone = last_zone
    hit = status in ('UPPER', 'LOWER') and d['notify_' + status.lower()]
    send = not baseline and not rolled_back and hit and status != last_zone
    record = dict(fingerprint=fingerprint, def_id=def_id, zone=zone, status=status, cursor=max(cursor, prev.get('cursor', '') if prev and not baseline else ''))
    result = dict(status=status, code=d['code'], unit=d['unit'], lower=d['lower'], upper=d['upper'],
                  value=custom_cards._shown(o) if o else None, tp=tp)
    return tp, o, status, def_id, send, record, result


def apply_proposal(track, ctx, cid, d, now, prepared):
    tp, o, status, def_id, send, record, result = prepared
    track.execute('INSERT OR IGNORE INTO card_def VALUES(?,?,?,?)', (def_id, cid, canonical_json(d), now))
    rid = track.execute("INSERT INTO run(card_def_id,trigger,started_at) VALUES(?,'AUTO_UPDATE',?)", (def_id, now)).lastrowid
    text = canonical_json(result)
    level = 'WATCH' if status in ('UPPER', 'LOWER') else 'UNDETERMINED' if status == 'UNKNOWN' else 'NONE'
    track.execute("INSERT INTO run_tp VALUES(?,?,'EVALUATED',?,?,?)", (rid, tp, level, text, sha256_hex(text.encode())))
    if o:
        track.execute("INSERT INTO run_input VALUES(?,?,?,?, 'TP')", (rid, tp, o.observation_id, o.revision))
    track.execute('INSERT INTO card_setting(card_id,key,value,set_at) VALUES(?,?,?,?)', (cid, STATE, canonical_json(record), now))
    if send:
        bound = d[status.lower()]
        phrase = '高于上限' if status == 'UPPER' else '低于下限'
        # Local banner contains details; existing Mac notifier applies its normal delivery policy.
        body = f"{d['label']} {phrase} {bound} {d['unit']}。这是你自己设的阈值，不是诊断。"
        channels = ['BANNER', 'MACOS'] if d['mac'] else ['BANNER']
        track.execute("INSERT OR IGNORE INTO alert_log VALUES(?,?,?,'WATCH',?,?,?,?,?)",
                      (f'{ctx.instance_id}|{cid}|{rid}', cid, tp, rid, 'PTDS 阈值提醒', body, canonical_json(channels), now))
    return dict(card_id=cid, status=status, notified=bool(send), run_id=rid)


def evaluate_all(track, ctx, now, only=None, prime=False, *, groups=None):
    with (nullcontext() if track.in_transaction else transaction(track)):
        conf = configs(track)
        if not conf: return []
        groups = groups if groups is not None else custom_cards.by_code(track, ctx)
        states = {}
        for cid, value in track.execute('SELECT card_id,value FROM card_setting WHERE key=? ORDER BY id', (STATE,)):
            states[cid] = json.loads(value)
        results = []
        for cid, d in conf.items():
            if only and cid != only: continue
            days = groups.get(d['code'], {})
            from compute_snapshot import capture
            prepared = proposal(*capture(d, days, now, states.get(cid), prime))
            if prepared is None: continue
            results.append(apply_proposal(track, ctx, cid, d, now, prepared))
        return results


def alerts(track):
    out = []
    for key, cid, tp, level, title, body, at in track.execute("SELECT dedupe_key,card_id,tp_date,level,title,body,created_at FROM alert_log WHERE card_id LIKE 'threshold-%'"):
        out.append(dict(dedupe_key=key, card_id=cid, tp=tp, level=level, title=title, body=body, created_at=at,
                        acked=track.execute('SELECT 1 FROM alert_ack WHERE dedupe_key=?',(key,)).fetchone() is not None,
                        deliveries=[dict(channel=c,outcome=o) for c,o in track.execute('SELECT channel,outcome FROM alert_delivery WHERE dedupe_key=?',(key,))]))
    return out


def apply_prepared_all(track, ctx, now, entries, guard):
    with (nullcontext() if track.in_transaction else transaction(track)):
        guard.before(track)
        results = []
        for cid, d, planned in entries:
            value = planned.unwrap()
            if value is not None:
                results.append(apply_proposal(track, ctx, cid, d, now, value))
        guard.advance(track)
        return results
