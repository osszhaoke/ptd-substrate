"""首页文字（产品负责人 2026-10-15 r65/r66）：大标题和每张实例卡（标签、卡名、说明、卡点 / 目标 / 行动 / 结果）可以用齿轮改。

默认文字写在这里；改动只追加到 <实例根目录>/home_texts.jsonl（每行一条：改标题、改某张卡、恢复默认），最新一条为准，旧版本都留着。
卡片标签同时是页面右上角显示的实例名；卡名只在首页卡片上。不改程序文件，不改 product_config.json，不碰任何实例数据。
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

LOCK = threading.Lock()
TITLE = "从关注一个状态，到关注人的一生"
ROWS = ("卡点", "目标", "行动", "结果")
MAX = {"tag": 30, "name": 20, "note": 120, "row": 300, "title": 40}

DEFAULTS = {}


class HomeError(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(code)
        self.code, self.detail = code, detail


def _path(root: Path) -> Path:
    return Path(root) / "home_texts.jsonl"


def _rows(root: Path) -> list:
    p = _path(root)
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text("utf-8").splitlines() if x.strip()]


def view(root: Path, keys) -> dict:
    """{title, cards: {key: {tag, name, note, rows:[[label, text]...], edited}}, edited_title}；只给传入的实例 key。"""
    title, cards = None, {}
    for r in _rows(root):
        if r.get("target") == "title":
            title = None if r.get("reset") else r.get("text")
        elif r.get("target") in DEFAULTS:
            cards[r["target"]] = None if r.get("reset") else r.get("fields")
    out = {}
    for k in keys:
        if k not in DEFAULTS:
            continue
        d = dict(DEFAULTS[k], **(cards.get(k) or {}))
        out[k] = {"tag": d["tag"], "name": d["name"], "note": d["note"], "rows": [[ROWS[i], d["rows"][i]] for i in range(4)],
                  "edited": bool(cards.get(k))}
    return {"title": title or TITLE, "edited_title": bool(title), "cards": out}


def _clean(v, limit: int, field: str) -> str:
    s = " ".join(str(v or "").split())
    if not s or len(s) > limit:
        raise HomeError("FIELD_INVALID", f"{field}：1～{limit} 个字")
    return s


def save(root: Path, body: dict, now: str) -> None:
    target = str(body.get("target") or "")
    if target != "title" and target not in DEFAULTS:
        raise HomeError("TARGET_UNKNOWN", target)
    rec = {"at": now, "target": target}
    if body.get("reset"):
        rec["reset"] = True
    elif target == "title":
        rec["text"] = _clean(body.get("text"), MAX["title"], "大标题")
    else:
        f = body.get("fields") or {}
        rows = f.get("rows") or []
        if len(rows) != 4:
            raise HomeError("FIELD_INVALID", "卡点、目标、行动、结果四行都要有")
        rec["fields"] = {"tag": _clean(f.get("tag"), MAX["tag"], "标签"), "name": _clean(f.get("name"), MAX["name"], "卡名"),
                         "note": _clean(f.get("note"), MAX["note"], "说明"),
                         "rows": [_clean(x, MAX["row"], ROWS[i]) for i, x in enumerate(rows)]}
    with LOCK:
        p = _path(root)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
