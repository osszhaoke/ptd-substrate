"""观测时间不能晚于现在（产品负责人 2026-10-15：手工录入写进了 2026-12-16，“增加一个日期限制不超过就行”）。

手工录入、化验单识别（单张和批量）、表格导入保存前都过这一道：观测时刻晚于现在，或只有日期且日期晚于今天（实例时区），就不收。
设备自动送来的读数不在这里拦（时间由设备给，偏几秒是常事）。
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

FUTURE_ZH = "日期在今天之后，请核对"


def is_future(temporal: dict, tz: str, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    role = (temporal or {}).get("role")
    if role == "INSTANT" and temporal.get("observed_at"):
        return datetime.fromisoformat(temporal["observed_at"]) > now
    if role == "DAY" and temporal.get("observed_date"):
        return temporal["observed_date"] > now.astimezone(ZoneInfo(tz)).date().isoformat()
    return False


def split(items, tz: str) -> tuple:
    """→ (能存的, 被拒的 [{row, code, why}])；row 从 source_ref 的 #rowN 里取，取不到就写 None。"""
    keep, out, now = [], [], datetime.now(timezone.utc)
    for it in items:
        if is_future(it.temporal, tz, now):
            ref = str(it.source_ref or "")
            row = ref.rsplit("#row", 1)[1] if "#row" in ref else None
            out.append({"row": int(row) if row and row.isdigit() else None, "code": it.code, "why": FUTURE_ZH})
        else:
            keep.append(it)
    return keep, out
