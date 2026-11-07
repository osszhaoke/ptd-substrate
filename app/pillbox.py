"""Explicit local Hi-PB1 connection; no acquisition at startup or clinical writes.

An owned stdio child is the only transport. HTTP clients cannot submit readings,
raw BLE bytes, arbitrary executables or reminder commands. Battery uses BAS or the device-verified Hi-PB1 / 0.47 QUERY04 profile.
Other proprietary layouts remain unknown.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import plistlib
import queue
import subprocess
import sys
import threading
import time
import uuid

SOURCE = Path(__file__).with_name('pillbox_bridge') / 'PillboxBridge.swift'
PROFILE = 'hi-pb1-0.47'
class PillboxError(ValueError): pass


def build(root):
    if sys.platform != 'darwin': raise PillboxError('药盒连接需要在这台 Mac 上操作')
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()[:20]
    bundle = Path(root) / 'pillbox-bridge' / digest / 'PTDSPillboxBridge.app'
    exe = bundle / 'Contents/MacOS/PTDSPillboxBridge'
    if not exe.exists():
        exe.parent.mkdir(parents=True, exist_ok=True)
        temp = exe.with_suffix('.building')
        try:
            subprocess.run(['/usr/bin/xcrun','swiftc',str(SOURCE),'-o',str(temp),'-framework','AppKit','-framework','CoreBluetooth'],capture_output=True,check=True,timeout=90)
        except (OSError,subprocess.SubprocessError) as exc: raise PillboxError('药盒桥构建失败，请检查本机 Swift 工具') from exc
        (bundle/'Contents/Info.plist').write_bytes(plistlib.dumps({
            'CFBundleIdentifier':'local.ptds.pillboxbridge','CFBundleExecutable':'PTDSPillboxBridge',
            'CFBundleName':'PTDS Pillbox Bridge','CFBundlePackageType':'APPL','LSUIElement':True,
            'NSBluetoothAlwaysUsageDescription':'仅在你点击查找、连接后接入自己的药盒，用于读取电量和主动响铃寻找。',
            'NSBluetoothPeripheralUsageDescription':'读取我的药盒电量并按本人操作响铃寻找。'}))
        os.replace(temp,exe)
    return exe


class Transport:
    def __init__(self, root):
        self.process = subprocess.Popen([str(build(root))],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,bufsize=1)
        self.replies=queue.Queue()
        def read():
            try:
                for line in self.process.stdout:
                    if len(line)>8192: continue
                    try: self.replies.put(json.loads(line))
                    except (ValueError,TypeError): pass
            finally: self.replies.put(None)
        threading.Thread(target=read,daemon=True).start()
    def request(self, op, **data):
        key=uuid.uuid4().hex
        if self.process.poll() is not None: raise PillboxError('药盒连接已停止')
        self.process.stdin.write(json.dumps(dict(data,id=key,op=op))+'\n'); self.process.stdin.flush()
        deadline=time.monotonic()+15
        while True:
            try: reply=self.replies.get(timeout=max(.01,deadline-time.monotonic()))
            except queue.Empty: raise PillboxError('药盒操作超时；请重新连接')
            if reply is None: raise PillboxError('药盒连接已停止')
            if not isinstance(reply,dict) or reply.get('id')!=key:
                if time.monotonic()>=deadline: raise PillboxError('药盒操作超时')
                continue
            if not reply.get('ok'): raise PillboxError(str(reply.get('detail') or '药盒操作失败')[:120])
            return reply
    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try: self.process.wait(timeout=2)
            except subprocess.TimeoutExpired: self.process.kill(); self.process.wait(timeout=2)
        for f in (self.process.stdin,self.process.stdout):
            if f: f.close()


class Manager:
    def __init__(self, root, *, factory=None, clock=time.monotonic):
        self.root=Path(root); self.factory=factory or (lambda:Transport(self.root)); self.clock=clock
        self.native_required = factory is None
        self.lock=threading.RLock(); self.transport=None; self.owner=None; self.candidates={}; self.last_find=None
    def _drop(self):
        t,self.transport=self.transport,None
        if t: t.close()
        self.owner=None; self.candidates={}; self.last_find=None
    def _request(self,op,**data):
        try: return self.transport.request(op,**data)
        except Exception as exc:
            self._drop()
            raise PillboxError(str(exc)[:120] if isinstance(exc,PillboxError) else '药盒连接已中断') from exc
    def scan(self,key):
        with self.lock:
            if self.owner not in (None,key): raise PillboxError('药盒由另一基座连接，请先在那里断开')
            if self.transport is None: self.transport=self.factory()
            self.owner=key
            reply=self._request('scan'); rows=[]
            for x in reply.get('candidates',[]):
                if isinstance(x,dict) and isinstance(x.get('device_id'),str) and isinstance(x.get('name'),str) and x['name'].startswith('Hi-PB1'):
                    try: uuid.UUID(x['device_id'])
                    except ValueError: continue
                    rows.append({'device_id':x['device_id'],'name':x['name'][:60]})
            self.candidates={x['device_id']:self.clock() for x in rows}
            return {'candidates':rows,'profile':PROFILE}
    def connect(self,key,device_id,confirmed):
        with self.lock:
            if confirmed is not True: raise PillboxError('请先确认药盒型号及协议范围')
            if self.owner!=key or self.transport is None or device_id not in self.candidates or self.clock()-self.candidates[device_id]>60:
                raise PillboxError('请重新查找并选择药盒')
            self._request('connect',device_id=device_id)
            return self.status(key)
    def status(self,key):
        with self.lock:
            base={'device':'pillbox','name':'我的药盒','connected':False,'battery':None,'battery_at':None,'battery_source':None,'selected':self.owner==key,'profile':PROFILE}
            if self.native_required and not SOURCE.is_file(): return dict(base,message='状态暂不可用')
            if self.owner!=key or self.transport is None: return base
            try: r=self._request('status')
            except PillboxError as exc: return dict(base,selected=False,detail=str(exc))
            connected=r.get('connected') is True
            b=r.get('battery'); stamp=r.get('battery_at')
            source=r.get('battery_source')
            verified_source=source=='GATT_BAS_2A19' or (source=='HI_PB1_QUERY04_V047' and r.get('firmware')=='0.47')
            valid=(connected and verified_source and type(b) is int and 0<=b<=100 and type(stamp) in (int,float) and 0<=time.time()-stamp<=180)
            return dict(base,connected=connected,battery=b if valid else None,battery_at=stamp if valid else None,battery_source=source if valid else None,firmware=str(r.get('firmware') or '')[:32])
    def find(self,key):
        with self.lock:
            if not self.status(key)['connected']: raise PillboxError('未连接，请先连接药盒')
            now=self.clock()
            if self.last_find is not None and now-self.last_find<3: raise PillboxError('请稍候再试，避免重复响铃')
            self.last_find=now
            r=self._request('find')
            result=r.get('result')
            if result not in ('sent','submitted'): raise PillboxError('寻找结果未知，请确认药盒响应后再操作')
            return {'ok':True,'result':result,'detail':'寻找指令已发送' if result=='sent' else '寻找指令已提交，响铃未确认'}
    def disconnect(self,key):
        with self.lock:
            if self.owner not in (None,key): raise PillboxError('请从连接药盒的基座操作')
            self._drop();return {'ok':True}
    def close(self):
        with self.lock: self._drop()


def handle_http(handler, app, method, path, query):
    """Narrow same-origin local endpoints; never mounted on the phone gateway."""
    if not path.startswith('/api/pillbox/') and path!='/api/desktop-tail/find': return False
    import phone_tail
    if not phone_tail.local_control_allowed(handler):
        handler._json(403,{'error':'LOCAL_ONLY'});return True
    try:
        if method=='GET' and path=='/api/pillbox/status':
            key=query.get('key'); inst=app.instances.get(key)
            if inst is None or inst.spec.get('replay'): raise PillboxError('请选择可连接设备的基座')
            handler._json(200,app.pillbox.status(key));return True
        if method!='POST' or path not in ('/api/pillbox/scan','/api/pillbox/connect','/api/pillbox/disconnect','/api/pillbox/find','/api/desktop-tail/find'):
            handler._json(404,{'error':'NOT_FOUND'});return True
        size=int(handler.headers.get('Content-Length') or 0)
        if not 1<=size<=2048 or handler.headers.get('Transfer-Encoding'):
            handler._json(413,{'error':'BODY_TOO_LARGE'});return True
        body=json.loads(handler.rfile.read(size))
        if not isinstance(body,dict): raise PillboxError('请求格式不正确')
        if path=='/api/desktop-tail/find': result=app.desktop_panels.find(query.get('panel'))
        else:
            key=body.get('key');inst=app.instances.get(key) if isinstance(key,str) else None
            if inst is None or inst.spec.get('replay'): raise PillboxError('请选择可连接设备的基座')
            if app.pillbox.status(key).get('message') == '状态暂不可用': raise PillboxError('状态暂不可用')
            op=path.rsplit('/',1)[-1]
            if op=='scan': result=app.pillbox.scan(key)
            elif op=='connect':
                device=body.get('device_id')
                if not isinstance(device,str): raise PillboxError('请选择查找到的药盒')
                result=app.pillbox.connect(key,device,body.get('confirmed'))
            elif op=='disconnect': result=app.pillbox.disconnect(key)
            else: result=app.pillbox.find(key)
        handler._json(200,result)
    except (ValueError,TypeError,OSError) as exc:
        handler._json(400,{'error':'PILLBOX_UNAVAILABLE','detail':str(exc)[:160]})
    return True
