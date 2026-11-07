"""竞争性解释的千问版本（R09 B1）：本机千问只根据结构化事实写人话，程序逐句核对，全部通过才替换程序版本。

- 事实来自 compete.explain() 的四列结果，每条事实记着出自哪一列；千问每句要写引用了哪些事实。
- 核对器（check）：说“缺/没有记录”的只能是缺数据的指标；说“未出现”的不能是缺数据的指标；
  提到某套方法时成立与否必须和它的结论一致；数字必须在事实里出现过；不能有诊断、病名、概率。
- 一次生成里有一句没过就重写一次；两次都没全过，就保留程序版本，并把没过的句子和原因摆出来。
- 只读：结果缓存在实例目录 lab/compete_ai.json（按事实指纹），不写星炬、星轨。
"""
from __future__ import annotations

import hashlib
from copy import deepcopy
import compete_claims
import json
import re
import threading
import time
from pathlib import Path

SYSTEM = ("你是一个帮家长看懂化验结果的助手。只能使用用户给出的事实，不能补充任何事实里没有的数字、指标、日期或医学判断；"
          "不写诊断，不写病名，不给总概率，不猜缺失项的值。输出 JSON："
          '{"sentences":[{"text":"一句中文","facts":["引用的事实编号，如 F3"]}],"summary":[{"text":"小结一句","facts":["F2"]}],"next":[{"id":"候选动作编号，如 A2","why":"一句理由"}],"ask":["带去问医生的一个问题"]}。'
          "sentences 4 到 6 句，每句不超过 60 个字；summary 1 到 2 句，根据“换算法再算”的事实说这个等级稳不稳、主要靠哪一套算法撑着，不重复数数，“稳”或“不稳”要和事实一致；"
          "next 从“候选动作”里挑最该先做的 1 到 3 个排好先后，why 用一句人话说为什么先做它，只能用候选里出现过的指标；"
          "ask 写 0 到 3 个带去问医生的问题，只能基于事实和候选，不写用药、治疗、剂量，不给时间承诺。"
          "事实编号只写在 facts 里，text 里不要出现 F1、F2 这类编号。"
          "内容：1) 几套方法分别得出什么；2) 它们为什么不一样（用到的指标不同、缺数据、看的是变化还是界值）；"
          "3) 和上一次比，哪些指标的变化值得关注；4) 还缺哪些数据才能让结论更确定。"
          "注意：前提满足不等于成立，每套方法成立与否只看它那条“结论”事实和“原因”事实；"
          "“缺数据”（没有记录）和“未出现”（记录了没有）是两回事，不能混用。")
SYSTEM_RETRO = ("你是一个帮家长看懂化验结果的助手。只能使用用户给出的事实，不能补充任何事实里没有的数字、指标、日期或医学判断；"
                "不写诊断，不写病名，不给总概率，不猜缺失项的值。事实说的是：同一段时间，换几种方法把每个时点重新算一遍，第一次提示落在哪天。输出 JSON："
                '{"sentences":[{"text":"一句中文","facts":["引用的事实编号，如 F3"]}],"summary":[{"text":"小结一句","facts":["F2"]}],"next":[{"id":"候选动作编号，如 A2","why":"一句理由"}],"ask":["带去问医生的一个问题"]}。'
                "sentences 3 到 5 句，每句不超过 60 个字：几种方法第一次提示分别在哪天、差几天、为什么（哪套规则先看到变化）、哪些一直算不了；"
                "说“早/晚几天”时，谁早谁晚必须和事实一致；summary 1 到 2 句，说这个提前量靠不靠得住、靠的是哪一套方法，不重复数数；"
                "next 从“候选动作”里挑最该先做的 1 到 3 个排好先后，why 用一句人话说为什么先做它；"
                "ask 写 0 到 3 个带去问医生的问题，只能基于事实和候选，不写用药、治疗、剂量，不给时间承诺。"
                "事实编号只写在 facts 里，text 里不要出现 F1、F2 这类编号。"
                "“缺数据”（没有记录）和“未出现”（记录了没有）是两回事，不能混用。")
REF = re.compile(r"[（(]?\s*(?:事实\s*)?F\d+(?:\s*[、,，和及/]\s*F\d+)*\s*[)）]?")  # 句子里夹带的事实编号
SALT = "5"  # 改了写法就换盐，旧缓存作废
CARE_WORDS = ("用药", "服用", "吃药", "停药", "加药", "减药", "剂量", "治疗", "激素", "输液", "住院", "手术")
PROMISE = re.compile(r"\d+\s*(天|小时|周|个月)(内|后|之内)|马上|立即|立刻|尽快")
BANNED = ("诊断", "确诊", "巨噬细胞活化综合征", "概率")
ATTEMPTS = 2
LOCK = threading.Lock()  # 千问一次只写一份
JOBS: dict = {}  # (实例根目录, 指纹) → 状态
_JOBS_LOCK = threading.Lock()  # Only in-memory state; never held across I/O.
_CACHE_LOCK = threading.RLock()  # Cache reads/publication; order CACHE -> JOBS.


def _flat(lines):
    for ln in lines:
        yield ln
        yield from _flat(ln.get("items") or [])


def short_name(col: dict) -> str:
    return re.sub(r"（.*?）", "", col["name"]).strip()


def facts_of(c: dict) -> tuple:
    """事实（文本, 列 id）+ 状态表（指标名 → 缺数据 / 未出现 / 有记录）+ 每套方法的结论。"""
    if c.get("kind") in ("retro", "page"):  # 回溯分叉、星灵页面解读：事实已经拼好
        return [tuple(f) for f in c["facts"]], dict(c.get("status_map") or {}), {}
    out, status = [], {}
    add = lambda text, cid: out.append((text, cid))  # noqa: E731
    for col in c["columns"]:
        name = short_name(col)
        add(f"{name} 的结论：{col['result_zh']}", col["id"])
        for g in col["groups"]:
            if col["id"] != "DYNAMIC" and g["zh"] not in ("前提", "必需"):
                add(f"{name} 的原因：{g['zh']}", col["id"])
        if col.get("missing"):
            add(f"{name} 缺数据（没有记录）：{'、'.join(col['missing'])}", col["id"])
        for m in col.get("missing") or []:
            status[m] = "缺数据"
        for g in col["groups"]:
            for ln in _flat(g["lines"]):
                ind = ln["need"].split(" ")[0].split("：")[0]
                if ind.startswith("以下"):
                    continue
                got = ln.get("got") or ""
                if got == "否" or got.startswith("未出现"):
                    status.setdefault(ind, "未出现")
                elif "没有" in got or ln["outcome"] in ("缺数据", "算不了"):
                    status.setdefault(ind, "缺数据")
                elif ln.get("code"):
                    status.setdefault(ind, "有记录")
                if (ln["outcome"] in ("满足", "超过变化阈值") and not ln["need"].endswith("：是")) or (col["id"] == "DYNAMIC" and got):
                    add(f"{name} · {ln['need']}：{got or '—'}（{ln['outcome']}）", col["id"])
    seen = [k for k, v in status.items() if v == "未出现"]
    if seen:
        add("记录了、但未出现的：" + "、".join(seen), None)
    for i, a in enumerate((c.get("next") or {}).get("actions") or []):
        add(f"候选动作 A{i + 1}：{a['title']}。{a['text']}" + ("问题：" + "；".join(a["ask"]) if a.get("ask") else ""), (a.get("cols") or [None])[0])
    sb = c.get("stability")
    if sb:
        add(f"换算法再算：共 {sb['alt']} 种，其中 {sb['changed']} 种的综合等级不再是“{c['level_zh']}”，"
            + ("这个等级不稳" if not sb["stable"] else "变的只是缺数据算不了，没有相反的结论，这个等级基本稳" if sb["changed"] else "这个等级比较稳"), None)
        for r in sb["rows"]:
            add(f"换算法再算 · {r['zh']}：{r['level_zh']}" + ("（变了）" if r["changed"] else "（没变）"), None)
    return out, status, {short_name(col): col["result"] for col in c["columns"]}


def check(text: str, facts: str, status: dict, results: dict) -> list:
    bad = []
    for clause in re.split(r"[；。;，,]", text):  # 说"缺"的子句里提到的指标，必须真是缺数据
        if re.search(r"缺|没有记录|无记录|无法计算|没记录|没有数据", clause):
            for name, st in status.items():
                if name in clause and st != "缺数据":
                    bad.append(f"把{name}（{st}）说成缺数据")
        if re.search(r"未出现|没有出现|没出现", clause):
            for name, st in status.items():
                if name in clause and st == "缺数据":
                    bad.append(f"把{name}（缺数据）说成未出现")
    names = sorted(results, key=lambda n: text.find(n) if n in text else 1e9)
    for i, n in enumerate(names):  # 提到某套方法时，说的成立与否要和它的结论一致
        if n not in text:
            continue
        start = text.find(n) + len(n)
        nxt = [text.find(m) for m in names[i + 1:] if m in text and text.find(m) > start]
        seg = text[start:min(nxt) if nxt else len(text)]
        r = results[n]
        if r == "NOT_MET" and (re.search(r"(?<!不)(?<!无法判定是否)成立", seg) or re.search(r"(均|都|全部).{0,4}满足", seg)):
            bad.append(f"{n} 实际未达到")
        if r == "MET" and "不成立" in seg:
            bad.append(f"{n} 实际成立")
        if r == "INDETERMINATE" and re.search(r"(?<!无法判定是否)(不?成立)", seg) and "无法" not in seg:
            bad.append(f"{n} 实际算不了")
    known = {x.lstrip("+-") for x in re.findall(r"[-+]?\d+(?:\.\d+)?", facts)}
    for n in re.findall(r"[-+]?\d+(?:\.\d+)?", text):  # 整个数要在事实里出现过（18 不能借 180 的光）
        if n.lstrip("+-") not in known:
            bad.append("数字 " + n + " 不在事实里")
    for w in BANNED:
        if w in text:
            bad.append("用了不该用的词：" + w)
    return bad


DAYS = re.compile(r"(早|晚|提前|推迟|迟)\s*(?:了\s*)?(\d+)\s*天")


def check_retro(text: str, facts: str, status: dict, c: dict) -> list:
    """回溯分叉另加：说“早/晚 N 天”时，N 要是程序算出的天数，谁早谁晚要和它对上；一直算不了的方法不能说成提示了。"""
    bad = check(text, facts, status, {})
    days = {x["verdict"].get("days") for x in c["lanes"] if x["verdict"].get("days")}
    for _, n in DAYS.findall(text):
        if int(n) not in days:
            bad.append(f"差 {n} 天和程序算的不一致")
    names = {}
    for x in c["lanes"]:
        for nm in {x["zh"], x["zh"].replace("只按 ", "")}:
            if len(nm) >= 3:
                names[nm] = x
    hits, raw = [], sorted(((text.find(n), n) for n in names if n in text), key=lambda t: (t[0], -len(t[1])))
    for pos, n in raw:  # “只按 HLH-2004 标准”里的“HLH-2004 标准”不再算一次
        if not hits or pos >= hits[-1][0] + len(hits[-1][1]):
            hits.append((pos, n))
    for i, (pos, n) in enumerate(hits):
        end = next((q for q, m in hits[i + 1:] if q > pos and m not in n), len(text))
        seg, v = text[pos + len(n):end], names[n]["verdict"]["state"]
        mine = re.split(r"[；。]|而|但", seg)[0]
        early = re.search(r"比(现在|正式)[^，。；]{0,6}(早|提前)", mine) or (
            re.search(r"早\s*\d+\s*天|提前", mine) and not re.search(r"(现在的方法|正式结果|正式线|变化规则|变化)[^，。；比]{0,4}(早|提前)", mine))
        if v == "LATE" and early:
            bad.append(f"{n} 实际比现在的方法晚")
        if v == "EARLY" and re.search(r"晚\s*\d+\s*天|推迟", mine):
            bad.append(f"{n} 实际比现在的方法早")
        if v == "NA" and re.search(r"提示|关注", mine) and not re.search(r"算不了|无法|缺", mine):
            bad.append(f"{n} 实际一直算不了")
    return bad


def check_retro_summary(text: str, facts: str, status: dict, c: dict) -> list:
    """回溯小结另加：阈值还是演示占位值时，不能说它已经验证过、靠得住。"""
    bad = check_retro(text, facts, status, c)
    if c.get("placeholder") and re.search(r"(?<![没未])(?<!没有)(?<!还没)(经过|已经|已)验证|靠得住|可靠", text) and not re.search(r"没有经过验证|未经验证|还没验证|没验证|不一定靠得住|不可靠|靠不住", text):
        bad.append("变化阈值还是演示占位值，句子却说它可靠")
    return bad


def check_summary(text: str, facts: str, status: dict, results: dict, stable: bool) -> list:
    """小结另加一条：不能和程序算出的稳不稳相反。"""
    bad = check(text, facts, status, results)
    unsure = re.search(r"不稳|不太稳|不确定|不牢靠|不可靠", text)
    if stable and unsure:
        bad.append("程序算出这个等级比较稳，句子却说不稳")
    if not stable and not unsure and re.search(r"稳|可靠|确定", text):
        bad.append("程序算出这个等级不稳，句子却说稳")
    return bad


def check_next(text: str, facts: str, status: dict, results: dict, allowed: str) -> list:
    """下一步另加三条：只能用候选里出现过的指标；不写用药治疗；不给时间承诺。"""
    bad = check(text, facts, status, results)
    for name in status:
        if len(name) >= 2 and name in text and name not in allowed:
            bad.append(f"{name} 不在候选动作里")
    for w in CARE_WORDS:
        if w in text:
            bad.append("写了用药或治疗：" + w)
    if PROMISE.search(text):
        bad.append("给了时间承诺")
    return bad


FILTER_VERSION = 'secondary-eligible/1'


def prepared_catalog(c):
    """Keep only program statements accepted by the unchanged role-specific guards."""
    facts, status, results = facts_of(c)
    catalog = compete_claims.compile_catalog(c)
    numbered = "\n".join(f"F{i + 1} {t}" for i, (t, _) in enumerate(facts))
    numbered += "\n" + "\n".join(x.text for x in catalog)
    retro = c.get("kind") == "retro"
    sb = c.get("stability") or {}
    acts = (c.get("next") or {}).get("actions") or []
    allowed = " ".join(a["title"] + a["text"] + "".join(a.get("ask") or []) for a in acts)
    def guard(role, text):
        if role == "sentences":
            return check_retro(text, numbered, status, c) if retro else check(text, numbered, status, results)
        if role == "summary":
            return check_retro_summary(text, numbered, status, c) if retro else check_summary(text, numbered, status, results, bool(sb.get("stable")))
        return check_next(text, numbered, status, results, allowed) + (check_retro(text, numbered, status, c) if retro else [])
    return tuple(item for item in catalog if not guard(item.role, item.text)), guard


def fingerprint(c: dict) -> str:
    facts, _, _ = facts_of(c)
    value = [SALT, c["tp"], c["level_zh"], facts]
    if c.get("kind") != "page":
        value.append([FILTER_VERSION, compete_claims.material(prepared_catalog(c)[0])])
    return hashlib.sha256(json.dumps(value, ensure_ascii=False).encode()).hexdigest()[:16]


def write(llm, c: dict) -> dict:
    """Select complete program statements; reject the whole reply on any invalid outlet."""
    if c.get("kind") == "page":
        import starling_page  # noqa: PLC0415
        return starling_page.write(llm, c)
    catalog, guard = prepared_catalog(c)
    t0, tried = time.time(), []
    system = ("只选择、排序给定目录中的完整原文，不改写、不拼接，不增加事实。"
              "输出JSON，sentences与summary为{text,facts:[唯一F编号]}数组，next为{id:目录selection,why:原文}数组，ask为原文字符串数组。"
              "仅使用对应role；正文至少3条，summary最多2条，next和ask各最多3条；无可选项时该节为空。")
    for n in range(1, ATTEMPTS + 1):
        try:
            raw = llm.chat(system, compete_claims.material(catalog))
            m = re.search(r"\{.*\}", raw, re.S)
            doc = json.loads(m.group(0)) if m else None
            bad = []
            if isinstance(doc, dict):
                for role in ("sentences", "summary", "next", "ask"):
                    values = doc.get(role) or []
                    for value in values if isinstance(values, list) else []:
                        text = value if role == "ask" else value.get("why" if role == "next" else "text") if isinstance(value, dict) else None
                        if isinstance(text, str):
                            reasons = guard(role, text)
                            if reasons:
                                bad.append({"text": text, "bad": reasons})
            try:
                selected = compete_claims.select(catalog, doc)
            except ValueError:
                if not bad:
                    bad.append({"text": "", "bad": ["格式不对"]})
            if bad:
                tried.extend(bad)
                continue
            return dict(compete_claims.render(selected), state="ok", rejected=tried,
                        checked=len(selected["sentences"]), seconds=round(time.time()-t0), by=_sign(llm), attempts=n)
        except Exception as exc:  # same two attempts and existing response mapping
            tried.append({"text": "千问没有返回可以读的结果（" + type(exc).__name__ + "）", "bad": ["格式不对"]})
    return {"state": "rejected", "sentences": [], "rejected": tried, "seconds": round(time.time()-t0),
            "by": _sign(llm), "attempts": ATTEMPTS}


def _sign(llm) -> str:
    import starling_page  # noqa: PLC0415
    return starling_page.sign(llm)


def _cache_path(root: Path) -> Path:
    return Path(root) / "lab" / "compete_ai.json"


def _load(root: Path) -> dict:
    with _CACHE_LOCK:
        try:
            return json.loads(_cache_path(root).read_text("utf-8"))
        except (OSError, ValueError):
            return {}


def _save(root: Path, fp: str, res: dict) -> None:
    with _CACHE_LOCK:
        p = _cache_path(root)
        p.parent.mkdir(parents=True, exist_ok=True)
        doc = _load(root)
        doc[fp] = res
        doc = dict(list(doc.items())[-40:])  # 只留最近 40 份
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False), "utf-8")
        tmp.replace(p)


def status(llm, root: Path, c: dict, start: bool = True) -> dict:
    """查（必要时在后台开始）这一时点的千问版本。事实没变就用缓存。"""
    if c.get("kind") != "page":
        c = deepcopy(c)  # Bind the background job to the same immutable input as its key.
    fp = fingerprint(c)
    key = (str(root), fp)
    # Reading the cache and reserving a job are one protocol with completion.
    # File I/O is protected by CACHE only, never by the in-memory JOBS lock.
    with _CACHE_LOCK:
        hit = _load(root).get(fp)
        if hit and (hit.get("state") != "rejected" or not start):
            return dict(hit, fp=fp)
        with _JOBS_LOCK:
            job = JOBS.get(key)
            if job:
                if job["state"] != "running":
                    JOBS.pop(key, None)  # 告诉一次，下次再试
                return dict(job, fp=fp)
            if llm is None or not llm.cfg.get("model"):
                return {"state": "no_llm", "fp": fp}
            if not start:
                return {"state": "idle", "fp": fp}
            owned = {"state": "running", "since": time.time()}
            JOBS[key] = owned

    def failed(state, **fields):
        with _JOBS_LOCK:
            if JOBS.get(key) is owned:
                JOBS[key] = dict(state=state, **fields)

    def run():
        try:
            with LOCK:
                if not llm.ensure():
                    failed("no_llm")
                    return
                res = write(llm, c)
            with _CACHE_LOCK:
                _save(root, fp, res)
                with _JOBS_LOCK:
                    if JOBS.get(key) is owned:
                        JOBS.pop(key)
        except Exception as e:  # noqa: BLE001
            failed("error", why=type(e).__name__)

    try:
        threading.Thread(target=run, daemon=True).start()
    except Exception as e:  # Reservation must not remain running after start fails.
        failed("error", why=type(e).__name__)
        return {"state": "error", "why": type(e).__name__, "fp": fp}
    return {"state": "running", "fp": fp}
