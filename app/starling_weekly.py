"""Read-only weekly focus summary; model arranges tokens, local code renders facts.

Only the four approved, visible, pinned groups are eligible. The model receives
fact identifiers and categorical descriptions, never measurements or result text.
This adapter reads an existing snapshot and does not open stores or write caches.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
import hashlib
import json
from zoneinfo import ZoneInfo

import compete_ai
import rule_registry as rules
import starling_page


NAMES = {"MAS": "MAS 预警", "BLOOD": "血液细胞", "COAG": "凝血", "LIVER": "肝脏"}
MAS_RULES = frozenset(("MAS.HLH-2004", "MAS.EULAR-2016", "MAS.MS-2019"))
JOINS = {"next": "；", "also": "；另外，", "meanwhile": "；同时，"}
METHOD = "本地模型仅组织事实顺序和衔接词；数值、日期与结果由本机记录原样回填，未作医学判断。"
SYSTEM = (
    "你是本地星灵，为用户组织所选时间范围内的关注记录。输入只有事实编号和类别，不含健康读数。"
    "每张卡的全部事实必须各用一次，不能遗漏、重复或跨卡。"
    "可以根据事实类型调整顺序，并选择衔接词，使每卡形成一段。"
    "输出严格JSON：{\"cards\":[{\"id\":\"grp:BLOOD\",\"items\":["
    "{\"fact\":\"F1\",\"join\":\"start\"},{\"fact\":\"F2\",\"join\":\"also\"}]}]}。"
    "每卡第一项join只能为start，之后只能为next、also、meanwhile。"
    "保持卡片输入顺序，只输出指定字段；禁止自由文本、医学判断或建议。"
)


def _window(now, tz):
    zone = ZoneInfo(tz)
    current = datetime.fromisoformat(now) if isinstance(now, str) else now
    if not isinstance(current, datetime) or current.tzinfo is None:
        raise ValueError("WEEKLY_NOW_REQUIRES_TIMEZONE")
    current = current.astimezone(zone)
    start = datetime.combine(current.date() - timedelta(days=6), time.min, zone)
    return start, current, zone


def _when(temporal, tp, zone):
    """Return observation time and precision; never fall back to a save timestamp."""
    temporal = temporal or {}
    role = temporal.get("role")
    try:
        if role == "INSTANT":
            value = datetime.fromisoformat(temporal["observed_at"])
            if value.tzinfo is None:
                return None
            local = value.astimezone(zone)
            return local, local.isoformat(timespec="seconds"), "instant"
        if role == "DAY":
            day = date.fromisoformat(temporal["observed_date"])
            return datetime.combine(day, time.min, zone), day.isoformat(), "day"
        if role is None and tp:
            day = date.fromisoformat(tp)
            return datetime.combine(day, time.min, zone), day.isoformat(), "day"
    except (ValueError, TypeError, KeyError):
        pass
    return None


def _shown(value):
    if value is None:
        return "缺失"
    if value == "":
        return "空值"
    if value is True or value == "true":
        return "有"
    if value is False or value == "false":
        return "无"
    return str(value)


def _clause(label, records, period_label="近7天"):
    if not records:
        return f"{label}：{period_label}无可用观测记录"
    observations = "、".join(
        f"{r['at']} {r.get('comparator') or ''}{_shown(r['value'])}"
        + (" " + r['unit'] if r['unit'] else "")
        + ("（仅记录日期）" if r['precision'] == "day" else "")
        for r in records
    )
    return f"{label}：{len(records)}次记录，{observations}"


def _fact(card, kind, label, text, model_text):
    card["facts"].append(dict(kind=kind, label=label, text=text, model_text=model_text))


def _raw_records(snap, code, label, start, end, zone):
    records, unknown = [], 0
    # The current snapshot repeats its unknown-time observations in a convenience
    # subset. Keep the primary timeline exactly as supplied, including duplicate
    # rows, and only supplement references absent from that timeline.
    rows = list(snap.get("timeline") or [])
    references = {row["ref"] for row in rows if row.get("ref")}
    for row in snap.get("unknown_time") or []:
        ref = row.get("ref")
        if ref and ref in references:
            continue
        rows.append(row)
        if ref:
            references.add(ref)
    for row in rows:
        if row.get("code") != code:
            continue
        when = _when(row.get("temporal"), row.get("tp"), zone)
        if when is None:
            unknown += 1
            continue
        instant, at, precision = when
        if not start <= instant <= end:
            continue
        raw = row.get("value_raw")
        value = _shown(raw) if isinstance(raw, bool) or raw in ("true", "false") else raw
        records.append(dict(label=label, at=at, precision=precision,
                            value=value, value_raw=raw, unit=row.get("unit_raw") or "",
                            comparator=row.get("comparator") or "", ref=row.get("ref"),
                            code=code, kind="observation", _sort=instant))
    # Stable sorting preserves original order for multiple observations at one time.
    records.sort(key=lambda r: r.pop("_sort"))
    return records, unknown


def _branch(card, group, snap, start, end, zone, period_label="近7天", scope_label="本周"):
    seen = set()
    for entry in group.get("cards") or []:
        definition = rules.BY_ID.get(entry.get("rule")) or {}
        if definition.get("set") != group["id"] or definition.get("kind") != "原始观测":
            continue
        for code in definition.get("inputs") or []:
            if code in seen:
                continue
            seen.add(code)
            label = definition["name"]
            records, unknown = _raw_records(snap, code, label, start, end, zone)
            card["records"].extend(records)
            kind = "empty" if not records else "single" if len(records) == 1 else "observations"
            description = {"empty": scope_label + "无可用观测", "single": "仅一次观测，不表示趋势",
                           "observations": scope_label + "多次观测，仅罗列原始读数，不判断可比性"}[kind]
            text = _clause(label, records, period_label)
            if len(records) == 1:
                text += "，仅一次观测，不能判断变化"
            if unknown:
                text += f"；另有{unknown}条记录的观测时间不明确，未计入{scope_label}"
            _fact(card, kind, label, text, description)


def _mas(card, group, snap, start, end, zone, period_label="近7天", scope_label="本周"):
    aggregate = []
    verification = {point["tp"]: point.get("status") for point in snap.get("timepoints") or []}
    for point in snap.get("timepoints") or []:
        when = _when(None, point.get("tp"), zone)
        if when is None or not start <= when[0] <= end or point.get("status") == "VANISHED":
            continue
        if point.get("level_zh") is None:
            continue
        value = str(point["level_zh"])
        if point.get("status") not in ("FRESH", "EVALUATED"):
            value += "（已有结果待更新核验）"
        aggregate.append(dict(label="综合关注", at=when[1], precision="day", value=value,
                              unit="", ref=f"run:{point.get('run_id')}:{point['tp']}",
                              run_id=point.get("run_id"), kind="state", code="sjia-mas"))
    aggregate.sort(key=lambda r: r["at"])
    card["records"].extend(aggregate)
    _fact(card, "state" if aggregate else "empty", "综合关注", _clause("综合关注", aggregate, period_label),
          scope_label + "有已计算状态结果" if aggregate else scope_label + "无可用状态结果")
    for entry in group.get("cards") or []:
        rule = entry.get("rule")
        if rule not in MAS_RULES:
            continue
        label = (rules.BY_ID.get(rule) or {}).get("name") or rule
        latest = {}
        for run in sorted(entry.get("runs") or [], key=lambda r: r["run_id"]):
            for item in run.get("items") or []:
                latest[item["tp"]] = dict(item, run_id=run["run_id"])
        records = []
        for tp in sorted(latest):
            item = latest[tp]
            when = _when(None, tp, zone)
            if when is None or not start <= when[0] <= end or item.get("status") == "VANISHED":
                continue
            value = item.get("text") or item.get("status_zh") or "暂无可用结果"
            # Per-rule results use the same formal calculation as the aggregate.
            # A stale/unverified snapshot must not make its rule rows look fresh.
            if verification.get(tp) in ("STALE", "UNVERIFIED"):
                value = str(value) + "（已有结果待更新核验）"
            records.append(dict(label=label, at=when[1], precision="day", value=value, unit="",
                                ref=f"run:{item['run_id']}:{rule}:{tp}", run_id=item["run_id"],
                                rule=rule, code=rule, kind="state"))
        card["records"].extend(records)
        _fact(card, "state" if records else "empty", label, _clause(label, records, period_label),
              scope_label + "有已计算规则结果" if records else scope_label + "无可用规则结果")


def build(snap, now, tz):
    """Project an existing snapshot, honoring pin/hide and active group settings."""
    start, end, zone = _window(now, tz)
    prefs = snap.get("wall_prefs") or {}
    hidden = {item["card"] for item in prefs.get("hidden") or []}
    groups = {"grp:" + group["id"]: group for group in (snap.get("engines") or {}).get("groups") or []
              if group.get("id") in NAMES}
    cards, seen = [], set()
    for cid in prefs.get("pins") or []:
        if cid in hidden or cid not in groups or cid in seen:
            continue
        seen.add(cid)
        group = groups[cid]
        card = dict(id=cid, name=NAMES[group["id"]], facts=[], records=[])
        if group["id"] == "MAS":
            _mas(card, group, snap, start, end, zone)
        else:
            _branch(card, group, snap, start, end, zone)
        if not card["facts"]:
            _fact(card, "empty", card["name"], "本卡尚无已启用且可用于周汇总的指标", "没有已启用的汇总指标")
        cards.append(card)
    sequence = 0
    for card in cards:
        for fact in card["facts"]:
            sequence += 1
            fact["id"] = "F" + str(sequence)
    return dict(scope="pinned-approved-cards/1", period=dict(start=start.isoformat(), end=end.isoformat(),
                tz=tz, label=f"{start.date().isoformat()} 至 {end.isoformat(timespec='minutes')}"), cards=cards)


def _render(doc, report):
    if not isinstance(doc, dict) or set(doc) != {"cards"} or not isinstance(doc["cards"], list):
        raise ValueError("WEEKLY_MODEL_FORMAT")
    if len(doc["cards"]) != len(report["cards"]):
        raise ValueError("WEEKLY_MODEL_CARD_COVERAGE")
    output = []
    for selection, card in zip(doc["cards"], report["cards"]):
        if not isinstance(selection, dict) or set(selection) != {"id", "items"} or selection["id"] != card["id"]:
            raise ValueError("WEEKLY_MODEL_CARD")
        available = {fact["id"]: fact for fact in card["facts"]}
        items = selection["items"]
        if not isinstance(items, list) or len(items) != len(available):
            raise ValueError("WEEKLY_MODEL_COVERAGE")
        seen, phrases = set(), []
        for i, item in enumerate(items):
            if not isinstance(item, dict) or set(item) != {"fact", "join"}:
                raise ValueError("WEEKLY_MODEL_ITEM")
            fid, join = item["fact"], item["join"]
            if not isinstance(fid, str) or fid not in available or fid in seen:
                raise ValueError("WEEKLY_MODEL_FACT")
            if join != "start" if i == 0 else join not in JOINS:
                raise ValueError("WEEKLY_MODEL_JOIN")
            seen.add(fid)
            phrases.append(("" if i == 0 else JOINS[join]) + available[fid]["text"])
        output.append(dict(id=card["id"], name=card["name"], text="".join(phrases) + "。",
                           records=card["records"], fact_ids=[item["fact"] for item in items]))
    return output


def summarize(llm, report):
    """No model means no AI paragraph; no arbitrary generated prose is accepted."""
    fingerprint = hashlib.sha256(json.dumps(report, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    base = dict(period=report["period"], fp=fingerprint, scope=report["scope"])
    if not report["cards"]:
        return dict(base, state="empty", cards=[], why="我的关注中没有本次支持的卡片。")
    if llm is None or not llm.cfg.get("model"):
        return dict(base, state="no_llm", why="本地星灵未运行，本次未生成周总结。")
    if not compete_ai.LOCK.acquire(blocking=False):
        return dict(base, state="error", why="本地星灵正忙，请稍后重试。")
    try:
        if not llm.ensure():
            return dict(base, state="no_llm", why="本地星灵未运行，本次未生成周总结。")
        safe = {"cards": [{"id": card["id"], "name": card["name"], "facts": [
            {key: fact[key] for key in ("id", "kind", "label", "model_text")} for fact in card["facts"]
        ]} for card in report["cards"]]}
        prompt = json.dumps(safe, ensure_ascii=False)
        for attempt in range(2):
            raw = llm.chat(SYSTEM, prompt)
            try:
                # A JSON envelope may be fenced by a local model; no extra prose is rendered.
                raw = raw.strip()
                if raw.startswith("```json\n") and raw.endswith("\n```"):
                    raw = raw[8:-4]
                cards = _render(json.loads(raw), report)
                return dict(base, state="ok", cards=cards, by=starling_page.sign(llm), method=METHOD)
            except (ValueError, TypeError, KeyError):
                if attempt == 0:
                    prompt += "\n上次未通过格式或全量覆盖核对。每卡全部事实必须各用一次，只返回指定JSON。"
        return dict(base, state="rejected", why="星灵输出未通过事实完整性核对，本次未采用。")
    except Exception:
        return dict(base, state="error", why="本地星灵调用失败，本次未生成周总结。")
    finally:
        compete_ai.LOCK.release()
