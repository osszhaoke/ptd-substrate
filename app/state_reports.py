"""Local scheduled report projections. No new canonical health store or network I/O.

Snapshots and accepted model output are immutable derived documents; subscription
metadata and notification intents use atomic replace. Health measurements are
never included in notification payloads. The owner injects mobile delivery.
"""
from __future__ import annotations

import copy
from datetime import datetime, time, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import uuid
from zoneinfo import ZoneInfo

import starling_weekly as weekly
from cards import MacOSNotifier

CARD_NAMES = {**{'grp:' + k: v for k, v in weekly.NAMES.items()},
    'band:LIVE.SOMALOOP-SPOT': '现场体征 · Somaloop',
    'band:LIVE.SPO2-LOW': '血氧低值提示',
    'band:SLEEP.A03-HRV-DEV-SOMALOOP': '夜间基线偏离 · Somaloop'}
SPOT_CODES = [('SOMALOOP_HR', '心率'), ('SOMALOOP_SPO2', '血氧'),
              ('SOMALOOP_SKIN_TEMP', '皮温'), ('SOMALOOP_HRV', '心率变异性')]
NIGHT_RULES = ('SLEEP.A03-HRV-DEV-SOMALOOP', 'SLEEP.A04-LOWHR-DEV-SOMALOOP',
               'RHYTHM.F01-TEMPDEV-SOMALOOP')
SAFE_KEY = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z')
SAFE_REPORT = re.compile(r'rpt-[0-9a-f]{32}\Z')
CLOCK = re.compile(r'(?:[01][0-9]|2[0-3]):[0-5][0-9]\Z')
NOTICE_TITLE, NOTICE_BODY = 'PTDS 状态报告', '你的状态报告已生成，打开 PTDS 查看。'


class ReportError(ValueError):
    def __init__(self, code, detail=''):
        self.code, self.detail = code, detail or code
        super().__init__(self.detail)


def _instant(value, tz):
    current = datetime.fromisoformat(value) if isinstance(value, str) else value
    if not isinstance(current, datetime) or current.tzinfo is None:
        raise ReportError('REPORT_TIME_INVALID', '时间必须包含时区')
    return current.astimezone(ZoneInfo(tz))


def _at(day, clock, tz):
    hour, minute = map(int, clock.split(':'))
    return datetime.combine(day, time(hour, minute), ZoneInfo(tz))


def first_due(now, clock, tz):
    current = _instant(now, tz)
    due = _at(current.date(), clock, tz)
    return due if due > current else _at(current.date() + timedelta(days=1), clock, tz)


def latest_due(subscription, now):
    current = _instant(now, subscription['tz'])
    anchor = _instant(subscription['anchor_at'], subscription['tz'])
    if current < anchor:
        return None
    count = (current.date() - anchor.date()).days // subscription['period_days']
    due = _at(anchor.date() + timedelta(days=count * subscription['period_days']),
              subscription['time'], subscription['tz'])
    if due > current:
        count -= 1
        due = _at(anchor.date() + timedelta(days=count * subscription['period_days']),
                  subscription['time'], subscription['tz'])
    return due if count >= 0 else None


def report_window(due, days, tz):
    if type(days) is not int or days not in (1, 3, 7):
        raise ReportError('REPORT_PERIOD_INVALID', '请选择每天、每三天或每周')
    local = _instant(due, tz)
    end = datetime.combine(local.date(), time.min, ZoneInfo(tz))
    start = datetime.combine(local.date() - timedelta(days=days), time.min, ZoneInfo(tz))
    return start, end


def catalog(snapshot):
    groups = {'grp:' + x['id'] for x in (snapshot.get('engines') or {}).get('groups') or []}
    prefs = snapshot.get('wall_prefs') or {}
    hidden = {x['card'] for x in prefs.get('hidden') or []}
    pins = set(prefs.get('pins') or [])
    band = snapshot.get('band_cards') or {}
    band_available = {'band:LIVE.SOMALOOP-SPOT': bool(band.get('spot')),
                      'band:LIVE.SPO2-LOW': 'spo2_low' in band,
                      'band:SLEEP.A03-HRV-DEV-SOMALOOP': bool(band.get('night'))}
    return [dict(id=cid, name=name, selected=cid in pins and cid not in hidden,
                 available=(cid in groups or band_available.get(cid, False)) and cid not in hidden,
                 reason=('卡片已隐藏' if cid in hidden else '' if cid in groups or band_available.get(cid, False)
                         else '尚未启用或暂无此卡片')) for cid, name in CARD_NAMES.items()]


def _recorded_rules(card, snapshot, rule_ids, start, end, zone):
    """Only render existing per-date rule results; never re-label a cumulative card."""
    entries = [entry for group in (snapshot.get('engines') or {}).get('groups') or []
               for entry in group.get('cards') or [] if entry.get('rule') in rule_ids]
    for entry in entries:
        chosen = {}
        for run in sorted(entry.get('runs') or [], key=lambda r: r['run_id']):
            for item in run.get('items') or []:
                chosen[item['tp']] = dict(item, run_id=run['run_id'])
        records = []
        for tp, item in sorted(chosen.items()):
            when = weekly._when(None, tp, zone)
            if when is None or not start <= when[0] < end or item.get('status') == 'VANISHED':
                continue
            value = item.get('text') or item.get('reason') or item.get('status_zh')
            if value is None:
                continue
            records.append(dict(kind='state', label=entry.get('name') or entry['rule'],
                                value=value, unit='', at=when[1], precision=when[2],
                                rule=entry['rule'], code=entry['rule'], run_id=item['run_id'],
                                ref=f"run:{item['run_id']}:{entry['rule']}:{tp}"))
        if records:
            card['records'].extend(records)
            weekly._fact(card, 'state', entry.get('name') or entry['rule'],
                         weekly._clause(entry.get('name') or entry['rule'], records, '本期'),
                         '本期已有逐时点计算记录，只陈述原结果')


def build(snapshot, card_ids, due, days, tz):
    """Explicit selected scope and previous complete calendar-day window."""
    start, end = report_window(due, days, tz)
    zone = ZoneInfo(tz)
    groups = {'grp:' + group['id']: group for group in (snapshot.get('engines') or {}).get('groups') or []}
    available = {row['id']: row['available'] for row in catalog(snapshot)}
    output = []
    for cid in card_ids:
        if cid not in CARD_NAMES:
            raise ReportError('REPORT_CARD_UNKNOWN', '包含不支持的状态卡片')
        card = dict(id=cid, name=CARD_NAMES[cid], facts=[], records=[])
        if not available.get(cid):
            weekly._fact(card, 'empty', card['name'], '本卡当前已隐藏、停用或不可用，本期未读取其数据', '卡片当前不可用')
        elif cid in groups:
            fn = weekly._mas if cid == 'grp:MAS' else weekly._branch
            fn(card, groups[cid], snapshot, start, end - timedelta(microseconds=1), zone,
               period_label='本期', scope_label='本期')
        elif cid == 'band:LIVE.SOMALOOP-SPOT':
            for code, label in SPOT_CODES:
                records, unknown = weekly._raw_records(snapshot, code, label, start, end - timedelta(microseconds=1), zone)
                card['records'].extend(records)
                text = weekly._clause(label, records, '本期')
                if unknown:
                    text += f'；另有{unknown}条观测时间不明确，未计入本期'
                weekly._fact(card, 'observations' if records else 'empty', label, text,
                             '本期原始观测记录，不推断连续监测或医学结论')
        elif cid == 'band:LIVE.SPO2-LOW':
            # Current snapshot is cumulative. Do not reinterpret its count as a period result.
            records, unknown = weekly._raw_records(snapshot, 'SOMALOOP_SPO2', '血氧', start,
                                                    end - timedelta(microseconds=1), zone)
            card['records'].extend(records)
            weekly._fact(card, 'observations' if records else 'empty', '血氧',
                         weekly._clause('血氧', records, '本期') + '；此卡尚无按本期保存的低值统计，未采用累计计数',
                         '只展示本期原始血氧记录，缺少本期低值统计，不新增计算')
            if unknown:
                weekly._fact(card, 'empty', '观测时间', f'另有{unknown}条观测时间不明确，未计入本期', '观测时间缺失')
        else:
            _recorded_rules(card, snapshot, NIGHT_RULES, start, end, zone)
            if not card['facts']:
                weekly._fact(card, 'empty', card['name'], '本期缺少可用的逐晚基线偏离记录，当前卡片结果不能代替本期历史',
                             '本期逐晚历史不足，不重算或推断历史基线')
        if not card['facts']:
            weekly._fact(card, 'empty', card['name'], '本卡尚无已启用且可用于本期汇总的指标', '本期没有可用指标')
        output.append(card)
    number = 0
    for card in output:
        for fact in card['facts']:
            number += 1
            fact['id'] = 'F' + str(number)
    return dict(scope='selected-state-report/1', period=dict(start=start.isoformat(), end=end.isoformat(),
                end_exclusive=True, days=days, tz=tz,
                label=f'{start.date().isoformat()} 至 {(end.date() - timedelta(days=1)).isoformat()}'), cards=output)


class Manager:
    def __init__(self, app):
        self.app = app
        self.root = Path(app.root) / 'state-reports'
        self.lock = threading.RLock()
        self.tick_lock = threading.Lock()
        self.wake = threading.Event()
        self.halt = threading.Event()
        self.thread = None
        # Optional callback(key, immutable_report) -> None. No health data in transport notifications.
        self.on_report = None

    def _instance(self, key):
        if not isinstance(key, str) or not key or len(key) > 200 or key not in self.app.instances:
            raise ReportError('REPORT_INSTANCE_INVALID', '实例不可用')
        return self.app.instances[key]

    def _folder(self, key, create=False):
        self._instance(key)
        folder = self.root / ('instance-' + hashlib.sha256(key.encode('utf-8')).hexdigest()[:24])
        for path in (self.root, folder, folder / 'reports'):
            if path.is_symlink():
                raise ReportError('REPORT_PATH_INVALID', '报告路径不可用')
        if create:
            (folder / 'reports').mkdir(parents=True, exist_ok=True, mode=0o700)
        return folder

    def _meta(self, key):
        path = self._folder(key) / 'metadata.json'
        if path.is_symlink():
            raise ReportError('REPORT_PATH_INVALID', '报告路径不可用')
        if not path.exists():
            return dict(subscription=None, reports=[], delivery={}, last_attempt=None)
        try:
            value = json.loads(path.read_text('utf-8'))
            if not isinstance(value, dict) or not isinstance(value.get('reports'), list):
                raise ValueError()
            return value
        except (ValueError, OSError) as exc:
            raise ReportError('REPORT_METADATA_INVALID', '报告配置无法读取，未覆盖现有文件') from exc

    def _store(self, key, value):
        folder = self._folder(key, create=True)
        dest = folder / 'metadata.json'
        if dest.is_symlink():
            raise ReportError('REPORT_PATH_INVALID', '报告路径不可用')
        temp = folder / ('.metadata-' + uuid.uuid4().hex)
        try:
            with temp.open('x', encoding='utf-8') as handle:
                os.chmod(temp, 0o600)
                json.dump(value, handle, ensure_ascii=False, separators=(',', ':'))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, dest)
        finally:
            if temp.exists():
                temp.unlink()

    def _snapshot(self, key):
        inst = self._instance(key)
        with self.app.lock:
            return copy.deepcopy(inst.snapshot()), inst

    @staticmethod
    def _validate(body, snapshot):
        allowed = {'card_ids', 'period_days', 'time', 'local_notification', 'enabled'}
        if not isinstance(body, dict) or set(body) - allowed:
            raise ReportError('REPORT_INPUT_INVALID', '报告设置格式不正确')
        ids = body.get('card_ids')
        if not isinstance(ids, list) or not ids or len(ids) > len(CARD_NAMES) or any(not isinstance(x, str) for x in ids):
            raise ReportError('REPORT_CARDS_INVALID', '请至少选择一张状态卡片')
        if len(ids) != len(set(ids)):
            raise ReportError('REPORT_CARDS_INVALID', '状态卡片不能重复')
        usable = {x['id'] for x in catalog(snapshot) if x['available']}
        if any(cid not in usable for cid in ids):
            raise ReportError('REPORT_CARD_UNAVAILABLE', '选中的卡片已隐藏、停用或不可用')
        if type(body.get('period_days')) is not int or body['period_days'] not in (1, 3, 7):
            raise ReportError('REPORT_PERIOD_INVALID', '请选择每天、每三天或每周')
        if not isinstance(body.get('time'), str) or not CLOCK.fullmatch(body['time']):
            raise ReportError('REPORT_CLOCK_INVALID', '请选择有效的推送时间')
        if any(type(body.get(k)) is not bool for k in ('local_notification', 'enabled')):
            raise ReportError('REPORT_INPUT_INVALID', '请选择通知和订阅开关')
        return copy.deepcopy(body)

    def phone_metadata(self, key):
        """Read derived report metadata only; a phone poll never rebuilds health snapshots."""
        with self.lock:
            meta = self._meta(key)
            return dict(subscription=copy.deepcopy(meta['subscription']),
                        reports=copy.deepcopy(list(reversed(meta['reports']))))

    def status(self, key):
        snapshot, inst = self._snapshot(key)
        with self.lock:
            meta = self._meta(key)
            return dict(tz=inst.ctx.tz, subscription=copy.deepcopy(meta['subscription']), catalog=catalog(snapshot),
                        reports=copy.deepcopy(list(reversed(meta['reports']))), delivery=copy.deepcopy(meta['delivery']),
                        generation=copy.deepcopy(meta.get('last_attempt')),
                        local_notification_available=any(getattr(n, 'channel', '') == 'MACOS' for n in getattr(self.app, 'notifiers', [])))

    def save(self, key, body):
        snapshot, inst = self._snapshot(key)
        data = self._validate(body, snapshot)
        now = _instant(inst.now(), inst.ctx.tz)
        with self.lock:
            meta = self._meta(key)
            old = meta['subscription'] or {}
            if old and all(old.get(k) == value for k, value in data.items()):
                return dict(tz=inst.ctx.tz, subscription=copy.deepcopy(old), catalog=catalog(snapshot), reports=copy.deepcopy(list(reversed(meta['reports']))), delivery=copy.deepcopy(meta['delivery']), generation=copy.deepcopy(meta.get('last_attempt')), local_notification_available=any(getattr(n, 'channel', '') == 'MACOS' for n in getattr(self.app, 'notifiers', [])))
            sub = dict(data, id=old.get('id') or 'sub-' + uuid.uuid4().hex,
                       revision=old.get('revision', 0) + 1, tz=inst.ctx.tz, updated_at=now.isoformat(),
                       anchor_at=first_due(now, data['time'], inst.ctx.tz).isoformat(),
                       next_due_at=first_due(now, data['time'], inst.ctx.tz).isoformat(), last_due_at=None)
            meta['subscription'], meta['last_attempt'] = sub, None
            self._store(key, meta)
        self.wake.set()
        return self.status(key)

    def pause(self, key, paused):
        if type(paused) is not bool:
            raise ReportError('REPORT_INPUT_INVALID', '暂停状态不正确')
        inst = self._instance(key)
        with self.lock:
            meta = self._meta(key)
            sub = meta['subscription']
            if not sub:
                raise ReportError('REPORT_SUBSCRIPTION_MISSING', '请先保存订阅')
            if sub['enabled'] == paused:
                sub.update(enabled=not paused, revision=sub['revision'] + 1, updated_at=inst.now())
                meta['last_attempt'] = None
                self._store(key, meta)
        self.wake.set()
        return self.status(key)

    def preview(self, key, body):
        snapshot, inst = self._snapshot(key)
        data = self._validate(body, snapshot)
        due = first_due(inst.now(), data['time'], inst.ctx.tz)
        result = weekly.summarize(self.app.llm, build(snapshot, data['card_ids'], due, data['period_days'], inst.ctx.tz))
        return dict(result, preview=True, card_ids=data['card_ids'])

    def report(self, key, report_id):
        if not isinstance(report_id, str) or not SAFE_REPORT.fullmatch(report_id):
            raise ReportError('REPORT_NOT_FOUND', '报告不存在')
        with self.lock:
            meta = self._meta(key)
            if report_id not in {r['id'] for r in meta['reports']}:
                raise ReportError('REPORT_NOT_FOUND', '报告不存在')
            path = self._folder(key) / 'reports' / (report_id + '.json')
            if path.is_symlink():
                raise ReportError('REPORT_PATH_INVALID', '报告路径不可用')
            try:
                return json.loads(path.read_text('utf-8'))
            except (OSError, ValueError) as exc:
                raise ReportError('REPORT_NOT_FOUND', '报告暂不可读取') from exc

    def _write_report(self, key, doc):
        path = self._folder(key, create=True) / 'reports' / (doc['id'] + '.json')
        encoded = json.dumps(doc, ensure_ascii=False, separators=(',', ':'))
        if path.exists():
            if path.is_symlink():
                raise ReportError('REPORT_PATH_INVALID', '报告路径不可用')
            existing = json.loads(path.read_text('utf-8'))
            if any(existing.get(k) != doc.get(k) for k in ('id', 'subscription_id', 'revision', 'card_ids', 'period', 'scheduled_at')):
                raise ReportError('REPORT_IMMUTABLE_CONFLICT', '已存在的报告不可覆盖')
            # Recover the already committed derived document after a metadata interruption.
            return existing
        temp = path.parent / ('.report-' + uuid.uuid4().hex)
        try:
            with temp.open('x', encoding='utf-8') as handle:
                os.chmod(temp, 0o600)
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            # Hard-link is atomic and refuses replacement of an immutable report.
            os.link(temp, path)
        finally:
            if temp.exists():
                temp.unlink()
        return doc

    def _deliver(self, key, report_id, revision):
        for channel in ('local', 'mobile'):
            with self.lock:
                meta = self._meta(key)
                sub = meta['subscription']
                item = meta['delivery'].get(report_id)
                if not sub or not sub['enabled'] or sub['revision'] != revision or not item or item.get(channel) != 'pending':
                    continue
                notifier = next((n for n in getattr(self.app, 'notifiers', []) if getattr(n, 'channel', '') == 'MACOS'), None)
                if channel == 'local' and notifier is None:
                    item[channel] = 'unavailable'
                    self._store(key, meta)
                    continue
                if channel == 'mobile' and not self.on_report:
                    continue
                doc = self.report(key, report_id) if channel == 'mobile' else None
                # Intent is recorded before any external side effect. A leftover 'sending'
                # is an unknown outcome and is not replayed automatically after restart.
                item[channel] = 'sending'
                self._store(key, meta)
            with self.lock:
                latest = self._meta(key)['subscription']
                allowed = bool(latest and latest['enabled'] and latest['revision'] == revision)
            outcome = 'cancelled'
            callback_state = None
            if allowed:
                try:
                    if channel == 'local':
                        if isinstance(notifier, MacOSNotifier):
                            MacOSNotifier.send(notifier, NOTICE_TITLE, NOTICE_BODY, 'NONE')
                        else:  # Injected recording / test notifier.
                            notifier.send(NOTICE_TITLE, NOTICE_BODY, 'NONE')
                        outcome = 'sent'
                    else:
                        reply = self.on_report(key, doc)
                        # An adapter returning None proves only dispatch, not delivery.
                        outcome = 'dispatched'
                        if isinstance(reply, dict):
                            callback_state = reply.get('state')
                            if isinstance(callback_state, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,48}', callback_state):
                                outcome = callback_state
                            else:
                                callback_state = None
                except Exception:
                    outcome = 'failed'
            with self.lock:
                meta = self._meta(key)
                if report_id in meta['delivery']:
                    meta['delivery'][report_id][channel] = outcome
                    self._store(key, meta)

    def tick(self, now=None):
        if not self.tick_lock.acquire(blocking=False):
            return []
        out = []
        try:
            for key in list(self.app.instances):
                try:
                    inst = self._instance(key)
                    current = _instant(now if now is not None else inst.now(), inst.ctx.tz)
                    with self.lock:
                        recovery = self._meta(key)
                        pending = [(r['id'], r['revision']) for r in recovery['reports']
                                   if 'pending' in recovery['delivery'].get(r['id'], {}).values()]
                    for report_id, revision in pending:
                        self._deliver(key, report_id, revision)
                    with self.lock:
                        meta = self._meta(key)
                        sub = copy.deepcopy(meta['subscription'])
                        if not sub or not sub['enabled']:
                            continue
                        due = latest_due(sub, current)
                        if due is None or (sub.get('last_due_at') and due <= _instant(sub['last_due_at'], sub['tz'])):
                            continue
                        attempt = meta.get('last_attempt')
                        if attempt and attempt.get('revision') == sub['revision'] and (current - _instant(attempt['at'], sub['tz'])).total_seconds() < 60:
                            continue
                        meta['last_attempt'] = dict(at=current.isoformat(), revision=sub['revision'], state='generating')
                        self._store(key, meta)
                    snapshot, _ = self._snapshot(key)
                    result = weekly.summarize(self.app.llm, build(snapshot, sub['card_ids'], due, sub['period_days'], sub['tz']))
                    with self.lock:
                        meta = self._meta(key)
                        live = meta['subscription']
                        if self.halt.is_set() or not live or not live['enabled'] or live['revision'] != sub['revision']:
                            out.append(dict(key=key, state='superseded'))
                            continue
                        meta['last_attempt'] = dict(at=current.isoformat(), revision=sub['revision'], state=result['state'], why=result.get('why'))
                        if result['state'] != 'ok':
                            self._store(key, meta)
                            out.append(dict(key=key, state=result['state']))
                            continue
                        identity = f"{sub['id']}|{sub['revision']}|{due.isoformat()}"
                        report_id = 'rpt-' + hashlib.sha256(identity.encode()).hexdigest()[:32]
                        doc = {k: copy.deepcopy(result[k]) for k in ('period', 'cards', 'by', 'method', 'fp')}
                        doc.update(state='ok', id=report_id, subscription_id=sub['id'], revision=sub['revision'],
                                   created_at=current.isoformat(), card_ids=sub['card_ids'], scheduled_at=due.isoformat())
                        doc = self._write_report(key, doc)
                        meta['reports'].append({k: copy.deepcopy(doc[k]) for k in ('id', 'subscription_id', 'revision', 'created_at', 'card_ids', 'period')})
                        live['last_due_at'] = due.isoformat()
                        live['next_due_at'] = _at(due.date() + timedelta(days=sub['period_days']), sub['time'], sub['tz']).isoformat()
                        meta['delivery'][report_id] = dict(local='pending' if sub['local_notification'] else 'disabled',
                                                           mobile='pending' if self.on_report else 'not_configured')
                        self._store(key, meta)
                    self._deliver(key, report_id, sub['revision'])
                    out.append(dict(key=key, state='ok', id=report_id))
                except Exception as exc:
                    # Only codes, never values, model text, endpoint or exception strings.
                    if hasattr(self.app, 'log'):
                        self.app.log('state_report_failed', key, getattr(exc, 'code', type(exc).__name__))
                    out.append(dict(key=key, state='error', code=getattr(exc, 'code', type(exc).__name__)))
            return out
        finally:
            self.tick_lock.release()

    def _run(self):
        while not self.halt.is_set():
            self.tick()
            self.wake.wait(30)
            self.wake.clear()

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.halt.clear()
        self.thread = threading.Thread(target=self._run, name='ptds-state-reports', daemon=True)
        self.thread.start()

    def stop(self):
        self.halt.set()
        self.wake.set()
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(timeout=2)
