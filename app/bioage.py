"""星轨 · 生物年龄（Biological Age）计算引擎（早期测试，只用于研究演示）。

一个引擎 = 一组卡片，每张卡一种算法，同一份血检数据各算一遍：
- PhenoAge 2018（Levine 等）：Gompertz 死亡风险模型换算成等效年龄，系数取原文；
- KDM 生物年龄（Klemera–Doubal）：各指标对年龄回归，再按误差加权组合；
- 稳态失调 HD（Homeostatic Dysregulation）：与年轻健康参考人群的马氏距离。
KDM、HD 的参数由 app/tools/fit_bioage_params.py 用 NHANES III 拟合，存在 app/core/bioage-params-0.2.json。

- 数据只来自星轨自己的 h1_inbox（与睡眠卡、自定义卡同一份 by_code 分组），只读：不写星轨、不定级、不提醒；
- 每个结果都列出用了哪条数据（哪天、哪一版），可以追到星炬里的原始记录；
- 实际年龄、性别来自本人填写的个人信息（实例目录 profile.jsonl，只追加，最新一条为准）；
- 结果是群体模型在个人身上的估算，不是诊断；参考人群是美国 NHANES III，用于中国人群未经验证。
"""
from __future__ import annotations

import json
import math
import time
from datetime import date, timedelta
from pathlib import Path

CORE = Path(__file__).resolve().parent / "core"
PARAMS_FILE = CORE / "bioage-params-0.2.json"
WINDOW_DAYS = 30  # 一次计算可以借用此前 30 天内最近的一次化验
NOTE = "群体模型在个人身上的估算，只用于研究演示，不是诊断。参考人群为美国 NHANES III，用于中国人群未经验证。"

# 9 项血检：代码、中文名、规范单位（字典）
MARKERS = [("ALB", "白蛋白", "g/L"), ("CREA", "肌酐", "μmol/L"), ("GLU", "血糖", "mmol/L"), ("CRP", "C 反应蛋白", "mg/L"),
           ("LYMPH_PCT", "淋巴细胞百分比", "%"), ("MCV", "平均红细胞体积", "fL"), ("RDW_CV", "红细胞分布宽度", "%"),
           ("ALP", "碱性磷酸酶", "U/L"), ("WBC", "白细胞计数", "×10^9/L")]
ZH = {c: z for c, z, _ in MARKERS}

METHODS = {
    "PHENOAGE": {"zh": "PhenoAge 表型年龄", "year": "2018", "unit": "岁",
                 "how": "Gompertz 死亡风险模型，把 9 项血检和实际年龄换算成死亡风险相同的“等效年龄”。",
                 "source": "Levine ME, et al. An epigenetic biomarker of aging for lifespan and healthspan. Aging, 2018"},
    "KDM": {"zh": "KDM 生物年龄", "year": "2006/2013", "unit": "岁",
            "how": "每项指标对年龄做回归，再按各自误差加权合成一个年龄；分性别，最多允许缺 2 项。",
            "source": "Klemera P, Doubal S. 2006；Levine ME. 2013；参数用 NHANES III 拟合（BioAge，Kwon & Belsky）"},
    "HD": {"zh": "稳态失调 HD", "year": "2013", "unit": "分",
           "how": "与 20–30 岁健康参考人群的多变量偏离（马氏距离），数越大偏离越多；分性别，9 项都要有。",
           "source": "Cohen AA, et al. 2013；参数用 NHANES III 拟合（BioAge，Kwon & Belsky）"},
}
ORDER = ["PHENOAGE", "KDM", "HD"]

_PARAMS = None


def params() -> dict:
    global _PARAMS
    if _PARAMS is None:
        _PARAMS = json.loads(PARAMS_FILE.read_text("utf-8"))
    return _PARAMS


# ----------------------------------------------------------------------------- 个人信息（出生日期、性别）

def profile_path(root) -> Path:
    return Path(root) / "profile.jsonl"


def load_profile(root) -> dict:
    p, out = profile_path(root), {}
    if p.exists():
        for line in p.read_text("utf-8").splitlines():
            try:
                out.update(json.loads(line))
            except ValueError:
                pass
    return {k: out.get(k) for k in ("birth_date", "sex", "at")}


def save_profile(root, body: dict) -> dict:
    bd, sex = str(body.get("birth_date") or "").strip(), body.get("sex")
    try:
        d = date.fromisoformat(bd)
    except ValueError:
        raise ValueError("BIRTH_DATE_INVALID")
    if not date(1900, 1, 1) <= d <= date.today():
        raise ValueError("BIRTH_DATE_INVALID")
    if sex not in ("男", "女"):
        raise ValueError("SEX_INVALID")
    row = {"birth_date": d.isoformat(), "sex": sex, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    p = profile_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def capture_profile(root, *, byte_limit):
    """Caller holds A; capture a read-only handle and boundary, not history."""
    from compute_input_versions import capture_prefix
    return capture_prefix(root, profile_path(root), byte_limit=byte_limit)


def read_profile_version(lease):
    """Outside A, preserve load_profile's precise bad-line/error policy."""
    from compute_input_versions import FileInput, private_value
    out = {}
    for line in lease.read_text().splitlines():
        try:
            out.update(json.loads(line))
        except ValueError:
            pass
    return FileInput(lease.version,
                     private_value({k: out.get(k) for k in ('birth_date', 'sex', 'at')}))


def private_parameters(values):
    """Explicit release values only; never calls params or publishes _PARAMS."""
    from compute_input_versions import private_value
    return private_value(values)


def age_at(birth: str, day: str) -> float:
    b, d = date.fromisoformat(birth), date.fromisoformat(day)
    return (d - b).days / 365.2425


# ----------------------------------------------------------------------------- 取数

def _latest(obs):
    return max(obs, key=lambda o: (o.instant.isoformat() if o.instant else "", o.revision, o.observation_id))


def _pick(groups: dict, code: str, day: str):
    """day 当天或之前 WINDOW_DAYS 天内最近的一条。"""
    days = groups.get(code) or {}
    lo = (date.fromisoformat(day) - timedelta(days=WINDOW_DAYS)).isoformat()
    cand = [d for d in days if lo <= d <= day]
    if not cand:
        return None
    d = max(cand)
    return _latest(days[d])


def inputs_at(groups: dict, day: str) -> dict:
    out = {}
    for code, zh, unit in MARKERS:
        o = None
        if code == "CRP":  # 优先超敏 CRP（低值更准），同一天两者都有时取超敏
            o = _pick(groups, "HSCRP", day)
            c = _pick(groups, "CRP", day)
            if c is not None and (o is None or c.day > o.day):
                o = c
        else:
            o = _pick(groups, code, day)
        if o is None:
            out[code] = {"code": code, "label_zh": zh, "unit": unit, "missing": True}
            continue
        v = float(o.value)
        note = None
        if o.comparator in ("<", "<="):
            note = f"报告写的是 {o.comparator}{format(o.value, 'f')}，按这个上限计算"
        elif o.comparator in (">", ">="):
            note = f"报告写的是 {o.comparator}{format(o.value, 'f')}，按这个下限计算"
        out[code] = {"code": code, "label_zh": zh, "unit": unit, "value": v, "value_text": format(o.value, "f"),
                     "day": o.day, "ref": o.ref, "source_code": o.code, "borrowed": o.day != day, "note": note}
    return out


# ----------------------------------------------------------------------------- 三种算法

def phenoage(x: dict, age: float):
    need = [c for c, _, _ in MARKERS if x[c].get("missing")]
    if need:
        return {"ok": False, "missing": need}
    crp_dl = max(x["CRP"]["value"] / 10.0, 0.001)  # 原式用 ln(CRP mg/dL)
    xb = (-19.907 - 0.0336 * x["ALB"]["value"] + 0.0095 * x["CREA"]["value"] + 0.1953 * x["GLU"]["value"]
          + 0.0954 * math.log(crp_dl) - 0.0120 * x["LYMPH_PCT"]["value"] + 0.0268 * x["MCV"]["value"]
          + 0.3306 * x["RDW_CV"]["value"] + 0.00188 * x["ALP"]["value"] + 0.0554 * x["WBC"]["value"] + 0.0804 * age)
    g = 0.0076927
    m = 1 - math.exp(-math.exp(xb) * (math.exp(120 * g) - 1) / g)
    if not 0 < m < 1:
        return {"ok": False, "missing": [], "error": "数值超出模型范围"}
    pa = 141.50225 + math.log(-0.00553 * math.log(1 - m)) / 0.090165
    return {"ok": True, "value": round(pa, 1), "delta": round(pa - age, 1), "extra": {"mortality_10y": round(m * 100, 1)}}


def _bm_value(x: dict, code: str):
    if x[code].get("missing"):
        return None
    v = x[code]["value"]
    return math.log(1 + max(v, 0) / 10.0) if code == "CRP" else v  # BioAge：ln(1 + CRP[mg/dL])


def kdm(x: dict, age: float, sex: str, *, parameters=None):
    p = (params() if parameters is None else parameters)["sex"][sex]["kdm"]
    num, den, used, miss = 0.0, 0.0, 0, []
    for mk in p["markers"]:
        v = _bm_value(x, mk["code"])
        if v is None:
            miss.append(mk["code"])
            continue
        num += (v - mk["q"]) * (mk["k"] / mk["s"] ** 2)
        used += 1
    den = sum((mk["k"] / mk["s"]) ** 2 for mk in p["markers"])
    if len(miss) > 2:
        return {"ok": False, "missing": miss}
    # BioAge：BA_e 按缺失项数放大后与实际年龄合成（s_ba2 为先验方差）
    num_scaled = num * len(p["markers"]) / used
    ba = (num_scaled + age / p["s_ba2"]) / (den + 1 / p["s_ba2"])
    return {"ok": True, "value": round(ba, 1), "delta": round(ba - age, 1), "missing": miss}


def hd(x: dict, age: float, sex: str, *, parameters=None):
    p = (params() if parameters is None else parameters)["sex"][sex]["hd"]
    codes = [m["code"] for m in (params() if parameters is None else parameters)["markers"]]
    vals = [_bm_value(x, c) for c in codes]
    miss = [c for c, v in zip(codes, vals) if v is None]
    if miss:
        return {"ok": False, "missing": miss}
    z = [(v - mu) / sd - zm for v, mu, sd, zm in zip(vals, p["mean"], p["sd"], p["zmean"])]
    inv = p["inv_cov"]
    d2 = sum(z[i] * inv[i][j] * z[j] for i in range(len(z)) for j in range(len(z)))
    score = math.sqrt(max(d2, 0)) / p["train_sd"]
    band = str(min(70, max(30, int(age // 10 * 10))))
    pct = p["percentiles_by_age"].get(band)
    where = None
    if pct:
        cuts = [10, 25, 50, 75, 90]
        below = [c for c, q in zip(cuts, pct) if score >= q]
        where = f"约高于同性别 {band}–{int(band) + 9} 岁参考人群的 {below[-1]}%" if below else f"低于同性别 {band}–{int(band) + 9} 岁参考人群的 10%"
    return {"ok": True, "value": round(score, 2), "delta": None, "extra": {"band": where}}


# ----------------------------------------------------------------------------- 引擎状态

def state(groups: dict, root, *, profile=None) -> dict:
    prof = load_profile(root) if profile is None else profile
    days = sorted({d for c, _, _ in MARKERS for d in (groups.get(c) or {})} | set((groups.get("HSCRP") or {})))
    cards = {m: dict(METHODS[m], id=m, series=[], latest=None) for m in ORDER}
    have_lab = bool(days)
    if prof.get("birth_date") and prof.get("sex"):
        for d in days:
            age = age_at(prof["birth_date"], d)
            x = inputs_at(groups, d)
            res = {"PHENOAGE": phenoage(x, age), "KDM": kdm(x, age, prof["sex"]), "HD": hd(x, age, prof["sex"])}
            for m in ORDER:
                r = dict(res[m], day=d, age=round(age, 1))
                if r["ok"]:
                    cards[m]["series"].append({"tp": d, "v": r["value"]})
                    r["inputs"] = [x[c] for c, _, _ in MARKERS]
                cards[m]["last_try"] = r
                if r["ok"]:
                    cards[m]["latest"] = r
        for m in ORDER:
            lt = cards[m].pop("last_try", None)
            if cards[m]["latest"] is None and lt:
                cards[m]["why"] = "最近一次化验缺：" + "、".join(ZH.get(c, c) for c in lt.get("missing") or []) if lt.get("missing") \
                    else lt.get("error") or "算不了"
    return {"profile": prof, "need_profile": not (prof.get("birth_date") and prof.get("sex")), "has_lab": have_lab,
            "lab_days": len(days), "cards": [cards[m] for m in ORDER], "markers": [{"code": c, "label_zh": z, "unit": u} for c, z, u in MARKERS],
            "note": NOTE, "window_days": WINDOW_DAYS}
