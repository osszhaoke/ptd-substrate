"""Versioned, read-only current-asset pages. No schema, ingestion or persistent cache writes.

The H1 committed prefix is authoritative for current assets. SQLite still scans
candidates for filtering/sorting; only selected payloads become Python objects.
Metric summaries stream compact scalar columns and retain at most 30 refs/group.
Cursors are signed positions, never capabilities or retained observation caches.
"""
from __future__ import annotations

from read_view import read_connection
import data_read_cache

import base64
from collections import deque
from contextlib import closing, nullcontext
from datetime import datetime, timezone
import hashlib
import hmac
import json
import math
import re
import secrets
import sqlite3
import time
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from cards import _obs, _obs_json, open_startrack
from h1_common import H1Error, strict_loads
from startrack_import import import_cursor
from startorch_outbox import open_startorch
from web import ENTRY_FAMILIES

VERSION = 1
MAX_LIMIT = 200
CURSOR_TTL = 900
_SECRET = secrets.token_bytes(32)
_GROUPS = {'MANUAL': 'manual', 'APPLE_HEALTH': 'phone', **{s: 'wearable' for s in (
    'DEVICE_GARMIN', 'DEVICE_OURA', 'DEVICE_SOMALOOP', 'DEVICE_QKEER', 'DEVICE_WITHINGS', 'DEVICE_CGM')}}


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _hash(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _fail(code, detail):
    raise H1Error(code, detail)


def _limit(value, view):
    if isinstance(value, bool) or not re.fullmatch(r'[1-9][0-9]{0,2}', str(value)):
        _fail('DATA_LIMIT_INVALID', '每页条数无效')
    value = int(value)
    if value > (50 if view == 'metrics' else MAX_LIMIT):
        _fail('DATA_LIMIT_INVALID', '每页条数超过上限')
    return value


def _encode(body):
    raw = _json(body).encode()
    return base64.urlsafe_b64encode(raw + hmac.digest(_SECRET, raw, 'sha256')).decode().rstrip('=')


def _decode(token, version, query):
    try:
        if not isinstance(token, str) or len(token) > 4096:
            raise ValueError()
        value = base64.b64decode(token + '=' * (-len(token) % 4), altchars=b'-_', validate=True)
        raw, sig = value[:-32], value[-32:]
        if not hmac.compare_digest(sig, hmac.digest(_SECRET, raw, 'sha256')):
            raise ValueError()
        body = json.loads(raw)
        if body['query'] != query or body['expires'] < time.time() or type(body['offset']) is not int or body['offset'] < 0:
            raise ValueError()
    except (ValueError, KeyError, TypeError):
        _fail('DATA_CURSOR_INVALID', '读取位置无效或已过期，请重新读取')
    if body['version'] != version:
        _fail('DATA_VIEW_CHANGED', '数据已更新，请重新读取当前筛选')
    return body['offset'], body['expires']


def _stat(path):
    try:
        s = path.stat()
        return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns
    except FileNotFoundError:
        return None


def _version(inst, conn, extras, view, oid):
    cursor = import_cursor(conn)
    db = inst._data_read_db if hasattr(inst, '_data_read_db') else _stat(inst.ctx.startrack_db)
    # Bind rendered content, not unrelated device heartbeats or grant access
    # logs. Local asset cursors are positions, not authorization capabilities;
    # cluster reads still enforce their own current grant independently.
    # Runtime instance configuration is bound below, rather than file mtime.
    formal = None
    evidence = None
    if view in ('observation', 'versions'):
        with read_connection(open_startorch, inst.ctx) as torch:
            formal = torch.execute('SELECT max(revision) FROM formal_observation WHERE observation_id=?', (oid,)).fetchone()[0]
    if view == 'versions':
        # These append-only ledgers can advance without a new observation.
        evidence = [conn.execute('SELECT max(rowid) FROM ' + table).fetchone()[0]
                    for table in ('run', 'run_input', 'card_def')]
    r = inst.app.registry.current
    return cursor[1], _hash([VERSION, getattr(inst, '_data_read_identity', id(inst)), getattr(inst, '_data_read_root', str(inst.ctx.root.resolve())), inst.ctx.instance_id,
                            db[:2] if db else None, inst.ctx.tz, cursor, inst.spec.get('archived_streams'),
                            r.version, getattr(inst, '_data_read_dictionary_identity', id(r)), extras, formal, evidence])


def preview_receipts(inst, text):
    """Unpersisted simulator display metadata; never an ingestion authority."""
    nature = inst.nature or ('REAL' if 'REAL' in inst.ctx.accept else 'SYNTHETIC')
    if nature == 'REAL' or not text:
        return []
    try:
        rows = json.loads(text)
        if not isinstance(rows, list):
            raise ValueError()
        for row in rows:
            if (not isinstance(row, dict) or set(row) != {'created', 'when', 'phone'}
                    or type(row['created']) is not int or row['created'] < 0
                    or any(not isinstance(row[k], str) or len(row[k]) > 200 for k in ('when', 'phone'))):
                raise ValueError()
        return rows
    except (ValueError, TypeError):
        _fail('DATA_PREVIEW_INVALID', '示意同步批次无效，请重新读取')


def extra_rows(inst, gene, receipts):
    """Existing asset metadata, in the same order/format as product.extraRows."""
    tz = ZoneInfo(inst.ctx.tz)
    def when(s):
        try:
            return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(tz).strftime('%Y-%m-%d %H:%M') + '（' + inst.ctx.tz + '）'
        except (ValueError, TypeError, AttributeError):
            return s
    rows = [{'name': '基因测序数据', 'val': f['file_name'], 'when': when(f['received_at']),
             'src': '文件 · 纳管' + {'REAL':' · 真实','SYNTHETIC':' · 合成示例'}.get(f.get('nature'), ''), 'g': 'file'} for f in reversed(gene)]
    rows += [{'name': '苹果健康同步批次', 'val': str(r['created']) + ' 条', 'when': when(r['when']),
              'src': '经苹果健康 · ' + r['phone'], 'g': 'phone', 'sem': 'SEM-35'} for r in receipts if r.get('created', 0) > 0]
    return rows


def _prepare(conn, inst, seq, extras):
    groups_snapshot = getattr(inst, '_data_read_groups', _GROUPS)
    tz = ZoneInfo(inst.ctx.tz)
    policy = inst.spec.get('archived_streams') or {}
    cutoffs = {}
    for source, value in policy.items():
        if source != 'DEVICE_SOMALOOP':
            raise ValueError('DISPLAY_RETENTION_SOURCE_INVALID')
        moment = datetime.fromisoformat(value)
        if moment.tzinfo is None:
            raise ValueError('DISPLAY_RETENTION_TIME_INVALID')
        cutoffs[source] = moment
    def visible(source, role, at):
        return int(source not in cutoffs or role != 'INSTANT' or datetime.fromisoformat(at.replace('Z', '+00:00')) >= cutoffs[source])
    def day(role, at, date):
        return (datetime.fromisoformat(at.replace('Z', '+00:00')).astimezone(tz).date().isoformat() if role == 'INSTANT'
                else date if role == 'DAY' else '时间未知')
    def instant(role, at):
        return datetime.fromisoformat(at.replace('Z', '+00:00')).astimezone(timezone.utc).isoformat() if role == 'INSTANT' else ''
    conn.create_function('data_visible', 3, visible, deterministic=True)
    conn.create_function('data_day', 3, day, deterministic=True)
    conn.create_function('data_instant', 2, instant, deterministic=True)
    conn.create_function('data_group', 1, lambda s: groups_snapshot.get(s, 'file'), deterministic=True)
    # Keep the mapping authoritative in Python, but avoid a Python callback for
    # every row. Values are bound parameters, including retention source names.
    args = {'seq': seq, 'extras': _json(extras)}
    groups = []
    for i, (source, category) in enumerate(groups_snapshot.items()):
        groups.append(f'WHEN :group_source_{i} THEN :group_category_{i}')
        args[f'group_source_{i}'] = source
        args[f'group_category_{i}'] = category
    category_sql = "CASE source " + ' '.join(groups) + " ELSE 'file' END"
    # Only the retained INSTANT stream needs a datetime comparison. Keep the
    # original Python conversion for offsets, microseconds and timezone rules.
    visible_sql = '1'
    if cutoffs:
        names = []
        for i, source in enumerate(cutoffs):
            names.append(f':retained_source_{i}'); args[f'retained_source_{i}'] = source
        visible_sql = ("CASE WHEN role='INSTANT' AND source IN (" + ','.join(names) +
                       ') THEN data_visible(source,role,at) ELSE 1 END')
    sql = '''WITH latest AS (
      SELECT h.* FROM h1_inbox h WHERE h.source_seq<=:seq AND NOT EXISTS (
        SELECT 1 FROM h1_inbox n WHERE n.observation_id=h.observation_id AND n.revision>h.revision AND n.source_seq<=:seq)
    ), fields AS (
      SELECT observation_id oid, revision, payload,
        json_extract(payload,'$.code') code, json_extract(payload,'$.source_kind') source,
        json_extract(payload,'$.temporal.role') role, json_extract(payload,'$.temporal.observed_at') at,
        json_extract(payload,'$.temporal.observed_date') date FROM latest WHERE status='ACTIVE'
    ), assets AS (
      SELECT oid,revision,payload,code,source,{category} category,
        CASE role WHEN 'INSTANT' THEN data_day(role,at,date) WHEN 'DAY' THEN date ELSE '时间未知' END happened,
        CASE role WHEN 'INSTANT' THEN data_instant(role,at) ELSE '' END instant,1 extra_order,0 extra_index,
        json_extract(payload,'$.value_raw') raw,json_extract(payload,'$.unit_raw') unit,
        json_extract(payload,'$.comparator') comparator,at FROM fields WHERE {visible}
      UNION ALL
      SELECT '',0,value,json_extract(value,'$.name'),'',json_extract(value,'$.g'),
        json_extract(value,'$.when'),'',0,CAST(key AS INTEGER),NULL,NULL,NULL,NULL FROM json_each(:extras)
    ) '''.format(category=category_sql, visible=visible_sql)
    return sql, args


def _filter(q):
    parts, params = [], {}
    category = q.get('category', 'ALL')
    if category not in ('ALL', 'wearable', 'file', 'phone', 'manual'):
        _fail('DATA_FILTER_INVALID', '来源分类无效')
    if category != 'ALL':
        parts.append('category=:category'); params['category'] = category
    if q.get('code'):
        parts.append('code=:code'); params['code'] = q['code']
    sources = sorted(set(filter(None, q.get('sources', '').split(','))))
    if len(sources) > 32 or any(len(s) > 80 for s in sources):
        _fail('DATA_FILTER_INVALID', '来源筛选无效')
    if sources:
        parts.append('source IN (' + ','.join(':s' + str(i) for i in range(len(sources))) + ')')
        params.update({'s' + str(i): s for i, s in enumerate(sources)})
    for name, op in (('from', '>='), ('to', '<=')):
        if q.get(name):
            try:
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', q[name]):
                    raise ValueError()
                datetime.strptime(q[name], '%Y-%m-%d')
            except ValueError:
                _fail('DATA_FILTER_INVALID', '日期无效')
            parts.append('happened<>\'时间未知\' AND substr(happened,1,10)' + op + ':' + name)
            params[name] = q[name]
    if q.get('from') and q.get('to') and q['from'] > q['to']:
        _fail('DATA_FILTER_INVALID', '日期范围无效')
    return (' WHERE ' + ' AND '.join(parts) if parts else ''), params


_ORDER = 'happened {direction}, extra_order, extra_index, instant, code, oid'


def _observation(inst, raw):
    labels = {code: c.label_zh for code, c in inst.app.registry.current.codes.items()}
    return _obs_json(_obs(strict_loads(raw), inst.ctx.tz), SimpleNamespace(labels=labels))


def _asset(inst, row):
    oid, revision, raw = row[:3]
    if not oid:
        return {'row': json.loads(raw)}
    return {'observation': _observation(inst, raw)}


def _point(inst, row):
    oid, revision, code, tp, raw, unit, cmp, at = row[:8]
    definition = inst.app.registry.current.codes.get(code)
    # Match the existing page's FULL projection exactly. Completing device
    # chart types is a separate presentation change, not part of pagination.
    if definition and definition.family not in ENTRY_FAMILIES:
        definition = None
    text = '' if raw is None else str(raw)
    numeric = bool(definition and definition.value_type == 'DECIMAL' and not re.search(r'_BEDTIME_(START|END)$', code))
    missing = raw is None or not text.strip()
    exact = numeric and not missing and not cmp and bool(re.fullmatch(r'[-+]?\d+(?:\.\d+)?', text.strip()))
    if exact:
        digits = re.sub(r'^0+', '', re.sub(r'^[+-]?0*', '', text).replace('.', ''))
        exact = len(digits) <= 15 and math.isfinite(float(text))
    try:
        old_numeric = bool(oid) and math.isfinite(float(text.strip() or '0'))
    except ValueError:
        old_numeric = False
    return {'ref': oid + '@' + str(revision) if oid else None, 'extra_index': row[8] if not oid else None, 'tp': tp, 'raw': text, 'unit': unit or '',
            'v': float(text) if exact else None, 'exact': bool(exact), 'missing': missing, 'comparator': cmp,
            'numeric': numeric, 'typed': bool(definition), 'method': None, 'instant': at, 'oldNumeric': old_numeric}


class _Stats:
    """Associative display facts, never a new physiological calculation."""
    def __init__(self):
        self.n = self.exact = self.old_numeric = 0
        self.units = set()
        self.ambiguous = self.missing_time = self.qualified = self.missing = self.untyped = self.numeric = False
        self.all_missing = True
        self.prev = None
        self.lo = self.hi = None
        self.tail = deque(maxlen=30)

    def add(self, p):
        self.n += 1
        self.exact += int(p['exact']); self.old_numeric += int(p['oldNumeric'])
        self.missing |= p['missing']; self.all_missing &= p['missing']
        self.qualified |= bool(p['numeric'] and p['comparator'])
        self.untyped |= not p['typed']; self.numeric |= p['numeric']; self.missing_time |= not bool(p['tp'])
        if self.prev and self.prev['tp'][:10] == p['tp'][:10]:
            try:
                # Date.parse in the existing browser chart has millisecond
                # precision. Sub-millisecond points remain ambiguous there.
                def millis(at):
                    return datetime.fromisoformat(re.sub(r'(\.\d{3})\d+', r'\1', at).replace('Z', '+00:00'))
                self.ambiguous |= not self.prev['instant'] or not p['instant'] or millis(self.prev['instant']) >= millis(p['instant'])
            except (ValueError, TypeError):
                self.ambiguous = True
        if p['exact']:
            self.units.add(p['unit'])
            self.lo = p['v'] if self.lo is None else min(self.lo, p['v'])
            self.hi = p['v'] if self.hi is None else max(self.hi, p['v'])
        self.prev = p
        self.tail.append(p)

    def result(self):
        # _obs_json deliberately exposes no method field, matching the legacy
        # chart's unknown-method warning. No method is invented from source.
        mixed = len(self.units) > 1
        unknown_unit = self.exact > 1 and '' in self.units
        connect = self.exact > 1 and not (mixed or unknown_unit or self.ambiguous or self.missing_time)
        reasons = []
        if not self.n:
            kind = 'zero_observations'; reasons.append(kind)
        else:
            if mixed: reasons.append('mixed_units')
            if unknown_unit: reasons.append('unknown_unit')
            if self.ambiguous: reasons.append('ambiguous_order')
            if self.missing_time: reasons.append('missing_time')
            if not self.exact:
                kind = 'unsupported'
                if self.qualified: kind = 'qualified_numeric_result'; reasons.append(kind)
                elif self.all_missing: reasons.append('no_numeric_values')
                elif self.untyped: reasons.append('unknown_type')
                elif self.numeric: reasons.append('unsupported_precision')
                else: kind = 'categorical_observation'; reasons.append(kind)
            else:
                kind = 'single_numeric_observation' if self.n == 1 else 'non_comparable_series'
                reasons.append('single_numeric_observation' if self.n == 1 else 'unknown_method')
                if self.qualified: kind = 'qualified_numeric_result'; reasons.append(kind)
                if self.missing: reasons.append('missing_values')
        return {'kind': kind, 'grammar': 'G05' if kind == 'categorical_observation' else 'G01' if self.n else None,
                'reasons': reasons, 'connect': bool(connect), 'mixed': mixed, 'noNumericScale': mixed or unknown_unit,
                'ambiguous': bool(self.ambiguous), 'unit': next(iter(self.units)) if len(self.units) == 1 else '',
                'oldPlot': self.old_numeric > 1, 'extent': [self.lo, self.hi], 'points': list(self.tail)}


def _summaries(inst, conn, cte, where, args):
    stats = {}
    for row in conn.execute(cte + 'SELECT oid,revision,code,happened,raw,unit,comparator,at,extra_index FROM assets' + where +
                            ' ORDER BY ' + _ORDER.format(direction='ASC'), args):
        s = stats.get(row[2])
        if s is None:
            s = stats[row[2]] = _Stats()
        s.add(_point(inst, row))
    return stats


def _history(inst, oid, offset, limit):
    import engines
    from evidence_graph import SRC_ZH
    with read_connection(open_startorch, inst.ctx) as torch, read_connection(open_startrack, inst.ctx) as track:
        total, current = torch.execute('SELECT count(*),max(revision) FROM formal_observation WHERE observation_id=?', (oid,)).fetchone()
        names, out = engines.card_names(track), []
        for revision, raw, at in torch.execute('SELECT revision,payload,saved_at FROM formal_observation WHERE observation_id=? ORDER BY revision DESC LIMIT ? OFFSET ?', (oid, limit, offset)):
            p = strict_loads(raw)
            rows = track.execute('SELECT DISTINCT i.run_id,c.card_id FROM run_input i JOIN run r USING(run_id) JOIN card_def c ON c.card_def_id=r.card_def_id WHERE i.observation_id=? AND i.revision=? ORDER BY i.run_id', (oid, revision)).fetchall()
            out.append({'revision': revision, 'status': p.get('status'), 'value': p.get('value_raw'), 'unit': p.get('unit_raw'),
                        'comparator': p.get('comparator'), 'saved_at': at, 'source_zh': SRC_ZH.get(p.get('source_kind'), p.get('source_kind')),
                        'runs': [r for r, _ in rows], 'cards': list(dict.fromkeys(names.get(cid, cid) for _, cid in rows))})
    return total, current, list(reversed(out))


def read(inst, view, *, cursor='', limit=50, extra_rows=None, **filters):
    if view not in ('summary', 'metrics', 'rows', 'series', 'observation', 'versions'):
        _fail('DATA_VIEW_INVALID', '读取视图无效')
    limit = _limit(limit, view)
    extras = extra_rows or []
    filters = {k: str(v) for k, v in filters.items() if k in ('category', 'code', 'sources', 'from', 'to', 'oid', 'revision') and v not in (None, '')}
    where, params = _filter(filters)
    oid = filters.get('oid', '')
    if view in ('observation', 'versions') and (not oid or len(oid) > 160):
        _fail('OBSERVATION_ID_INVALID', '数据标识无效')
    query = _hash([view, limit, filters])
    connection = nullcontext(inst._data_read_connection) if hasattr(inst, '_data_read_connection') else read_connection(open_startrack, inst.ctx)
    with connection as conn:
        seq, version = _version(inst, conn, extras, view, oid)
        offset, expiry = _decode(cursor, version, query) if cursor else (0, time.time() + CURSOR_TTL)
        result = {'projection': 'data-read/1', 'view': view, 'version': version,
                  'scope': {'instance_id': inst.ctx.instance_id, 'source_seq': seq, 'kind': 'committed-current-visible' if view not in ('observation', 'versions') else 'exact-formal-history'}}
        def paged(total, items):
            def token(pos):
                return _encode({'version': version, 'query': query, 'expires': expiry, 'offset': pos})
            return dict(result, total=total, offset=offset, limit=limit, items=items, has_more=offset + limit < total,
                        next_cursor=token(offset + limit) if offset + limit < total else None,
                        previous_cursor=token(max(0, offset - limit)) if offset else None)
        if view == 'observation':
            import evidence_navigation
            exact = evidence_navigation.observation(inst, oid, filters.get('revision'))
            return dict(result, observation=_observation(inst, _json(exact['payload'])) if exact['found'] else None,
                        found=exact['found'], metadata={k: v for k, v in exact.items() if k != 'payload'})
        if view == 'versions':
            total, current, items = _history(inst, oid, offset, limit)
            return dict(paged(total, items), current_revision=current)
        cacheable = not cursor and limit == 50 and filters in ({}, {'category': 'ALL'}) and view in ('summary', 'metrics')
        cache_identity = (version, tuple(sorted(getattr(inst, '_data_read_groups', _GROUPS).items()))) if cacheable else None
        cached = data_read_cache.get(inst, cache_identity, view) if cacheable else None
        if cached is not None:
            return dict(result, **cached) if view == 'summary' else paged(cached['total'], cached['items'])
        cte, args = _prepare(conn, inst, seq, extras)
        args.update(params)
        if view == 'summary':
            counts = {g: n for g, n in conn.execute(cte + 'SELECT category,count(*) FROM assets GROUP BY category', args)}
            aggregate = dict(total=sum(counts.values()), counts=counts)
            if cacheable:
                data_read_cache.put(inst, cache_identity, view, aggregate)
            return dict(result, **aggregate)
        if view in ('metrics', 'series'):
            stats = _summaries(inst, conn, cte, where, args)
            if view == 'metrics':
                labels = {code: c.label_zh for code, c in inst.app.registry.current.codes.items()}
                keys = sorted(stats, key=lambda code: re.sub(r'，距当天\s*0\s*点分钟', '', labels.get(code, code)))
                keys.sort(key=lambda code: stats[code].prev['tp'], reverse=True)
                items = []
                for code in keys[offset:offset + limit]:
                    s = stats[code]
                    if s.prev['ref']:
                        last_oid, last_rev = s.prev['ref'].rsplit('@', 1)
                        last = conn.execute('SELECT observation_id,revision,payload FROM h1_inbox WHERE observation_id=? AND revision=?', (last_oid, int(last_rev))).fetchone()
                        asset = _asset(inst, last)
                    else:
                        asset = {'row': extras[s.prev['extra_index']]}
                    items.append({'code': code, 'count': s.n, 'last': asset, 'series': s.result()})
                if cacheable:
                    data_read_cache.put(inst, cache_identity, view, dict(total=len(keys), items=items))
                return paged(len(keys), items)
            if not filters.get('code'):
                _fail('DATA_FILTER_INVALID', '请选择指标')
            s = stats.get(filters['code'], _Stats())
            points = [_point(inst, r) for r in conn.execute(cte + 'SELECT oid,revision,code,happened,raw,unit,comparator,at,extra_index FROM assets' + where +
                         ' ORDER BY ' + _ORDER.format(direction='DESC').replace('extra_order, extra_index, instant, code, oid', 'extra_order DESC, extra_index DESC, instant DESC, code DESC, oid DESC') + ' LIMIT :limit OFFSET :offset', dict(args, limit=limit, offset=offset))]
            points.reverse()
            presentation = s.result(); presentation.pop('points')
            return dict(paged(s.n, points), presentation=presentation)
        # Keep full payloads out of SQLite's offset+limit sorting records.
        # A window count shares the filtered scan with the page. An empty or
        # out-of-range page has no row carrying that count, so retain the exact
        # count query for that case (a signed cursor may point past the end).
        page_sql = ' ORDER BY ' + _ORDER.format(direction='DESC') + ' LIMIT :limit OFFSET :offset'
        page_args = dict(args, limit=limit, offset=offset)
        if sqlite3.sqlite_version_info >= (3, 25, 0):
            refs = conn.execute(cte + 'SELECT oid,revision,extra_index,count(*) OVER () FROM assets' + where + page_sql, page_args).fetchall()
            total = refs[0][3] if refs else conn.execute(cte + 'SELECT count(*) FROM assets' + where, args).fetchone()[0]
        else:
            # Older custom Python builds keep the existing two-query path.
            total = conn.execute(cte + 'SELECT count(*) FROM assets' + where, args).fetchone()[0]
            refs = [(*r, total) for r in conn.execute(cte + 'SELECT oid,revision,extra_index FROM assets' + where + page_sql, page_args)]
        items = []
        for oid, revision, extra_index, _ in refs:
            row = conn.execute('SELECT observation_id,revision,payload FROM h1_inbox WHERE observation_id=? AND revision=?', (oid, revision)).fetchone() if oid else ('', 0, _json(extras[extra_index]))
            if row is None:
                _fail('DATA_VIEW_CHANGED', '数据已更新，请重新读取当前筛选')
            items.append(_asset(inst, row))
        return paged(total, items)
