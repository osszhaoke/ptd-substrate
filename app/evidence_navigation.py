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


def batch_page_matches(page_doc, whole, page):
    """Prove a historical batch page is a contiguous projection of this original."""
    batch = page_doc.get("batch")
    if not isinstance(batch, dict) or batch.get("page") != page or not batch.get("id"):
        return False
    if any(whole.get(k) != page_doc.get(k) for k in ("sha256", "original", "nature")):
        return False
    rows = page_doc.get("rows")
    lines = page_doc.get("source_lines")
    original = whole.get("source_lines")
    if not all(isinstance(v, list) for v in (rows, lines, original)) or not rows or not lines:
        return False
    wanted = [r for r in whole.get("rows", []) if r.get("page") == page]
    # A legacy parser may have interpreted spellings which the new strict
    # reader leaves unmatched. Such rows never enter the new review. Establish
    # the page offset solely from independently recognised physical rows.
    page_rows = {}
    prefix = "OCR:" + whole["sha256"][:16] + "#p" + str(page) + "l"
    for item in rows:
        if not isinstance(item, dict) or item.get("page") != page:
            return False
        n, box = item.get("line"), item.get("box")
        if type(n) is not int or not 1 <= n <= len(lines) or item.get("ref") != prefix + str(n):
            return False
        if not isinstance(box, list) or len(box) != 4 or not all(type(x) in (float, int) for x in box):
            return False
        position = tuple(box)
        if position in page_rows:
            return False
        page_rows[position] = item
    delta = None
    for reference in wanted:
        item = page_rows.get(tuple(reference.get("box") or ()))
        if item is None or any(item.get(k) != reference.get(k) for k in ("code", "value", "unit", "cmp", "text", "abn", "ref_range")):
            return False
        absolute = reference.get("line")
        if type(absolute) is not int or reference.get("ref") != prefix + str(absolute):
            return False
        offset = absolute - item["line"]
        if offset < 0 or (delta is not None and delta != offset):
            return False
        delta = offset
    if delta is None:
        return False
    return original[delta:delta + len(lines)] == lines


def ocr_page_matches(page_record, record, page):
    """Compare the exact page and line selectors used by the evidence graph."""
    if not isinstance(page_record, dict) or any(
        page_record.get(key) != record.get(key) for key in ("sha256", "original", "nature")
    ):
        return False
    canonical = record.get("rows", [])
    if not isinstance(canonical, list) or not all(isinstance(r, dict) and type(r.get("page")) is int and type(r.get("line")) is int for r in canonical):
        return False
    if not isinstance(record.get("source_lines"), list):
        return False
    rows = page_record.get("rows")
    lines = page_record.get("source_lines")
    if not isinstance(rows, list) or not isinstance(lines, list):
        return False
    expected = [row for row in canonical if row["page"] == page]
    page_count = record.get("pages", max((row["page"] for row in canonical), default=1))
    if type(page_count) is not int or not 1 <= page <= page_count:
        return False
    # Older individual-page sidecars can include batch information and a different
    # display filename. Their references must still address the same original line.
    actual = [row for row in rows if isinstance(row, dict) and row.get("page") == page]
    if rows != actual and rows != canonical:
        return False
    if expected != actual:
        # The old batch parser numbers each separately processed page from one.
        # Preserve that file and its old refs when the full source and geometry prove the offset.
        return batch_page_matches(page_record, record, page)
    source = record["source_lines"]
    if lines != source:
        # On one page the complete original text has just one valid projection.
        # For a multipage legacy file, the graph still indexes by absolute line
        # number; every supplied line must be the canonical line at that index.
        if page_count == 1 or not lines or lines != source[:len(lines)]:
            return False
    if any(not 1 <= row["line"] <= len(lines) for row in expected):
        return False
    return True


OCR_COLUMN_ROLES = {
    "项目": "name", "指标": "name", "test": "name", "analyte": "name",
    "结果": "result", "检验结果": "result", "检测结果": "result", "测定结果": "result",
    "result": "result", "results": "result", "单位": "unit", "unit": "unit", "units": "unit",
    "参考区间": "reference", "参考范围": "reference", "参考值": "reference",
    "referencerange": "reference", "referenceinterval": "reference",
    "提示": "flag", "标志": "flag", "flag": "flag",
}
OCR_RESULT_LITERAL = re.compile(r"(<=|>=|≤|≥|＜|＞|〈|〉|<|>)?\s*(-?[0-9]+(?:\.[0-9]+)?)")


def _printed_flag_positions(parts, positions, abnormal):
    """An absent abnormality code carries no evidence that the printed flag was empty.

    Vision can omit a cell which crosses a column edge. Including every possible
    width lets the rest of the row prove a result position independently.
    """
    if not abnormal:
        possible = set(positions)  # An empty flag consumes no printed segment.
        possible.update(range(min(positions) + 1, len(parts) + 1))
        return possible
    marks = {"H":"H", "↑":"H", "偏高":"H", "L":"L", "↓":"L", "偏低":"L"}
    possible = {i + 1 for i in positions if i < len(parts) and marks.get(parts[i]) == abnormal}
    return possible


def _numbered_name_forms(tokens, intrinsic):
    """Read at most one printed row number, only inside the metric-name field."""
    from recognize import SEQ_RE, norm_name
    raw = norm_name(" ".join(tokens))
    if not raw or not raw[0].isdigit() or intrinsic(raw):
        return {raw}
    first, *tail = tokens
    if tail and re.fullmatch(r"\d{1,2}", first.strip()):
        return {raw, norm_name(" ".join(tail))}
    unnumbered = SEQ_RE.sub("", first.strip())
    return {raw, norm_name(" ".join([unnumbered, *tail]))}


def _protected_numbered_names(dictionary_codes):
    """The versioned dictionary is already in memory. Build this only for a numbered name."""
    from recognize import ALIASES, norm_name
    labels = [s for group in ALIASES.values() for s in group if s and s[0].isdigit()]
    for code, definition in dictionary_codes.items():
        labels.extend(s for s in (code, definition.label_zh) if s and s[0].isdigit())
    return {norm_name(s) for s in labels}


def _column_offsets(roles, cells, row, batch_page, names, intrinsic, backwards=False):
    """Possible field boundaries on one side of a printed result. Never consult its value."""
    from recognize import norm_name
    import unicodedata
    order, parts = (roles[::-1], cells[::-1]) if backwards else (roles, cells)
    size = len(parts)
    positions = {0}
    for role in order:
        if not positions:
            break
        if role is None or (role == "reference" and not row.get("ref_range")):
            # Neither the text nor its number of Vision segments was recorded.
            positions = set(range(min(positions), size + 1))
            continue
        if role == "flag":
            positions = _printed_flag_positions(parts, positions, row.get("abn"))
            continue
        if role == "unit":
            unit = str(row.get("unit") or "")
            if batch_page:
                unit = unicodedata.normalize("NFKC", unit)
            possible = set()
            for start in positions:
                if start >= size:
                    continue
                text = unicodedata.normalize("NFKC", parts[start]) if batch_page else parts[start]
                if batch_page and re.fullmatch(r"10~[0-9]+/L", text):
                    text = text.replace("~", "^")
                if text == unit:
                    possible.add(start + 1)
            positions = possible
            continue
        reference = row.get("ref_range")
        normalize = norm_name if role == "name" else lambda text: " ".join(text.split())
        expected = names if role == "name" else {normalize(reference)} if isinstance(reference, str) else set()
        possible = set()
        for start in positions:
            tokens = []
            for index in range(start, size):
                tokens.append(parts[index])
                ordered = tokens[::-1] if backwards else tokens
                forms = _numbered_name_forms(ordered, intrinsic) if role == "name" else {normalize(" ".join(ordered))}
                if forms & expected:
                    possible.add(index + 1)
                if role == "name" and not backwards and len(tokens) == 1 and re.fullmatch(r"\d{1,2}", tokens[0]):
                    continue  # With a following segment this token can be a printed ordinal.
                if not any(label.endswith(part) if backwards else label.startswith(part) for label in expected for part in forms):
                    break
        positions = possible
    return positions


def _source_line_agrees(lines, number, row, batch_page=False, metric_label=None, dictionary_codes=None):
    """A displayed source must support its identified result, including its qualifier."""
    from recognize import ALIASES, CMP, HEADER_NAMES, norm_name
    import unicodedata
    protected = None
    def intrinsic(name):
        nonlocal protected
        if protected is None:
            protected = _protected_numbered_names(dictionary_codes or {})
        return name in protected
    raw = lines[number-1]
    expected = (row.get("cmp") or "", str(row.get("value")))
    def numeric(cell):
        match = OCR_RESULT_LITERAL.fullmatch(cell.strip())
        return (CMP.get(match[1], ""), match[2]) if match else None
    # Tabular metadata stores literal Vision segments. Use the most recent
    # named headers and never use a matching number from a reference column.
    if "\t" in raw:
        cells = [cell.strip() for cell in raw.split("\t")]
        roles = []
        for index in range(number-2, -1, -1):
            heading = lines[index]
            if not isinstance(heading, str):
                return False
            labels = ["".join(label.lower().split()) for label in heading.split("\t")]
            fields = ["name" if label in HEADER_NAMES else OCR_COLUMN_ROLES.get(label) for label in labels]
            if not any(fields):
                continue
            if any(fields.count(required) != 1 for required in ("name","result","unit")):
                return False
            # Each later optional header of the same kind replaces its predecessor in _column_cells.
            roles = [None if role in ("flag", "reference") and role in fields[i+1:] else role
                     for i, role in enumerate(fields)]
            break
        if not roles:
            return False
        # Vision does not serialize an empty box into the tab-separated text.
        # Locate the result by independently proving the roles on either side.
        # The recorded value plays no part in choosing which field is the result.
        cells = [cell for cell in cells if cell]
        pos = roles.index("result")
        code = row.get("code")
        if not isinstance(code, str) or not code:
            return False
        names = {norm_name(name) for name in (code, metric_label, *ALIASES.get(code, ())) if isinstance(name, str) and name}
        # row.text is the first printed segment; it may be a fragment of a
        # longer name or belong to another column. Only code-bound names count.
        names.discard("")
        starts = _column_offsets(roles[:pos], cells, row, batch_page, names, intrinsic)
        tails = _column_offsets(roles[pos+1:], cells, row, batch_page, names, intrinsic, backwards=True)
        by_position = {}
        for start in sorted(starts):
            if start >= len(cells):
                continue
            index = start
            joined = cells[start]
            if joined in CMP and start + 1 < len(cells):
                index += 1
                joined += cells[index]
            parsed = numeric(joined)
            if parsed is not None and len(cells)-index-1 in tails:
                # A free-standing comparison sign and its number are one result.
                # Prefer that full literal over the same number without its sign.
                by_position.setdefault(index, parsed)
        matches = list(by_position.values())
        if len(matches) != 1:
            return False
        return matches[0] == expected
    # Old text-only evidence has no columns. Require a single complete
    # numeric token and reject multiple possibilities and separated qualifiers.
    if re.search(r"参考|对照|(?i:\breference\b|\brange\b)", raw):
        return False
    tokens = raw.split()
    values = []
    for i, token in enumerate(tokens):
        parsed = numeric(token)
        if parsed is None:
            continue
        start = i
        if i and tokens[i-1] in CMP and not parsed[0]:
            parsed = (CMP[tokens[i-1]], parsed[1])
            start -= 1
        code = row.get("code")
        if not isinstance(code, str):
            return False
        labels = {norm_name(x) for x in (row.get("text"), code, metric_label, *ALIASES.get(code, ())) if isinstance(x, str) and x}
        tail = " ".join(tokens[i+1:])
        last = norm_name(tokens[start-1]) if start else ""
        if not start or (tail and tail != row.get("unit")):
            continue
        prefix = tokens[:start]
        if not (_numbered_name_forms(prefix, intrinsic) & labels):
            # Preserve old text-only rows carrying an unnumbered source prefix.
            # Unmatched digits in a prefix are never discarded to find a result.
            if last not in labels or any(t[:1].isdigit() for t in prefix):
                continue
        values.append(parsed)
    return values == [expected]



def _stored_segment_agrees(raw, row, metric_label=None):
    """row.text records the first segment after strip_seq, even when it is a flag or unit."""
    if "text" not in row:
        return True  # Older records without a segment still require the separate source checks.
    saved = row["text"]
    if not isinstance(saved, str):
        return False
    from recognize import ALIASES, norm_name, strip_seq
    parts = raw.split("\t")
    printed = strip_seq(parts)
    if printed and printed[0] == saved:
        return True
    if len(parts) == 1:
        # Legacy flat text may spell the entire metric with its registered alias.
        # A suffix match could instead identify a different metric (e.g. HSCRP).
        code = row.get("code")
        if not isinstance(code, str):
            return False
        spellings = [code, *ALIASES.get(code, ())]
        if metric_label:
            spellings.append(metric_label)
        names = {norm_name(spelling) for spelling in spellings}
        if norm_name(saved) not in names:
            return False
        words = printed[0].split()
        for index, word in enumerate(words):
            if OCR_RESULT_LITERAL.fullmatch(word):
                from recognize import CMP
                edge = index - 1 if index > 0 and words[index - 1] in CMP else index
                return norm_name(" ".join(words[:edge])) in names
        return False
    if "\t" not in saved:
        return False
    # Vision can emit a tab *inside* a single recognised phrase. Rejoin exactly
    # the recorded number of tabs, with and without a leading sequence field.
    width = saved.count("\t") + 1
    for offset in (0, 1):
        if offset + width > len(parts):
            continue
        candidate = parts[:offset] + ["\t".join(parts[offset:offset+width])] + parts[offset+width:]
        first = strip_seq(candidate)
        if first and first[0] == saved:
            return True
    return False


def ocr_line(inst, short, page, number, observation=None, unique_key=None):
    """Resolve the exact formal record; whole-document and batch line numbers can overlap."""
    folder = Path("startorch/originals")
    ref = f"OCR:{short}#p{page}l{number}"
    records = {}
    for owner, suffix in (("page", f".p{page}.recognition.json"), ("whole", ".recognition.json")):
        try:
            records[owner] = _json(inst, folder / (short + suffix))
        except H1Error as exc:
            if exc.code != "ORIGINAL_NOT_FOUND":
                raise
    if not records:
        _fail("ORIGINAL_NOT_FOUND", "没有找到该文档已保存的原件登记")
    hashes = [d.get("sha256") for d in records.values()]
    if any(not isinstance(h, str) or not re.fullmatch(r"[0-9a-f]{64}", h) or h[:16] != short for h in hashes) or len(set(hashes)) != 1:
        _fail("ORIGINAL_AMBIGUOUS", "该文档关联了多个原件，不能自动选择")
    if "page" in records and "whole" in records and not ocr_page_matches(records["page"], records["whole"], page):
        _fail("ORIGINAL_AMBIGUOUS", "原件的分页与整件记录不一致")
    candidates = []
    sha = next(iter(records.values())).get("sha256")
    whole_key = f"OCR|{sha}|p{page}l{number}"
    if isinstance(unique_key, str) and unique_key.startswith("OCR|") and unique_key != whole_key:
        _fail("ORIGINAL_AMBIGUOUS", "无法唯一定位这条数据的原文")
    requires_whole = unique_key == whole_key
    for owner, doc in records.items():
        if requires_whole and owner != "whole":
            continue
        lines = doc.get("source_lines")
        if not isinstance(lines, list) or not 1 <= number <= len(lines) or not isinstance(lines[number-1], str) or not lines[number-1].strip():
            continue
        rows = doc.get("rows")
        if not isinstance(rows, list):
            # A legacy unstructured sidecar is usable only for an unambiguous direct lookup.
            if observation is None and len(records) == 1:
                candidates.append((None, lines[number-1], doc))
            continue
        for row in rows:
            if not isinstance(row, dict) or (row.get("ref"), row.get("page"), row.get("line")) != (ref, page, number):
                continue
            if observation:
                if row.get("code") != observation.get("code") or (row.get("unit") or "") != (observation.get("unit_raw") or ""):
                    continue
                if observation.get("revision", 1) == 1 and (
                    str(row.get("value")) != str(observation.get("value_raw")) or
                    (row.get("cmp") or "") != (observation.get("comparator") or "")
                ):
                    continue
            box = row.get("box")
            if not isinstance(box, list) or len(box) != 4 or not all(type(x) in (int,float) for x in box):
                continue
            registry = getattr(getattr(inst, "app", None), "registry", None)
            definition = None
            dictionary = None
            if registry is not None and isinstance(row.get("code"), str):
                version = (observation or {}).get("dictionary_version")
                dictionary = registry.get(version) if version else registry.current
                definition = dictionary.codes.get(row.get("code"))
            caption = getattr(definition, "label_zh", None)
            if not _stored_segment_agrees(lines[number-1], row, caption):
                _fail("ORIGINAL_AMBIGUOUS", "原件的识别记录与原文不一致")
            if not _source_line_agrees(lines, number, row, bool(doc.get("batch")), caption, dictionary.codes if dictionary else None):
                _fail("ORIGINAL_AMBIGUOUS", "原件的识别记录与原文不一致")
            identity = (tuple(box), row.get("code"), row.get("value"), row.get("unit"), row.get("cmp"))
            candidates.append((identity, lines[number-1], doc))
    if not candidates:
        _fail("ORIGINAL_NOT_FOUND", "无法定位这条数据的原文")
    identity, text, chosen = candidates[0]
    if any((key, raw) != (identity, text) for key, raw, _ in candidates[1:]):
        _fail("ORIGINAL_AMBIGUOUS", "无法唯一定位这条数据的原文")
    return chosen, text


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
        latest = torch.execute("SELECT revision,payload,saved_at,unique_key FROM formal_observation WHERE observation_id=? "
                               "ORDER BY revision DESC LIMIT 1", (observation_id,)).fetchone()
        row = latest if revision is None or (latest and latest[0] == revision) else torch.execute(
            "SELECT revision,payload,saved_at,unique_key FROM formal_observation WHERE observation_id=? AND revision=?",
            (observation_id, revision)).fetchone()
    if not row:
        return {"found": False, "observation_id": observation_id, "revision": revision,
                "reason": "当前实例中没有这条数据的指定版本"}
    payload, current = json.loads(row[1]), json.loads(latest[1])
    from evidence_graph import _origin
    return {"found": True, "observation_id": observation_id, "revision": row[0], "payload": payload,
            "saved_at": row[2], "latest_revision": latest[0], "latest_status": current.get("status"),
            "superseded": row[0] != latest[0], "origin": _origin(inst, payload.get("source_ref") or "", payload, row[3]),
            "destination": destination({"kind": "observation", "observation_id": observation_id, "revision": row[0]})}
