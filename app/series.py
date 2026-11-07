"""明细库（R20，产品负责人 2026-10-14 06:04Z 选“明细另存 + 日汇总”）。

心率、步数、活动能量、连续血糖、睡眠分段这类高频数据，一条条存进正式库会把星轨拖慢（6 万条时每次快照约 8 秒），
所以原始明细存在这里（<实例>/startorch/series.db，独立 SQLite，只增不改），正式库每天只存一条汇总。
- 每条明细记着来自哪份文件（文件指纹）和文件里的位置，汇总可以一路追回原文。
- 同一条明细（同一类、同一开始和结束时间、同一来源、同一数值）再导入一次不会重复。同一时刻同一来源有几个不同的数
  （有的戒指、手表一个时间点会写好几条）都保留，不互相覆盖。
- 一天有好几个来源时（比如手机和手表都记了步数），只用当天条数最多的那个来源，不叠加，免得重复计算。
- 汇总按实例时区分天；睡眠记在醒来那天（晚上 6 点以后结束的睡眠段算第二天）。
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

DDL = """
CREATE TABLE IF NOT EXISTS sample (
  series   TEXT NOT NULL,
  start    TEXT NOT NULL,
  end      TEXT NOT NULL,
  day      TEXT NOT NULL,
  value    TEXT NOT NULL,
  unit     TEXT NOT NULL,
  source   TEXT NOT NULL,
  file_sha TEXT NOT NULL,
  loc      TEXT NOT NULL,
  added_at TEXT NOT NULL,
  PRIMARY KEY (series, start, end, source, value)
);
CREATE INDEX IF NOT EXISTS sample_day ON sample (series, day);
CREATE TRIGGER IF NOT EXISTS sample_no_update BEFORE UPDATE ON sample BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS sample_no_delete BEFORE DELETE ON sample BEGIN SELECT RAISE(ABORT, 'append-only'); END;
"""

# 明细类 → 怎么汇总、保留几位小数、汇总写成哪些代码、来源类别
SERIES = {
    "AH_HR": ("minmaxavg", 1, ("AH_HR_DAY_MIN", "AH_HR_DAY_AVG", "AH_HR_DAY_MAX"), "APPLE_HEALTH"),
    "AH_GLUCOSE": ("minmaxavg", 2, ("AH_GLUCOSE_DAY_MIN", "AH_GLUCOSE_DAY_AVG", "AH_GLUCOSE_DAY_MAX"), "APPLE_HEALTH"),
    "AH_STEPS_DAY": ("sum", 0, ("AH_STEPS_DAY",), "APPLE_HEALTH"),
    "AH_ACTIVE_ENERGY_DAY": ("sum", 1, ("AH_ACTIVE_ENERGY_DAY",), "APPLE_HEALTH"),
    "AH_SLEEP_DAY": ("sleep", 0, ("AH_SLEEP_DAY",), "APPLE_HEALTH"),
    "WITHINGS_HR": ("minmaxavg", 1, ("WITHINGS_HR_DAY_MIN", "WITHINGS_HR_DAY_AVG", "WITHINGS_HR_DAY_MAX"), "DEVICE_WITHINGS"),
    "WITHINGS_GLUCOSE": ("minmaxavg", 2, ("WITHINGS_GLUCOSE_DAY_MIN", "WITHINGS_GLUCOSE_DAY_AVG", "WITHINGS_GLUCOSE_DAY_MAX"),
                         "DEVICE_WITHINGS"),
    "CGM_GLUCOSE": ("minmaxavg", 2, ("CGM_GLUCOSE_DAY_MIN", "CGM_GLUCOSE_DAY_AVG", "CGM_GLUCOSE_DAY_MAX"), "DEVICE_CGM"),
}
SLEEP_DAY_SHIFT = timedelta(hours=6)


def path_of(root: Path) -> Path:
    return root / "startorch" / "series.db"


def open_series(root: Path) -> sqlite3.Connection:
    p = path_of(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p, isolation_level=None, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(DDL)
    return conn


def day_of(series: str, start: str, end: str, tz: str) -> str:
    z = ZoneInfo(tz)
    if SERIES[series][0] == "sleep":
        return (datetime.fromisoformat(end).astimezone(z) + SLEEP_DAY_SHIFT).date().isoformat()
    return datetime.fromisoformat(start).astimezone(z).date().isoformat()


def add(conn, series: str, rows, file_sha: str, tz: str, now: str) -> dict:
    """rows: [开始, 结束, 数值, 单位, 来源, 位置]。返回新存的、已经有的条数，以及涉及的日期。"""
    out = {"added": 0, "same": 0, "days": set()}
    conn.execute("BEGIN IMMEDIATE")
    try:
        for start, end, value, unit, source, loc in rows:
            day = day_of(series, start, end, tz)
            out["days"].add(day)
            cur = conn.execute("INSERT OR IGNORE INTO sample VALUES (?,?,?,?,?,?,?,?,?,?)",
                               (series, start, end, day, value, unit, source, file_sha, str(loc), now))
            out["added" if cur.rowcount else "same"] += 1
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return out


def _q(d: Decimal, digits: int) -> Decimal:
    return d.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_EVEN)


def _plain(d: Decimal) -> str:
    s = format(d, "f")
    return s if "." not in s else s.rstrip("0").rstrip(".") or "0"


def _union_minutes(spans: list) -> Decimal:
    total, cur_s, cur_e = 0.0, None, None
    for s, e in sorted(spans):
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += (cur_e - cur_s).total_seconds()
            cur_s, cur_e = s, e
        elif e > cur_e:
            cur_e = e
    if cur_e is not None:
        total += (cur_e - cur_s).total_seconds()
    return Decimal(round(total / 60))


def summarize(conn, series: str, days) -> list:
    """每天一条（或最低 / 平均 / 最高三条）汇总：[{code, day, value, unit, source, n, other_sources}]。"""
    op, digits, codes, _ = SERIES[series]
    out = []
    for day in sorted(days):
        rows = conn.execute("SELECT start, end, value, unit, source FROM sample WHERE series=? AND day=?",
                            (series, day)).fetchall()
        if not rows:
            continue
        by_src = {}
        for r in rows:
            by_src.setdefault(r[4], []).append(r)
        src = sorted(by_src, key=lambda s: (-len(by_src[s]), s))[0]
        pick = by_src[src]
        units = {}
        for r in pick:
            units[r[3]] = units.get(r[3], 0) + 1
        unit = sorted(units, key=lambda u: (-units[u], u))[0]
        pick = [r for r in pick if r[3] == unit]  # 同一来源同一天单位不一致（极少见）：只用多数单位的那些
        base = {"day": day, "unit": unit, "source": src, "n": len(pick), "other_sources": sorted(s for s in by_src if s != src)}
        if op == "minmaxavg":
            vals = [Decimal(r[2]) for r in pick]
            lo, hi = min(vals), max(vals)
            avg = _q(sum(vals) / len(vals), digits)
            out += [dict(base, code=codes[0], value=_plain(lo)), dict(base, code=codes[1], value=_plain(avg)),
                    dict(base, code=codes[2], value=_plain(hi))]
        elif op == "sum":
            out.append(dict(base, code=codes[0], value=_plain(_q(sum(Decimal(r[2]) for r in pick), digits))))
        else:  # sleep：睡着的分段取并集（重叠的不重复算），折成分钟
            spans = [(datetime.fromisoformat(r[0]), datetime.fromisoformat(r[1])) for r in pick]
            out.append(dict(base, code=codes[0], value=_plain(_union_minutes(spans)), unit="min"))
    return out


def stats(conn) -> dict:
    return {s: n for s, n in conn.execute("SELECT series, count(*) FROM sample GROUP BY series")}
