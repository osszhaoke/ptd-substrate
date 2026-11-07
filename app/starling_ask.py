"""问星灵（产品负责人 2026-10-14）：右下角浮窗，问 PTDS（星炬 / 星轨 / 星簇）里的任何记录，带语义围栏。

- 只在我点了“问”以后才问本机 Qwen，一次只答一个（服务端也只放一个进来）。署名“星灵（Qwen 3.5 9B本地）发出”。
- 程序先分流，不经过模型：
  · 诊断、用药、就医、好坏判断 → 挡下，固定一句“不在 PTDS 的记录里，星灵不回答”，并写明原因；
  · 想让星灵替我做事（导入数据、加状态、授权…）→ 暂不支持自动创建，指到现有页面；
  · 问具体数值 → 程序直接查星炬里的正式记录作答，标“程序查的记录”，数值不交给星灵（HR-42）；
  · 问题里没有任何 PTDS 的对象 → 挡下。
- 进了门的问题：按问题落到星炬 / 星轨 / 星簇，只拼那一块的记录事实（不含健康数值，送出前逐行过 check_context），
  Qwen 必须回答 in_scope；写了 false 就照实说星灵判断不在范围内。
- 核对：数字必须出现在记录或问题里；不写诊断、建议、好坏判断；授权编号必须在记录里。没过就带着原因让它重写一次，
  再不过就照实说没采用，把没过的句子摆出来。不替换、不兜底（产品负责人 2026-10-14：翻车就翻车）。
- 每次问答记在 <实例>/starling/sessions.jsonl。
"""
from __future__ import annotations

import json
import re
import threading
import time
import uuid
from pathlib import Path

import evidence_graph
import starling
import starling_page
import starling_history

AREA_ZH = {"torch": "星炬 · 掌握数据", "track": "星轨 · 理解状态", "cluster": "星簇 · 可信协作", "page": "这一页"}
NAV = dict(starling.NAV, eng="增加我的状态", guard="数据导航", adv="状态实验室", alerts="状态通知")
AREA_GO = {"torch": ["sources", "data", "graph"], "track": ["wall", "alerts", "adv"], "cluster": ["records", "grants"]}
ATTEMPTS = 2
BUSY = threading.Lock()

# 围栏一：不回答的（先于一切）
MEDICAL = re.compile(r"吃什么药|用药|药量|剂量|服用|吃药|停药|换药|治疗|怎么治|治得好|要不要去医院|去医院|就医|看急诊|挂号|"
                     r"严重吗|危险吗|要紧吗|是不是得了|得了什么|什么病|诊断|确诊|会不会死|预后|能活")
JUDGE = re.compile(r"正常吗|正不正常|偏高吗|偏低吗|高不高|低不低|好不好|好吗|健康吗|有没有问题|有问题吗|该怎么办|怎么办")
# 围栏二：想让星灵替我做事 → 指路（产品负责人 2026-10-14 06:33：暂不支持自动创建，引导到现有页面）
ACTIONS = [
    (re.compile(r"(导入|录入|上传|添加|新增|加一?条|补|拍|扫).{0,6}(数据|化验|报告|表格|记录|文件)|接入.{0,8}(设备|Oura|苹果健康|手机|戒指|手环)|连上|绑定设备"),
     "导入或接入数据", ["guard", "sources"]),
    (re.compile(r"(增加|新增|添加|新建|创建|加一?个|搭一?个?|建一?个?).{0,6}(状态|卡|引擎|模板)"), "增加状态卡", ["eng"]),
    (re.compile(r"(授权|分享|共享|发给|给.{0,6}看|收回|撤销授权)"), "授权或收回授权", ["grants", "records"]),
    (re.compile(r"(更正|修改|改一下|撤回|删除|删掉).{0,6}(数据|记录|这条)?"), "更正或撤回数据", ["data"]),
    (re.compile(r"(重算|重新算|再算一遍|换.{0,4}规则|改.{0,4}阈值|调.{0,4}灵敏度)"), "重算或换规则", ["adv", "eng"]),
]
ASK_LIKE = re.compile(r"[吗？?]$|哪|什么|几|多少|有没有|是不是|怎么来|从哪|为什么")
VALUE = re.compile(r"多少|几(?:点|个|次)?$|数值|读数|值是|值为|测得|测出|结果是|最近一次|上一?次|最新")
DATE = re.compile(r"(?:(\d{4})[-/年.])?(\d{1,2})[-/月.](\d{1,2})日?")
VOCAB = {
    "torch": ("数据", "数源", "来源", "接入", "导入", "录入", "化验", "报告", "表格", "Oura", "苹果健康", "手机", "基因", "位点", "文件",
              "更正", "撤回", "版本", "证据", "图谱", "追溯", "溯源", "原始", "原件", "设备", "星炬", "指标", "读数", "记录了"),
    "track": ("状态", "卡", "等级", "关注", "观察", "提醒", "通知", "计算", "算", "规则", "引擎", "生物年龄", "时点", "结论", "竞争性解释",
              "回溯", "实验室", "变化", "星轨", "评分", "标准"),
    "cluster": ("授权", "出域", "离开", "分享", "共享", "给谁", "谁看", "谁用", "收回", "对象", "通道", "披露", "推送", "读取", "星簇"),
}
GENERIC = ("数据", "记录了")
META = ("PTDS", "基座", "星灵", "这个系统", "这里能", "你能", "怎么用")
HERE = re.compile(r"这一?页|这里|这个页面|当前页")

SYSTEM = ("你是 PTDS 里的星灵，一个只读的本机助手。只根据给你的「记录事实」回答本人关于 PTDS（星炬：数据和来源；星轨：状态卡、计算和提醒；"
          "星簇：授权和出域）的问题。规则：只用事实里写着的内容；事实里没有就说记录里没有这条信息；问题和这些记录无关，就把 in_scope 写成 false，"
          "answer 留空。不做诊断，不给治疗、用药或就医建议，不推测原因，不给新的结论、等级、预警或阈值，不评价好坏；不出现事实和问题里没有的数字；"
          "用第二人称，不超过 120 字，不写事实编号。"
          "如果给了「我的记忆」：那是用户自己确认让你记住的偏好，不是事实证据；用到时要说“你之前让我记住”，只复述记忆原意，"
          "不补充记忆里没有的内容；问题只和记忆有关时，答记忆就够了，in_scope 写 true。没有给「我的记忆」时，不能说你记得任何事。"
          '输出 JSON：{"in_scope":true,"answer":"……","go":[可选，从给出的可去页面编号里选]}')
MEM_HEAD = "【我的记忆 · 你确认过的偏好，不是事实证据】"
MEM_WORDS = re.compile(r"记得|记住|之前告诉|你说过|之前让我")


def _base(label: str) -> str:
    return re.sub(r"[（(].*?[)）]", "", label or "").strip()


def route(question: str, labels: dict) -> dict:
    """程序分流。labels: code → 中文名（本实例星炬里有的指标）。"""
    q = question.strip()
    if MEDICAL.search(q):
        return {"kind": "out", "why": "问的是诊断、用药或就医"}
    if JUDGE.search(q):
        return {"kind": "out", "why": "问的是好坏判断"}
    wants = re.search(r"我要|我想|帮我|帮忙|请|怎么|如何|能不能|可不可以|可以|给我|替我", q) and \
        not re.search(r"过|谁|哪些|几|多少|有没有|什么时候|记录|怎么来|从哪|为什么", q)
    for rx, what, go in ACTIONS:
        if wants and rx.search(q):
            return {"kind": "guide", "what": what, "go": go}
    history = starling_history.intent(q)
    if history:
        return history
    hits = sorted({(c, labels[c]) for c in labels if _base(labels[c]) and _base(labels[c]) in q}, key=lambda x: -len(_base(x[1])))
    if hits and VALUE.search(q) and not re.search(r"怎么来|从哪|为什么|哪些计算|谁用", q):
        m = DATE.search(q)
        return {"kind": "value", "codes": [c for c, _ in hits[:8]], "date": (int(m.group(2)), int(m.group(3))) if m else None}
    # 越具体的块越靠前；“数据”“记录”这类泛词只在没有别的块时才算星炬
    areas = [a for a in ("cluster", "track", "torch") if any(w in q for w in VOCAB[a] if a != "torch" or w not in GENERIC)]
    if not areas and any(w in q for w in GENERIC):
        areas = ["torch"]
    if hits and "torch" not in areas:
        areas.append("torch")
    here = bool(HERE.search(q))
    if not areas and not here and not any(w in q for w in META):
        return {"kind": "out", "why": "问题里没有 PTDS 里的对象（数据、来源、状态卡、提醒、授权等）"}
    if not areas and here:
        return {"kind": "ask", "areas": [], "here": True}
    return {"kind": "ask", "areas": areas or ["torch", "track", "cluster"], "here": here, "codes": [c for c, _ in hits[:3]]}


def value_answer(snap: dict, codes: list, date) -> dict:
    rows = snap.get("timeline") or []
    out = []
    for code in codes:
        mine = [o for o in rows if o.get("code") == code]
        if date:
            mine = [o for o in mine if (o.get("tp") or "")[5:] == f"{date[0]:02d}-{date[1]:02d}"]
        if not mine:
            continue
        o = max(mine, key=lambda x: ((x.get("temporal") or {}).get("observed_at") or x.get("tp") or ""))
        rev = str(o.get("ref", "")).rsplit("@", 1)[-1]
        val = {"true": "有", "false": "无"}.get(str(o.get("value_raw")).lower(), o.get("value_raw"))
        if len(out) >= 3:
            break
        out.append(f"{o.get('label_zh')} {o.get('comparator') or ''}{val}{(' ' + o['unit_raw']) if o.get('unit_raw') else ''} · {o.get('tp')} · "
                   f"{evidence_graph.SRC_ZH.get(o.get('source_kind'), o.get('source_kind'))} · 第 {rev} 版" + ("" if rev == "1" else "（更正过，旧版保留）"))
    return {"lines": out, "ref": None}


def _check(text: str, facts: list, question: str) -> list:
    bad = []
    why = starling.check_answer(text, facts, question)
    if why == "NUMBER_NOT_IN_CONTEXT":
        known = set(re.findall(r"\d+", " ".join(facts) + " " + question))
        bad += ["数字 " + n + " 不在记录里" for n in dict.fromkeys(re.findall(r"\d+", text)) if n not in known]
    elif why == "INTERPRETATION":
        bad.append("写了诊断、建议或好坏判断")
    elif why == "EMPTY":
        bad.append("没写内容")
    t = text
    for d in tuple(starling.DISCLAIMERS) + starling_page.NAMES:
        t = t.replace(d, "")
    bad += ["用了不该用的词：" + w for w in starling_page.EXTRA_BANNED if w in t and not (w == "病" and "病例" in t)]
    joined = " ".join(facts)
    bad += ["授权编号 " + g + " 不在记录里" for g in re.findall(r"G-\d+", text) if g not in joined]
    return sorted(set(bad))


def ask(llm, question: str, labels: dict, snap: dict, facts_for, sign: str, memory=None,
        history_query=None, now=None) -> dict:  # noqa: C901
    """facts_for(area) → (事实行列表, 允许的名称)；area 为 torch / track / cluster / page。
    memory：None = 记忆功能关着；否则是 starling_memory.Store.recall() 的结果（问之前已经检索好）。"""
    q = (question or "").strip()[:300]
    res = {"question": q, "state": "", "area": "", "area_zh": "", "answer": "", "by": "", "go": [], "sent": [], "why": "", "rejected": [],
           "memory_state": memory["state"] if memory else "off", "memories": []}
    if not q:
        return dict(res, state="out", why="没有问题")
    hits = (memory or {}).get("hits") or []
    if memory is not None:
        import starling_memory  # noqa: PLC0415
        want = starling_memory.proposal(q)
        if want:  # “请记住……”：程序截出要记的那句，等我点“确认记住”才写；不问模型
            return dict(res, state="remember_ask", by="程序 · 没有问星灵", area_zh="我的记忆", proposal=want,
                        answer="要我把这句话记成长期记忆吗？点“确认记住”才会存；以后问到相关的事，星灵会先想起它。")
    r = route(q, labels)
    if r["kind"] == "history":
        result = starling_history.answer(r, now, (snap.get("instance") or {}).get("tz", "Asia/Shanghai"), history_query)
        return dict(res, state="value", by="程序查的保存记录 · 没有问星灵", area="torch",
                    area_zh="星炬 · 保存记录", go=["data"], **result)
    if r["kind"] == "out" and hits and r["why"].startswith("问题里没有 PTDS"):
        r = {"kind": "ask", "areas": [], "here": False, "codes": [], "memory_only": True}  # 只和我的记忆有关
    if r["kind"] == "out":
        if memory and memory["state"] == "failed" and r["why"].startswith("问题里没有 PTDS"):
            return dict(res, state="out", by="程序挡下 · 没有问星灵", why="记忆这次没取到（检索失败）", area_zh="不在范围内",
                        answer="记忆这次没取到，星灵不凭空回答。可以稍后再问，或到“我的记忆”里看看。")
        if memory and memory["state"] == "empty" and MEM_WORDS.search(q) and r["why"].startswith("问题里没有 PTDS"):
            return dict(res, state="out", by="程序查的记忆 · 没有问星灵", why="“我的记忆”里没有相关的", area_zh="我的记忆",
                        answer="“我的记忆”里没找到和这个问题相关的记忆，星灵不编。想让它记住，就说“请记住……”。")
        mem_note = "，“我的记忆”里也没有相关的" if memory and memory["state"] == "empty" and r["why"].startswith("问题里没有 PTDS") else ""
        return dict(res, state="out", by="程序挡下 · 没有问星灵", why=r["why"], area_zh="不在范围内",
                    answer=f"这个问题不在 PTDS 的记录里{mem_note}，星灵不回答。")
    if r["kind"] == "guide":
        return dict(res, state="guide", by="程序指路 · 没有问星灵", area_zh="去现有页面操作", go=r["go"],
                    answer=f"星灵暂时不能替你{r['what']}，也不会自动创建。请到下面的页面里自己操作，每一步都会让你确认。")
    if r["kind"] == "value":
        v = value_answer(snap, r["codes"], r["date"])
        text = "；".join(v["lines"]) + "。" if v["lines"] else ("星炬里没有这项数据" + ("在这一天" if r["date"] else "") + "的记录。")
        return dict(res, state="value", by="程序查的记录 · 数值不交给星灵", area="torch", area_zh="星炬 · 我的数据", go=["data"], answer=text)
    # 进了门：拼这几块的记录事实
    lines, lits, dropped = [], set(), 0
    areas = (["page"] if r["here"] else []) + r["areas"]
    for a in areas:
        f, lit = facts_for(a)
        head = f"【{AREA_ZH[a]}】"
        for line in f:
            try:
                starling.check_context([line], lit)
            except starling.RawValueInContext:
                dropped += 1  # 混进了数值的那一行不送
                continue
            lines.append(head + line)
    shown = r["areas"] or ["page"]
    for code in r.get("codes") or []:  # 问到具体指标：只给这项数据的来历（日期、条数、来源、版本），不给数值
        mine = [o for o in snap.get("timeline") or [] if o.get("code") == code]
        if not mine:
            lines.append(f"【星炬 · 我的数据】{labels.get(code, code)}：星炬里没有这项数据的记录")
            continue
        days = sorted({o.get("tp") for o in mine if o.get("tp")})
        srcs = sorted({evidence_graph.SRC_ZH.get(o.get("source_kind"), o.get("source_kind")) for o in mine})
        fixed = [o for o in mine if not str(o.get("ref", "")).endswith("@1")]
        line = (f"{labels.get(code, code)}：星炬里有 {len(mine)} 条，日期 " + "、".join(days[-5:]) +
                f"，来自 {'、'.join(srcs)}，" + (f"{len(fixed)} 条更正过，旧版保留" if fixed else "都没有更正过"))
        try:
            starling.check_context([line], {labels.get(code, code)} | set(evidence_graph.SRC_ZH.values()))
            lines.insert(0, "【星炬 · 我的数据】" + line)
        except starling.RawValueInContext:
            dropped += 1
    if memory is not None:  # 记忆单独成段，和记录事实分开；检索失败也照实告诉星灵
        if hits:
            lines += [MEM_HEAD + f"{h['created_at'][:10]} 记下：{h['text']}" for h in hits]
            res["memories"] = [{"chain_id": h["chain_id"], "text": h["text"], "created_at": h["created_at"], "method": h["method"]} for h in hits]
        elif memory["state"] == "failed":
            lines.append(MEM_HEAD + "这次没取到（检索失败），不要说你记得任何事")
    if r.get("memory_only"):
        shown = []
    area = shown[0] if len(shown) == 1 else ""
    go_all = list(dict.fromkeys(g for a in r["areas"] for g in AREA_GO.get(a, []))) or ([] if r.get("memory_only") else ["graph", "data"])
    res.update(area=area, area_zh=("我的记忆" if r.get("memory_only") else " · ".join(AREA_ZH[a].split(" · ")[0] for a in shown) if not area else AREA_ZH[area]),
               sent=lines, dropped=dropped)
    if llm is None or not llm.healthy():
        return dict(res, state="no_llm")
    if not BUSY.acquire(blocking=False):
        return dict(res, state="busy")
    try:
        q_sent, masked = starling.mask_question(q)
        prompt = "记录事实：\n" + "\n".join(lines) + "\n可去页面：" + "；".join(f"{g}={NAV[g]}" for g in go_all) + "\n\n问题：" + q_sent
        t0, tried, extra = time.time(), [], ""
        for n in range(1, ATTEMPTS + 1):
            try:
                raw = llm.chat(SYSTEM, prompt + extra)
                m = re.search(r"\{.*\}", raw, re.S)
                doc = json.loads(m.group(0)) if m else {}
            except Exception as e:  # noqa: BLE001
                tried.append({"text": "模型没有返回可以读的结果（" + type(e).__name__ + "）", "bad": ["格式不对"]})
                continue
            if isinstance(doc, dict) and doc.get("in_scope") is False:
                return dict(res, state="out", by=sign, why="星灵判断这个问题不在这些记录里", masked=masked,
                            answer="星灵判断这个问题不在 PTDS 的记录里，没有回答。", seconds=round(time.time() - t0))
            text = re.sub(r"\s+([，。；])", r"\1", starling_page.REF.sub("", str((doc or {}).get("answer") or ""))).strip()
            said = text
            for h in hits:  # 复述我自己让它记住的话不算违规（比如记忆里本来就有“病历”）
                said = said.replace(h["text"], "")
                for w in tuple(starling.BANNED) + starling_page.EXTRA_BANNED:
                    if w in h["text"]:
                        said = said.replace(w, "")
            bad = _check(said, lines, q_sent)
            if not hits and MEM_WORDS.search(text):
                bad.append("没有给记忆，却说记得")  # 不编记忆
            if not bad:
                go = [g for g in (doc.get("go") or []) if g in go_all] if isinstance(doc.get("go"), list) else []
                return dict(res, state="ok", by=sign, answer=text, go=go or go_all[:2], masked=masked, rejected=tried,
                            attempts=n, seconds=round(time.time() - t0))
            tried.append({"text": text or "（空）", "bad": bad})
            extra = "\n\n上一次的回答没通过核对：" + "；".join(bad) + "。请只用记录事实重写。"
        return dict(res, state="rejected", by=sign, masked=masked, rejected=tried, attempts=ATTEMPTS, seconds=round(time.time() - t0))
    finally:
        BUSY.release()


def log(root: Path, at: str, page: dict, res: dict) -> str:
    rid = "S-" + uuid.uuid4().hex[:10]
    rec = {"id": rid, "at": at, "page": page, "intent": "ask", "question": res["question"], "sent": res["sent"], "answer": res["answer"],
           "by": res["by"], "state": res["state"], "why": res.get("why"), "rejected": res.get("rejected"), "masked": res.get("masked")}
    path = root / "starling" / "sessions.jsonl"
    with starling.LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rid
