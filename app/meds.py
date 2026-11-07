"""星炬 · 用药记录（产品负责人 2026-10-14 07:33 选定“血液肝凝血 + 用药”）：用药背景另存一份记录，不改数据库表结构。

- 存在实例目录 startorch/meds.jsonl，只追加：开始、改剂量、停药、重新用药、更正、撤回都是新的一行，旧行不动。
- 每行带上一行的指纹（prev），整份文件可以从头核对有没有被改过。
- 只记本人或照护者亲手录入的事实（药名、剂量、单位、途径、频次、日期、原因），不做剂量判断、不判断药物反应。
- 这些记录不交给星灵（本机千问），也不进任何阈值。
"""
from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

from h1_common import canonical_bytes, sha256_hex

UNITS = ("mg", "mg/kg", "g", "μg", "mL", "IU", "片", "粒", "支")
ROUTES = ("口服", "静脉", "皮下", "肌肉", "外用", "吸入", "其他")
KINDS = ("START", "CHANGE", "STOP", "RESTART")
KIND_ZH = {"START": "开始用药", "CHANGE": "改剂量", "STOP": "停药", "RESTART": "重新用药", "CORRECT": "更正", "RETRACT": "撤回"}
LOCK = threading.Lock()
GENESIS = "0" * 64


class MedError(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(code)
        self.code, self.detail = code, detail


def path_of(root: Path) -> Path:
    return root / "startorch" / "meds.jsonl"


def head_of(root: Path) -> Path:
    return root / "startorch" / "meds.head.json"


def _read(root: Path):
    """读出所有行。坏行（不是完整 JSON）不丢，记下行号，交给 verify 报出来。"""
    p = path_of(root)
    if not p.exists():
        return [], None, 0
    rows, bad, n = [], None, 0
    for i, x in enumerate(p.read_text("utf-8").splitlines(), 1):
        if not x.strip():
            continue
        n += 1
        try:
            rec = json.loads(x)
            if not isinstance(rec, dict):
                raise ValueError
        except ValueError:
            bad = bad or i
            continue
        rows.append(rec)
    return rows, bad, n


def _lines(root: Path) -> list:
    return _read(root)[0]


def verify(root: Path) -> dict:
    """从头核对指纹链：每行的 prev 等于上一行的 sha，每行的 sha 等于这行内容的指纹；
    另存一份“链头”（行数和最后一行指纹），文件尾部被截掉也能发现。"""
    rows, bad, _ = _read(root)
    prev = GENESIS
    for i, rec in enumerate(rows, 1):
        if bad and i >= bad:
            return {"ok": False, "line": bad}
        body = {k: v for k, v in rec.items() if k != "sha"}
        if rec.get("prev") != prev or sha256_hex(canonical_bytes(body)) != rec.get("sha"):
            return {"ok": False, "line": i}
        prev = rec["sha"]
    if bad:
        return {"ok": False, "line": bad}
    try:
        head = json.loads(head_of(root).read_text("utf-8"))
    except (OSError, ValueError):
        head = None
    if isinstance(head, dict) and head.get("lines"):
        n = int(head["lines"])
        if n > len(rows) or rows[n - 1].get("sha") != head.get("sha"):
            return {"ok": False, "line": min(n, len(rows) + 1), "truncated": True}
    return {"ok": True, "lines": len(rows), "head": prev}


def _append(root: Path, rec: dict) -> dict:
    p = path_of(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = _lines(root)
    rec = dict(rec, prev=rows[-1]["sha"] if rows else GENESIS)
    rec["sha"] = sha256_hex(canonical_bytes(rec))
    with open(p, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
    head_of(root).write_text(json.dumps({"lines": len(rows) + 1, "sha": rec["sha"]}), "utf-8")
    return rec


_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DOSE = re.compile(r"^\d{1,6}(\.\d{1,4})?$")


def _day(s, field="date") -> str:
    s = str(s or "").strip()
    try:
        if not _DAY.match(s):
            raise ValueError
        d = date.fromisoformat(s)
        if d.year < 1900:
            raise ValueError
    except ValueError:
        raise MedError("DATE_INVALID", "日期要写成 YYYY-MM-DD") from None
    return d.isoformat()


def _fields(body, today: str, partial=False) -> dict:
    if not isinstance(body, dict):
        raise MedError("BODY_INVALID", "内容格式不对")
    out = {}
    if not partial or "drug" in body:
        drug = re.sub(r"\s+", " ", str(body.get("drug") or "")).strip()
        if not drug or len(drug) > 60:
            raise MedError("DRUG_INVALID", "药名不能为空，最多 60 个字")
        out["drug"] = drug
    if not partial or "dose" in body:
        raw = str(body.get("dose") if body.get("dose") is not None else "").strip()
        if not _DOSE.match(raw):
            raise MedError("DOSE_INVALID", "剂量要写数字，最多 6 位整数、4 位小数")
        dose = Decimal(raw)
        if dose <= 0:
            raise MedError("DOSE_INVALID", "剂量要大于 0")
        out["dose"] = format(dose.normalize(), "f")
    if not partial or "unit" in body:
        if body.get("unit") not in UNITS:
            raise MedError("UNIT_INVALID", "单位只能选：" + "、".join(UNITS))
        out["unit"] = body["unit"]
    if not partial or "route" in body:
        route = body.get("route") or "口服"
        if route not in ROUTES:
            raise MedError("ROUTE_INVALID", "途径只能选：" + "、".join(ROUTES))
        out["route"] = route
    for k, n in (("freq", 30), ("reason", 120)):
        if not partial or k in body:
            v = re.sub(r"\s+", " ", str(body.get(k) or "")).strip()
            if len(v) > n:
                raise MedError(k.upper() + "_TOO_LONG", f"最多 {n} 个字")
            out[k] = v
    if not partial or "date" in body:
        out["date"] = _day(body.get("date"))
        if out["date"] > today:
            raise MedError("DATE_FUTURE", "日期不能晚于今天")
    return out


def _events(rows: list) -> dict:
    """套用更正和撤回后的事件（按录入先后）。"""
    events = {r["event_id"]: dict(r, retracted=False, corrected_by=[]) for r in rows if r.get("kind") in KINDS}
    for r in rows:
        t = events.get(r.get("target"))
        if t is None:
            continue
        if r["kind"] == "CORRECT":
            t.update(r.get("fields") or {})
            t["corrected_by"].append(r["event_id"])
        elif r["kind"] == "RETRACT":
            t["retracted"] = True
            t["retract_reason"] = r.get("reason", "")
    return events


def _check(live: list) -> None:
    """一个疗程里没撤回的记录，按录入先后必须讲得通：先开始，停了才能重新用，在用才能改剂量或停；
    日期不倒退；停药日期是“这天起不再用”，所以要晚于上一条的日期。"""
    on, prev = False, None
    for e in live:
        k = e["kind"]
        if prev is None:
            if k != "START":
                raise MedError("SEQUENCE_BROKEN", "这样改之后，这个药的第一条不再是“开始用药”；要先撤回后面的记录")
        elif k == "START":
            raise MedError("SEQUENCE_BROKEN", "一个疗程只能有一条“开始用药”")
        elif k in ("CHANGE", "STOP") and not on:
            raise MedError("MED_NOT_ACTIVE", "这个药已经停了，要先记“重新用药”")
        elif k == "RESTART" and on:
            raise MedError("MED_ACTIVE", "这个药还在用，不用记“重新用药”")
        if prev is not None:
            if e["date"] < prev["date"]:
                raise MedError("DATE_ORDER", f"日期不能早于这个药上一条记录的 {prev['date']}")
            if k == "STOP" and e["date"] == prev["date"]:
                raise MedError("DATE_ORDER", f"停药日期是“这天起不再用”，要晚于上一条记录的 {prev['date']}")
        on, prev = k != "STOP", e


def _live(events: dict, mid: str) -> list:
    return sorted((e for e in events.values() if e["med_id"] == mid and not e["retracted"]), key=lambda e: e["seq"])


def courses(root: Path) -> dict:
    """读模型：先套用更正和撤回，再按每个疗程（med_id）排出事件和用药区间。"""
    events = _events(_lines(root))
    by = {}
    for e in events.values():
        by.setdefault(e["med_id"], []).append(e)
    out = []
    for mid, evs in by.items():
        evs.sort(key=lambda e: e["seq"])
        live = [e for e in evs if not e["retracted"]]
        spans, cur = [], None
        for e in live:
            if e["kind"] in ("START", "RESTART", "CHANGE"):
                if cur:
                    cur["to"], cur["end"] = e["date"], "CHANGE"
                    spans.append(cur)
                cur = {"from": e["date"], "to": None, "kind": e["kind"], "end": None, "dose": e["dose"], "unit": e["unit"],
                       "route": e["route"], "freq": e["freq"]}
            elif e["kind"] == "STOP" and cur:
                cur["to"], cur["end"] = e["date"], "STOP"
                spans.append(cur)
                cur = None
        if cur:
            spans.append(cur)
        last = live[-1] if live else None
        start = next((e for e in evs if e["kind"] == "START"), evs[0])
        out.append({"med_id": mid, "drug": start["drug"], "active": bool(last and last["kind"] != "STOP"),
                    "live": bool(live), "spans": spans,
                    "events": [{k: e.get(k) for k in ("event_id", "kind", "drug", "dose", "unit", "route",
                                                      "freq", "date", "reason", "nature", "recorded_at",
                                                      "retracted", "retract_reason", "corrected_by")}
                               | {"kind_zh": KIND_ZH[e["kind"]]} for e in evs]})
    out.sort(key=lambda c: (not c["active"], not c["live"], c["drug"]))
    return {"courses": out, "chain": verify(root)}


def _writable(root: Path) -> list:
    chain = verify(root)
    if not chain["ok"]:
        raise MedError("STORE_TAMPERED", f"用药记录文件核对不上（第 {chain['line']} 行），先不再写入，需要人工检查")
    return _lines(root)


def record(root: Path, body: dict, *, now: str, today: str, nature: str) -> dict:
    """开始用药 / 改剂量 / 停药 / 重新用药。每次都是新的一行，返回保存后的读模型。"""
    if not isinstance(body, dict):
        raise MedError("BODY_INVALID", "内容格式不对")
    kind = body.get("kind")
    if kind not in KINDS:
        raise MedError("KIND_INVALID", "只能是：开始用药、改剂量、停药、重新用药")
    with LOCK:
        rows = _writable(root)
        events = _events(rows)
        seq = len(rows) + 1
        if kind == "START":
            mid = "MED-" + uuid.uuid4().hex[:8]
            f = _fields(body, today)
            live = []
        else:
            mid = body.get("med_id")
            live = _live(events, mid) if isinstance(mid, str) else []
            if not live:
                raise MedError("MED_UNKNOWN", "没有这条用药记录（或已全部撤回）")
            last = live[-1]
            if kind == "STOP":
                f = {k: last[k] for k in ("drug", "dose", "unit", "route", "freq")}
                f.update(_fields({k: body[k] for k in ("date", "reason") if k in body}, today, partial=True))
                if "date" not in f:
                    raise MedError("DATE_INVALID", "要写停药日期")
            else:
                f = _fields(dict({k: last[k] for k in ("drug", "dose", "unit", "route", "freq")}, **body), today)
                f["drug"] = live[0]["drug"]  # 同一个疗程不改药名；换药 = 停一个、开始另一个
        rec = {"event_id": "ME-" + uuid.uuid4().hex[:10], "seq": seq, "med_id": mid, "kind": kind, **f,
               "source": "MANUAL", "nature": nature, "recorded_at": now}
        _check(live + [rec])
        _append(root, rec)
        return courses(root)


def amend(root: Path, body: dict, *, now: str, today: str, nature: str) -> dict:
    """更正（改某一行的字段）或撤回（这一行作废）。原行保留，界面上能看到改过什么。
    改完之后整个疗程仍要讲得通（_check），讲不通就不收。"""
    if not isinstance(body, dict):
        raise MedError("BODY_INVALID", "内容格式不对")
    kind = body.get("kind")
    if kind not in ("CORRECT", "RETRACT"):
        raise MedError("KIND_INVALID", "只能是更正或撤回")
    with LOCK:
        rows = _writable(root)
        target = next((r for r in rows if r.get("event_id") == body.get("event_id") and r.get("kind") in KINDS), None)
        if target is None:
            raise MedError("EVENT_UNKNOWN", "没有这一条记录")
        if _events(rows)[target["event_id"]]["retracted"]:
            raise MedError("EVENT_RETRACTED", "这一条已经撤回了")
        rec = {"event_id": "ME-" + uuid.uuid4().hex[:10], "seq": len(rows) + 1, "med_id": target["med_id"],
               "kind": kind, "target": target["event_id"], "source": "MANUAL", "nature": nature, "recorded_at": now}
        if kind == "CORRECT":
            fields = _fields(body.get("fields") if "fields" in body else {}, today, partial=True)
            if target["kind"] != "START":
                fields.pop("drug", None)  # 药名只在开始那一行改
            if target["kind"] == "STOP":
                fields = {k: v for k, v in fields.items() if k in ("date", "reason")}  # 停药那行只有日期和原因
            if not fields:
                raise MedError("NOTHING_TO_CORRECT", "没有要更正的内容")
            rec["fields"] = fields
        else:
            reason = re.sub(r"\s+", " ", str(body.get("reason") or "")).strip()
            if not reason:
                raise MedError("REASON_REQUIRED", "撤回要写原因")
            if len(reason) > 120:
                raise MedError("REASON_TOO_LONG", "最多 120 个字")
            rec["reason"] = reason
        _check(_live(_events(rows + [rec]), target["med_id"]))
        _append(root, rec)
        return courses(root)


def on_day(root: Path, day: str) -> list:
    """某一天在用的药（给回溯、竞争性解释和溯源当背景用）。只读，不参与任何计算。"""
    out = []
    for c in courses(root)["courses"]:
        for s in c["spans"]:
            if s["from"] <= day and (s["to"] is None or day < s["to"]):
                out.append({"drug": c["drug"], "dose": s["dose"], "unit": s["unit"], "route": s["route"], "freq": s["freq"],
                            "since": s["from"]})
    return out
