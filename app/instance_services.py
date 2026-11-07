"""Instance file readers shared by projections and HTTP-owned writers.

Read-only methods moved verbatim; no server dependency, new I/O or lock policy.
"""
from __future__ import annotations

import json
from pathlib import Path
import gene_db
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from server import Instance


class SourceReader:
    """Read existing source registration; never creates directories or files."""

    def __init__(self, inst: Instance):
        self.path = inst.ctx.root / "startorch" / "sources.json"

    def read(self) -> dict:
        return json.loads(self.path.read_text("utf-8")) if self.path.exists() else {}


def _asset_rows(stream):
    """Project an existing text-line iterator without a second parsing contract."""
    return [{k: rec[k] for k in ("file_name", "received_at", "nature") if k != "nature" or k in rec}
            for line in stream if line.strip() for rec in [json.loads(line)]]


class GeneReader:
    """Read existing gene receipts and their existing point-store statistics."""

    def __init__(self, inst: Instance):
        self.dir = inst.ctx.root / "startorch" / "gene"
        self.ledger = self.dir / "receipts.jsonl"
        self.inst = inst

    @property
    def db_path(self) -> Path:
        return self.dir / "genotypes.db"

    def list(self) -> list:
        if not self.ledger.exists():
            return []
        out = [json.loads(line) for line in self.ledger.read_text("utf-8").splitlines() if line.strip()]
        loaded = {f["file_sha"]: f for f in gene_db.stats(self.db_path).get("by_file", [])}
        for rec in out:
            side = self.dir / (rec["stored_as"] + ".profile.json")
            if not rec.get("profile") and side.exists():
                rec["profile"], rec["profile_added_later"] = json.loads(side.read_text("utf-8")), True
            f = loaded.get(rec["sha256"])
            rec["db_now"] = {"status": "LOADED", "rows": f["rows"], "loaded_at": f["loaded_at"]} if f else None
        return out

    def asset_capture(self, capture):
        """A-owned read delegate: pin or inspect this ledger, never gene points."""
        return capture(self.inst.ctx.root, self.ledger)

    def asset_receipts(self) -> list:
        """List only file-asset labels; no profiles, point-store reads or DDL."""
        if not self.ledger.exists():
            return []
        with self.ledger.open(encoding="utf-8") as stream:
            return _asset_rows(stream)



# G serializes credential persistence with binding changes; A protects host
# identity and Source publication. Network and SecretStore calls never hold A.
import device_targets


def oura_authorize(app, key, variant, client_factory):
    import oura
    with device_targets.binding_gate(app):
        with app.lock:
            if device_targets.configured_key(app, 'oura') is None:
                return None, None
            binding = device_targets.capture_oura(app, key)
            client = device_targets.bound_client(binding, client_factory)
        if not client.configured():
            return client, None
        with app.lock:
            inst = device_targets.validate_oura(app, binding)
            binding = device_targets.capture_oura(app, key, advance=True)
            state, verifier = oura.new_state(), oura.new_verifier()
            app.oauth_states[state] = (binding, verifier)
            link = client.authorize_link(state, verifier, variant)
            app.log('oura_authorize', binding.instance_id, variant or 'default')
            return client, link


def oura_connect(app, state, code, client_factory, sources):
    with app.lock:
        entry = app.oauth_states.pop(state, None)
        if entry is None or code is None:
            return None
        binding, verifier = entry
        inst = device_targets.validate_oura(app, binding)
        client = device_targets.bound_client(binding, client_factory)
    token = client.exchange_token(code, verifier)
    with device_targets.binding_gate(app):
        with app.lock:
            device_targets.validate_oura(app, binding)
        client.save_token(token)
        with app.lock:
            device_targets.validate_oura(app, binding)
            sources(inst).update('oura', status='CONNECTED', connected_at=inst.now(), last_error=None)
            app.log('oura_connected', binding.instance_id)
    return inst


def oura_disconnect(app, inst, client_factory, sources):
    with device_targets.binding_gate(app):
        with app.lock:
            binding = device_targets.capture_oura(app, inst.spec['key'])
            if device_targets.validate_oura(app, binding) is not inst:
                from h1_common import H1Error
                raise H1Error('OURA_AUTHORIZATION_CHANGED', '')
            client = device_targets.bound_client(binding, client_factory)
            device_targets.invalidate_oura(app, inst)
        client.disconnect()
        with app.lock:
            app.log('oura_disconnected', inst.ctx.instance_id)
            result = sources(inst).update('oura', status='DISCONNECTED', disconnected_at=inst.now())
            inst.watch_devices()
            return result


def oura_sources(app, key, client_factory, sources):
    """Metadata GET: credentials outside A; no implicit authorization or sync."""
    with app.lock:
        inst = app.inst(key)
        configured = device_targets.configured_key(app, 'oura') == key
        binding = device_targets.capture_oura(app, key) if configured else None
        client = device_targets.bound_client(binding, client_factory) if configured else None
    missing = client.missing() if client else ['instance_key']
    with app.lock:
        if binding is not None:
            device_targets.validate_oura(app, binding)
        elif app.inst(key) is not inst or device_targets.configured_key(app, 'oura') == key:
            from h1_common import H1Error
            raise H1Error('OURA_AUTHORIZATION_CHANGED', '')
        result = sources(inst).read()
        if app.config.get('band_bridge') is True and key == app.config.get('band_instance_key'):
            result = dict(result)
            result['somaloop'] = dict(result.get('somaloop') or {}, transport='band_bridge')
        return dict(result, oura_configured=not missing, oura_missing=missing)
