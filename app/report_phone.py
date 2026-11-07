"""Independent STATE_REPORT phone gateway. No listener or data access at construction.

Reuses the existing phone transport's TLS identity and loopback safeguards, not
its Somaloop authority, snapshot or short-lived in-memory viewing sessions.
"""
from __future__ import annotations
import base64
import copy
import hashlib
import json
import struct
import zlib
import os
import re
import secrets
import stat
import threading
import time
import uuid
from collections import deque
from contextlib import nullcontext
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import phone_tail as pt
from h1_common import H1Error

ROOT = Path(__file__).resolve().parent
RESOURCE = "STATE_REPORT"
COOKIE = "__Host-PTDSReport"
SCHEMA = "PTDS_REPORT_PHONES_V1"
TOKEN_RE = re.compile(r"[A-Za-z0-9_-]{32,100}")
EVENTS = {"PAIRED": "已批准手机查看状态报告", "READ": "手机已读取状态报告", "DENIED": "手机报告访问被拒绝",
          "REVOKED": "手机报告授权已撤回", "PUSH_REGISTERED": "已登记手机提醒", "PUSH_DISABLED": "已停止手机提醒",
          "PUSH_ACCEPTED": "推送服务已接受提醒", "PUSH_EXPIRED": "手机提醒订阅已失效", "PUSH_REJECTED": "推送服务拒绝提醒",
          "PUSH_UNKNOWN": "提醒投递结果未确认"}

class ReportPhoneError(ValueError):
    pass


class AccessError(ReportPhoneError):
    pass


def _dt(value):
    value = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ReportPhoneError("报告时间缺少时区")
    return value


def _iso(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="microseconds")


def _digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _read_audit(root):
    path = root / "cluster/report_phone_events.jsonl"
    if not path.exists():
        return []
    if path.is_symlink() or path.stat().st_size > 8 * 1024 * 1024:
        raise ReportPhoneError("手机报告授权记录不可读")
    out = []
    try:
        for line in path.read_text("utf-8").splitlines():
            r = json.loads(line)
            if (not isinstance(r, dict) or r.get("event") not in EVENTS or r.get("resource") != RESOURCE
                    or not re.fullmatch(r"G-\d+", r.get("grant", ""))
                    or not re.fullmatch(r"[a-f0-9]{32}", r.get("device_id", ""))
                    or not isinstance(r.get("at"), str)):
                raise ValueError()
            _dt(r["at"])
            out.append(r)
    except (OSError, ValueError, TypeError, KeyError):
        raise ReportPhoneError("手机报告授权记录不可读") from None
    return out


def audit_records(store):
    return [{"id": "report-phone-" + str(i + 1), "grant": r["grant"], "at": r["at"], "when": store._when(r["at"]),
             "obj": "我的手机 · 状态报告", "how": EVENTS[r["event"]], "level": "已选状态报告",
             "summary": "授权后生成的指定订阅报告", "result": EVENTS[r["event"]],
             "ok": r["event"] not in ("DENIED", "PUSH_REJECTED", "PUSH_UNKNOWN"), "action": r["event"],
             "via": "REPORT_PHONE", "outcome": r["event"], "resource": RESOURCE,
             "egress": r["event"] in ("READ", "PUSH_ACCEPTED")} for i, r in enumerate(_read_audit(store.root))]


class Manager:
    def __init__(self, app, *, transport=None, clock=time.time):
        self.app, self.clock = app, clock
        self.lock = threading.RLock()
        self.app_lock = getattr(app, "lock", threading.RLock())
        self.gateway = self.thread = self.cfg = None
        self.stopping = False
        self.invitations, self.pending = {}, {}
        self.traffic = deque()
        if transport is None:
            from report_webpush import Transport
            transport = Transport((app.config.get("state_report_phone") or {}).get("webpush") or {})
        self.transport = transport

    def _config(self):
        raw = self.app.config.get("state_report_phone") or {}
        if not isinstance(raw, dict) or raw.get("enabled") is not True:
            raise ReportPhoneError("手机报告尚未配置固定 HTTPS 入口；本机订阅仍可使用")
        cfg = pt.settings(dict(raw, port=raw.get("port", 8792)))
        if cfg["deployment_mode"] == "quick_tunnel" or cfg["hostname"].endswith(".trycloudflare.com"):
            raise ReportPhoneError("定期手机报告需要固定 HTTPS 地址，临时通道不能用于长期订阅")
        return cfg

    def _instance(self, key):
        if key not in self.app.instances:
            raise ReportPhoneError("请选择当前数据实例")
        return self.app.instances[key]

    def _path(self, key):
        root = Path(self._instance(key).ctx.root)
        directory = root / "state_reports"
        if directory.is_symlink():
            raise ReportPhoneError("手机报告私有目录无效")
        return directory / "phone_devices.json"

    def _load(self, key):
        path = self._path(key)
        if not path.exists():
            return {"schema": SCHEMA, "devices": []}
        if path.is_symlink() or path.stat().st_size > 1024 * 1024:
            raise ReportPhoneError("手机报告设备记录不可读")
        try:
            data = json.loads(path.read_text("utf-8"))
            rows = data["devices"]
            if data.get("schema") != SCHEMA or not isinstance(rows, list) or len(rows) > 100:
                raise ValueError()
            for r in rows:
                if (not isinstance(r, dict) or not re.fullmatch(r"[a-f0-9]{32}", r.get("device_id", ""))
                        or not re.fullmatch(r"[a-f0-9]{64}", r.get("token_hash", ""))
                        or not re.fullmatch(r"G-\d+", r.get("grant_id", ""))
                        or not isinstance(r.get("origin"), str)
                        or not isinstance(r.get("name"), str) or len(r["name"]) > 40):
                    raise ValueError()
                _dt(r["created_at"]); _dt(r["expires_at"])
            if len({r["device_id"] for r in rows}) != len(rows) or len({r["token_hash"] for r in rows}) != len(rows):
                raise ValueError()
            return data
        except (OSError, ValueError, TypeError, KeyError):
            raise ReportPhoneError("手机报告设备记录不可读，已停止访问") from None

    def _save(self, key, data):
        path = self._path(key)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if path.is_symlink():
            raise ReportPhoneError("手机报告设备记录不可写")
        tmp = path.with_name(".phone-" + uuid.uuid4().hex + ".tmp")
        try:
            fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, allow_nan=False)
                f.flush(); os.fsync(f.fileno())
            os.replace(tmp, path)
        finally:
            if tmp.exists():
                tmp.unlink()

    def _audit(self, key, row, event):
        store = self._instance(key).cluster
        old = _read_audit(store.root)
        if event in ("DENIED", "PAIRED", "REVOKED") and any(r["device_id"] == row["device_id"] and r["event"] == event for r in old):
            return
        path = store.root / "cluster/report_phone_events.jsonl"
        data = {"event": event, "device_id": row["device_id"], "grant": row["grant_id"],
                "at": _iso(self.clock()), "resource": RESOURCE}
        fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n"); f.flush(); os.fsync(f.fileno())

    def _metadata(self, key):
        provider = getattr(self.app.state_reports, "phone_metadata", None) or self.app.state_reports.status
        return provider(key)

    def _subscription(self, key):
        sub = self._metadata(key).get("subscription")
        if not sub or not sub.get("card_ids"):
            raise ReportPhoneError("请先保存需要推送的状态订阅")
        return sub

    def _grant(self, key, row, *, audit=False):
        code, grant = self._instance(key).cluster.check_report_grant(row["grant_id"], _iso(self.clock()))
        if (code or row.get("revoked") or _dt(row["expires_at"]).timestamp() <= self.clock()
                or self.stopping or not self.cfg or row["origin"] != self.cfg["public_origin"]):
            if audit:
                self._audit(key, row, "DENIED")
            raise AccessError("手机报告授权已结束，请在 Mac 重新连接")
        return grant

    def _expire_pending(self):
        now = self.clock()
        self.invitations = {k: v for k, v in self.invitations.items() if v["until"] > now}
        self.pending = {k: v for k, v in self.pending.items() if v["until"] > now}

    def status(self, key):
        with self.app_lock, self.lock:
            self._instance(key); self._expire_pending()
            try:
                cfg = self._config()
                configured, detail = True, "固定 HTTPS 入口已配置；手机连通性与系统通知仍需真机核验"
            except (ReportPhoneError, pt.ViewerError) as e:
                cfg, configured, detail = None, False, str(e)
            rows = []
            try:
                sub = self._subscription(key)
            except ReportPhoneError:
                sub = None
            for r in self._load(key)["devices"]:
                code, grant = self._instance(key).cluster.check_report_grant(r["grant_id"], _iso(self.clock()))
                scope = (grant or {}).get("events") or {}
                changed = not sub or sub.get("id") != scope.get("subscription_id") or not set(sub.get("card_ids", [])) <= set(scope.get("card_ids", []))
                state = "REVOKED" if r.get("revoked") else code or "ACTIVE"
                rows.append({k: r[k] for k in ("device_id", "grant_id", "name", "created_at", "expires_at")})
                rows[-1].update(status=state, notification_enabled=bool(r.get("push")) and state == "ACTIVE",
                                scope=scope, scope_changed=changed, delivery_state=r.get("delivery_state", "not_sent"))
            inv = self.invitations.get(key)
            invitation = {k: inv.get(k) for k in ("pair_url", "pair_code", "expires_at", "qr")} if inv else None
            pending = [{k: r[k] for k in ("device_id", "name", "confirmation", "expires_at")} for r in self.pending.values() if r["key"] == key]
            return {"configured": configured, "setup_required": not configured, "running": self.gateway is not None,
                    "detail": detail, "invitation": invitation, "pending": pending, "devices": rows,
                    "public_origin": cfg["public_origin"] if cfg else None}

    def start_gateway(self):
        with self.app_lock, self.lock:
            if self.gateway:
                return True
            cfg = self._config()
            pt.check_bind_address(cfg)
            context = pt.server_context(cfg)
            self.cfg = cfg
            try:
                gateway = Gateway((cfg["bind_host"], cfg["port"]), self, context)
            except Exception:
                self.cfg = None
                raise
            self.gateway = gateway
            self.stopping = False
            self.thread = threading.Thread(target=gateway.serve_forever, kwargs={"poll_interval": .2}, daemon=True)
            self.thread.start()
            return True

    def start(self, key):
        self.start_gateway()
        with self.app_lock, self.lock:
            sub = copy.deepcopy(self._subscription(key))
            active = [r for r in self.status(key)["devices"] if r["status"] == "ACTIVE"]
            if len(active) >= self.cfg.get("max_viewers", 1):
                raise ReportPhoneError("已达到已连接手机数量上限，请先撤回旧设备")
            ticket, code = secrets.token_urlsafe(32), f"{secrets.randbelow(100000000):08d}"
            while any(v["pair_code"] == code for v in self.invitations.values()):
                code = f"{secrets.randbelow(100000000):08d}"
            until = self.clock() + self.cfg["pair_seconds"]
            inv = {"ticket_hash": _digest(ticket), "pair_code": code, "pair_url": self.cfg["public_origin"] + "/#" + ticket,
                   "expires_at": _iso(until), "until": until, "attempts": 0, "subscription": sub, "qr": None}
            self.invitations[key] = inv
            self.pending = {i: r for i, r in self.pending.items() if r["key"] != key}
        try:
            raw = pt.qr_png(inv["pair_url"], Path(self.app.root))
            qr = "data:image/png;base64," + base64.b64encode(raw).decode()
        except Exception:
            qr = None
        with self.app_lock, self.lock:
            if self.invitations.get(key) is inv:
                inv["qr"] = qr
            return self.status(key)

    def pair(self, supplied, name="我的手机"):
        with self.app_lock, self.lock:
            self._expire_pending()
            if not isinstance(supplied, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", supplied):
                raise ReportPhoneError("配对码不正确或已失效")
            matched = None
            for key, inv in self.invitations.items():
                if inv["attempts"] < 5 and (secrets.compare_digest(_digest(supplied), inv["ticket_hash"]) or secrets.compare_digest(supplied, inv["pair_code"])):
                    matched = key, inv; break
            if matched is None:
                for inv in self.invitations.values():
                    inv["attempts"] += 1
                raise ReportPhoneError("配对码不正确或已失效")
            key, inv = matched
            token, device_id = secrets.token_urlsafe(32), uuid.uuid4().hex
            clean = name.strip()[:40] if isinstance(name, str) else "我的手机"
            clean = re.sub(r"[\x00-\x1f\x7f]", "", clean) or "我的手机"
            confirmation = f"{secrets.randbelow(10000):04d}"
            while any(r["confirmation"] == confirmation for r in self.pending.values()):
                confirmation = f"{secrets.randbelow(10000):04d}"
            row = {"key": key, "device_id": device_id, "token_hash": _digest(token), "name": clean,
                   "confirmation": confirmation, "until": inv["until"],
                   "expires_at": inv["expires_at"], "subscription": inv["subscription"]}
            self.pending[device_id] = row
            del self.invitations[key]
            return token, {"approved": False, "confirmation": row["confirmation"], "lease_seconds": 12}

    def approve(self, key, device_id):
        with self.app_lock, self.lock:
            self._expire_pending()
            r = self.pending.get(device_id)
            if not r or r["key"] != key:
                raise ReportPhoneError("待确认手机已变化，请重新连接")
            sub = self._subscription(key)
            old = r["subscription"]
            if any(sub.get(k) != old.get(k) for k in ("id", "revision", "card_ids")):
                raise ReportPhoneError("订阅内容已变化，请重新连接后确认范围")
            data = self._load(key)
            if sum(self._instance(key).cluster.check_report_grant(d["grant_id"], _iso(self.clock()))[0] is None for d in data["devices"]) >= self.cfg.get("max_viewers", 1):
                raise ReportPhoneError("已达到手机数量上限")
            grant = self._instance(key).cluster.create_report_grant(sub["id"], sub["revision"], list(sub["card_ids"]), _iso(self.clock()))
            row = {k: r[k] for k in ("device_id", "token_hash", "name")}
            row.update(grant_id=grant["id"], created_at=grant["created_at"], expires_at=grant["expires_at"],
                       origin=self.cfg["public_origin"], push=None, notified=[], read_reports=[], revoked=False)
            if len(data["devices"]) >= 100:
                self._instance(key).cluster.revoke(grant["id"], _iso(self.clock()), via="SYSTEM")
                raise ReportPhoneError("已达到设备登记记录上限，请联系维护人员")
            data["devices"].append(row)
            try:
                self._save(key, data); self._audit(key, row, "PAIRED")
            except Exception:
                self._instance(key).cluster.revoke(grant["id"], _iso(self.clock()), via="SYSTEM")
                raise
            del self.pending[device_id]
            return self.status(key)

    def _access(self, token):
        self._expire_pending()
        if not isinstance(token, str) or not TOKEN_RE.fullmatch(token):
            raise AccessError("请在 Mac 连接手机并核对配对号码")
        digest = _digest(token)
        for row in self.pending.values():
            if secrets.compare_digest(digest, row["token_hash"]):
                return row["key"], None, row, None
        for key in self.app.instances:
            data = self._load(key)
            for row in data["devices"]:
                if secrets.compare_digest(digest, row["token_hash"]):
                    grant = self._grant(key, row, audit=True)
                    return key, data, row, grant
        raise AccessError("手机报告授权已结束，请在 Mac 重新连接")

    def session(self, token):
        with self.app_lock, self.lock:
            key, data, row, grant = self._access(token)
            if data is None:
                return {"approved": False, "confirmation": row["confirmation"], "lease_seconds": 12}
            scope = grant["events"]
            try:
                sub = self._subscription(key)
            except ReportPhoneError:
                sub = None
            changed = not sub or sub.get("id") != scope["subscription_id"] or not set(sub.get("card_ids", [])) <= set(scope["card_ids"])
            return {"approved": True, "name": row["name"], "expires_at": row["expires_at"], "lease_seconds": 12,
                    "notification_enabled": bool(row.get("push")), "scope_changed": changed,
                    "public_key": self.transport.public_key, "scope": scope,
                    "subscription": {k: sub.get(k) for k in ("period_days", "time", "tz", "enabled")} if sub else None}

    def _report_allowed(self, doc, grant, current=None):
        scope = grant["events"]
        try:
            return (isinstance(doc, dict) and doc.get("subscription_id") == scope["subscription_id"]
                    and type(doc.get("revision")) is int and doc["revision"] >= scope["revision"]
                    and isinstance(doc.get("card_ids"), list) and bool(doc["card_ids"])
                    and set(doc["card_ids"]) <= set(scope["card_ids"])
                    and isinstance(doc.get("cards"), list)
                    and all(isinstance(c, dict) for c in doc["cards"])
                    and {c.get("id") for c in doc["cards"]} == set(doc["card_ids"])
                    and _dt(doc["created_at"]) >= _dt(scope["after"])
                    and (current is None or (current.get("id") == scope["subscription_id"]
                         and set(doc["card_ids"]) <= set(current.get("card_ids", [])))))
        except (KeyError, ValueError, TypeError):
            return False

    def reports(self, token, report_id=None):
        with self.app_lock, self.lock:
            key, data, row, grant = self._access(token)
            if data is None:
                raise AccessError("请等待 Mac 确认")
            current = self._subscription(key)
            if report_id is None:
                values = []
                for item in self._metadata(key).get("reports", []):
                    # Full document is authority even if status metadata omits card scope.
                    doc = self.app.state_reports.report(key, item["id"])
                    if self._report_allowed(doc, grant, current):
                        values.append({k: doc.get(k) for k in ("id", "created_at", "card_ids", "period", "by", "method")})
                self._grant(key, row, audit=True)
                return {"reports": values, "lease_seconds": 12}
            if not isinstance(report_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", report_id):
                raise ReportPhoneError("无法读取这份报告")
            doc = self.app.state_reports.report(key, report_id)
            if not self._report_allowed(doc, grant, current):
                self._audit(key, row, "DENIED")
                raise ReportPhoneError("这份报告不在当前授权范围内")
            self._grant(key, row, audit=True)
            if report_id not in row.get("read_reports", []):
                self._audit(key, row, "READ")
                row["read_reports"] = (row.get("read_reports", []) + [report_id])[-100:]
                self._save(key, data)
            safe = {k: copy.deepcopy(doc.get(k)) for k in ("id", "subscription_id", "revision", "created_at", "card_ids", "period", "cards", "by", "method", "fp")}
            return {"report": safe, "lease_seconds": 12}

    def register_push(self, token, subscription):
        with self.app_lock, self.lock:
            key, data, row, grant = self._access(token)
            if data is None:
                raise AccessError("请等待 Mac 确认")
            if not self.transport.public_key:
                raise ReportPhoneError("手机通知通道尚未配置；报告仍可查看")
            row["push"] = self.transport.validate_subscription(subscription)
            self._save(key, data); self._audit(key, row, "PUSH_REGISTERED")
            return {"registered": True}

    def disable_push(self, token):
        with self.app_lock, self.lock:
            key, data, row, grant = self._access(token)
            if data is None:
                raise AccessError("请等待 Mac 确认")
            row["push"] = None
            self._save(key, data); self._audit(key, row, "PUSH_DISABLED")
            return {"registered": False}

    def revoke(self, key, grant_id):
        with self.app_lock, self.lock:
            data = self._load(key)
            row = next((r for r in data["devices"] if r["grant_id"] == grant_id), None)
            if not row:
                raise ReportPhoneError("没有这项手机报告授权")
            self._instance(key).cluster.revoke(grant_id, _iso(self.clock()), via="UI")
            row.update(revoked=True, push=None)
            self._save(key, data); self._audit(key, row, "REVOKED")
            return self.status(key)

    def revoked(self, key, grant_id):
        return self.revoke(key, grant_id)

    def leave(self, token):
        with self.app_lock, self.lock:
            key, data, row, grant = self._access(token)
            if data is None:
                del self.pending[row["device_id"]]
                return {"ok": True}
            self.revoke(key, row["grant_id"])
            return {"ok": True}

    def notify(self, report, key):
        # Durable intents and authority checks are local and short. Never hold the
        # product lock during DNS, signing or network I/O. An in-flight generic
        # reminder may arrive after revocation; report access is always rechecked.
        results = []
        with self.app_lock, self.lock:
            if self.stopping or not self.cfg:
                return {"state": "setup_required", "devices": []}
            sub = self._subscription(key)
            if sub.get("enabled") is not True:
                return {"state": "paused", "devices": []}
            if report.get("revision") != sub.get("revision") or report.get("subscription_id") != sub.get("id"):
                return {"state": "superseded", "devices": []}
            ids = [r["device_id"] for r in self._load(key)["devices"]
                   if r.get("push") and report.get("id") not in r.get("notified", [])]
        for device_id in ids:
            with self.app_lock, self.lock:
                # Reload before each dispatch, including after another phone's slow send.
                sub = self._subscription(key)
                if (sub.get("enabled") is not True or sub.get("revision") != report.get("revision")
                        or sub.get("id") != report.get("subscription_id")):
                    break
                data = self._load(key)
                row = next((r for r in data["devices"] if r["device_id"] == device_id), None)
                if not row or not row.get("push") or report["id"] in row.get("notified", []):
                    continue
                try:
                    grant = self._grant(key, row)
                except AccessError:
                    continue
                if (not self._report_allowed(report, grant, sub)
                        or not set(sub["card_ids"]) <= set(grant["events"]["card_ids"])):
                    continue
                if not self.transport.public_key:
                    results.append({"device_id": device_id, "state": "setup_required"})
                    continue
                target, grant_id = copy.deepcopy(row["push"]), row["grant_id"]
                # Commit before external side effects. Ambiguous sends are never replayed.
                row["delivery_state"] = "unknown"
                row["notified"] = (row.get("notified", []) + [report["id"]])[-100:]
                self._save(key, data)
            try:
                result = self.transport.send(target)
            except (ValueError, OSError):
                result = {"state": "unknown"}
            state = result.get("state", "unknown") if isinstance(result, dict) else "unknown"
            if state not in ("accepted", "expired", "rejected", "unknown", "setup_required"):
                state = "unknown"
            with self.app_lock, self.lock:
                # Reconcile onto fresh state; never resurrect a revoked subscription.
                data = self._load(key)
                row = next((r for r in data["devices"] if r["device_id"] == device_id and r["grant_id"] == grant_id), None)
                if row:
                    row["delivery_state"] = state
                    if state == "expired" and row.get("push") == target:
                        row["push"] = None
                    if state != "setup_required":
                        self._audit(key, row, "PUSH_" + state.upper())
                    self._save(key, data)
            results.append({"device_id": device_id, "state": state})
        states = {r["state"] for r in results}
        state = "no_devices" if not states else next(iter(states)) if len(states) == 1 else "partial"
        return {"state": state, "devices": results}

    def allowed_rate(self):
        with self.lock:
            now = self.clock()
            while self.traffic and self.traffic[0] < now - 10:
                self.traffic.popleft()
            if len(self.traffic) >= 100:
                return False
            self.traffic.append(now)
            return True

    def stop(self):
        with self.lock:
            self.stopping = True
            gateway = self.gateway
            self.gateway = None
            self.invitations.clear(); self.pending.clear()
        if gateway:
            gateway.shutdown(); gateway.server_close()
        # Approved, scoped grants survive restart. Cookies contain no recoverable raw token on disk.


class Gateway(pt.Gateway):
    def __init__(self, address, manager, context):
        if context is None:
            raise ReportPhoneError("手机报告网关需要经过核验的 TLS")
        self.viewer, self.context = manager, context
        self.slots = threading.BoundedSemaphore(8)
        ThreadingHTTPServer.__init__(self, address, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = "PTDS-Report"
    def log_message(self, *args):
        pass

    def reply(self, status, value, kind="application/json; charset=utf-8", *, cookie=None, asset=False):
        body = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        headers = {"Content-Type": kind, "Content-Length": str(len(body)), "Cache-Control": "private, no-store, max-age=0",
                   "CDN-Cache-Control": "no-store", "Cloudflare-CDN-Cache-Control": "no-store", "Referrer-Policy": "no-referrer",
                   "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Connection": "close",
                   "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
                   "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self' data:; connect-src 'self'; worker-src 'self'; manifest-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"}
        for k, v in headers.items():
            self.send_header(k, v)
        if cookie is not None:
            self.send_header("Set-Cookie", f"{COOKIE}={cookie}; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=" + ("2592000" if cookie else "0"))
        self.end_headers(); self.wfile.write(body); self.close_connection = True

    def guard(self, post=False):
        cfg = self.server.viewer.cfg
        if (len(self.headers.get_all("Host", [])) != 1 or len(self.headers.get_all("Origin", [])) > 1
                or self.headers.get("Host") != cfg["host"]
                or self.headers.get("Origin", cfg["public_origin"]) != cfg["public_origin"]
                or (post and self.headers.get("Origin") != cfg["public_origin"])
                or self.headers.get("Sec-Fetch-Site") == "cross-site"):
            self.reply(403, {"detail": "请从手机报告页面操作"}); return False
        if self.path != self.requestline.split()[1]:
            self.reply(404, {"detail": "没有此入口"}); return False
        if not self.server.viewer.allowed_rate():
            self.reply(429, {"detail": "操作过快，请稍后再试"}); return False
        return True

    def token(self):
        try:
            cookie = SimpleCookie(); cookie.load(self.headers.get("Cookie", ""))
            return cookie[COOKIE].value if COOKIE in cookie else ""
        except Exception:
            return ""

    def _failure(self, exc):
        if isinstance(exc, AccessError):
            self.reply(401, {"code": "AUTH_REQUIRED", "detail": str(exc)}, cookie="")
        elif isinstance(exc, ReportPhoneError):
            self.reply(400, {"detail": str(exc)})
        elif isinstance(exc, (H1Error, OSError, ValueError, KeyError)):
            self.reply(503, {"detail": "暂时无法核验授权或读取报告，请稍后重试"})
        else:
            self.reply(503, {"detail": "手机报告暂时无法使用"})

    def do_GET(self):
        if not self.guard(): return
        m = self.server.viewer
        static = {"/": ("report_phone.html", "text/html; charset=utf-8"),
                  "/report_phone.js": ("report_phone.js", "text/javascript; charset=utf-8"),
                  "/report_phone.css": ("report_phone.css", "text/css; charset=utf-8"),
                  "/report_phone_sw.js": ("report_phone_sw.js", "text/javascript; charset=utf-8"),
                  "/report_phone.webmanifest": ("report_phone.webmanifest", "application/manifest+json")}
        try:
            if self.path == "/report_phone_fonts.css":
                css = "\n".join(re.findall(r"@font-face\s*\{[^}]*\}", pt.desktop_tail.PRODUCT.read_text()))
                return self.reply(200, css.encode(), "text/css; charset=utf-8", asset=True)
            if self.path in ("/report-icon-192.png", "/report-icon-512.png"):
                return self.reply(200, icon_png(192 if "192" in self.path else 512), "image/png", asset=True)
            if self.path in static:
                name, kind = static[self.path]
                return self.reply(200, (ROOT / "web" / name).read_bytes(), kind, asset=True)
            if self.path == "/api/session":
                if not self.token():
                    return self.reply(401, {"code": "PAIR_REQUIRED", "detail": "请在 Mac 连接手机"}, cookie="")
                return self.reply(200, m.session(self.token()))
            if self.path == "/api/reports":
                return self.reply(200, m.reports(self.token()))
            match = re.fullmatch(r"/api/report/([A-Za-z0-9_-]{1,128})", self.path)
            if match:
                return self.reply(200, m.reports(self.token(), match[1]))
            self.reply(404, {"detail": "没有此入口"})
        except Exception as exc:
            self._failure(exc)

    def do_POST(self):
        if not self.guard(post=True): return
        if self.path not in ("/api/pair", "/api/push", "/api/push/disable", "/api/leave"):
            return self.reply(404, {"detail": "没有此入口"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if (not 1 <= size <= 8192 or self.headers.get("Transfer-Encoding")
                    or len(self.headers.get_all("Content-Length", [])) != 1
                    or self.headers.get_content_type() != "application/json"):
                return self.reply(400, {"detail": "请求格式不正确"})
            def unique_pairs(pairs):
                obj = {}
                for k, v in pairs:
                    if k in obj: raise ValueError()
                    obj[k] = v
                return obj
            body = json.loads(self.rfile.read(size), object_pairs_hook=unique_pairs)
            allowed = {"/api/pair": {"ticket", "name"}, "/api/push": {"subscription"}, "/api/push/disable": set(), "/api/leave": set()}
            if not isinstance(body, dict) or not set(body) <= allowed[self.path]:
                raise ValueError()
        except (ValueError, TypeError):
            return self.reply(400, {"detail": "请求格式不正确"})
        m = self.server.viewer
        try:
            if self.path == "/api/pair":
                token, result = m.pair(body.get("ticket"), body.get("name", "我的手机"))
                return self.reply(200, result, cookie=token)
            if self.path == "/api/push":
                return self.reply(200, m.register_push(self.token(), body.get("subscription")))
            if self.path == "/api/push/disable":
                return self.reply(200, m.disable_push(self.token()))
            return self.reply(200, m.leave(self.token()), cookie="")
        except Exception as exc:
            self._failure(exc)


def icon_png(size):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            xx, yy = x / size, y / size
            main = abs(xx - .43) / .25 + abs(yy - .54) / .34 < 1
            small = abs(xx - .74) / .11 + abs(yy - .27) / .14 < 1
            row.extend((193, 157, 87, 255) if main or small else (17, 26, 54, 255))
        rows.append(row)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"".join(rows))) + chunk(b"IEND", b"")
