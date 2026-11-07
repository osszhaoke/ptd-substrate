"""Phone-session audit adapter for ClusterStore, not a second grant authority.

Generic callers retain A; phone actions and journal I/O hold shared P.
Storage delegates never acquire P or A. No observation values, pairing secrets or bearer tokens.
The append-only association journal shares the existing cluster audit directory.
"""
from datetime import datetime, timezone
import json
import os
import re
import phone_lifecycle

from h1_common import H1Error

RESOURCE = "SOMALOOP_TAIL"
EVENT_ZH = {"PAIRED": "本机已批准手机配对", "READ": "手机首次读取限定快照",
            "DEVICE_PAIRED": "本机已批准一台手机", "DEVICE_LEFT": "一台手机已结束查看",
            "DEVICE_READ": "该手机首次读取限定快照",
            "DENIED": "手机访问被拒绝", "ENDED": "手机分享已结束"}
REASON_ZH = {"REVOKED": "访问授权已撤回", "EXPIRED": "访问授权已到期",
             "PAIR_EXPIRED": "配对已超时", "SESSION_EXPIRED": "查看会话已到期",
             "ATTEMPTS": "配对尝试次数已用尽", "PHONE_LEFT": "手机结束查看",
             "STOPPED": "本机停止分享", "SHUTDOWN": "本机服务退出",
             "RESTART": "本机服务重新启动", "START_FAILED": "手机查看未能启动",
             "NOT_FOUND": "授权不存在", "OUT_OF_SCOPE": "授权范围不匹配",
             "SESSION_MISMATCH": "手机会话不匹配", "NOT_APPROVED": "手机尚未获准",
             "NOT_READ": "授权不含读取", "WAIT_CHANNEL": "通道未就绪"}


def now():
    return datetime.now(timezone.utc)


@phone_lifecycle.serialized
def events(store):
    path = store.root / "cluster" / "phone_sessions.jsonl"
    if not path.exists():
        return []
    try:
        rows = [json.loads(line) for line in path.read_text("utf-8").splitlines() if line]
        for r in rows:
            if (not isinstance(r, dict)
                    or not isinstance(r.get("grant"), str) or not re.fullmatch(r"G-\d+", r["grant"])
                    or not isinstance(r.get("session"), str) or not re.fullmatch(r"[a-f0-9]{32}", r["session"])
                    or not isinstance(r.get("event"), str) or r["event"] not in EVENT_ZH
                    or (r.get("reason") is not None and (not isinstance(r["reason"], str) or r["reason"] not in REASON_ZH))
                    or r.get("actor") not in ("LOCAL_USER", "PHONE_GATEWAY")
                    or r.get("resource") != RESOURCE or r.get("permission") != "read"
                    or not isinstance(r.get("scope"), list) or len(r["scope"]) != 4
                    or not all(isinstance(code, str) and code for code in r["scope"])
                    or not isinstance(r.get("at"), str)
                    or datetime.fromisoformat(r["at"]).tzinfo is None):
                raise ValueError("invalid phone association")
        return rows
    except (OSError, ValueError, TypeError, KeyError):
        raise H1Error("PHONE_AUDIT_UNREADABLE", "手机授权关联记录不可读，已停止访问") from None


@phone_lifecycle.serialized
def record(store, gid, sid, event, reason=None, at=None):
    if event not in EVENT_ZH or (reason is not None and reason not in REASON_ZH):
        raise H1Error("PHONE_AUDIT_INVALID", "event")
    if not re.fullmatch(r"[a-f0-9]{32}", sid):
        raise H1Error("PHONE_AUDIT_INVALID", "session")
    old = events(store)
    if any(r["grant"] == gid and r["session"] == sid and r["event"] == event and r.get("reason") == reason for r in old):
        return  # bounded lifecycle summaries, never every poll
    row = {"grant": gid, "session": sid, "event": event, "reason": reason,
           "at": (at or now()).isoformat(timespec="microseconds"),
           "actor": "LOCAL_USER" if event in ("PAIRED", "DEVICE_PAIRED") else "PHONE_GATEWAY",
           "resource": RESOURCE, "scope": store.cfg["phone_tail"]["codes"], "permission": "read"}
    with (store.root / "cluster" / "phone_sessions.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def binding(store, gid):
    return next((r["session"] for r in events(store) if r["grant"] == gid and r["event"] == "PAIRED"), None)


def records(store, rows=None):
    out = []
    for i, r in enumerate(events(store) if rows is None else rows):
        text = EVENT_ZH[r["event"]]
        reason = REASON_ZH.get(r.get("reason"), "")
        out.append({"id": "phone-" + str(i + 1), "grant": r["grant"], "at": r["at"], "when": store._when(r["at"]),
                    "obj": "临时手机浏览器", "how": text, "level": "限定四项读数",
                    "summary": "Somaloop 临时只读查看 · 会话 " + r["session"],
                    "result": reason or text, "ok": r["event"] != "DENIED", "action": r["event"],
                    "via": "PHONE", "outcome": r["event"], "reason": r.get("reason"),
                    "session": r["session"], "actor": r["actor"], "resource": r["resource"],
                    "scope": r["scope"], "egress": r["event"] == "READ"})
    return out


class Authority:
    def __init__(self, app, spec, gid, sid):
        self.app, self.key, self.gid, self.sid = app, spec["key"], gid, sid
        self.store = app.instances[self.key].cluster
        self.codes = [t["code"] for t in spec["tiles"]]
        self.lock = phone_lifecycle.bound(app, self.store)

    def check(self, *, approved=False, audit=False):
        code, grant = self.store.phone_check(self.gid, self.codes, now())
        bound = binding(self.store, self.gid)
        if not code and ((approved and bound != self.sid) or (bound and bound != self.sid)):
            code = "SESSION_MISMATCH"
        if code and audit:
            record(self.store, self.gid, self.sid, "DENIED", code)
        return code, grant

    def approve(self):
        code, grant = self.check()
        if code:
            return code, 0
        record(self.store, self.gid, self.sid, "PAIRED")
        remaining = (datetime.fromisoformat(grant["expires_at"]) - now()).total_seconds()
        return None, max(0, remaining)

    def end(self, reason):
        # Dedicated one-session resource only; never revoke another grant type.
        grant = self.store.find(self.gid, now())
        if grant and grant["card"] == RESOURCE:
            self.store.revoke(self.gid, now(), via="PHONE")
            record(self.store, self.gid, self.sid, "ENDED", reason)

    def audit(self, event, reason=None):
        record(self.store, self.gid, self.sid, event, reason)
