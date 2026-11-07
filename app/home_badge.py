"""Read-only homepage change badge; never computes state or reads history again."""
from __future__ import annotations

import hashlib
import json

from baseline_view import CLUES


def offset_revision(inst, read, timepoints):
    """Opaque waterline for related records, not a clinical result or permission.

    Input is the caller's existing current-ACTIVE observation view and complete
    timepoint metadata. DAY and INSTANT observations match baseline_view; unknown
    time and unrelated codes do not. An append, correction or withdrawal changes
    the relevant reference set. No values, DB reads or rule execution are needed.
    """
    if not inst.sjia or inst.spec.get("kind") != "DEMO":
        return None
    points = [tp for tp in timepoints or [] if tp.get("result")]
    if not points:
        return []
    codes = {code for _, _, group in CLUES for code in group}
    refs = sorted((obs.code, obs.day, obs.ref) for obs in read.observations
                  if obs.code in codes and obs.day is not None
                  and obs.payload.get("status", "ACTIVE") == "ACTIVE")
    runs = sorted((str(tp.get("tp") or ""), str(tp.get("run_id"))) for tp in points)
    scope = [inst.ctx.instance_id, str(inst.ctx.root)]
    raw = json.dumps(["offset-related/1", scope, refs, runs],
                     ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return ["offset:" + hashlib.sha256(raw).hexdigest()]
