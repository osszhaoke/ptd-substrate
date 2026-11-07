"""化验单识别的轻量脱敏（产品负责人 2026-10-15：sJIA 演示今后用真实脱敏数据）。

识别出来的文字里，凡是带姓名栏、身份证号、手机 / 电话、病历号一类的行，整行不存（识别记录、候选、原文行都去掉），
并告诉用户去掉了哪几类。只管识别结果，原图不改——原图上的个人信息要在上传前自己遮住。
"""
from __future__ import annotations

import re

RULES = [
    ("姓名", re.compile(r"(姓\s*名|患\s*者\s*名|病\s*人\s*名)\s*[:：]")),
    ("身份证号", re.compile(r"身份证|(?<!\d)\d{17}[\dXx](?!\d)")),
    ("电话", re.compile(r"电\s*话|手\s*机|(?<!\d)1[3-9]\d{9}(?!\d)|(?<!\d)0\d{2,3}-\d{7,8}(?!\d)")),
    ("病历号", re.compile(r"病\s*历\s*号|住\s*院\s*号|门\s*诊\s*号|就\s*诊\s*卡\s*号|登\s*记\s*号|ID\s*号")),
]


def hits(text: str) -> list:
    return [zh for zh, rx in RULES if rx.search(text or "")]


def _text(x) -> str:
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        return " ".join(_text(v) for v in x.values() if isinstance(v, (str, dict, list)))
    if isinstance(x, list):
        return " ".join(_text(v) for v in x)
    return ""


def scrub(result: dict) -> list:
    """就地去掉带个人信息的行；返回去掉了哪几类（没有就是空列表）。"""
    found = set()
    for key in ("source_lines", "lines", "unmatched"):
        v = result.get(key)
        if not isinstance(v, list):
            continue
        keep = []
        for item in v:
            h = hits(_text(item))
            if h:
                found.update(h)
            else:
                keep.append(item)
        result[key] = keep
    rows = result.get("rows")
    if isinstance(rows, list):
        keep = []
        for r in rows:
            h = hits(_text(r))
            found.update(h)
            if not h:
                keep.append(r)
        result["rows"] = keep
    kinds = [zh for zh, _ in RULES if zh in found]
    if kinds:
        note = "已去掉识别结果里的个人信息：" + "、".join(kinds) + "（原图没有改，上传前请自己遮住）"
        result["notice"] = (result.get("notice") + "；" if result.get("notice") else "") + note
    return kinds
