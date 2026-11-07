"""星轨 · 竞争性解释（早期测试；FR-S-055 / FR-S-063 / FR-S-084）。

同一组数据（一个时点上星轨现有的那份输入），按不同规则或假设各算一遍，并排列出各自成立与否、依据是哪些数据。
- 规则并排：规则包本来就分别求值 R1 / R2 / R3，这里把每条规则的每个条件摊开：要求、实际值、成立与否、缺什么；
- 假设：只按一条规则、只看变化、换一档灵敏度——在内存里用同一份输入重算，不写星轨、不发提醒、不改卡的设置；
- 文字只说"在这条规则 / 假设下成立与否"，不出现鉴别、诊断或病名（SEM-36）；规则名用规则包登记的简称；
- 结果只用于测试，不是结论；星轨卡上的等级仍以正式计算为准。
"""
from __future__ import annotations

import re

from cards import classify, evaluate_tp, load_card, open_startrack, take_snapshot, values_at
from dynamic import SENSITIVITIES, change_word
from rules import combine_level

LEVEL_ZH = {"ALERT": "关注", "WATCH": "观察", "UNDETERMINED": "无法判定", "NONE": "无", "NOT_EVALUABLE": "算不了（缺数据）"}
RESULT_ZH = {"MET": "成立", "NOT_MET": "不成立", "INDETERMINATE": "缺数据，无法判定", "NOT_APPLICABLE": "前提不满足，不适用"}
OUTCOME_ZH = {"TRUE": "满足", "FALSE": "不满足", "UNKNOWN": "缺数据"}
OP_ZH = {">": "高于", ">=": "不低于", "<": "低于", "<=": "不高于"}
SENS_ZH = {"LOW": "低", "MEDIUM": "中", "HIGH": "高"}
STATUS_ZH = {"NEW": "新时点", "FRESH": "最新", "STALE": "来源已更新"}
DYN_STATUS_ZH = {"TRIGGERED": "超过变化阈值", "NOT_TRIGGERED": "没超过变化阈值", "NOT_EVALUABLE": "算不了"}
DYN_REASON_ZH = {"NO_THRESHOLD": "没有登记阈值", "NO_CURRENT_VALUE": "这个时点没有这一项", "NO_BASELINE": "之前没有可比的值",
                 "INEXACT_VALUE": "值带 > 或 <，不能算变化", "ZERO_BASELINE": "之前的值是 0"}


def _val(d: dict) -> str:
    if d.get("missing"):
        return "没有数据"
    v = d.get("value")
    v = {"true": "是", "false": "否"}.get(v, v)
    return ((d.get("comparator") or "") + str(v)) + ("（有冲突）" if d.get("conflict") else "")


def _line(d: dict, zh) -> dict:
    """一个条件 → {要求, 实际, 结果}。嵌套的"任一 / 其中 k 项"摊成一行说明 + 子项。"""
    if "any" in d:
        return {"need": "以下任一项", "got": "", "outcome": OUTCOME_ZH[d["outcome"]], "items": [_line(x, zh) for x in d["any"]]}
    if "items" in d:
        return {"need": f"以下 {len(d['items'])} 项中至少 {d['k_of']} 项", "got": "", "outcome": OUTCOME_ZH[d["outcome"]],
                "items": [_line(x, zh) for x in d["items"]]}
    if "flag" in d:
        return {"need": f"{zh(d['flag'])}：是", "got": _val(d), "outcome": OUTCOME_ZH[d["outcome"]], "code": d["flag"]}
    return {"need": f"{zh(d['code'])} {OP_ZH.get(d['op'], d['op'])} {d['threshold']} {d['unit']}", "got": _val(d) + (
        " " + d["unit"] if not d.get("missing") and d.get("value") is not None else ""), "outcome": OUTCOME_ZH[d["outcome"]],
        "code": d["code"]}


def _rule_col(rid: str, r: dict, short: str, zh) -> dict:
    col = {"id": rid, "name": short, "result": r["result"], "result_zh": RESULT_ZH[r["result"]],
           "expert_review": "待专家核实" if r.get("expert_review") == "PENDING" else r.get("expert_review"),
           "missing": [zh(c) for c in r.get("missing") or []], "groups": []}
    col["groups"].append({"zh": "前提", "outcome": OUTCOME_ZH[r["gate"]["outcome"]], "lines": [_line(x, zh) for x in r["gate"]["items"]]})
    if "required" in r:
        col["groups"].append({"zh": "必需", "lines": [_line(x, zh) for x in r["required"]]})
        col["groups"].append({"zh": f"另需 {r['additional_min']} 项（满足 {r['additional_true']} 项，缺数据 {r['additional_unknown']} 项）",
                              "lines": [_line(x, zh) for x in r["additional"]]})
    elif "criteria" in r:
        col["groups"].append({"zh": f"{len(r['criteria'])} 项中需 {r['min_met']} 项（满足 {r['met_count']} 项，缺数据 {r['unknown_count']} 项）",
                              "lines": [_line(x, zh) for x in r["criteria"]]})
    else:
        col["groups"].append({"zh": f"评分 {r['score'] if r.get('score') is not None else '算不了（缺数据）'}，"
                                    f"需要 {OP_ZH.get(r['cutoff']['op'], r['cutoff']['op'])} {r['cutoff']['value']}",
                              "lines": [{"need": f"{zh(t['input'])} × {t['coef']}", "got": _val(t),
                                         "outcome": "可用" if t["usable"] else "缺数据", "code": t["input"]} for t in r["terms"]]})
    return col


def _dyn_col(dyn: dict) -> dict:
    lines = []
    for i in dyn["indicators"]:
        dirz = change_word(i["bad_direction"], i.get("measure"))
        role = '核心' if i['role'] == 'CORE' else '一般'
        if i.get("measure") in ("APPEAR", "PERSIST"):
            need = f"{i['label_zh']} {dirz}（{role}）"
        elif i.get("effective_threshold") is not None:
            need = f"{i['label_zh']} {dirz}超过 {_pct(i['effective_threshold'])}（{role}）"
        else:
            need = f"{i['label_zh']}（没有登记阈值）"
        got = (i.get("change") or "") + (f"（对比 {i['base_tp']}）" if i.get("base_tp") else "")
        lines.append({"need": need, "got": got or DYN_REASON_ZH.get(i.get("reason"), i.get("reason") or ""),
                      "outcome": DYN_STATUS_ZH.get(i["status"], i["status"]), "code": i["code"]})
    return {"id": "DYNAMIC", "name": "变化（与之前的时点比）", "result": dyn["level"], "result_zh": LEVEL_ZH.get(dyn["level"], dyn["level"]),
            "expert_review": "阈值是演示占位值，不出自文献", "missing": [], "groups": [{"zh": "各项变化", "lines": lines}]}


def _pct(x) -> str:
    try:
        return format(float(x) * 100, "g") + "%"
    except (TypeError, ValueError):
        return str(x)


def explain(inst, tp: str, *, read=None) -> dict:
    """Explain unchanged rules, optionally reusing the caller's complete read."""
    app = inst.app
    track = open_startrack(inst.ctx)
    try:
        card = inst.card(track)
        snap = take_snapshot(track, inst.ctx, card, read=read)
        status, latest = classify(track, snap, card)
        tps = sorted(snap.tps)
        if tp not in snap.tps:
            return {"tp": tp, "found": False, "tps": tps}
        cache = {d: values_at(card, obs) for d, obs in snap.tps.items()}
        level, res = evaluate_tp(card, tp, cache)
        formal = latest.get(tp)
    finally:
        track.close()
    zh = lambda c: card.labels.get(c, c)  # noqa: E731
    short = {rid: r.get("short_zh", rid) for rid, r in app.rulepack["rules"].items()}
    cols = [_rule_col(rid, res["rules"][rid], short.get(rid, rid), zh) for rid in card.rulepack.rules] + [_dyn_col(res["dynamic"])]
    combine = card.rulepack.combine
    quiet = {"level": "NONE", "indicators": []}
    neutral = {rid: {"result": "NOT_MET", "missing": []} for rid in card.rulepack.rules}
    hyp = []
    for rid in card.rulepack.rules:  # 只按这一条规则：成立 → 关注，缺数据 → 无法判定，否则无
        lv, _ = combine_level(res["rules"], quiet, {"alert_on_met": [rid], "undetermined_on_indeterminate": [rid]})
        hyp.append({"id": rid, "zh": f"只按 {short.get(rid, rid)}", "level": lv, "level_zh": LEVEL_ZH[lv]})
    lv, _ = combine_level(neutral, res["dynamic"], {"alert_on_met": [], "undetermined_on_indeterminate": []})
    hyp.append({"id": "DYNAMIC", "zh": "只看变化（灵敏度" + SENS_ZH[card.dynamic.sensitivity] + "）", "level": lv, "level_zh": LEVEL_ZH[lv]})
    for s in SENSITIVITIES:
        alt = load_card(app.registry, inst.ctx, app.rulepack, card.definition["dynamic"], s)  # 带上预警设置
        lv, _ = evaluate_tp(alt, tp, {d: values_at(alt, obs) for d, obs in snap.tps.items()})
        hyp.append({"id": "SENS-" + s, "zh": f"规则全用 + 变化灵敏度{SENS_ZH[s]}" + ("（现在的设置）" if s == card.dynamic.sensitivity else ""),
                    "level": lv, "level_zh": LEVEL_ZH[lv], "current": s == card.dynamic.sensitivity})
    used = sorted({o.code for o in snap.tps[tp]})
    return {"tp": tp, "found": True, "tps": tps, "status": status.get(tp), "status_zh": STATUS_ZH.get(status.get(tp), status.get(tp)),
            "level": level, "level_zh": LEVEL_ZH[level],
            "formal": {"run_id": formal["run_id"], "level": formal["level"], "level_zh": LEVEL_ZH.get(formal["level"], formal["level"])}
            if formal else None,
            "columns": cols, "hypotheses": hyp, "explain": fixed_explain(cols, LEVEL_ZH[level]), "data": [zh(c) for c in used],
            "stability": stability(hyp, cols, level),
            "next": next_steps(res, cols, zh, short, stability(hyp, cols, level), level),
            "note": "同一组数据按不同规则或假设各算一遍，只说各自成立与否；只用于测试，不是结论。星轨卡上的等级以正式计算为准。"}


def _hname(zh: str) -> str:
    return re.sub(r"（R\d+）", "", zh.replace("（现在的设置）", "")).replace("规则全用 + ", "三套标准都用、")


def stability(hyp: list, cols: list, level: str) -> dict:
    """小结的客观部分：换几种算法再算，等级变不变；还缺几项数据。只用已经算出的结果拼句子。"""
    alt = [h for h in hyp if not h.get("current")]
    diff = [h for h in alt if h["level"] != level]
    miss = []
    for c in cols:
        miss += [m for m in c["missing"] if m not in miss]
    for g in cols[-1]["groups"]:
        miss += [ln["need"].split(" ")[0] for ln in g["lines"] if ln["outcome"] == "算不了" and ln["need"].split(" ")[0] not in miss]
    lv = LEVEL_ZH[level]
    real = [h for h in diff if h["level"] != "UNDETERMINED"]  # 只是缺数据算不了的，不算结论相反
    if diff and not real:
        first = (f"换 {len(alt)} 种算法再算，有 {len(diff)} 种因为缺数据算不了（" + "、".join(_hname(h["zh"]) for h in diff)
                 + f"），其余都还是“{lv}”，没有算出相反的结论，基本稳。")
    elif diff:
        first = (f"换 {len(alt)} 种算法再算，有 {len(diff)} 种不再是“{lv}”："
                 + "、".join(f"{_hname(h['zh'])}是{h['level_zh']}" if h["level"] != "UNDETERMINED" else f"{_hname(h['zh'])}无法判定" for h in diff)
                 + "。这个等级要靠特定的算法才成立，还不稳。")
    else:
        first = f"换 {len(alt)} 种算法再算，结果都还是“{lv}”，这个等级不靠某一套算法撑着，比较稳。"
    text = [first] + ([f"还缺 {len(miss)} 项数据，补上后再请医生判断。"] if miss else [])
    return {"stable": not real, "alt": len(alt), "changed": len(diff), "missing": len(miss), "text": text,
            "rows": [{"zh": _hname(h["zh"]), "level": h["level"], "level_zh": h["level_zh"], "changed": h["level"] != level} for h in alt]}


def _flat(lines: list) -> list:
    out = []
    for ln in lines:
        out.append(ln)
        out += _flat(ln.get("items") or [])
    return out


def fixed_explain(cols: list, level_zh: str) -> list:
    """程序拼的解释：每句只用列里已有的事实，带上出自哪一列。千问的版本写好前先显示它，千问核对不过时也退回它。"""
    out = []
    by = {"MET": [], "INDETERMINATE": [], "NOT_MET": []}
    for c in cols[:-1]:
        by.get(c["result"], by["NOT_MET"]).append(c["name"])
    parts = [f"{'、'.join(by['MET'])} 达到界值" if by["MET"] else "",
             f"{'、'.join(by['INDETERMINATE'])} 缺数据算不了" if by["INDETERMINATE"] else "",
             f"{'、'.join(by['NOT_MET'])} 未达到" if by["NOT_MET"] else ""]
    out.append({"text": f"三套标准结论不一样：{'；'.join(p for p in parts if p)}。合起来的关注等级是“{level_zh}”。",
                "cols": [c["id"] for c in cols[:-1]]})
    for c in cols[:-1]:
        lines = [ln for g in c["groups"] for ln in _flat(g["lines"])]
        if c["result"] == "INDETERMINATE":
            head = next((g["zh"] for g in c["groups"] if "项" in g["zh"] and "需" in g["zh"]), "")
            why = (head + "，" if head else "") + "缺 " + "、".join(c["missing"][:4]) + ("等" if len(c["missing"]) > 4 else "")
        elif any(g["zh"].startswith("评分") for g in c["groups"]):
            why = next(g["zh"] for g in c["groups"] if g["zh"].startswith("评分"))
        else:
            met = [f"{ln['need']}（{ln['got']}）" for ln in lines if ln.get("code") and ln["outcome"] == "满足"
                   and not ln["need"].endswith("：是")]
            head = next((g["zh"] for g in c["groups"] if g["zh"].startswith("另需")), "")
            why = "；".join(([head] if head else []) + met[:3])
        out.append({"text": f"{c['name']}{c['result_zh']}：{why}。", "cols": [c["id"]]})
    dyn = cols[-1]
    lines = [ln for g in dyn["groups"] for ln in g["lines"]]
    hit = [f"{ln['need'].split(' ')[0]} {ln['got'].split('（')[0]}" for ln in lines if ln["outcome"] == "超过变化阈值"]
    gone = [ln["need"].split(" ")[0] for ln in lines if ln["outcome"] == "算不了"]
    if hit:
        out.append({"text": "和上一次比，超过变化阈值的有：" + "、".join(hit) + "。", "cols": ["DYNAMIC"]})
    elif dyn["result"] != "NOT_EVALUABLE":
        out.append({"text": "和上一次比，没有指标超过变化阈值。", "cols": ["DYNAMIC"]})
    miss = []
    for c in cols[:-1]:
        miss += [m for m in c["missing"] if m not in miss]
    miss += [m for m in gone if m not in miss]
    if miss:
        out.append({"text": "要让结论更确定，还缺：" + "、".join(miss) + "。缺的不当作正常。",
                    "cols": [c["id"] for c in cols if c["missing"]] + (["DYNAMIC"] if gone else [])})
    return out


def tps_of(inst) -> list:
    track = open_startrack(inst.ctx)
    try:
        return sorted(take_snapshot(track, inst.ctx, inst.card(track)).tps)
    finally:
        track.close()

SELF_CODES = {"TEMP", "FEVER", "HEMORRHAGE"}  # 在家自己能记的
DOCTOR_CODES = {"SPLENOMEGALY", "CNS_INVOLVEMENT", "ARTHRITIS", "LAB_NOT_OTHERWISE_EXPLAINED", "SJIA_KNOWN_OR_SUSPECTED"}  # 要医生查体或判断的
NEXT_NOTE = "这是按算法分歧整理的下一步，不是医嘱，怎么做听医生的。"


def next_steps(res: dict, cols: list, zh, short: dict, sb: dict, level: str) -> dict:
    """下一步：只从竞争性解释里已经算出的分歧推出来（哪套缺什么、哪些变化超阈值、稳不稳），程序列候选，千问只挑和排。"""
    acts, ask = [], []
    lab, self_rec, doc = {}, [], []
    short = {k: re.sub(r"（R\d+）", "", v) for k, v in short.items()}
    for rid, r in res["rules"].items():
        name = short.get(rid, rid)
        if r["result"] != "INDETERMINATE":
            continue
        for c in r.get("missing") or []:
            (self_rec if c in SELF_CODES else doc if c in DOCTOR_CODES else lab.setdefault(rid, [])).append(c)
    dyn = res["dynamic"]["indicators"]
    for i in dyn:
        if i["status"] == "NOT_EVALUABLE" and i.get("reason") == "NO_CURRENT_VALUE" and i["code"] in SELF_CODES:
            self_rec.append(i["code"])
    self_rec = list(dict.fromkeys(self_rec))
    doc = list(dict.fromkeys(doc))
    for rid, codes in lab.items():
        r, name = res["rules"][rid], short.get(rid, rid)
        if "criteria" in r:
            gap = f"已满足 {r['met_count']} 项，至少还要再满足 {r['min_met'] - r['met_count']} 项才成立"
        elif "additional" in r:
            gap = f"另需项已满足 {r['additional_true']} 项，至少还要再满足 {r['additional_min'] - r['additional_true']} 项才成立"
        else:
            gap = "评分里这几项没有数据，算不出分"
        names = "、".join(zh(c) for c in codes)
        acts.append({"id": f"LAB-{rid}", "kind": "lab", "title": "补检测：" + names,
                     "text": f"{name}缺这几项算不了；{gap}。补上后就能判定。", "cols": [rid]})
    hot = [i for i in dyn if i["status"] == "TRIGGERED"]
    if hot:
        hot.sort(key=lambda i: (i["role"] != "CORE", i["label_zh"]))
        items = "、".join(i["label_zh"] + (f"（{i['change']}）" if i.get("measure") not in ("APPEAR", "PERSIST") else change_word(i["bad_direction"], i.get("measure"))) for i in hot)
        labs = [i["label_zh"] for i in hot if i.get("measure") not in ("APPEAR", "PERSIST")]
        acts.append({"id": "WATCH", "kind": "watch", "title": ("下次化验重点看：" + "、".join(labs[:4])) if labs else "接着观察：" + "、".join(i["label_zh"] for i in hot),
                     "text": f"这几项和上次比超过了变化阈值：{items}。下次化验看它们还在不在继续变。", "cols": ["DYNAMIC"]})
    if self_rec:
        acts.append({"id": "SELF", "kind": "self", "title": "自己记：" + "、".join(zh(c) for c in self_rec),
                     "text": "这几项在家就能记，记下来能让算不了的规则和变化算得出来。", "cols": [c["id"] for c in cols if any(zh(x) in c["missing"] for x in self_rec)] or ["DYNAMIC"]})
    met = [short.get(rid, rid) for rid, r in res["rules"].items() if r["result"] == "MET"]
    undet = [short.get(rid, rid) for rid, r in res["rules"].items() if r["result"] == "INDETERMINATE"]
    if level in ("ALERT", "WATCH") or not sb["stable"]:
        if hot and not met:
            ask.append(f"三套标准都还没达到或缺数据，但和上次比{hot[0]['label_zh']}等变化已经超过阈值，这个变化需要怎么看？")
        if met and undet:
            ask.append(f"{'、'.join(met)}已经成立，{'、'.join(undet)}因为缺数据算不了，要不要补查缺的项？")
        if doc:
            ask.append("能不能检查一下" + "、".join(zh(c) for c in doc) + "？现在没有记录，要医生查体或判断。")
        if not sb["stable"] and len(ask) < 3:
            ask.append("换一种算法等级就会变，现在这个结论该怎么看，多久再查一次合适？")
        ask = ask[:3]
        acts.insert(0, {"id": "ASK", "kind": "doctor", "title": "带去问医生（" + str(len(ask)) + " 个问题）",
                        "text": "几套算法在这里说法不一样，值得当面问清楚。", "cols": [], "ask": ask})
    return {"actions": acts, "ask": ask, "note": NEXT_NOTE}

