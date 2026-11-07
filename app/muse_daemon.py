"""User-enabled, local Muse acquisition. Continuous connection, sealed partial segments.

Uses the pinned SDK/backend and bundle implementation; never claims a chunk is
an ended device session. Existing Muse Store remains the formal visibility point.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import threading
import time
from types import SimpleNamespace
import unicodedata
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import muse_sessions as assets


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic(path, value):
    assets._safe_path(path)
    temporary = path.with_name('.pending-' + uuid.uuid4().hex)
    data = assets._canonical(value)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as out:
        out.write(data)
        out.flush()
        os.fsync(out.fileno())
    os.replace(temporary, path)
    assets._sync_dir(path.parent)


def component():
    assets._component_check()
    if str(assets.COMPONENT) not in sys.path:
        sys.path.insert(0, str(assets.COMPONENT))
    from muse_atom import contracts
    from muse_atom.bundle import BundleWriter
    from muse_atom.worker import _load_backend
    from muse_atom.cli import exclusive_lock
    return contracts.DEFAULT_PROFILE, BundleWriter, _load_backend, exclusive_lock


class Daemon:
    def __init__(self, config, backend=None):
        self.config = config
        self.root = assets._safe_path(Path(config['runtime_root']))
        assets._private_dir(self.root)
        for name in ('segments', 'journals', 'connections', 'locks'):
            assets._private_dir(self.root / name)
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.paused = not config.get('enabled', False)
        self.mutex = threading.Lock()
        self.profile, self.Writer, default_backend, self.exclusive = component()
        self.backend = backend or default_backend
        self.auth = config['authorization']
        if (self.auth.get('device_name') != config['device_name']
                or self.auth.get('continuous_capture_and_save') is not True):
            raise ValueError('Explicit device-bound continuous authorization required')
        self.auth_hash = hashlib.sha256(assets._canonical(self.auth)).hexdigest()
        self.chunk_seconds = config['segment_seconds']
        if type(self.chunk_seconds) is not int or not 30 <= self.chunk_seconds <= 120:
            raise ValueError('segment_seconds must be 30..120')
        instance_root = assets._safe_path(Path(config['instance_root']))
        if not instance_root.is_dir():
            raise ValueError('Existing selected instance required')
        if (self.auth.get('instance_id') != config['instance_id']
                or self.auth.get('instance_root') != str(instance_root)):
            raise ValueError('Authorization must bind exactly one target instance')
        metadata = json.loads(assets._read(instance_root / 'instance.json'))
        if metadata.get('instance_id') != config['instance_id']:
            raise ValueError('Target instance metadata differs')
        self.target_name = metadata.get('display_name') or config['instance_id']
        inst = SimpleNamespace(ctx=SimpleNamespace(root=instance_root,
            instance_id=config['instance_id'], accept=metadata.get('data_policy', {}).get('accept', [])), spec={'replay': False}, now=now)
        self.store = assets.Store(inst)
        self.state = {}
        self.update('STARTING')

    def update(self, state, **extra):
        with self.mutex:
            self.state.update(state=state, device=self.config['device_name'], updated_at=now(),
                              target_instance_id=self.config['instance_id'], target_instance_name=self.target_name,
                              pid=os.getpid(), enabled=not self.paused, **extra)
            atomic(self.root / 'status.json', self.state)

    def enabled(self, enabled):
        with self.mutex:
            self.config['enabled'] = enabled
            atomic(Path(self.config['config_path']), self.config)
            self.paused = not enabled
        self.wake.set()

    def new_segment(self, connection_id):
        sid = uuid.uuid4().hex
        directory = self.root / 'segments' / sid
        assets._private_dir(directory)
        request = dict(schema_version='muse-capture-request/1', session_id=sid,
                       request_id='continuous-' + sid, profile='muse-s-athena', mode='real',
                       data_nature='REAL', device_name=self.config['device_name'],
                       duration_seconds=self.chunk_seconds,
                       operation_context={'profile': 'ptds-continuous-muse/1',
                                          'target_instance_id': self.config['instance_id'],
                                          'authorization_sha256': self.auth_hash})
        atomic(directory / 'request.json', request)
        writer = self.Writer(directory, request, {'component': 'ptds-muse-continuous/1',
                            'brainflow_required': '5.23.0', 'connection_id': connection_id})
        return writer

    def seal(self, writer, lifecycle, reason, errors=None):
        counts = {name: stream['observation'].samples for name, stream in writer.streams.items()}
        manifest = writer.finalize('PARTIAL', lifecycle, errors or [], runtime={
            'fixture_only': False, 'segment_sealed': True, 'segment_reason': reason,
            'authorization_sha256': self.auth_hash, 'connection_continues': reason == 'rotation',
            'professional_or_medical_validation': 'NOT_RUN'})
        # A segment is sealed while the native connection may remain open.
        # Do not forge WORKER_EXITED or stop/release success for this case.
        atomic(writer.directory / 'supervisor.json', {'status': 'CHUNK_SEALED',
            'ended_at': now(), 'manifest_sha256': hashlib.sha256(
                (writer.directory / 'manifest.json').read_bytes()).hexdigest()})
        if any(counts.values()):
            receipt = self.admit(writer.directory)
            self.update('RECORDING' if reason == 'rotation' else 'DISCONNECTED',
                        last_saved_at=receipt['saved_at'], last_asset_id=receipt['asset_id'],
                        last_counts=counts, last_segment_reason=reason,
                        quality='UNVALIDATED', streams=manifest['streams'])

    def admit(self, directory):
        sid = directory.name
        journal = self.root / 'journals' / (sid + '.json')
        record = json.loads(journal.read_text()) if journal.exists() else None
        if record is None:
            files = {p.name: assets._read(p) for p in directory.iterdir()}
            review = self.store.prepare(files)
            record = {'review_id': review['review_id'], 'review_sha256': review['review_sha256'],
                      'request_id': 'auto-save-' + sid, 'authorization_sha256': self.auth_hash}
            atomic(journal, record)
        if record['authorization_sha256'] != self.auth_hash:
            raise ValueError('Authorization differs from pending segment')
        original = self.store.request(record['request_id'])
        if original['status'] == 'SAVED':
            return original['receipt']
        # Same immutable review and same request are used after any uncertain response.
        return self.store.save(record['review_id'], record['request_id'], record['review_sha256'])

    def recover(self):
        for path in sorted((self.root / 'segments').iterdir()):
            assets._safe_path(path)
            if not (path / 'supervisor.json').exists():
                continue  # Interrupted unsealed bytes retained, never declared committed.
            manifest = json.loads(assets._read(path / 'manifest.json'))
            if (manifest['runtime'].get('authorization_sha256') == self.auth_hash
                    and any(s.get('samples', 0) for s in manifest['streams'].values())):
                self.admit(path)

    def connection(self):
        cid = uuid.uuid4().hex
        logdir = self.root / 'connections' / cid
        assets._private_dir(logdir)
        board = writer = None
        lifecycle = dict.fromkeys(('prepare', 'start', 'stop', 'release'), 'NOT_RUN')
        reason, errors = 'stopped', []
        try:
            self.update('CONNECTING', error=None, connection_id=cid)
            board, layouts = self.backend({'device_name': self.config['device_name']}, logdir)
            lifecycle['prepare'] = 'ATTEMPTED'
            board.prepare_session()
            lifecycle['prepare'] = 'OK'
            if self.stop.is_set() or self.paused:
                return
            lifecycle['start'] = 'ATTEMPTED'
            board.start_stream(60000)
            lifecycle['start'] = 'OK'
            self.update('RECORDING', connected_at=now())
            latest = {name: time.monotonic() for name in self.profile['streams']}
            while not self.stop.is_set() and not self.paused:
                if writer is None:
                    if shutil.disk_usage(self.root).free < self.config['minimum_free_bytes']:
                        raise RuntimeError('LOW_DISK_SPACE')
                    writer = self.new_segment(cid)
                    for name, spec in self.profile['streams'].items():
                        writer.configure_stream(name, layouts[name], board.get_board_sampling_rate(spec['preset']))
                    started = time.monotonic()
                for name, spec in self.profile['streams'].items():
                    data = board.get_board_data(preset=spec['preset'])
                    if len(data.shape) != 2 or data.shape[0] != spec['layout']['num_rows']:
                        raise ValueError('SDK_DATA_SHAPE')
                    rows = data.T.tolist()
                    if rows:
                        writer.append(name, rows)
                        latest[name] = time.monotonic()
                if time.monotonic() - min(latest.values()) > self.config['no_data_seconds']:
                    raise RuntimeError('STREAM_DATA_TIMEOUT')
                if time.monotonic() - started >= self.chunk_seconds:
                    sealing, writer = writer, None
                    self.seal(sealing, lifecycle.copy(), 'rotation')
                self.wake.wait(0.25)
                self.wake.clear()
        except Exception as exc:
            reason = 'interrupted'
            errors.append({'type': type(exc).__name__, 'message': str(exc)[:250]})
            if type(exc).__name__ != 'BrainFlowError' and str(exc) != 'STREAM_DATA_TIMEOUT':
                self.enabled(False)
            self.update('WAITING_DEVICE', error=errors[-1])
        finally:
            if board is not None:
                for operation, function in [('stop', board.stop_stream), ('release', board.release_session)]:
                    if lifecycle['start' if operation == 'stop' else 'prepare'] == 'NOT_RUN':
                        continue
                    lifecycle[operation] = 'ATTEMPTED'
                    try:
                        function()
                        lifecycle[operation] = 'OK'
                        if operation == 'stop' and writer is not None and not writer.closed:
                            for name, spec in self.profile['streams'].items():
                                rows = board.get_board_data(preset=spec['preset']).T.tolist()
                                if rows:
                                    writer.append(name, rows)
                    except Exception as exc:
                        lifecycle[operation] = 'FAILED'
                        errors.append({'type': type(exc).__name__, 'stage': operation})
                        self.enabled(False)
            if writer is not None and not writer.closed:
                self.seal(writer, lifecycle, reason, errors)
            atomic(logdir / 'lifecycle.json', {'ended_at': now(), 'lifecycle': lifecycle, 'errors': errors})

    def run(self):
        key = 'device:muse-s-athena:' + unicodedata.normalize('NFC', self.config['device_name']).casefold()
        with ExitStack() as stack:
            stack.enter_context(self.exclusive(self.root / 'locks', 'continuous-service'))
            stack.enter_context(self.exclusive(Path(self.config['device_lock_root']), key))
            self.recover()
            while not self.stop.is_set():
                if self.paused:
                    self.update('PAUSED')
                else:
                    self.connection()
                    if not self.stop.is_set() and not self.paused:
                        self.update('WAITING_DEVICE')
                self.wake.wait(self.config['retry_seconds'])
                self.wake.clear()
            self.update('STOPPED')


def serve(daemon):
    port = daemon.config['control_port']
    origin = 'http://127.0.0.1:' + str(port)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def send(self, status, data, content_type='application/json'):
            self.send_response(status)
            self.send_header('Content-Type', content_type + '; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'")
            self.end_headers()
            self.wfile.write(data.encode())
        def allowed(self):
            return self.headers.get('Host') == '127.0.0.1:' + str(port)
        def do_GET(self):
            if not self.allowed():
                return self.send(403, '{}')
            if self.path == '/status':
                with daemon.mutex:
                    data = dict(daemon.state)
                return self.send(200, json.dumps(data, ensure_ascii=False))
            if self.path != '/':
                return self.send(404, '{}')
            import html
            self.send(200, PAGE.replace('VIEWER_URL', html.escape(daemon.config['viewer_url'], quote=True)), 'text/html')
        def do_POST(self):
            if (not self.allowed() or self.headers.get('Origin') != origin
                    or self.headers.get('X-PTDS-Muse') != 'control'):
                return self.send(403, '{}')
            if self.path not in ('/pause', '/resume'):
                return self.send(404, '{}')
            daemon.enabled(self.path == '/resume')
            self.send(200, '{"ok":true}')
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


PAGE = '''<!doctype html><meta charset="utf-8"><title>Muse 自动入库</title>
<style>body{font:18px system-ui;max-width:760px;margin:50px auto;background:#faf9f5;color:#202638}button,a{padding:12px;margin:8px;display:inline-block}pre{white-space:pre-wrap;font:16px system-ui}</style>
<h1>Muse 自动入库</h1><p>设备开机后自动连接。关闭此网页不停止采集；Mac 需保持唤醒、蓝牙开启。</p>
<h2 id="state">读取状态…</h2><pre id="details"></pre>
<button onclick="control('pause')">暂停自动采集</button><button onclick="control('resume')">恢复自动采集</button>
<a href="VIEWER_URL" target="_blank">打开已保存数据</a>
<p>按约一分钟分段保存；断连后的短段也保留。信号质量尚未验证，原始数据不参与医学判断。</p>
<script>const names={STARTING:'正在启动',CONNECTING:'正在连接设备',RECORDING:'正在采集',WAITING_DEVICE:'等待设备开机／重连',PAUSED:'已暂停',STOPPED:'已停止'};
async function refresh(){try{let s=await(await fetch('/status')).json();document.getElementById('state').textContent=names[s.state]||s.state;let err=!s.error?'无':s.error.type==='BrainFlowError'?'设备尚未就绪，请确认开机、距离和其他应用占用':s.error.message==='LOW_DISK_SPACE'?'磁盘剩余空间不足，已暂停':'采集异常，请查看本机日志';document.getElementById('details').textContent='唯一写入库：'+s.target_instance_name+'\\n设备：'+s.device+'\\n最近保存：'+(s.last_saved_at?new Date(s.last_saved_at).toLocaleString():'尚无')+'\\n最近一段样本数：'+Object.entries(s.last_counts||{}).map(([k,v])=>({eeg:'脑电',imu:'运动',optical:'光学'}[k]||k)+' '+v).join('，')+'\\n提示：'+err;}catch(e){document.getElementById('state').textContent='采集服务不可达';}}
async function control(x){await fetch('/'+x,{method:'POST',headers:{'X-PTDS-Muse':'control'}});refresh();}refresh();setInterval(refresh,2000);</script>'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    config = json.loads(assets._read(args.config.absolute()))
    config['config_path'] = str(args.config.absolute())
    daemon = Daemon(config)
    def stop(*_):
        daemon.stop.set()
        daemon.wake.set()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    server = serve(daemon)
    try:
        daemon.run()
    finally:
        server.shutdown()


if __name__ == '__main__':
    main()
