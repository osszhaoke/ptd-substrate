"""Metadata-only device recovery facade. No credentials, values or history reads."""
from __future__ import annotations

import time
import threading
import re
import device_targets
from urllib.parse import urlencode

NAMES = {'oura': 'Oura', 'garmin': 'Garmin', 'qkeer': 'QKeer', 'somaloop': 'Somaloop'}
_lock = threading.Lock()
_inflight = set()


def _text(value, limit=160):
    return ' '.join(str(value or '').split())[:limit]


def _reason(src):
    error = src.get('sync_error') or src.get('last_error')
    raw = error.get('code') if isinstance(error, dict) else error
    # Export a symbolic code only, never an exception message, URL or headers.
    code = raw if isinstance(raw, str) and re.fullmatch(r'[A-Z][A-Z0-9_]*(?:[.:-][A-Z0-9_]+)*', raw) and len(raw) <= 80 else None
    category = src.get('retry_category')
    if category not in ('auth', 'rate_limit', 'network_or_service', 'tls', 'blocked', 'paused'):
        category = None
    upper = code or ''
    if src.get('paused') or src.get('status') in ('PAUSED', 'PAUSED_PRIMARY_BRIDGE'):
        category = 'paused'
    elif src.get('status') in ('NEEDS_REAUTH', 'REVOKED') or any(x in upper for x in ('REVOK', 'REAUTH', 'INVALID_CLIENT', 'UNAUTHORIZED', 'SCOPE_DENIED', 'SUBJECT_MISMATCH', 'USER_ACCESS_DENIED')):
        category = 'auth'
    elif any(x in upper for x in ('RATE_LIMIT', 'TOO_MANY_REQUESTS', 'HTTP_429')):
        category = 'rate_limit'
    elif any(x in upper for x in ('TLS', 'SSL', 'CERTIFICATE')):
        category = 'tls'
    elif any(x in upper for x in ('BLOCKED', 'PERMISSION', 'FORBIDDEN')):
        category = 'blocked'
    elif error and category is None:
        category = 'network_or_service'
    hints = {
        'auth': '请在设备连接设置中更新登录或授权，完成后再同步。',
        'rate_limit': '服务正在限制请求，请等待允许重试时间，连续点击不会加快恢复。',
        'tls': '请检查系统时间、代理及网络证书路径；保留证书验证，网络恢复后再重试。',
        'blocked': '请查看设备权限或服务访问设置；恢复访问后再重试。',
        'paused': '当前已暂停，不会自动恢复；请在连接设置中确认后恢复。',
        'network_or_service': '请检查网络和代理路径；网络恢复后会自动重试，也可手动重试同步。',
    }
    return code, category, hints.get(category, '')


def _row(key, name, src):
    error = src.get('sync_error') or src.get('last_error')
    code = error.get('code') if isinstance(error, dict) else error
    status = src.get('status')
    reason, category, hint = _reason(src)
    state, message = 'UNCONFIRMED', '状态待确认'
    if src.get('paused') or status in ('PAUSED', 'PAUSED_PRIMARY_BRIDGE'):
        state, message = 'PAUSED', '同步已暂停'
    elif category == 'auth':
        state, message = 'NEEDS_REAUTH', '需要更新登录或授权'
    elif category == 'rate_limit':
        state, message = 'RATE_LIMITED', '等待服务允许重试'
    elif src.get('sync_status') == 'SYNCING' or status == 'CONNECTING':
        state, message = 'CONNECTING', '正在同步'
    elif error or status in ('ERROR', 'RETRY_WAIT'):
        state, message = 'RETRY_WAIT', '暂未连接，将自动重试'
    elif status == 'CONNECTED':
        state, message = 'CONNECTED', '已连接'
    elif status in ('DISCONNECTED', 'NOT_CONNECTED'):
        state, message = 'DISCONNECTED', '未连接'
    if src.get('transport') == 'phone_agent' and state == 'CONNECTED':
        message = '手机可访问 · 腕带' + ('已连接' if src.get('device_connected') else '未连接')
    result = {'id': name, 'instance_key': key, 'name': _text(src.get('display_name') or NAMES.get(name, name)),
              'transport': src.get('transport') or 'cloud', 'state': state, 'message': message,
              'reason_code': reason, 'retry_category': category, 'hint': hint,
              'last_read_at': src.get('last_read_at'), 'last_success_at': src.get('last_pull_at') or src.get('last_success'),
              'next_retry_at': src.get('next_attempt') or src.get('retry_at'), 'actions': ['details'],
              'detail_url': '/?' + urlencode({'view': 'device-connections', 'device': name, 'key': key})}
    if name in NAMES and state not in ('PAUSED', 'NEEDS_REAUTH', 'RATE_LIMITED', 'CONNECTING', 'DISCONNECTED'):
        result['actions'].insert(0, 'retry')
    return result


def snapshot(app, source_reader):
    primary = False  # The distribution does not provide the native bridge.
    target = app.config.get('band_instance_key') if primary else None
    rows, errors = [], []
    for key, inst in app.trial.instances(app).items():
        try:
            sources = source_reader(inst)
        except Exception:
            errors.append({'code': 'SOURCE_STATUS_UNAVAILABLE', 'instance_key': key})
            continue
        for name, src in sources.items():
            if not isinstance(src, dict) or 'status' not in src:
                continue
            if name == 'somaloop' and (primary or src.get('transport') != 'phone_agent'):
                continue
            row = _row(key, name, src)
            # These existing workers are bound to their admission target, not to
            # a scene that happens to contain an old source registration.
            if name in ('oura', 'garmin', 'qkeer', 'somaloop'):
                provider = 'somaloop_agent' if name == 'somaloop' else name
                if key != device_targets.configured_key(app, provider):
                    row['actions'] = ['details']
                    if name == 'oura':
                        row.update(state='UNCONFIRMED', message='尚未配置', hint='')
            if name != 'oura' or not app.trial.oura or key != app.trial.target:
                row['actions'] = ['details']
                if name == 'oura': row.update(state='UNCONFIRMED', message='尚未配置', hint='')
            rows.append(row)
    if primary:
        band = getattr(app, '_band', None)
        state = dict(getattr(band, 'status', {}) or {})
        alive = bool(state.get('at') and time.time() - state['at'] < 90)
        ready = alive and state.get('connection') == 'ready'
        paused = app.config.get('band_paused') is True
        row = _row(target or '', 'somaloop', {'transport': 'band_bridge', 'status': 'CONNECTED' if ready else 'CONNECTING'})
        row.update(state='PAUSED' if paused else 'CONNECTED' if ready else 'WAITING_DEVICE',
                   message='采集已暂停' if paused else '已连接 · Mac 蓝牙' if ready else '等待腕带桥或设备',
                   last_read_at=state.get('last_read_at'), last_success_at=state.get('last_saved_at'),
                   pending_formal=len(getattr(band, 'pending', [])), pending_delivery=state.get('queued'),
                   actions=['details'] if paused or target not in app.instances else ['retry', 'details'])
        row.update(reason_code='BAND_PAUSED' if paused else None, retry_category='paused' if paused else None,
                   hint='请在连接设置中确认后恢复采集。' if paused else '' if ready else '请将腕带唤醒并靠近 Mac，断开手机对腕带的占用，再点击重新连接。')
        if state.get('data_policy') == 'daily':
            row['data_policy'] = 'daily'
            row['last_daily_saved_at'] = state.get('last_daily_saved_at')
            if ready and not paused:
                row['message'] = '已连接 · 实时只读'
                row['hint'] = '最近读数供小尾巴显示，不保存逐点历史；每天结束后归档收到的样本汇总。'
        if not paused and state.get('save_error'):
            row.update(state='SAVE_PENDING', message='已接收，等待保存；记录仍在本机',
                       reason_code='BAND_FORMAL_SAVE_FAILED', retry_category='blocked',
                       hint='待保存记录保留在本机；请检查个人基座可用性后重试，不要删除腕带桥待发送记录。')
        elif not paused and not ready and state.get('note') == 'permissionDenied':
            row.update(state='NEEDS_PERMISSION', message='需要蓝牙权限，请在系统设置中允许',
                       reason_code='BLUETOOTH_PERMISSION_REQUIRED', retry_category='blocked',
                       hint='请在系统设置的隐私与安全性中允许腕带桥使用蓝牙，再重新连接。')
        elif not paused and not ready and state.get('note') == 'bluetoothUnavailable':
            row.update(state='WAITING_BLUETOOTH', message='蓝牙暂不可用，请检查 Mac 蓝牙开关',
                       reason_code='BLUETOOTH_UNAVAILABLE', retry_category='blocked',
                       hint='请打开 Mac 蓝牙并等待系统恢复可用，再重新连接。')
        rows.append(row)
    return {'devices': rows, 'errors': errors}


def retry(app, body, source_reader, oura_retry=None, bridge_retry=None):
    if not isinstance(body, dict) or set(body) != {'id', 'instance_key', 'action'} or body.get('action') != 'retry':
        raise ValueError('DEVICE_ACTION_INVALID')
    device, key = body['id'], body['instance_key']
    if not isinstance(device, str) or not isinstance(key, str):
        raise ValueError('DEVICE_ACTION_INVALID')
    row = next((r for r in snapshot(app, source_reader)['devices'] if r['id'] == device and r['instance_key'] == key), None)
    if not row or 'retry' not in row['actions']:
        raise ValueError('DEVICE_ACTION_REQUIRED')
    token = (id(app), key, device)
    with _lock:
        if token in _inflight:
            return {'ok': True, 'status': 'already_running'}
        _inflight.add(token)
    try:
        if device == 'somaloop' and row['transport'] == 'band_bridge':
            if bridge_retry is not None:
                bridge_retry()
            return app.band().request_reconnect()
        if device == 'oura':
            if oura_retry is None:
                raise ValueError('DEVICE_RETRY_UNSUPPORTED')
            return oura_retry(app.inst(key))
        from background.control import retry_device
        return retry_device('somaloop-agent' if device == 'somaloop' else device)
    finally:
        with _lock:
            _inflight.discard(token)
