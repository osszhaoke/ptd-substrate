"""Generic dynamic monitoring (星轨): change of an indicator against a baseline time point.

Never fills forward: a time point without the indicator is NOT_EVALUABLE for that indicator.
Censored (<, >) or conflicting values are NOT_EVALUABLE. A zero baseline for a relative
measure is NOT_EVALUABLE. A missing threshold (null) is NOT_EVALUABLE, never a guess.
"""
from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal, Inexact, localcontext

from h1_common import DECIMAL_CONTEXT, DictionaryRegistry, H1Error, canonical_decimal, parse_decimal

ROLES = ("CORE", "GENERAL")
DIRECTIONS = ("UP", "DOWN")
BASES = ("PREVIOUS", "FIRST", "WINDOW_EXTREME")
MEASURES = ("PCT", "ABS", "PCT_PER_DAY")
BOOL_MEASURES = ("APPEAR", "PERSIST")  # 0.2 起：是/否类指标（症状）——“新出现”“持续存在”，与上一次记录比
SENSITIVITIES = ("LOW", "MEDIUM", "HIGH")
SCHEMAS = ("dynamic-config/0.1", "dynamic-config/0.2")


def change_word(direction: str, measure: str | None = None) -> str:
    """提醒和解释里的一个词：上升 / 下降 / 新出现 / 持续。"""
    if measure == "APPEAR":
        return "新出现"
    if measure == "PERSIST":
        return "持续"
    return "上升" if direction == "UP" else "下降"


class DynamicConfig:
    def __init__(self, doc: dict, registry: DictionaryRegistry, sensitivity: str):
        if doc.get("schema") not in SCHEMAS:
            raise H1Error("CONFIG_INVALID", "schema")
        measures = MEASURES + (BOOL_MEASURES if doc["schema"] != SCHEMAS[0] else ())
        self.doc = doc
        self.config_id, self.version, self.provenance = doc["config_id"], doc["version"], doc["provenance"]
        multipliers = {k: parse_decimal(v) for k, v in doc["sensitivity_multipliers"].items()}
        if set(multipliers) != set(SENSITIVITIES) or any(m <= 0 for m in multipliers.values()):
            raise H1Error("CONFIG_INVALID", "sensitivity_multipliers")
        if sensitivity not in multipliers:
            raise H1Error("CONFIG_INVALID", "sensitivity")
        self.sensitivity, self.multiplier = sensitivity, multipliers[sensitivity]
        self.general_sum_threshold = parse_decimal(doc["general_sum_threshold"])
        if self.general_sum_threshold <= 0:
            raise H1Error("CONFIG_INVALID", "general_sum_threshold must be > 0")
        self.indicators = []
        for ind in doc["indicators"]:
            required = {"code", "role", "bad_direction", "basis", "measure", "threshold", "weight"}
            if not isinstance(ind, dict) or set(ind) != required:
                raise H1Error("CONFIG_INVALID", "indicator keys (threshold may be null, never absent)")
            cdef = registry.current.codes.get(ind["code"])
            boolean = ind.get("measure") in BOOL_MEASURES
            if cdef is None or cdef.value_type != ("BOOLEAN" if boolean else "DECIMAL"):
                raise H1Error("CONFIG_INVALID", f"{ind['code']}: dynamic indicators must be DECIMAL codes "
                                                "(BOOLEAN only with APPEAR / PERSIST)")
            basis = ind["basis"]
            if ind["role"] not in ROLES or ind["bad_direction"] not in DIRECTIONS or ind["measure"] not in measures \
                    or basis.get("kind") not in BASES:
                raise H1Error("CONFIG_INVALID", ind["code"])
            if boolean and (basis["kind"] != "PREVIOUS" or ind["threshold"] is not None or ind["bad_direction"] != "UP"):
                raise H1Error("CONFIG_INVALID", f"{ind['code']}: APPEAR / PERSIST need PREVIOUS, UP, threshold null")
            if basis["kind"] == "WINDOW_EXTREME":
                if set(basis) != {"kind", "days"} or type(basis["days"]) is not int or basis["days"] < 1:
                    raise H1Error("CONFIG_INVALID", f"{ind['code']}: WINDOW_EXTREME needs integer days >= 1")
            elif set(basis) != {"kind"}:
                raise H1Error("CONFIG_INVALID", f"{ind['code']}: basis")
            threshold = None if ind["threshold"] is None else parse_decimal(ind["threshold"])
            weight = parse_decimal(ind["weight"])
            if (threshold is not None and threshold < 0) or weight <= 0:
                raise H1Error("CONFIG_INVALID", f"{ind['code']}: threshold/weight")
            self.indicators.append(dict(ind, threshold=threshold, weight=weight, unit=cdef.unit_canonical,
                                        label_zh=cdef.label_zh))
        codes = [i["code"] for i in self.indicators]
        if len(set(codes)) != len(codes):
            raise H1Error("CONFIG_INVALID", "duplicate indicator")
        self.codes = frozenset(codes)


def _exact(value) -> bool:
    return value.value is not None and value.comparator is None


def _base(ind: dict, tp: str, earlier: list):
    """earlier: [(tp, Value)] ascending, all before tp. Returns ((tp, Value), reason)."""
    if not earlier:
        return None, "NO_BASELINE"
    kind = ind["basis"]["kind"]
    if kind == "PREVIOUS":
        return earlier[-1], None
    if kind == "FIRST":
        return earlier[0], None
    days = ind["basis"]["days"]
    window = [e for e in earlier if (date.fromisoformat(tp) - date.fromisoformat(e[0])).days <= days]
    if not window:
        return None, "NO_BASELINE"
    if not all(_exact(v) for _, v in window):
        return None, "INEXACT_VALUE"
    pick = min if ind["bad_direction"] == "UP" else max  # the best recent value
    return pick(window, key=lambda e: e[1].value), None


def _pct(value: Decimal) -> str:
    q = (value * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    return ("+" if q > 0 else "") + format(q, "f")


def _evaluate_bool(ind: dict, res: dict, current, earlier: list) -> None:
    """是/否类：和这一项上一次的记录比（缺的时点不算“没有”，不往前补）。"""
    if current is None:
        res["reason"] = "NO_CURRENT_VALUE"
        return
    if not earlier:
        res["reason"] = "NO_BASELINE"
        return
    base = earlier[-1]
    res["base_tp"] = base[0]
    res["refs"] = list(current[1].refs) + list(base[1].refs)
    if current[1].value is None or base[1].value is None:
        res["reason"] = "INEXACT_VALUE"
        return
    now, before = bool(current[1].value), bool(base[1].value)
    if ind["measure"] == "APPEAR":
        hit = now and not before
        res["change"] = "新出现" if hit else ("持续存在" if now else ("已消失" if before else "未出现"))
    else:
        hit = now and before
        res["change"] = "持续存在" if hit else ("新出现" if now else "未出现")
    res["status"] = "TRIGGERED" if hit else "NOT_TRIGGERED"


def evaluate_dynamic(cfg: DynamicConfig, tp: str, series: dict) -> dict:
    """series: code -> [(tp, Value)] ascending, only time points <= tp where the code has a value."""
    out = []
    for ind in cfg.indicators:
        entries = series.get(ind["code"], [])
        current = entries[-1] if entries and entries[-1][0] == tp else None
        earlier = [e for e in entries if e[0] < tp]
        with localcontext(DECIMAL_CONTEXT) as ctx:
            ctx.traps[Inexact] = True
            effective = None if ind["threshold"] is None else ind["threshold"] * cfg.multiplier
        res = {"code": ind["code"], "label_zh": ind["label_zh"], "role": ind["role"],
               "bad_direction": ind["bad_direction"], "basis": ind["basis"], "measure": ind["measure"],
               "threshold": None if ind["threshold"] is None else canonical_decimal(ind["threshold"]),
               "effective_threshold": None if effective is None else canonical_decimal(effective),
               "weight": canonical_decimal(ind["weight"]), "status": "NOT_EVALUABLE", "reason": None,
               "change": None, "base_tp": None, "refs": []}
        out.append(res)
        if ind["measure"] in BOOL_MEASURES:
            _evaluate_bool(ind, res, current, earlier)
            continue
        if effective is None:
            res["reason"] = "NO_THRESHOLD"
            continue
        if current is None:
            res["reason"] = "NO_CURRENT_VALUE"
            continue
        base, reason = _base(ind, tp, earlier)
        if base is None:
            res["reason"] = reason
            continue
        res["base_tp"] = base[0]
        res["refs"] = list(current[1].refs) + list(base[1].refs)
        if not (_exact(current[1]) and _exact(base[1])):
            res["reason"] = "INEXACT_VALUE"
            continue
        cur, prev = current[1].value, base[1].value
        with localcontext(DECIMAL_CONTEXT):
            if ind["measure"] in ("PCT", "PCT_PER_DAY"):
                if prev == 0:
                    res["reason"] = "ZERO_BASELINE"
                    continue
                change = (cur - prev) / prev
                if ind["measure"] == "PCT_PER_DAY":
                    change = change / (date.fromisoformat(tp) - date.fromisoformat(base[0])).days
                    res["change"] = _pct(change) + "%/天"
                else:
                    res["change"] = _pct(change) + "%"
            else:
                change = cur - prev
                res["change"] = ("+" if change > 0 else "") + canonical_decimal(change) + " " + ind["unit"]
            bad = change if ind["bad_direction"] == "UP" else -change
            res["status"] = "TRIGGERED" if bad >= effective else "NOT_TRIGGERED"
    triggered_general = [r for r in out if r["status"] == "TRIGGERED" and r["role"] == "GENERAL"]
    with localcontext(DECIMAL_CONTEXT) as ctx:
        ctx.traps[Inexact] = True
        general_sum = sum((parse_decimal(r["weight"]) for r in triggered_general), Decimal(0))
    if any(r["status"] == "TRIGGERED" and r["role"] == "CORE" for r in out):
        level = "ALERT"
    elif triggered_general and general_sum >= cfg.general_sum_threshold:
        level = "WATCH"
    elif any(r["status"] != "NOT_EVALUABLE" for r in out):
        level = "NONE"
    else:
        level = "NOT_EVALUABLE"
    return {"config_id": cfg.config_id, "version": cfg.version, "provenance": cfg.provenance,
            "sensitivity": cfg.sensitivity, "multiplier": canonical_decimal(cfg.multiplier), "level": level,
            "general_sum": canonical_decimal(general_sum),
            "general_sum_threshold": canonical_decimal(cfg.general_sum_threshold), "indicators": out}
