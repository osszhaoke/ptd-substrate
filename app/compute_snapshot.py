"""Value-only calculation seams. Caller retains its original A/SQL boundaries.

CAPTURE_INPUTS is an internal rollback switch, not a config or public contract.
False preserves the existing reference path; True detaches every input value.
No connection, Instance, cache, notifier or external resource is accepted.
"""
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

CAPTURE_INPUTS = False


class FrozenDict(dict):
    def _deny(self, *args, **kwargs):
        raise TypeError('FROZEN_COMPUTE_INPUT')
    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _deny
    def __deepcopy__(self, memo):
        return self


def freeze(value):
    from cards import Obs
    from rules import Value
    if isinstance(value, FrozenDict):
        return value
    if isinstance(value, dict):
        return FrozenDict({k: freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(v) for v in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(freeze(v) for v in value)
    if isinstance(value, Value):
        return replace(value, value=freeze(value.value), refs=freeze(value.refs))
    if isinstance(value, Obs):
        return replace(value, payload=freeze(value.payload))
    if value is None or isinstance(value, (str, bytes, bool, int, float, Decimal, date, datetime)):
        return value
    raise TypeError('NON_VALUE_COMPUTE_INPUT: ' + type(value).__name__)


def capture(*values):
    return tuple(freeze(v) for v in values) if CAPTURE_INPUTS else values


def engine_plan(rule_id, groups, prof, days, latest, evaluate):
    """Pure proposal. Dedup read and commit remain in the original transaction."""
    todo = {}
    for day in sorted(days):
        res, inputs = evaluate(rule_id, groups, day, prof)
        it = latest.get(day)
        if it is None:
            todo[day] = (res, inputs, 'NEW')
        elif it['status'] == 'VANISHED' or it['inputs'] != inputs:
            todo[day] = (res, inputs, 'STALE')
    gone = [tp for tp, it in latest.items() if tp not in days and it['status'] == 'EVALUATED']
    return todo, gone


def custom_point(definition, tp, days, evaluate):
    if tp in days:
        level, result, inputs = evaluate(definition, tp, days)
        return level, result, inputs, 'EVALUATED'
    return 'NONE', {'tp': tp, 'status': 'VANISHED'}, frozenset(), 'VANISHED'


def vitals_result(items, day):
    return {'tp': day, 'items': [{'code': i['code'], 'label_zh': i['label_zh'], 'value': i['value'], 'unit': i['unit'],
                                 'observed_at': i['observed_at'] or i['observed_date'], 'source_kind': i['source_kind'],
                                 'ref': f"{i['observation_id']}@{i['revision']}"} for i in items]}


def core_point(rule_definitions, combination, engine_version, tp, values_cache, eval_rule, combine_level):
    """Original rule evaluation over detached values and definitions; no Card object."""
    vals = values_cache[tp]
    rules = {rid: eval_rule(rid, rule, vals) for rid, rule in rule_definitions.items()}
    dynamic = {"level": "NONE", "indicators": [], "retired": True,
               "reason": "MAS.DYN demo thresholds retired; observations remain available."}
    level, drivers = combine_level(rules, dynamic, combination)
    shown = {}
    for code, v in sorted(vals.items()):
        shown[code] = {"value": None if v.value is None else (("true" if v.value else "false")
                                                               if v.kind == "BOOLEAN" else format(v.value, "f")),
                       "comparator": v.comparator, "unit": v.unit, "conflict": v.conflict, "refs": list(v.refs)}
    return level, {"tp": tp, "engine_version": engine_version, "level": level, "drivers": drivers,
                   "rules": rules, "dynamic": dynamic, "values": shown}
