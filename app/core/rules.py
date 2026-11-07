"""Generic three-valued rule kernels (星轨). No disease names here: content comes from a rule pack.

Three-valued logic (Kleene): True / False / None (= unknown). Always test with `is True` /
`is False`; never rely on truthiness, because None and False must not be confused.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, Inexact, localcontext

from h1_common import DECIMAL_CONTEXT, DictionaryRegistry, H1Error, apply_rule, canonical_decimal, parse_decimal

OPS = (">", ">=", "<", "<=")
RESULTS = ("MET", "NOT_MET", "INDETERMINATE", "NOT_APPLICABLE")
SELECTION_MODES = ("LATEST", "MAX", "ANY_TRUE")
BANNED_IN_ALERT = ("诊断", "确诊", "MAS 发生", "MAS发生")


@dataclass(frozen=True)
class Value:
    """The value of one code at one time point after selection (see cards.select_values)."""
    code: str
    kind: str                     # DECIMAL | BOOLEAN
    value: object                 # Decimal | bool | None (None only when conflict)
    comparator: str | None
    unit: str | None              # canonical unit
    conflict: bool
    refs: tuple                   # ("OBS-...@rev", ...) chosen observations, or all candidates on conflict


# ----------------------------------------------------------------------------- Kleene logic

def tri_and(values) -> bool | None:
    values = list(values)
    if any(v is False for v in values):
        return False
    if all(v is True for v in values):
        return True
    return None


def tri_or(values) -> bool | None:
    values = list(values)
    if any(v is True for v in values):
        return True
    if all(v is False for v in values):
        return False
    return None


def k_of_n(values, k: int) -> bool | None:
    values = list(values)
    true = sum(1 for v in values if v is True)
    unknown = sum(1 for v in values if v is None)
    if true >= k:
        return True
    if true + unknown < k:
        return False
    return None


# ----------------------------------------------------------------------------- censored values

def compare(value: Decimal | None, comparator: str | None, op: str, threshold: Decimal) -> bool | None:
    """Is `observation op threshold`? The observation is an interval:
    exact v -> [v, v];  '<v' -> (-inf, v);  '<=v' -> (-inf, v];  '>v' -> (v, inf);  '>=v' -> [v, inf).
    True if every point satisfies the condition, False if none does, None otherwise.
    """
    if value is None:
        return None
    lo, lo_closed, hi, hi_closed = {
        None: (value, True, value, True),
        "<": (None, False, value, False),
        "<=": (None, False, value, True),
        ">": (value, False, None, False),
        ">=": (value, True, None, False),
    }[comparator]
    above_open = lo is not None and (lo > threshold or (lo == threshold and not lo_closed))   # all > t
    above_closed = lo is not None and lo >= threshold                                         # all >= t
    below_open = hi is not None and (hi < threshold or (hi == threshold and not hi_closed))   # all < t
    below_closed = hi is not None and hi <= threshold                                         # all <= t
    if op == ">":
        return True if above_open else False if below_closed else None
    if op == ">=":
        return True if above_closed else False if below_open else None
    if op == "<":
        return True if below_open else False if above_closed else None
    if op == "<=":
        return True if below_closed else False if above_open else None
    raise H1Error("RULE_OP_INVALID", op)


def tri_label(value: bool | None) -> str:
    return "TRUE" if value is True else "FALSE" if value is False else "UNKNOWN"


def result_from(overall: bool | None, gate: bool | None) -> str:
    if overall is True:
        return "MET"
    if overall is False:
        return "NOT_APPLICABLE" if gate is False else "NOT_MET"
    return "INDETERMINATE"


# ----------------------------------------------------------------------------- rule pack

class RulePack:
    """Loads a rule pack document. Thresholds are registered in the unit of the source publication
    and converted ONCE here with the dictionary's own conversion rule (same rule as observations)."""

    def __init__(self, doc: dict, registry: DictionaryRegistry):
        self.doc = doc
        self.dictionary = registry.current
        if doc.get("schema") != "rulepack/0.1":
            raise H1Error("RULEPACK_INVALID", "schema")
        self.pack_id, self.version = doc["pack_id"], doc["version"]
        selection = doc["selection"]
        allowed = {"DECIMAL": ("LATEST", "MAX"), "BOOLEAN": ("ANY_TRUE", "LATEST")}
        checks = [("DECIMAL", selection["DECIMAL"]), ("BOOLEAN", selection["BOOLEAN"])]
        for code, mode in selection["overrides"].items():
            cdef = self.dictionary.codes.get(code)
            if cdef is None:
                raise H1Error("RULEPACK_INVALID", f"selection override for unknown code {code}")
            checks.append((cdef.value_type, mode))
        if any(mode not in allowed[kind] for kind, mode in checks):
            raise H1Error("RULEPACK_INVALID", "selection mode")
        self.selection = selection
        self.codes: set = set()
        self.rules = {}
        for rule_id, rule in doc["rules"].items():
            for word in BANNED_IN_ALERT:
                if word in rule["short_zh"]:
                    raise H1Error("RULEPACK_COPY_UNSAFE", rule_id)
            self.rules[rule_id] = self._load_rule(rule_id, rule)
        combine = doc["combine"]
        for key in ("alert_on_met", "undetermined_on_indeterminate"):
            if not set(combine[key]) <= set(self.rules):
                raise H1Error("RULEPACK_INVALID", f"combine.{key}")
        self.combine = combine

    def selection_mode(self, code: str, kind: str) -> str:
        return self.selection["overrides"].get(code, self.selection[kind])

    def _code(self, code: str, kind: str):
        cdef = self.dictionary.codes.get(code)
        if cdef is None or cdef.value_type != kind:
            raise H1Error("RULEPACK_INVALID", f"{code} must be a {kind} code in the dictionary")
        self.codes.add(code)
        return cdef

    def _criterion(self, c: dict, path: str) -> dict:
        out = dict(c)
        if "code" in c:
            cdef = self._code(c["code"], "DECIMAL")
            if c["op"] not in OPS:
                raise H1Error("RULEPACK_INVALID", f"{path}: op")
            raw = parse_decimal(c["value"])
            if c["unit"] == cdef.unit_canonical:
                threshold = raw
            else:
                threshold = apply_rule(cdef.rule_for(c["unit"]), raw)
                out["converted_from"] = f'{c["value"]} {c["unit"]}'
            out["threshold"] = threshold
            out["unit_canonical"] = cdef.unit_canonical
        elif "flag" in c:
            self._code(c["flag"], "BOOLEAN")
        elif "any" in c:
            out["any"] = [self._criterion(x, f"{path}.any") for x in c["any"]]
        elif "k_of" in c:
            out["items"] = [self._criterion(x, f"{path}.items") for x in c["items"]]
            if type(c["k_of"]) is not int or not 1 <= c["k_of"] <= len(out["items"]):
                raise H1Error("RULEPACK_INVALID", f"{path}: k_of")
        else:
            raise H1Error("RULEPACK_INVALID", f"{path}: unknown criterion")
        return out

    def _load_rule(self, rule_id: str, rule: dict) -> dict:
        out = dict(rule)
        out["gate"] = [self._criterion(c, f"{rule_id}.gate") for c in rule.get("gate", [])]
        kind = rule["kind"]
        if kind == "GATED_REQUIRED_K_OF_N":
            out["required"] = [self._criterion(c, f"{rule_id}.required") for c in rule["required"]]
            out["additional"] = [self._criterion(c, f"{rule_id}.additional") for c in rule["additional"]]
            if not 0 <= rule["additional_min"] <= len(out["additional"]):
                raise H1Error("RULEPACK_INVALID", f"{rule_id}: additional_min")
        elif kind == "K_OF_N":
            out["criteria"] = [self._criterion(c, f"{rule_id}.criteria") for c in rule["criteria"]]
            if not 1 <= rule["min_met"] <= len(out["criteria"]):
                raise H1Error("RULEPACK_INVALID", f"{rule_id}: min_met")
        elif kind == "LINEAR_SCORE":
            terms = []
            for term in rule["terms"]:
                t = dict(term, coef=parse_decimal(term["coef"]))
                if "code" in term:
                    cdef = self._code(term["code"], "DECIMAL")
                    if term["unit"] != cdef.unit_canonical:  # AC-05: never feed a non-canonical unit
                        raise H1Error("COEFFICIENT_UNIT_MISMATCH", f"{rule_id}.{term['code']}")
                else:
                    self._code(term["flag"], "BOOLEAN")
                terms.append(t)
            out["terms"] = terms
            out["cutoff_value"] = parse_decimal(rule["cutoff"]["value"])
            if rule["cutoff"]["op"] not in OPS:
                raise H1Error("RULEPACK_INVALID", f"{rule_id}: cutoff op")
        else:
            raise H1Error("RULEPACK_INVALID", f"{rule_id}: kind")
        return out


# ----------------------------------------------------------------------------- evaluation

def _value_json(v: Value | None) -> dict:
    if v is None:
        return {"value": None, "comparator": None, "missing": True, "conflict": False, "refs": []}
    shown = None if v.value is None else (("true" if v.value else "false") if v.kind == "BOOLEAN"
                                          else canonical_decimal(v.value))
    return {"value": shown, "comparator": v.comparator, "missing": False, "conflict": v.conflict,
            "refs": list(v.refs)}


def eval_criterion(c: dict, vals: dict) -> tuple:
    if "code" in c:
        v = vals.get(c["code"])
        if v is not None and v.value is not None and v.unit != c["unit_canonical"]:
            raise H1Error("UNIT_MISMATCH_AT_EVALUATION", c["code"])
        outcome = compare(None if v is None else v.value, None if v is None else v.comparator,
                          c["op"], c["threshold"])
        detail = {"code": c["code"], "op": c["op"], "threshold": canonical_decimal(c["threshold"]),
                  "unit": c["unit_canonical"], **_value_json(v), "outcome": tri_label(outcome)}
        if "converted_from" in c:
            detail["threshold_source"] = c["converted_from"]
    elif "flag" in c:
        v = vals.get(c["flag"])
        outcome = None if v is None or v.value is None else bool(v.value)
        detail = {"flag": c["flag"], **_value_json(v), "outcome": tri_label(outcome)}
    elif "any" in c:
        parts = [eval_criterion(x, vals) for x in c["any"]]
        outcome = tri_or(p[0] for p in parts)
        detail = {"any": [p[1] for p in parts], "outcome": tri_label(outcome)}
    else:
        parts = [eval_criterion(x, vals) for x in c["items"]]
        outcome = k_of_n((p[0] for p in parts), c["k_of"])
        detail = {"k_of": c["k_of"], "items": [p[1] for p in parts], "outcome": tri_label(outcome)}
    if "id" in c:
        detail["id"] = c["id"]
    return outcome, detail


def _missing(details) -> list:
    """Codes that are absent or conflicting anywhere in a criterion tree (the 缺项清单)."""
    out = []
    for d in details:
        if "any" in d:
            out += _missing(d["any"])
        elif "items" in d:
            out += _missing(d["items"])
        elif d.get("missing") or d.get("conflict"):
            out.append(d.get("code") or d.get("flag"))
    return sorted(set(out))


def eval_rule(rule_id: str, rule: dict, vals: dict) -> dict:
    gate_parts = [eval_criterion(c, vals) for c in rule["gate"]]
    gate = tri_and(p[0] for p in gate_parts)
    out = {"rule": rule_id, "name_zh": rule["name_zh"], "expert_review": rule["expert_review"],
           "gate": {"outcome": tri_label(gate), "items": [p[1] for p in gate_parts]}}
    details = [p[1] for p in gate_parts]
    if rule["kind"] == "GATED_REQUIRED_K_OF_N":
        req = [eval_criterion(c, vals) for c in rule["required"]]
        add = [eval_criterion(c, vals) for c in rule["additional"]]
        part = tri_and([tri_and(p[0] for p in req), k_of_n((p[0] for p in add), rule["additional_min"])])
        overall = tri_and([gate, part])
        out.update(required=[p[1] for p in req], additional=[p[1] for p in add],
                   additional_min=rule["additional_min"],
                   additional_true=sum(1 for p in add if p[0] is True),
                   additional_unknown=sum(1 for p in add if p[0] is None),
                   criteria_part=result_from(part, True))
        details += [p[1] for p in req + add]
    elif rule["kind"] == "K_OF_N":
        crit = [eval_criterion(c, vals) for c in rule["criteria"]]
        part = k_of_n((p[0] for p in crit), rule["min_met"])
        overall = tri_and([gate, part])
        out.update(criteria=[p[1] for p in crit], min_met=rule["min_met"],
                   met_count=sum(1 for p in crit if p[0] is True),
                   unknown_count=sum(1 for p in crit if p[0] is None),
                   criteria_part=result_from(part, True))
        details += [p[1] for p in crit]
    else:  # LINEAR_SCORE
        terms, inputs = [], []
        for term in rule["terms"]:
            key = term.get("code") or term["flag"]
            v = vals.get(key)
            x = None
            if v is not None and v.value is not None and v.comparator is None:
                if "code" in term:
                    if v.unit != term["unit"]:
                        raise H1Error("COEFFICIENT_UNIT_MISMATCH", key)
                    x = v.value
                else:
                    x = Decimal(1) if v.value else Decimal(0)
            inputs.append(x)
            terms.append({"input": key, "coef": canonical_decimal(term["coef"]), "unit": term.get("unit"),
                          **_value_json(v), "usable": x is not None})
        score = None
        if all(x is not None for x in inputs):
            with localcontext(DECIMAL_CONTEXT) as ctx:
                ctx.traps[Inexact] = True
                score = sum((term["coef"] * x for term, x in zip(rule["terms"], inputs)), Decimal(0))
        part = None if score is None else compare(score, None, rule["cutoff"]["op"], rule["cutoff_value"])
        overall = tri_and([gate, part])
        out.update(terms=terms, score=None if score is None else canonical_decimal(score),
                   cutoff={"op": rule["cutoff"]["op"], "value": rule["cutoff"]["value"]},
                   criteria_part=result_from(part, True),
                   censored=[t["input"] for t in terms if t["comparator"] is not None])
        details += [{"code": t["input"], "missing": t["missing"], "conflict": t["conflict"]}
                    for t in terms if not t["usable"]]
    out["result"] = result_from(overall, gate)
    out["missing"] = _missing(details)
    return out


def combine_level(rule_results: dict, dynamic: dict, combine: dict) -> tuple:
    """ALERT > WATCH > UNDETERMINED > NONE, with the drivers that produced the level."""
    drivers = [{"kind": "RULE", "rule": rid, "result": "MET"}
               for rid in combine["alert_on_met"] if rule_results[rid]["result"] == "MET"]
    core = [i for i in dynamic["indicators"] if i["status"] == "TRIGGERED" and i["role"] == "CORE"]
    if drivers or dynamic["level"] == "ALERT":
        return "ALERT", drivers + [_dyn_driver(i) for i in core]
    if dynamic["level"] == "WATCH":
        general = [i for i in dynamic["indicators"] if i["status"] == "TRIGGERED" and i["role"] == "GENERAL"]
        return "WATCH", [_dyn_driver(i) for i in general]
    undetermined = [{"kind": "RULE", "rule": rid, "result": "INDETERMINATE",
                     "missing": rule_results[rid]["missing"]}
                    for rid in combine["undetermined_on_indeterminate"]
                    if rule_results[rid]["result"] == "INDETERMINATE"]
    if undetermined:
        return "UNDETERMINED", undetermined
    return "NONE", []


def _dyn_driver(indicator: dict) -> dict:
    out = {"kind": "DYNAMIC", "code": indicator["code"], "role": indicator["role"],
           "direction": indicator["bad_direction"], "change": indicator["change"],
           "refs": indicator["refs"]}
    if indicator.get("measure") in ("APPEAR", "PERSIST"):  # 0.2 的是/否类指标；0.1 的结果逐字不变
        out["measure"] = indicator["measure"]
    return out
