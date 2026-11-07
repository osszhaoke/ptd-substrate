"""Typed, instance-local evidence destinations and registered original resolution.

Descriptors are navigation hints, never authorization. Callers bind the selected
instance and retain their existing request guards. No absolute path is accepted
from a browser; file paths come only from the instance's saved metadata.
"""
from __future__ import annotations

from contextlib import closing
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from h1_common import H1Error
from startorch_outbox import open_startorch

MAX_METADATA = 2 * 1024 * 1024
MAX_RECORDS = 4096
_HASH = re.compile(r"[0-9a-f]{16}\Z")
_NAME = re.compile(r"[0-9a-f]{16}\.(?:png|jpg|jpeg|heic|pdf|tif|tiff|webp|bin)\Z")
DEVICES = {"DEVICE_OURA": "oura", "DEVICE_GARMIN": "garmin", "DEVICE_SOMALOOP": "somaloop",
           "DEVICE_QKEER": "qkeer", "DEVICE_WITHINGS": "withings", "DEVICE_CGM": "dexcom"}


def destination(node: dict) -> dict:
    """Map an existing graph entity to an internal target without reading data."""
    kind, nid = node.get("kind"), str(node.get("id") or "")
    out = {"kind": kind or "unavailable", "label": "查看详情", "available": True}
    if kind == "indicator" and nid.startswith("code:"):
        out.update(kind="data_metric", label="查看该指标的数据", code=nid[5:],
                   sources=list(node.get("sources") or []))
    elif kind == "observation" and node.get("observation_id"):
        out.update(label="查看这版数据", observation_id=node["observation_id"], revision=node.get("revision"))
    elif kind == "card" and nid.startswith("card:"):
        out.update(label="打开状态卡", card_id=node.get("card_id") or nid[5:])
        if node.get("wall_id"):
            out["wall_id"] = node["wall_id"]
        if node.get("revision") is not None:
            out["revision"] = node["revision"]
    elif kind == "conclusion" and node.get("run_id") and node.get("card") and node.get("tp"):
        out.update(kind="trace", label="查看这次计算", card_id=node["card"], tp=node["tp"], run_id=node["run_id"])
    elif kind == "document" and nid.startswith(("doc:", "gene:")):
        out.update(label="查看原件", document_id=nid)
    elif kind == "source" and nid.startswith("src:"):
        source = nid[4:]
        out.update(label="查看接入详情" if source in DEVICES else "查看来源记录", source_kind=source)
        if source in DEVICES:
            out["device"] = DEVICES[source]
    elif kind == "alert" and nid.startswith("alert:"):
        out.update(label="查看这条通知", dedupe_key=nid[6:], card_id=node.get("card"), tp=node.get("tp"))
    elif kind == "channel" and nid.startswith("chan:"):
        out.update(label="查看送达记录", channel=nid[5:])
    elif kind == "grant" and nid.startswith("grant:"):
        out.update(label="查看授权记录", grant_id=nid[6:])
    elif kind == "party" and nid.startswith("party:"):
        out.update(label="查看关联授权", object_id=nid[6:])
    elif kind == "store" and nid == "store:gene":
        out.update(label="打开基因位点库", store="gene")
    else:
        out.update(available=False, reason="此节点尚无可定位的内容")
    return out


def _fail(code: str, detail: str):
    raise H1Error(code, detail)


def _basename(value) -> str:
    if (not isinstance(value, str) or not value or len(value) > 240 or value in (".", "..")
            or any(c in value for c in ("/", "\\", "\x00")) or any(ord(c) < 32 for c in value)):
        _fail("ORIGINAL_PATH_INVALID", "原件登记路径无效")
    return value


def _checked(inst, relative: Path, *, allow_link=False) -> Path:
    """Check each instance-relative component, including dangling symlinks."""
    root = Path(inst.ctx.root)
    if relative.is_absolute() or ".." in relative.parts:
        _fail("ORIGINAL_PATH_INVALID", "原件路径越界")
    # macOS /var itself is a system link. Trust resolved ancestors of the configured
    # instance root, but reject a linked instance root or any component below it.
    if root.is_symlink():
        _fail("ORIGINAL_PATH_INVALID", "实例目录不能是符号链接")
    root = root.resolve()
    target = root
    try:
        for part in relative.parts:
            target = target / part
            if stat.S_ISLNK(target.lstat().st_mode):
                _fail("ORIGINAL_PATH_INVALID", "原件不能经过符号链接")
        info = target.stat()
    except FileNotFoundError:
        _fail("ORIGINAL_NOT_FOUND", "PTDS 保存的原件副本已不存在")
    except OSError:
        _fail("ORIGINAL_PATH_INVALID", "原件路径无法安全读取")
    if not target.resolve().is_relative_to(root) or not stat.S_ISREG(info.st_mode):
        _fail("ORIGINAL_PATH_INVALID", "原件不是实例内的普通文件")
    if info.st_nlink != 1 and not allow_link:
        _fail("ORIGINAL_LINK_UNSAFE", "原件包含未核验的硬链接")
    return target


def _json(inst, relative: Path) -> dict:
    path = _checked(inst, relative)
    if path.stat().st_size > MAX_METADATA:
        _fail("ORIGINAL_METADATA_LIMIT", "原件登记超出读取范围")
    try:
        value = json.loads(path.read_text("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("object")
        return value
    except (ValueError, UnicodeError):
        _fail("ORIGINAL_METADATA_INVALID", "原件登记无法读取")


def _metadata_files(inst, relative: Path, pattern: str):
    folder = Path(inst.ctx.root) / relative
    # Validate directories independently so a glob never follows a substituted dir.
    base = Path(inst.ctx.root)
    for part in relative.parts:
        base = base / part
        if base.is_symlink():
            _fail("ORIGINAL_PATH_INVALID", "原件登记目录不能是符号链接")
    if not folder.exists():
        return []
    paths = []
    for path in folder.glob(pattern):
        paths.append(relative / path.name)
        if len(paths) > MAX_RECORDS:
            _fail("ORIGINAL_METADATA_LIMIT", "原件登记过多，请缩小范围")
    return sorted(paths)


def _batch_matches(inst, short: str):
    matches = []
    for path in _metadata_files(inst, Path("startorch/batch/items"), "*.json"):
        item = _json(inst, path)
        sha = item.get("sha") or ""
        if isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{64}", sha) and sha.startswith(short):
            matches.append(item)
    return matches


def _original_record(inst, short: str) -> tuple[dict, Path]:
    candidates = _metadata_files(inst, Path("startorch/originals"), short + "*.recognition.json")
    records = []
    for rel in candidates:
        if not re.fullmatch(short + r"(?:\.p[1-9][0-9]*)?\.recognition\.json", rel.name):
            continue
        rec = _json(inst, rel)
        name = _basename(rec.get("original"))
        if not _NAME.fullmatch(name) or name[:16] != short:
            _fail("ORIGINAL_METADATA_INVALID", "原件登记与文档标识不一致")
        sha = rec.get("sha256") or ""
        if not re.fullmatch(r"[0-9a-f]{64}", str(sha)) or not sha.startswith(short):
            _fail("ORIGINAL_METADATA_INVALID", "原件登记缺少一致的指纹")
        records.append((rec, Path("startorch/originals") / name))
    if not records:
        _fail("ORIGINAL_NOT_FOUND", "没有找到该文档已保存的原件登记")
    if len({str(path) for _, path in records}) != 1 or len({rec["sha256"] for rec, _ in records}) != 1:
        _fail("ORIGINAL_AMBIGUOUS", "该文档关联了多个原件，不能自动选择")
    return records[0]


def _gene_record(inst, receipt_id: str) -> dict:
    ledger = _checked(inst, Path("startorch/gene/receipts.jsonl"))
    # Stream the receipt ledger; never instantiate GeneStore or load genetic data.
    with ledger.open(encoding="utf-8") as handle:
        total = 0
        for index, line in enumerate(handle):
            total += len(line.encode("utf-8"))
            if index >= MAX_RECORDS or total > 16 * MAX_METADATA:
                _fail("ORIGINAL_METADATA_LIMIT", "原件回执超出读取范围")
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                _fail("ORIGINAL_METADATA_INVALID", "原件回执无法读取")
            if rec.get("receipt_id") == receipt_id:
                return rec
    _fail("ORIGINAL_NOT_FOUND", "当前实例没有这份基因文件回执")


def _registered(inst, document_id: str) -> tuple[Path, dict]:
    if not isinstance(document_id, str) or len(document_id) > 160:
        _fail("DOCUMENT_ID_INVALID", "文档标识无效")
    m = re.fullmatch(r"doc:(OCR|TABLE|FILE):([0-9a-f]{16})", document_id)
    if m:
        kind, short = m.groups()
        if kind == "OCR":
            rec, rel = _original_record(inst, short)
            return rel, {"kind": kind, "name": rec.get("name") or rel.name, "sha256": rec["sha256"]}
        matches = _batch_matches(inst, short)
        if not matches:
            _fail("ORIGINAL_NOT_FOUND", "这次导入未保留可定位的原件副本")
        files = {(x["sha"], _basename(x.get("file"))) for x in matches}
        if len(files) != 1:
            _fail("ORIGINAL_AMBIGUOUS", "该文档关联了多个原件，不能自动选择")
        sha, name = next(iter(files))
        if not re.fullmatch(re.escape(short) + r"[.a-z0-9]{0,8}", name):
            _fail("ORIGINAL_METADATA_INVALID", "保存文件与批次指纹不一致")
        return Path("startorch/batch/files") / name, {"kind": kind, "name": matches[0].get("name") or name, "sha256": sha}
    m = re.fullmatch(r"gene:(G-[A-Za-z0-9_-]{1,100})", document_id)
    if m:
        rec = _gene_record(inst, m.group(1))
        sha, name = str(rec.get("sha256") or ""), _basename(rec.get("stored_as"))
        if not re.fullmatch(r"[0-9a-f]{64}", sha) or not name.startswith(sha[:16] + "_"):
            _fail("ORIGINAL_METADATA_INVALID", "保存文件与基因回执指纹不一致")
        return Path("startorch/gene") / name, {"kind": "GENE", "name": rec.get("file_name"), "sha256": sha}
    if re.fullmatch(r"doc:TABLE:[A-Za-z0-9_.-]{1,100}", document_id):
        _fail("ORIGINAL_NOT_FOUND", "旧导入记录没有可核验的原件文件映射")
    _fail("DOCUMENT_ID_INVALID", "此节点没有已登记的原件标识")


def resolve_original(inst, document_id: str) -> Path:
    rel, meta = _registered(inst, document_id)
    return _resolve_registered(inst, rel, meta)


def _resolve_registered(inst, rel: Path, meta: dict) -> Path:
    return _registered_file(inst, rel, meta)[0]


def _registered_file(inst, rel, meta):
    path = _checked(inst, rel, allow_link=True)
    info = path.stat()
    if info.st_nlink != 1:
        # Existing OCR imports deliberately link these two registered copies.
        # Admit exactly that pair; any third/outside hard link stays rejected.
        if info.st_nlink != 2 or meta["kind"] != "OCR":
            _fail("ORIGINAL_LINK_UNSAFE", "原件包含未核验的硬链接")
        paired = False
        for item in _batch_matches(inst, meta["sha256"][:16]):
            if item["sha"] != meta["sha256"]:
                continue
            other = _checked(inst, Path("startorch/batch/files") / _basename(item.get("file")), allow_link=True)
            pair = other.stat()
            if (pair.st_dev, pair.st_ino) == (info.st_dev, info.st_ino) and other != path:
                paired = True
                break
        if not paired:
            _fail("ORIGINAL_LINK_UNSAFE", "原件硬链接缺少同实例保存记录")
    return path, info


def resolve_original_name(inst, name: str) -> Path:
    """Legacy OCR GET name adapter; retains names but shares registration checks."""
    return original_reference(inst, name)[0]


def original_reference(inst, name):
    """A caller may pin the registered digest as well as the verified path."""
    if not isinstance(name, str) or not _NAME.fullmatch(name):
        _fail("DOCUMENT_ID_INVALID", "原件名称无效")
    rel, meta = _registered(inst, "doc:OCR:" + name[:16])
    path, info = _registered_file(inst, rel, meta)
    if path.name != name:
        _fail("ORIGINAL_NOT_FOUND", "原件名称与保存记录不一致")
    return path, meta["sha256"], info


def document(inst, document_id: str) -> dict:
    """UI metadata with an explicit unavailable reason; never expose local paths."""
    try:
        rel, meta = _registered(inst, document_id)
        path = _resolve_registered(inst, rel, meta)
        return {"document_id": document_id, "found": True, "name": meta.get("name") or path.name,
                "kind": meta["kind"], "bytes": path.stat().st_size, "saved_copy": True,
                "reveal_local_only": True}
    except H1Error as exc:
        return {"document_id": document_id, "found": False, "error": exc.code, "reason": exc.detail}


def reveal(inst, document_id: str, *, local_allowed=False, runner=None) -> dict:
    """Native local action; HTTP caller must establish Host/Origin/loopback guard."""
    if local_allowed is not True:
        _fail("LOCAL_CONTROL_REQUIRED", "仅可在这台 Mac 上显示原件")
    if runner is None and sys.platform != "darwin":
        _fail("ORIGINAL_REVEAL_UNSUPPORTED", "仅 macOS 支持在访达中显示原件")
    path = resolve_original(inst, document_id)
    try:
        (runner or subprocess.run)(["/usr/bin/open", "-R", str(path)], check=True,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, timeout=5)
    except (OSError, subprocess.SubprocessError):
        _fail("ORIGINAL_REVEAL_FAILED", "无法在访达中显示原件，请重试")
    return {"ok": True, "document_id": document_id, "saved_copy": True}


def observation(inst, observation_id: str, revision=None) -> dict:
    """Fetch exactly one formal version and latest metadata, never a timeline."""
    if not isinstance(observation_id, str) or not observation_id or len(observation_id) > 160:
        _fail("OBSERVATION_ID_INVALID", "数据标识无效")
    if revision not in (None, ""):
        if isinstance(revision, bool) or not re.fullmatch(r"[1-9][0-9]{0,9}", str(revision)):
            _fail("OBSERVATION_REVISION_INVALID", "数据版本无效")
        revision = int(revision)
    else:
        revision = None
    with closing(open_startorch(inst.ctx)) as torch:
        latest = torch.execute("SELECT revision,payload,saved_at FROM formal_observation WHERE observation_id=? "
                               "ORDER BY revision DESC LIMIT 1", (observation_id,)).fetchone()
        row = latest if revision is None or (latest and latest[0] == revision) else torch.execute(
            "SELECT revision,payload,saved_at FROM formal_observation WHERE observation_id=? AND revision=?",
            (observation_id, revision)).fetchone()
    if not row:
        return {"found": False, "observation_id": observation_id, "revision": revision,
                "reason": "当前实例中没有这条数据的指定版本"}
    payload, current = json.loads(row[1]), json.loads(latest[1])
    from evidence_graph import _origin
    return {"found": True, "observation_id": observation_id, "revision": row[0], "payload": payload,
            "saved_at": row[2], "latest_revision": latest[0], "latest_status": current.get("status"),
            "superseded": row[0] != latest[0], "origin": _origin(inst, payload.get("source_ref") or ""),
            "destination": destination({"kind": "observation", "observation_id": observation_id, "revision": row[0]})}
