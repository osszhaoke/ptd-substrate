"""Opt-in read-only HTTPS gateway. No database, device control, or generic proxy.

Only the local product controls pairing. The LAN handler receives a display
snapshot callback, never the application or its stores. Sessions live in memory.
"""
from __future__ import annotations

from contextlib import nullcontext
import uuid
import base64
from collections import deque
import copy
import errno
import hashlib
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import math
from pathlib import Path
import re
import secrets
import socket
import os
import ssl
import subprocess
import threading
import time
from urllib.parse import urlsplit
from datetime import datetime
from zoneinfo import ZoneInfo

import desktop_tail
import guest_band
import phone_tail_auth as auth
import phone_lifecycle
from h1_common import H1Error

ROOT = Path(__file__).parent
DEFAULTS = {"port": 8791, "poll_seconds": 3, "pair_seconds": 180, "session_seconds": 3600}
COOKIE = "__Host-PTDSTail"


class ViewerError(ValueError):
    pass


def settings(config):
    if config is not None and not isinstance(config, dict):
        raise ViewerError("手机查看配置需要一个对象")
    cfg = dict(DEFAULTS, **(config or {}))
    required = ("bind_host", "public_origin", "cert_file", "key_file") + (("origin_server_name",) if cfg.get("deployment_mode") == "quick_tunnel" else ())
    missing = [k for k in required if not cfg.get(k)]
    if missing:
        labels = {"bind_host": "Mac 内网地址", "public_origin": "加密访问地址", "cert_file": "HTTPS 证书", "key_file": "证书私钥", "origin_server_name": "本机网关 TLS 身份"}
        raise ViewerError("手机查看尚未配置：" + "、".join(labels[k] for k in missing))
    try:
        cfg.setdefault("max_viewers", 1)
        for k, lo, hi in (("port", 1024, 65535), ("poll_seconds", 1, 10), ("pair_seconds", 30, 300), ("session_seconds", 60, 28800), ("max_viewers", 1, 5)):
            if type(cfg[k]) is not int or not lo <= cfg[k] <= hi:
                raise ValueError()
        mode = cfg.get("deployment_mode", "lan")
        address = ipaddress.ip_address(cfg["bind_host"])
        local = address.is_loopback or any(address in ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))
        if address.version != 4 or not local or address.is_unspecified or mode not in ("lan", "tunnel", "quick_tunnel"):
            raise ValueError()
        origin = urlsplit(cfg["public_origin"])
        hostname = origin.hostname or ""
        external_port = origin.port or 443
        # Public QR, Host and Origin share one canonical identity. Quick Tunnel has a separate local TLS identity.
        canonical = "https://" + hostname + (":" + str(external_port) if external_port != 443 else "")
        if (origin.scheme != "https" or not hostname or origin.username or origin.password
                or origin.path or origin.query or origin.fragment or cfg["public_origin"] != canonical
                or len(hostname) > 253 or not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in hostname.split("."))):
            raise ValueError()
        try:
            origin_ip = ipaddress.ip_address(hostname)
        except ValueError:
            origin_ip = None
        if mode == "lan":
            if external_port != cfg["port"] or (origin_ip is not None and origin_ip != address):
                raise ValueError()
        elif mode == "quick_tunnel":
            local_name = cfg["origin_server_name"]
            if (not isinstance(local_name, str) or len(local_name) > 253
                    or not local_name.endswith(".localhost")
                    or not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in local_name.split("."))):
                raise ValueError()
            if (str(address) != "127.0.0.1" or external_port != 443 or cfg["port"] == 8780
                    or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.trycloudflare\.com", hostname)):
                raise ValueError()
        elif (not address.is_loopback or external_port != 443 or origin_ip is not None
              or "." not in hostname or cfg["port"] == 8780):
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise ViewerError("请核对指定的私网 IPv4 与 HTTPS 地址；局域网端口须一致，隧道须绑定本机回环及独立端口") from None
    lease_file, lease_id = cfg.get("tunnel_lease_file"), cfg.get("tunnel_lease_id")
    if lease_file is not None or lease_id is not None:
        if (mode != "quick_tunnel" or not isinstance(lease_file, str)
                or not Path(lease_file).is_absolute() or not isinstance(lease_id, str)
                or not re.fullmatch(r"[a-zA-Z0-9_-]{32,64}", lease_id)):
            raise ViewerError("Wi-Fi 分享通道的运行凭据配置不完整，请重新准备通道")
    cfg.update(host=origin.netloc, hostname=hostname, deployment_mode=mode)
    return cfg


def check_tunnel_lease(cfg):
    """Fail closed for supervised Quick Tunnels; no health data or remote probes.

    A fresh local heartbeat proves only the supervised processes are alive,
    never public reachability. Legacy LAN and isolated deployments are unchanged.
    """
    if not cfg.get("tunnel_lease_file"):
        return
    try:
        with Path(cfg["tunnel_lease_file"]).open("rb") as stream:
            raw = stream.read(8193)
        if len(raw) > 8192:
            raise ValueError()
        lease = json.loads(raw)
        now = time.time()
        if (not isinstance(lease, dict) or lease.get("schema") != "PTDS_TUNNEL_LEASE_V1"
                or lease.get("lease_id") != cfg["tunnel_lease_id"]
                or lease.get("public_origin") != cfg["public_origin"]
                or lease.get("state") != "ready"):
            raise ValueError()
        for key in ("updated_at", "expires_at"):
            if type(lease.get(key)) not in (int, float) or not math.isfinite(lease[key]):
                raise ValueError()
        if not -2 <= now - lease["updated_at"] <= 15 or lease["expires_at"] <= now:
            raise ValueError()
        for key in ("supervisor_pid", "cloudflared_pid"):
            pid = lease.get(key)
            if type(pid) is not int or not 1 < pid <= 2147483647:
                raise ValueError()
            os.kill(pid, 0)
    except (OSError, ValueError, TypeError, KeyError):
        raise ViewerError("本次 Wi-Fi 分享通道已结束或尚未就绪，请重新建立通道后再授权") from None


def check_bind_address(cfg):
    """Check local address ownership; no listener, peer connection or data sent."""
    check_tunnel_lease(cfg)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.bind((cfg["bind_host"], 0))
    except OSError as exc:
        if exc.errno == errno.EADDRNOTAVAIL:
            raise ViewerError("Mac 网络地址已变化，手机分享尚不可用。请连接原网络，或更新内网地址及对应证书后再授权") from None
        raise ViewerError("暂时无法核对 Mac 的手机分享地址，请检查网络后重试") from None


_DNS_SLOT = threading.BoundedSemaphore(1)


def resolve_addresses(host, port, timeout=3):
    """Bound DNS latency and outstanding work; never leave unlimited resolver threads."""
    if not _DNS_SLOT.acquire(blocking=False):
        raise ViewerError("域名解析仍在进行，请稍后重试")
    done, answers, errors = threading.Event(), [], []
    def resolve():
        try:
            answers.extend(socket.getaddrinfo(host, port, type=socket.SOCK_STREAM))
        except OSError as exc:
            errors.append(exc)
        finally:
            _DNS_SLOT.release()
            done.set()
    threading.Thread(target=resolve, daemon=True).start()
    if not done.wait(timeout):
        raise ViewerError("域名解析超时，请核对 DNS 后重试")
    if errors:
        raise ViewerError("无法解析手机访问域名，请先核对 DNS 与现场网络")
    return {row[4][0] for row in answers}

def server_context(cfg):
    """Validate the presented identity, not public-CA trust; clients still verify trust."""
    host = cfg["origin_server_name"] if cfg["deployment_mode"] == "quick_tunnel" else cfg["hostname"]
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if cfg["deployment_mode"] == "lan" and ip is None:
        try:
            resolved = resolve_addresses(host, cfg["port"])
            if host == "localhost" and ipaddress.ip_address(cfg["bind_host"]).is_loopback:
                resolved.discard("::1")
            if resolved != {cfg["bind_host"]}:
                raise ViewerError("访问域名解析与网关绑定地址不一致，请核对 DNS；当前网关仅支持 IPv4")
        except OSError:
            raise ViewerError("无法解析手机访问域名，请先核对 DNS 与现场网络") from None
    try:
        result = subprocess.run(["openssl", "x509", "-in", cfg["cert_file"], "-noout", "-ext", "subjectAltName", "-startdate", "-enddate"],
                                capture_output=True, text=True, check=True, timeout=5, env=dict(os.environ, LC_ALL="C"))
        names = re.findall(r"(DNS|IP Address):([^,\n]+)", result.stdout)
        def matches(kind, value):
            value = value.strip().lower()
            if ip is not None:
                return kind == "IP Address" and ipaddress.ip_address(value) == ip
            return kind == "DNS" and (value == host or (value.startswith("*.") and host.partition(".")[2] == value[2:] and "." in host))
        dates = dict(re.findall(r"(notBefore|notAfter)=([^\n]+)", result.stdout))
        now = time.time()
        if not any(matches(kind, value) for kind, value in names):
            raise ViewerError("HTTPS 证书 SAN 与网关 TLS 域名或地址不匹配")
        if not ssl.cert_time_to_seconds(dates["notBefore"]) <= now < ssl.cert_time_to_seconds(dates["notAfter"]):
            raise ViewerError("HTTPS 证书尚未生效或已到期，请更新证书")
    except (OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
        if isinstance(exc, ViewerError):
            raise
        raise ViewerError("无法核验证书 SAN 和有效期，请检查证书与本机 OpenSSL") from None
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(cfg["cert_file"], cfg["key_file"], password="")
    def check_sni(sock, name, initial):
        # IP clients normally omit SNI; DNS origins must present the exact name.
        if (ip is None and name != host) or (ip is not None and name not in (None, host)):
            return ssl.ALERT_DESCRIPTION_UNRECOGNIZED_NAME
    context.sni_callback = check_sni
    return context


def page_html(nonce, cfg=None):
    fonts = "\n".join(re.findall(r"@font-face\s*\{[^}]*\}", desktop_tail.PRODUCT.read_text()))
    page = (ROOT / "web/phone_tail.html").read_text().replace("/*FONTS*/", fonts).replace("/*COMPONENT*/", desktop_tail.component_js()).replace("NONCE_VALUE", nonce)
    if cfg and cfg.get("deployment_mode") in ("tunnel", "quick_tunnel"):
        page = page.replace("连接与 Mac 相同的 Wi-Fi，输入电脑显示的配对码。", "输入 Mac 显示的配对码，申请临时只读查看。")
        page = page.replace("仅查看 · Mac 后台采集 · 保留每项实际观测时间", "仅查看 · 本次连接经受控 HTTPS 服务转发 · 保留每项实际观测时间")
    if cfg and cfg.get("max_viewers", 1) > 1:
        page = page.replace("数据分享已结束 · 访问授权已撤回。", "本机查看已结束；其他已批准手机不受影响。")
    return page


def qr_png(url, root):
    """macOS system CoreImage; secret URL goes through stdin, never argv/logs."""
    source = ROOT / "tools/PhoneTailQR.swift"
    executable = root / "phone-tail-tools" / (hashlib.sha256(source.read_bytes()).hexdigest()[:16] + "-qr")
    if not executable.exists():
        executable.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["/usr/bin/xcrun", "swiftc", str(source), "-o", str(executable), "-framework", "AppKit", "-framework", "CoreImage"], check=True, capture_output=True, timeout=60)
    return subprocess.run([str(executable)], input=url.encode(), check=True, capture_output=True, timeout=5).stdout


class Viewer:
    """One pending/approved phone. No permissions survive stop or process restart."""
    def __init__(self, cfg, snapshot, clock=time.monotonic, *, authority=None):
        self.cfg, self.snapshot, self.clock = cfg, snapshot, clock
        self.authority, self.ended_at, self.end_reason = authority, None, None
        self.lock = threading.RLock()
        self.active = True
        self.ticket = secrets.token_urlsafe(32)
        self.code = f"{secrets.randbelow(100000000):08d}"
        self.pair_until = clock() + cfg["pair_seconds"]
        self.secret = self.confirmation = None
        self.approved = False
        self.session_until = 0
        self.attempts = 0
        self.traffic = deque()
        self.revision, self.signature = 0, None

    def guard(self):
        return self.authority.lock if self.authority else nullcontext()

    def _check(self, audit=False):
        if self.active:
            try:
                check_tunnel_lease(self.cfg)
            except ViewerError:
                self.end("STOPPED")
                if self.authority and audit:
                    self.authority.check(approved=self.approved, audit=True)
                raise
        if self.authority:
            code, _ = self.authority.check(approved=self.approved, audit=audit)
            if code:
                self.revoke(code if code in auth.REASON_ZH else "OUT_OF_SCOPE")
                raise ViewerError("数据分享已结束 · " + auth.REASON_ZH.get(code, "访问授权已失效"))

    def _expire(self):
        now = self.clock()
        if self.authority and self.active:
            if self.approved and now >= self.session_until:
                self.end("SESSION_EXPIRED")
            elif not self.approved and now >= self.pair_until:
                self.end("PAIR_EXPIRED")
        if self.secret and now >= (self.session_until if self.approved else self.pair_until):
            self.secret = self.confirmation = None
            self.approved = False
        if now >= self.pair_until:
            self.ticket = self.code = None

    def allowed_rate(self):
        with self.guard(), self.lock:
            now = self.clock()
            while self.traffic and self.traffic[0] < now - 10:
                self.traffic.popleft()
            if len(self.traffic) >= 50 + 20 * (self.cfg.get("max_viewers", 1) - 1):
                return False
            self.traffic.append(now)
            return True

    def pair(self, supplied):
        with self.guard(), self.lock:
            self._expire()
            self._check(audit=True)
            if not self.active or not self.ticket or self.secret or self.attempts >= 5:
                raise ViewerError("配对已失效，请在 Mac 重新开启")
            self.attempts += 1
            if not isinstance(supplied, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", supplied) or not (secrets.compare_digest(supplied, self.ticket) or secrets.compare_digest(supplied, self.code)):
                if self.attempts >= 5 and self.authority:
                    self.end("ATTEMPTS")
                raise ViewerError("配对码不正确")
            self.ticket = self.code = None
            self.secret = secrets.token_urlsafe(32)
            self.confirmation = f"{secrets.randbelow(10000):04d}"
            return self.secret

    def access(self, secret):
        with self.guard(), self.lock:
            self._expire()
            self._check(audit=True)
            if not self.active or not self.secret or not isinstance(secret, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", secret) or not secrets.compare_digest(secret, self.secret):
                raise ViewerError("数据分享已结束，请在 Mac 重新配对")
            return self.approved

    def approve(self, confirmation):
        with self.guard(), self.lock:
            self._expire()
            self._check(audit=True)
            if not self.active or not self.secret or self.approved or confirmation != self.confirmation:
                raise ViewerError("待确认手机已变化，请刷新后重试")
            remaining = self.cfg["session_seconds"]
            if self.authority:
                code, seconds = self.authority.approve()
                if code:
                    raise ViewerError("授权已失效，请重新授权")
                remaining = min(remaining, seconds)
            self.approved = True
            self.session_until = self.clock() + remaining

    def end(self, reason):
        with self.guard(), self.lock:
            try:
                if self.authority:
                    self.authority.end(reason)
            finally:
                self.revoke(reason)

    def revoke(self, reason="REVOKED"):
        with self.guard(), self.lock:
            self.ended_at = self.ended_at or self.clock()
            self.end_reason = self.end_reason or reason
            self.active = False
            self.ticket = self.code = self.secret = self.confirmation = None
            self.approved = False

    def status(self):
        with self.guard(), self.lock:
            self._expire()
            if self.active:
                try:
                    self._check()
                except ViewerError:
                    pass
            return {"end_reason": self.end_reason, "running": self.active, "paired": bool(self.secret and self.approved),
                    "pending": self.confirmation if self.secret and not self.approved else None,
                    "pair_seconds": max(0, int(self.pair_until - self.clock())) if self.ticket or (self.secret and not self.approved) else 0,
                    "session_seconds": max(0, int(self.session_until - self.clock())) if self.approved else 0,
                    "pair_url": self.cfg["public_origin"] + "/#" + self.ticket if self.ticket else None,
                    "entry_url": self.cfg["public_origin"] + "/", "pair_code": self.code}

    def data(self, secret):
        # Check again after producing the read-only snapshot: stop/revoke can race.
        if not self.access(secret):
            raise ViewerError("请等待 Mac 确认")
        payload = self.snapshot()
        with self.guard(), self.lock:
            if not self.access(secret):
                raise ViewerError("查看已结束")
            if self.authority:
                self.authority.audit("READ")
            signature = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)
            if signature != self.signature:
                self.signature = signature
                self.revision += 1
            return {"display": payload, "revision": self.revision, "poll_seconds": self.cfg["poll_seconds"],
                    "remaining_seconds": max(0, int(self.session_until - self.clock())), "lease_seconds": 12}

    def phone_status(self, secret):
        approved = self.access(secret)
        return {"approved": approved, "confirmation": self.confirmation if not approved else None}

    def leave(self, secret):
        self.access(secret)
        self.end("PHONE_LEFT")


class MultiViewer(Viewer):
    """Bounded devices under one formal grant; each phone needs local approval."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.devices = {}

    def device_event(self, row, event):
        if self.authority:
            auth.record(self.authority.store, self.authority.gid, row["sid"], event)

    def _expire(self):
        super()._expire()
        for token, row in list(self.devices.items()):
            if self.clock() >= row["until"]:
                self.device_event(row, "DEVICE_LEFT")
                del self.devices[token]

    def pair(self, supplied):
        with self.guard(), self.lock:
            self._expire(); self._check(audit=True)
            if not self.active or not self.ticket or self.attempts >= 5:
                raise ViewerError("配对码已失效，请在 Mac 添加手机")
            if len(self.devices) >= self.cfg["max_viewers"]:
                raise ViewerError("已达到手机数量上限，请先让一台手机结束查看")
            if (not isinstance(supplied, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,100}", supplied)
                    or not (secrets.compare_digest(supplied, self.ticket) or secrets.compare_digest(supplied, self.code))):
                self.attempts += 1
                if self.attempts >= 5:
                    self.ticket = self.code = None
                raise ViewerError("配对码不正确")
            number = f"{secrets.randbelow(10000):04d}"
            while any(r["confirmation"] == number for r in self.devices.values()):
                number = f"{secrets.randbelow(10000):04d}"
            token = secrets.token_urlsafe(32)
            self.devices[token] = dict(sid=uuid.uuid4().hex, confirmation=number, approved=False, until=self.pair_until, last_read=None)
            return token

    def access(self, token):
        with self.guard(), self.lock:
            self._expire(); self._check(audit=True)
            row = self.devices.get(token) if isinstance(token, str) else None
            if not self.active or not row:
                raise ViewerError("本机查看已结束，请在 Mac 重新配对")
            return row["approved"]

    def phone_status(self, token):
        with self.guard(), self.lock:
            approved = self.access(token)
            return {"approved": approved, "confirmation": None if approved else self.devices[token]["confirmation"]}

    def approve(self, confirmation):
        with self.guard(), self.lock:
            self._expire(); self._check(audit=True)
            row = next((r for r in self.devices.values() if not r["approved"] and r["confirmation"] == confirmation), None)
            if not self.active or not row:
                raise ViewerError("待确认手机已变化，请刷新后重试")
            remaining = self.cfg["session_seconds"]
            if self.authority:
                code, seconds = self.authority.approve()
                if code:
                    raise ViewerError("授权已失效，请重新授权")
                remaining = min(remaining, seconds)
            until = self.clock() + remaining
            self.session_until = min(self.session_until, until) if self.approved else until
            self.approved = True
            self.device_event(row, "DEVICE_PAIRED")
            row.update(approved=True, until=self.session_until)

    def invite(self):
        with self.guard(), self.lock:
            self._expire(); self._check()
            if not self.active or len(self.devices) >= self.cfg["max_viewers"]:
                raise ViewerError("已达到手机数量上限或授权已结束")
            self.ticket = secrets.token_urlsafe(32)
            self.code = f"{secrets.randbelow(100000000):08d}"
            self.pair_until = self.clock() + self.cfg["pair_seconds"]
            self.attempts = 0

    def leave(self, token):
        with self.guard(), self.lock:
            self.access(token)
            self.device_event(self.devices[token], "DEVICE_LEFT")
            del self.devices[token]
            if not self.devices:
                self.end("PHONE_LEFT")

    def remove_device(self, sid):
        with self.guard(), self.lock:
            self._expire(); self._check(audit=True)
            token = next((t for t, r in self.devices.items() if r["sid"] == sid), None)
            if not token:
                raise ViewerError("该手机已离开，请刷新列表")
            self.device_event(self.devices[token], "DEVICE_LEFT")
            del self.devices[token]
            # Keep the grant and other phones alive; a new invite may use this slot.

    def revoke(self, reason="REVOKED"):
        with self.guard(), self.lock:
            super().revoke(reason)
            self.devices.clear()

    def status(self):
        with self.guard(), self.lock:
            status = super().status()
            pending = [r for r in self.devices.values() if not r["approved"]]
            count = sum(r["approved"] for r in self.devices.values())
            full = len(self.devices) >= self.cfg["max_viewers"]
            status.update(paired=bool(count), pending=pending[0]["confirmation"] if pending else None,
                          approved_count=count, pending_count=len(pending), max_viewers=self.cfg["max_viewers"],
                          can_invite=self.active and not full)
            rows = []
            for row in self.devices.values():
                last = row.get("last_read")
                age = max(0, self.clock() - last) if last is not None else None
                online = bool(row["approved"] and age is not None and age < 12)
                rows.append({"id": row["sid"], "confirmation": row["confirmation"],
                             "approved": row["approved"], "online": online,
                             "state": "pending" if not row["approved"] else "online" if online else "waiting" if age is None else "offline",
                             "last_read_seconds": None if age is None else int(age)})
            status.update(devices=rows, online_count=sum(r["online"] for r in rows))
            if full:
                status.update(pair_url=None, pair_code=None)
            return status

    def data(self, token):
        payload = super().data(token)
        with self.guard(), self.lock:
            self.access(token)
            self.devices[token]["last_read"] = self.clock()
            self.device_event(self.devices[token], "DEVICE_READ")
        return payload


class Gateway(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False
    request_queue_size = 8

    def __init__(self, address, viewer, context):
        if context is None:
            raise ViewerError("手机网关必须使用经过身份核验的 TLS")
        self.viewer, self.context = viewer, context
        self.slots = threading.BoundedSemaphore(8)
        super().__init__(address, Handler)

    def process_request(self, request, client_address):
        if self.viewer.cfg.get("deployment_mode") in ("tunnel", "quick_tunnel") and not ipaddress.ip_address(client_address[0]).is_loopback:
            request.close()
            return
        if not self.slots.acquire(blocking=False):
            request.close()
            return
        request.settimeout(5)
        try:
            super().process_request(request, client_address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            # Handshake in the bounded worker, never block the accept loop.
            try:
                request = self.context.wrap_socket(request, server_side=True)
                super().process_request_thread(request, client_address)
            except (OSError, ssl.SSLError):
                request.close()
        finally:
            self.slots.release()

    def handle_error(self, request, client_address):
        pass  # Never dump headers, URL credentials or health payloads to logs.


class Handler(BaseHTTPRequestHandler):
    server_version = "PTDS-Phone"

    def log_message(self, *args):
        pass

    def reply(self, status, value, kind="application/json; charset=utf-8", cookie=None, nonce=None):
        body = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        for k, v in {"Content-Type": kind, "Content-Length": str(len(body)), "Cache-Control": "private, no-store, max-age=0",
                     "CDN-Cache-Control": "no-store", "Cloudflare-CDN-Cache-Control": "no-store",
                     "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY",
                     "Permissions-Policy": "camera=(), microphone=(), geolocation=()", "Connection": "close",
                     "Content-Security-Policy": "default-src 'none'; script-src " + ("'nonce-" + nonce + "'" if nonce else "'none'") + "; style-src 'unsafe-inline'; font-src data:; img-src data:; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"}.items():
            self.send_header(k, v)
        if cookie is not None:
            self.send_header("Set-Cookie", f"{COOKIE}={cookie}; Secure; HttpOnly; SameSite=Strict; Path=/" + ("; Max-Age=0" if not cookie else ""))
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def guard(self, post=False):
        cfg = self.server.viewer.cfg
        if (len(self.headers.get_all("Host", [])) != 1 or len(self.headers.get_all("Origin", [])) > 1
                or self.headers.get("Host") != cfg["host"] or self.headers.get("Origin", cfg["public_origin"]) != cfg["public_origin"]
                or self.headers.get("Sec-Fetch-Site") == "cross-site"
                or (post and self.headers.get("Origin") != cfg["public_origin"])):
            self.reply(403, {"detail": "请从配对页面操作"})
            return False
        if self.path != self.requestline.split()[1]:
            self.reply(404, {"detail": "没有此查看入口"})
            return False
        # Proxy headers never grant identity or reset the global request budget.
        if not self.server.viewer.allowed_rate():
            self.reply(429, {"detail": "操作过快，请稍后重试"})
            return False
        return True

    def token(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
            return cookie[COOKIE].value if COOKIE in cookie else ""
        except Exception:
            return ""

    def do_GET(self):
        if not self.guard():
            return
        viewer = self.server.viewer
        if self.path == "/":
            nonce = secrets.token_urlsafe(18)
            return self.reply(200, page_html(nonce, viewer.cfg).encode(), "text/html; charset=utf-8", nonce=nonce)
        if self.path not in ("/status", "/snapshot"):
            return self.reply(404, {"detail": "没有此查看入口"})
        try:
            if self.path == "/status":
                if not self.token():
                    return self.reply(401, {"code": "PAIR_REQUIRED", "detail": "请扫码或输入 Mac 上的配对码"}, cookie="")
                return self.reply(200, viewer.phone_status(self.token()))
            if not viewer.access(self.token()):
                return self.reply(403, {"detail": "请等待 Mac 确认"})
            return self.reply(200, viewer.data(self.token()))
        except ViewerError as exc:
            return self.reply(401, {"code": "SESSION_ENDED", "detail": str(exc)}, cookie="")

        except (H1Error, OSError):
            return self.reply(503, {"detail": "授权暂时无法核验，请在 Mac 查看授权状态"}, cookie="")
        except Exception:
            return self.reply(503, {"detail": "暂时无法读取，保留上次观测"})

    def do_POST(self):
        if not self.guard(post=True):
            return
        if self.path not in ("/pair", "/leave"):
            return self.reply(404, {"detail": "没有此查看入口"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 1 <= size <= 2048 or self.headers.get("Transfer-Encoding") or self.headers.get_content_type() != "application/json":
                return self.reply(400, {"detail": "请求格式不正确"})
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError()
        except (ValueError, TypeError):
            return self.reply(400, {"detail": "请求格式不正确"})
        viewer = self.server.viewer
        try:
            if self.path == "/pair":
                token = viewer.pair(body.get("ticket"))
                return self.reply(200, {"confirmation": viewer.phone_status(token)["confirmation"]}, cookie=token)
            viewer.leave(self.token())
            return self.reply(200, {"ok": True}, cookie="")
        except ViewerError as exc:
            return self.reply(401, {"code": "SESSION_ENDED", "detail": str(exc)}, cookie="")
        except (H1Error, OSError):
            return self.reply(503, {"detail": "授权暂时无法核验，请在 Mac 查看授权状态"}, cookie="")


def local_control_allowed(handler):
    port = handler.server.server_port
    host = handler.headers.get("Host")
    return (handler.client_address[0] in ("127.0.0.1", "::1") and host in (f"127.0.0.1:{port}", f"localhost:{port}")
            and handler.headers.get("Origin", "http://" + host) == "http://" + host
            and handler.headers.get("X-PTDS") == "1")


class Manager:
    def __init__(self, app):
        self.app = app
        self.lock = phone_lifecycle.bind(app)
        self.gateway = self.viewer = self.thread = self.spec = None
        self.qr = None
        self.monitor = None
        # Process restart never restores phone authority or bearer secrets.
        with getattr(app, "lock", nullcontext()), self.lock:
            for inst in app.instances.values():
                if not hasattr(inst, "cluster"):
                    continue
                for grant in inst.cluster.list(auth.now()):
                    if grant["card"] == auth.RESOURCE and grant["status"] in ("ACTIVE", "WAIT_CHANNEL"):
                        inst.cluster.revoke(grant["id"], auth.now(), via="SYSTEM")
                        sid = auth.binding(inst.cluster, grant["id"]) or uuid.uuid4().hex
                        auth.record(inst.cluster, grant["id"], sid, "ENDED", "RESTART")

    def snapshot(self, spec=None):
        spec = self.spec if spec is None else spec
        # Never app.band(): its constructor can replay pending history writes.
        band = getattr(self.app, "_band", None)
        view = band.tail_snapshot() if band is not None else {"status": {"alive": False}, "tiles": [{"kind": k, "latest": None} for k in guest_band.TAIL]}
        display = self.app.desktop_panels.readings(spec, band_view=view)
        tz = ZoneInfo(self.app.instances[spec["key"]].ctx.tz)
        today = datetime.now(tz).date()
        for tile, row in zip(display["tiles"], view["tiles"]):
            latest = row["latest"]
            tile["observed_at"] = datetime.fromtimestamp(latest["at"], tz).isoformat() if latest else None
            if latest:
                dt = datetime.fromtimestamp(latest["at"], tz)
                tile["note"] = dt.strftime("%H:%M" if dt.date() == today else "%Y-%m-%d %H:%M") + " 的读数"
        display.pop("share_key", None)
        display["readOnly"] = True
        display["footer"] = "连续个人读数 · 仅查看 · Mac 后台采集"
        return display

    def current_grant(self):
        if self.viewer and self.viewer.authority:
            a = self.viewer.authority
            return a.key, a.store.find(a.gid, auth.now())
        for key, inst in self.app.instances.items():
            if hasattr(inst, "cluster"):
                for g in inst.cluster.list(auth.now()):
                    if g["card"] == auth.RESOURCE and g["status"] == "ACTIVE":
                        return key, g
        return None, None

    def owner_key(self):
        # Same recipient as App.band(), without initializing the band or reading its store.
        configured = self.app.config.get("band_instance_key")
        if configured:
            return configured if configured in self.app.instances else None
        return None  # Partner sharing never infers an owner from instance order.

    def require_owner(self, key):
        if key != self.owner_key():
            raise ViewerError("请在 Somaloop 当前接收数据的实例中授权")
        band = getattr(self.app, "_band", None)
        if band is not None and Path(band.path).parent.parent != self.app.instances[key].ctx.root:
            raise ViewerError("Somaloop 采集实例与授权实例不一致，未开启分享")

    def create_grant(self, key, form):
        """Called only by the existing formal create route after user confirmation."""
        with self.lock:
            self.require_owner(key)
            cfg = settings(self.app.config.get("phone_tail"))
            check_bind_address(cfg)
            if self.viewer:
                self.viewer.status()  # refresh expiry before deciding whether a new grant may exist
            if self.gateway and not self.viewer.active:
                raise ViewerError("上一项分享正在结束，请稍后重新授权")
            inst = self.app.instances[key]
            inst.cluster._validate(form)
            old_key, existing = self.current_grant()
            if existing and existing["status"] == "ACTIVE":
                if old_key != key:
                    raise ViewerError("已有另一份数据的手机授权，请先在授权详情结束分享")
                return existing
            return inst.cluster.create(form, auth.now())

    def status(self):
        with self.lock:
            mode, max_viewers = None, 1
            try:
                cfg = settings(self.app.config.get("phone_tail"))
                mode = cfg["deployment_mode"]
                max_viewers = cfg["max_viewers"]
                check_bind_address(cfg)
                configured, detail = True, ("Wi-Fi 转发进程已运行，手机连通性仍需核验" if cfg.get("tunnel_lease_file") else "受控 HTTPS 转发参数已填写，尚未核验公开入口" if mode != "lan" else "加密参数已填写，开启时校验；手机仍需信任该证书")
            except ViewerError as exc:
                configured, detail = False, str(exc)
            status = self.viewer.status() if self.viewer else {"running": False}
            key, grant = self.current_grant()
            return dict(status, running=self.gateway is not None, configured=configured, detail=detail, deployment_mode=mode,
                        key=key, owner_key=self.owner_key(), grant=grant, max_viewers=max_viewers, qr=self.qr if status.get("pair_url") else None)

    def start(self, body):
        with self.lock:
            cfg = settings(self.app.config.get("phone_tail"))
            spec = self.app.desktop_panels.validate(body)
            if spec["device"] != "somaloop":
                raise ViewerError("第一版手机查看支持 Somaloop")
            self.require_owner(spec["key"])
            inst = self.app.instances[spec["key"]]
            if not hasattr(inst, "cluster") or not body.get("grant_id"):
                raise ViewerError("请先通过正式授权确认手机查看范围")
            if self.gateway:
                if (self.viewer.active and self.viewer.authority.key == spec["key"]
                        and self.viewer.authority.gid == body["grant_id"]):
                    return self.status()
                raise ViewerError("上一项分享正在结束，请稍后重试")
            authority = auth.Authority(self.app, spec, body["grant_id"], uuid.uuid4().hex)
            code, _ = authority.check()
            if code or auth.binding(authority.store, authority.gid):
                raise ViewerError("正式授权已失效、范围不匹配或已用于旧手机会话")
            try:
                check_tunnel_lease(cfg)
                context = server_context(cfg)
                viewer = (MultiViewer if cfg["max_viewers"] > 1 else Viewer)(cfg, lambda spec=copy.deepcopy(spec): self.snapshot(spec), authority=authority)
                gateway = Gateway((cfg["bind_host"], cfg["port"]), viewer, context)
            except (OSError, ssl.SSLError, ViewerError) as exc:
                authority.end("START_FAILED")
                if isinstance(exc, ViewerError):
                    detail = str(exc)
                elif exc.errno == errno.EADDRNOTAVAIL:
                    detail = "Mac 网络地址已变化，配置的地址不在当前网络中。请连接原网络，或更新内网地址及对应证书后重新授权"
                elif exc.errno == errno.EADDRINUSE:
                    detail = "手机查看端口正被占用，请结束占用后重新授权"
                else:
                    detail = "无法启动 HTTPS 手机查看，请检查证书、私钥、地址及端口后重新授权"
                raise ViewerError(detail + "；本次临时授权已结束") from None
            self.spec, self.viewer, self.gateway = copy.deepcopy(spec), viewer, gateway
            self.thread = threading.Thread(target=gateway.serve_forever, kwargs={"poll_interval": .2}, daemon=True)
            self.thread.start()
            self.monitor = threading.Thread(target=self._watch, args=(viewer, gateway), daemon=True)
            self.monitor.start()
        # QR compilation can take time. Do not block permission revocation on it.
        try:
            url = viewer.status()["pair_url"]
            qr = "data:image/png;base64," + base64.b64encode(qr_png(url, self.app.root)).decode() if url else None
        except (OSError, subprocess.SubprocessError):
            qr = None
        with self.lock:
            if self.viewer is viewer and viewer.active and viewer.status().get("pair_url") == url:
                self.qr = qr
            return self.status()

    def _watch(self, viewer, gateway):
        while True:
            time.sleep(.25)
            with self.lock:
                if self.viewer is not viewer:
                    return
                try:
                    viewer.status()
                except Exception:
                    try:
                        viewer.authority.end("OUT_OF_SCOPE")
                    except Exception:
                        pass  # unavailable audit cannot leave the in-memory reader active
                    finally:
                        viewer.revoke("OUT_OF_SCOPE")
                done = not viewer.active and time.monotonic() - viewer.ended_at >= 13
            if done:
                self._close(viewer, gateway)
                return

    def require_control(self, body):
        key, grant = self.current_grant()
        if not grant or body.get("key") != key or body.get("grant_id") != grant["id"]:
            raise ViewerError("手机授权已变化，请从当前授权详情重新操作")

    def approve(self, confirmation):
        with self.lock:
            if not self.viewer:
                raise ViewerError("手机查看未开启")
            self.viewer.approve(confirmation)
            if not isinstance(self.viewer, MultiViewer):
                self.qr = None
            return self.status()

    def remove_device(self, sid):
        with self.lock:
            if not isinstance(self.viewer, MultiViewer):
                raise ViewerError("当前分享不支持逐台移除")
            self.viewer.remove_device(sid)
            return self.status()

    def invite(self, body=None):
        with self.lock:
            if body is not None:
                self.require_control(body)
            if not isinstance(self.viewer, MultiViewer):
                raise ViewerError("当前分享不支持添加手机")
            viewer = self.viewer
            viewer.invite()
            url = viewer.status()["pair_url"]
            gid, ticket = viewer.authority.gid, viewer.ticket
        try:
            qr = "data:image/png;base64," + base64.b64encode(qr_png(url, self.app.root)).decode()
        except (OSError, subprocess.SubprocessError):
            qr = None
        with self.lock:
            if self.viewer is viewer and viewer.active and viewer.authority.gid == gid and viewer.ticket == ticket:
                self.qr = qr
            return self.status()

    def revoked(self, key, gid):
        """Called while the existing revoke route holds app.lock; no waiting/join here."""
        with self.lock:
            if self.viewer and (self.viewer.authority.key, self.viewer.authority.gid) == (key, gid):
                self.viewer.end("REVOKED")
                self.qr = None

    def end_share(self):
        with self.lock:
            if self.viewer:
                self.viewer.end("STOPPED")
                self.qr = None
            else:
                key, grant = self.current_grant()
                if grant and grant["card"] == auth.RESOURCE:
                    store = self.app.instances[key].cluster
                    store.revoke(grant["id"], auth.now(), via="UI")
                    auth.record(store, grant["id"], uuid.uuid4().hex, "ENDED", "STOPPED")
            return self.status()

    def _close(self, viewer, gateway):
        # Never join a worker/accept loop while holding A, P or V.
        gateway.shutdown()
        gateway.server_close()
        with self.lock:
            if self.viewer is viewer:
                self.gateway = self.viewer = self.thread = self.spec = self.qr = None

    def stop(self):
        """Process cleanup. Hiding either UI never calls this."""
        viewer = gateway = None
        try:
            with self.lock:
                viewer, gateway = self.viewer, self.gateway
                if viewer:
                    try:
                        viewer.end("SHUTDOWN")
                    finally:
                        viewer.revoke("SHUTDOWN")
                else:
                    self.end_share()
        finally:
            if gateway:
                self._close(viewer, gateway)
        return {"running": False, "ok": True}
