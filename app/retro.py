"""星轨 · 回溯式重计算（早期测试；FR-S-053 / FR-S-084）。

用现在的方法（规则包、变化阈值、灵敏度），或换一种方法，把过去的时点重算一遍；新旧结果并排，旧结果保留。
- 计算只追加：每次重算是一条新的计算记录，旧的结果、所用数据版本都还在（证据图谱里能追）；
- "按现在的方法重算"：同一份输入、同一个方法，结果应逐字一致（比结果指纹），这本身就是一次回溯核对；
- "换一种方法"：改的是 sJIA 关注卡的灵敏度设置（卡的正式设置，之后的计算都按它），由我确认后才改；
- 提醒照星轨原有规则：只看最新时点的等级变化，不会因为重算过去的时点补发旧提醒。
"""
from __future__ import annotations

import json
import re

from cards import open_startrack, recompute, take_snapshot
from dynamic import SENSITIVITIES

LEVEL_ZH = {"ALERT": "关注", "WATCH": "观察", "UNDETERMINED": "无法判定", "NONE": "无"}
TRIGGER_ZH = {"SYNC": "数据到达后计算", "AUTO_UPDATE": "来源更新后自动更新", "RECOMPUTE": "重新计算"}
SENS_ZH = {"LOW": "低", "MEDIUM": "中", "HIGH": "高"}


def _method(defn: dict) -> dict:
    rp, dy = defn.get("rulepack") or {}, defn.get("dynamic") or {}
    s = defn.get("sensitivity")
    return {"rulepack": rp.get("version"), "dynamic": dy.get("version"), "sensitivity": s,
            "engine": defn.get("engine_version"),
            "zh": f"规则包 {rp.get('version')} · 变化阈值 {dy.get('version')}"
                  f"{'（演示占位值）' if dy.get('provenance') == 'PLACEHOLDER_NOT_LITERATURE' else ''} · 灵敏度{SENS_ZH.get(s, s)}"}


def history(inst) -> dict:
    track = open_startrack(inst.ctx)
    try:
        card = inst.card(track)
        tps = sorted(take_snapshot(track, inst.ctx, card).tps)
        defs = {cid: json.loads(d) for cid, d in track.execute("SELECT card_def_id, definition FROM card_def WHERE card_id = ?",
                                                                (card.card_id,))}
        rows = track.execute("SELECT rt.tp_date, rt.run_id, r.trigger, r.started_at, r.card_def_id, rt.status, rt.level, "
                             "rt.result_sha256 FROM run_tp rt JOIN run r USING (run_id) JOIN card_def c ON c.card_def_id = r.card_def_id "
                             "WHERE c.card_id = ? ORDER BY rt.run_id", (card.card_id,)).fetchall()
    finally:
        track.close()
    methods = {cid: dict(_method(d), current=cid == card.card_def_id) for cid, d in defs.items()}
    by_tp, last_cid = {}, {}
    for tp, rid, trig, at, cid, status, level, sha in rows:
        zh = "换方法后重算" if tp in last_cid and last_cid[tp] != cid else TRIGGER_ZH.get(trig, trig)
        last_cid[tp] = cid
        by_tp.setdefault(tp, []).append({"run_id": rid, "trigger": trig, "trigger_zh": zh, "at": at,
                                         "method": methods[cid]["zh"], "current_method": cid == card.card_def_id,
                                         "status": status, "level": level, "level_zh": LEVEL_ZH.get(level, level),
                                         "sha": sha})
    out = []
    for tp in sorted(set(by_tp) | set(tps)):
        runs = by_tp.get(tp, [])
        latest, prev = (runs[-1] if runs else None), (runs[-2] if len(runs) > 1 else None)
        if latest and prev:
            same = "逐字一致" if latest["sha"] == prev["sha"] else (
                "等级不变，依据有变化" if latest["level"] == prev["level"] else f"等级变了：{prev['level_zh']} → {latest['level_zh']}")
        else:
            same = None
        out.append({"tp": tp, "runs": runs, "latest": latest, "prev": prev, "compare": same,
                    "method_changed": bool(latest and prev and latest["method"] != prev["method"])})
    return {"method": methods[card.card_def_id] if card.card_def_id in methods else dict(_method(card.definition), current=True),
            "sensitivity": card.dynamic.sensitivity, "sensitivities": [{"id": s, "zh": SENS_ZH[s]} for s in SENSITIVITIES],
            "tps": out, "note": "每次重算都追加一条计算记录，旧结果保留；提醒只看最新时点，重算过去的时点不会补发旧提醒。"}


def rerun(inst) -> dict:
    """按现在的方法，把全部过去时点重算一遍（不管是否最新）。"""
    track = open_startrack(inst.ctx)
    try:
        card = inst.card(track)
        tps = sorted(take_snapshot(track, inst.ctx, card).tps)
        if not tps:
            return {"evaluated": [], "run_id": None}
        r = recompute(track, inst.ctx, card, now=inst.now(), notifiers=inst.app.notifiers, tps=tps)
        return {"evaluated": r["evaluated"], "run_id": r["run_id"]}
    finally:
        track.close()


# ----------------------------------------------------------------------------- 时间分叉（产品负责人 2026-10-14 批准 R13）
# 同一段时间换一种方法从头再算，结论哪天开始不一样。每个时点都用竞争性解释的内存计算（不写库、不发提醒），
# 按“方法”串成一条线：正式线 = 现在的方法；分叉 = 只按某一套标准 / 只看变化 / 换一档灵敏度。
FLAG = ("ALERT", "WATCH")
NA = ("UNDETERMINED", "NOT_EVALUABLE")
ORDER = {"LATE": 0, "EARLY": 0, "NEVER": 1, "DIFF": 2, "NA": 3, "SAME": 9}


def _days(a: str, b: str) -> int:
    from datetime import date  # noqa: PLC0415
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def _first(series: list) -> str | None:
    return next((p["tp"] for p in series if p["level"] in FLAG), None)


def _verdict(series: list, formal: list) -> dict:
    """这条分叉和正式线比：SAME 一样 / LATE 晚 N 天 / EARLY 早 N 天 / NEVER 一直没提示 / NA 一直算不了 / DIFF 提示同一天、之后不一样。"""
    if [p["level"] for p in series] == [p["level"] for p in formal]:
        return {"state": "SAME", "zh": "和现在一样"}
    if all(p["level"] in NA for p in series):
        return {"state": "NA", "zh": "一直算不了"}
    fb, ff = _first(series), _first(formal)
    if ff and not fb:
        return {"state": "NEVER", "zh": "一直没提示"}
    if fb and not ff:
        return {"state": "EARLY", "zh": f"{fb[5:]} 就提示", "first": fb}
    if fb != ff:
        n = _days(ff, fb)
        return {"state": "LATE" if n > 0 else "EARLY", "days": abs(n), "first": fb,
                "zh": ("晚 " if n > 0 else "早 ") + f"{abs(n)} 天"}
    diff = sum(1 for a, b in zip(series, formal) if a["level"] != b["level"])
    return {"state": "DIFF", "zh": f"有 {diff} 个时点不一样", "first": fb}


def _hits(col: dict) -> list:
    return [f"{ln['need'].split(' ')[0]} {ln['got'].split('（')[0]}" for g in col["groups"] for ln in g["lines"]
            if ln["outcome"] == "超过变化阈值"]


def _status_map(c: dict) -> dict:
    import compete_ai  # noqa: PLC0415
    return compete_ai.facts_of(c)[1]


def branches(inst) -> dict:
    import compete  # noqa: PLC0415
    tps = compete.tps_of(inst)
    per = [compete.explain(inst, tp) for tp in tps]
    per = [p for p in per if p.get("found")]
    if not per:
        return {"found": False, "tp": "RETRO"}
    meth = history(inst)["method"]
    last = per[-1]
    names = {c["id"]: re.sub(r"（.*?）", "", c["name"]).replace("变化与之前的时点比", "变化").strip() for c in last["columns"]}
    formal = [{"tp": p["tp"], "level": p["level"], "level_zh": p["level_zh"]} for p in per]
    ids = [h["id"] for h in last["hypotheses"] if not h.get("current")]
    hz = {h["id"]: re.sub(r"（.*?）", "", h["zh"]).replace("规则全用 + 变化", "") for h in last["hypotheses"]}
    lanes = []
    for bid in ids:
        series = []
        for p in per:
            h = next(x for x in p["hypotheses"] if x["id"] == bid)
            series.append({"tp": p["tp"], "level": h["level"], "level_zh": h["level_zh"]})
        lanes.append({"id": bid, "zh": hz[bid], "series": series, "verdict": _verdict(series, formal)})
    ff = _first(formal)
    # 解释用的事实（程序拼句子；千问只能在这些事实里改写）
    span = f"{per[0]['tp']} 至 {per[-1]['tp']}" if len(per) > 1 else per[0]["tp"]
    ex, facts = [], []
    fact = lambda text, col=None: facts.append((text, col))  # noqa: E731
    fact(f"现在的方法：{meth['zh']}；一共 {len(per)} 个时点（{span}）")
    fact("现在的方法 每个时点：" + "，".join(f"{p['tp']} {p['level_zh']}" for p in formal)
         + (f"；第一次提示在 {ff}" if ff else "；一直没有提示"))
    for ln in lanes:
        v = ln["verdict"]
        fact(f"{ln['zh']} 每个时点：" + "，".join(f"{p['tp']} {p['level_zh']}" for p in ln["series"]) + f"；和现在的方法比：{v['zh']}",
             ln["id"] if ln["id"] in names else None)
    late = [ln for ln in lanes if ln["verdict"]["state"] == "LATE"]
    early = [ln for ln in lanes if ln["verdict"]["state"] == "EARLY"]
    na = [ln for ln in lanes if ln["verdict"]["state"] == "NA"]
    never = [ln for ln in lanes if ln["verdict"]["state"] == "NEVER"]
    same = [ln for ln in lanes if ln["verdict"]["state"] == "SAME"]
    cols = lambda ls: [x["id"] for x in ls if x["id"] in names]  # noqa: E731
    if late:
        d = late[0]["verdict"]
        grp = [x for x in late if x["verdict"].get("first") == d["first"]]
        who = "或".join(x["zh"] if i == 0 else " " * x["zh"].replace("只按 ", "")[:1].isascii() + x["zh"].replace("只按 ", "") for i, x in enumerate(grp))
        ex.append({"text": f"按现在的方法，{ff} 第一次进入{formal[[p['tp'] for p in formal].index(ff)]['level_zh']}；"
                           f"{who}算，要到 {d['first']} 才提示，晚 {d['days']} 天。", "cols": cols(grp)})
    for x in early:
        d = x["verdict"]
        ex.append({"text": f"{x['zh']}算，{d['first']} 就会提示" + (f"，比现在的方法早 {d['days']} 天。" if d.get("days") else "，现在的方法一直没有提示。"),
                   "cols": cols([x])})
    dyn = next((x for x in lanes if x["id"] == "DYNAMIC"), None)
    if late and ff and dyn and _first(dyn["series"]) == ff:
        at = per[[p["tp"] for p in per].index(ff)]
        hit = _hits(at["columns"][-1])
        rules_flag = [c for c in at["columns"][:-1] if c["result"] == "MET"]
        if hit and not rules_flag:
            fact(f"{ff} 和上一次比，超过变化阈值的：" + "、".join(hit), "DYNAMIC")
            fact(f"{ff} 三套标准：" + "，".join(f"{names[c['id']]} {c['result_zh']}" for c in at["columns"][:-1]))
            ex.append({"text": f"早的这 {late[0]['verdict']['days']} 天来自变化规则：{ff} 和上一次比，"
                               + "、".join(h.split(" ")[0] for h in hit[:2]) + ("等" if len(hit) > 2 else "")
                               + "变化超过了阈值，而三套标准那时都还没达到。", "cols": ["DYNAMIC"]})
    for x in never:
        ex.append({"text": f"{x['zh']}算，{len(per)} 个时点都没有提示。", "cols": cols([x])})
    for x in na:
        miss = next((c["missing"] for c in last["columns"] if c["id"] == x["id"]), [])
        if miss:
            fact(f"{names.get(x['id'], x['zh'])} 缺数据（没有记录）：" + "、".join(miss), x["id"] if x["id"] in names else None)
        ex.append({"text": f"{x['zh']}，{len(per)} 个时点都缺数据算不了，看不出它会在哪天提示。", "cols": cols([x])})
    sens = [x for x in lanes if x["id"].startswith("SENS-")]
    if sens and all(x["verdict"]["state"] == "SAME" for x in sens):
        ex.append({"text": f"变化灵敏度调低、调高，{len(per)} 个时点的结论都和现在的方法一样。", "cols": []})
    if not ex:
        ex.append({"text": f"换 {len(lanes)} 种方法把 {len(per)} 个时点重算一遍，结论都和现在的方法一样。", "cols": []})
    # 小结（客观部分）
    parts = []
    for grp, word in ((late, "比现在晚"), (early, "比现在早")):
        by = {}
        for x in grp:
            by.setdefault(x["verdict"].get("days"), []).append(x)
        parts += [f"{len(v)} 种{word} {k} 天发现" if k else f"{len(v)} 种{word}发现" for k, v in by.items()]
    if never:
        parts.append(f"{len(never)} 种一直没提示")
    if na:
        parts.append(f"{len(na)} 种一直算不了")
    diff = [x for x in lanes if x["verdict"]["state"] == "DIFF"]
    if diff:
        parts.append(f"{len(diff)} 种提示同一天、之后不一样")
    if same:
        parts.append(f"{len(same)} 种完全一样")
    text = [f"换 {len(lanes)} 种方法把 {len(per)} 个时点重算一遍：" + "，".join(parts) + "。"]
    placeholder = "演示占位值" in meth["zh"]
    if late and dyn and _first(dyn["series"]) == ff and ex[1:2] and "变化规则" in ex[1]["text"]:
        text.append(f"提前的 {late[0]['verdict']['days']} 天全靠变化规则" + ("，而它的阈值还是演示占位值，没有经过验证。" if placeholder else "。"))
        if placeholder:
            fact("变化阈值是演示占位值，没有经过验证", "DYNAMIC")
    fact("换方法回头再算：" + "".join(text))
    rows = [{"zh": x["zh"], "level": x["verdict"]["state"], "level_zh": x["verdict"]["zh"], "changed": x["verdict"]["state"] != "SAME"} for x in lanes]
    # 下一步：只从分叉里推（程序列候选，千问只挑和排）
    acts, ask = [], []
    if late or early:
        a = (late or early)[0]["verdict"]
        if ex[1:2] and "变化规则" in ex[1]["text"]:
            ask.append(f"变化规则比标准早 {a['days']} 天提示，这几天的变化需要怎么看？")
        else:
            ask.append(f"换一种方法，提示的时间会差 {a['days']} 天，现在用的方法合适吗？")
    if na:
        ask.append("、".join(names.get(x["id"], x["zh"]) for x in na) + " 一直缺数据算不了，缺的这几项要不要查？")
    if ask:
        acts.append({"id": "ASK", "kind": "doctor", "title": f"带去问医生（{len(ask)} 个问题）",
                     "text": "几种方法在时间上说法不一样，值得当面问清楚。", "cols": [], "ask": ask})
    for x in na:
        miss = next((c["missing"] for c in last["columns"] if c["id"] == x["id"]), [])
        if miss:
            acts.append({"id": "LAB-" + x["id"], "kind": "lab", "title": "补检测：" + "、".join(miss[:2]) + (f"等 {len(miss)} 项" if len(miss) > 2 else ""),
                         "text": f"{names.get(x['id'], x['zh'])}缺这几项一直算不了：{'、'.join(miss)}。补上后这条线才画得出来。", "cols": [x["id"]]})
    acts.append({"id": "SET", "kind": "set", "title": "想换正式方法：去预警设置改，改完自动回溯重算，旧结果保留",
                 "text": "这里的分叉都是试算，不改正式结果。要换方法，在预警设置里改灵敏度或指标，确认后星轨按新方法把全部时点重算一遍，旧结果保留。", "cols": []})
    for i, a in enumerate(acts):
        fact(f"候选动作 A{i + 1}：{a['title']}。{a['text']}" + ("问题：" + "；".join(a["ask"]) if a.get("ask") else ""), (a.get("cols") or [None])[0])
    # 图：正式线 + 最多 2 条有分歧的线（先差得多的，再算不了的）；一样的收起
    shown = sorted([x for x in lanes if x["verdict"]["state"] != "SAME"], key=lambda x: (ORDER[x["verdict"]["state"]], -(x["verdict"].get("days") or 0)))
    merged = []
    for x in shown:  # 每个时点都一样的分叉合成一条
        m = next((y for y in merged if [p["level"] for p in y["series"]] == [p["level"] for p in x["series"]]), None)
        if m:
            m["zh"] += "、" + x["zh"].replace("只按 ", "")
            m["ids"].append(x["id"])
        else:
            merged.append(dict(x, ids=[x["id"]]))
    columns = [{"id": c["id"], "name": names[c["id"]], "result": next((x["verdict"]["state"] for x in lanes if x["id"] == c["id"]), "SAME"),
                "verdict": next((x["verdict"] for x in lanes if x["id"] == c["id"]), {"state": "SAME", "zh": "和现在一样"}),
                "series": next((x["series"] for x in lanes if x["id"] == c["id"]), formal)} for c in last["columns"]]
    return {"found": True, "kind": "retro", "tp": "RETRO", "span": span, "level_zh": "", "method": meth["zh"],
            "tps": [p["tp"] for p in per], "formal": formal, "first": ff, "lanes": lanes,
            "graph": {"main": formal, "lanes": merged[:2], "more": len(merged) - 2 if len(merged) > 2 else 0,
                      "same": [x["zh"] for x in same]},
            "columns": columns, "explain": ex, "facts": facts, "status_map": _status_map(last), "placeholder": placeholder,
            "stability": {"text": text, "alt": len(lanes), "rows": rows, "stable": True,
                          "how": "只用其中一套标准，或者把“变化”的灵敏度调高、调低，把每个时点都重算一遍，看第一次提示落在哪天。"},
            "next": {"actions": acts, "ask": ask, "note": "这是按方法分歧整理的下一步，不是医嘱，怎么做听医生的。"},
            "note": "同一段数据换一种方法回头再算，只说哪天开始不一样；只用于测试，不是结论。星轨卡上的等级以正式计算为准。"}
