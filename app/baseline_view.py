"""状态实验室 · 整体基线洞察（产品负责人 2026-10-15 批准 mock7；只在 sJIA 演示）。

表头只有 基线状态 / 发展状态 / 偏移情况，不写日期：每一格单独选——换指标、换用哪一次的值，格子里写这个值的日期。
这里只给“可选的东西”：主状态每个时点的结果（星轨账本），六类评估线索里每个指标的全部记录（星轨收件箱里的正式观测，
单位换成规范单位，带来源和 观测编号@版本）。选哪两个、偏移多少由页面算；选择只存在浏览器里，不进正式库。
- 三项文献规则按各自结果展示，不再提供自定义综合等级与演示动态规则。
- 评估线索默认只比较观测；本人阈值只作用于线索显示，不进入规则结果。
- 原有本人阈值历史继续保留；恢复设置只追加撤回记录。
- 只说升高 / 降低多少，不说好坏；没有记录写“无记录”。研究演示，未经临床验证。
"""
from __future__ import annotations

from types import SimpleNamespace

import json
from pathlib import Path

import body_bindings
from cards import open_startrack, take_snapshot

LEVEL_ZH = {"ALERT": "关注", "WATCH": "观察", "NONE": "无", "NOT_EVALUABLE": "算不了", "UNDETERMINED": "无法判定"}
RESULT_ZH = {"MET": "达到界值", "NOT_MET": "未达到", "INDETERMINATE": "缺数据算不了", "NOT_APPLICABLE": "不适用"}

CLUES = [
    ("neuro", "神经", ["CNS_INVOLVEMENT"]),
    ("fever", "发热", ["FEVER", "TEMP"]),
    ("liver", "肝脏", ["AST", "LDH", "TG", "ALT", "GGT", "ALP", "TBIL", "DBIL", "ALB"]),
    ("blood", "血液", ["FERRITIN", "PLT", "HB", "WBC", "ANC", "LYMPH"]),
    ("coag", "凝血", ["FIB", "DDIMER", "PT", "APTT", "INR", "TT", "FDP", "HEMORRHAGE"]),
    ("joint", "关节", ["ARTHRITIS"]),
]
MAIN = [("R1", "2016 分类标准", "MAS.EULAR-2016"), ("R2", "HLH-2004", "MAS.HLH-2004"),
        ("R3", "MS 评分", "MAS.MS-2019")]
SHORT = {"CNS_INVOLVEMENT": "中枢受累", "FEVER": "发热", "TEMP": "体温", "AST": "AST", "ALT": "ALT", "LDH": "LDH", "TG": "甘油三酯",
         "GGT": "GGT", "ALP": "ALP", "TBIL": "总胆红素", "DBIL": "直接胆红素", "ALB": "白蛋白", "FERRITIN": "铁蛋白", "PLT": "血小板",
         "HB": "血红蛋白", "WBC": "白细胞", "ANC": "中性粒细胞", "LYMPH": "淋巴细胞", "FIB": "纤维蛋白原", "DDIMER": "D-二聚体",
         "PT": "凝血酶原时间", "APTT": "APTT", "INR": "INR", "TT": "凝血酶时间", "FDP": "FDP", "HEMORRHAGE": "出血表现",
         "ARTHRITIS": "关节炎"}
SRC_ZH = {"OCR_LLM": "化验单", "MANUAL": "手动录入", "TABLE": "表格导入", "TEXT_LLM": "文本识别", "SYNTHETIC": "合成",
          "APPLE_HEALTH": "苹果健康", "DEVICE_GARMIN": "Garmin", "DEVICE_OURA": "Oura", "DEVICE_SOMALOOP": "Somaloop", "DEVICE_QKEER": "QKeer"}
NOTE = "研究演示，未经临床验证。颜色只表示偏离，不是诊断。"


def _unknown(node) -> int:
    return sum(1 for c in (node or {}).get("criteria") or [] if c.get("outcome") == "UNKNOWN")


def _main_cell(key: str, tp: dict, lead: dict) -> dict:
    r = tp["result"]
    out = {"tp": tp["tp"], "run_id": tp.get("run_id")}
    if key == "level":
        return dict(out, text=tp.get("level_zh") or "—", tone={"ALERT": "big", "WATCH": "small"}.get(tp.get("level"), "none"))
    if key == "dyn":
        lv = (r.get("dynamic") or {}).get("level")
        t = LEVEL_ZH.get(lv, lv or "—")
        if lead.get("dynamic_tp") == tp["tp"] and lead.get("days"):
            t += f" 早 {lead['days']} 天"
        return dict(out, text=t, state=LEVEL_ZH.get(lv, lv or "—"), tone={"ALERT": "big", "WATCH": "small"}.get(lv, "none"))
    rule = (r.get("rules") or {}).get(key) or {}
    res = rule.get("result")
    if key == "R2" and res == "INDETERMINATE":
        return dict(out, text=f"缺 {_unknown(rule)} 项", tone="none")
    if key == "R3" and rule.get("score") is not None:
        return dict(out, text=str(rule["score"]) + (" 达到" if res == "MET" else ""), num=str(rule["score"]),
                    tone="big" if res == "MET" else "none")
    return dict(out, text=RESULT_ZH.get(res, res or "—"), tone="big" if res == "MET" else "none")


def _records(inst) -> dict:
    """{代码: [记录…]}：星轨收件箱里每条当前有效的正式观测（只取有时间的），按时间排。"""
    track = open_startrack(inst.ctx)
    try:
        snap = take_snapshot(track, inst.ctx, SimpleNamespace(codes=set(), labels={}))
    finally:
        track.close()
    labels = {k: c.label_zh for k, c in inst.app.registry.current.codes.items()}
    out = {}
    for o in snap.observations:
        if o.day is None:
            continue
        p = o.payload
        rec = {"tp": o.day, "at": o.instant.isoformat() if o.instant else None, "ref": o.ref,
               "value": p["value_canonical"], "unit": p.get("unit_canonical") or "", "raw": (p.get("comparator") or "") + p["value_raw"],
               "raw_unit": p.get("unit_raw") or "", "comparator": p.get("comparator"), "bool": p["value_canonical"] in ("true", "false"),
               "source": SRC_ZH.get(p["source_kind"], p["source_kind"]), "label": SHORT.get(o.code) or labels.get(o.code, o.code)}
        out.setdefault(o.code, []).append(rec)
    for v in out.values():
        v.sort(key=lambda r: (r["tp"], r["at"] or ""))
    return out


# ----------------------------------------------------------------------------- 本人规则（只在这一页）

def _rules_path(inst) -> Path:
    return Path(inst.ctx.root) / "startorch" / "patient_rules.jsonl"


def rule_history(inst) -> list:
    p = _rules_path(inst)
    if not p.exists():
        return []
    out = []
    for line in p.read_text("utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def patient_thresholds(inst) -> dict:
    """{代码: 阈值（小数，如 "0.3"）}：每个指标最新的一条；撤回（threshold 为 null）就没有。"""
    cur = {}
    for r in rule_history(inst):
        cur[r["code"]] = r.get("threshold")
    return {c: t for c, t in cur.items() if t is not None}


def save_rule(inst, clue: str, thresholds: dict, *, reset: bool = False) -> dict:
    """thresholds: {代码: 百分数（如 30）}；reset = 这一类全部恢复规则。只追加。"""
    codes = dict((cid, cs) for cid, _, cs in CLUES).get(clue)
    if codes is None:
        raise ValueError("clue")
    rows, ver = [], len(rule_history(inst)) + 1
    now = inst.now()
    targets = {c: None for c in codes if c in patient_thresholds(inst)} if reset else thresholds
    for code, pct in targets.items():
        if code not in codes:
            raise ValueError("code")
        thr = None
        if pct is not None:
            v = float(pct)
            if not 0 < v <= 1000:
                raise ValueError("threshold")
            thr = format(v / 100, ".4g")
        rows.append({"version": ver, "author": "patient", "at": now, "clue": clue, "code": code, "threshold": thr})
    if rows:
        p = _rules_path(inst)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return {"saved": len(rows), "version": ver if rows else None}




def _sjia_view(inst, meds_on_day=None) -> dict:
    if not inst.sjia or inst.spec.get("kind") != "DEMO":
        return {"found": False, "why": "DEMO_ONLY"}
    snap = inst.snapshot()
    tps = [t for t in snap.get("timepoints") or [] if t.get("result")]
    if not tps:
        return {"found": False, "why": "NO_TIMEPOINTS"}
    published = {}  # Demo thresholds are not published medical rules.
    mine = patient_thresholds(inst)
    # Personal display thresholds never alter the three published rule results.
    main = [{"key": k, "label": zh, "rule": rid, "mark": "规", "patient_codes": [],
             "options": [_main_cell(k, t, {}) for t in tps]} for k, zh, rid in MAIN]
    recs = _records(inst)
    clues, days = [], set(t["tp"] for t in tps)
    for cid, zh, codes in CLUES:
        inds = [{"code": c, "label": recs[c][0]["label"], "records": recs[c]} for c in codes if c in recs]
        for i in inds:
            days.update(r["tp"] for r in i["records"])
        own = {c: mine[c] for c in codes if c in mine}
        clues.append({"id": cid, "label": zh, "indicators": inds, "default": [i["code"] for i in inds[:2]],
                      "mark": "患" if own else "观测", "rule": None,
                      "published": {c: published[c] for c in codes if c in published},
                      "thresholds": dict({c: published[c] for c in codes if c in published}, **own),
                      "history": [r for r in rule_history(inst) if r.get("clue") == cid]})
    day_rec = {d: {"symptoms": [], "meds": meds_on_day(d) if meds_on_day else []} for d in sorted(days)}
    for code, zh in (("FEVER", "发热"), ("ARTHRITIS", "关节炎"), ("SPLENOMEGALY", "脾大"), ("HEMORRHAGE", "出血表现"), ("CNS_INVOLVEMENT", "中枢受累")):
        for r in recs.get(code, []):
            if r["value"] == "true":
                day_rec.setdefault(r["tp"], {"symptoms": [], "meds": []})["symptoms"].append(zh)
    body_map = body_bindings.project(clues, inst.app.registry.current.version)
    return {"found": True, "main": main, "clues": clues, "days": day_rec, "note": NOTE, "body_map": body_map,
            "records": len(days), "summary": f"演示病例 · {len(days)} 次记录 · 研究演示，未经临床验证"}


def metric_groups(inst):
    """Bounded observation projection; exact source/code/unit identity, no ledger writes."""
    import hashlib
    import heapq
    from background_read import BackgroundRead
    from display_retention import display_read
    from vitals import _when
    if not hasattr(inst, "_background_read"):
        inst._background_read = BackgroundRead(inst)
    read = display_read(inst._background_read.read(), inst.spec.get("archived_streams"))
    labels = inst.app.registry.current.codes
    groups = {}
    for p in read.payloads.values():
        if p["code"] not in labels:
            continue
        at, day = _when(p, inst.ctx.tz)
        if not day:
            continue
        pair = (p["source_kind"], p["code"], p.get("unit_canonical") or "")
        groups.setdefault(pair, []).append((at.isoformat() if at else day, p["observation_id"], p, day))
    limit = max(2, min(120, 3000 // max(1, len(groups))))
    out = []
    for (source, code, unit), values in sorted(groups.items()):
        gid = "metric-" + hashlib.sha256(json.dumps([source, code, unit]).encode()).hexdigest()[:20]
        label = labels[code].label_zh + " · " + SRC_ZH.get(source, source) + (" · " + unit if unit else "")
        records = []
        for at, oid, p, day in sorted(heapq.nlargest(limit, values, key=lambda r: (r[0], r[1])), key=lambda r: (r[0], r[1])):
            records.append({"tp": day, "at": at, "ref": oid + "@" + str(p["revision"]),
                "value": p["value_canonical"], "unit": unit, "raw": p["value_raw"],
                "raw_unit": p.get("unit_raw") or "", "comparator": p.get("comparator"),
                "bool": p["value_canonical"] in ("true", "false"), "source": SRC_ZH.get(source, source),
                "source_kind": source, "label": label})
        out.append({"id": gid, "label": label, "metric": True, "mark": "观测", "rule": None,
                    "indicators": [{"code": code, "label": label, "records": records}],
                    "default": [code], "thresholds": {}, "published": {}, "history": [],
                    "total": len(values), "shown": len(records)})
    return out, limit


def view(inst, meds_on_day=None) -> dict:
    groups, limit = metric_groups(inst)
    # Only the existing sJIA scene exposes its literature rules; other scenes are observational.
    legacy = _sjia_view(inst, meds_on_day) if inst.sjia and inst.spec.get("kind") == "DEMO" else {}
    if not legacy.get("found"):
        legacy = {"found": True, "main": [], "clues": groups[:3], "days": {}, "body_map": {},
                  "note": "只比较所选记录，不作诊断或因果判断。", "records": 0}
    legacy.update(catalogue=groups, record_limit=limit,
                  summary="各指标展示最近至多 %s 条记录；完整历史仍保留在我的数据中。" % limit)
    return legacy
