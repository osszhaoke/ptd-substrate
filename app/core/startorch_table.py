"""星炬 side: lab table (CSV) adapter -> ObservationInput rows (reference).

CSV: UTF-8, comma separated, header exactly:
    code,value,unit,comparator,observed_at,observed_date,tz

- value: decimal string (DECIMAL codes) or true/false (BOOLEAN codes)
- unit: a literal from the dictionary (DECIMAL codes); empty for BOOLEAN codes
- comparator: empty or one of < <= > >=
- time: observed_at (instant with offset)  OR  observed_date + tz  OR  all three empty (UNKNOWN)

The adapter only parses and shapes rows; validation happens in build_payload during save_batch,
so a bad row rejects the whole batch at the 核对 step with a row index and an error code.
"""
from __future__ import annotations

import csv
import io

from h1_common import H1Error, InstanceContext, sha256_hex, time_key
from startorch_outbox import ObservationInput

HEADER = ["code", "value", "unit", "comparator", "observed_at", "observed_date", "tz"]


def unique_key_for_lab(code: str, temporal: dict, source_ref: str) -> str:
    """Default recipe for MANUAL / TABLE / TEXT_LLM / SYNTHETIC lab-like observations."""
    return f"LAB|{code}|{time_key(temporal, source_ref)}"


def parse_table(data: bytes, ctx: InstanceContext, *, trust_tier: str = "CLINICAL_LAB", synthetic=None) -> tuple:
    """Returns (batch_id, [ObservationInput]). synthetic=None keeps the old default (DEMO -> SYNTHETIC rows);
    True/False is the nature the person chose for this file (E1: entry method and nature are separate)."""
    file_tag = sha256_hex(data)[:16]
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise H1Error("TABLE_INVALID", "file must be UTF-8") from None
    reader = csv.reader(io.StringIO(text, newline=""))
    rows = list(reader)
    if not rows or rows[0] != HEADER:
        raise H1Error("TABLE_INVALID", "header must be: " + ",".join(HEADER))
    if (ctx.kind == "DEMO") if synthetic is None else synthetic:
        source_kind, trust = "SYNTHETIC", "SYNTHETIC"
    else:
        source_kind, trust = "TABLE", trust_tier
    items = []
    for number, row in enumerate(rows[1:], start=1):
        if not any(cell.strip() for cell in row):
            continue
        if len(row) != len(HEADER):
            raise H1Error("TABLE_INVALID", f"row {number}: expected {len(HEADER)} columns")
        code, value, unit, comparator, observed_at, observed_date, tz = row
        if observed_at and not observed_date and not tz:
            temporal = {"role": "INSTANT", "observed_at": observed_at}
        elif observed_date and tz and not observed_at:
            temporal = {"role": "DAY", "observed_date": observed_date, "tz": tz}
        elif not (observed_at or observed_date or tz):
            temporal = {"role": "UNKNOWN"}
        else:
            raise H1Error("TABLE_INVALID", f"row {number}: give observed_at, or observed_date+tz, or neither")
        source_ref = f"TABLE:{file_tag}#row{number}"
        try:
            unique_key = unique_key_for_lab(code, temporal, source_ref)
        except H1Error as exc:
            raise H1Error(exc.code, f"row {number}: {exc.detail}") from None
        items.append(ObservationInput(
            unique_key=unique_key, code=code, value_raw=value,
            comparator=comparator or None, unit_raw=unit or None, temporal=temporal,
            source_kind=source_kind, source_ref=source_ref, trust_tier=trust))
    return f"TABLE-{file_tag}", items
