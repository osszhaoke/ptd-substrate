"""体验腕带（Somaloop）的三张卡（产品负责人 2026-10-14 10:51 确认示意稿 v2）：只在 sJIA 演示里出现，只读星轨里已有的正式读数。

- 现场体征：心率、血氧、皮肤温度、心率变异性的最近读数，标“是不是刚测的”。只描述，不判断。（LIVE.SOMALOOP-SPOT@0.1）
- 血氧低值提示：本位体验者的血氧读数里，低于 94% 的条数。研究演示，未经临床验证；只提示，不发提醒、不进任何预警。（LIVE.SPO2-LOW@0.1）
- 结果写进星轨计算账本（card_def / run / run_tp / run_input，只追加，和引擎卡同一套），证据图谱能从结果追到每条读数。
  只有输入真的变了才记一次（打开页面不记）；一条输入都没有的卡不记。
- 夜间基线偏离：A03 / A04 / F01 的 0.2 版（Somaloop 输入），当晚值 − 前 28 晚（不含当晚）中位数，至少 14 晚。
  夜间 = 本地 0:00–6:00；一晚至少 3 条读数才算一晚。HRV、皮温取中位数，心率取最低值。皮温只作背景，不计入发热。
  Oura 用的 0.1 版不变。
"""
from __future__ import annotations

import statistics
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import rule_registry as RR
from cards import latest_results, take_snapshot
from h1_common import canonical_bytes, canonical_json, local_day, sha256_hex
from sqlite_util import transaction

from engines import _nofloat  # noqa: E402 — 账本 JSON 不许有浮点数，和引擎卡同一个办法

FRESH_S = 60
SPO2_LOW = 94.0
NIGHT_HOURS = (0, 6)
NIGHT_MIN_READINGS = 3
BASE_DAYS, BASE_MIN = 28, 14
SPOT = [("SOMALOOP_HR", "心率", "次/分"), ("SOMALOOP_SPO2", "血氧", "%"), ("SOMALOOP_SKIN_TEMP", "皮温", "°C"),
        ("SOMALOOP_HRV", "心率变异性", "ms")]
NIGHTLY = [("SLEEP.A03-HRV-DEV-SOMALOOP", "HRV", "SOMALOOP_HRV", "median", "ms"),
           ("SLEEP.A04-LOWHR-DEV-SOMALOOP", "最低心率", "SOMALOOP_HR", "min", "次/分"),
           ("RHYTHM.F01-TEMPDEV-SOMALOOP", "体温", "SOMALOOP_SKIN_TEMP", "median", "°C")]


def _num(o):
    try:
        return float(o.payload["value_canonical"])
    except (TypeError, ValueError, KeyError):
        return None


def _fmt(v: float, unit: str) -> str:
    return f"{v:.1f}" if unit == "°C" else str(int(round(v)))


def night_obs(obs: list, tz: str) -> dict:
    """{本地日期: [当晚 0:00–6:00 的读数]}，只留至少 NIGHT_MIN_READINGS 条的晚上。"""
    by = {}
    zone = ZoneInfo(tz)
    for o in obs:
        if o.instant is None or _num(o) is None:
            continue
        t = o.instant.astimezone(zone)
        if NIGHT_HOURS[0] <= t.hour < NIGHT_HOURS[1]:
            by.setdefault(t.date(), []).append(o)
    return {d: v for d, v in by.items() if len(v) >= NIGHT_MIN_READINGS}


def nights(obs: list, tz: str, how: str) -> dict:
    """{本地日期: 当晚值}：本地 0:00–6:00 的读数，至少 NIGHT_MIN_READINGS 条。"""
    agg = statistics.median if how == "median" else min
    return {d: agg([_num(o) for o in v]) for d, v in night_obs(obs, tz).items()}


def baseline(per_night: dict) -> dict:
    """最近一晚 − 前 28 晚（不含当晚）中位数；至少 14 晚。数据不够照实写几晚。"""
    if not per_night:
        return {"status": "insufficient", "have": 0, "need": BASE_MIN}
    last = max(per_night)
    base = [v for d, v in per_night.items() if last - timedelta(days=BASE_DAYS) <= d < last]
    if len(base) < BASE_MIN:
        return {"status": "insufficient", "have": len(base), "need": BASE_MIN, "night": last.isoformat()}
    return {"status": "computed", "have": len(base), "need": BASE_MIN, "night": last.isoformat(),
            "value": per_night[last], "delta": per_night[last] - statistics.median(base)}


def compute(track, ctx, *, since: float | None = None, now: datetime | None = None, read=None) -> tuple:
    """(界面要的三张卡, 账本条目 [(规则编号, 时点, 结果, 输入集合)])。since = 本位体验者开始的时间（秒）。"""
    now = now or datetime.now(timezone.utc)
    snap = take_snapshot(track, ctx, SimpleNamespace(codes=set(), labels={}), read=read)
    from compute_snapshot import capture
    return compute_values(*capture(snap.observations, ctx.tz, since, now))


def compute_values(observations, tz, since, now):
    """Value-only projection; preparation and ledger writes stay with their owners."""
    obs = {}
    for o in observations:
        if o.code.startswith("SOMALOOP_") and o.instant is not None:
            obs.setdefault(o.code, []).append(o)
    if not obs:
        return {}, []
    for v in obs.values():
        v.sort(key=lambda o: o.instant)
    day = lambda o: local_day(o.instant, tz).isoformat()  # noqa: E731
    tp = lambda os_: (frozenset((o.observation_id, o.revision, "TP") for o in os_))  # noqa: E731
    ledger = []
    spot, used = [], []
    for code, zh, unit in SPOT:
        o = (obs.get(code) or [None])[-1]
        if o is not None:
            used.append(o)
        spot.append({"label": zh, "unit": unit, "value": _fmt(_num(o), unit) if o else None,
                     "at": o.instant.isoformat() if o else None,
                     "fresh": bool(o and (now - o.instant).total_seconds() <= FRESH_S)})
    if used:
        last = max(used, key=lambda o: o.instant)
        ledger.append(("LIVE.SOMALOOP-SPOT", day(last),
                       {"status": "computed", "text": " · ".join(f"{x['label']} {x['value']} {x['unit']}" for x in spot if x["value"]),
                        "value": None, "unit": "", "items": [{k: x[k] for k in ("label", "value", "unit", "at")} for x in spot]},
                       tp(used)))
    sp_obs = [o for o in obs.get("SOMALOOP_SPO2", []) if (since is None or o.instant.timestamp() >= since) and _num(o) is not None]
    sp = [_num(o) for o in sp_obs]
    spo2 = {"n": len(sp), "low": sum(1 for v in sp if v < SPO2_LOW), "threshold": SPO2_LOW,
            "min": min(sp) if sp else None, "max": max(sp) if sp else None}
    if sp_obs:
        ledger.append(("LIVE.SPO2-LOW", day(sp_obs[-1]),
                       {"status": "computed", "value": spo2["low"], "unit": "条", "text": f"{spo2['low']} / {spo2['n']}",
                        "extra": spo2, "reason": "研究演示，未经临床验证"}, tp(sp_obs)))
    night = []
    for rule, zh, code, how, unit in NIGHTLY:
        per_obs = night_obs(obs.get(code, []), tz)
        r = baseline(nights(obs.get(code, []), tz, how))
        r.update(rule=rule, label=zh, unit=unit)
        if r["status"] == "computed":
            r["text"] = ("+" if r["delta"] > 0 else "") + _fmt(r["delta"], unit) + " " + unit
        night.append(r)
        if per_obs:
            last = max(per_obs)
            hist = [o for d, v in per_obs.items() if last - timedelta(days=BASE_DAYS) <= d < last for o in v]
            res = {"status": "computed" if r["status"] == "computed" else "insufficient_data",
                   "value": r.get("delta"), "unit": unit, "text": r.get("text"),
                   "reason": None if r["status"] == "computed" else f"数据还不够：{r['have']}/{r['need']} 晚"}
            inputs = tp(per_obs[last]) | frozenset((o.observation_id, o.revision, "HISTORY") for o in hist)
            ledger.append((rule, last.isoformat(), res, inputs))
    cards = {"spot": spot, "spo2_low": spo2, "night": night,
             "rules": {"spot": "LIVE.SOMALOOP-SPOT", "spo2_low": "LIVE.SPO2-LOW"}}
    return cards, ledger


def build(track, ctx, *, since: float | None = None, now: datetime | None = None, read=None) -> dict:
    return compute(track, ctx, since=since, now=now, read=read)[0]


ENGINE = "band/0.1"
TEMPLATE = "LIVE"


def _definition(rule_id: str) -> dict:
    return {"kind": "ENGINE_RULE", "engine_version": ENGINE, "template": TEMPLATE, "card_id": "engine-" + rule_id,
            "rule": RR.ref(rule_id), "fingerprint": RR.fingerprint(rule_id)}


def apply_entry(track, rule_id, tp_day, res, inputs, now, *, guard=None):
    d = _definition(rule_id)
    def_id = sha256_hex(canonical_bytes(d))
    with transaction(track):
        if guard is not None:
            guard.before(track)
        it = latest_results(track, def_id).get(tp_day)
        if it is not None and it["status"] == "EVALUATED" and it["inputs"] == inputs:
            if guard is not None:
                guard.advance(track)
            return None
        text = canonical_json(_nofloat(res))
        track.execute("INSERT OR IGNORE INTO card_def (card_def_id, card_id, definition, registered_at) VALUES (?, ?, ?, ?)",
                      (def_id, d["card_id"], canonical_json(d), now))
        run_id = track.execute("INSERT INTO run (card_def_id, trigger, started_at) VALUES (?, ?, ?)",
                               (def_id, "SYNC" if it is None else "AUTO_UPDATE", now)).lastrowid
        track.execute("INSERT INTO run_tp (run_id, tp_date, status, level, result, result_sha256) "
                      "VALUES (?, ?, 'EVALUATED', 'NONE', ?, ?)", (run_id, tp_day, text, sha256_hex(text.encode())))
        track.executemany("INSERT INTO run_input (run_id, tp_date, observation_id, revision, role) VALUES (?, ?, ?, ?, ?)",
                          [(run_id, tp_day, oid, rev, role) for oid, rev, role in sorted(inputs)])
        if guard is not None:
            guard.advance(track)
    return {"rule": rule_id, "tp": tp_day, "run_id": run_id}


def record(track, ctx, *, now: str, since: float | None = None, read=None) -> list:
    """把三张卡的结果写进星轨账本：每条规则每个时点，输入（观测编号@版本）和上次不一样才记一次。只追加。"""
    _, ledger = compute(track, ctx, since=since, read=read)
    out = []
    for rule_id, tp_day, res, inputs in ledger:
        item = apply_entry(track, rule_id, tp_day, res, inputs, now)
        if item is not None:
            out.append(item)
    return out
