"""Shared source-registration writer. Callers retain existing lock ownership.

One owner for the existing temp-file/replace write; no new lock or I/O policy.
"""
import json
import os
from instance_services import SourceReader


class SourceRegistry(SourceReader):
    """Read via SourceReader; atomically publish the existing registration JSON."""

    def update(self, name: str, **fields) -> dict:
        doc = self.read()
        doc[name] = dict(doc.get(name, {}), **fields)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), "utf-8")
        os.replace(tmp, self.path)
        return doc[name]

