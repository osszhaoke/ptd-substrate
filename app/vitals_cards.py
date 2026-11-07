"""Independent read-only vitals card definitions, using the existing StarTrack ledger.

No observation, device binding, notification, rule or authorization is changed here.
Definitions and request receipts are appended to card_def/card_setting in one existing
SQLite transaction. Legacy per-source cards are projected without writing a migration;
editing one persists its original wall identity. Values never enter the definitions.
"""
from __future__ import annotations

import hashlib
import json
import re
import uuid

from device_watch import CARD_SOURCES
from sqlite_util import transaction

VERSION = 1
KIND = "VITALS_VIEW"
DEF_KEY = "vitals_view_def"
REQUEST_KEY = "vitals_view_request"
LEGACY_PREFIX = "card:VITALS:"
NEW_PREFIX = "vitals-"
MAX_ITEMS = 100
_REQUEST_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{7,127}\Z")
_CARD_RE = re.compile(r"vitals-[0-9a-f]{32}\Z")


class VitalsCardError(ValueError):
    def __init__(self, code: str, detail: str, *, status: int = 400):
        super().__init__(code)
        self.code, self.detail, self.status = code, detail, status


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _pair(item) -> tuple[str, str] | None:
    if not isinstance(item, dict):
        return None
    family, code = item.get("family"), item.get("code")
    if not isinstance(family, str) or family not in CARD_SOURCES or not isinstance(code, str) or not code or len(code) > 160:
        return None
    return family, code


def _meta(item: dict) -> dict:
    family, code = _pair(item)
    # The unit is a placeholder hint only. Actual reading UI must use its own unit_raw.
    return {"family": family, "code": code,
            "label_zh": str(item.get("label_zh") or code),
            "unit": str(item.get("unit_raw") or item.get("unit") or "")}


def catalogue(snap: dict) -> list[dict]:
    """Available source/metric pairs; prefer the unfiltered read model, never history."""
    vitals = snap.get("vitals_all")
    if vitals is None:
        vitals = snap.get("vitals") or {}
    out = {}
    for item in vitals.get("items") or []:
        pair = _pair(item)
        if pair:
            out.setdefault(pair, _meta(item))
    order = {family: n for n, family in enumerate(CARD_SOURCES)}
    return sorted(out.values(), key=lambda item: (order[item["family"]], item["code"]))


def _legacy(snap: dict) -> list[dict]:
    setup = snap.get("card_setup") or {}
    if "VITALS" not in setup.get("cards", (snap.get("instance") or {}).get("cards", [])):
        return []
    visible = {}
    for item in (snap.get("vitals") or {}).get("items") or []:
        pair = _pair(item)
        if pair:
            visible.setdefault(pair[0], []).append(_meta(item))
    bindings = setup.get("vitals_sources")
    for family, selected in (bindings or {}).items():
        if family in CARD_SOURCES and selected:
            visible.setdefault(family, [])
    for family in snap.get("known_sources") or []:
        if family in CARD_SOURCES and (bindings is None or bindings.get(family) or family == "DEVICE_GARMIN"):
            visible.setdefault(family, [])
    prefs = snap.get("wall_prefs") or {}
    display = prefs.get("display") or {}
    # Explicit legacy preferences identify a card even while its source has no data.
    ids = list(display) + list(prefs.get("pins") or [])
    ids += [h.get("card", "") for h in prefs.get("hidden") or []]
    for card in ids:
        if isinstance(card, str) and card.startswith(LEGACY_PREFIX):
            family = card[len(LEGACY_PREFIX):]
            if family in CARD_SOURCES:
                visible.setdefault(family, [])
    available = {_pair(item): item for item in catalogue(snap)}
    cards = []
    for family, values in visible.items():
        cid = LEGACY_PREFIX + family
        pref = display.get(cid) or {}
        by_code = {v["code"]: v for v in values}
        chosen = pref.get("items")
        items = ([by_code.get(code) or available.get((family, code)) or
                  {"family": family, "code": code, "label_zh": code, "unit": ""}
                  for code in chosen] if isinstance(chosen, list) else list(by_code.values()))
        cards.append({"kind": KIND, "schema_version": VERSION, "card_id": cid, "wall_id": cid,
                      "revision": 0, "legacy": True,
                      "name": pref.get("name") or "我的体征（" + CARD_SOURCES[family] + "）",
                      "items": items, "created_at": None, "updated_at": None})
    return cards


def _stored(track) -> dict[str, dict]:
    rows = track.execute(
        "SELECT s.card_id,d.definition FROM card_setting s "
        "LEFT JOIN card_def d ON d.card_def_id=s.value "
        "WHERE s.key=? ORDER BY s.id", (DEF_KEY,))
    out = {}
    for cid, raw in rows:
        try:
            value = json.loads(raw)
            if (value["kind"] != KIND or value["schema_version"] != VERSION or value["card_id"] != cid
                    or type(value["revision"]) is not int or value["revision"] < 1):
                raise ValueError("definition identity")
        except (TypeError, ValueError, KeyError) as exc:
            raise VitalsCardError("VITALS_STORE_INVALID", "卡片配置无法读取，请保留现场并重试", status=500) from exc
        out[cid] = value
    return out


def state(track, snap: dict) -> list[dict]:
    """Stable definitions, including unavailable items and original legacy wall keys."""
    stored = _stored(track)
    cards = {c["card_id"]: c for c in _legacy(snap)}
    cards.update(stored)
    return [c for c in cards.values() if not c.get("deleted", False)]


def _request(body: dict) -> tuple[str, str, dict]:
    if not isinstance(body, dict) or set(body) - {"key", "request_id", "card_id", "expected_revision", "name", "items", "action"}:
        raise VitalsCardError("VITALS_CARD_INVALID", "卡片请求格式不正确")
    rid = body.get("request_id")
    if not isinstance(rid, str) or not _REQUEST_RE.fullmatch(rid):
        raise VitalsCardError("VITALS_CARD_INVALID", "缺少有效的保存请求编号")
    normalized = {k: v for k, v in body.items() if k not in ("key", "request_id")}
    try:
        digest = hashlib.sha256(_json(normalized).encode("utf-8")).hexdigest()
    except (ValueError, TypeError) as exc:
        raise VitalsCardError("VITALS_CARD_INVALID", "卡片请求格式不正确") from exc
    return rid, digest, normalized


def save(track, body: dict, snap: dict, *, at: str) -> dict:
    """Create or revise one card. Same request/body recovers its original receipt.

    Updates require expected_revision; a new card uses 0 (or omits it). New metrics
    must exist in this instance's catalogue. Existing selected pairs may survive a
    disconnected device, without permitting a different source to fill their values.
    """
    rid, digest, request = _request(body)
    receipt_id = "vitals-request:" + rid
    with transaction(track):
        row = track.execute("SELECT value FROM card_setting WHERE key=? AND card_id=? ORDER BY id DESC LIMIT 1",
                            (REQUEST_KEY, receipt_id)).fetchone()
        if row:
            receipt = json.loads(row[0])
            if receipt["request_sha256"] != digest:
                raise VitalsCardError("VITALS_REQUEST_CONFLICT", "同一保存请求的内容已变化，请先核对上次结果", status=409)
            return {"card": receipt["card"], "replayed": True}
        cid = request.get("card_id")
        current = None
        if cid is not None:
            if not isinstance(cid, str) or not (_CARD_RE.fullmatch(cid) or
                    cid.startswith(LEGACY_PREFIX) and cid[len(LEGACY_PREFIX):] in CARD_SOURCES):
                raise VitalsCardError("VITALS_CARD_UNKNOWN", "这张卡片不存在", status=404)
            current = next((c for c in state(track, snap) if c["card_id"] == cid), None)
            if current is None:
                raise VitalsCardError("VITALS_CARD_UNKNOWN", "这张卡片不属于当前数据基座", status=404)
        expected = request.get("expected_revision", 0 if current is None else None)
        if type(expected) is not int or expected < 0:
            raise VitalsCardError("VITALS_CARD_INVALID", "请提供卡片的当前版本")
        if expected != (current["revision"] if current else 0):
            raise VitalsCardError("VITALS_CARD_CONFLICT", "卡片已在其他页面修改，请重新读取后核对", status=409)
        action = request.get("action", "save")
        if action not in ("save", "delete"):
            raise VitalsCardError("VITALS_CARD_INVALID", "不支持的卡片操作")
        if action == "delete":
            if current is None or set(request) != {"card_id", "expected_revision", "action"}:
                raise VitalsCardError("VITALS_CARD_INVALID", "请指定要删除的卡片及当前版本")
            card = dict(current, revision=expected + 1, deleted=True, deleted_at=at, updated_at=at)
            _append(track, cid, card, rid, digest, at)
            return {"card": card, "replayed": False}
        name = request.get("name")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 40:
            raise VitalsCardError("VITALS_CARD_INVALID", "请填写 1 至 40 字的卡片名称")
        raw_items = request.get("items")
        if not isinstance(raw_items, list) or not 1 <= len(raw_items) <= MAX_ITEMS:
            raise VitalsCardError("VITALS_CARD_INVALID", "请选择 1 至 100 个展示项目")
        available = {_pair(item): item for item in catalogue(snap)}
        prior = {_pair(item): item for item in current["items"]} if current else {}
        chosen, seen = [], set()
        for item in raw_items:
            pair = _pair(item)
            if pair is None or set(item) != {"family", "code"} or pair in seen:
                raise VitalsCardError("VITALS_CARD_INVALID", "项目须包含设备来源和指标，且不能重复")
            metadata = available.get(pair) or prior.get(pair)
            if metadata is None:
                raise VitalsCardError("VITALS_ITEM_UNAVAILABLE", "所选项目不属于当前数据基座，请重新读取", status=409)
            chosen.append(dict(metadata))
            seen.add(pair)
        cid = cid or NEW_PREFIX + uuid.uuid4().hex
        card = {"kind": KIND, "schema_version": VERSION, "card_id": cid,
                "wall_id": current["wall_id"] if current else "card:" + cid,
                "revision": expected + 1, "legacy": bool(current and current["legacy"]),
                "name": name.strip(), "items": chosen,
                "created_at": current["created_at"] if current and current["created_at"] else at,
                "updated_at": at}
        _append(track, cid, card, rid, digest, at)
        return {"card": card, "replayed": False}


def _append(track, cid, card, rid, digest, at):
    encoded = _json(card)
    definition_id = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    track.execute("INSERT INTO card_def(card_def_id,card_id,definition,registered_at) VALUES(?,?,?,?)",
                  (definition_id, cid, encoded, at))
    track.execute("INSERT INTO card_setting(card_id,key,value,set_at) VALUES(?,?,?,?)",
                  (cid, DEF_KEY, definition_id, at))
    receipt = _json({"request_sha256": digest, "card": card})
    track.execute("INSERT INTO card_setting(card_id,key,value,set_at) VALUES(?,?,?,?)",
                  ("vitals-request:" + rid, REQUEST_KEY, receipt, at))
