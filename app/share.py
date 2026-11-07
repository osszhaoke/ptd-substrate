"""授权协作 · 授权图片（产品负责人 2026-10-14 00:37 / 00:42 / 00:45）。

用户自选状态卡（可附上和上次比的变化）或某个时点的竞争性解释（四路结论原样），填给谁、用途、有效到，
本机画一张带水印的图片；同时在星簇记一条授权记录。图片由用户自己复制、粘贴发给小 Q 或别人。

- 图片里的内容由服务端按当前快照拼好（payload），界面照着画，不另外编；记录里存内容指纹（payload + 授权信息的 SHA-256），
  不存健康数值，只存选了哪些卡、哪个时点。
- 记录只追加、前后串指纹（<实例>/cluster/shares.jsonl），断链或改动能查出来。撤销也是追加一笔；发出去的图收不回。
- 水印是声明，不是加密：图片能被裁剪，AI 也能读出内容。这一点写在页面上。
- 回放实例不记；个人基座里隐藏的卡不出现在可选列表里，也不能被选上。
- 授权时效分开始、结束两天（产品负责人 2026-10-15 r57）：开始日期也进记录和水印；旧记录没有开始日期，照旧显示。
- 测试时记的授权可以从列表隐藏：追加一条 HIDE，原记录和指纹链都不动；星簇授权记录（出域流水）照旧全列。
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
from datetime import date, datetime, timedelta
from pathlib import Path

LOCK = threading.Lock()
MAX_TO, MAX_PURPOSE, MAX_DAYS, MAX_ITEMS = 20, 30, 90, 12
NOTE = "仅供授权对象在授权用途内查看；不构成医学建议。"


class ShareError(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(code)
        self.code, self.detail = code, detail


def _canon(o) -> str:
    return json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(o) -> str:
    return hashlib.sha256(_canon(o).encode()).hexdigest()


def _hm(hours) -> str:
    try:
        m = round(float(hours) * 60)
    except (TypeError, ValueError):
        return str(hours)
    return f"{m // 60} 小时 {m % 60} 分" if m % 60 else f"{m // 60} 小时"


def _pretty(t: str) -> str:
    return str(t or "").replace("×10^9/L", "×10⁹/L").replace("×10^12/L", "×10¹²/L")


def _sg(v) -> str:
    s = str(v)
    return s if s.startswith("-") or s in ("0", "0.0") else "+" + s


def _change(L: dict) -> str:
    x = L.get("extra") or {}
    if not x.get("prev_day"):
        return ""
    head = f"上次 {str(x['prev_day'])[5:]}" + (f"：{_pretty(x['prev_text'])}" if x.get("prev_text") else "")
    if x.get("change") is None:
        return head
    return head + f" · 变化 {_sg(x['change'])}" + (f"（{_sg(x['change_pct'])}%）" if x.get("change_pct") is not None else "")


# ----------------------------------------------------------------------------- 可选内容

def options(snap: dict, compete_tps: list, hidden: set) -> dict:
    """界面上能选的：状态卡（按组）+ 竞争性解释的时点。没有结果的卡不列（不做空卡）。"""
    groups = []
    tps = snap.get("timepoints") or []
    if tps and "sjia-mas" not in hidden and snap.get("runs_by_tp") is not None and (snap.get("instance") or {}).get("cards", ["SJIA_FOCUS"]).count("SJIA_FOCUS"):
        last = tps[-1]
        groups.append({"zh": "综合关注", "items": [{"id": "C:sjia-mas", "name": "综合关注", "value": last.get("level_zh") or "", "tp": last["tp"]}]})
    for g in (snap.get("engines") or {}).get("groups") or []:
        items = []
        for c in g["cards"]:
            L = c.get("latest") or {}
            if not L.get("tp"):
                continue
            items.append({"id": "E:" + c["rule"], "name": c["name"], "value": _value(c, L), "tp": L["tp"], "has_change": bool(_change(L))})
        if items:
            groups.append({"zh": g["zh"], "items": items})
    cc = [{"id": "U:" + c["card_id"], "name": c["name"], "value": (c.get("current") or {}).get("level_zh") or "还没有结果",
           "tp": (c.get("current") or {}).get("tp")} for c in snap.get("custom_cards") or [] if c.get("active", True)]
    if cc:
        groups.append({"zh": "我自建的卡", "items": cc})
    return {"groups": groups, "compete": [{"id": "X:" + t, "tp": t} for t in compete_tps]}


def _value(c: dict, L: dict) -> str:
    if L.get("status") != "computed":
        return L.get("status_zh") or L.get("text") or ""
    if c["rule"] == "SLEEP.A01-DURATION" and L.get("value") is not None:
        return _hm(L["value"])
    return _pretty(L.get("text"))


def payload(snap: dict, ids: list, with_change: bool, compete_of, hidden: set) -> dict:
    """按选中的 id 拼图片内容。compete_of(tp) → compete.explain 的结果。不认识或被隐藏的 id → 报错，不悄悄略过。"""
    if not ids or len(ids) > MAX_ITEMS or len(set(ids)) != len(ids):
        raise ShareError("ITEMS_INVALID", f"选 1～{MAX_ITEMS} 项")
    eng = {"E:" + c["rule"]: c for g in (snap.get("engines") or {}).get("groups") or [] for c in g["cards"]}
    grp = {"E:" + c["rule"]: g["zh"] for g in (snap.get("engines") or {}).get("groups") or [] for c in g["cards"]}
    custom = {"U:" + c["card_id"]: c for c in snap.get("custom_cards") or []}
    cards, lanes = [], None
    for i in ids:
        if not isinstance(i, str):
            raise ShareError("ITEMS_INVALID", "")
        if i == "C:sjia-mas":
            tps = snap.get("timepoints") or []
            if "sjia-mas" in hidden or not tps:
                raise ShareError("ITEM_UNKNOWN", i)
            last = tps[-1]
            res = last.get("result") or {}
            drv = res.get("drivers") or []
            rules = [d["rule"] for d in drv if d.get("kind") == "RULE" and d.get("result") == "MET"]
            note = ("达到界值的标准：" + "、".join(_rule_short(r) for r in rules)) if rules else ""
            card = {"id": i, "group": "综合关注", "name": "综合关注", "value": last.get("level_zh") or "", "tp": last["tp"], "note": note}
            if with_change:
                ch = [ind for ind in (res.get("dynamic") or {}).get("indicators") or [] if ind.get("status") == "TRIGGERED"]
                if ch:
                    card["change"] = "超过变化阈值：" + "、".join(f"{x['label_zh']} {x.get('change') or ''}".strip() for x in ch)
            cards.append(card)
        elif i in eng:
            c, L = eng[i], eng[i].get("latest") or {}
            if not L.get("tp"):
                raise ShareError("ITEM_EMPTY", c["name"])
            card = {"id": i, "group": grp[i], "name": c["name"], "value": _value(c, L), "tp": L["tp"]}
            if with_change and _change(L):
                card["change"] = _change(L)
            cards.append(card)
        elif i in custom:
            c = custom[i]
            cur = c.get("current") or {}
            cards.append({"id": i, "group": "我自建的卡", "name": c["name"], "value": cur.get("level_zh") or "还没有结果",
                          "tp": cur.get("tp"), "note": c.get("rule_zh") or ""})
        elif i.startswith("X:"):
            if lanes is not None:
                raise ShareError("ITEMS_INVALID", "竞争性解释一次只放一个时点")
            d = compete_of(i[2:])
            if not d or not d.get("found"):
                raise ShareError("ITEM_UNKNOWN", i)
            lanes = _lanes(d)
        else:
            raise ShareError("ITEM_UNKNOWN", i)
    return {"cards": cards, "compete": lanes, "with_change": bool(with_change)}


RULE_SHORT = {"R1": "2016 分类标准", "R2": "HLH-2004 标准", "R3": "MS 评分"}


def _rule_short(r: str) -> str:
    return RULE_SHORT.get(r, r)


def _flat(lines: list, deep: int = 0) -> list:
    out = []
    for ln in lines:
        out.append(dict(ln, deep=deep))
        out += _flat(ln.get("items") or [], deep + 1)
    return out


def _lanes(d: dict) -> dict:
    """竞争性解释原样：每一路的名字、结论、缺什么、各条件（要求 / 实际 / 结果），加小结。不改写、不合并打分。"""
    cols = []
    for c in d["columns"]:
        rows = []
        for g in c["groups"]:
            rows.append({"head": g["zh"] + (f"：{g['outcome']}" if g.get("outcome") else "")})
            rows += [{"need": ln["need"], "got": ln.get("got") or "", "outcome": ln.get("outcome") or "", "deep": ln["deep"]}
                     for ln in _flat(g["lines"])]
        cols.append({"id": c["id"], "name": re.sub(r"（R\d+）", "", c["name"]), "result": c["result"], "result_zh": c["result_zh"],
                     "review": c.get("expert_review") or "", "missing": c.get("missing") or [], "rows": rows})
    return {"tp": d["tp"], "level_zh": d["level_zh"], "formal": (d.get("formal") or {}).get("level_zh"), "columns": cols,
            "summary": (d.get("stability") or {}).get("text") or [], "note": d.get("note") or ""}


# ----------------------------------------------------------------------------- 授权记录（只追加、串指纹）

def _path(root: Path) -> Path:
    return Path(root) / "cluster" / "shares.jsonl"


def _read(root: Path) -> list:
    p = _path(root)
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text("utf-8").splitlines() if x.strip()]


def verify(root: Path) -> dict:
    prev = ""
    for n, r in enumerate(_read(root), 1):
        body = {k: v for k, v in r.items() if k != "sha"}
        if r.get("prev") != prev or _sha(body) != r.get("sha"):
            return {"ok": False, "line": n}
        prev = r["sha"]
    return {"ok": True, "line": None}


def _append(root: Path, rec: dict) -> dict:
    p = _path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = _read(root)
    if not verify(root)["ok"]:
        raise ShareError("STORE_TAMPERED", "授权图片记录的指纹链对不上，先核对再记")
    rec = dict(rec, seq=len(rows) + 1, prev=rows[-1]["sha"] if rows else "")
    rec["sha"] = _sha(rec)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def _form(body: dict, today: date) -> dict:
    to = str(body.get("to") or "").strip()
    purpose = str(body.get("purpose") or "").strip()
    if not 1 <= len(to) <= MAX_TO:
        raise ShareError("TO_INVALID", f"给谁：1～{MAX_TO} 个字")
    if not 1 <= len(purpose) <= MAX_PURPOSE:
        raise ShareError("PURPOSE_INVALID", f"用途：1～{MAX_PURPOSE} 个字")
    def day(name, code, zh):
        v = str(body.get(name) or "")
        try:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
                return v, date.fromisoformat(v)
        except ValueError:
            pass
        raise ShareError(code, zh + "：请填正确的日期")
    start, s = day("from", "FROM_INVALID", "开始") if body.get("from") else (today.isoformat(), today)
    until, u = day("until", "UNTIL_INVALID", "结束")
    if not today <= s <= today + timedelta(days=MAX_DAYS):
        raise ShareError("FROM_INVALID", f"开始：今天起 {MAX_DAYS} 天内")
    if not s <= u <= s + timedelta(days=MAX_DAYS):
        raise ShareError("UNTIL_INVALID", f"结束：不能早于开始，最长 {MAX_DAYS} 天")
    return {"to": to, "purpose": purpose, "from": start, "until": until}


def create(root: Path, body: dict, content: dict, now: str, nature: str) -> dict:
    """记一条授权，返回 {share, payload}。图片内容就是 payload；指纹盖住内容和授权信息。"""
    f = _form(body, date.fromisoformat(now[:10]))
    names = [c["name"] for c in content["cards"]] + (["竞争性解释 " + content["compete"]["tp"]] if content["compete"] else [])
    scope = "、".join(names) + ("（含变化）" if content["with_change"] and any(c.get("change") for c in content["cards"]) else "")
    meta = dict(f, scope=scope, at=now, nature=nature)
    content_sha = _sha({"payload": content, "meta": meta})
    with LOCK:
        n = len(_read(root)) + 1
        sid = "S-" + hashlib.sha256(f"{root}|{n}|{content_sha}".encode()).hexdigest()[:6].upper()
        rec = _append(root, {"kind": "CREATE", "share_id": sid, "at": now, "to": f["to"], "purpose": f["purpose"], "from": f["from"], "until": f["until"],
                             "items": [c["id"] for c in content["cards"]] + (["X:" + content["compete"]["tp"]] if content["compete"] else []),
                             "tps": sorted({c["tp"] for c in content["cards"] if c.get("tp")}), "with_change": content["with_change"],
                             "scope": scope, "content_sha": content_sha, "nature": nature})
    return {"share": _row(rec, set()), "payload": content, "meta": dict(meta, share_id=sid, content_sha=content_sha, note=NOTE)}


def revoke(root: Path, sid: str, now: str) -> dict:
    with LOCK:
        rows = _read(root)
        if not any(r["kind"] == "CREATE" and r["share_id"] == sid for r in rows):
            raise ShareError("SHARE_UNKNOWN", sid)
        if any(r["kind"] == "REVOKE" and r["share_id"] == sid for r in rows):
            raise ShareError("SHARE_REVOKED", sid)
        _append(root, {"kind": "REVOKE", "share_id": sid, "at": now})
    return {"ok": True}


def hide(root: Path, sid: str, now: str) -> dict:
    """从“记过的授权图片”列表隐藏一条（测试时记的）。只追加，原记录不动。"""
    with LOCK:
        rows = _read(root)
        if not any(r["kind"] == "CREATE" and r["share_id"] == sid for r in rows):
            raise ShareError("SHARE_UNKNOWN", sid)
        if not any(r["kind"] == "HIDE" and r["share_id"] == sid for r in rows):
            _append(root, {"kind": "HIDE", "share_id": sid, "at": now})
    return {"ok": True}


def _row(r: dict, revoked: set) -> dict:
    return {"share_id": r["share_id"], "at": r["at"], "to": r["to"], "purpose": r["purpose"], "from": r.get("from"), "until": r["until"], "scope": r["scope"],
            "content_sha": r["content_sha"], "revoked": r["share_id"] in revoked}


def listing(root: Path) -> dict:
    rows = _read(root)
    gone = {r["share_id"] for r in rows if r["kind"] == "REVOKE"}
    hid = {r["share_id"] for r in rows if r["kind"] == "HIDE"}
    return {"shares": [_row(r, gone) for r in reversed(rows) if r["kind"] == "CREATE" and r["share_id"] not in hid], "verify": verify(root)}


def records(root: Path, when) -> list:
    """并进星簇的授权记录（出域）。摘要只写范围名称和用途，不写健康数值。"""
    rows = _read(root)
    hid = {r["share_id"] for r in rows if r["kind"] == "HIDE"}
    out = []
    for r in rows:
        if r["kind"] == "HIDE":
            continue
        made = r["kind"] == "CREATE"
        c = r if made else next((x for x in rows if x["kind"] == "CREATE" and x["share_id"] == r["share_id"]), {})
        out.append({"id": "share-" + str(r["seq"]), "grant": r["share_id"], "at": r["at"], "when": when(r["at"]), "obj": c.get("to", "—"),
                    "how": ("生成授权图片" if made else "撤销授权图片") + " · 用户自己粘贴发送", "level": "图片（含所选状态卡的数值）",
                    "summary": ("范围：" + c.get("scope", "") + " · 用途：" + c.get("purpose", "")) if made else "图片已发出的收不回，只在这里记一笔",
                    "result": "已生成" if made else "已撤销", "ok": True, "action": "SHARE" if made else "SHARE_REVOKE", "via": "IMAGE",
                    "outcome": "SHARED" if made else "REVOKED", "reason": None, "egress": made,
                    "hidden": r["share_id"] in hid})   # 测试时记、已从列表隐藏的（星痕的授权记录里不列，只报条数）
    return out
