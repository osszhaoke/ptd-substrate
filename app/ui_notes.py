"""界面批注：产品负责人 在页面上点一处写一句意见，存成本机一个 jsonl 文件（只追加；删除也是追加一条记录）。"""
import itertools
import json
import threading
import time
from pathlib import Path

_LOCK = threading.Lock()
_SEQ = itertools.count()


def path(root: Path) -> Path:
    return Path(root) / "ui-notes" / "notes.jsonl"


def _rows(root):
    p = path(root)
    if not p.exists():
        return []
    out = []
    for line in p.read_text("utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def list_notes(root):
    gone, notes = set(), {}
    for r in _rows(root):
        if r.get("op") == "clear":
            notes.clear()
        elif r.get("op") == "delete":
            notes.pop(r.get("id"), None)
        elif r.get("id"):
            notes[r["id"]] = r
    return list(notes.values())


def add(root, body: dict):
    text = str(body.get("text") or "").strip()[:2000]
    if not text:
        raise ValueError("EMPTY_NOTE")
    keep = ("page", "page_zh", "sel", "snippet", "x", "y", "vw", "vh", "url")
    row = {k: body[k] for k in keep if k in body}
    row.update(id="n%d-%d" % (int(time.time() * 1000), next(_SEQ)), at=time.strftime("%Y-%m-%d %H:%M:%S"), text=text)
    _append(root, row)
    return row


def delete(root, nid):
    _append(root, {"op": "delete", "id": str(nid), "at": time.strftime("%Y-%m-%d %H:%M:%S")})


def clear(root):
    _append(root, {"op": "clear", "at": time.strftime("%Y-%m-%d %H:%M:%S")})


def _append(root, row):
    p = path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def markdown(root):
    notes = list_notes(root)
    lines = ["# PTDS 界面批注", "", f"共 {len(notes)} 条。文件：{path(root)}", ""]
    for i, n in enumerate(notes, 1):
        lines.append(f"## {i}. {n.get('page_zh') or n.get('page') or ''}  ({n['at']})")
        lines.append("")
        lines.append(n["text"])
        lines.append("")
        if n.get("snippet"):
            lines.append(f"- 点的位置文字：{n['snippet']}")
        if n.get("sel"):
            lines.append(f"- 元素：`{n['sel']}`")
        lines.append(f"- 坐标：{n.get('x')}, {n.get('y')}（窗口 {n.get('vw')}×{n.get('vh')}）")
        lines.append("")
    return "\n".join(lines)
