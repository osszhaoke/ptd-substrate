"""时区兜底（产品负责人 2026-10-15 Windows 队友测试版）。

Windows 版 Python 不自带 IANA 时区库（要另装 tzdata 包），ZoneInfo("Asia/Shanghai") 会直接报错。
install() 在其他模块导入 zoneinfo 之前调用：本机能正常用 ZoneInfo 就什么都不改；不能用时，只把 Asia/Shanghai（自 1991 年起固定东八区、
无夏令时，固定偏移和真实时区等价）和 UTC 换成固定偏移，其他时区照旧报“找不到”，不猜。
"""
from __future__ import annotations

import zoneinfo
from datetime import timedelta, timezone

FIXED = {"Asia/Shanghai": timezone(timedelta(hours=8), "Asia/Shanghai"), "UTC": timezone.utc, "Etc/UTC": timezone.utc}
_real = zoneinfo.ZoneInfo


def _fallback(key: str):
    try:
        return _real(key)
    except zoneinfo.ZoneInfoNotFoundError:
        if key in FIXED:
            return FIXED[key]
        raise


def install() -> bool:
    """返回 True = 本机缺时区库，已换成固定偏移兜底。"""
    try:
        _real("Asia/Shanghai")
        return False
    except zoneinfo.ZoneInfoNotFoundError:
        zoneinfo.ZoneInfo = _fallback
        return True
