"""星轨 · 卡片设置与"设备断开"通知（路径 C，PRD Δ2 / DC-21 / DC-22）。

卡片设置（状态工程建卡、绑定、解绑、配通知）写在实例的 startrack/card_setup.jsonl，只追加；当前设置 = 依次折叠。
"设备断开"：绑定在"我的体征"上的来源，接入失效或超过时限没有新读数，就记一条事件并按配置通知本人（星轨照发，
星簇补记到预置授权 G-001 的记录里）。恢复后再断开会再通知一次；同一次断开只通知一次。
"""
from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from contextlib import contextmanager
import sys
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

SOURCES = {"DEVICE_OURA": "Oura", "PHONE_HEALTH": "苹果健康", "DEVICE_SOMALOOP": "Somaloop 手环", "DEVICE_QKEER": "Qkeer"}
# Independent display cards must not change the legacy notification/sleep binding set.
# In particular, adding Garmin to SOURCES would hide old Garmin data when historical
# vitals_sources records have no Garmin entry. New cards use this display catalogue.
CARD_SOURCES = {"DEVICE_GARMIN": "Garmin", **SOURCES}
_LOCK = threading.Lock()


def _append(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _read(path: Path) -> list:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


class CardSetup:
    def __init__(self, root: Path, default_cards: list):
        self.path = root / "startrack" / "card_setup.jsonl"
        self.default_cards = list(default_cards)

    def state(self, *, rows=None) -> dict:
        st = {"cards": list(self.default_cards), "vitals_sources": None, "notify": {}, "changed_at": None}
        for ev in _read(self.path) if rows is None else rows:
            if ev["action"] == "CREATE_CARD":
                if ev["card"] not in st["cards"]:
                    st["cards"].append(ev["card"])
                if ev["card"] == "VITALS":
                    st["vitals_sources"] = dict(ev.get("sources") or {})
                st["notify"][ev["card"]] = dict(ev.get("notify") or {})
            elif ev["action"] == "BIND":
                st["vitals_sources"] = dict(st["vitals_sources"] or {}, **{ev["source"]: bool(ev["bound"])})
            st["changed_at"] = ev["at"]
        return st

    def bound(self, family: str) -> bool:
        vs = self.state()["vitals_sources"]
        return True if vs is None else bool(vs.get(family))

    def capture_version(self, *, byte_limit):
        """Caller holds A; short A -> D capture, without reading history."""
        from compute_input_versions import capture_prefix, private_value
        with _LOCK:
            return capture_prefix(self.path.parent.parent, self.path,
                                  byte_limit=byte_limit,
                                  context=private_value(self.default_cards))

    def check_version(self, version):
        """Caller keeps A through use; D excludes setup appenders."""
        with _LOCK:
            version.require_current()

    def create_card(self, card: str, sources: dict, notify: dict, at: str) -> dict:
        with _LOCK:
            _append(self.path, {"id": uuid.uuid4().hex[:12], "at": at, "action": "CREATE_CARD", "card": card,
                                "sources": {k: bool(v) for k, v in (sources or {}).items() if k in SOURCES},
                                "notify": {k: [str(x) for x in v] for k, v in (notify or {}).items()}})
        return self.state()

    def bind(self, source: str, bound: bool, at: str) -> dict:
        if source not in SOURCES:
            raise ValueError("SOURCE_UNKNOWN")
        with _LOCK:
            _append(self.path, {"id": uuid.uuid4().hex[:12], "at": at, "action": "BIND", "source": source,
                                "bound": bool(bound)})
        return self.state()


def read_settings_version(lease):
    """Outside A/D, fold exactly the captured prefix with the original parser."""
    from compute_input_versions import FileInput, private_value
    defaults = lease.context.copy()
    text = lease.read_text()
    rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    # Passing rows makes state a pure fold; it cannot reopen the latest path.
    state = CardSetup(Path(lease.version.root), defaults).state(rows=rows)
    return FileInput(lease.version, private_value(state))


@dataclass(frozen=True)
class EventPrefix:
    """One immutable captured prefix; projection cannot reread a newer file."""
    present: bool
    raw: bytes

    @property
    def version(self):
        return hashlib.sha256((b'1' if self.present else b'0') + self.raw).hexdigest()

    def rows(self):
        return [json.loads(line) for line in self.raw.decode('utf-8').splitlines() if line.strip()]


class DeviceEvents:
    """设备断开 / 恢复事件，只追加。"""

    def __init__(self, root: Path):
        self.path = root / "startrack" / "device_events.jsonl"

    def capture(self) -> EventPrefix:
        with _LOCK:
            present = self.path.exists()
            raw = self.path.read_bytes() if present else b''
        return EventPrefix(present, raw)

    def append(self, record: dict) -> None:
        with _LOCK:
            _append(self.path, record)

    def list(self) -> list:
        return self.capture().rows()

    def offline_now(self) -> dict:
        state = {}
        for ev in self.list():
            state[ev["source"]] = ev if ev["kind"] == "DEVICE_OFFLINE" else None
        return {k: v for k, v in state.items() if v}


def check(inst, vitals: dict, oura_status: str | None, *, now: datetime | None = None, notifiers=None,
          offline_hours: float = 36) -> list:
    """看绑定在"我的体征"上的每个来源是否断开；状态有变化才记事件，断开时按配置通知。返回新记的事件。"""
    now = now or datetime.now(timezone.utc)
    setup = CardSetup(inst.ctx.root, inst.spec["cards"]).state()
    if "VITALS" not in setup["cards"]:
        return []
    events = DeviceEvents(inst.ctx.root)
    offline = events.offline_now()
    newest, seen = {}, set()
    for item in vitals.get("items") or []:
        fam = item.get("family")
        if fam not in SOURCES:
            continue
        seen.add(fam)
        t = item.get("observed_at") or ((item.get("observed_date") or "") + "T12:00:00+00:00")
        try:
            at = datetime.fromisoformat(t)
        except ValueError:
            continue
        newest[fam] = max(newest.get(fam, at), at)
    if oura_status:
        seen.add("DEVICE_OURA")
    out = []
    for fam in sorted(seen):
        if setup["vitals_sources"] is not None and not setup["vitals_sources"].get(fam):
            continue  # 没绑定的来源不归"我的体征"管
        reason = None
        if fam == "DEVICE_OURA" and oura_status and oura_status != "CONNECTED":
            reason = {"NEEDS_REAUTH": "Oura 授权失效，需要重新授权", "DISCONNECTED": "Oura 已在星炬断开接入"}.get(
                oura_status, "Oura 接入状态：" + oura_status)
        elif fam in newest and now - newest[fam] > timedelta(hours=offline_hours):
            hours = int((now - newest[fam]).total_seconds() // 3600)
            reason = f"{SOURCES[fam]} 已经 {hours} 小时没有新读数"
        if reason and fam not in offline:
            rec = {"id": "D-" + uuid.uuid4().hex[:10], "kind": "DEVICE_OFFLINE", "source": fam, "reason": reason,
                   "at": inst.now(), "title": "设备断开 · " + SOURCES[fam],
                   "body": reason + "。\"我的体征\"暂时不会更新，已有记录保留。", "deliveries": []}
            who = (setup["notify"].get("VITALS") or {}).get("DEVICE_OFFLINE") or []
            if "self" in who:
                for n in notifiers or []:
                    try:
                        n.send(rec["title"], rec["body"], "WATCH")
                        rec["deliveries"].append({"channel": n.channel, "outcome": "SENT", "detail": ""})
                    except Exception as exc:  # noqa: BLE001
                        rec["deliveries"].append({"channel": n.channel, "outcome": "FAILED",
                                                  "detail": type(exc).__name__})
            events.append(rec)
            out.append(rec)
        elif not reason and fam in offline:
            rec = {"id": "D-" + uuid.uuid4().hex[:10], "kind": "DEVICE_ONLINE", "source": fam, "at": inst.now(),
                   "title": "设备恢复 · " + SOURCES[fam], "body": SOURCES[fam] + " 又有新读数了。", "deliveries": []}
            events.append(rec)
            out.append(rec)
    return out


def macos_enabled(config: dict) -> bool:
    return bool(config.get("macos_notify")) and sys.platform == "darwin"


@contextmanager
def capture_inputs(root, default_cards):
    """Hold the existing owner while a caller pins its SQL read snapshot."""
    with _LOCK:
        def prefix(path):
            present = path.exists()
            return EventPrefix(present, path.read_bytes() if present else b'')
        setup = CardSetup(root, default_cards)
        settings = prefix(setup.path)
        events = prefix(DeviceEvents(root).path)
        yield setup.state(rows=settings.rows()), events, settings


@contextmanager
def compute_settings(root, default_cards):
    """Existing D owner: capture or validate settings across a caller's BEGIN.

    Do not call state wrappers, notification preparation or another lock here.
    The caller acquires A before this lease; storage delegates never acquire D.
    """
    with _LOCK:
        setup = CardSetup(root, default_cards)
        present = setup.path.exists()
        prefix = EventPrefix(present, setup.path.read_bytes() if present else b'')
        yield setup.state(rows=prefix.rows()), prefix.version
