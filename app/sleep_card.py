"""星轨 · 睡眠卡（早期测试；卡墙"睡眠"）：设备睡眠数据的长期观察。

- 只显示读数和变化（比上一晚、比之前 7 晚的平均），不打分、不定级、不提醒；
  睡眠评分、准备度评分是 Oura 自己给的分，原样显示并写明出处；
- 每个数都能追到是哪台设备、哪一晚（星轨收到的那条数据，可在星炬中打开）；
- 数据只来自星轨自己的 h1_inbox（H1 交接导入的副本）；与"我的体征"共用绑定：解绑的来源不进这张卡。
"""
from __future__ import annotations

from datetime import timezone
from decimal import Decimal

METRICS = ["OURA_TOTAL_SLEEP", "OURA_SLEEP_SCORE", "OURA_HRV", "OURA_LOWEST_HR", "OURA_RESTING_HR", "OURA_RESP_RATE", "OURA_TEMP_DEV",
           "OURA_READINESS_SCORE", "AH_SLEEP"]
VENDOR_SCORE = {"OURA_SLEEP_SCORE", "OURA_READINESS_SCORE"}
NO_PCT = {"OURA_TEMP_DEV"}  # 偏差本身围绕 0，百分比没有意义，只给差值
SOURCE_ZH = {"DEVICE_OURA": "Oura", "PHONE_HEALTH": "苹果健康"}
UNIT_ZH = {"score": "分", "min": "分钟", "bpm": "次/分"}
NOTE = "只显示读数和变化，不打分、不提醒。睡眠评分、准备度评分是 Oura 给的分，原样显示。"


def _latest(obs: list):
    return max(obs, key=lambda o: (o.instant.astimezone(timezone.utc).isoformat() if o.instant else "", o.observation_id))


def _fmt(x: Decimal, places: str = "0.1") -> str:
    return format(x.quantize(Decimal(places)).normalize(), "f")


def _pct(cur: Decimal, base: Decimal):
    if base == 0:
        return None
    return _fmt((cur - base) / abs(base) * 100)


def state(groups: dict, registry, vitals_sources: dict | None = None) -> dict:
    """groups = custom_cards.by_code() 的结果：代码 → 时点 → [Obs]。"""
    codes = registry.current.codes
    nights, metrics, series = {}, [], {}
    for code in METRICS:
        cdef = codes.get(code)
        if cdef is None or code not in groups:
            continue
        if vitals_sources is not None and not vitals_sources.get(cdef.family, False):
            continue  # 解绑的来源不进这张卡（已有记录保留在星炬与星轨）
        days = sorted(groups[code])
        vals = {}
        for d in days:
            o = _latest(groups[code][d])
            vals[d] = o
            nights.setdefault(d, {})[code] = {"value": format(o.value, "f"), "ref": o.ref,
                                              "source_ref": o.payload.get("source_ref")}
        last_day = days[-1]
        last = vals[last_day].value
        prev_day = days[-2] if len(days) > 1 else None
        before = [vals[d].value for d in days[-8:-1]]
        avg7 = sum(before) / len(before) if before else None
        metrics.append({
            "code": code, "label_zh": cdef.label_zh.replace("（Oura）", "").replace("（苹果健康）", ""),
            "source_zh": SOURCE_ZH.get(cdef.family, cdef.family), "unit": cdef.unit_canonical,
            "unit_zh": UNIT_ZH.get(cdef.unit_canonical, cdef.unit_canonical or ""), "vendor_score": code in VENDOR_SCORE,
            "last_day": last_day, "last": format(last, "f"), "ref": vals[last_day].ref, "nights": len(days),
            "prev_day": prev_day, "prev": format(vals[prev_day].value, "f") if prev_day else None,
            "vs_prev": _fmt(last - vals[prev_day].value) if prev_day else None,
            "vs_prev_pct": _pct(last, vals[prev_day].value) if prev_day and code not in NO_PCT else None,
            "avg7": _fmt(avg7) if avg7 is not None else None, "avg7_n": len(before),
            "vs_avg7_pct": _pct(last, avg7) if avg7 is not None and code not in NO_PCT else None,
            "vs_avg7": _fmt(last - avg7) if avg7 is not None else None})
        series[code] = [{"tp": d, "v": format(vals[d].value, "f")} for d in days[-60:]]
    return {"metrics": metrics, "series": series, "last_day": max(nights) if nights else None,
            "nights": [{"day": d, "values": nights[d]} for d in sorted(nights, reverse=True)[:90]],
            "night_count": len(nights), "sources": sorted({m["source_zh"] for m in metrics}), "note": NOTE}
