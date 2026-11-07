"""星灵解读（产品负责人 2026-10-14）：证据图谱、我的数据、我的数源三页，以及证据图谱的来龙去脉浮窗。

- 只在我点了“星灵解读”之后才写（不自动触发，降低本机并发）；写的是本机 Qwen，署名“星灵（Qwen 3.5 9B本地）发出”。
- 事实只用记录：来源、条数、版本、时间、计算编号、授权与出域；不含任何健康数值（HR-42）。送出前过 starling.check_context()。
- 逐句核对：数字（整数整词）必须在事实里出现过；不写诊断、建议、好坏判断。一次没全过就重写一次。
- 不替换、不兜底：两次都没过，就照实说没采用，并把没过的句子和原因摆出来；模型没开就说没开。
- 只读：结果按事实指纹缓存在实例目录 lab/compete_ai.json（和竞争性解释同一个缓存、同一把锁，一次只写一份）。
"""
from __future__ import annotations

import json
import re
import time
from collections import Counter
from datetime import datetime, timedelta

import evidence_graph
import starling

SYSTEM = ("你是“星灵”，帮人看懂自己的数据记录。只能使用用户给出的记录事实，不能补充任何事实里没有的数字、日期、来源或判断；"
          "不写诊断、病名、建议、好坏判断，不评价健康状况。输出 JSON："
          '{"sentences":[{"text":"一句中文","facts":["引用的事实编号，如 F3"]}]}。'
          "sentences 2 到 4 句，每句不超过 50 个字，用平常说话的口气，先说最重要的；事实编号只写在 facts 里，text 里不要出现 F1 这类编号。")
REF = re.compile(r"[（(]?\s*(?:事实\s*)?F\d+(?:\s*[、,，和及/]\s*F\d+)*\s*[)）]?")
EXTRA_BANNED = ("诊断", "病", "正常", "异常", "偏高", "偏低", "健康", "概率", "应该", "需要注意")
ATTEMPTS = 2
NAMES = ("苹果健康", "手机健康", "Apple Health", "谷歌健康", "小米健康", "华为健康", "演示病例")
PAGE_ZH = {"graph": "证据图谱", "data": "我的数据", "sources": "我的数源", "trace": "这个数是怎么来的", "alert": "这条提醒为什么触发"}


def sign(llm) -> str:
    """署名（产品负责人 2026-10-14）：星灵（Qwen 3.5 9B本地）发出。型号从模型文件名读，不写死。"""
    name = getattr(llm, "model_name", "") or ""
    m = re.search(r"(?i)qwen\s*([\d.]+)[-_ ]*(\d+(?:\.\d+)?)b", name)
    return f"星灵（Qwen {m.group(1)} {m.group(2)}B本地）发出" if m else f"星灵（{name or '本地模型'}本地）发出"


def _t(iso) -> str:
    s = str(iso or "")
    return s[:10] + (" " + s[11:16] if len(s) >= 16 else "")


def _ctx(page: str, facts: list, literals: set, key: str) -> dict:
    lines = [f for f, _ in facts]
    starling.check_context(lines, literals)  # HR-42：有健康数值就不送
    return {"kind": "page", "page": page, "page_zh": PAGE_ZH[page], "tp": f"PAGE:{key}", "level_zh": "",
            "facts": facts, "status_map": {}}


def graph_page(inst, m: dict, snap: dict, records: list, cards: list) -> dict:
    facts = []
    add = lambda t: facts.append((t, None))  # noqa: E731
    add(f"状态结论一共 {m.get('total', 0)} 条，其中 {m.get('traceable', 0)} 条每条输入都能追到星炬里的正式记录")
    if m.get("not_traceable"):
        add(f"追不全的有 {len(m['not_traceable'])} 条，时点是：" + "、".join(m["not_traceable"][:5]))
    names = [c.get("name") or c.get("card_id") for c in cards]
    if names:
        add(f"参与计算的状态卡有 {len(names)} 张：" + "、".join(n for n in names[:6] if n) + ("等" if len(names) > 6 else ""))
    from contextlib import closing  # noqa: PLC0415
    from cards import open_startrack  # noqa: PLC0415
    with closing(open_startrack(inst.ctx)) as track:
        n, last = track.execute("SELECT count(*), max(started_at) FROM run").fetchone()
    if n:
        add(f"星轨一共算过 {n} 次（各张卡合计），最近一次是 {_t(last)}")
    by = Counter(evidence_graph.SRC_ZH.get(o.get("source_kind"), o.get("source_kind")) for o in snap.get("timeline") or [])
    if by:
        add("星炬里的正式数据来自：" + "、".join(f"{k} {v} 条" for k, v in by.most_common(6)))
    out = [r for r in records if r.get("egress")]
    add(f"数据离开本机的记录有 {len(out)} 次" + ("，对象是：" + "、".join(sorted({str(r.get('obj') or r.get('object') or '我自己') for r in out})[:4]) if out else "，没有数据出域"))
    alerts = snap.get("alerts") or []
    add(f"星轨发过 {len(alerts)} 条提醒")
    return _ctx("graph", facts, set(evidence_graph.SRC_ZH.values()) | {n for n in names if n}, inst.spec["key"])


def trace(inst, t: dict) -> dict:
    facts = []
    add = lambda x: facts.append((x, None))  # noqa: E731
    c = t["conclusion"]
    if c.get("value") is None and c.get("level_zh"):  # 引擎卡的结果本身就是健康数值，不送（HR-42）
        add(f"这是 {t.get('card_zh') or t['card_id']} 在 {t['tp']} 的结论，等级是“{c['level_zh']}”")
    else:
        add(f"这是 {t.get('card_zh') or t['card_id']} 在 {t['tp']} 的结果（具体数值不交给星灵）")
    tp_in = [i for i in t["inputs"] if i.get("role") != "HISTORY"]
    hist = [i for i in t["inputs"] if i.get("role") == "HISTORY"]
    add(f"这个时点用了 {len(tp_in)} 项数据" + (f"，另有 {len(hist)} 条更早的数据作对照" if hist else ""))
    src = Counter(i.get("source_zh") or "来源不明" for i in t["inputs"] if i.get("found"))
    if src:
        add("数据来源：" + "、".join(f"{k} {v} 条" for k, v in src.most_common()))
    labels = sorted({i.get("label") for i in tp_in if i.get("label")})
    if labels:
        add("用到的指标：" + "、".join(labels[:12]))
    newer = [i for i in t["inputs"] if i.get("superseded")]
    add(f"用到的数据里有 {len(newer)} 条后来又更正过" if newer else "用到的数据算完以后都没有被更正过")
    r = t["run"]
    add(f"星轨在 {_t(r['started_at'])} 算出这个结果（计算 #{r['run_id']}），原因是{r['trigger_zh']}；这个时点一共算过 {len(r['history'])} 次")
    add("每条输入都能追到星炬里的正式记录，来源、版本齐全" if t.get("traceable") else "有输入追不全，缺：" + "、".join(t.get("missing") or []))
    v = (t.get("verify") or {}).get("state")
    add({"SAME": "打开时按同一版规则现场重算了一遍，和存下的结果一字不差", "DIFFER": "打开时现场重算了一遍，和存下的结果不一样",
         "STALE": "这个结果算完以后用到的数据有更新，要等下次计算"}.get(v, "这类卡不支持现场重算"))
    for a in t.get("alerts") or []:
        ok = [d["zh"] for d in a.get("deliveries") or [] if d.get("outcome") == "SENT"]
        add(f"发过一条提醒，送到了：" + ("、".join(ok) if ok else "还没送到"))
    gave = [u for u in t.get("used_by") or [] if u.get("obj") != "我自己"]
    add(f"之后经授权给了别人 {len(gave)} 次" if gave else "没有出域给别人")
    lits = set(evidence_graph.SRC_ZH.values()) | set(labels) | {t.get("card_zh") or ""} | {c.get("level_zh") or ""}
    return _ctx("trace", facts, {x for x in lits if x}, f"{inst.spec['key']}|{t['card_id']}|{t['tp']}")


def data_page(inst, snap: dict, now: datetime, labels: dict) -> dict:
    facts = []
    add = lambda x: facts.append((x, None))  # noqa: E731
    rows = snap.get("timeline") or []
    add(f"星炬里现在有 {len(rows)} 条正式数据，涉及 {len({o['code'] for o in rows})} 个指标")
    if rows:
        days = sorted(o.get("tp") for o in rows if o.get("tp"))
        if days:
            add(f"观测日期最早是 {days[0]}，最近是 {days[-1]}")
        since = (now - timedelta(days=6)).date().isoformat()
        recent = Counter(evidence_graph.SRC_ZH.get(o.get("source_kind"), o.get("source_kind")) for o in rows if since <= (o.get("tp") or "") <= now.date().isoformat())
        add("观测日期在最近 7 天内（含今天）的数据" + (f" {sum(recent.values())} 条：" + "、".join(f"{k} {v} 条" for k, v in recent.most_common()) if recent else "：没有"))
        rev = [o for o in rows if not str(o.get("ref", "")).endswith("@1")]
        add(f"其中 {len(rev)} 条更正过，旧版本都还留着" if rev else "没有更正过的数据")
        once = Counter(o["code"] for o in rows)
        one = sorted(labels.get(k, k) for k, n in once.items() if n == 1)
        if one:
            add(f"只记过一次的指标有 {len(one)} 个（还看不出变化）：" + "、".join(one[:8]))
    if snap.get("unknown_time"):
        add(f"另有 {len(snap['unknown_time'])} 条数据时间不明")
    lits = set(evidence_graph.SRC_ZH.values()) | set(labels.values()) | {"最近 7 天"}
    return _ctx("data", facts, lits, inst.spec["key"])


def sources_page(inst, snap: dict, src: dict, bridge: dict | None, genes: int) -> dict:
    facts = []
    add = lambda x: facts.append((x, None))  # noqa: E731
    rows = snap.get("timeline") or []
    by = {}
    for o in rows:
        k = evidence_graph.SRC_ZH.get(o.get("source_kind"), o.get("source_kind"))
        b = by.setdefault(k, {"n": 0, "last": ""})
        b["n"] += 1
        b["last"] = max(b["last"], o.get("tp") or "")
    add(f"送来过数据的来源有 {len(by)} 个" + ("：" + "、".join(f"{k} {v['n']} 条，最近一条 {v['last']}" for k, v in sorted(by.items(), key=lambda kv: kv[1]['last'], reverse=True)) if by else ""))
    o = (src or {}).get("oura") or {}
    if o.get("status") == "CONNECTED":
        add(f"Oura 已接入，最近一次拉取在 {_t(o.get('last_pull_at'))}" + ("，上次拉取没成功" if o.get("last_error") else ""))
    elif o.get("status"):
        add("Oura 现在没有接入" if o.get("status") != "NEEDS_REAUTH" else "Oura 需要重新授权")
    if bridge is not None:
        phones = bridge.get("phones") or []
        add(f"苹果健康：配对过 {len(phones)} 部手机，收到过 {bridge.get('n', 0)} 次推送" if phones else "苹果健康还没有配对手机")
    add(f"基因文件纳管了 {genes} 份" if genes else "还没有基因文件")
    ev = snap.get("device_events") or []
    if ev:
        add(f"设备断开或恢复的记录有 {len(ev)} 条")
    return _ctx("sources", facts, set(evidence_graph.SRC_ZH.values()) | {"Oura", "Somaloop", "Qkeer"}, inst.spec["key"])


def check(text: str, facts: str, allow: tuple = ()) -> list:
    """allow：事实里本来就有的词（如提醒解释里的“阈值”），模型复述它不算违规。"""
    bad = []
    known = {str(int(x)) for x in re.findall(r"\d+", facts)}  # 按数值比：事实里的“2026-10-04”和回答里的“10 月 4 日”是同一个数
    for n in re.findall(r"\d+", text):
        if str(int(n)) not in known:
            bad.append("数字 " + n + " 不在记录里")
    t = text
    for d in tuple(starling.DISCLAIMERS) + NAMES:  # 来源名里的“健康”“病例”不算判断
        t = t.replace(d, "")
    for w in tuple(starling.BANNED) + EXTRA_BANNED:
        if w in allow and w in facts:
            continue
        if w in t and not (w == "病" and "病例" in t):
            bad.append("用了不该用的词：" + w)
    return sorted(set(bad))


def write(llm, c: dict) -> dict:
    numbered = "\n".join(f"F{i + 1} {t}" for i, (t, _) in enumerate(c["facts"]))
    plain = "\n".join(t for t, _ in c["facts"])  # 核对数字只对事实原文，不算 F 编号
    t0, tried = time.time(), []
    for n in range(1, ATTEMPTS + 1):
        try:
            raw = llm.chat(c.get("system") or SYSTEM, f"页面：{c['page_zh']}。记录事实：\n{numbered}")
            m = re.search(r"\{.*\}", raw, re.S)
            sents = json.loads(m.group(0))["sentences"] if m else []
            sents = [s for s in sents if isinstance(s, dict) and isinstance(s.get("text"), str) and s["text"].strip()][:4]
        except Exception as e:  # noqa: BLE001
            tried.append({"text": "模型没有返回可以读的结果（" + type(e).__name__ + "）", "bad": ["格式不对"]})
            continue
        rows = []
        for s in sents:
            text = re.sub(r"\s+([，。；])", r"\1", REF.sub("", s["text"])).strip()
            rows.append({"text": text, "bad": check(text, plain, tuple(c.get("allow") or ()))})
        if rows and not any(r["bad"] for r in rows):
            return {"state": "ok", "sentences": [{"text": r["text"], "cols": []} for r in rows], "rejected": tried,
                    "checked": len(rows), "seconds": round(time.time() - t0), "by": sign(llm), "attempts": n}
        tried += [{"text": r["text"], "bad": r["bad"]} for r in rows if r["bad"]] or [{"text": "一句也没写", "bad": ["句子太少"]}]
    return {"state": "rejected", "sentences": [], "rejected": tried, "seconds": round(time.time() - t0), "by": sign(llm), "attempts": ATTEMPTS}
