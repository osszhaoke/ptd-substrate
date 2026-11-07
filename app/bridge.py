"""星炬 · 苹果健康接收端（iPhone 快捷指令 → 家里 Wi-Fi → 这台电脑）。

链路：设备写进健康 App → 我在 iPhone 上运行快捷指令"同步到星炬" → 本接收端 → 星炬正式保存 → 星轨计算
（Instance.save_items 一步做完保存 + 导出 + 计算）。

规则（spec N16-N20 / HR-31 / HR-50）：
- 接收端只在我打开时监听：enable() 起一个独立的 ThreadingHTTPServer（0.0.0.0:<port>，默认 8787），
  disable() 立刻关掉。主界面端口仍然只在 127.0.0.1。重启进程后接收端默认关着。
- 配对码 6 位数字，10 分钟内有效，只能用一次；连续输错 5 次作废。配对码只在内存里，不落盘、不进日志。
- 配对成功只给手机一次"只能写入"的凭据；这台电脑只留它的 SHA-256，而且放在实例目录之外
  （$PTDS_SECRETS 或 ~/.ptds/secrets），文件名绑定实例目录的绝对路径——实例搬家后需要重新配对。
- 每次上传都核对凭据（Authorization: Bearer <凭据>），不对就 401。
- 同一台手机的同一个批次号 = 同一个 request_id：重发不会重复保存，回执里记为"重复"。
- 不能保存的行逐行报原码、不保存；同一次上传里能保存的行照常保存（只把合格的行交给一次 save_items）。
- 日志只记事件、编号和条数，从不记数值、凭据和配对码。

HealthKit 类型 → H1 代码（见 TYPES；也接受去掉前缀的短名、英文显示名、中文显示名）：

    HKQuantityTypeIdentifierHeartRate                  AH_HR             bpm / count/min / 次/分
    HKQuantityTypeIdentifierRestingHeartRate           AH_RESTING_HR     bpm / count/min / 次/分
    HKQuantityTypeIdentifierHeartRateVariabilitySDNN   AH_HRV            ms
    HKQuantityTypeIdentifierOxygenSaturation           AH_SPO2           %   （健康常给小数 0.97 → 存 "97"，见 _spo2）
    HKQuantityTypeIdentifierRespiratoryRate            AH_RESP_RATE      次/分 / breaths/min / count/min
    HKQuantityTypeIdentifierBodyTemperature            AH_BODY_TEMP      °C / ℃ / degC（°F 不收，报 UNIT_UNSUPPORTED）
    HKQuantityTypeIdentifierStepCount                  AH_STEPS          steps / count / 步
    HKQuantityTypeIdentifierActiveEnergyBurned         AH_ACTIVE_ENERGY  kcal / Cal
    HKCategoryTypeIdentifierSleepAnalysis              AH_SLEEP          min（睡眠阶段样本按 end-start 折成分钟）
    HKQuantityTypeIdentifierBodyMass                   AH_WEIGHT         kg

时点：样本开始时间（start），INSTANT，保留手机给的时区偏移。unique_key 带上健康里的来源名（Apple Watch、
Oura……），同一时刻来自两个来源的读数各自保存，不跨来路合并。
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import socket
import sys
import threading
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

APP = Path(__file__).resolve().parent
if str(APP / "core") not in sys.path:
    sys.path.insert(0, str(APP / "core"))

import input_guard

from h1_common import H1Error, build_payload, canonical_decimal, time_key  # noqa: E402
from startorch_outbox import ObservationInput, open_startorch  # noqa: E402

SCHEMA = "ptds-bridge/0.1"
DEFAULT_PORT = 8787
CODE_MINUTES = 10
CODE_MAX_ATTEMPTS = 5
MAX_BODY = 16 * 1024 * 1024
MAX_SAMPLES = 50000
MAX_RECEIPTS = 200
SOURCE_KIND, TRUST_TIER = "APPLE_HEALTH", "DEVICE_CONSUMER"
CREDENTIAL_PREFIX = "ptdsah_"

# HK identifier -> (code, {incoming unit literal -> dictionary literal}). Units not listed here are passed
# through unchanged, so H1 itself decides (UNIT_UNSUPPORTED). Aliases only spell the SAME unit differently.
_HR_UNITS = {"bpm": "bpm", "BPM": "bpm", "count/min": "count/min", "次/分": "次/分", "次/分钟": "次/分"}
TYPES = {
    "HKQuantityTypeIdentifierHeartRate": ("AH_HR", _HR_UNITS),
    "HKQuantityTypeIdentifierRestingHeartRate": ("AH_RESTING_HR", _HR_UNITS),
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": ("AH_HRV", {"ms": "ms", "毫秒": "ms"}),
    "HKQuantityTypeIdentifierOxygenSaturation": ("AH_SPO2", {"%": "%", "": "%"}),
    "HKQuantityTypeIdentifierRespiratoryRate": ("AH_RESP_RATE", {"次/分": "次/分", "次/分钟": "次/分",
                                                                 "breaths/min": "breaths/min",
                                                                 "count/min": "count/min"}),
    "HKQuantityTypeIdentifierBodyTemperature": ("AH_BODY_TEMP", {"°C": "°C", "℃": "℃", "degC": "degC"}),
    "HKQuantityTypeIdentifierStepCount": ("AH_STEPS", {"steps": "steps", "count": "count", "步": "步",
                                                       "": "count"}),
    "HKQuantityTypeIdentifierActiveEnergyBurned": ("AH_ACTIVE_ENERGY", {"kcal": "kcal", "Cal": "Cal",
                                                                        "千卡": "kcal", "大卡": "kcal"}),
    "HKCategoryTypeIdentifierSleepAnalysis": ("AH_SLEEP", {"min": "min", "分钟": "min"}),
    "HKQuantityTypeIdentifierBodyMass": ("AH_WEIGHT", {"kg": "kg", "公斤": "kg"}),
}
_DISPLAY = {  # what a Shortcut user may type instead of the identifier (English / 简体中文 display names)
    "Heart Rate": "HeartRate", "心率": "HeartRate",
    "Resting Heart Rate": "RestingHeartRate", "静息心率": "RestingHeartRate",
    "Heart Rate Variability": "HeartRateVariabilitySDNN", "HRV": "HeartRateVariabilitySDNN",
    "心率变异性": "HeartRateVariabilitySDNN",
    "Blood Oxygen": "OxygenSaturation", "Oxygen Saturation": "OxygenSaturation", "血氧": "OxygenSaturation",
    "血氧饱和度": "OxygenSaturation",
    "Respiratory Rate": "RespiratoryRate", "呼吸频率": "RespiratoryRate", "呼吸速率": "RespiratoryRate",
    "Body Temperature": "BodyTemperature", "体温": "BodyTemperature",
    "Steps": "StepCount", "步数": "StepCount",
    "Active Energy": "ActiveEnergyBurned", "活动能量": "ActiveEnergyBurned",
    "Sleep": "SleepAnalysis", "睡眠": "SleepAnalysis", "睡眠分析": "SleepAnalysis",
    "Weight": "BodyMass", "Body Mass": "BodyMass", "体重": "BodyMass",
}
ALIASES = {}
for _ident in TYPES:
    ALIASES[_ident] = _ident
    ALIASES[_ident.split("Identifier", 1)[1]] = _ident
for _name, _short in _DISPLAY.items():
    ALIASES[_name] = next(i for i in TYPES if i.endswith("Identifier" + _short))

# Sleep stage values Shortcuts may show. Only "asleep" stages count as sleep minutes.
SLEEP_ASLEEP = re.compile(r"(?i)asleep|core|deep|rem|unspecified|睡眠|核心|深度|快速动眼|^睡着")
SLEEP_NOT_ASLEEP = re.compile(r"(?i)in ?bed|awake|卧床|清醒|醒着")

_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?(?:[.,]\d+)?\s*"
                      r"(Z|[+-]\d{2}(?::?\d{2})?)?")
_NUM_UNIT_RE = re.compile(r"\s*(-?\d+(?:,\d{3})*(?:[.,]\d+)?)\s*(.*?)\s*")
_THOUSANDS_RE = re.compile(r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?")


def _clean(text, limit: int, drop: str = ":|") -> str:
    """Free text from the phone: drop control characters and the ':' / '|' separators used in refs/keys."""
    out = "".join(ch for ch in str(text) if ord(ch) >= 32 and ch not in drop).strip()
    return out[:limit]


def parse_when(text, tz: str) -> str:
    """Shortcuts "Format Date → ISO 8601" (and close variants) → H1 instant 'YYYY-MM-DDTHH:MM:SS+HH:MM'.

    Accepted: 2026-10-13T08:05:00+08:00, 2026-10-13T08:05:00+0800, 2026-10-13 08:05:00 +0800,
    2026-10-13T00:05:00Z, fractional seconds (dropped), no seconds. Without an offset the instance's own
    time zone is assumed (documented in docs/apple_health_shortcut.md).
    """
    if not isinstance(text, str):
        raise H1Error("TEMPORAL_INVALID", "date text required")
    m = _DATE_RE.fullmatch(text.strip())
    if not m:
        raise H1Error("TEMPORAL_INVALID", "unrecognised date format")
    day, hh, mm, ss, off = m.groups()
    try:
        local = datetime.fromisoformat(f"{day}T{hh}:{mm}:{ss or '00'}")
    except ValueError:
        raise H1Error("TEMPORAL_INVALID", "not a valid date-time") from None
    if off is None:
        value = local.replace(tzinfo=ZoneInfo(tz))
    elif off == "Z":
        value = datetime.fromisoformat(local.isoformat() + "+00:00")
    else:
        digits = off[1:].replace(":", "")
        digits = digits + "00" if len(digits) == 2 else digits
        value = datetime.fromisoformat(f"{local.isoformat()}{off[0]}{digits[:2]}:{digits[2:]}")
    return value.isoformat(timespec="seconds")


def _decimal(value) -> Decimal:
    """JSON number (kept as its literal text) or numeric text → Decimal. Never goes through float."""
    if isinstance(value, bool) or value is None:
        raise H1Error("VALUE_INVALID", "number required")
    if not isinstance(value, (str, int)):
        raise H1Error("VALUE_INVALID", "number required")
    text = str(value).strip()
    # "1,234" (thousands, as Shortcuts may format step counts) vs "0,97" (decimal comma)
    text = text.replace(",", "") if _THOUSANDS_RE.fullmatch(text) else text.replace(",", ".")
    try:
        number = Decimal(text)
    except InvalidOperation:
        raise H1Error("VALUE_INVALID", "number required") from None
    if not number.is_finite():
        raise H1Error("VALUE_INVALID", "finite number required")
    return number


def _plain(number: Decimal) -> str:
    return canonical_decimal(number)


def _spo2(number: Decimal, unit: str) -> Decimal:
    """Health stores SpO2 as a fraction (0.97). A value <= 1 is read as a fraction and turned into percent
    (0.97 → 97) on purpose; a value > 1 is already percent (97 → 97). Both are saved with unit '%'."""
    return number * 100 if number <= 1 else number


def _read_document(read_text) -> dict:
    try:
        doc = json.loads(read_text())
    except (OSError, ValueError):
        doc = {}
    return {"schema": SCHEMA, "phones": list(doc.get("phones", [])), "receipts": list(doc.get("receipts", []))}


class Bridge:
    """One receiver per instance. All public methods are safe to call from the main server's handlers."""

    def __init__(self, instance, secrets_dir=None, port: int = DEFAULT_PORT, host: str = "0.0.0.0"):
        self.inst, self.port, self.host = instance, port, host
        ctx = instance.ctx
        self.path = Path(ctx.root) / "startorch" / "bridge.json"
        base = secrets_dir or os.environ.get("PTDS_SECRETS") or "~/.ptds/secrets"
        self.secrets_dir = Path(base).expanduser()
        root_tag = hashlib.sha256(str(Path(ctx.root).resolve()).encode("utf-8")).hexdigest()[:12]
        self.secret_path = self.secrets_dir / f"ptds-bridge-{ctx.instance_id}-{root_tag}.json"
        self._lock = threading.RLock()  # bridge state only; order is always app.lock -> self._lock
        self._code = None              # {"code", "expires_at", "used", "attempts"} — memory only
        self._server = None
        self._thread = None
        self._enabled_at = None

    # ------------------------------------------------------------------ helpers
    def _now(self) -> datetime:
        return datetime.fromisoformat(self.inst.now())

    def _log(self, event: str, *fields) -> None:
        log = getattr(getattr(self.inst, "app", None), "log", None)
        if callable(log):
            log(event, self.inst.ctx.instance_id, *fields)

    def _read(self) -> dict:
        return _read_document(lambda: self.path.read_text("utf-8"))

    def _write(self, doc: dict) -> None:
        _atomic_write(self.path, json.dumps(doc, ensure_ascii=False, indent=1).encode("utf-8"))

    def _hashes(self) -> dict:
        try:
            doc = json.loads(self.secret_path.read_text("utf-8"))
        except (OSError, ValueError):
            return {}
        return doc.get("phones", {}) if isinstance(doc, dict) else {}

    def _put_hashes(self, hashes: dict) -> None:
        self.secrets_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        doc = {"schema": SCHEMA + "-secrets", "instance_root": str(Path(self.inst.ctx.root).resolve()),
               "phones": hashes}
        _atomic_write(self.secret_path, json.dumps(doc, indent=1).encode("utf-8"), mode=0o600)

    # ------------------------------------------------------------------ main-UI side (127.0.0.1 routes)
    def code(self, now=None) -> dict:
        """New 6-digit pairing code, valid CODE_MINUTES, single use. Replaces any earlier code."""
        at = now if isinstance(now, datetime) else (datetime.fromisoformat(now) if now else self._now())
        input_guard.require_writable(self.inst)
        with self._lock:
            self._code = {"code": f"{secrets.randbelow(10 ** 6):06d}",
                          "expires_at": (at + timedelta(minutes=CODE_MINUTES)).isoformat(timespec="seconds"),
                          "used": False, "attempts": 0}
            self._log("bridge_code_issued")
            return {"code": self._code["code"], "expires_at": self._code["expires_at"]}

    def enable(self) -> dict:
        input_guard.require_writable(self.inst)
        with self._lock:
            if self._server is None:
                server = ThreadingHTTPServer((self.host, self.port), _make_handler(self))
                server.daemon_threads = True
                self._server = server
                self._thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.2},
                                                name="ptds-bridge", daemon=True)
                self._thread.start()
                self._enabled_at = self.inst.now()
                self._log("bridge_enabled", self.port)
            return self.state()

    def disable(self) -> dict:
        with self._lock:
            server, self._server, self._code, self._enabled_at = self._server, None, None, None
        if server is not None:
            server.shutdown()
            server.server_close()
            self._log("bridge_disabled")
        return self.state()

    @property
    def on(self) -> bool:
        return self._server is not None

    def state(self) -> dict:
        """Everything the 苹果健康 page renders. Never contains a credential or its hash."""
        with self._lock:
            code = None
            if self._code and not self._code["used"]:
                expired = self._now() >= datetime.fromisoformat(self._code["expires_at"])
                if not expired and self._code["attempts"] < CODE_MAX_ATTEMPTS:
                    code = {"code": self._code["code"], "expires_at": self._code["expires_at"], "used": False}
            doc = self._read()
            return {"on": self.on, "port": self.port, "enabled_at": self._enabled_at,
                    "addresses": lan_addresses(self.port) if self.on else [],
                    "code": code, "code_minutes": CODE_MINUTES,
                    "phones": self._phones(doc), "receipts": doc["receipts"], "n": len(doc["receipts"])}

    def _phones(self, doc: dict) -> list:
        hashes = self._hashes()
        return [dict(p, status="PAIRED" if p["id"] in hashes else "NEEDS_REPAIR") for p in doc["phones"]]

    def phones(self) -> list:
        with self._lock:
            return self._phones(self._read())

    def receipt_capture(self, capture):
        """A -> H metadata delegate; no secret store, parsing or device I/O."""
        with self._lock:
            return capture(self.inst.ctx.root, self.path)

    def receipts(self) -> list:
        with self._lock:
            return self._read()["receipts"]

    def unpair(self, phone_id: str) -> dict:
        """Revoke the phone's credential (its hash is deleted). Data already saved stays."""
        with self._lock:
            doc = self._read()
            keep = [p for p in doc["phones"] if p["id"] != phone_id]
            hashes = self._hashes()
            if len(keep) == len(doc["phones"]) and phone_id not in hashes:
                return {"outcome": "PHONE_UNKNOWN"}
            hashes.pop(phone_id, None)
            self._put_hashes(hashes)
            doc["phones"] = keep
            self._write(doc)
            self._log("bridge_unpaired", phone_id)
            return {"outcome": "UNPAIRED", "phone_id": phone_id}

    # ------------------------------------------------------------------ phone side (LAN routes)
    def pair(self, code, phone_name) -> tuple:
        """POST /ah/pair → (status, body). The credential is returned exactly once and never stored."""
        input_guard.require_writable(self.inst)
        with self._lock:
            c = self._code
            if c is None or c["used"] or c["attempts"] >= CODE_MAX_ATTEMPTS:
                self._log("bridge_pair_rejected", "CODE_INVALID")
                return 400, {"outcome": "CODE_INVALID"}
            given = re.sub(r"\D", "", str(code or ""))
            if not hmac.compare_digest(given.encode(), c["code"].encode()):
                c["attempts"] += 1
                self._log("bridge_pair_rejected", "CODE_INVALID")
                return 400, {"outcome": "CODE_INVALID"}
            if self._now() >= datetime.fromisoformat(c["expires_at"]):
                c["used"] = True
                self._log("bridge_pair_rejected", "CODE_EXPIRED")
                return 400, {"outcome": "CODE_EXPIRED"}
            c["used"] = True
            name = _clean(phone_name or "", 40) or "iPhone"
            doc = self._read()
            hashes = self._hashes()
            for old in [p for p in doc["phones"] if p["name"] == name]:  # re-pairing the same phone replaces it
                hashes.pop(old["id"], None)
            doc["phones"] = [p for p in doc["phones"] if p["name"] != name]
            phone = {"id": "P-" + uuid.uuid4().hex[:8], "name": name, "paired_at": self.inst.now(),
                     "last_sync": None}
            credential = CREDENTIAL_PREFIX + secrets.token_urlsafe(32)
            hashes[phone["id"]] = hashlib.sha256(credential.encode("utf-8")).hexdigest()
            self._put_hashes(hashes)
            doc["phones"].append(phone)
            self._write(doc)
            self._log("bridge_paired", phone["id"])
            return 200, {"outcome": "PAIRED", "phone_id": phone["id"], "phone": dict(phone, status="PAIRED"),
                         "credential": credential}

    def authenticate(self, header) -> dict | None:
        """Authorization: Bearer <credential> → the paired phone, or None."""
        if not isinstance(header, str) or not header.startswith("Bearer "):
            return None
        digest = hashlib.sha256(header[7:].strip().encode("utf-8")).hexdigest()
        with self._lock:
            match = None
            for phone_id, stored in self._hashes().items():
                if hmac.compare_digest(stored, digest):
                    match = phone_id
            if match is None:
                return None
            return next((p for p in self._read()["phones"] if p["id"] == match), None)

    def to_items(self, phone: dict, samples) -> tuple:
        """samples → (valid [(index, ObservationInput)], errors [{index, code}], in-upload duplicates)."""
        ctx, registry = self.inst.ctx, self.inst.app.registry
        valid, errors, seen, dup = [], [], {}, 0
        for index, s in enumerate(samples):
            try:
                item = self._item(phone, s)
                # Same check the formal save will run, done per row so one bad row cannot sink the upload.
                build_payload(registry, ctx, observation_id="OBS-" + "0" * 32, revision=1, status="ACTIVE",
                              code=item.code, value_raw=item.value_raw, comparator=None, unit_raw=item.unit_raw,
                              temporal=item.temporal, source_kind=item.source_kind, source_ref=item.source_ref,
                              trust_tier=item.trust_tier, batch_id="AH-CHECK", request_id="AH-CHECK",
                              saved_at=self.inst.now())
            except H1Error as exc:
                errors.append({"index": index, "code": exc.code})
                continue
            same = seen.get(item.unique_key)
            if same is not None:
                if (same.value_raw, same.unit_raw) == (item.value_raw, item.unit_raw):
                    dup += 1
                else:
                    errors.append({"index": index, "code": "DUPLICATE_IN_UPLOAD"})
                continue
            seen[item.unique_key] = item
            valid.append((index, item))
        return valid, errors, dup

    def _item(self, phone: dict, s) -> ObservationInput:
        if not isinstance(s, dict):
            raise H1Error("SAMPLE_INVALID", "object required")
        ident = ALIASES.get(str(s.get("type", "")).strip())
        if ident is None:
            raise H1Error("TYPE_UNSUPPORTED", "")
        code, units = TYPES[ident]
        tz = self.inst.ctx.tz
        start = parse_when(s.get("start") or s.get("startDate") or s.get("date"), tz)
        raw_value, unit = s.get("value"), s.get("unit")
        unit = "" if unit is None else str(unit).strip()
        if code == "AH_SLEEP" and isinstance(raw_value, str) and not _NUM_UNIT_RE.fullmatch(raw_value):
            if SLEEP_NOT_ASLEEP.search(raw_value) or not SLEEP_ASLEEP.search(raw_value):
                raise H1Error("SLEEP_NOT_ASLEEP", "")
            end = parse_when(s.get("end") or s.get("endDate"), tz)
            seconds = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()
            if seconds <= 0:
                raise H1Error("TEMPORAL_INVALID", "end before start")
            number, unit = Decimal(int(seconds)) / 60, "min"
            number = number.quantize(Decimal("0.1")) if number != number.to_integral_value() else number
        else:
            if isinstance(raw_value, str):
                m = _NUM_UNIT_RE.fullmatch(raw_value)  # "72 count/min" when the whole sample was put in a field
                if m:
                    raw_value, unit = m.group(1), unit or m.group(2)
            number = _decimal(raw_value)
            if code == "AH_SPO2":
                number = _spo2(number, unit)
        unit_raw = units.get(unit, unit)
        hk_source = _clean(s.get("source") or "Health", 80) or "Health"
        temporal = {"role": "INSTANT", "observed_at": start}
        source_ref = f"AH:{_clean(phone['name'], 40)}:{hk_source}:{start}"
        unique_key = f"AH|{code}|{time_key(temporal, source_ref)}|{hk_source}"
        return ObservationInput(unique_key, code, _plain(number), None, unit_raw, temporal, SOURCE_KIND,
                                source_ref, TRUST_TIER)

    def upload(self, phone: dict, body) -> tuple:
        """POST /ah/upload → (status, body). Caller has authenticated `phone`."""
        input_guard.require_writable(self.inst)
        if not isinstance(body, dict):
            return 400, {"outcome": "BAD_REQUEST", "error": "BODY_INVALID"}
        batch = body.get("batch_id")
        batch = _clean(batch, 64, drop="") if isinstance(batch, (str, int)) and not isinstance(batch, bool) else ""
        samples = flatten_samples(body.get("samples"))
        if not batch:
            return 400, {"outcome": "BAD_REQUEST", "error": "BATCH_ID_INVALID"}
        if not isinstance(samples, list) or len(samples) > MAX_SAMPLES:
            return 400, {"outcome": "BAD_REQUEST", "error": "SAMPLES_INVALID"}
        ctx = self.inst.ctx
        request_id = "AH-" + hashlib.sha256(f"{ctx.instance_id}|{phone['id']}|{batch}".encode()).hexdigest()[:24]
        batch_id = f"AH-{phone['id']}-{batch}"
        with self.inst.app.lock:  # one writer at a time across the whole process
            valid, errors, dup = self.to_items(phone, samples)
            replay = self._seen(phone["id"], batch) or self._request_known(request_id)
            counts = {"CREATED": 0, "REVISED": 0, "UNCHANGED": 0}
            sync = None
            if valid:
                try:
                    res = self.inst.save_items([item for _, item in valid], batch_id=batch_id,
                                               request_id=request_id)
                except H1Error as exc:
                    self._log("bridge_upload_failed", phone["id"], exc.code)
                    status = 409 if exc.code == "REQUEST_CONFLICT" else 500
                    return status, {"outcome": "BATCH_CONFLICT" if status == 409 else "SAVE_FAILED",
                                    "error": exc.code}
                for r in res.get("results", []):
                    counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
                s = res.get("sync") or {}
                sync = {"ok": bool(s.get("ok")), "error": (s.get("error") or {}).get("code") if s else None}
            if replay:  # same phone + same batch id: nothing new was written this time
                counts = {"CREATED": 0, "REVISED": 0, "UNCHANGED": len(valid)}
            with self._lock:
                doc = self._read()
                ph = next((p for p in doc["phones"] if p["id"] == phone["id"]), None)
                since = ph.get("last_sync") if ph else None
                errors_by_code = {}
                for e in errors:
                    errors_by_code[e["code"]] = errors_by_code.get(e["code"], 0) + 1
                starts = [item.temporal["observed_at"] for _, item in valid]
                receipt = {"receipt_id": "HB-" + uuid.uuid4().hex[:10], "batch": batch, "batch_id": batch_id,
                           "request_id": request_id, "phone_id": phone["id"], "phone": phone["name"],
                           "when": self.inst.now(), "since": since,
                           "first_sample": min(starts) if starts else None,
                           "last_sample": max(starts) if starts else None,
                           "received": len(samples), "created": counts["CREATED"], "revised": counts["REVISED"],
                           "duplicate": counts["UNCHANGED"] + dup, "failed": len(errors),
                           "errors": errors, "errors_by_code": [{"code": k, "n": n} for k, n in errors_by_code.items()],
                           "replay": replay, "sync": sync}
                if ph is not None and not replay:
                    ph["last_sync"] = receipt["when"]
                doc["receipts"] = [receipt] + doc["receipts"][:MAX_RECEIPTS - 1]
                self._write(doc)
        self._log("bridge_received", phone["id"], receipt["received"], receipt["created"], receipt["duplicate"],
                  receipt["failed"])
        return 200, {"outcome": "RECEIVED", "receipt": receipt, "message": phone_message(receipt)}

    def _seen(self, phone_id: str, batch: str) -> bool:
        with self._lock:
            return any(r.get("phone_id") == phone_id and r.get("batch") == batch for r in self._read()["receipts"])

    def _request_known(self, request_id: str) -> bool:
        torch = open_startorch(self.inst.ctx)
        try:
            return torch.execute("SELECT 1 FROM save_request WHERE request_id = ?",
                                 (request_id,)).fetchone() is not None
        finally:
            torch.close()


def _loads(text: str):
    return json.loads(text, parse_float=str, parse_constant=lambda _: None)


def flatten_samples(samples):
    """Shortcuts may hand the sample list over as a JSON array, as an array nested in an array, as JSON text,
    or as text with one JSON object per line (a list of 字典 turned into text). All become a flat list.
    Returns None when `samples` is not any of these."""
    if isinstance(samples, str):
        text = samples.strip()
        try:
            samples = _loads(text) if text else []
        except ValueError:
            try:
                samples = [_loads(line) for line in text.splitlines() if line.strip()]
            except ValueError:
                return None
        if isinstance(samples, dict):
            samples = [samples]
    if not isinstance(samples, list):
        return None
    out = []
    for s in samples:
        if isinstance(s, str):
            try:
                s = _loads(s)
            except ValueError:
                pass
        if isinstance(s, list):
            out.extend(s)
        else:
            out.append(s)
    return out


def phone_message(r: dict) -> str:
    """Notification text the Shortcut shows (same wording as the prototype's phoneMsg)."""
    if not r["received"]:
        return "这段时间没有收到数据。"
    text = f"星炬已收到 {r['received']} 条，新增 {r['created']} 条。"
    if r["duplicate"] and not r["created"]:
        text += "之前已经收到过，没有新增。"
    if r["failed"]:
        text += f"有 {r['failed']} 条不能保存，其余已保存。"
    return text


def lan_addresses(port: int) -> list:
    """URLs the phone can use: the Bonjour name and the current LAN IP (no packet is sent)."""
    out = []
    host = socket.gethostname()
    if host:
        out.append(f"http://{host if host.endswith('.local') else host + '.local'}:{port}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
        if ip and not ip.startswith("127."):
            out.append(f"http://{ip}:{port}")
    except OSError:
        pass
    return out


def _atomic_write(path: Path, data: bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), mode)  # Windows：二进制，不改换行
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        if tmp.exists():
            tmp.unlink()
        raise


def _make_handler(bridge: Bridge):
    class Handler(BaseHTTPRequestHandler):
        server_version = "PTDS-bridge/0.1"

        def log_message(self, fmt, *args):  # the default logger would print request lines; we log nothing here
            pass

        def _json(self, status: int, obj):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.split("?", 1)[0] == "/ah/ping":
                return self._json(200, {"ok": True, "service": "ptds-bridge"})
            return self._json(404, {"outcome": "NOT_FOUND"})

        def do_POST(self):
            try:
                config = getattr(getattr(bridge.inst, "app", None), "config", {})
                with input_guard.request_body(self, self.path.split("?", 1)[0], config, maximum=MAX_BODY):
                    return self._post()
            except input_guard.RequestError as exc:
                self.close_connection = True
                return self._json(exc.status, {"outcome": "BAD_REQUEST", "error": exc.code})
            except H1Error as exc:
                self.close_connection = True
                return self._json(400, {"outcome": "BAD_REQUEST", "error": exc.code})

        def _post(self):
            path = self.path.split("?", 1)[0]
            if path not in ("/ah/pair", "/ah/upload"):
                return self._json(404, {"outcome": "NOT_FOUND"})
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = -1
            if not 0 < length <= MAX_BODY:
                self.close_connection = True
                return self._json(413 if length > MAX_BODY else 400, {"outcome": "BAD_REQUEST", "error": "BODY_SIZE"})
            phone = None
            if path == "/ah/upload":  # every upload checks the credential; nothing is parsed before that
                phone = bridge.authenticate(self.headers.get("Authorization"))
                if phone is None:
                    bridge._log("bridge_unauthorized")
                    self.close_connection = True
                    return self._json(401, {"outcome": "UNPAIRED"})
            raw = self.rfile.read(length)
            try:
                # JSON numbers keep their literal text: 0.97 stays "0.97", never a float.
                body = _loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                return self._json(400, {"outcome": "BAD_REQUEST", "error": "JSON_INVALID"})
            try:
                if path == "/ah/pair":
                    if not isinstance(body, dict):
                        return self._json(400, {"outcome": "BAD_REQUEST", "error": "BODY_INVALID"})
                    return self._json(*bridge.pair(body.get("code"), body.get("phone_name")))
                return self._json(*bridge.upload(phone, body))
            except H1Error as exc:
                return self._json(400, {"outcome": "BAD_REQUEST", "error": exc.code})
            except Exception as exc:  # noqa: BLE001 — code only, never values
                bridge._log("bridge_error", type(exc).__name__)
                return self._json(500, {"outcome": "SAVE_FAILED", "error": type(exc).__name__})

    return Handler
