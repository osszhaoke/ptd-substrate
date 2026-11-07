"""星灵 · 解释与导航（PRD 4.4，横切，只读，默认本机模型）。

在我当前所在的页面里，用已经存在的结果回答"这是什么、从哪来、去哪看"。
- 推断层只收离散化的等级标签与对象引用，不收原始数值（HR-42 / DC-04）：上下文由代码从快照里挑标签拼成，
  送给模型前过 check_context()，出现健康数值就不送；我问题里打的数值也换成"某个数值"再送。
- 不创建或修改授权、不发起计算、不生成新结论 / 预警 / 阈值、不替我提交：这里只读。
- 回答要过核对：出现上下文里没有的数字，或诊断、用药、阈值、好坏判断类说法，就不用，并如实标注（不再拿规则拼的回答顶替）。
- 只调本机模型（127.0.0.1）；没在运行就照实说。
- 每次问答记在 <实例>/starling/sessions.jsonl：问题、送给模型的上下文、回答、出自谁、是否被拒。
"""
from __future__ import annotations

import json
import re
import threading
import uuid
from collections import Counter
from pathlib import Path

from cluster import GSTATE_ZH, RULE_RES_ZH, STATUS_ZH  # cluster 把 app/core 放进 sys.path

import compete  # noqa: E402
from dynamic import change_word  # noqa: E402
import retro  # noqa: E402
import evidence_graph  # noqa: E402

LEVEL_ZH = evidence_graph.LEVEL_ZH
SRC_ZH = evidence_graph.SRC_ZH
PAGES = {
    "general": ("PTDS", "个人可信数据基座：星炬接入并保存我的数据，星轨按我绑定的状态卡自动计算，星簇管数据离开 PTDS 的授权和记录。"),
    "wall": ("星轨 · 我的状态", "我绑定的状态卡。每张卡按时点显示综合关注等级，或只显示读数。"),
    "card": ("星轨 · sJIA 关注卡", "星轨按 sJIA 规则包，把每个时点的化验和症状算成综合关注等级（无、观察、关注、无法判定）。这是关注信号，不构成诊断或治疗建议。"),
    "tp": ("星轨 · 一个时点的结果", "这个时点的综合关注等级、驱动它的规则和变化、用了哪些数据、算过几次。"),
    "vitals": ("星轨 · 我的体征", "设备读数（Oura、苹果健康等），只显示读数和是否最新，不算等级。"),
    "alerts": ("星轨 · 状态通知", "星轨发出的提醒，以及送到了哪些通道。"),
    "compete": ("星轨 · 状态实验室", "竞争性解释：同一组数据按不同规则或假设各算一遍，并排列出各自成立与否、依据是哪些数据。只用于测试，不是结论。"),
    "track": ("星轨", "星轨按我绑定的卡计算状态，数据一到就自动更新。"),
    "data": ("星炬 · 我的数据", "星炬里保存的正式数据。每条都有来源和版本，更正和撤回都追加新版本，旧版本保留。"),
    "torch_detail": ("星炬 · 一条数据", "一条数据的值、来源、版本史，以及每一版被哪几次计算用过。"),
    "graph": ("星痕 · 证据图谱", "从一条状态结论追到计算、所用数据的版本、原件和交接文件，以及之后谁经哪个授权用过它。只读已有的记录，不推断。"),
    "gene": ("星炬 · 基因数据", "原始基因文件原样纳管，装进位点库供按 rs 号调取。PTDS 不解读基因型，基因不进状态计算，也不触发提醒。"),
    "sources": ("星炬 · 我的数源", "接入了哪些数据来源：化验单识别、表格、Oura、苹果健康、基因文件等。"),
    "entry": ("星炬 · 录入数据", "手工录入、拍化验单或导入表格。保存前要我确认，保存后交给星轨自动计算。"),
    "guard": ("星炬 · 数据导航", "星炬数据的保存与交接状态。"),
    "cluster": ("星簇", "数据或状态只要离开 PTDS，都要经过星簇授权，并留下记录。在 PTDS 里面使用不需要授权。"),
    "grant": ("星簇 · 一条授权", "一条授权的对象、范围、方式、披露级别、时效和状态，以及它的出域记录。"),
}
NAV = {"graph": "星痕", "data": "我的数据", "tp": "这个时点的结果", "wall": "我的状态", "vitals": "我的体征",
       "alerts": "状态通知", "records": "星痕 · 授权记录", "grants": "授权规则", "gene": "基因数据", "sources": "我的数源"}
# 对象引用里的数字（日期、编号、版本、计数、标准名）不是健康数值，可以出现在上下文里
REF_RE = re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}:\d{2}(?::\d{2})?|\bG-\d+|\bE\d+|#\d+|第 ?\d+ ?版|"
                    r"\d+ ?(?:条|次|份|个|行|项|张|处)|GRCh3[78]|hg(?:19|38)|\bR\d\b|Somaloop|Qkeer")
BANNED = ("确诊", "患有", "考虑为", "提示可能", "可能是", "建议", "治疗", "服用", "用药", "就医", "复查", "阈值",
          "严重", "恶化", "好转", "危险", "风险", "诊断为")
DISCLAIMERS = ("不构成诊断或治疗建议", "不构成诊断", "不是诊断", "不做诊断", "非诊断", "不给建议", "不给治疗建议",
               "不构成治疗建议")
LOCK = threading.Lock()


class RawValueInContext(Exception):
    pass


def check_context(lines: list, literals: set) -> None:
    """HR-42：去掉对象引用和允许的名称后，不能再有任何数字。"""
    for line in lines:
        text = line
        for lit in sorted(literals, key=len, reverse=True):
            text = text.replace(lit, "")
        if re.search(r"\d", REF_RE.sub("", text)):
            raise RawValueInContext(line)


def mask_question(q: str) -> tuple:
    """我问题里的数值不交给模型：换成"某个数值"。返回 (送出的问题, 是否改过)。"""
    keep = REF_RE.findall(q)
    masked = re.sub(r"\d+(?:\.\d+)?", "某个数值", REF_RE.sub("\x00", q))
    for k in keep:
        masked = masked.replace("\x00", k, 1)
    return masked, masked != q


def check_answer(answer: str, context: list, question: str) -> str | None:
    if not answer.strip():
        return "EMPTY"
    known = set(re.findall(r"\d+", " ".join(context) + " " + question))
    if any(n not in known for n in re.findall(r"\d+", answer)):
        return "NUMBER_NOT_IN_CONTEXT"
    text = answer
    for d in DISCLAIMERS:
        text = text.replace(d, "")
    ctx = " ".join(context)
    for w in BANNED:  # 记录里本来就有的标签（如等级“建议补检”）照抄不算自己下判断；只放行和记录里一字不差的短语
        for phrase in sorted(set(re.findall(r"[\u4e00-\u9fff]{0,4}" + re.escape(w) + r"[\u4e00-\u9fff]{1,4}|[\u4e00-\u9fff]{1,4}" + re.escape(w), ctx)), key=len, reverse=True):
            text = text.replace(phrase, "")
    if any(w in text for w in BANNED):
        return "INTERPRETATION"
    return None


# ----------------------------------------------------------------------------- 上下文（只拼标签）

def _run_label(trace: dict, rule_zh: dict, code_zh: dict, status: str | None) -> list:
    out = []
    if not trace.get("found"):
        return out
    c, r = trace["conclusion"], trace["run"]
    out.append(f"{trace['tp']} 的结论：综合关注等级 {c['level_zh']}" + (f"（结果状态：{STATUS_ZH.get(status, status)}）" if status else ""))
    drv = []
    for d in c.get("drivers") or []:
        if d.get("kind") == "RULE":
            drv.append(f"规则 {rule_zh.get(d['rule'], d['rule'])} {RULE_RES_ZH.get(d.get('result'), d.get('result'))}")
        elif d.get("kind") == "DYNAMIC":
            drv.append(f"{code_zh.get(d.get('code'), d.get('code'))} {change_word(d.get('direction'), d.get('measure'))}")
    if drv:
        out.append("驱动：" + "；".join(drv))
    out.append(f"计算 #{r['run_id']}（{r['trigger_zh']}），这个时点一共算过 {len(r['history'])} 次：" +
               " → ".join(f"#{h['run_id']} {h['level_zh']}" for h in r["history"]))
    now = [i for i in trace["inputs"] if i.get("role") != "HISTORY" and i.get("found")]
    hist = [i for i in trace["inputs"] if i.get("role") == "HISTORY"]
    src = Counter(i.get("source_zh") or "未知来源" for i in now)
    out.append(f"用了这个时点的 {len(now)} 条数据（" + "、".join(f"{k} {v} 条" for k, v in src.items()) + "）" +
               (f"，另有 {len(hist)} 条作为历史基线" if hist else ""))
    if now:
        out.append("用到的指标：" + "、".join(sorted({i["label"] for i in now})))
    sup = [i for i in trace["inputs"] if i.get("superseded")]
    if sup:
        out.append("其中 " + "、".join(i["label"] for i in sup) + " 之后有新版本，这次计算用的是旧版")
    out.append("全部输入都能追到来源、版本和信度" if trace["traceable"] else "有输入追不全：缺 " + "、".join(trace["missing"]))
    for a in trace.get("alerts") or []:
        got = [d["zh"] + ("已送达" if d["outcome"] == "SENT" else "未送达") for d in a["deliveries"]]
        out.append(f"提醒：{a['level_zh']} · {a['title']}" + ("（" + "、".join(got) + "）" if got else ""))
    if trace.get("used_by"):
        out.append("之后经授权读取或推送过：" + "、".join(sorted({f"{u.get('grant')} {u.get('obj')}" for u in trace["used_by"]})))
    return out


def build(inst, page: dict, snap: dict, records: list, grants: list, gene: list) -> dict:
    """→ {page, page_zh, what, facts[], go[], literals}。facts 只有标签与对象引用。"""
    pid = page.get("page") if page.get("page") in PAGES else "general"
    zh, what = PAGES[pid]
    kind = (snap.get("instance") or {}).get("kind")
    facts = [f"数据性质：{'合成的演示数据' if kind == 'DEMO' else '我的真实数据'}"]
    literals, go = set(), []
    tps = snap.get("timepoints") or []
    tp = page.get("tp") or ((snap.get("current") or {}).get("tp"))
    for g in gene:  # 文件名、厂商名（23andMe）、格式代码里的数字不是健康数值
        prof = g.get("profile") or {}
        literals |= {g.get("file_name") or "", prof.get("vendor") or "", prof.get("format_code") or ""}
    code_zh = {c: getattr(r, "label_zh", c) for c, r in (inst.app.registry.current.codes or {}).items()}
    cl = inst.cluster
    literals |= set(code_zh.values()) | set(cl.rule_zh.values())
    literals.discard("")
    if pid in ("wall", "card", "tp", "graph", "alerts", "track", "general"):
        if tps:
            facts.append("sJIA 关注卡各时点：" + "；".join(f"{t['tp']} {t.get('level_zh') or LEVEL_ZH.get(t['level'], t['level'])}" for t in tps))
        if pid in ("card", "tp", "graph", "wall") and tp:
            facts += _run_label(evidence_graph.trace(inst, tp, records, grants), cl.rule_zh, code_zh,
                                next((t.get("status") for t in tps if t["tp"] == tp), None))
            go += ["graph", "tp"] if pid != "tp" else ["graph", "data"]
        if pid in ("alerts", "card", "wall"):
            al = snap.get("alerts") or []
            facts.append(f"一共 {len(al)} 条提醒" + ("：" + "；".join(f"{a['tp']} {LEVEL_ZH.get(a['level'], a['level'])}" for a in al) if al else ""))
            go.append("alerts")
        if pid == "graph":
            m = evidence_graph.traceable(inst)
            facts.append(f"可追溯状态结论：{m['total']} 条中 {m['traceable']} 条（全部输入都能追到来源、版本、信度）")
            go = ["tp", "data", "records"]
    if pid == "compete" and (snap.get("instance") or {}).get("cards", ["SJIA_FOCUS"]).count("SJIA_FOCUS"):
        d = compete.explain(inst, tp or "")
        if d.get("found"):
            facts.append(f"比较的时点：{d['tp']}（星轨正式结果 {d['formal']['level_zh'] if d.get('formal') else '还没有'}）")
            facts += [f"{c['name']}：{c['result_zh']}" + ("；缺的数据：" + "、".join(c["missing"]) if c["missing"] else "")
                      for c in d["columns"]]
            facts += [f"假设「{h['zh']}」下的等级：{h['level_zh']}" for h in d["hypotheses"]]
        h = retro.history(inst)
        literals.add(h["method"]["zh"])  # "规则包 0.1"这类版本号不是健康数值
        facts.append("回溯式重算 · 现在的方法：" + h["method"]["zh"])
        facts.append("各时点最近两次计算的比较：" + "；".join(f"{t['tp']} {t['compare'] or '只算过一次'}" for t in h["tps"]))
        go = ["tp", "graph"]
    if pid == "vitals":
        items = (snap.get("vitals") or {}).get("items") or []
        facts.append("读数：" + ("；".join(f"{x.get('label_zh')}（{SRC_ZH.get(x.get('source_kind'), x.get('source_kind'))}，{'最新' if x.get('fresh') else '不是最新'}）" for x in items) or "还没有"))
        off = [e for e in snap.get("device_events") or [] if e.get("kind") == "DEVICE_OFFLINE"]
        if off:
            facts.append("设备断开记录：" + "；".join(e["title"] for e in off[-3:]))
        facts.append("这张卡只显示读数，不算等级，也不出关注提醒（设备断开的连接通知除外）")
        go = ["sources", "data"]
    if pid in ("data", "torch_detail", "sources", "guard", "entry"):
        tl = snap.get("timeline") or []
        src = Counter(SRC_ZH.get(o.get("source_kind"), o.get("source_kind")) for o in tl)
        facts.append(f"星炬里当前有 {len(tl)} 条正式数据" + ("：" + "、".join(f"{k} {v} 条" for k, v in src.items()) if tl else ""))
        go = ["graph", "sources"] if pid != "sources" else ["data", "gene"]
    if pid == "torch_detail" and page.get("ref"):
        oid = str(page["ref"]).split("@")[0]
        o = next((x for x in snap.get("timeline") or [] if x.get("ref", "").split("@")[0] == oid), None)
        vs = evidence_graph.versions(inst, oid)
        if o:
            facts.append(f"这条数据：{o.get('label_zh')}，时点 {o.get('tp')}，来源 {SRC_ZH.get(o.get('source_kind'), o.get('source_kind'))}")
        for v in vs:
            facts.append(f"第 {v['revision']} 版（{'已撤回' if v['status'] != 'ACTIVE' else '当前' if v is vs[-1] else '旧版，保留'}，{v['source_zh']}）" +
                         ("：被 " + "、".join(v.get("cards") or [f"计算 #{r}" for r in v["runs"]]) + " 用过" if v["runs"] else "：现有状态卡暂未包含该数据"))
        go = ["graph", "data"]
    if pid in ("gene", "sources"):
        files = [g for g in gene if g.get("outcome") != "DUPLICATE"]
        facts.append(f"已纳管基因文件 {len(files)} 份" + ("：" + "；".join(
            f"{g.get('file_name')}（{(g.get('profile') or {}).get('vendor') or (g.get('profile') or {}).get('format_code') or '格式未记'}"
            f"{'，' + g['profile']['build'] if (g.get('profile') or {}).get('build') else ''}）" for g in files) if files else ""))
        gg = [g for g in grants if g.get("card") == "GENE_LOCI"]
        if gg:
            facts.append("基因位点授权：" + "；".join(f"{g['id']} {'全部位点' if g.get('loci') == '*' else str(len(g.get('loci') or [])) + ' 个位点'}（{GSTATE_ZH.get(g['status'], g['status'])}）" for g in gg))
        facts.append("基因只纳管和按位点调取，PTDS 不解读、不进状态计算、不触发提醒")
        if pid == "gene":
            go = ["grants", "records"]
    if pid in ("cluster", "grant"):
        show = [g for g in grants if pid == "cluster" or g["id"] == page.get("gid")]
        for g in show[:8]:
            facts.append(f"授权 {g['id']}：对象 {(cl.objects.get(g['object']) or {}).get('zh', g['object'])}，"
                         f"{'读取' if g['method'] == 'read' else '推送'}，披露级别 {cl.levels.get(g['level'], {}).get('zh', g['level'])}，"
                         f"范围 {cl._card_zh(g['card'])}，{GSTATE_ZH.get(g['status'], g['status'])}")
        recs = [r for r in records if pid == "cluster" or r.get("grant") == page.get("gid")][:6]
        for r in recs:
            facts.append(f"记录：{r['summary']} · {r['obj']} · {r['result']}")
        go = ["records", "grants"] if pid == "cluster" else ["records", "graph"]
    if pid == "general":
        go = ["wall", "data", "records"]
    return {"page": pid, "page_zh": zh, "what": what, "facts": facts, "go": [g for g in dict.fromkeys(go) if g in NAV],
            "literals": literals, "tp": tp}


# 旧的“按规则整理的回答”兜底和逐页问答已撤（产品负责人 2026-10-14：翻车就翻车，不替换）；问答改由 starling_ask.py（右下角浮窗）负责。


def log(root: Path, at: str, page: dict, intent: str, res: dict) -> str:
    rid = "S-" + uuid.uuid4().hex[:10]
    rec = {"id": rid, "at": at, "page": page, "intent": intent, "question": res["question"], "sent": res["sent"],
           "answer": res["answer"], "by": res["by"], "rejected": res["rejected"], "masked": res["masked"]}
    path = root / "starling" / "sessions.jsonl"
    with LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rid


def _sign(llm) -> str:
    """署名（产品负责人 2026-10-14）：星灵（Qwen 3.5 9B本地）发出。"""
    import starling_page  # noqa: PLC0415
    return starling_page.sign(llm)
