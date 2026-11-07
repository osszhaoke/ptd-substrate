"""星轨 · 通用时点状态（PTDS-local，10-17 演示版）。

对字典里任意代码给出：最近值、观测时间、来源、是否最新、历史序列。只描述，不定级、不提醒（PRD UXD-05）。
数据只来自星轨自己的 h1_inbox（H1 文件交接导入的副本），不读星炬的库。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from h1_common import DictionaryRegistry, InstanceContext, local_day, parse_instant, strict_loads
from time_freshness import PresentationClock

# 读数"是否最新"的时效（N7）：按代码族给默认值，演示版写在这里，赛后进配置
FRESH_WINDOW = {
    "DEVICE_GARMIN": timedelta(hours=30),
    "DEVICE_SOMALOOP": timedelta(seconds=60),
    "DEVICE_QKEER": timedelta(seconds=60),
    "DEVICE_OURA": timedelta(hours=30),
    "PHONE_HEALTH": timedelta(hours=26),
}
SERIES_MAX = 120


def _active_payloads(conn) -> list:
    newest = {}
    for oid, rev, payload in conn.execute("SELECT observation_id, revision, payload FROM h1_inbox"):
        if oid not in newest or rev > newest[oid][0]:
            newest[oid] = (rev, payload)
    out = []
    for oid in newest:
        p = strict_loads(newest[oid][1])
        if p["status"] == "ACTIVE":
            out.append(p)
    return out


def _when(p: dict, tz: str):
    # Compatibility entry used by baseline_view and device_watch_read.
    t = p["temporal"]
    if t["role"] == "INSTANT":
        instant = parse_instant(t["observed_at"])
        return instant, local_day(instant, tz).isoformat()
    if t["role"] == "DAY":
        return None, t["observed_date"]
    return None, None


def _when_in_zone(p: dict, zone):
    t = p["temporal"]
    if t["role"] == "INSTANT":
        instant = parse_instant(t["observed_at"])
        return instant, instant.astimezone(zone).date().isoformat()
    if t["role"] == "DAY":
        return None, t["observed_date"]
    return None, None


def vitals_state(conn, ctx: InstanceContext, registry: DictionaryRegistry, *, now: datetime | None = None,
                 families=None, read=None) -> dict:
    now = now or datetime.now(timezone.utc)
    clock = PresentationClock(now, ctx.tz)
    codes = registry.current.codes
    payloads = read.payloads.values() if read is not None else _active_payloads(conn)
    return vitals_values(payloads, codes, clock, now, families)


def vitals_values(payloads, codes, clock, now, families=None):
    """Value selection only; the caller owns storage and the evaluation clock."""
    today = clock.today.isoformat()
    by_code = {}
    for p in payloads:
        cdef = codes.get(p["code"])
        if cdef is None or (families is not None and cdef.family not in families):
            continue
        instant, day = _when_in_zone(p, clock.zone)
        sort_key = instant.astimezone(timezone.utc).isoformat() if instant else (day or "")
        by_code.setdefault(p["code"], []).append((sort_key, instant, day, p))
    items = []
    for code, rows in by_code.items():
        rows.sort(key=lambda r: (r[0], r[3]["observation_id"]))
        cdef = codes[code]
        current = next((r for r in reversed(rows)
                        if (r[1] <= now if r[1] is not None else r[2] is None or r[2] <= today)), None)
        if current is None:
            continue
        _, instant, day, p = current
        window = FRESH_WINDOW.get(cdef.family)
        is_fresh = clock.fresh(window, instant=instant, day=day)
        items.append({
            "code": code, "label_zh": cdef.label_zh, "family": cdef.family,
            "value": p["value_canonical"], "unit": p["unit_canonical"], "value_raw": p["value_raw"],
            "unit_raw": p["unit_raw"], "comparator": p["comparator"],
            "observed_at": instant.isoformat() if instant else None, "observed_date": day,
            "source_kind": p["source_kind"], "source_ref": p["source_ref"], "trust_tier": p["trust_tier"],
            "nature": "SYNTHETIC" if p["source_kind"] == "SYNTHETIC" else "REAL",
            "observation_id": p["observation_id"], "revision": p["revision"], "fresh": is_fresh,
            "count": len(rows),
            "series": [{"t": r[1].isoformat() if r[1] else r[2], "v": r[3]["value_canonical"]}
                       for r in rows[-SERIES_MAX:]],
        })
    items.sort(key=lambda i: (i["family"], i["code"]))
    return {"computed_at": now.isoformat(timespec="seconds"), "items": items}
