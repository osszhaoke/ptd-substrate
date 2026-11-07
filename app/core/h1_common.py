"""H1 contract: 星炬 (StarTorch) -> 星轨 (StarTrack) observation handoff via files.

This file IS the contract. Both repos vendor it byte-for-byte and pin its SHA-256 in a test.
Stdlib only. Floats are rejected on every value path.

Per-instance directory layout (outside both repos):

    <instances_root>/<instance_id>/
        instance.json            written once by init_instance(); read-only afterwards
        startorch/startorch.db   written only by 星炬
        exchange/h1/             written only by 星炬's exporter; read-only for 星轨
        startrack/startrack.db   written only by 星轨
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import (ROUND_HALF_EVEN, Context, Decimal, DivisionByZero, Inexact,
                     InvalidOperation, Overflow, localcontext)
from pathlib import Path
from zoneinfo import ZoneInfo

PAYLOAD_SCHEMA = "h1-obs/0.1"
MANIFEST_SCHEMA = "h1-manifest/0.2"
INSTANCE_SCHEMA = "ptds-instance/0.1"
DICTIONARY_SCHEMA = "h1-dictionary/0.1"

# version -> SHA-256 of the exact dictionary file bytes. Editing the file without updating this
# pin (and re-pinning this file in both repos) makes load_dictionary() fail.
DICTIONARY_PINS = {
    "0.15": "aa5f1ce93d3b9ce506414243dc54c7cc10406e1f10579022824b9c0d408981c4", # QKeer raw semantics daily extension

    "0.13": "a4e1524e50183d12692d09e32ae72c1f7b9a55847b80d98ca9e331e985f8f906", # PPI RMSSD window-day summaries
    "0.12": "398dba34264211d9f65d611df073ed34837c5f51682270204b0d0c3345e7a086", # native device day summaries
    "0.11": "3288d9b2c9771cb5555e291b718da5cd79fea87293fa016af8b7cca61877acf7", # additive sampled-day statistics
    "0.10": "cd46465c359bfa98e69d0b702a70c19471689eca7d1642d2deffd6889e973749", # Somaloop Agent additive local projection

    "0.9": "ed868635bc618429cd32c0a560dec83e120ba8584a1d0d033501679bf29cd15f",  # Garmin additive local extension, 2026-10-18
    "0.1": "8796767e230fc5705b78956d715832cff607872e67ddeb2c2ef427a202dc4ce8",
    "0.2": "a5065678740cd91f1203a276dee1e57cbca4af5ab606772993883687a31da3c1",  # PTDS-local, app/tools/make_dictionary_02.py
    "0.3": "ec625fec12f6f0134ec4eb5151e52074b9bf8990907aa113ecbfbd75a8eeee9a",  # PTDS-local, app/tools/make_dictionary_03.py
    "0.4": "8db5edc8c0829f29fe36895f5fc87f02a6240b8a85de98a2c94ea52aca4c2f4e",  # PTDS-local, app/tools/make_dictionary_04.py
    "0.5": "bfb7e9d02855ccc9ec8ea09dae4c0fa790b887033e2f60833f9de621624b758e",  # PTDS-local, app/tools/make_dictionary_05.py
    "0.6": "efba54192b5f35e7bb24d99583deefa6f9039e89a927e358f4f6371144c440e4",  # PTDS-local, app/tools/make_dictionary_06.py
    "0.7": "659a8d243b6a2c2cc005c1a3e1b46242fa6c62f95173217a1b3bb557c9fd06e0",  # PTDS-local, app/tools/make_dictionary_07.py
    "0.8": "f979de62222c1bc54d63c877ddf494beebc1cb617fe4e29c73fd7890a7e90362",  # PTDS-local, app/tools/make_dictionary_08.py
}

INSTANCE_KINDS = ("DEMO", "REAL")
STATUSES = ("ACTIVE", "RETRACTED")
VALUE_TYPES = ("DECIMAL", "BOOLEAN")
COMPARATORS = ("<", "<=", ">", ">=")
BOOLEAN_VALUES = ("true", "false")
TEMPORAL_ROLES = ("INSTANT", "DAY", "UNKNOWN")
SOURCE_KINDS = ("MANUAL", "TABLE", "TEXT_LLM", "OCR_LLM", "DEVICE_OURA", "DEVICE_SOMALOOP", "DEVICE_QKEER",
                "APPLE_HEALTH", "SYNTHETIC", "DEVICE_WITHINGS", "DEVICE_CGM", "DEVICE_GARMIN")
# PTDS-local 0.2: nature is derived from source_kind (SYNTHETIC -> SYNTHETIC, everything else -> REAL);
# which natures an instance accepts comes from instance.json data_policy, never from its kind (HR-06).
NATURES = ("SYNTHETIC", "REAL")
TRUST_TIERS = ("CLINICAL_LAB", "DEVICE_CONSUMER", "SELF_REPORT", "SYNTHETIC")
CODE_FAMILIES = ("LAB", "VITAL", "FLAG", "DEVICE_OURA", "DEVICE_SOMALOOP", "DEVICE_QKEER", "PHONE_HEALTH",
                 "DEVICE_WITHINGS", "DEVICE_CGM", "DEVICE_GARMIN")  # 后两个是 R20 批量入库（Withings 导出、连续血糖仪导出的表格）

ALLOWED_TRUST = {
    "DEVICE_GARMIN": ("DEVICE_CONSUMER",),
    "MANUAL": ("CLINICAL_LAB", "SELF_REPORT"),
    "TABLE": ("CLINICAL_LAB", "SELF_REPORT"),
    "TEXT_LLM": ("CLINICAL_LAB", "SELF_REPORT"),
    "OCR_LLM": ("CLINICAL_LAB", "SELF_REPORT"),
    "DEVICE_OURA": ("DEVICE_CONSUMER",),
    "DEVICE_SOMALOOP": ("DEVICE_CONSUMER",),
    "DEVICE_QKEER": ("DEVICE_CONSUMER",),
    "APPLE_HEALTH": ("DEVICE_CONSUMER", "SELF_REPORT"),
    "SYNTHETIC": ("SYNTHETIC",),
    "DEVICE_WITHINGS": ("DEVICE_CONSUMER",),
    "DEVICE_CGM": ("DEVICE_CONSUMER",),
}
# Which code families each source kind may carry. A wearable can never produce TEMP or FEVER.
ALLOWED_FAMILIES = {
    "DEVICE_GARMIN": ("DEVICE_GARMIN",),
    "MANUAL": ("LAB", "VITAL", "FLAG"),
    "TABLE": ("LAB", "VITAL", "FLAG"),
    "TEXT_LLM": ("LAB", "VITAL", "FLAG"),
    "OCR_LLM": ("LAB", "VITAL", "FLAG"),
    "DEVICE_OURA": ("DEVICE_OURA",),
    "DEVICE_SOMALOOP": ("DEVICE_SOMALOOP",),
    "DEVICE_QKEER": ("DEVICE_QKEER",),
    "APPLE_HEALTH": ("PHONE_HEALTH",),
    "SYNTHETIC": CODE_FAMILIES,
    "DEVICE_WITHINGS": ("DEVICE_WITHINGS",),
    "DEVICE_CGM": ("DEVICE_CGM",),
}

PAYLOAD_KEYS = frozenset((
    "schema", "instance_id", "observation_id", "revision", "status", "code", "dictionary_version",
    "value_type", "value_raw", "comparator", "unit_raw", "value_canonical", "unit_canonical",
    "conversion_rule", "temporal", "source_kind", "source_ref", "trust_tier", "batch_id",
    "request_id", "saved_at", "content_digest",
))
# A new revision is created only when these fields change (content_digest covers exactly these).
# source_ref is deliberately NOT included: re-importing the same value from another file is not
# a change; the pointer keeps the source of the revision that introduced the value.
SEMANTIC_KEYS = (
    "status", "code", "value_type", "value_raw", "comparator", "unit_raw", "value_canonical",
    "unit_canonical", "conversion_rule", "temporal", "source_kind", "trust_tier",
)
# One manifest = exactly one 星炬 save commit (all-or-nothing on both sides).
MANIFEST_KEYS = frozenset((
    "schema", "payload_schema", "instance_id", "commit_id", "seq_from", "seq_to", "count", "file",
    "file_sha256",
))
LINE_KEYS = frozenset(("seq", "payload", "payload_sha256"))

INSTANCE_ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{2,39}")
OBSERVATION_ID_RE = re.compile(r"OBS-[0-9a-f]{32}")
CODE_RE = re.compile(r"[A-Z][A-Z0-9_]{1,39}")
VERSION_RE = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")
DECIMAL_RE = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
# Offset hours 00-14, minutes 00-59; "-00:00" (RFC 3339 "unknown offset") is rejected in parse_instant.
INSTANT_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3}|\.\d{6})?[+-](?:0\d|1[0-4]):[0-5]\d")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
MANIFEST_NAME_RE = re.compile(r"h1-c(\d{12})(?:\.r([1-9][0-9]{0,2}))?\.manifest\.json")
MAX_VALUE_CHARS = 32
MAX_TEXT_CHARS = 512
MAX_INT = 2**31 - 1  # revision / commit_id / seq upper bound: never reaches SQLite as an overflow

# One arithmetic context for every computation. 50 significant digits is far above any input
# (value_raw <= 32 chars); exact operations additionally trap Inexact so nothing rounds silently.
DECIMAL_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN,
                          traps=[InvalidOperation, DivisionByZero, Overflow])


class H1Error(Exception):
    """Every contract failure carries a stable code. Details never contain health values."""

    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


# ----------------------------------------------------------------------------- canonical forms

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _check_json_types(obj, path: str = "$") -> None:
    if obj is None or isinstance(obj, (str, bool)):
        return
    if isinstance(obj, float):
        raise TypeError(f"float not allowed at {path}")
    if isinstance(obj, int):
        return
    if isinstance(obj, list):
        for i, item in enumerate(obj):
            _check_json_types(item, f"{path}[{i}]")
        return
    if isinstance(obj, dict):
        for key, item in obj.items():
            if not isinstance(key, str):
                raise TypeError(f"non-string key at {path}")
            _check_json_types(item, f"{path}.{key}")
        return
    raise TypeError(f"{type(obj).__name__} not allowed at {path}")


def canonical_json(obj) -> str:
    """Sorted keys, no whitespace, UTF-8 text kept as is, no NaN, no floats."""
    _check_json_types(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def canonical_bytes(obj) -> bytes:
    return canonical_json(obj).encode("utf-8")


def _unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key")
        out[key] = value
    return out


def _no_float(text):
    raise ValueError("JSON numbers with a fraction or exponent are not allowed")


def _no_constant(text):
    raise ValueError("NaN/Infinity are not allowed")


def strict_loads(text: str):
    """json.loads that rejects duplicate keys, floats, NaN and Infinity (raises ValueError)."""
    return json.loads(text, object_pairs_hook=_unique_pairs, parse_float=_no_float,
                      parse_constant=_no_constant)


# ----------------------------------------------------------------------------- decimals & time

def parse_decimal(text) -> Decimal:
    if not isinstance(text, str) or len(text) > MAX_VALUE_CHARS or not DECIMAL_RE.fullmatch(text):
        raise H1Error("VALUE_INVALID", "decimal string expected")
    return Decimal(text)


def canonical_decimal(value: Decimal) -> str:
    """Shortest plain form: no exponent, no trailing zeros, '-0' -> '0'. Never rounds."""
    if not isinstance(value, Decimal) or not value.is_finite():
        raise H1Error("VALUE_INVALID", "finite Decimal expected")
    with localcontext(DECIMAL_CONTEXT) as ctx:
        ctx.traps[Inexact] = True
        text = format(value.normalize(), "f")
    return "0" if text == "-0" else text


def parse_instant(text) -> datetime:
    if not isinstance(text, str) or not INSTANT_RE.fullmatch(text) or text.endswith("-00:00"):
        raise H1Error("TEMPORAL_INVALID", "instant must be YYYY-MM-DDTHH:MM:SS[.fff|.ffffff]+HH:MM")
    try:
        value = datetime.fromisoformat(text)
    except ValueError:
        raise H1Error("TEMPORAL_INVALID", "instant is not a valid date-time") from None
    if abs(value.utcoffset().total_seconds()) > 14 * 3600:
        raise H1Error("TEMPORAL_INVALID", "offset out of range")
    return value


def parse_date(text) -> date:
    if not isinstance(text, str) or not DATE_RE.fullmatch(text):
        raise H1Error("TEMPORAL_INVALID", "date must be YYYY-MM-DD")
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise H1Error("TEMPORAL_INVALID", "date is not valid") from None


def check_tz(name) -> ZoneInfo:
    if not isinstance(name, str) or not 1 <= len(name) <= 64:
        raise H1Error("TZ_INVALID", "IANA time zone name required")
    try:
        return ZoneInfo(name)
    except (KeyError, ValueError, OSError):
        raise H1Error("TZ_INVALID", "unknown IANA time zone") from None


def local_day(instant: datetime, tz: str) -> date:
    return instant.astimezone(check_tz(tz)).date()


def time_key(temporal: dict, source_ref: str) -> str:
    """Default time component of a unique_key (see spec 4.2): one instant = one key."""
    role = temporal.get("role")
    if role == "INSTANT":
        utc = parse_instant(temporal["observed_at"]).astimezone(timezone.utc)
        return utc.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    if role == "DAY":
        return "DAY:" + parse_date(temporal["observed_date"]).isoformat()
    if role == "UNKNOWN":
        return "UNKNOWN:" + source_ref
    raise H1Error("TEMPORAL_INVALID", "unknown temporal role")


# ----------------------------------------------------------------------------- conversions

def apply_rule(rule: str, value: Decimal) -> Decimal:
    """Registered conversions. SCALE is exact (Inexact trapped); F_TO_C quantizes to 0.0001 half-even."""
    if not isinstance(rule, str):
        raise H1Error("CONVERSION_RULE_UNKNOWN", "rule must be a string")
    with localcontext(DECIMAL_CONTEXT) as ctx:
        if rule == "IDENTITY":
            return value
        if rule.startswith("SCALE:"):
            factor = parse_decimal(rule[len("SCALE:"):])
            ctx.traps[Inexact] = True
            return value * factor
        if rule == "F_TO_C:Q4":
            return ((value - 32) * 5 / 9).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
        if rule == "IFCC_TO_NGSP:Q2":  # 糖化血红蛋白 mmol/mol → %：NGSP = 0.09148 × IFCC + 2.152（IFCC–NGSP 主方程）
            return (value * Decimal("0.09148") + Decimal("2.152")).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
    raise H1Error("CONVERSION_RULE_UNKNOWN", rule)


# ----------------------------------------------------------------------------- dictionary

@dataclass(frozen=True)
class CodeDef:
    code: str
    label_zh: str
    family: str
    value_type: str
    unit_canonical: str | None
    comparators_allowed: bool
    units: tuple  # ((unit literal, rule), ...)

    def rule_for(self, unit_raw) -> str:
        for literal, rule in self.units:
            if unit_raw == literal:
                return rule
        raise H1Error("UNIT_UNSUPPORTED", f"code={self.code} unit not in dictionary")


@dataclass(frozen=True, eq=False)
class Dictionary:
    version: str
    sha256: str
    codes: dict  # code -> CodeDef


def _version_key(version: str) -> tuple:
    return tuple(int(part) for part in version.split("."))


def _parse_dictionary(raw: bytes, file_sha: str) -> Dictionary:
    try:
        doc = strict_loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise H1Error("DICTIONARY_INVALID", "not strict JSON") from None
    if not isinstance(doc, dict) or set(doc) != {"schema", "version", "status", "note_zh", "codes"}:
        raise H1Error("DICTIONARY_INVALID", "top-level keys")
    if doc["schema"] != DICTIONARY_SCHEMA or not isinstance(doc["version"], str) \
            or not VERSION_RE.fullmatch(doc["version"]):
        raise H1Error("DICTIONARY_INVALID", "schema/version")
    codes = {}
    if not isinstance(doc["codes"], dict) or not doc["codes"]:
        raise H1Error("DICTIONARY_INVALID", "codes")
    for code, c in doc["codes"].items():
        keys = {"label_zh", "family", "value_type", "unit_canonical", "comparators_allowed", "units"}
        if not CODE_RE.fullmatch(code) or not isinstance(c, dict) or set(c) != keys:
            raise H1Error("DICTIONARY_INVALID", f"code {code}")
        if c["family"] not in CODE_FAMILIES or c["value_type"] not in VALUE_TYPES \
                or not isinstance(c["label_zh"], str) or not isinstance(c["comparators_allowed"], bool) \
                or not isinstance(c["units"], dict):
            raise H1Error("DICTIONARY_INVALID", f"code {code}")
        if c["value_type"] == "DECIMAL":
            if c["units"].get(c["unit_canonical"]) != "IDENTITY":
                raise H1Error("DICTIONARY_INVALID", f"code {code}: canonical unit must map to IDENTITY")
            for literal, rule in c["units"].items():
                if not isinstance(literal, str) or not literal:
                    raise H1Error("DICTIONARY_INVALID", f"code {code}: unit literal")
                apply_rule(rule, Decimal("1"))  # raises CONVERSION_RULE_UNKNOWN
        elif c["unit_canonical"] is not None or c["units"] or c["comparators_allowed"]:
            raise H1Error("DICTIONARY_INVALID", f"code {code}: boolean codes carry no unit/comparator")
        codes[code] = CodeDef(code, c["label_zh"], c["family"], c["value_type"], c["unit_canonical"],
                              c["comparators_allowed"], tuple(c["units"].items()))
    return Dictionary(doc["version"], file_sha, codes)


def load_dictionary(path: Path, pins: dict = DICTIONARY_PINS) -> Dictionary:
    raw = Path(path).read_bytes()
    file_sha = sha256_hex(raw)
    dictionary = _parse_dictionary(raw, file_sha)
    if pins.get(dictionary.version) != file_sha:
        raise H1Error("DICTIONARY_PIN_MISMATCH", f"version {dictionary.version}")
    return dictionary


class DictionaryRegistry:
    """All dictionary versions a component knows. Newer versions may only ADD codes or unit literals."""

    def __init__(self, dictionaries):
        ordered = sorted(dictionaries, key=lambda d: _version_key(d.version))
        if not ordered or len({d.version for d in ordered}) != len(ordered):
            raise H1Error("DICTIONARY_INVALID", "empty or duplicate versions")
        for older, newer in zip(ordered, ordered[1:]):
            for code, old in older.codes.items():
                new = newer.codes.get(code)
                same = new is not None and (old.family, old.value_type, old.unit_canonical,
                                            old.comparators_allowed) == (new.family, new.value_type,
                                                                         new.unit_canonical,
                                                                         new.comparators_allowed)
                if not same or not set(old.units) <= set(new.units):
                    raise H1Error("DICTIONARY_INCOMPATIBLE", f"{older.version}->{newer.version} code {code}")
        self._by_version = {d.version: d for d in ordered}
        self.current = ordered[-1]

    @property
    def versions(self) -> tuple:
        return tuple(self._by_version)

    def get(self, version) -> Dictionary:
        if not isinstance(version, str) or version not in self._by_version:
            raise H1Error("DICTIONARY_VERSION_UNKNOWN", "dictionary version not known here")
        return self._by_version[version]


# ----------------------------------------------------------------------------- instance

@dataclass(frozen=True)
class InstanceContext:
    root: Path
    instance_id: str
    kind: str
    tz: str
    display_name: str
    accept: tuple = NATURES  # data_policy.accept from instance.json; default: both natures (HR-06)

    @property
    def startorch_db(self) -> Path:
        return self.root / "startorch" / "startorch.db"

    @property
    def exchange_dir(self) -> Path:
        return self.root / "exchange" / "h1"

    @property
    def startrack_db(self) -> Path:
        return self.root / "startrack" / "startrack.db"


def _check_text(value, field: str, max_chars: int = MAX_TEXT_CHARS) -> None:
    if not isinstance(value, str) or not 1 <= len(value) <= max_chars or any(ord(ch) < 32 for ch in value):
        raise H1Error("TEXT_INVALID", field)


def nature_of(source_kind: str) -> str:
    return "SYNTHETIC" if source_kind == "SYNTHETIC" else "REAL"


def _check_policy(policy) -> tuple:
    if not isinstance(policy, dict) or set(policy) != {"accept"} or not isinstance(policy["accept"], list) \
            or not policy["accept"] or not set(policy["accept"]) <= set(NATURES) \
            or len(set(policy["accept"])) != len(policy["accept"]):
        raise H1Error("INSTANCE_INVALID", "data_policy")
    return tuple(n for n in NATURES if n in policy["accept"])


def init_instance(instances_root: Path, instance_id: str, kind: str, tz: str, display_name: str,
                  created_at: str, data_policy: dict | None = None) -> InstanceContext:
    """Creates the directory layout and writes instance.json exactly once (mode 'xb')."""
    if not isinstance(instance_id, str) or not INSTANCE_ID_RE.fullmatch(instance_id):
        raise H1Error("INSTANCE_ID_INVALID", "lowercase letters, digits, '-'; 3-40 chars")
    if kind not in INSTANCE_KINDS:
        raise H1Error("INSTANCE_KIND_INVALID", "DEMO or REAL")
    check_tz(tz)
    _check_text(display_name, "display_name", 64)
    parse_instant(created_at)
    root = Path(instances_root) / instance_id
    try:
        root.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        raise H1Error("INSTANCE_EXISTS", instance_id) from None
    (root / "startorch").mkdir()
    (root / "exchange" / "h1").mkdir(parents=True)
    (root / "startrack").mkdir()
    doc = {"schema": INSTANCE_SCHEMA, "instance_id": instance_id, "kind": kind, "tz": tz,
           "display_name": display_name, "created_at": created_at}
    if data_policy is not None:
        _check_policy(data_policy)
        doc["data_policy"] = data_policy
    # Publish the instance description only after both new stores are initialized.
    # A partial creation is never a license to recreate a missing store on a request.
    from cards import open_startrack
    from startorch_outbox import open_startorch
    ctx = InstanceContext(root, instance_id, kind, tz, display_name,
                          _check_policy(data_policy) if data_policy is not None else NATURES)
    for initialize in (open_startorch, open_startrack):
        initialize(ctx, create=True).close()
    with open(root / "instance.json", "xb") as handle:
        handle.write(canonical_bytes(doc) + b"\n")
    return load_instance(root)


def load_instance(root: Path) -> InstanceContext:
    root = Path(root)
    try:
        doc = strict_loads((root / "instance.json").read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise H1Error("INSTANCE_INVALID", "instance.json missing or not strict JSON") from None
    keys = {"schema", "instance_id", "kind", "tz", "display_name", "created_at"}
    if not isinstance(doc, dict) or set(doc) - {"data_policy"} != keys or doc["schema"] != INSTANCE_SCHEMA:
        raise H1Error("INSTANCE_INVALID", "instance.json shape")
    if not isinstance(doc["instance_id"], str) or not INSTANCE_ID_RE.fullmatch(doc["instance_id"]) \
            or doc["kind"] not in INSTANCE_KINDS:
        raise H1Error("INSTANCE_INVALID", "id/kind")
    if root.name != doc["instance_id"]:
        raise H1Error("INSTANCE_DIR_MISMATCH", "directory name must equal instance_id")
    check_tz(doc["tz"])
    _check_text(doc["display_name"], "display_name", 64)
    parse_instant(doc["created_at"])
    accept = _check_policy(doc["data_policy"]) if "data_policy" in doc else NATURES
    return InstanceContext(root, doc["instance_id"], doc["kind"], doc["tz"], doc["display_name"], accept)


# ----------------------------------------------------------------------------- payload

def make_observation_id(instance_id: str, unique_key: str) -> str:
    _check_text(unique_key, "unique_key")
    return "OBS-" + sha256_hex(canonical_bytes({"instance_id": instance_id, "unique_key": unique_key}))[:32]


def content_digest(payload: dict) -> str:
    return sha256_hex(canonical_bytes({key: payload[key] for key in SEMANTIC_KEYS}))


def _validate_temporal(temporal) -> None:
    if not isinstance(temporal, dict):
        raise H1Error("TEMPORAL_INVALID", "object required")
    role = temporal.get("role")
    if role == "INSTANT" and set(temporal) == {"role", "observed_at"}:
        parse_instant(temporal["observed_at"])
    elif role == "DAY" and set(temporal) == {"role", "observed_date", "tz"}:
        parse_date(temporal["observed_date"])
        check_tz(temporal["tz"])
    elif not (role == "UNKNOWN" and set(temporal) == {"role"}):
        raise H1Error("TEMPORAL_INVALID", "shape does not match role")


def validate_payload(p, registry: DictionaryRegistry, ctx: InstanceContext) -> None:
    """Closed-world validation shared by both sides. Raises H1Error with a stable code."""
    if not isinstance(p, dict) or set(p) != PAYLOAD_KEYS:
        raise H1Error("PAYLOAD_KEYS", "payload keys must equal the contract key set")
    if p["schema"] != PAYLOAD_SCHEMA:
        raise H1Error("PAYLOAD_SCHEMA_MISMATCH", "unexpected payload schema")
    if p["instance_id"] != ctx.instance_id:
        raise H1Error("INSTANCE_MISMATCH", "payload instance differs from this instance")
    if not isinstance(p["observation_id"], str) or not OBSERVATION_ID_RE.fullmatch(p["observation_id"]):
        raise H1Error("OBSERVATION_ID_INVALID", "")
    if type(p["revision"]) is not int or not 1 <= p["revision"] <= MAX_INT:
        raise H1Error("REVISION_INVALID", "")
    if p["status"] not in STATUSES:
        raise H1Error("STATUS_INVALID", "")
    dictionary = registry.get(p["dictionary_version"])
    cdef = dictionary.codes.get(p["code"]) if isinstance(p["code"], str) else None
    if cdef is None:
        raise H1Error("CODE_UNKNOWN", "code not in dictionary")
    if p["value_type"] != cdef.value_type:
        raise H1Error("VALUE_TYPE_MISMATCH", f"code={cdef.code}")
    if cdef.value_type == "DECIMAL":
        value = parse_decimal(p["value_raw"])
        if p["comparator"] is not None:
            if p["comparator"] not in COMPARATORS:
                raise H1Error("COMPARATOR_INVALID", f"code={cdef.code}")
            if not cdef.comparators_allowed:
                raise H1Error("COMPARATOR_NOT_ALLOWED", f"code={cdef.code}")
        rule = cdef.rule_for(p["unit_raw"])
        if p["conversion_rule"] != rule:
            raise H1Error("CONVERSION_RULE_MISMATCH", f"code={cdef.code}")
        if p["unit_canonical"] != cdef.unit_canonical:
            raise H1Error("UNIT_CANONICAL_MISMATCH", f"code={cdef.code}")
        if p["value_canonical"] != canonical_decimal(apply_rule(rule, value)):
            raise H1Error("CONVERSION_MISMATCH", f"code={cdef.code} rule={rule}")
    else:
        if p["value_raw"] not in BOOLEAN_VALUES:
            raise H1Error("VALUE_INVALID", f"code={cdef.code} expects 'true' or 'false'")
        if (p["comparator"], p["unit_raw"], p["unit_canonical"], p["conversion_rule"]) != (None, None, None, "IDENTITY") \
                or p["value_canonical"] != p["value_raw"]:
            raise H1Error("BOOLEAN_SHAPE_INVALID", f"code={cdef.code}")
    _validate_temporal(p["temporal"])
    source_kind, trust_tier = p["source_kind"], p["trust_tier"]
    if source_kind not in SOURCE_KINDS:
        raise H1Error("SOURCE_KIND_INVALID", "")
    if trust_tier not in ALLOWED_TRUST[source_kind]:
        raise H1Error("TRUST_TIER_INVALID", f"source_kind={source_kind}")
    if cdef.family not in ALLOWED_FAMILIES[source_kind]:
        raise H1Error("SOURCE_CODE_MISMATCH", f"source_kind={source_kind} code={cdef.code}")
    nature = nature_of(source_kind)
    if nature not in ctx.accept:
        raise H1Error("NON_SYNTHETIC_IN_DEMO" if nature == "REAL" else "SYNTHETIC_IN_REAL",
                      "instance data_policy does not accept " + nature)
    for field in ("source_ref", "batch_id", "request_id"):
        _check_text(p[field], field)
    parse_instant(p["saved_at"])
    if p["content_digest"] != content_digest(p):
        raise H1Error("CONTENT_DIGEST_MISMATCH", "")


def build_payload(registry: DictionaryRegistry, ctx: InstanceContext, *, observation_id: str,
                  revision: int, status: str, code: str, value_raw: str, comparator, unit_raw,
                  temporal: dict, source_kind: str, source_ref: str, trust_tier: str,
                  batch_id: str, request_id: str, saved_at: str) -> dict:
    """Builds a payload under the CURRENT dictionary and validates it before returning."""
    dictionary = registry.current
    cdef = dictionary.codes.get(code) if isinstance(code, str) else None
    if cdef is None:
        raise H1Error("CODE_UNKNOWN", "code not in dictionary")
    if cdef.value_type == "DECIMAL":
        rule = cdef.rule_for(unit_raw)
        value_canonical = canonical_decimal(apply_rule(rule, parse_decimal(value_raw)))
        unit_canonical = cdef.unit_canonical
    else:
        rule, value_canonical, unit_canonical = "IDENTITY", value_raw, None
    payload = {
        "schema": PAYLOAD_SCHEMA, "instance_id": ctx.instance_id, "observation_id": observation_id,
        "revision": revision, "status": status, "code": code, "dictionary_version": dictionary.version,
        "value_type": cdef.value_type, "value_raw": value_raw, "comparator": comparator,
        "unit_raw": unit_raw, "value_canonical": value_canonical, "unit_canonical": unit_canonical,
        "conversion_rule": rule, "temporal": temporal, "source_kind": source_kind,
        "source_ref": source_ref, "trust_tier": trust_tier, "batch_id": batch_id,
        "request_id": request_id, "saved_at": saved_at,
    }
    payload["content_digest"] = content_digest(payload)
    validate_payload(payload, registry, ctx)
    return payload


# ----------------------------------------------------------------------------- export files

def data_file_name(commit_id: int, repair: int = 0) -> str:
    return f"h1-c{commit_id:012d}" + (f".r{repair}" if repair else "") + ".jsonl"


def manifest_file_name(commit_id: int, repair: int = 0) -> str:
    return f"h1-c{commit_id:012d}" + (f".r{repair}" if repair else "") + ".manifest.json"


def encode_export(instance_id: str, commit_id: int, rows, repair: int = 0) -> tuple:
    """rows: [(seq, payload_canonical_json_text, payload_sha256)] of ONE commit, ascending and contiguous.

    Returns (data_name, data_bytes, manifest_name, manifest_bytes). Pure and deterministic. A repair
    copy (repair >= 1) differs from the base copy only in its file names.
    """
    if not rows or not 1 <= commit_id <= MAX_INT:
        raise H1Error("EXPORT_EMPTY", "")
    lines = []
    for index, (seq, payload_text, payload_sha) in enumerate(rows):
        if seq != rows[0][0] + index:
            raise H1Error("OUTBOX_SEQ_GAP", f"seq {seq}")
        if sha256_hex(payload_text.encode("utf-8")) != payload_sha:
            raise H1Error("OUTBOX_DIGEST_MISMATCH", f"seq {seq}")
        payload = strict_loads(payload_text)
        if canonical_json(payload) != payload_text:
            raise H1Error("OUTBOX_NOT_CANONICAL", f"seq {seq}")
        lines.append(canonical_json({"seq": seq, "payload": payload, "payload_sha256": payload_sha}) + "\n")
    data = "".join(lines).encode("utf-8")
    seq_from, seq_to = rows[0][0], rows[-1][0]
    manifest = {"schema": MANIFEST_SCHEMA, "payload_schema": PAYLOAD_SCHEMA, "instance_id": instance_id,
                "commit_id": commit_id, "seq_from": seq_from, "seq_to": seq_to, "count": len(rows),
                "file": data_file_name(commit_id, repair), "file_sha256": sha256_hex(data)}
    return (data_file_name(commit_id, repair), data, manifest_file_name(commit_id, repair),
            canonical_bytes(manifest) + b"\n")
