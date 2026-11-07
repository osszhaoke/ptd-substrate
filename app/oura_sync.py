"""Oura pull orchestration. Dependencies are supplied by the host; no server import.

The per-instance guard serializes pulls. Network calls run outside the global
write lock; status and formal admission retain their existing lock boundary.
"""
from datetime import timedelta
from zoneinfo import ZoneInfo
import threading
import json
import uuid
import oura
import oura_raw
from h1_common import H1Error

_OURA_PULL_LOCKS = {}
_OURA_PULL_GUARD = threading.Lock()


def pull_guard(inst):
    """The single nonblocking pull/erasure lock for this host instance."""
    with _OURA_PULL_GUARD:
        return _OURA_PULL_LOCKS.setdefault((id(inst.app), inst.spec["key"]), threading.Lock())


def pull(inst, lock=None, *, pull_once) -> dict:
    guard = pull_guard(inst)
    if not guard.acquire(blocking=False):
        return {"ok": True, "status": "already_running"}
    try:
        from oura_raw_upgrade import ownership
        with ownership(getattr(inst.ctx, 'root', None), guard):
            if getattr(inst.ctx, 'root', None) is not None:
                import oura_erase
                try:
                    oura_erase.resume_pending(inst)
                except Exception as exc:
                    code = exc.code if isinstance(exc, H1Error) else 'OURA_ERASE_RESUME_FAILED'
                    raise H1Error(code, '') from None
            return pull_once(inst, lock=lock)
    finally:
        guard.release()


# Process-wide bounded staging owner; never wait while holding A or U.
STAGING_BYTES = 64 * 1024 * 1024
_STAGING_OWNER = threading.Lock()


class _Pages:
    """Request-owned bytes only; Recorder remains the sole persistent owner."""
    def __init__(self, limit):
        self.limit, self.used, self.pages = limit, 0, []
        self.failure, self.overflow = None, False

    def charge(self, amount):
        if self.used + amount > self.limit:
            self.failure, self.overflow = 'OURA_RAW_WRITE_FAILED', True
            self.assert_ok()
        self.used += amount

    def assert_ok(self):
        if self.failure:
            raise H1Error(self.failure, '')

    def on_page(self, collection, params, raw, status, requested_at, error_code=None, *, secrets=()):
        if collection == 'heartrate':
            return
        self.assert_ok()
        try:
            if collection not in oura_raw.COLLECTIONS or set(params) - {'start_date', 'end_date', 'start_datetime', 'end_datetime', 'next_token'}:
                raise H1Error('OURA_RAW_REQUEST_INVALID', '')
            encoded = oura_raw._json(params)
            if any(secret and secret.encode() in (raw or b'') + encoded for secret in secrets):
                raise H1Error('OURA_RAW_CREDENTIAL_ECHO', '')
            decode_error = False
            try:
                payload = json.loads(raw) if raw else {}
                oura_raw._no_credentials(payload, secrets)
                oura_raw._no_credentials(params, secrets)
                data = payload.get('data') or []
                if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
                    raise ValueError('shape')
            except (ValueError, AttributeError):
                decode_error = True
            # Conservative retained-byte accounting includes metadata and token
            # references. Parsed observations/HTTP transient allocations are not
            # claimed to fit this raw-response staging quota.
            metadata = oura_raw._json([collection, params, status, requested_at, error_code, list(secrets)])
            self.charge(len(raw or b'') + len(metadata))
            self.pages.append((collection, json.loads(encoded), raw, status, requested_at, error_code, tuple(secrets)))
            if decode_error:
                raise H1Error('OURA_RAW_RESPONSE_INVALID', '')
        except Exception as exc:
            self.failure = exc.code if isinstance(exc, H1Error) else 'OURA_RAW_WRITE_FAILED'
            raise H1Error(self.failure, '') from None

    def replay(self, recorder):
        for collection, params, raw, status, requested_at, error_code, secrets in self.pages:
            recorder.on_page(collection, params, raw, status, requested_at, error_code, secrets=secrets)
        self.assert_ok()

    def clear(self):
        self.pages.clear()
        self.used = 0


class _TokenStage:
    """Refresh tokens stay private until the same binding is ready to commit."""
    def __init__(self, store, account, pages):
        self.store, self.account, self.pages, self.pending = store, account, pages, None

    def get(self, account):
        return self.pending if account == self.account and self.pending is not None else self.store.get(account)

    def put(self, account, value):
        if account != self.account:
            raise H1Error('OURA_AUTHORIZATION_CHANGED', '')
        self.pages.charge(len(value.encode()) - len((self.pending or '').encode()))
        self.pending = value

    def commit(self):
        if self.pending is not None:
            self.store.put(self.account, self.pending)


def pull_once(inst, lock=None, *, sources, client_factory, clock, save) -> dict:
    """Fetch outside A; validate one binding before any new pull publication."""
    import device_targets
    held = lock if lock is not None else inst.app.lock
    if not _STAGING_OWNER.acquire(blocking=False):
        return {'ok': True, 'status': 'already_running'}
    client = staged_token = None
    pages = _Pages(STAGING_BYTES)
    try:
        with held:
            binding = device_targets.capture_oura(inst.app, inst.spec['key'])
            if binding.instance is not inst:
                raise H1Error('OURA_AUTHORIZATION_CHANGED', '')
            src = sources(inst)
            state = src.read().get('oura', {})
            policy = dict(inst.app.daily_policy(inst.spec['key']))
            client = device_targets.bound_client(binding, client_factory)
        today = clock.now(ZoneInfo(inst.ctx.tz)).date()
        last = state.get('last_pull_day')
        since = (clock.fromisoformat(last).date() - timedelta(days=2)) if last else today - timedelta(days=oura.HISTORY_DAYS)
        if state.get('fields', 1) < oura.FIELDS_VERSION:
            since = min(since, today - timedelta(days=oura.BACKFILL_DAYS))
        if policy['enabled']:
            daily_last = state.get('daily_through')
            since = (clock.fromisoformat(daily_last).date() - timedelta(days=2)) if daily_last else clock.fromisoformat(policy['cutover_day']).date()
        if isinstance(client, oura.OuraClient):
            staged_token = _TokenStage(client.store, binding.instance_id, pages)
            client.store, client.recorder = staged_token, pages
        got = error = None
        try:
            if policy['enabled']:
                got = oura.pull_daily(client, inst.ctx.tz, since=since, until=today,
                                     cutover_day=policy['cutover_day'], summaries=state.get('daily_scanned_on') != today.isoformat())
            else:
                got = oura.pull(client, inst.ctx.tz, since=since, until=today)
            pages.assert_ok()
        except Exception as exc:
            error = exc
        # G owns the commit interval. Runtime authorization/disconnection also
        # acquire G before A. Startup configuration is not hot-mutated.
        with device_targets.binding_gate(inst.app):
            with held:
                device_targets.validate_oura(inst.app, binding)
            record, receipts = None, []
            try:
                if not pages.overflow and staged_token is not None:
                    staged_token.commit()  # SecretStore I/O outside A.
                    record = oura_raw.Recorder(inst.ctx.root, binding.instance_id,
                                               'daily' if policy['enabled'] else 'legacy', since, today)
                    if record:
                        pages.replay(record)
                if error is not None:
                    raise error
                if record:
                    record.assert_ok()
                    if policy['enabled']:
                        record.prepare(got, inst.ctx.tz)
                        got['_raw_receipts'] = receipts
                with held:
                    device_targets.validate_oura(inst.app, binding)
                    disconnected = src.read().get('oura', {}).get('status') != 'CONNECTED'
                    result = ({'state': src.read().get('oura', {}), 'sync': None} if disconnected else save(inst, src, got, today))
                if record:
                    for receipt in receipts:
                        record.link(receipt)
                    record.finish('DISCONNECTED' if disconnected else 'OK')
                    record = None
                return result
            except Exception as exc:
                code = exc.code if isinstance(exc, H1Error) else 'OURA_UNREACHABLE'
                if record:
                    try:
                        record.finish('ERROR', code)
                    except Exception:
                        code = 'OURA_RAW_FINALIZE_FAILED'
                with held:
                    device_targets.validate_oura(inst.app, binding)
                    updates = {'last_error': {'code': code, 'at': inst.now()},
                               'status': 'NEEDS_REAUTH' if code in ('OURA_UNAUTHORIZED', 'OURA_NOT_CONNECTED') else src.read().get('oura', {}).get('status')}
                    if receipts:
                        updates.update(daily_scanned_on=state.get('daily_scanned_on'), daily_through=state.get('daily_through'))
                    src.update('oura', **updates)
                    inst.app.log('oura_pull_failed', binding.instance_id, code)
                if isinstance(exc, H1Error) and exc.code == code:
                    raise
                raise H1Error(code, type(exc).__name__) from None
    finally:
        if staged_token is not None:
            client.store = staged_token.store
            staged_token.pending = None
        if isinstance(client, oura.OuraClient):
            client.recorder = None
        pages.clear()
        _STAGING_OWNER.release()


def save(inst, src, got: dict, today) -> dict:
    if inst.app.daily_policy(inst.spec["key"])["enabled"]:
        import device_daily
        for item in got.get("latest", []):
            device_daily.cache_latest(inst, "DEVICE_OURA", item["code"], item["value_raw"],
                                      item["unit_raw"], item["observed_at"], device_key="oura-account")
        days, counts = {}, {}
        cutoff = inst.app.daily_policy(inst.spec["key"])["cutover_day"]
        for item in got["items"]:
            day = item.temporal.get("observed_date", "")
            if item.temporal.get("role") != "DAY" or not cutoff <= day < today.isoformat():
                raise H1Error("DEVICE_DAILY_DAY_INVALID", "")
            days.setdefault(day, []).append({"code": item.code, "value_raw": item.value_raw, "unit_raw": item.unit_raw})
        for day, items in sorted(days.items()):
            receipt = device_daily.admit(inst, {"schema": "ptds-device-day/1", "key": inst.spec["key"],
                "source_kind": "DEVICE_OURA", "day": day, "timezone": inst.ctx.tz,
                "device_key": "oura-account", "method": "vendor_daily", "items": items,
                "quality": {"coverage": "vendor_reported", "raw_points_retained": False, "provider_summary": True}})
            if "_raw_receipts" in got:
                got["_raw_receipts"].append(receipt)
            for outcome, count in receipt["formal_counts"].items():
                counts[outcome] = counts.get(outcome, 0) + count
        updates = {"last_pull_at": inst.now(), "last_error": None,
                   "last_pull": {"collections": got["collections"], "saved": counts},
                   "data_policy": "daily", "fields": oura.FIELDS_VERSION}
        for key in ("daily_through", "daily_scanned_on"):
            if got.get(key):
                updates[key] = got[key]
        state = src.update("oura", **updates)
        inst.app.log("oura_daily_pulled", inst.ctx.instance_id, len(days), counts.get("CREATED", 0))
        return {"state": state, "sync": None}
    saved = {"CREATED": 0, "REVISED": 0, "UNCHANGED": 0}
    sync_result = None
    if got["items"]:
        res = inst.save_items(got["items"], batch_id="OURA-" + today.isoformat(),
                              request_id=oura.batch_request_id(got["items"]) + "-" + uuid.uuid4().hex[:8])
        for r in res["results"]:
            saved[r["outcome"]] = saved.get(r["outcome"], 0) + 1
        sync_result = res["sync"]
    state = src.update("oura", last_pull_at=inst.now(), last_pull_day=today.isoformat(), last_error=None,
                       last_pull={"collections": got["collections"], "saved": saved}, fields=oura.FIELDS_VERSION)
    inst.app.log("oura_pulled", inst.ctx.instance_id, sum(got["collections"].values()), saved["CREATED"])
    return {"state": state, "sync": sync_result}

