"""星炬 · Oura 适配器（真实接入：OAuth 授权码 + 官方 v2 接口）。

接入 = 本人在 Oura 官方页面登录并同意（持续保存许可，DC-16）；之后按批拉取并保存，断开即停止。
令牌不进实例目录、不进日志（HR-50、HR-31）：macOS 存钥匙串，其他系统存 ~/.ptds/secrets（0600）。
只访问 Oura 官方接口（HR-32）。字段缺失就不写，不补值（PC-06）。
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from h1_common import H1Error, time_key
from startorch_outbox import ObservationInput

AUTHORIZE_URL = "https://cloud.ouraring.com/oauth/authorize"
AUTHORIZE_URL_NEW = "https://developer.ouraring.com/authorize"  # 官方给新建应用的备选授权地址
TOKEN_URL = "https://api.ouraring.com/oauth/token"
REVOKE_URL = "https://api.ouraring.com/oauth/revoke"  # 官方授权文档“Revoking The Access Token”；文档未写请求方法
API_BASE = "https://api.ouraring.com/v2/usercollection/"
DEFAULT_SCOPES = "personal daily heartrate"
HISTORY_DAYS = 30
FIELDS_VERSION = 3  # 2 = 字典 0.5：夜间最低心率、卧床时长、入睡/醒来时刻、运动；3 = 字典 0.6：当天消耗卡路里
BACKFILL_DAYS = 60  # 状态卡的个人基线要 28 天以上的历史


# ----------------------------------------------------------------------------- secrets (outside the instance)

class SecretStore:
    def __init__(self, service: str = "ptds-oura"):
        self.service = service
        self.dir = Path(os.environ.get("PTDS_SECRETS", "~/.ptds/secrets")).expanduser()

    def _mac(self) -> bool:
        return sys.platform == "darwin" and not os.environ.get("PTDS_SECRETS")

    def get(self, account: str):
        if self._mac():
            r = subprocess.run(["security", "find-generic-password", "-s", self.service, "-a", account, "-w"],
                               capture_output=True, text=True)
            return r.stdout.strip() or None if r.returncode == 0 else None
        path = self.dir / f"{self.service}-{account}"
        return path.read_text("utf-8") if path.exists() else None

    def put(self, account: str, value: str) -> None:
        if self._mac():
            subprocess.run(["security", "add-generic-password", "-U", "-s", self.service, "-a", account, "-w", value],
                           capture_output=True, check=True)
            return
        self.dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = self.dir / f"{self.service}-{account}"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_BINARY", 0), 0o600)  # Windows：二进制，不改换行
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(value)

    def delete(self, account: str) -> None:
        if self._mac():
            subprocess.run(["security", "delete-generic-password", "-s", self.service, "-a", account],
                           capture_output=True)
            return
        path = self.dir / f"{self.service}-{account}"
        if path.exists():
            path.unlink()


# ----------------------------------------------------------------------------- HTTP

def _http(method: str, url: str, *, data: dict | None = None, token: str | None = None, timeout: int = 30, on_response=None):
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    if body is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    last = None
    for attempt in range(3):  # 运行许可包络：外部不可达时最多重试 3 次，间隔递增
        requested_at = datetime.now(timezone.utc).isoformat()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                if on_response:
                    on_response(raw, resp.status, requested_at, None)
                return json.loads(raw or b"{}")
        except urllib.error.HTTPError as exc:
            if on_response:
                on_response(None, exc.code, requested_at, 'OURA_HTTP_ERROR')
            if exc.code in (401, 403):
                raise H1Error("OURA_UNAUTHORIZED", f"http {exc.code}") from None
            if exc.code == 429 or exc.code >= 500:
                last = H1Error("OURA_UNAVAILABLE", f"http {exc.code}")
            else:
                raise H1Error("OURA_REQUEST_FAILED", f"http {exc.code}") from None
        except (urllib.error.URLError, TimeoutError) as exc:
            if on_response:
                on_response(None, None, requested_at, 'OURA_UNREACHABLE')
            last = H1Error("OURA_UNREACHABLE", type(exc).__name__)
            if _no_network(exc):  # 断网（域名解析不了、网络不可达）：重试也没用，马上告诉用户
                raise last from None
        if attempt < 2:
            time.sleep(1 + attempt * 2)
    raise last


def _no_network(exc) -> bool:
    reason = getattr(exc, "reason", exc)
    return isinstance(reason, socket.gaierror) or getattr(reason, "errno", None) in (50, 51, 65, 100, 101, 113)  # ENETDOWN/ENETUNREACH/EHOSTUNREACH (mac, linux)


class OuraClient:
    def __init__(self, config: dict, store: SecretStore, account: str):
        self.client_id = config.get("client_id") or os.environ.get("PTDS_OURA_CLIENT_ID")
        self.redirect_uri = config.get("redirect_uri", "http://127.0.0.1:8780/oauth/oura/callback")
        self.scopes = config.get("scopes", DEFAULT_SCOPES)
        self.api_base = config.get("api_base", API_BASE)
        self.token_url = config.get("token_url", TOKEN_URL)
        self.revoke_url = config.get("revoke_url", REVOKE_URL)
        self.authorize_url = config.get("authorize_url", AUTHORIZE_URL)
        self.store, self.account = store, account
        self.recorder = None

    def client_secret(self):
        return self.store.get("client-secret." + self.account)

    def configured(self) -> bool:
        return not self.missing()

    def missing(self) -> list:
        """Only field names leave this boundary; secret accounts are per instance."""
        out = [] if self.client_id else ["client_id"]
        return out if self.client_secret() else out + ["client_secret"]

    def authorize_link(self, state: str, verifier: str | None = None, variant: str = "") -> str:
        """variant（排查用）：dev = 用新建应用的备选授权地址；noscope = 不带 scope（官方：不带即全部）。"""
        q = {"response_type": "code", "client_id": self.client_id, "redirect_uri": self.redirect_uri, "state": state}
        if "noscope" not in variant:
            q["scope"] = self.scopes
        if verifier:  # PKCE（官方推荐）
            q["code_challenge"] = pkce_challenge(verifier)
            q["code_challenge_method"] = "S256"
        base = AUTHORIZE_URL_NEW if "dev" in variant else self.authorize_url
        return base + "?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote)

    def _save_token(self, tok: dict) -> None:
        tok = dict(tok, obtained_at=int(time.time()))
        self.store.put(self.account, json.dumps(tok))

    def exchange_token(self, code: str, verifier: str | None = None) -> dict:
        """Obtain tokens without persisting; the host validates its generation."""
        data = {"grant_type": "authorization_code", "code": code, "redirect_uri": self.redirect_uri,
                "client_id": self.client_id, "client_secret": self.client_secret()}
        if verifier:
            data["code_verifier"] = verifier
        return _http("POST", self.token_url, data=data)

    def save_token(self, tok: dict) -> None:
        """Persist a validated exchange result under the host ownership lock."""
        self._save_token(tok)

    def exchange(self, code: str, verifier: str | None = None) -> None:
        self.save_token(self.exchange_token(code, verifier))

    def token(self) -> str:
        raw = self.store.get(self.account)
        if not raw:
            raise H1Error("OURA_NOT_CONNECTED", "")
        tok = json.loads(raw)
        if tok.get("refresh_token") and time.time() > tok["obtained_at"] + int(tok.get("expires_in", 86400)) - 300:
            new = _http("POST", self.token_url, data={
                "grant_type": "refresh_token", "refresh_token": tok["refresh_token"],
                "client_id": self.client_id, "client_secret": self.client_secret()})
            self._save_token(new)  # refresh token is single-use: store the new one at once
            tok = json.loads(self.store.get(self.account))
        return tok["access_token"]

    def connected(self) -> bool:
        return self.store.get(self.account) is not None

    def disconnect(self) -> None:
        self.store.delete(self.account)

    def revoke_remote(self) -> None:
        """Revoke the current access token at Oura; any non-2xx or network failure raises.

        The documented URL carries the token as a query parameter: it is never logged,
        returned or put in an error. Local credentials are deleted by the host afterwards.
        """
        status = []
        try:
            url = self.revoke_url + "?" + urllib.parse.urlencode({"access_token": self.token()})
            _http("GET", url, on_response=lambda raw, code, at, error: status.append(code))
        except ValueError:  # a 2xx body that is not JSON is still a completed revocation
            if not (status and status[-1] is not None and 200 <= status[-1] < 300):
                raise H1Error("OURA_REVOKE_FAILED", "") from None
        except H1Error as exc:
            raise H1Error("OURA_REVOKE_FAILED", exc.code) from None

    def fetch(self, collection: str, params: dict) -> list:
        if self.recorder:
            self.recorder.assert_ok()
        token, rows, next_token = self.token(), [], None
        for _ in range(200):
            q = dict(params, **({"next_token": next_token} if next_token else {}))
            callback = (lambda raw, status, at, error: self.recorder.on_page(
                collection, q, raw, status, at, error, secrets=(token,))) if self.recorder and collection != 'heartrate' else None
            options = {'on_response': callback} if callback else {}
            page = _http("GET", self.api_base + collection + "?" + urllib.parse.urlencode(q), token=token, **options)
            rows.extend(page.get("data") or [])
            next_token = page.get("next_token")
            if not next_token:
                break
        return rows


# ----------------------------------------------------------------------------- mapping → H1 observations

def _num(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        s = format(v, "f").rstrip("0").rstrip(".")
        return s if s not in ("", "-0") else "0"
    return None


def _clock_min(text, tz: str):
    """设备给的带时区时刻 → 本实例时区里当天 0 点起的分钟数（0–1439.9）。"""
    if not text:
        return None
    try:
        t = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        return None
    from zoneinfo import ZoneInfo  # noqa: PLC0415
    t = t.astimezone(ZoneInfo(tz))
    return round(t.hour * 60 + t.minute + t.second / 60, 1)


def map_oura(collections: dict, tz: str) -> list:
    """collections: {name: [rows]} as returned by the API. Returns [ObservationInput] (no duplicates)."""
    out = {}

    def add(code, value, unit, temporal, ref):
        v = _num(value)
        if v is None:
            return
        key = f"OURA|{code}|{time_key(temporal, ref)}"
        out[key] = ObservationInput(key, code, v, None, unit, temporal, "DEVICE_OURA", ref, "DEVICE_CONSUMER")

    def day(d):
        return {"role": "DAY", "observed_date": d, "tz": tz}

    for r in collections.get("daily_readiness", []):
        if r.get("day"):
            ref = "OURA:daily_readiness:" + r["day"]
            add("OURA_READINESS_SCORE", r.get("score"), "score", day(r["day"]), ref)
            add("OURA_TEMP_DEV", r.get("temperature_deviation"), "°C", day(r["day"]), ref)
    for r in collections.get("daily_sleep", []):
        if r.get("day"):
            add("OURA_SLEEP_SCORE", r.get("score"), "score", day(r["day"]), "OURA:daily_sleep:" + r["day"])
    for r in collections.get("daily_activity", []):
        if r.get("day"):
            ref = "OURA:daily_activity:" + r["day"]
            add("OURA_ACTIVITY_SCORE", r.get("score"), "score", day(r["day"]), ref)
            add("OURA_STEPS", r.get("steps"), "steps", day(r["day"]), ref)
            add("OURA_CAL_TOTAL", r.get("total_calories"), "kcal", day(r["day"]), ref)  # 字典 0.6
            add("OURA_CAL_ACTIVE", r.get("active_calories"), "kcal", day(r["day"]), ref)
    for r in collections.get("daily_spo2", []):
        if r.get("day") and isinstance(r.get("spo2_percentage"), dict):
            add("OURA_SPO2", r["spo2_percentage"].get("average"), "%", day(r["day"]), "OURA:daily_spo2:" + r["day"])
    # 夜间睡眠：同一天只取主睡眠（long_sleep；没有就取最长的一段）
    best = {}
    for r in collections.get("sleep", []):
        d = r.get("day")
        if not d:
            continue
        rank = (r.get("type") == "long_sleep", r.get("total_sleep_duration") or 0)
        if d not in best or rank > best[d][0]:
            best[d] = (rank, r)
    for d, (_, r) in best.items():
        ref = "OURA:sleep:" + str(r.get("id", d))
        add("OURA_HRV", r.get("average_hrv"), "ms", day(d), ref)
        # lowest_heart_rate 是夜间最低心率：字典 0.5 起写到 OURA_LOWEST_HR；以前写在 OURA_RESTING_HR 的旧记录保留（产品负责人 2026-10-14）
        add("OURA_LOWEST_HR", r.get("lowest_heart_rate"), "bpm", day(d), ref)
        add("OURA_RESP_RATE", r.get("average_breath"), "次/分", day(d), ref)
        for code, field in (("OURA_TOTAL_SLEEP", "total_sleep_duration"), ("OURA_TIME_IN_BED", "time_in_bed")):
            dur = r.get(field)
            if isinstance(dur, (int, float)) and not isinstance(dur, bool):
                add(code, round(dur / 60), "min", day(d), ref)
        for code, field in (("OURA_BEDTIME_START", "bedtime_start"), ("OURA_BEDTIME_END", "bedtime_end")):
            m = _clock_min(r.get(field), tz)
            if m is not None:
                add(code, m, "min", day(d), ref)
    # 运动：每次一条（开始时刻为时点），时长 = 结束 − 开始
    for r in collections.get("workout", []):
        try:
            s0 = datetime.fromisoformat(str(r["start_datetime"]).replace("Z", "+00:00"))
            s1 = datetime.fromisoformat(str(r["end_datetime"]).replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        mins = round((s1 - s0).total_seconds() / 60, 1)
        if s0.tzinfo is None or not 0 < mins < 24 * 60:
            continue
        add("OURA_WORKOUT_MIN", mins, "min", {"role": "INSTANT", "observed_at": s0.isoformat(timespec="seconds")},
            "OURA:workout:" + str(r.get("id") or s0.isoformat()))
    for r in collections.get("heartrate", []):
        ts = r.get("timestamp")
        if not ts:
            continue
        try:
            instant = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        if instant.tzinfo is None:
            continue
        iso = instant.isoformat(timespec="seconds")
        add("OURA_HR", r.get("bpm"), "bpm", {"role": "INSTANT", "observed_at": iso}, "OURA:heartrate:" + iso)
    return list(out.values())


def pull(client: OuraClient, tz: str, *, since: date, until: date) -> dict:
    """Fetches one window. Returns {collections: counts, items: [ObservationInput]}."""
    end = until + timedelta(days=1)  # end_date may be exclusive on some endpoints
    dparams = {"start_date": since.isoformat(), "end_date": end.isoformat()}
    names = ["daily_readiness", "daily_sleep", "daily_activity", "sleep"]
    collections = {n: client.fetch(n, dparams) for n in names}
    for opt in ("daily_spo2", "workout"):  # 血氧、运动要各自的权限；没给就跳过，不影响其他数据
        try:
            collections[opt] = client.fetch(opt, dparams)
        except H1Error:  # 主要的几类已经取到，可选的这一类取不到不算失败
            pass
    # 逐分钟心率量大：只取最近 2 天（"我的体征"只看最近读数与短序列），日汇总照常取整个窗口
    start_dt = datetime.combine(max(since, until - timedelta(days=2)), datetime.min.time(), tzinfo=timezone.utc)
    collections["heartrate"] = client.fetch("heartrate", {
        "start_datetime": start_dt.isoformat(timespec="seconds"),
        "end_datetime": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    items = map_oura(collections, tz)
    return {"collections": {k: len(v) for k, v in collections.items()}, "items": items}


def pull_daily(client: OuraClient, tz: str, *, since: date, until: date,
               cutover_day: str | None = None, now: datetime | None = None,
               summaries: bool = True) -> dict:
    """Daily policy: closed vendor days only; recent heart rate stays in RAM.

    The legacy ``pull`` is deliberately unchanged. This function never writes
    files and never maps workout sessions or heart-rate samples into formal
    observations. ``sleep`` may contain vendor arrays in its HTTP response;
    only the already-supported scalar mapping leaves this function.
    """
    from zoneinfo import ZoneInfo
    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        raise H1Error("OURA_DAILY_TIMEZONE_REQUIRED", "")
    local_today = clock.astimezone(ZoneInfo(tz)).date()
    first = max(since, date.fromisoformat(cutover_day)) if cutover_day else since
    last = min(until, local_today - timedelta(days=1))
    collections = {}
    if summaries and first <= last:
        params = {"start_date": first.isoformat(), "end_date": (last + timedelta(days=1)).isoformat()}
        for name in ("daily_readiness", "daily_sleep", "daily_activity", "sleep"):
            collections[name] = client.fetch(name, params)
        try:
            collections["daily_spo2"] = client.fetch("daily_spo2", params)
        except H1Error:
            pass  # Same optional scope behavior as legacy pull.
    items = [item for item in map_oura(collections, tz)
             if item.temporal.get("role") == "DAY"
             and first.isoformat() <= item.temporal["observed_date"] <= last.isoformat()]
    # A short overlap is sufficient for a volatile latest reading; older
    # samples cannot recreate a formal INSTANT or extend persistent history.
    recent = client.fetch("heartrate", {
        "start_datetime": (clock - timedelta(hours=1)).isoformat(timespec="seconds"),
        "end_datetime": clock.isoformat(timespec="seconds")})
    latest = []
    for item in map_oura({"heartrate": recent}, tz):
        observed = datetime.fromisoformat(item.temporal["observed_at"])
        if clock - timedelta(hours=1) <= observed <= clock:
            latest.append({"code": item.code, "value_raw": item.value_raw,
                           "unit_raw": item.unit_raw, "observed_at": observed.isoformat()})
    latest = sorted(latest, key=lambda x: datetime.fromisoformat(x["observed_at"]), reverse=True)[:1]
    return {"collections": {**{k: len(v) for k, v in collections.items()}, "heartrate": len(recent)},
            "items": items, "latest": latest,
            "daily_through": last.isoformat() if summaries and first <= last else None,
            "daily_scanned_on": local_today.isoformat() if summaries else None}


def batch_request_id(items: list) -> str:
    digest = hashlib.sha256("\n".join(sorted(f"{i.unique_key}={i.value_raw}" for i in items)).encode()).hexdigest()
    return "OURA-" + digest[:24]


def client_for(app, instance_id: str) -> OuraClient:
    """Single client factory shared by HTTP and erasure callers; no server import."""
    cfg = dict(app.config.get("oura", {}))
    if not cfg.get("redirect_uri"):
        cfg["redirect_uri"] = f"http://127.0.0.1:{app.port}/oauth/oura/callback"
    return OuraClient(cfg, SecretStore(), instance_id)


def new_state() -> str:
    return secrets.token_urlsafe(16)


def new_verifier() -> str:
    return secrets.token_urlsafe(48)


def pkce_challenge(verifier: str) -> str:
    import base64
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
