"""Versioned UI metadata; no observation, dictionary or rule-engine writes.

Metric codes resolve to semantic regions here. SVG anchors/label coordinates
belong exclusively to the geometry asset. Unknown codes remain unlocated.
"""
from copy import deepcopy
import json
from pathlib import Path


def load() -> dict:
    cfg = json.loads(Path(__file__).with_suffix(".json").read_text(encoding="utf-8"))
    if cfg["version"] != "body-binding/1":
        raise ValueError("Unsupported body binding version")
    for region in cfg["regions"].values():
        if region["scope"] not in ("anatomical", "systemic"):
            raise ValueError("Unknown region scope")
        if region["scope"] == "anatomical" and (not region["anchor_ids"] or not region.get("label_anchor")):
            raise ValueError("Anatomical region needs geometry anchors")
        if region["scope"] == "systemic" and region["anchor_ids"]:
            raise ValueError("Systemic indicators cannot imply organ localization")
    for regions in cfg["metrics"].values():
        if not regions or len(set(regions)) != len(regions) or not set(regions) <= cfg["regions"].keys():
            raise ValueError("Invalid metric regions")
    return cfg


def project(clues: list[dict], dictionary_version: str) -> dict:
    """Enrich only this response's indicators, preserving records and row slots."""
    cfg = load()
    for clue in clues:
        for indicator in clue["indicators"]:
            code = indicator["code"]
            indicator["body_binding"] = {
                "code": code, "dictionary_version": dictionary_version,
                "version": cfg["version"], "region_ids": list(cfg["metrics"].get(code, [])),
            }
    return {k: deepcopy(cfg[k]) for k in ("version", "asset_id", "asset_version", "regions", "meaning")}
