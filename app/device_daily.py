"""Compact daily admission and disposable latest readings; never archives raw points.

Existing formal observations, queues and authorizations are not migrated here.
The host holds its application write lock around admit(), not around collection.
"""
from __future__ import annotations

import copy
from datetime import date, datetime, time, timedelta, timezone as UTC_ZONE
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import uuid
import weakref
from zoneinfo import ZoneInfo

from h1_common import H1Error, time_key
from startorch_outbox import ObservationInput
import input_guard

SCHEMA = 'ptds-device-day/1'
SOURCES = {'DEVICE_SOMALOOP', 'DEVICE_QKEER', 'DEVICE_GARMIN', 'DEVICE_OURA'}
METRICS = {'SOMALOOP': {'HR': 'bpm', 'SPO2': '%', 'HRV': 'ms', 'SKIN_TEMP': '°C'},
           'QKEER': {'HR': 'bpm', 'SPO2': '%', **{k: 'raw' for k in ('HRV_RAW', 'TEMP_RAW', 'STEPS_RAW', 'STRESS_RAW', 'MOTION_RAW', 'PERFUSION_RAW')}}}
STATS = ('MEAN', 'MIN', 'MAX', 'COUNT')
SAMPLED_CODES = {f'DEVICE_{s}': {f'{s}_SAMPLE_{m}_{stat}' for m in kinds for stat in STATS}
                 for s, kinds in METRICS.items()}
SAMPLED_CODES['DEVICE_QKEER'].add('QKEER_SLEEP_TAG_COUNT')
QKEER_RAW_FIELDS = {'hrv':'HRV_RAW', 'temperature':'TEMP_RAW', 'step_count':'STEPS_RAW',
                    'stress':'STRESS_RAW', 'motion_intensity':'MOTION_RAW', 'perfusion_index':'PERFUSION_RAW'}
VENDOR_CODES = {
    'DEVICE_GARMIN': {'GARMIN_' + x for x in ('STEPS CAL_TOTAL CAL_ACTIVE RESTING_HR HR_MIN HR_MAX '
        'STRESS_AVG BATTERY_MAX BATTERY_MIN HRV_NIGHT SLEEP_SECONDS SLEEP_DEEP SLEEP_LIGHT SLEEP_REM '
        'SLEEP_AWAKE SPO2_AVG SPO2_MIN RESP_AWAKE RESP_SLEEP').split()},
    'DEVICE_OURA': {'OURA_' + x for x in ('READINESS_SCORE TEMP_DEV SLEEP_SCORE ACTIVITY_SCORE STEPS '
        'CAL_TOTAL CAL_ACTIVE SPO2 HRV LOWEST_HR RESP_RATE TOTAL_SLEEP TIME_IN_BED BEDTIME_START BEDTIME_END').split()},
    'DEVICE_SOMALOOP': {'SOMALOOP_AGENT_' + x for x in ('CAL_DAY DISTANCE_DAY HRV_DAY LOAD_DAY '
                                                     'SPO2_DAY STEPS_DAY TEMP_DEV_DAY').split()},
}
SOMALOOP_SDK_UNITS = {'STEPS': 'steps', 'ACTIVE_SECONDS': 's', 'DISTANCE': 'km', 'CALORIES': 'kcal'}
VENDOR_CODES['DEVICE_SOMALOOP'].update('SOMALOOP_PPI_RMSSD_' + x + '_DAY' for x in ('MEAN','MIN','MAX','COUNT'))
VENDOR_CODES['DEVICE_SOMALOOP'].update('SOMALOOP_SDK_' + name + '_DAY' for name in SOMALOOP_SDK_UNITS)
_TRANSPORT_TIMES = {'acquired_at', 'fetched_at', 'received_at', 'synced_at', 'updated_at'}
_LATEST = weakref.WeakKeyDictionary()
_LATEST_LOCK = threading.RLock()


def _fail(code):
    raise H1Error('DEVICE_DAILY_' + code, '')


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        _fail('NUMBER_INVALID')
    try:
        n = Decimal(str(value))
    except InvalidOperation:
        _fail('NUMBER_INVALID')
    if not n.is_finite() or abs(n) > Decimal('1e30'):
        _fail('NUMBER_INVALID')
    text = format(n, 'f')
    if len(text) > 96:
        _fail('NUMBER_INVALID')
    return '0' if not n else text.rstrip('0').rstrip('.') if '.' in text else text


def _moment(value):
    try:
        moment = (datetime.fromtimestamp(float(value), UTC_ZONE.utc) if type(value) in (int, float)
                  else datetime.fromisoformat(value.replace('Z', '+00:00')))
        if moment.utcoffset() is None:
            _fail('TIMEZONE_REQUIRED')
        return moment.astimezone(UTC_ZONE.utc)
    except (ValueError, TypeError, AttributeError, OverflowError, OSError):
        _fail('TIME_INVALID')


def _day(day, tz):
    try:
        if not isinstance(day, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
            _fail('DAY_INVALID')
        return date.fromisoformat(day), ZoneInfo(tz)
    except (ValueError, TypeError, KeyError):
        _fail('DAY_INVALID')


def _device(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 128 or any(ord(c) < 32 for c in value):
        _fail('DEVICE_INVALID')
    return value


def _code_unit(inst, source, code, unit):
    cdef = inst.app.registry.current.codes.get(code)
    if cdef is None or cdef.family != source:
        _fail('CODE_UNIT_MISMATCH')
    try:
        cdef.rule_for(unit)
    except H1Error:
        _fail('CODE_UNIT_MISMATCH')


def _clean_quality(value, depth=0):
    if depth > 4:
        _fail('QUALITY_INVALID')
    if isinstance(value, dict):
        if len(value) > 32:
            _fail('QUALITY_INVALID')
        out = {}
        for key, item in value.items():
            if not isinstance(key, str) or not 1 <= len(key) <= 64:
                _fail('QUALITY_INVALID')
            if key in _TRANSPORT_TIMES:
                continue
            if key.lower() in {'raw', 'raw_data', 'points', 'records', 'events', 'values', 'readings', 'timestamps'}:
                _fail('RAW_POINTS_FORBIDDEN')
            out[key] = _clean_quality(item, depth + 1)
        return out
    if value is None or isinstance(value, bool) or type(value) is int:
        if type(value) is int and abs(value) > 2**53:
            _fail('QUALITY_INVALID')
        return value
    if isinstance(value, str) and len(value) <= 256:
        return value
    _fail('QUALITY_INVALID')  # No arrays, samples, floats or arbitrary payloads.


def _normalized(body):
    if not isinstance(body, dict) or set(body) - {'schema', 'key', 'source_kind', 'day', 'timezone',
            'device_key', 'method', 'items', 'quality', 'input_digest'}:
        _fail('BODY_INVALID')
    required = {'schema', 'key', 'source_kind', 'day', 'timezone', 'device_key', 'method', 'items', 'quality'}
    if (not required <= set(body) or body['schema'] != SCHEMA or not isinstance(body['source_kind'], str)
            or body['source_kind'] not in SOURCES):
        _fail('BODY_INVALID')
    if not isinstance(body['key'], str) or not 1 <= len(body['key']) <= 128:
        _fail('BODY_INVALID')
    _day(body['day'], body['timezone']); _device(body['device_key'])
    if body['method'] not in ('vendor_daily', 'sampled_daily', 'derived_daily'):
        _fail('METHOD_INVALID')
    allow = (SAMPLED_CODES if body['method'] == 'sampled_daily' else VENDOR_CODES).get(body['source_kind'], set())
    if not isinstance(body['items'], list) or not 0 <= len(body['items']) <= 64:
        _fail('ITEMS_INVALID')
    items, seen = [], set()
    for item in body['items']:
        if not isinstance(item, dict) or set(item) != {'code', 'value_raw', 'unit_raw'}:
            _fail('ITEM_INVALID')
        code, unit = item['code'], item['unit_raw']
        if not isinstance(code, str) or code not in allow or code in seen:
            _fail('CODE_INVALID')
        if not isinstance(unit, str) or not 1 <= len(unit) <= 32:
            _fail('UNIT_INVALID')
        seen.add(code); items.append({'code': code, 'value_raw': _number(item['value_raw']), 'unit_raw': unit})
    quality = _clean_quality(body['quality'])
    if not isinstance(quality, dict) or not isinstance(quality.get('coverage'), str):
        _fail('QUALITY_INVALID')
    if quality.get('raw_retained', False) is not False or quality.get('raw_points_retained', False) is not False:
        _fail('RAW_POINTS_FORBIDDEN')
    is_ppi = any(i['code'].startswith('SOMALOOP_PPI_RMSSD_') for i in items)
    if is_ppi or body['method'] == 'derived_daily':
        if body['source_kind'] != 'DEVICE_SOMALOOP' or body['method'] != 'derived_daily' or not body['device_key'].startswith('somaloop-sdk-ppi:'):
            _fail('PPI_METHOD_INVALID')
        somaloop_ppi_day({'binding_generation':'validated-local', 'kind':'ppi_rmssd',
            'day':body['day'], 'items':items, 'input_digest':body.get('input_digest'), 'quality':quality},
            key=body['key'], timezone=body['timezone'], device_key='validation')
    if body['method'] == 'sampled_daily':
        if quality['coverage'] != 'received_samples_only' or not isinstance(quality.get('metrics'), dict):
            _fail('COVERAGE_INVALID')
        prefix = body['source_kind'].removeprefix('DEVICE_')
        by_code = {item['code']: item for item in items}
        for kind in METRICS.get(prefix, {}):
            codes = [f'{prefix}_SAMPLE_{kind}_{stat}' for stat in STATS]
            present = [code in by_code for code in codes]
            if not any(present):
                continue
            if not all(present):
                _fail('STATISTICS_INCOMPLETE')
            mean, lower, upper, count = [Decimal(by_code[code]['value_raw']) for code in codes]
            if not lower <= mean <= upper or count != count.to_integral_value() or not 1 <= count <= 2**53:
                _fail('STATISTICS_INVALID')
            meta = quality['metrics'].get(kind)
            if (not isinstance(meta, dict) or meta.get('sample_count') != int(count)
                    or type(meta.get('observed_minutes')) is not int or type(meta.get('day_minutes')) is not int
                    or not 1 <= meta['observed_minutes'] <= min(int(count), meta['day_minutes'])
                    or not 1 <= meta['day_minutes'] <= 2880):
                _fail('COVERAGE_INVALID')
            start, end = _moment(meta.get('first_at')), _moment(meta.get('last_at'))
            _, zone = _day(body['day'], body['timezone'])
            if start > end or any(t.astimezone(zone).date().isoformat() != body['day'] for t in (start, end)):
                _fail('COVERAGE_INVALID')
    if body['source_kind'] == 'DEVICE_QKEER' and any(i['code'] == 'QKEER_SLEEP_TAG_COUNT' for i in items):
        tags = quality.get('sleep_tags')
        count = next(Decimal(i['value_raw']) for i in items if i['code'] == 'QKEER_SLEEP_TAG_COUNT')
        if not isinstance(tags, dict) or not tags or any(type(v) is not int or v < 1 for v in tags.values()) or sum(tags.values()) != count:
            _fail('SLEEP_TAG_INVALID')
    if body.get('input_digest') is not None and (not isinstance(body['input_digest'], str) or
                                               not re.fullmatch('[0-9a-f]{64}', body['input_digest'])):
        _fail('DIGEST_INVALID')
    out = {key: body[key] for key in required - {'items', 'quality'}}
    out.update(items=sorted(items, key=lambda item: item['code']), quality=quality)
    if len(_json(out)) > 65536:
        _fail('BODY_TOO_LARGE')
    return out


def body_digest(body):
    """Transport timestamps / vendor request timestamps do not create revisions."""
    return hashlib.sha256(_json(_normalized(body))).hexdigest()


def _dir(root, *parts):
    path = Path(root)
    if path.is_symlink() or not path.is_dir():
        _fail('PATH_UNSAFE')
    for part in parts:
        path = path / part
        if path.is_symlink():
            _fail('PATH_UNSAFE')
        path.mkdir(mode=0o700, exist_ok=True)
    return path


def _load(path):
    if path.is_symlink() or (path.exists() and (not path.is_file() or path.stat().st_nlink != 1)):
        _fail('PATH_UNSAFE')
    if not path.exists():
        return None
    if path.stat().st_size > 65536:
        _fail('STATE_INVALID')
    return json.loads(path.read_text('utf-8'))


def _write(path, value):
    _load(path)  # Reject unsafe existing entries before an atomic replacement.
    raw = _json(value)
    if len(raw) > 65536:
        _fail('STATE_INVALID')
    temporary = path.with_name('.daily-' + uuid.uuid4().hex)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(raw); output.flush(); os.fsync(output.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def admit(inst, body):
    """Admit a closed-day compact report via the existing formal transaction."""
    input_guard.require_writable(inst)
    content = _normalized(body)
    if content['key'] != inst.spec.get('key') or content['timezone'] != inst.ctx.tz:
        _fail('TARGET_MISMATCH')
    day, zone = _day(content['day'], content['timezone'])
    if day >= _moment(inst.now()).astimezone(zone).date():
        _fail('DAY_NOT_CLOSED')
    for item in content['items']:
        _code_unit(inst, content['source_kind'], item['code'], item['unit_raw'])
    digest = body_digest(content)
    root = _dir(inst.ctx.root, 'startorch', 'device_daily')
    receipts = _dir(root, 'receipts'); evidence = _dir(root, 'summaries')
    receipt_path = receipts / (digest + '.json')
    old = _load(receipt_path)
    if old is not None:
        if old.get('content_digest') != digest or old.get('instance_id') != inst.ctx.instance_id:
            _fail('RECEIPT_INVALID')
        return dict(old, duplicate=True)
    proof = evidence / (digest + '.json')
    previous = _load(proof)
    if previous is not None and previous != content:
        _fail('EVIDENCE_CONFLICT')
    if previous is None:
        _write(proof, content)
    identity = hashlib.sha256(_json([inst.ctx.instance_id, content['source_kind'], content['device_key'],
                                    content['timezone'], content['day']])).hexdigest()
    temporal = {'role': 'DAY', 'observed_date': content['day'], 'tz': content['timezone']}
    def unique_key(code):
        # The existing single-account bindings already own these daily keys.
        # Continue their version chains; a different device binding stays isolated.
        if content['method'] == 'vendor_daily':
            if content['source_kind'] == 'DEVICE_OURA' and content['device_key'] == 'oura-account':
                return 'OURA|' + code + '|' + time_key(temporal, '')
            if content['source_kind'] == 'DEVICE_GARMIN' and content['device_key'] == 'garmin-connect-cn':
                return 'GARMIN|' + code + '|' + content['day']
        return 'DEVICE-DAY-1|' + identity + '|' + code
    items = [ObservationInput(unique_key(item['code']), item['code'], item['value_raw'],
              None, item['unit_raw'], temporal, content['source_kind'],
              'DEVICE_DAY:' + digest + '#' + item['code'], 'DEVICE_CONSUMER') for item in content['items']]
    request_id = 'DEVICE-DAY-' + digest
    result = (inst.save_items(items, batch_id='DEVICE-DAY-' + identity, request_id=request_id)
              if items else {'results': []})
    counts = {}
    for row in result['results']:
        counts[row['outcome']] = counts.get(row['outcome'], 0) + 1
    if sum(counts.get(k, 0) for k in ('CREATED', 'REVISED', 'UNCHANGED')) != len(items):
        _fail('RECEIPT_INCOMPLETE')
    receipt = {'schema': 'ptds-device-day-receipt/1', 'ok': True, 'status': 'SAVED' if items else 'NO_DATA',
               'instance_key': content['key'], 'instance_id': inst.ctx.instance_id,
               'source_kind': content['source_kind'], 'day': content['day'], 'device_key': content['device_key'],
               'content_digest': digest, 'request_id': request_id, 'formal_counts': counts, 'projected': len(items)}
    if body.get('input_digest'):
        receipt['input_digest'] = body['input_digest']
    _write(receipt_path, receipt)
    return receipt


def validate_latest(inst, source_kind, code, value_raw, unit_raw, observed_at, device_key=''):
    """Pure validation for hosts that persist aggregate statistics before display."""
    if (not isinstance(source_kind, str) or source_kind not in SOURCES or not isinstance(code, str)
            or not code.startswith(source_kind.removeprefix('DEVICE_') + '_')):
        _fail('CODE_INVALID')
    _code_unit(inst, source_kind, code, unit_raw)
    if device_key != '':
        _device(device_key)
    moment = _moment(observed_at)
    if moment > datetime.now(UTC_ZONE.utc):
        _fail('TIME_FUTURE')
    return {'code': code, 'value_raw': _number(value_raw), 'unit_raw': unit_raw,
            'observed_at': moment.isoformat(), 'device_key': device_key}


def cache_latest_batch(inst, source_kind, items):
    """Validate every item before replacing any RAM reading; no disk writes."""
    if not isinstance(items, list) or not 1 <= len(items) <= 64:
        _fail('ITEMS_INVALID')
    rows = []
    for item in items:
        if not isinstance(item, dict) or set(item) - {'code', 'value_raw', 'unit_raw', 'observed_at', 'device_key'}:
            _fail('ITEM_INVALID')
        rows.append(validate_latest(inst, source_kind, item.get('code'), item.get('value_raw'),
                               item.get('unit_raw'), item.get('observed_at'), item.get('device_key', '')))
    with _LATEST_LOCK:
        sources = _LATEST.setdefault(inst, {})
        readings = sources.setdefault(source_kind, {})
        for row in rows:
            code = row['code']
            if code not in readings or _moment(row['observed_at']) >= _moment(readings[code]['observed_at']):
                readings[code] = row
    return copy.deepcopy(rows)


def cache_latest(inst, source_kind, code, value_raw, unit_raw, observed_at, device_key=''):
    """RAM only; not a formal record, receipt, or authorization decision."""
    return cache_latest_batch(inst, source_kind, [{'code': code, 'value_raw': value_raw, 'unit_raw': unit_raw,
        'observed_at': observed_at, 'device_key': device_key}])[0]


def realtime(inst, source=None):
    """{SOURCE_KIND: {CODE: latest}}; detached per-instance display projection."""
    with _LATEST_LOCK:
        sources = _LATEST.get(inst, {})
        return copy.deepcopy(sources if source is None else ({source: sources[source]} if source in sources else {}))


def _empty_metric():
    return {'count': 0, 'sum': '0', 'min': None, 'max': None, 'first_at': None, 'last_at': None,
            'minutes': '0'}


def _add(metric, value, moment, day, zone):
    value = Decimal(_number(value))
    start = datetime.combine(day, time.min, zone).astimezone(UTC_ZONE.utc)
    minute = int((moment - start).total_seconds() // 60)
    if not 0 <= minute < 2880:
        _fail('TIME_INVALID')
    metric['count'] += 1
    with localcontext() as context:
        context.prec = 80
        metric['sum'] = _number(Decimal(metric['sum']) + value)
    metric['min'] = _number(value if metric['min'] is None else min(value, Decimal(metric['min'])))
    metric['max'] = _number(value if metric['max'] is None else max(value, Decimal(metric['max'])))
    stamp = moment.isoformat()
    metric['first_at'] = min(stamp, metric['first_at'] or stamp)
    metric['last_at'] = max(stamp, metric['last_at'] or stamp)
    metric['minutes'] = format(int(metric['minutes'], 16) | (1 << minute), 'x')


def _body(key, source, day, tz, device, metrics):
    items, coverage = [], {}
    parsed, zone = _day(day, tz)
    start = datetime.combine(parsed, time.min, zone).astimezone(UTC_ZONE.utc)
    end = datetime.combine(parsed + timedelta(days=1), time.min, zone).astimezone(UTC_ZONE.utc)
    day_minutes = int((end - start).total_seconds() // 60)
    prefix = source.removeprefix('DEVICE_')
    for kind, metric in sorted(metrics.items()):
        if not metric['count']:
            continue
        with localcontext() as context:
            context.prec = 18
            mean = _number(Decimal(metric['sum']) / metric['count'])
        for statistic, value in [('MEAN', mean), ('MIN', metric['min']), ('MAX', metric['max']),
                                  ('COUNT', str(metric['count']))]:
            items.append({'code': f'{prefix}_SAMPLE_{kind}_{statistic}', 'value_raw': value,
                          'unit_raw': 'count' if statistic == 'COUNT' else METRICS[prefix][kind]})
        coverage[kind] = {'sample_count': metric['count'], 'first_at': metric['first_at'],
                          'last_at': metric['last_at'], 'observed_minutes': int(metric['minutes'], 16).bit_count(),
                          'day_minutes': day_minutes}
    return {'schema': SCHEMA, 'key': key, 'source_kind': source, 'day': day, 'timezone': tz,
            'device_key': device, 'method': 'sampled_daily', 'items': items,
            'quality': {'coverage': 'received_samples_only', 'raw_retained': False,
                        'algorithm_version': 'sample-arithmetic/1', 'metrics': coverage}}


class SomaloopAccumulator:
    """Fixed-size statistics per local day; no event arrays or individual values."""
    def __init__(self, root, tz, device_key, *, key='', now=None):
        self.tz, self.zone, self.device, self.key = tz, ZoneInfo(tz), _device(device_key), key
        self.now = now or (lambda: datetime.now(UTC_ZONE.utc))
        identity = hashlib.sha256(_json([tz, device_key])).hexdigest()
        self.path = _dir(root, 'startorch', 'device_daily', 'accumulators', identity)
        self.lock = threading.RLock()

    def _clock(self):
        result = self.now() if callable(self.now) else self.now
        return result.astimezone(UTC_ZONE.utc)

    def _state(self, day):
        path = self.path / (day + '.json')
        state = _load(path)
        if state is None:
            state = {'schema': 'ptds-device-aggregate/1', 'timezone': self.tz, 'device_key': self.device,
                     'day': day, 'metrics': {}, 'last_delivery': {}, 'submitted_digest': None}
        if (state.get('schema') != 'ptds-device-aggregate/1' or state.get('day') != day or
                state.get('timezone') != self.tz or state.get('device_key') != self.device or
                set(state.get('metrics', {})) - set(METRICS['SOMALOOP'])):
            _fail('STATE_INVALID')
        return path, state

    def consume(self, kind, value, at, delivery_id=None):
        if kind not in METRICS['SOMALOOP']:
            _fail('CODE_INVALID')
        moment = _moment(at)
        if moment > self._clock():
            _fail('TIME_FUTURE')
        day = moment.astimezone(self.zone).date().isoformat()
        if delivery_id is not None and (not isinstance(delivery_id, str) or not 1 <= len(delivery_id) <= 128):
            _fail('DELIVERY_INVALID')
        with self.lock:
            path, state = self._state(day)
            if delivery_id is not None and state['last_delivery'].get(kind) == delivery_id:
                return {'ok': True, 'ack': 'aggregate_received', 'day': day, 'duplicate': True}
            metric = state['metrics'].setdefault(kind, _empty_metric())
            _add(metric, value, moment, date.fromisoformat(day), self.zone)
            if delivery_id is not None:
                state['last_delivery'][kind] = delivery_id
            _write(path, state)
        return {'ok': True, 'ack': 'aggregate_received', 'day': day}

    def due(self, day=None):
        with self.lock:
            today = self._clock().astimezone(self.zone).date()
            days = [day] if day is not None else sorted(p.stem for p in self.path.glob('*.json'))
            result = []
            for one in days:
                parsed, _ = _day(one, self.tz)
                if parsed >= today:
                    continue
                _, state = self._state(one)
                if not state['metrics']:
                    continue
                body = _body(self.key, 'DEVICE_SOMALOOP', one, self.tz, self.device, state['metrics'])
                if state.get('submitted_digest') != body_digest(body):
                    result.append(body)
            return result

    def mark(self, day, receipt):
        if (receipt.get('schema') != 'ptds-device-day-receipt/1' or receipt.get('ok') is not True or
                receipt.get('day') != day or receipt.get('source_kind') != 'DEVICE_SOMALOOP' or
                receipt.get('device_key') != self.device or receipt.get('instance_key') != self.key or
                not re.fullmatch('[0-9a-f]{64}', str(receipt.get('content_digest')))):
            _fail('RECEIPT_INVALID')
        with self.lock:
            path, state = self._state(day)
            # If a late sample arrived while admission ran, due() detects the
            # different current digest instead of marking the new sample saved.
            state['submitted_digest'] = receipt['content_digest']
            _write(path, state)


def qkeer_records(rows, *, day, timezone):
    """Return current non-retracted rows in RAM; opaque revision order is not guessed."""
    parsed, zone = _day(day, timezone)
    newest = {}
    for row in rows:
        if not isinstance(row, dict) or not all(isinstance(row.get(k), str) and row[k]
                                               for k in ('record_id', 'revision')):
            _fail('QKEER_RECORD_INVALID')
        moment = _moment(row.get('record_time'))
        if moment.astimezone(zone).date() != parsed:
            continue
        old = newest.get(row['record_id'])
        if old is not None:
            if old['revision'] == row['revision']:
                if any(old.get(field) != row.get(field) for field in ('raw_data', 'record_time', 'status', 'deleted')):
                    _fail('QKEER_REVISION_CONFLICT')
                continue
            if not old.get('updated_at') or not row.get('updated_at'):
                _fail('REVISION_AMBIGUOUS')
            before, after = _moment(old['updated_at']), _moment(row['updated_at'])
            if before == after:
                _fail('REVISION_AMBIGUOUS')
            if before > after:
                continue
        newest[row['record_id']] = row
    return [row for row in newest.values()
            if row.get('status') not in ('RETRACTED', 'DELETED') and row.get('deleted') is not True]


def qkeer_day(rows, *, key, day, timezone, device_key):
    """Aggregate a complete fetched day in RAM; ambiguous opaque revisions fail."""
    parsed, zone = _day(day, timezone); _device(device_key)
    metrics, tags = {}, {}
    current = qkeer_records(rows, day=day, timezone=timezone)
    for row in current:
        values = row.get('raw_data')
        if not isinstance(values, dict):
            _fail('QKEER_RECORD_INVALID')
        for field, kind in {'heart_rate':'HR', 'spo2':'SPO2', **QKEER_RAW_FIELDS}.items():
            if values.get(field) is not None:
                _add(metrics.setdefault(kind, _empty_metric()), values[field], _moment(row['record_time']), parsed, zone)
        tag = values.get('sleep_state')
        if tag is not None:
            if not isinstance(tag, str) or not 1 <= len(tag) <= 64 or any(ord(c)<32 for c in tag):
                _fail('SLEEP_TAG_INVALID')
            tags[tag] = tags.get(tag, 0) + 1
            if len(tags) > 32:
                _fail('SLEEP_TAG_LIMIT')
    body = _body(key, 'DEVICE_QKEER', day, timezone, device_key, metrics)
    body['quality'].update(projection_version='qkeer-raw-day/2', unit_semantics='raw_fields_unspecified_by_vendor',
        sleep_semantics='reported_tag_counts_not_durations', source_record_count=len(current),
        source_revision_digest=hashlib.sha256(_json(sorted((r['record_id'],r['revision']) for r in current))).hexdigest())
    if tags:
        body['items'].append({'code':'QKEER_SLEEP_TAG_COUNT','value_raw':str(sum(tags.values())),'unit_raw':'count'})
        body['quality']['sleep_tags'] = tags
    return body


def somaloop_sdk_day(body, *, key, timezone, device_key):
    """Explicit native activity or validated PPI-derived daily summary."""
    if isinstance(body, dict) and body.get("kind") == "ppi_rmssd":
        return somaloop_ppi_day(body, key=key, timezone=timezone, device_key=device_key)
    if not isinstance(body, dict) or set(body) != {'binding_generation', 'day', 'items', 'input_digest'}:
        _fail('SDK_BODY_INVALID')
    items = body['items']
    if not isinstance(items, list) or not 1 <= len(items) <= len(SOMALOOP_SDK_UNITS):
        _fail('SDK_ITEMS_INVALID')
    seen = set()
    for item in items:
        if not isinstance(item, dict) or set(item) != {'code', 'value_raw', 'unit_raw'}:
            _fail('SDK_ITEM_INVALID')
        code = item['code']
        field = next((name for name in SOMALOOP_SDK_UNITS if code == 'SOMALOOP_SDK_' + name + '_DAY'), None)
        if field is None or code in seen or item['unit_raw'] != SOMALOOP_SDK_UNITS[field]:
            _fail('SDK_FIELD_INVALID')
        seen.add(code)
        value = Decimal(_number(item['value_raw']))
        if value < 0 or (field in ('STEPS', 'ACTIVE_SECONDS') and value != value.to_integral_value()):
            _fail('SDK_VALUE_INVALID')
        if field == 'ACTIVE_SECONDS' and value > 86400:
            _fail('SDK_VALUE_INVALID')
    return {'schema': SCHEMA, 'key': key, 'source_kind': 'DEVICE_SOMALOOP',
            'day': body['day'], 'timezone': timezone, 'device_key': 'somaloop-sdk:' + _device(device_key),
            'method': 'vendor_daily', 'items': items, 'input_digest': body['input_digest'],
            'quality': {'coverage': 'device_reported_day', 'raw_points_retained': False,
                        'sdk_history_kind': 'activity', 'transport_complete': True}}


def somaloop_ppi_day(body, *, key, timezone, device_key):
    """Compact SDK result only: never accepts raw intervals, guessed HRV or timestamps."""
    if set(body) != {'binding_generation','kind','day','items','input_digest','quality'}:
        _fail('PPI_BODY_INVALID')
    q=body['quality']
    fixed={'coverage':'valid_windows_by_device_save_day','algorithm':'ppi-rmssd',
           'policy':'sdk-standard-35-300-2000-0.70-1.05','sdk_version':'0.1.16',
           'aggregation':'arithmetic_mean_of_valid_windows','transport_complete':True,
           'raw_points_retained':False,'timestamp_meaning':'device_save_time'}
    counts={'valid_windows','invalid_windows','retained_intervals','adjacent_pairs'}
    if not isinstance(q,dict) or set(q)!=set(fixed)|counts or any(type(q[k]) is not type(v) or q[k]!=v for k,v in fixed.items()):
        _fail('PPI_QUALITY_INVALID')
    if any(type(q[k]) is not int or not 0<=q[k]<=10000000 for k in counts):
        _fail('PPI_COUNTS_INVALID')
    n=q['valid_windows']
    if n<1 or q['retained_intervals']<35*n or not n<=q['adjacent_pairs']<=q['retained_intervals']-n:
        _fail('PPI_COUNTS_INVALID')
    required={'SOMALOOP_PPI_RMSSD_'+x+'_DAY':('count' if x=='COUNT' else 'ms') for x in ('MEAN','MIN','MAX','COUNT')}
    items=body['items']; values={}
    if not isinstance(items,list) or len(items)!=4: _fail('PPI_ITEMS_INVALID')
    for item in items:
        if not isinstance(item,dict) or set(item)!={'code','value_raw','unit_raw'}: _fail('PPI_ITEM_INVALID')
        code=item['code']
        if code not in required or code in values or item['unit_raw']!=required[code]: _fail('PPI_FIELD_INVALID')
        values[code]=Decimal(_number(item['value_raw']))
    get=lambda x: values['SOMALOOP_PPI_RMSSD_'+x+'_DAY']
    if not 0<=get('MIN')<=get('MEAN')<=get('MAX')<=1700 or get('COUNT')!=n:
        _fail('PPI_VALUE_INVALID')
    return {'schema':SCHEMA,'key':key,'source_kind':'DEVICE_SOMALOOP','day':body['day'],
            'timezone':timezone,'device_key':'somaloop-sdk-ppi:'+_device(device_key),
            'method':'derived_daily','items':items,'input_digest':body['input_digest'],'quality':q}
