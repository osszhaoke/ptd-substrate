"""星轨 · 计算引擎模板（产品负责人 2026-10-14 批准 R05、R06）：状态工程里选模板 → 绑数据 → 定规则 → 配通知 → 审方案。

- 一个模板 = 一个卡片组；组里每张算法卡对应状态规则库里的一条规则（编号@版本，见 rule_registry）。
- 建好之后，星轨每次同步都按各卡的定义算新时点、数据有变化的时点；每次计算、用了哪条数据（哪一版）都写进
  星轨原有的账本（card_def / run / run_tp / run_input），和 sJIA 关注卡、自定义卡同一套，证据图谱能追。旧结果不删。
- 引擎的启用、规则选择、通知设置、“看过到哪一次”都只追加写在 card_setting；不改任何表结构。
- 计算状态和等级分开：结果里写“已算出 / 数据不足 / 输入无效 / 不适用”；这些卡没有阈值规则，等级一律 NONE。
- 结果是计算，不是诊断。界面、通知不出现病名（L-34）。
"""
from __future__ import annotations

import compute_snapshot
import json
import math
import statistics
from datetime import date, timedelta

import bioage
import rule_registry as RR
from cards import latest_results
from h1_common import canonical_bytes, canonical_json, parse_instant, sha256_hex
from sqlite_util import transaction

ENGINE = "engine/0.1"
TPL_PREFIX = "engine-tpl-"
CARD_PREFIX = "engine-"
SUFFIX = "这是计算结果，不是诊断。"
STATUS_ZH = {"computed": "已算出", "insufficient_data": "数据不足", "invalid_input": "输入无效", "not_applicable": "不适用"}
TRIGGER_ZH = {"SYNC": "新数据", "AUTO_UPDATE": "数据有更正或补充", "RECOMPUTE": "定义变了，重算"}

TEMPLATES = {
    "BIOAGE": {"zh": "生物年龄（Biological Age）计算引擎", "sub": "三种算法，同一份血检各算一遍",
               "rules": ["BIOAGE.PHENOAGE", "BIOAGE.KDM", "BIOAGE.HD"], "notify": "optional"},
    "SLEEP": {"zh": "睡眠恢复观察", "sub": "睡眠时长、效率，以及夜间 HRV、最低心率相对自己基线的偏离",
              "rules": ["SLEEP.A01-DURATION", "SLEEP.A02-EFFICIENCY", "SLEEP.A03-HRV-DEV", "SLEEP.A04-LOWHR-DEV",
                        "SLEEP.A05S-TIMING"], "notify": "optional"},
    "INFLAM": {"zh": "炎症免疫观察", "sub": "CRP 读数与变化、中性粒/淋巴比",
               "rules": ["INFLAM.B01-CRP", "INFLAM.B02-NLR"], "notify": "optional"},
    "METAB": {"zh": "代谢观察", "sub": "糖化血红蛋白、非 HDL 胆固醇", "rules": ["METAB.D01-HBA1C", "METAB.D02-NONHDL"],
              "notify": "optional"},
    "ORGAN": {"zh": "器官功能观察", "sub": "按 CKD-EPI 2021 算 eGFR", "rules": ["ORGAN.E01-EGFR"], "notify": "optional"},
    "BLOOD": {"zh": "血液细胞观察", "sub": "血小板、中性粒细胞、白细胞、血红蛋白：每次读数和与上次比的变化，不设阈值",
              "rules": [f"BLOOD.{c}" for c, _ in RR.BRANCH["BLOOD"]], "notify": "optional"},
    "COAG": {"zh": "凝血观察", "sub": "纤维蛋白原、D-二聚体、PT、INR、APTT：每次读数和与上次比的变化，不设阈值",
             "rules": [f"COAG.{c}" for c, _ in RR.BRANCH["COAG"]], "notify": "optional"},
    "LIVER": {"zh": "肝脏观察", "sub": "转氨酶、LDH、胆红素、白蛋白、甘油三酯：每次读数和与上次比的变化，不设阈值",
              "rules": [f"LIVER.{c}" for c, _ in RR.BRANCH["LIVER"]], "notify": "optional"},
    "RHYTHM": {"zh": "生理节律观察", "sub": "夜间体温相对基线的偏离", "rules": ["RHYTHM.F01-TEMPDEV"], "notify": "optional"},
    "EXERCISE": {"zh": "运动观察", "sub": "近 7 天运动时长与次数", "rules": ["EXERCISE.C01-WEEKLY"], "notify": "optional"},
}
ORDER = ["BLOOD", "COAG", "LIVER", "BIOAGE", "SLEEP", "INFLAM", "METAB", "ORGAN", "RHYTHM", "EXERCISE"]


class EngineError(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(code)
        self.code, self.detail = code, detail


# ----------------------------------------------------------------------------- 取数小工具

def _latest(obs: list):
    return max(obs, key=lambda o: (o.instant.isoformat() if o.instant else "", o.revision, o.observation_id))


def _on(groups, code, day):
    obs = (groups.get(code) or {}).get(day)
    return _latest(obs) if obs else None


def _f(o) -> float:
    return float(o.value)


def _batch(o) -> str:
    """同一份报告：来源引用 # 号之前那段相同（同一次录入 / 识别 / 导入）。"""
    return str((o.payload or {}).get("source_ref") or "").split("#")[0]


def _shown(o, label=None) -> dict:
    return {"ref": o.ref, "code": o.code, "label": label or o.code, "value": (o.comparator or "") + format(o.value, "f"),
            "unit": o.unit, "day": o.day}


def _g(x) -> str:
    return format(x, "g") if isinstance(x, float) else str(x)


def _res(status, value=None, unit="", text=None, tp=None, hist=None, reason=None, extra=None) -> dict:
    return {"status": status, "value": value, "unit": unit, "text": text, "reason": reason, "extra": extra or {},
            "tp": list(tp or []), "hist": list(hist or [])}


def _days(groups, *codes) -> set:
    out = set()
    for c in codes:
        out |= set(groups.get(c) or {})
    return out


def _baseline(groups, codes, day, days_back, lag, min_n):
    lo = (date.fromisoformat(day) - timedelta(days=days_back + lag - 1)).isoformat()
    hi = (date.fromisoformat(day) - timedelta(days=lag)).isoformat()
    vals = {}
    for c in codes:
        for d, obs in (groups.get(c) or {}).items():
            if lo <= d <= hi and d not in vals:
                vals[d] = _latest(obs)
    return vals, len(vals) >= min_n


def _pick(groups, codes, day):
    for c in codes:
        o = _on(groups, c, day)
        if o is not None:
            return o
    return None


def _prev(groups, code, day):
    before = sorted(d for d in (groups.get(code) or {}) if d < day)
    return _latest(groups[code][before[-1]]) if before else None


# ----------------------------------------------------------------------------- 各规则的计算（day → 结果）

def _dev(codes, unit, digits):
    m = {"baseline_days": 28, "lag": 1, "min": 14}

    def days(groups):
        return _days(groups, *codes)

    def run(groups, day, prof):
        cur = _pick(groups, codes, day)
        if cur is None:
            return _res("insufficient_data", reason="当晚没有读数")
        base, ok = _baseline(groups, codes, day, m["baseline_days"], m["lag"], m["min"])
        if not ok:
            return _res("insufficient_data", tp=[cur], hist=base.values(),
                        reason=f"基线不足：前 {m['baseline_days']} 天只有 {len(base)} 晚，至少要 {m['min']} 晚")
        med = statistics.median(_f(o) for o in base.values())
        d = _f(cur) - med
        pct = None if med == 0 else round(d / med * 100, 1)
        sign = "+" if d > 0 else ""
        return _res("computed", round(d, digits), unit, f"{sign}{_g(round(d, digits))} {unit}" + (f"（{sign}{_g(pct)}%）" if pct is not None else ""),
                    tp=[cur], hist=base.values(),
                    extra={"current": _f(cur), "baseline_median": round(med, digits), "baseline_nights": len(base), "pct": pct})
    return days, run


def _a01_days(groups):
    return _days(groups, "OURA_TOTAL_SLEEP", "AH_SLEEP")


def _a01(groups, day, prof):
    o = _pick(groups, ["OURA_TOTAL_SLEEP", "AH_SLEEP"], day)
    if o is None:
        return _res("insufficient_data", reason="当晚没有睡眠时长")
    h = round(_f(o) / 60, 2)
    return _res("computed", h, "小时", f"{_g(h)} 小时", tp=[o], extra={"source": "Oura" if o.code.startswith("OURA") else "苹果健康"})


def _a02_days(groups):
    return _days(groups, "OURA_TOTAL_SLEEP") & _days(groups, "OURA_TIME_IN_BED")


def _a02(groups, day, prof):
    t, b = _on(groups, "OURA_TOTAL_SLEEP", day), _on(groups, "OURA_TIME_IN_BED", day)
    if t is None or b is None:
        return _res("insufficient_data", tp=[x for x in (t, b) if x], reason="缺总睡眠或卧床时长")
    if (t.payload or {}).get("source_ref") != (b.payload or {}).get("source_ref"):
        return _res("invalid_input", tp=[t, b], reason="两项不是同一条睡眠记录")
    if _f(b) <= 0 or _f(t) > _f(b):
        return _res("invalid_input", tp=[t, b], reason="卧床时长为 0 或小于总睡眠")
    v = round(100 * _f(t) / _f(b), 1)
    return _res("computed", v, "%", f"{_g(v)}%", tp=[t, b])


def _circ_sd(mins):
    ang = [m / 1440 * 2 * math.pi for m in mins]
    c, s = sum(math.cos(a) for a in ang) / len(ang), sum(math.sin(a) for a in ang) / len(ang)
    r = min(max(math.hypot(c, s), 1e-12), 1.0)
    return math.sqrt(-2 * math.log(r)) * 1440 / (2 * math.pi)


def _a05_days(groups):
    return _days(groups, "OURA_BEDTIME_START") & _days(groups, "OURA_BEDTIME_END")


def _a05(groups, day, prof):
    lo = (date.fromisoformat(day) - timedelta(days=13)).isoformat()
    nights = [d for d in _a05_days(groups) if lo <= d <= day]
    if len(nights) < 7:
        return _res("insufficient_data", reason=f"近 14 天只有 {len(nights)} 晚有入睡、醒来时刻，至少要 7 晚")
    st = [_on(groups, "OURA_BEDTIME_START", d) for d in nights]
    en = [_on(groups, "OURA_BEDTIME_END", d) for d in nights]
    a, b = _circ_sd([_f(o) for o in st]), _circ_sd([_f(o) for o in en])
    v = round((a + b) / 2, 1)
    cur = [o for o in st + en if o.day == day]
    return _res("computed", v, "分钟", f"{_g(v)} 分钟", tp=cur, hist=[o for o in st + en if o.day != day],
                extra={"start_sd": round(a, 1), "end_sd": round(b, 1), "nights": len(nights), "not_sri": True})


def _b01_days(groups):
    return _days(groups, "HSCRP", "CRP")


def _b01(groups, day, prof):
    o = _pick(groups, ["HSCRP", "CRP"], day)
    if o is None:
        return _res("insufficient_data", reason="当天没有 CRP")
    p = _prev(groups, o.code, day)
    ex = {"assay": "超敏 CRP" if o.code == "HSCRP" else "CRP"}
    if p is not None and not p.comparator and not o.comparator:
        ex.update(prev_day=p.day, change=round(_f(o) - _f(p), 2),
                  change_pct=None if _f(p) == 0 else round((_f(o) - _f(p)) / _f(p) * 100, 1))
    txt = (o.comparator or "") + format(o.value, "f") + " mg/L"
    return _res("computed", _f(o), "mg/L", txt, tp=[o], hist=[p] if p else [], extra=ex,
                reason="报告写的是带 < > 的值，原样显示" if o.comparator else None)


def _pair(code_a, code_b, op, unit, digits, check=None):
    def days(groups):
        return _days(groups, code_a) & _days(groups, code_b)

    def run(groups, day, prof):
        a, b = _on(groups, code_a, day), _on(groups, code_b, day)
        if a is None or b is None:
            return _res("insufficient_data", tp=[x for x in (a, b) if x], reason="同一天缺其中一项")
        if _batch(a) != _batch(b):
            return _res("invalid_input", tp=[a, b], reason="两项不在同一份报告里，不跨报告拼接")
        if a.comparator or b.comparator:
            return _res("invalid_input", tp=[a, b], reason="报告带 < 或 >，算不了确定值")
        bad = check(_f(a), _f(b)) if check else None
        if bad:
            return _res("invalid_input", tp=[a, b], reason=bad)
        v = round(op(_f(a), _f(b)), digits)
        return _res("computed", v, unit, _g(v) + (f" {unit}" if unit else ""), tp=[a, b])
    return days, run


def _c01_days(groups):
    return _days(groups, "OURA_WORKOUT_MIN")


def _c01(groups, day, prof):
    lo = (date.fromisoformat(day) - timedelta(days=6)).isoformat()
    ses = [o for d, obs in (groups.get("OURA_WORKOUT_MIN") or {}).items() if lo <= d <= day for o in obs]
    if not ses:
        return _res("insufficient_data", reason="近 7 天没有运动记录")
    mins = round(sum(_f(o) for o in ses))
    return _res("computed", mins, "分钟", f"{mins} 分钟 · {len(ses)} 次", tp=[o for o in ses if o.day == day],
                hist=[o for o in ses if o.day != day], extra={"sessions": len(ses)})


def _d01_days(groups):
    return _days(groups, "HBA1C")


def _d01(groups, day, prof):
    o = _on(groups, "HBA1C", day)
    p = _prev(groups, "HBA1C", day)
    ex = {}
    if p is not None and not p.comparator and not o.comparator:
        ex.update(prev_day=p.day, change=round(_f(o) - _f(p), 2))
    return _res("computed", _f(o), "%", (o.comparator or "") + format(o.value, "f") + "%", tp=[o], hist=[p] if p else [], extra=ex)


def _e01_days(groups):
    return _days(groups, "CREA")


def _e01(groups, day, prof):
    o = _on(groups, "CREA", day)
    if not (prof.get("birth_date") and prof.get("sex")):
        return _res("insufficient_data", tp=[o], reason="缺出生日期或性别")
    age = bioage.age_at(prof["birth_date"], day)
    if age < 18:
        return _res("not_applicable", tp=[o], reason="CKD-EPI 2021 只用于 18 岁以上")
    if o.comparator:
        return _res("invalid_input", tp=[o], reason="肌酐带 < 或 >，算不了确定值")
    scr = _f(o) / 88.4
    if scr <= 0:
        return _res("invalid_input", tp=[o], reason="肌酐为 0")
    f = prof["sex"] == "女"
    k, a = (0.7, -0.241) if f else (0.9, -0.302)
    g = 142 * min(scr / k, 1) ** a * max(scr / k, 1) ** -1.200 * 0.9938 ** age * (1.012 if f else 1)
    v = round(g)
    return _res("computed", v, "mL/min/1.73m²", f"{v} mL/min/1.73m²", tp=[o],
                extra={"age": round(age, 1), "scr_mg_dl": round(scr, 3), "sex": prof["sex"]})


def _f01_days(groups):
    return _days(groups, "OURA_TEMP_DEV")


def _f01(groups, day, prof):
    o = _on(groups, "OURA_TEMP_DEV", day)
    v = _f(o)
    return _res("computed", v, "°C", ("+" if v > 0 else "") + format(o.value, "f") + " °C", tp=[o])


def _bio(method):
    def days(groups):
        return {d for c, _, _ in bioage.MARKERS for d in (groups.get(c) or {})} | set(groups.get("HSCRP") or {})

    def run(groups, day, prof):
        if not (prof.get("birth_date") and prof.get("sex")):
            return _res("insufficient_data", reason="缺出生日期或性别")
        age = bioage.age_at(prof["birth_date"], day)
        x = bioage.inputs_at(groups, day)
        def parameters():
            captured = prof.get('_compute_parameters')
            return captured.unwrap() if captured is not None else None
        r = {"PHENOAGE": lambda: bioage.phenoage(x, age), "KDM": lambda: bioage.kdm(x, age, prof["sex"], parameters=parameters()),
             "HD": lambda: bioage.hd(x, age, prof["sex"], parameters=parameters())}[method]()
        used = [i for i in x.values() if not i.get("missing")]
        tp = [_Ref(i["ref"], i["source_code"], i["day"]) for i in used if not i.get("borrowed")]
        hist = [_Ref(i["ref"], i["source_code"], i["day"]) for i in used if i.get("borrowed")]
        if not r.get("ok"):
            miss = r.get("missing") or []
            return _res("insufficient_data", tp=tp, hist=hist,
                        reason=("缺：" + "、".join(bioage.ZH.get(c, c) for c in miss)) if miss else (r.get("error") or "算不了"))
        unit = "岁" if method != "HD" else "分"
        txt = f"{_g(r['value'])} {unit}"
        ex = {"age": round(age, 1), "delta": r.get("delta"), **(r.get("extra") or {}),
              "inputs": [{k: i.get(k) for k in ("label_zh", "value_text", "unit", "day", "borrowed", "note", "missing")}
                         for i in x.values()]}
        return _res("computed", r["value"], unit, txt, tp=tp, hist=hist, extra=ex)
    return days, run


class _Ref:
    """生物年龄的输入来自 bioage.inputs_at（字典），这里还原成账本要的 观测编号@版本。"""
    def __init__(self, ref, code, day):
        self.observation_id, rev = ref.rsplit("@", 1)
        self.revision, self.code, self.day = int(rev), code, day
        self.ref = ref


def _obs(code):
    """分器官观察：当天读数 + 与上一次同项读数比的变化。不设阈值、不判好坏（R03 没有给出变化阈值）。"""
    def days(groups):
        return _days(groups, code)

    def run(groups, day, prof):
        o = _on(groups, code, day)
        p = _prev(groups, code, day)
        ex = {}
        if p is not None:
            ex.update(prev_day=p.day, prev_text=(p.comparator or "") + format(p.value, "f") + (" " + p.unit if p.unit else ""))
            if not p.comparator and not o.comparator:
                ex.update(change=round(_f(o) - _f(p), 3),
                          change_pct=None if _f(p) == 0 else round((_f(o) - _f(p)) / _f(p) * 100, 1))
        txt = (o.comparator or "") + format(o.value, "f") + (" " + o.unit if o.unit else "")
        return _res("computed", _f(o), o.unit or "", txt, tp=[o], hist=[p] if p else [], extra=ex,
                    reason="报告写的是带 < > 的值，原样显示，不算变化" if o.comparator else None)
    return days, run


_D_A03 = _dev(["OURA_HRV"], "ms", 1)
_D_A04 = _dev(["OURA_LOWEST_HR", "OURA_RESTING_HR"], "bpm", 1)
_D_B02 = _pair("ANC", "LYMPH", lambda a, b: a / b, "", 2, lambda a, b: "淋巴细胞绝对值为 0，不能相除" if b <= 0 else None)
_D_D02 = _pair("TC", "HDL_C", lambda a, b: a - b, "mmol/L", 2)
CALC = {
    "BIOAGE.PHENOAGE": _bio("PHENOAGE"), "BIOAGE.KDM": _bio("KDM"), "BIOAGE.HD": _bio("HD"),
    "SLEEP.A01-DURATION": (_a01_days, _a01), "SLEEP.A02-EFFICIENCY": (_a02_days, _a02), "SLEEP.A03-HRV-DEV": _D_A03,
    "SLEEP.A04-LOWHR-DEV": _D_A04, "SLEEP.A05S-TIMING": (_a05_days, _a05), "INFLAM.B01-CRP": (_b01_days, _b01),
    "INFLAM.B02-NLR": _D_B02, "EXERCISE.C01-WEEKLY": (_c01_days, _c01), "METAB.D01-HBA1C": (_d01_days, _d01),
    "METAB.D02-NONHDL": _D_D02, "ORGAN.E01-EGFR": (_e01_days, _e01), "RHYTHM.F01-TEMPDEV": (_f01_days, _f01),
}
CALC.update({f"{s}.{c}": _obs(c) for s, items in RR.BRANCH.items() for c, _ in items})


def evaluate(rule_id: str, groups: dict, day: str, prof: dict) -> tuple:
    """一个时点 → (结果, 输入集合)。结果里不放观测对象，只放能落账的字段。"""
    r = CALC[rule_id][1](groups, day, prof)
    inputs = {(o.observation_id, o.revision, "TP") for o in r["tp"] if o is not None}
    inputs |= {(o.observation_id, o.revision, "HISTORY") for o in r["hist"] if o is not None
               and (o.observation_id, o.revision, "TP") not in inputs}
    used = [dict(_shown(o) if hasattr(o, "payload") else {"ref": o.ref, "code": o.code, "day": o.day}, role=role)
            for role, lst in (("TP", r["tp"]), ("HISTORY", r["hist"])) for o in lst if o is not None]
    out = {"tp": day, "engine_version": ENGINE, "rule": RR.ref(rule_id), "fingerprint": RR.fingerprint(rule_id),
           "status": r["status"], "value": r["value"], "unit": r["unit"], "text": r["text"], "reason": r["reason"],
           "extra": r["extra"], "used": used[:60], "used_count": len(used)}
    return _nofloat(json.loads(json.dumps(out, default=str))), frozenset(inputs)


def _nofloat(x):
    """账本里的 JSON 不许有浮点数（canonical_json）：数值一律存成十进制字符串。"""
    if isinstance(x, bool) or x is None:
        return x
    if isinstance(x, float):
        return format(x, ".10g")
    if isinstance(x, dict):
        return {k: _nofloat(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_nofloat(v) for v in x]
    return x


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# ----------------------------------------------------------------------------- 引擎登记（只追加）

def _settings(track) -> dict:
    out = {}
    for cid, key, val, at in track.execute("SELECT card_id, key, value, set_at FROM card_setting "
                                           "WHERE substr(card_id, 1, ?) = ? ORDER BY id", (len(TPL_PREFIX), TPL_PREFIX)):
        if cid[len(TPL_PREFIX):] not in TEMPLATES:
            continue
        t = out.setdefault(cid[len(TPL_PREFIX):], {"active": False, "conf": None, "seen": 0, "created_at": at})
        if key == "engine_status":
            t["active"] = val == "ACTIVE"
            t["status_at"] = at
        elif key == "engine_conf":
            t["conf"] = json.loads(val)
        elif key == "seen_run":
            t["seen"] = max(t["seen"], int(val))
    return out


def active(track) -> dict:
    return {k: v for k, v in _settings(track).items() if v["active"] and v["conf"]}


def create(track, tpl: str, body: dict, *, at: str, sjia: bool) -> dict:
    if tpl not in TEMPLATES:
        raise EngineError("TEMPLATE_UNKNOWN", tpl)
    T = TEMPLATES[tpl]
    rules = [r for r in (body.get("rules") or T["rules"]) if r in T["rules"]]
    if not rules:
        raise EngineError("RULES_EMPTY", "至少选一条规则")
    notify = bool(body.get("notify_self"))
    if T["notify"] == "required":
        notify = True  # 预警引擎的通知不可关闭（产品负责人 2026-10-14）
    conf = {"template": tpl, "rules": rules, "refs": [RR.ref(r) for r in rules], "notify_self": notify,
            "channels": ["BANNER", "MACOS"] if notify else ["BANNER"]}
    with transaction(track):
        track.execute("INSERT INTO card_setting (card_id, key, value, set_at) VALUES (?, 'engine_conf', ?, ?)",
                      (TPL_PREFIX + tpl, canonical_json(conf), at))
        track.execute("INSERT INTO card_setting (card_id, key, value, set_at) VALUES (?, 'engine_status', 'ACTIVE', ?)",
                      (TPL_PREFIX + tpl, at))
    return conf


def stop(track, tpl: str, *, at: str) -> None:
    if tpl not in active(track):
        raise EngineError("TEMPLATE_NOT_ACTIVE", tpl)
    with transaction(track):
        track.execute("INSERT INTO card_setting (card_id, key, value, set_at) VALUES (?, 'engine_status', 'STOPPED', ?)",
                      (TPL_PREFIX + tpl, at))


def mark_seen(track, tpl: str, *, at: str) -> None:
    run = track.execute("SELECT max(run_id) FROM run").fetchone()[0] or 0
    track.execute("INSERT INTO card_setting (card_id, key, value, set_at) VALUES (?, 'seen_run', ?, ?)",
                  (TPL_PREFIX + tpl, str(run), at))


# ----------------------------------------------------------------------------- 计算

def _definition(tpl: str, rule_id: str, prof: dict) -> dict:
    d = {"kind": "ENGINE_RULE", "engine_version": ENGINE, "template": tpl, "card_id": CARD_PREFIX + rule_id,
         "rule": RR.ref(rule_id), "fingerprint": RR.fingerprint(rule_id)}
    if RR.BY_ID[rule_id].get("needs_profile"):
        d["profile"] = {"birth_date": prof.get("birth_date"), "sex": prof.get("sex")}
    return d


def prepare_rule(track, tpl, rule_id, prof, groups):
    d = _definition(tpl, rule_id, prof)
    def_id = sha256_hex(canonical_bytes(d))
    days = CALC[rule_id][0](groups)
    latest = latest_results(track, def_id)
    fresh_def = not latest
    had_other = track.execute("SELECT 1 FROM card_def WHERE card_id = ? AND card_def_id != ? LIMIT 1",
                              (d["card_id"], def_id)).fetchone() is not None
    return d, def_id, days, latest, fresh_def, had_other


def apply_rule(track, d, def_id, todo, gone, fresh_def, had_other, now):
    trig = "RECOMPUTE" if fresh_def and had_other else (
        "AUTO_UPDATE" if any(s == "STALE" for _, _, s in todo.values()) or gone else "SYNC")
    track.execute("INSERT OR IGNORE INTO card_def (card_def_id, card_id, definition, registered_at) VALUES (?, ?, ?, ?)",
                  (def_id, d["card_id"], canonical_json(d), now))
    run_id = track.execute("INSERT INTO run (card_def_id, trigger, started_at) VALUES (?, ?, ?)",
                           (def_id, trig, now)).lastrowid
    for day, (res, inputs, _) in sorted(todo.items()):
        text = canonical_json(res)
        track.execute("INSERT INTO run_tp (run_id, tp_date, status, level, result, result_sha256) "
                      "VALUES (?, ?, 'EVALUATED', 'NONE', ?, ?)", (run_id, day, text, sha256_hex(text.encode())))
        track.executemany("INSERT INTO run_input (run_id, tp_date, observation_id, revision, role) VALUES (?, ?, ?, ?, ?)",
                          [(run_id, day, oid, rev, role) for oid, rev, role in sorted(inputs)])
    for tp in gone:
        text = canonical_json({"tp": tp, "status": "VANISHED"})
        track.execute("INSERT INTO run_tp (run_id, tp_date, status, level, result, result_sha256) "
                      "VALUES (?, ?, 'VANISHED', 'NONE', ?, ?)", (run_id, tp, text, sha256_hex(text.encode())))
    return run_id


def sync_all(track, ctx, root, *, now: str, notifiers, groups: dict, only: str | None = None) -> list:
    """每个启用的模板、每条规则：新时点、输入变了的时点按当前定义算；定义（规则版本、个人信息）变了就全部重算。"""
    prof = bioage.load_profile(root)
    out = []
    for tpl, t in active(track).items():
        if only and tpl != only:
            continue
        with transaction(track):
            changed = []
            for rule_id in t["conf"]["rules"]:
                d, def_id, days, latest, fresh_def, had_other = prepare_rule(track, tpl, rule_id, prof, groups)
                prepared = compute_snapshot.capture(rule_id, groups, prof, days, latest)
                todo, gone = compute_snapshot.engine_plan(*prepared, evaluate)
                if not todo and not gone:
                    continue
                run_id = apply_rule(track, d, def_id, todo, gone, fresh_def, had_other, now)
                changed.append((rule_id, run_id, sorted(todo)))
                out.append({"template": tpl, "rule": rule_id, "run_id": run_id, "evaluated": sorted(todo), "vanished": gone})
            if changed and t["conf"].get("notify_self"):
                _notify(track, ctx, tpl, t["conf"], changed, now)
    return out


def _notify(track, ctx, tpl: str, conf: dict, changed: list, now: str):
    """“有新结果时通知我”：一次同步一条，写进状态通知（alert_log），由星簇的本机通道发出。等级 NONE（这些卡不定级）。"""
    rule_id, run_id, days = changed[-1]
    if not days:
        return
    day = max(days)
    names = "、".join(RR.BY_ID[r]["name"] for r, _, ds in changed if ds)
    title = f"PTDS 新结果 · {TEMPLATES[tpl]['zh']}"
    body = f"{day}：{names}有新结果。{SUFFIX}"
    key = f"{ctx.instance_id}|{TPL_PREFIX + tpl}|{day}|R{run_id}"
    track.execute("INSERT OR IGNORE INTO alert_log (dedupe_key, card_id, tp_date, level, run_id, title, body, channels, created_at) "
                  "VALUES (?, ?, ?, 'NONE', ?, ?, ?, ?, ?)",
                  (key, TPL_PREFIX + tpl, day, run_id, title, body, canonical_json(sorted(set(conf["channels"]))), now))


# ----------------------------------------------------------------------------- 读模型（界面）

def _runs_of(track, card_id: str) -> list:
    """这张算法卡的全部计算（新的在前），每次计算算了哪些时点、结果是什么。"""
    runs = {}
    for rid, trig, at, def_id, tp, status, result, sha in track.execute(
            "SELECT r.run_id, r.trigger, r.started_at, r.card_def_id, t.tp_date, t.status, t.result, t.result_sha256 "
            "FROM run r JOIN card_def c USING (card_def_id) JOIN run_tp t USING (run_id) WHERE c.card_id = ? "
            "ORDER BY r.run_id, t.tp_date", (card_id,)):
        r = runs.setdefault(rid, {"run_id": rid, "trigger": trig, "trigger_zh": TRIGGER_ZH.get(trig, trig), "at": at,
                                  "def": def_id[:12], "items": []})
        res = json.loads(result)
        text, unit = res.get("text"), res.get("unit")
        suffix = " " + unit if unit else ""
        value_text = text[:-len(suffix)] if text and suffix and text.endswith(suffix) else text
        r["items"].append({"tp": tp, "status": status if status == "VANISHED" else res.get("status"),
                           "status_zh": "这个时点的数据已撤回" if status == "VANISHED" else STATUS_ZH.get(res.get("status")),
                           "text": text, "unit": unit, "value_text": value_text,
                           "value": res.get("value"), "reason": res.get("reason"), "sha": sha})
    return sorted(runs.values(), key=lambda r: -r["run_id"])


def _new_since(runs: list, seen: int) -> bool:
    """看过之后有没有“结果变了”的计算：同一时点结果指纹和之前不同，或出现新时点。"""
    last = {}
    flag = False
    for r in sorted(runs, key=lambda r: r["run_id"]):
        for it in r["items"]:
            if r["run_id"] > seen and last.get(it["tp"]) != it["sha"]:
                flag = True
            last[it["tp"]] = it["sha"]
    return flag


def _input_saved_at(track, run_id: int, tp: str):
    """最新结果所用当期输入的入库时间；不把重算、交接或采样时间当录入时间。"""
    rows = track.execute(
        "SELECT h.payload FROM run_input i LEFT JOIN h1_inbox h "
        "ON h.observation_id = i.observation_id AND h.revision = i.revision "
        "WHERE i.run_id = ? AND i.tp_date = ? AND i.role = 'TP'", (run_id, tp)).fetchall()
    times = [json.loads(row[0]).get("saved_at") if row[0] else None for row in rows]
    return max(times, key=parse_instant) if times and all(times) else None


def state(track, root, groups: dict, *, sjia: bool, profile=None) -> dict:
    prof = bioage.load_profile(root) if profile is None else profile
    sets = _settings(track)
    tpls = []
    for tid in ORDER:
        T = TEMPLATES[tid]
        s = sets.get(tid) or {}
        tpls.append({"id": tid, "zh": T["zh"], "sub": T["sub"], "rules": T["rules"], "notify": T["notify"],
                     "active": bool(s.get("active") and s.get("conf")), "conf": s.get("conf"),
                     "needs_profile": any(RR.BY_ID[r].get("needs_profile") for r in T["rules"])})
    out_groups = []
    for t in tpls:
        if not t["active"]:
            continue
        seen = (sets.get(t["id"]) or {}).get("seen", 0)
        cards = []
        rule_ids = t["conf"]["rules"]
        for rule_id in rule_ids:
            R = RR.BY_ID[rule_id]
            runs = _runs_of(track, CARD_PREFIX + rule_id)
            cur = {}
            for r in sorted(runs, key=lambda r: r["run_id"]):
                for it in r["items"]:
                    cur[it["tp"]] = dict(it, run_id=r["run_id"])
            live = [cur[d] for d in sorted(cur) if cur[d]["status"] != "VANISHED"]
            latest = next((x for x in reversed(live) if x["status"] == "computed"), live[-1] if live else None)
            if latest:  # 最新结果用了哪些数据、附带的数值（卡片页“用到的数据”）
                row = track.execute("SELECT result FROM run_tp WHERE run_id = ? AND tp_date = ?",
                                    (latest["run_id"], latest["tp"])).fetchone()
                if row:
                    full = json.loads(row[0])
                    latest = dict(latest, used=full.get("used"), used_count=full.get("used_count"), extra=full.get("extra"),
                                  fingerprint=full.get("fingerprint"), rule_ref=full.get("rule"),
                                  saved_at=_input_saved_at(track, latest["run_id"], latest["tp"]))
            points = [{"tp": x["tp"], "v": _num(x["value"]),
                       "value_text": x.get("value_text") or x.get("text") or str(x["value"])} for x in live
                      if x["status"] == "computed" and _num(x["value"]) is not None]
            cards.append({"rule": rule_id, "ref": RR.ref(rule_id), "name": R["name"], "kind": R["kind"], "summary": R["summary"],
                          "card": R.get("card"), "output": R["output"], "latest": latest, "new": _new_since(runs, seen),
                          "series": points[-60:], "series_count": len(points),
                          "runs": runs})
        out_groups.append({"id": t["id"], "zh": t["zh"], "sub": t["sub"], "conf": t["conf"], "cards": cards,
                           "new": any(c["new"] for c in cards)})
    return {"templates": tpls, "groups": out_groups, "profile": prof,
            "need_profile": not (prof.get("birth_date") and prof.get("sex")), "status_zh": STATUS_ZH, "note": SUFFIX}


def check(groups: dict, registry, root, tpl: str, *, sjia: bool) -> dict:
    """绑数据：一键检查这份数据能不能算。每条规则用到的指标有没有、最近一次是哪天、多少；在最新的时点试算一次。"""
    if tpl not in TEMPLATES:
        raise EngineError("TEMPLATE_UNKNOWN", tpl)
    prof = bioage.load_profile(root)
    rules = []
    for rule_id in TEMPLATES[tpl]["rules"]:
        R = RR.BY_ID[rule_id]
        ins = []
        for c in R["inputs"]:
            days = groups.get(c) or {}
            cd = registry.current.codes.get(c)
            last = max(days) if days else None
            o = _latest(days[last]) if last else None
            ins.append({"code": c, "label": cd.label_zh if cd else c, "days": len(days), "last_day": last,
                        "last": ((o.comparator or "") + format(o.value, "f") + (" " + o.unit if o.unit else "")) if o else None})
        dd = sorted(CALC[rule_id][0](groups))
        st, reason, txt, ok_n, ok_last = "insufficient_data", "还没有要用的数据", None, 0, None
        for i, d in enumerate(reversed(dd)):  # 最近一个时点的情况 + 一共有几个时点算得出
            res, _ = evaluate(rule_id, groups, d, prof)
            if i == 0:
                st, reason, txt = res["status"], res["reason"], res["text"]
            if res["status"] == "computed":
                ok_n += 1
                ok_last = ok_last or d
        if st != "computed" and ok_n:
            reason = f"最近一个时点（{dd[-1]}）{STATUS_ZH.get(st)}：{reason}；最近算得出的是 {ok_last}"
            st = "computed"
        rules.append({"rule": rule_id, "ref": RR.ref(rule_id), "name": R["name"], "inputs": ins, "status": st,
                      "status_zh": ("可算" if st == "computed" else STATUS_ZH.get(st)), "reason": reason, "try": txt,
                      "days": len(dd), "ok_days": ok_n, "last_day": dd[-1] if dd else None,
                      "needs_profile": bool(R.get("needs_profile"))})
    return {"template": tpl, "rules": rules, "profile": prof,
            "need_profile": any(r.get("needs_profile") for r in rules) and not (prof.get("birth_date") and prof.get("sex")),
            "computable": sum(1 for r in rules if r["status"] == "computed")}


def used_by(track, sjia: bool) -> dict:
    out = {}
    for tpl, t in active(track).items():
        for r in t["conf"]["rules"]:
            out.setdefault(r, []).append(TEMPLATES[tpl]["zh"] + " · " + RR.BY_ID[r]["name"])
    return out


def card_names(track) -> dict:
    """card_id → 界面上的卡名（数据详情里“被 XXX 用过”）。"""
    names = {"sjia-mas": "sJIA 关注卡"}
    for cid, d in track.execute("SELECT card_id, definition FROM card_def"):
        if cid in names:
            continue
        try:
            dd = json.loads(d)
        except ValueError:
            continue
        if dd.get("kind") == "ENGINE_RULE":
            rid = cid[len(CARD_PREFIX):]
            if rid in RR.BY_ID:
                grp = TEMPLATES[dd["template"]]["zh"] if dd["template"] in TEMPLATES else RR.SET_ZH[RR.BY_ID[rid]["set"]]  # 体验腕带卡不是引擎模板
                names[cid] = grp + " · " + RR.BY_ID[rid]["name"]
        elif dd.get("kind") == "CUSTOM":
            names[cid] = dd.get("name") or cid
    return names



def apply_prepared_template(track, ctx, tpl, prepared, now, guard):
    out, changed = [], []
    with transaction(track):
        guard.before(track)
        conf, rules = prepared.unwrap()
        for rule_id, planned in rules:
            d, def_id, todo, gone, fresh_def = planned.unwrap()
            # Earlier templates may have registered a definition for this card.
            had_other = track.execute("SELECT 1 FROM card_def WHERE card_id = ? AND card_def_id != ? LIMIT 1",
                                      (d['card_id'], def_id)).fetchone() is not None
            if not todo and not gone:
                continue
            run_id = apply_rule(track, d, def_id, todo, gone, fresh_def, had_other, now)
            changed.append((rule_id, run_id, sorted(todo)))
            out.append({'template': tpl, 'rule': rule_id, 'run_id': run_id, 'evaluated': sorted(todo), 'vanished': gone})
        if changed and conf.get('notify_self'):
            _notify(track, ctx, tpl, conf, changed, now)
        guard.advance(track)
    return out
