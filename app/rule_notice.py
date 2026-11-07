"""规则触发，星灵转告（产品负责人 2026-10-14 00:37 / 00:42 / 00:43）。

- 触发器是状态规则库里的规则，不是星灵：只有本来就有阈值、本来就会发提醒的规则（sJIA 关注卡、我自建的阈值卡），
  等级到“观察”或“关注”、写进状态通知的那一条，才会在星灵图标上方弹小卡。分支卡、基因卡、“有新结果”通知不弹。L3 仍然关闭。
- 小卡上的话是程序按规则写的固定句式（就是提醒原文 + 一句“建议尽快联系主治医生复查”），不调千问。
- “星灵讲讲”一直在（产品负责人：客户可以不问，但不能没有）：点了才让本机千问讲“为什么触发”。只给规则名、各路结论、
  变化方向、发提醒的规矩，不给健康数值和阈值数值（HR-42）；逐句核对，不兜底。
- “加到日历”：生成一条 .ics，Mac 上用“日历”打开，我点“添加”才加进去。日历会同步到 iCloud，所以里面不写任何数值、指标和卡名。
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import evidence_graph
import rule_registry
from cards import open_startrack
from custom_cards import METHODS
from dynamic import change_word

LEVELS = ("ALERT", "WATCH")
LEVEL_ZH = evidence_graph.LEVEL_ZH
CHANNEL_ZH = {"BANNER": "界面横幅", "MACOS": "Mac 系统通知"}
ADVICE = "建议尽快联系主治医生复查。这不是诊断。"
CAL_TITLE = "复查预约（请自己联系医院）"
CAL_NOTE = "PTDS 规则提醒，详情在本机 PTDS 查看。这不是医嘱，也不是挂号，请自己联系医院预约。"


def _set_of(card_id: str) -> tuple:
    if card_id == "sjia-mas":
        return "MAS", None  # Composite notification belongs to the set, not a retired demo rule.
    return "CUSTOM", "CUSTOM." + card_id


def notice(snap: dict, hidden: set, replay: bool) -> dict | None:
    """最新一条没读过的规则提醒（观察 / 关注）。回放实例、隐藏的卡不弹。"""
    if replay:
        return None
    custom = {c["card_id"] for c in snap.get("custom_cards") or []}
    cand = [a for a in snap.get("alerts") or [] if a.get("level") in LEVELS and not a.get("acked")
            and a.get("card_id") not in hidden and (a.get("card_id") == "sjia-mas" or a.get("card_id") in custom)]
    if not cand:
        return None
    a = max(cand, key=lambda x: (x.get("created_at") or "", x["dedupe_key"]))
    rs, rid = _set_of(a["card_id"])
    return {"dedupe_key": a["dedupe_key"], "tp": a.get("tp"), "level": a["level"], "level_zh": LEVEL_ZH.get(a["level"], a["level"]),
            "title": a["title"], "body": a["body"], "advice": ADVICE, "card_id": a["card_id"], "created_at": a.get("created_at"),
            "rule_set": rs, "rule_set_zh": rule_registry.SET_ZH.get(rs, rs), "rule_id": rid}


# ----------------------------------------------------------------------------- 星灵讲讲：为什么触发

SYSTEM = ("你是“星灵”。用户问：这条提醒为什么触发？只根据给出的记录事实，用平常话讲清楚三件事：提醒来自哪套规则；"
          "哪几路结论把等级推到了这一级；提醒是按什么规矩发出来的。不能补充事实里没有的数字、日期或判断；"
          "不写诊断、病名、治疗、用药或就医建议，不评价严重程度，不推测原因。输出 JSON："
          '{"sentences":[{"text":"一句中文","facts":["引用的事实编号，如 F3"]}]}。'
          "sentences 2 到 4 句，每句不超过 60 个字，先说最重要的；text 里不要出现 F1 这类编号。")


def _alert_row(inst, key: str):
    track = open_startrack(inst.ctx)
    try:
        row = track.execute("SELECT card_id, tp_date, level, run_id, created_at FROM alert_log WHERE dedupe_key = ?", (key,)).fetchone()
        if row is None:
            return None, None
        res = track.execute("SELECT result FROM run_tp WHERE run_id = ? AND tp_date = ?", (row[3], row[1])).fetchone()
        return dict(zip(("card_id", "tp", "level", "run_id", "created_at"), row)), (json.loads(res[0]) if res else None)
    finally:
        track.close()


def _when(iso: str) -> str:
    s = str(iso or "")
    return s[:10] + (" " + s[11:16] if len(s) >= 16 else "")


def why_ctx(inst, snap: dict, key: str) -> dict | None:
    """→ starling_page 的上下文（facts / literals）；找不到这条提醒或卡被隐藏 → None。"""
    a, res = _alert_row(inst, key)
    import engines  # noqa: PLC0415
    tpl_alert = str(a["card_id"] if a else "").startswith(engines.TPL_PREFIX)  # 卡组“有新结果时通知我”（不定级，等级 NONE）
    if a is None or a["card_id"] in evidence_graph.hidden_cards(inst) or (a["level"] not in LEVELS and not tpl_alert):
        return None
    delivered = next((x for x in snap.get("alerts") or [] if x["dedupe_key"] == key), {}).get("deliveries") or []
    facts, lits = [], set()
    add = lambda t: facts.append((t, None))  # noqa: E731
    lv = LEVEL_ZH.get(a["level"], "新结果")
    if tpl_alert:  # 产品负责人 2026-10-15：卡组新结果的提醒也能让星灵讲（原来只有关注 / 观察两级）
        tpl = a["card_id"][len(engines.TPL_PREFIX):]
        T = engines.TEMPLATES.get(tpl, {})
        zh, set_zh = T.get("zh", tpl), rule_registry.SET_ZH.get(tpl, tpl)
        names = [rule_registry.BY_ID[r]["name"] for r in T.get("rules", []) if r in rule_registry.BY_ID]
        lits |= {zh, set_zh} | set(names)
        add(f"这条提醒来自卡组「{zh}」，规则在状态规则库的「{set_zh}」里：{'、'.join(names)}")
        add(f"{a['tp']} 这个时点有了新结果（计算 #{a['run_id']}），提醒在 {_when(a['created_at'])} 写进了状态通知")
        add("这组卡只列读数和与上次比的变化，不设阈值、不定级；建这组卡时选了“有新结果时通知我”，所以每次有新结果都提醒一次")
    elif a["card_id"] == "sjia-mas":
        rp = inst.app.rulepack
        name = lambda rid: re.sub(r"（R\d+）", "", rp["rules"][rid].get("short_zh", rid))  # noqa: E731
        set_zh = rule_registry.SET_ZH["MAS"]
        rules = list(rp["rules"])
        lits |= {set_zh, "sJIA 关注卡"} | {name(r) for r in rules}
        add(f"这条提醒来自状态规则库里的「{set_zh}」，算的是 sJIA 关注卡在 {a['tp']} 这个时点（计算 #{a['run_id']}）")
        add(f"那次计算合起来的关注等级是“{lv}”，提醒在 {_when(a['created_at'])} 写进了状态通知")
        add("合起来的规矩：各套标准里任一套成立，或者核心指标和上一个时点比变化超过变化阈值，等级就是“关注”；"
            "只有一般指标的变化超过阈值、而且够一定项数，等级是“观察”")
        if res:
            for rid in rules:
                r = res["rules"].get(rid) or {}
                zh = {"MET": "成立", "NOT_MET": "不成立", "INDETERMINATE": "缺数据，无法判定"}.get(r.get("result"), "没有结果")
                miss = r.get("missing") or []
                add(f"{name(rid)}：{zh}" + (f"，缺 {len(miss)} 项数据" if miss else ""))
            hit = [i for i in res["dynamic"].get("indicators") or [] if i.get("status") == "TRIGGERED"]
            base = sorted({i["base_tp"] for i in hit if i.get("base_tp")})
            lits |= {i["label_zh"] for i in hit}
            if hit:
                add("变化：" + (f"和 {'、'.join(base)} 比，" if base else "") + "超过变化阈值的有 " +
                    "、".join(f"{i['label_zh']}{change_word(i['bad_direction'], i.get('measure'))}（{'核心' if i['role'] == 'CORE' else '一般'}指标）" for i in hit))
            else:
                add("变化：和上一个时点比，没有指标超过变化阈值")
            met = [name(d["rule"]) for d in res.get("drivers") or [] if d.get("kind") == "RULE" and d.get("result") == "MET"]
            core = [i for i in hit if i["role"] == "CORE"]
            moved = core if a["level"] == "ALERT" else [i for i in hit if i["role"] != "CORE"]
            push = met + (["指标变化（" + "、".join(i["label_zh"] + change_word(i["bad_direction"], i.get("measure")) for i in moved) + "）"] if moved else [])
            add(f"把等级推到“{lv}”的是：" + "、".join(push) if push else f"等级“{lv}”没有记下推动它的规则")
        add("变化阈值是本工程的演示默认值，不出自文献；三套标准的参数出自原文，还待专家核实")
    else:
        c = next((x for x in snap.get("custom_cards") or [] if x["card_id"] == a["card_id"]), None)
        if c is None:
            return None
        d = c["definition"]
        lits |= {c["name"], d.get("label_zh") or "", rule_registry.SET_ZH["CUSTOM"]}
        add(f"这条提醒来自你自建的状态卡「{c['name']}」，规则在状态规则库的「{rule_registry.SET_ZH['CUSTOM']}」里，是你自己设的")
        add(f"规则：{d.get('label_zh')}{METHODS.get(d.get('method'), '')}你设的阈值，等级记为“{lv}”")
        add(f"{a['tp']} 这个时点的读数达到了这条规则（计算 #{a['run_id']}），提醒在 {_when(a['created_at'])} 写进了状态通知")
    if not tpl_alert:  # 卡组的“新结果”提醒不按等级升降发，这条规矩对它不成立，不能交给星灵
        add("发提醒的规矩：只看最新一个时点的等级，比上一次记下的等级高才提醒；同一时点同一等级只提醒一次")
    ok = [CHANNEL_ZH.get(x.get("channel"), x.get("channel")) for x in delivered if x.get("outcome") == "SENT"]
    add("这条提醒送到了：" + "、".join(ok) if ok else "这条提醒还没有送到任何通道")
    add("提醒里只写变化的方向，具体读数和阈值数值不交给星灵")
    return {"kind": "page", "page": "alert", "page_zh": "这条提醒为什么触发", "tp": "ALERT:" + key, "level_zh": lv,
            "facts": facts, "status_map": {}, "system": SYSTEM, "allow": ("阈值",), "literals": {x for x in lits if x}}


# ----------------------------------------------------------------------------- 加到日历

def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def ics(key: str, day: date, hhmm: str, now_utc: datetime, tz: str = "Asia/Shanghai") -> str:
    """一条日历事件。只有固定标题和说明：不写数值、指标、卡名、等级（会同步到 iCloud）。"""
    h, m = (int(x) for x in hhmm.split(":"))
    start = datetime(day.year, day.month, day.day, h, m)
    end = start + timedelta(minutes=30)
    f = lambda t: t.strftime("%Y%m%dT%H%M%S")  # noqa: E731
    uid = hashlib.sha256(f"{key}|{day.isoformat()}|{hhmm}".encode()).hexdigest()[:24] + "@ptds.local"
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//PTDS//rule-notice//ZH", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
             "BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{now_utc.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
             f"DTSTART;TZID={tz}:{f(start)}", f"DTEND;TZID={tz}:{f(end)}", f"SUMMARY:{_esc(CAL_TITLE)}",
             f"DESCRIPTION:{_esc(CAL_NOTE)}", "BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_esc(CAL_TITLE)}",
             "TRIGGER:-P1D", "END:VALARM", "END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(lines) + "\r\n"


def calendar(root: Path, key: str, day_s: str, hhmm: str, today: date, now_utc: datetime, tz: str) -> dict:
    """校验日期时间，写 .ics 到实例目录，记一笔（只记提醒编号和日期）。→ {path, ics, day, time}。"""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day_s or ""):
        day = today + timedelta(days=2)
    else:
        day = date.fromisoformat(day_s)
    if not today <= day <= today + timedelta(days=180):
        raise ValueError("DATE_RANGE")
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", hhmm or ""):
        hhmm = "09:00"
    text = ics(key, day, hhmm, now_utc, tz)
    d = root / "calendar"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"recheck-{day.isoformat()}-{hashlib.sha256(key.encode()).hexdigest()[:8]}.ics"
    path.write_text(text, "utf-8")
    with open(d / "calendar.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": now_utc.isoformat(timespec="seconds"), "alert": key, "day": day.isoformat(), "time": hhmm,
                             "file": path.name}, ensure_ascii=False) + "\n")
    return {"path": str(path), "ics": text, "day": day.isoformat(), "time": hhmm, "file": path.name}
