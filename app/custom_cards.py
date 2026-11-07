"""星轨 · 自定义状态卡（早期测试；FR-S-015～020，状态工程"自定义规则"模板）。

我自己挑一个指标、定一条规则：高于 / 低于某个值，或比上一个时点升高 / 下降超过百分之几；星轨按时点计算。
- 卡的定义写进星轨 card_def（内容指纹就是定义编号），当前用哪一版记在 card_setting，只追加；
  改规则 = 新定义、按新定义重算，旧定义下的结果都还在；停用也只追加一条记录；
- 计算、用了哪条数据（哪一版）、等级变化、提醒和投递，都写在星轨原有的表里（run / run_tp / run_input / alert_*），
  和 sJIA 关注卡同一套账本，证据图谱能追；
- 规则是我自己定的，不是医学规则；提醒文字不出现诊断字样，结尾固定写"这是你自己设的规则，不是诊断。"。
"""
from __future__ import annotations

import compute_snapshot
from contextlib import nullcontext

import json
import uuid
from datetime import timezone
from decimal import Decimal, InvalidOperation

from cards import LEVEL_RANK, _obs, latest_results
from h1_common import canonical_bytes, canonical_json, sha256_hex, strict_loads
from rules import BANNED_IN_ALERT
from sqlite_util import transaction

PREFIX = "custom-"
ENGINE = "custom/0.1"
METHODS = {"ABOVE": "高于", "BELOW": "低于", "RISE": "比上一个时点升高超过", "FALL": "比上一个时点下降超过"}
LEVELS = {"WATCH": "观察", "ALERT": "关注"}
LEVEL_ZH = {"ALERT": "关注", "WATCH": "观察", "UNDETERMINED": "无法判定", "NONE": "无"}
OUTCOME_ZH = {"MET": "达到", "NOT_MET": "没达到", "INDETERMINATE": "无法判定"}
REASON_ZH = {"COMPARATOR": "读数带 > 或 <，判断不了", "NO_BASELINE": "之前没有可比的读数", "ZERO_BASELINE": "上一次的读数是 0，算不了变化"}
TITLE = "PTDS 状态提醒"
# 卡名、说明里也不许出现病名（提醒标题和正文会带上卡名，SEM-36）
NAME_BANNED = ("综合征", "MAS", "HLH", "SJIA", "关节炎", "噬血", "巨噬细胞活化", "白血病", "肿瘤", "癌", "感染", "败血")
SUFFIX = "这是你自己设的规则，不是诊断。"
FAMILY_ZH = {"LAB": "化验", "VITAL": "体征", "DEVICE_GARMIN": "Garmin", "DEVICE_OURA": "Oura", "PHONE_HEALTH": "苹果健康",
             "DEVICE_SOMALOOP": "Somaloop 手环", "DEVICE_QKEER": "Qkeer",
             "DEVICE_WITHINGS": "Withings", "DEVICE_CGM": "连续血糖"}
UNIT_ZH = {"score": "分", "steps": "步", "min": "分钟", "bpm": "次/分"}


class CustomError(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(code)
        self.code, self.detail = code, detail


def cond_zh(d: dict) -> str:
    pct = d["method"] in ("RISE", "FALL")
    unit = "%" if pct else (" " + UNIT_ZH.get(d.get("unit"), d.get("unit") or "")).rstrip()
    return f"{d['label_zh']}{METHODS[d['method']]} {d['threshold']}{unit}"


def rule_zh(d: dict) -> str:
    return f"{cond_zh(d)}，等级为{LEVELS[d['level']]}"


# ----------------------------------------------------------------------------- definitions

def _definition(registry, ctx, body: dict, card_id: str) -> dict:
    name = str(body.get("name") or "").strip()
    if not 1 <= len(name) <= 24:
        raise CustomError("NAME_INVALID", "卡片名 1～24 个字")
    note = str(body.get("note") or "").strip()[:120]
    if any(w in (name + note).upper() for w in BANNED_IN_ALERT + NAME_BANNED):
        raise CustomError("NAME_UNSAFE", "卡片名和说明里不能有诊断字样")
    code = body.get("code")
    cdef = registry.current.codes.get(code)
    if cdef is None or cdef.value_type != "DECIMAL":
        raise CustomError("CODE_INVALID", "只能选有数值的指标")
    method = body.get("method")
    if method not in METHODS:
        raise CustomError("METHOD_INVALID", "")
    try:
        thr = Decimal(str(body.get("threshold") or "").strip())
    except InvalidOperation:
        raise CustomError("THRESHOLD_INVALID", "阈值要填数字") from None
    if not thr.is_finite() or (method in ("RISE", "FALL") and not Decimal(0) < thr <= Decimal(1000)):
        raise CustomError("THRESHOLD_INVALID", "变化百分比要大于 0、不超过 1000")
    level = body.get("level") or "WATCH"
    if level not in LEVELS:
        raise CustomError("LEVEL_INVALID", "")
    return {"kind": "CUSTOM", "engine_version": ENGINE, "card_id": card_id, "name": name, "note": note,
            "code": code, "label_zh": cdef.label_zh, "unit": cdef.unit_canonical, "method": method,
            "threshold": format(thr.normalize(), "f"), "level": level, "notify_self": bool(body.get("notify_self")),
            "instance_tz": ctx.tz}


def save(track, registry, ctx, body: dict, *, at: str) -> dict:
    """新建（不带 card_id）或改规则（带 card_id）。返回卡的当前定义。"""
    card_id = body.get("card_id") or PREFIX + uuid.uuid4().hex[:8]
    if not card_id.startswith(PREFIX):
        raise CustomError("CARD_UNKNOWN", card_id)
    if body.get("card_id") and card_id not in {c["card_id"] for c in cards(track, include_off=True)}:
        raise CustomError("CARD_UNKNOWN", card_id)
    d = _definition(registry, ctx, body, card_id)
    def_id = sha256_hex(canonical_bytes(d))
    with transaction(track):
        track.execute("INSERT OR IGNORE INTO card_def (card_def_id, card_id, definition, registered_at) VALUES (?, ?, ?, ?)",
                      (def_id, card_id, canonical_json(d), at))
        track.execute("INSERT INTO card_setting (card_id, key, value, set_at) VALUES (?, 'custom_def', ?, ?)",
                      (card_id, def_id, at))
        track.execute("INSERT INTO card_setting (card_id, key, value, set_at) VALUES (?, 'custom_status', 'ACTIVE', ?)",
                      (card_id, at))
    return {"card_id": card_id, "card_def_id": def_id, "definition": d}


def stop(track, card_id: str, *, at: str) -> None:
    if card_id not in {c["card_id"] for c in cards(track)}:
        raise CustomError("CARD_UNKNOWN", card_id)
    with transaction(track):
        track.execute("INSERT INTO card_setting (card_id, key, value, set_at) VALUES (?, 'custom_status', 'STOPPED', ?)",
                      (card_id, at))


def cards(track, include_off: bool = False) -> list:
    out = {}
    for cid, key, val, at in track.execute("SELECT card_id, key, value, set_at FROM card_setting "
                                           "WHERE substr(card_id, 1, 7) = ? ORDER BY id", (PREFIX,)):
        c = out.setdefault(cid, {"card_id": cid, "created_at": at, "versions": [], "active": True})
        if key == "custom_def":
            c["versions"].append({"card_def_id": val, "set_at": at})
        elif key == "custom_status":
            c["active"] = val == "ACTIVE"
            c["status_at"] = at
    defs = {cid: json.loads(d) for cid, d in track.execute(
        "SELECT card_def_id, definition FROM card_def WHERE substr(card_id, 1, 7) = ?", (PREFIX,))}
    res = []
    for c in out.values():
        if not c["versions"] or not (c["active"] or include_off):
            continue
        c["card_def_id"] = c["versions"][-1]["card_def_id"]
        c["definition"] = defs[c["card_def_id"]]
        for v in c["versions"]:
            v["rule_zh"] = rule_zh(defs[v["card_def_id"]])
        res.append(c)
    return res


# ----------------------------------------------------------------------------- evaluation

def by_code(track, ctx, *, read=None) -> dict:
    """星轨里每条当前有效观测，按代码 → 时点（实例本地日期）分组；时间未知的不进时点。"""
    if read is not None:
        out = {}
        for o in read.observations:
            if o.kind == "DECIMAL" and o.day is not None:
                out.setdefault(o.code, {}).setdefault(o.day, []).append(o)
        return out
    newest = {}
    for oid, rev, payload in track.execute("SELECT observation_id, revision, payload FROM h1_inbox"):
        if oid not in newest or rev > newest[oid][0]:
            newest[oid] = (rev, payload)
    out = {}
    for oid in sorted(newest):
        p = strict_loads(newest[oid][1])
        if p["status"] != "ACTIVE" or p["value_type"] != "DECIMAL":
            continue
        o = _obs(p, ctx.tz)
        if o.day is not None:
            out.setdefault(o.code, {}).setdefault(o.day, []).append(o)
    return out


def _cmp(o, op: str, thr: Decimal) -> str:
    """单条读数是否 高于(op='>') / 低于(op='<') 阈值：MET / NOT_MET / INDETERMINATE（带比较符时尽量判断）。"""
    v, c = o.value, o.comparator
    if op == ">":
        if c is None:
            return "MET" if v > thr else "NOT_MET"
        if c in (">", ">="):
            return "MET" if (v >= thr if c == ">" else v > thr) else "INDETERMINATE"
        return "NOT_MET" if v <= thr else "INDETERMINATE"
    if c is None:
        return "MET" if v < thr else "NOT_MET"
    if c in ("<", "<="):
        return "MET" if (v <= thr if c == "<" else v < thr) else "INDETERMINATE"
    return "NOT_MET" if v >= thr else "INDETERMINATE"


def _latest(obs: list):
    return max(obs, key=lambda o: (o.instant.astimezone(timezone.utc).isoformat() if o.instant else "", o.observation_id))


def _shown(o) -> dict:
    return {"value": format(o.value, "f"), "comparator": o.comparator, "unit": o.unit, "ref": o.ref}


def evaluate(d: dict, tp: str, days: dict) -> tuple:
    """一个时点 → (等级, 结果, 用到的输入)。高于 / 低于：当天任一读数达到即达到；变化：当天最后一条比上一个时点最后一条。"""
    thr, obs = Decimal(d["threshold"]), days[tp]
    inputs = {(o.observation_id, o.revision, "TP") for o in obs}
    res = {"tp": tp, "engine_version": ENGINE, "method": d["method"], "threshold": d["threshold"], "unit": d["unit"],
           "readings": len(obs), "base": None, "change_pct": None, "reason": None}
    if d["method"] in ("ABOVE", "BELOW"):
        op = ">" if d["method"] == "ABOVE" else "<"
        outs = [(_cmp(o, op, thr), o) for o in obs]
        hit = [o for r, o in outs if r == "MET"]
        unk = [o for r, o in outs if r == "INDETERMINATE"]
        pick = (max if op == ">" else min)(hit or unk or obs, key=lambda o: o.value)
        outcome = "MET" if hit else ("INDETERMINATE" if unk else "NOT_MET")
        res["value"] = _shown(pick)
        if outcome == "INDETERMINATE":
            res["reason"] = "COMPARATOR"
    else:
        cur = _latest(obs)
        res["value"] = _shown(cur)
        before = sorted(day for day in days if day < tp)
        if not before:
            outcome, res["reason"] = "INDETERMINATE", "NO_BASELINE"
        else:
            bobs = days[before[-1]]
            inputs |= {(o.observation_id, o.revision, "HISTORY") for o in bobs}
            base = _latest(bobs)
            res["base"] = dict(_shown(base), tp=before[-1])
            if cur.comparator or base.comparator:
                outcome, res["reason"] = "INDETERMINATE", "COMPARATOR"
            elif base.value == 0:
                outcome, res["reason"] = "INDETERMINATE", "ZERO_BASELINE"
            else:
                pct = (cur.value - base.value) / abs(base.value) * 100
                res["change_pct"] = format(pct.quantize(Decimal("0.1")), "f")
                hit = pct > thr if d["method"] == "RISE" else -pct > thr
                outcome = "MET" if hit else "NOT_MET"
    level = d["level"] if outcome == "MET" else ("UNDETERMINED" if outcome == "INDETERMINATE" else "NONE")
    res.update(outcome=outcome, level=level, drivers=[])
    return level, res, frozenset(inputs)


def _status(track, card: dict, days: dict) -> tuple:
    latest = latest_results(track, card["card_def_id"])
    return status_values(latest, card, days)


def status_values(latest, card, days):
    status = {}
    for tp in days:
        item = latest.get(tp)
        if item is None:
            status[tp] = "NEW"
        elif item["status"] == "VANISHED" or item["inputs"] != evaluate(card["definition"], tp, days)[2]:
            status[tp] = "STALE"
        else:
            status[tp] = "FRESH"
    for tp, item in latest.items():
        if tp not in days and item["status"] == "EVALUATED":
            status[tp] = "STALE"
    return status, latest


def message(d: dict, tp: str, level: str) -> tuple:
    title = f"{TITLE} · {d['name']}"
    body = f"{tp}「{d['name']}」：{cond_zh(d)}，等级{LEVEL_ZH[level]}。" + SUFFIX
    if any(w in title + body[:-len(SUFFIX)] for w in BANNED_IN_ALERT):
        raise CustomError("ALERT_COPY_UNSAFE", "")
    return title, body


def apply_point(track, run_id, tp, level, res, inputs, status):
    text = canonical_json(res)
    track.execute("INSERT INTO run_tp (run_id, tp_date, status, level, result, result_sha256) VALUES (?, ?, ?, ?, ?, ?)",
                  (run_id, tp, status, level, text, sha256_hex(text.encode())))
    track.executemany("INSERT INTO run_input (run_id, tp_date, observation_id, revision, role) VALUES (?, ?, ?, ?, ?)",
                      [(run_id, tp, oid, rev, role) for oid, rev, role in sorted(inputs)])


def _run(track, ctx, card: dict, days: dict, tps: list, trigger: str, now: str, channels: list, *, points=None) -> tuple:
    d = card["definition"]
    with (nullcontext() if track.in_transaction else transaction(track)):
        track.execute("INSERT OR IGNORE INTO card_def (card_def_id, card_id, definition, registered_at) VALUES (?, ?, ?, ?)",
                      (card["card_def_id"], card["card_id"], canonical_json(d), now))
        run_id = track.execute("INSERT INTO run (card_def_id, trigger, started_at) VALUES (?, ?, ?)",
                               (card["card_def_id"], trigger, now)).lastrowid
        for tp in sorted(tps):
            if points is None:
                prepared = compute_snapshot.capture(d, tp, days)
                level, res, inputs, status = compute_snapshot.custom_point(*prepared, evaluate)
            else:
                level, res, inputs, status = points[tp].unwrap()
            apply_point(track, run_id, tp, level, res, inputs, status)
        alert = _alert(track, ctx, card, days, run_id, now, channels)
    return run_id, alert


def _alert(track, ctx, card: dict, days: dict, run_id: int, now: str, channels: list):
    """同 sJIA 关注卡：只看最新一个时点的等级；比上次记下的等级高才提醒，同一时点同一等级只提醒一次。"""
    latest = latest_results(track, card["card_def_id"])
    evaluated = [tp for tp, it in latest.items() if it["status"] == "EVALUATED" and tp in days]
    if not evaluated:
        return None
    tp = max(evaluated)
    level = latest[tp]["level"]
    prev = track.execute("SELECT tp_date, level FROM alert_state WHERE card_id = ? ORDER BY id DESC LIMIT 1",
                         (card["card_id"],)).fetchone()
    if prev is not None and tuple(prev) == (tp, level):
        return None
    track.execute("INSERT INTO alert_state (card_id, tp_date, level, run_id, recorded_at) VALUES (?, ?, ?, ?, ?)",
                  (card["card_id"], tp, level, run_id, now))
    if LEVEL_RANK[level] <= (LEVEL_RANK[prev[1]] if prev else 0):
        return None
    key = f"{ctx.instance_id}|{card['card_id']}|{tp}|{level}"
    title, body = message(card["definition"], tp, level)
    n = track.execute("INSERT OR IGNORE INTO alert_log (dedupe_key, card_id, tp_date, level, run_id, title, body, channels, "
                      "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (key, card["card_id"], tp, level, run_id, title, body, canonical_json(sorted(set(channels))), now)).rowcount
    return {"dedupe_key": key, "tp": tp, "level": level, "title": title, "body": body} if n == 1 else None


def channels_for(card: dict, notifiers) -> list:
    every = [n.channel for n in notifiers]
    return every if card["definition"].get("notify_self") else [c for c in every if c == "BANNER"]


def sync_all(track, ctx, *, now: str, notifiers, only: str | None = None, trigger: str | None = None,
             groups=None) -> list:
    """每张启用的自定义卡：新时点、数据有变化的时点（更正、撤回、补了更早的读数）按当前定义重算。"""
    out = []
    for card in cards(track):
        if only and card["card_id"] != only:
            continue
        groups = groups if groups is not None else by_code(track, ctx)
        days = groups.get(card["definition"]["code"], {})
        with transaction(track):
            status, _ = _status(track, card, days)
            targets = sorted(tp for tp, s in status.items() if s in ("NEW", "STALE"))
            if not targets:
                continue
            trig = trigger or ("AUTO_UPDATE" if any(status[t] == "STALE" for t in targets) else "SYNC")
            run_id, alert = _run(track, ctx, card, days, targets, trig, now, channels_for(card, notifiers))
        out.append({"card_id": card["card_id"], "run_id": run_id, "evaluated": targets, "alert": alert})
    return out


# ----------------------------------------------------------------------------- read model (UI)

def available(track, ctx, registry) -> list:
    """可选的指标：星轨里已经有数值读数的代码。"""
    out = []
    for code, days in by_code(track, ctx).items():
        cdef = registry.current.codes.get(code)
        if cdef is None:
            continue
        last_day = max(days)
        o = _latest(days[last_day])
        out.append({"code": code, "label_zh": cdef.label_zh, "family": cdef.family,
                    "family_zh": FAMILY_ZH.get(cdef.family, cdef.family), "unit": cdef.unit_canonical,
                    "unit_zh": UNIT_ZH.get(cdef.unit_canonical, cdef.unit_canonical or ""), "days": len(days),
                    "last_tp": last_day, "last": (o.comparator or "") + format(o.value, "f")})
    order = list(FAMILY_ZH)
    out.sort(key=lambda x: (order.index(x["family"]) if x["family"] in order else 99, x["label_zh"]))
    return out


def state(track, ctx, include_off: bool = False, groups: dict | None = None) -> list:
    groups = groups if groups is not None else by_code(track, ctx)
    out = []
    for card in cards(track, include_off=include_off):
        d = card["definition"]
        days = groups.get(d["code"], {})
        status, latest = _status(track, card, days)
        tps = []
        for tp in sorted(set(days) | set(latest), reverse=True):
            it = latest.get(tp)
            res = strict_loads(it["result"]) if it and it["status"] == "EVALUATED" else None
            tps.append({"tp": tp, "status": status.get(tp, "VANISHED"), "run_id": it["run_id"] if it else None,
                        "level": it["level"] if it else None, "level_zh": LEVEL_ZH.get(it["level"]) if it else None,
                        "result": res, "outcome_zh": OUTCOME_ZH.get((res or {}).get("outcome")),
                        "reason_zh": REASON_ZH.get((res or {}).get("reason"))})
        current = next((t for t in tps if t["tp"] in days and t["result"]), None)
        alerts = []
        for key, tp, lv, title, body, at in track.execute(
                "SELECT dedupe_key, tp_date, level, title, body, created_at FROM alert_log WHERE card_id = ? ORDER BY created_at",
                (card["card_id"],)):
            acked = track.execute("SELECT 1 FROM alert_ack WHERE dedupe_key = ?", (key,)).fetchone() is not None
            dl = [dict(zip(("channel", "outcome"), r)) for r in track.execute(
                "SELECT channel, outcome FROM alert_delivery WHERE dedupe_key = ? ORDER BY id", (key,))]
            alerts.append({"dedupe_key": key, "tp": tp, "level": lv, "level_zh": LEVEL_ZH.get(lv, lv), "title": title,
                           "body": body, "created_at": at, "acked": acked, "deliveries": dl})
        runs = [dict(zip(("run_id", "trigger", "started_at", "card_def_id"), r)) for r in track.execute(
            "SELECT r.run_id, r.trigger, r.started_at, r.card_def_id FROM run r JOIN card_def c USING (card_def_id) "
            "WHERE c.card_id = ? ORDER BY r.run_id", (card["card_id"],))]
        out.append({"card_id": card["card_id"], "name": d["name"], "note": d["note"], "active": card["active"],
                    "definition": d, "rule_zh": rule_zh(d), "card_def_id": card["card_def_id"],
                    "created_at": card["created_at"], "versions": card["versions"],
                    "unit_zh": UNIT_ZH.get(d["unit"], d["unit"] or ""),
                    "current": None if current is None else {"tp": current["tp"], "level": current["level"],
                                                             "level_zh": current["level_zh"],
                                                             "stale": current["status"] == "STALE"},
                    "timepoints": tps, "alerts": alerts, "new_alert": any(not a["acked"] for a in alerts),
                    "runs": runs[-20:], "series": [{"tp": tp, "v": format(_latest(days[tp]).value, "f")}
                                                    for tp in sorted(days)][-60:],
                    "note_zh": "规则是你自己定的，不是医学规则；结果只用于测试，不是结论。"})
    return out


def apply_prepared_card(track, ctx, card, days, planned, now, notifiers, guard):
    with transaction(track):
        guard.before(track)
        status, targets, points = planned.unwrap()
        if not targets:
            guard.advance(track)
            return None
        trigger = 'AUTO_UPDATE' if any(status[t] == 'STALE' for t in targets) else 'SYNC'
        run_id, alert = _run(track, ctx, card, days, targets, trigger, now,
                            channels_for(card, notifiers), points=points)
        guard.advance(track)
    return {'card_id': card['card_id'], 'run_id': run_id, 'evaluated': targets, 'alert': alert}
