"""Somaloop 连续个人读数：原始记录追加保存，正式入库与采样规则保持。
既有 VISITOR 标记仅保留溯源，不再分段、清空或截断当前读数。
腕带桥仍只推实际收到的实时读数；不新增设备扫描或历史回填。
"""
from __future__ import annotations

import json
import hashlib
import os
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

LABEL = "Somaloop"
KINDS = {"HR": ("心率", "bpm"), "SPO2": ("血氧", "%"), "HRV": ("心率变异性", "ms"), "SKIN_TEMP": ("皮肤温度", "°C"),
         "STEPS": ("步数", "步"), "BATTERY": ("电量", "%")}
# 字典 0.8 里有的四项 → 正式保存
CODES = {"HR": "SOMALOOP_HR", "SPO2": "SOMALOOP_SPO2", "HRV": "SOMALOOP_HRV", "SKIN_TEMP": "SOMALOOP_SKIN_TEMP"}
# 小尾巴固定四项（产品负责人 09:21；09:23 只放最近读数，不画走势）
TAIL = ["HR", "SPO2", "SKIN_TEMP", "HRV"]
UNITS = {"bpm": "bpm", "次/分": "bpm", "count/min": "bpm", "beats/min": "bpm", "%": "%", "ms": "ms",
         "°C": "°C", "℃": "°C", "degC": "°C", "C": "°C", "celsius": "°C"}
# 腕带历史种类 → 读数种类（单位还要对得上才算）
HISTORY_KIND = {"heartRate": "HR", "singleHeartRate": "HR", "spo2": "SPO2", "hrv": "HRV", "temperature": "SKIN_TEMP"}
ALIVE_S = 90  # 桥接 App 一轮心率 40 秒 + 血氧 40 秒 + HRV，读数稀疏的段落 20 秒会误报“没在运行”
LIVE_BATCH = 100
LIVE_RETRY_MIN_S = 1.0
LIVE_RETRY_MAX_S = 30.0
_SAFE = re.compile(r"[^0-9A-Za-z_.:-]")


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds")


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and abs(f) < 1e12 else None


def _fmt(kind: str, v: float) -> str:
    return str(int(round(v))) if kind in ("HR", "SPO2", "STEPS", "BATTERY") else f"{v:.2f}".rstrip("0").rstrip(".")


class BandTrial:
    def __init__(self, root: Path, saver=None, lock=None, *, async_flush=False):
        """saver(items, batch_id) -> {"CREATED": n, ...}：星炬正式保存（server 提供，持全局写锁）；None 时只记原始记录。"""
        self.path = Path(root) / "startorch" / "band_trial.jsonl"
        self.live_mark = self.path.with_name("band_live_formal.json")
        self.hist_dir = Path(root) / "startorch" / "band_history"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Async delivery owns a short-lived receiver lock. The formal saver must
        # never run while it is held; its app/database lock is independent.
        self.lock = lock if lock is not None else threading.RLock()
        self.saver = saver
        self.async_flush = bool(async_flush)
        self._flush_event = threading.Event()
        self._flush_stop = threading.Event()
        self._flush_thread = None
        self.rows = []
        if self.path.exists():
            for line in self.path.read_text("utf-8").splitlines():
                try:
                    self.rows.append(json.loads(line))
                except ValueError:
                    continue
        self.seen, self.seen_ts = set(), set()
        self.hist_counts = {}
        if self.hist_dir.exists():
            for f in self.hist_dir.glob("*.jsonl"):
                n = 0
                for line in f.read_text("utf-8").splitlines():
                    try:
                        r = json.loads(line)
                        self.seen.add(r["id"])
                        if r.get("ts") is not None:
                            self.seen_ts.add(r["id"])
                        n += 1
                    except (ValueError, KeyError):
                        continue
                self.hist_counts[f.stem] = n
        self.status = {"connection": None, "device": None, "wear": None, "note": None, "at": None}
        self.sync_req = None      # 页面点“立即同步”的时间；桥接 App 每几秒来问一次
        self.history = {"at": None, "kinds": {}, "saved": {}, "error": None}
        self.bucket = {}          # 实时读数：每项当前这一分钟已存的
        self.pending = []
        self.saved = {"CREATED": 0, "REVISED": 0, "UNCHANGED": 0}
        self.reconnect_req = None
        self.deliveries = {r["delivery_id"]: r.get("delivery_hash") for r in self.rows if r.get("delivery_id")}
        # Only this version's explicitly marked records are replayed. Old history
        # remains untouched; a cursor never authorizes moving records to another root.
        first_live = next((n for n, r in enumerate(self.rows) if "formal_pending" in r), len(self.rows))
        self.live_cursor = first_live
        self._active_batch = None
        if self.live_mark.exists():
            mark = json.loads(self.live_mark.read_text("utf-8"))
            self.live_cursor = mark["row"]
            if type(self.live_cursor) is not int or not first_live <= self.live_cursor <= len(self.rows):
                raise ValueError("BAND_LIVE_CHECKPOINT_INVALID")
            if mark.get("last_saved_at") is not None:
                self.status["last_saved_at"] = mark["last_saved_at"]
            self._active_batch = mark.get("inflight")
        self.status["last_read_at"] = max((r.get("at", 0) for r in self.rows if r.get("kind") in KINDS), default=None)
        for r in self.rows:
            if r.get("formal_pending"):
                self.bucket[r["kind"]] = int(r["at"] // 60)
        self._pending_rows = [n + 1 for n, r in enumerate(self.rows)
                              if n >= self.live_cursor and r.get("formal_pending")]
        self.pending = [self._live_item(self.rows[n - 1]) for n in self._pending_rows]
        if self._active_batch is not None:
            active = self._active_batch
            if (not isinstance(active, dict) or set(active) != {"start_row", "end_row", "count"}
                    or any(type(active[k]) is not int for k in active)
                    or active["start_row"] != self.live_cursor
                    or not 1 <= active["count"] <= min(len(self.pending), LIVE_BATCH)
                    or active["end_row"] != self._pending_rows[active["count"] - 1]):
                raise ValueError("BAND_LIVE_INFLIGHT_INVALID")
        self._latest, self._live_latest, self._row_count = {}, {}, 0
        for row in self.rows:
            self._index_latest(row)
        self._cu_running = self._cu_again = False
        if self.async_flush and self.saver is not None:
            self._flush_thread = threading.Thread(target=self._flush_loop, name="PTDS-band-formal", daemon=True)
            self._flush_thread.start()
            if self.pending:
                self._flush_event.set()
        if self.saver is not None and self.hist_dir.exists():
            self.catch_up_later()  # 上次没存完的历史接着存

    # ---- 写
    def _append(self, row: dict):
        if self.path.is_symlink():
            raise ValueError("BAND_LIVE_PATH_UNSAFE")
        separator = ""
        if self.path.exists() and self.path.stat().st_size:
            with self.path.open("rb") as old:
                old.seek(-1, os.SEEK_END)
                if old.read(1) != b"\n":
                    separator = "\n"  # Retain a crash-truncated tail without joining the next record to it.
        fd = os.open(self.path, os.O_APPEND | os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as f:
            f.write(separator + json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        directory = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        self.rows.append(row)
        self._index_latest(row)

    def _index_latest(self, row):
        kind = row.get("kind")
        if kind not in KINDS:
            return
        self._row_count += 1
        if row.get("value") is not None and row["at"] >= self._latest.get(kind, {}).get("at", float("-inf")):
            self._latest[kind] = {k: row[k] for k in ("value", "unit", "at")}
            self._latest[kind]["zh"] = KINDS[kind][0]

    def _live_item(self, row):
        return self._item(row["kind"], row["value"], row["at"],
                          f"SOMALOOP:{row.get('device') or '-'}:live:{row['kind']}:{int(row['at'])}")

    def _checkpoint_live(self, cursor=None):
        from device_recovery import save
        cursor = len(self.rows) if cursor is None else cursor
        if type(cursor) is not int or not self.live_cursor <= cursor <= len(self.rows):
            raise ValueError("BAND_LIVE_CHECKPOINT_INVALID")
        saved_at = time.time()
        save(self.live_mark, {"row": cursor, "last_saved_at": saved_at})
        self.live_cursor = cursor
        return saved_at

    def _item(self, kind: str, value: float, at: float, ref: str):
        from startorch_outbox import ObservationInput  # noqa: PLC0415 — 只有正式保存时才要
        temporal = {"role": "INSTANT", "observed_at": _iso(at)}
        key = f"SOMALOOP|{CODES[kind]}|{temporal['observed_at']}"
        return ObservationInput(key, CODES[kind], _fmt(kind, value), None, KINDS[kind][1], temporal,
                                "DEVICE_SOMALOOP", ref[:200], "DEVICE_CONSUMER")

    def _save(self, items: list, batch_id: str) -> dict:
        if not items or self.saver is None:
            return {}
        got = self.saver(items, batch_id)
        for k, n in got.items():
            self.saved[k] = self.saved.get(k, 0) + n
        return got

    def _flush(self):
        if self.saver is None:
            return
        if self.async_flush:
            if self.pending:
                self._flush_event.set()
            return
        items = list(self.pending)
        if not items:
            return
        try:
            got = self._save(items, "SOMALOOP-LIVE")
            if sum(got.get(k, 0) for k in ("CREATED", "REVISED", "UNCHANGED")) != len(items):
                raise ValueError("BAND_FORMAL_RECEIPT_INCOMPLETE")
            saved_at = self._checkpoint_live()
            self.pending = []
            self._pending_rows = []
            self._active_batch = None
            self.status["save_error"] = None
            self.status["last_saved_at"] = saved_at
        except Exception as exc:  # noqa: BLE001 — 原始记录已在；正式保存失败如实记下
            self.status["note"] = "正式保存没成功：" + type(exc).__name__
            self.status["save_error"] = "BAND_FORMAL_SAVE_FAILED"

    def _flush_loop(self):
        """One live writer: capture a bounded prefix, save unlocked, then commit its cursor."""
        retry = LIVE_RETRY_MIN_S
        while not self._flush_stop.is_set():
            self._flush_event.wait()
            self._flush_event.clear()
            if self._flush_stop.is_set():
                return
            try:
                with self.lock:
                    if self._active_batch is None:
                        count = min(len(self.pending), LIVE_BATCH)
                        if not count:
                            continue
                        active = {"start_row": self.live_cursor, "count": count,
                                  "end_row": self._pending_rows[count - 1]}
                        # Persist only the raw-row boundary, before attempting
                        # admission. An unknown result must replay the same batch
                        # even after restart and concurrent new raw deliveries.
                        from device_recovery import save
                        mark = {"row": self.live_cursor, "inflight": active}
                        if self.status.get("last_saved_at") is not None:
                            mark["last_saved_at"] = self.status["last_saved_at"]
                        save(self.live_mark, mark)
                        self._active_batch = active
                    count = self._active_batch["count"]
                    cursor = self._active_batch["end_row"]
                    items = list(self.pending[:count])
                # In particular, do not hold the receiver lock while the saver
                # waits for app.lock or runs export / state calculations.
                got = self.saver(items, "SOMALOOP-LIVE")
                if sum(got.get(k, 0) for k in ("CREATED", "REVISED", "UNCHANGED")) != count:
                    raise ValueError("BAND_FORMAL_RECEIPT_INCOMPLETE")
                with self.lock:
                    saved_at = self._checkpoint_live(cursor)
                    del self.pending[:count]
                    del self._pending_rows[:count]
                    self._active_batch = None
                    for key, value in got.items():
                        self.saved[key] = self.saved.get(key, 0) + value
                    self.status["save_error"] = None
                    self.status["last_saved_at"] = saved_at
                    if self.pending:
                        self._flush_event.set()
                retry = LIVE_RETRY_MIN_S
            except Exception as exc:  # noqa: BLE001 — durable raw and cursor remain recoverable
                with self.lock:
                    self.status["note"] = "正式保存没成功：" + type(exc).__name__
                    self.status["save_error"] = "BAND_FORMAL_SAVE_FAILED"
                # Status/push wake-ups cannot bypass backoff. Only shutdown can.
                if self._flush_stop.wait(retry):
                    return
                retry = min(retry * 2, LIVE_RETRY_MAX_S)
                self._flush_event.set()

    def close(self, timeout=2.0):
        """Stop scheduling; an in-flight save may finish and checkpoint safely."""
        self._flush_stop.set()
        self._flush_event.set()
        if self._flush_thread is not None and self._flush_thread is not threading.current_thread():
            self._flush_thread.join(timeout)

    def push(self, body: dict) -> dict:
        now = time.time()
        with self.lock:
            dev = str(body.get("device") or "")[-6:].upper() or None
            if body.get("type") == "status":
                for k in ("connection", "wear", "note"):
                    if k in body:
                        self.status[k] = str(body[k])[:60] if body[k] is not None else None
                # Bounded diagnostics only; no PPI, sleep segments or readings.
                for field, allowed in {
                    "daily_hrv_state": {"saved", "no_eligible_windows", "retry", "incomplete"},
                    "daily_hrv_reason": {"interrupted", "record_limit", "page_limit", "end_not_seen"},
                    "daily_sleep_state": {"generation_firmware_unverified"},
                }.items():
                    if isinstance(body.get(field), str) and body[field] in allowed:
                        self.status[field] = body[field]
                for field in ("firmware_version", "firmware_date"):
                    value = body.get(field)
                    if isinstance(value, str) and len(value) <= 32 and re.fullmatch(r"[A-Za-z0-9.:-]+", value):
                        self.status[field] = value
                for field in ("daily_hrv_pages", "daily_hrv_records"):
                    if type(body.get(field)) is int and 0 <= body[field] <= 100000:
                        self.status[field] = body[field]
                days = body.get("daily_hrv_days")
                if type(days) is int and 0 <= days <= 3660:
                    self.status["daily_hrv_days"] = days
                if dev:
                    self.status["device"] = dev
                if type(body.get("queued")) is int and 0 <= body["queued"] <= 20000:
                    self.status["queued"] = body["queued"]
                if isinstance(body.get("binding_generation"), str):
                    self.status["binding_generation"] = body["binding_generation"]
                self.status["at"] = now
                if self.pending:
                    self._flush()
                return {"ok": True}
            kind = body.get("kind")
            if kind not in KINDS:
                raise ValueError("kind")
            v = _num(body.get("value"))
            at = _num(body.get("at")) or now
            delivery_id = body.get("delivery_id")
            if delivery_id is not None and (not isinstance(delivery_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{16,80}", delivery_id)):
                raise ValueError("BAND_DELIVERY_ID_INVALID")
            payload_hash = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
            if delivery_id in self.deliveries:
                if self.deliveries[delivery_id] != payload_hash:
                    raise ValueError("BAND_DELIVERY_CONFLICT")
                if self.pending:
                    self._flush()
                return {"ok": True, "ack": "durable_received", "delivery_id": delivery_id, "duplicate": True}
            minute = int(at // 60)
            if not self.async_flush and self._stale_pending(minute):
                self._flush()
            selected = v is not None and kind in CODES and self.bucket.get(kind) != minute
            row = {"at": at, "kind": kind, "value": v, "unit": KINDS[kind][1],
                   "quality": str(body.get("quality") or "")[:30], "device": dev, "label": LABEL,
                   "formal_pending": selected, "delivery_id": delivery_id or uuid.uuid4().hex,
                   "delivery_hash": payload_hash, "binding_generation": body.get("binding_generation")}
            self._append(row)
            self.deliveries[row["delivery_id"]] = payload_hash
            self.status["at"] = now
            self.status["last_read_at"] = max(at, self.status.get("last_read_at") or at)
            if dev:
                self.status["device"] = dev
            if selected:
                self.bucket[kind] = minute
                self.pending.append(self._live_item(row))
                self._pending_rows.append(len(self.rows))
                if self.async_flush or len(self.pending) >= len(CODES):
                    self._flush()
            return {"ok": True, "ack": "durable_received", "delivery_id": delivery_id}

    def live(self, body: dict, consume=None) -> dict:
        """Readout only: no raw row, delivery queue, or formal observation write.

        The optional consumer maintains a compact daily accumulator, never a
        per-event history. This reply is deliberately not a durable raw ACK.
        """
        kind = body.get("kind")
        value, at = _num(body.get("value")), _num(body.get("at"))
        if kind not in KINDS or value is None or at is None or at <= 0 or at > time.time():
            raise ValueError("LIVE_SAMPLE_INVALID")
        if consume is not None:
            consume(kind, value, at)
        with self.lock:
            if at >= self._live_latest.get(kind, {}).get("at", float("-inf")):
                self._live_latest[kind] = {"value": value, "unit": KINDS[kind][1], "at": at, "zh": KINDS[kind][0]}
            self.status["at"] = time.time()
            self.status["last_read_at"] = max(at, self.status.get("last_read_at") or at)
            self.status["device"] = str(body.get("device") or "")[-6:].upper() or self.status.get("device")
            self.status["data_policy"] = "daily"
        return {"ok": True, "ack": "live_display", "raw_persisted": False, "formal_saved": False}

    def _stale_pending(self, minute: int) -> bool:
        return any(int(datetime.fromisoformat(i.temporal["observed_at"]).timestamp() // 60) < minute for i in self.pending)

    def push_history(self, body: dict) -> dict:
        """桥接 App 把腕带里存的历史按批送来：{kind, device, samples:[{id, field, value, unit, ts, quality}], done?}。
        原始样本按编号去重后只追加；有代码、单位对得上、有时间的，走星炬正式保存。"""
        hk = _SAFE.sub("", str(body.get("kind") or ""))[:30]
        if not hk:
            raise ValueError("kind")
        dev = str(body.get("device") or "")[-6:].upper() or None
        samples = body.get("samples") or []
        if not isinstance(samples, list):
            raise ValueError("samples")
        with self.lock:
            fresh = []
            for s in samples[:5000]:
                if not isinstance(s, dict):
                    continue
                sid = _SAFE.sub("", str(s.get("id") or ""))[:120]
                v, ts = _num(s.get("value")), _num(s.get("ts"))
                # 同一样本再来一次：只有这次带上了时间（以前没有）才追加一行，旧行保留
                if not sid or (sid in self.seen and (ts is None or sid in self.seen_ts)):
                    continue
                unit = str(s.get("unit") or "")[:20]
                rec = {"id": sid, "kind": hk, "field": str(s.get("field") or "")[:40], "value": v, "unit": unit,
                       "ts": ts, "quality": str(s.get("quality") or "")[:30], "device": dev, "label": LABEL,
                       "received_at": time.time(),
                       "time_meaning": str(s.get("time_meaning") or "")[:20], "time_evidence": str(s.get("time_evidence") or "")[:120]}
                fresh.append(rec)
                self.seen.add(sid)
                if ts is not None:
                    self.seen_ts.add(sid)
            if fresh:
                self.hist_dir.mkdir(parents=True, exist_ok=True)
                with (self.hist_dir / f"{hk}.jsonl").open("a", encoding="utf-8") as f:
                    for rec in fresh:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                self.hist_counts[hk] = self.hist_counts.get(hk, 0) + len(fresh)
            k = self.history["kinds"].setdefault(hk, {"received": 0, "new": 0})
            k["received"] += len(samples)
            k["new"] += len(fresh)
            if body.get("note"):
                k["note"] = str(body["note"])[:80]
            self.history["at"] = time.time()
            self.status["at"] = time.time()
        self.catch_up_later()
        return {"ok": True, "new": len(fresh)}

    # ---- 历史 → 星炬正式保存：按原始文件逐行补，做到哪一行记在 band_history/formal.json，进程重启后接着做（同一读数再存是“未变”）
    def catch_up_later(self):
        with self.lock:
            if self._cu_running:
                self._cu_again = True
                return
            self._cu_running = True
        threading.Thread(target=self._catch_up_loop, daemon=True).start()

    def _catch_up_loop(self):
        while True:
            try:
                self.catch_up()
            except Exception as exc:  # noqa: BLE001 — 原始记录还在，下次再补
                self.history["error"] = type(exc).__name__
            with self.lock:
                if not self._cu_again:
                    self._cu_running = False
                    return
                self._cu_again = False

    def catch_up(self) -> dict:
        if self.saver is None or not self.hist_dir.exists():
            return {}
        mark = self.hist_dir / "formal.json"
        done = json.loads(mark.read_text("utf-8")) if mark.exists() else {}
        total = {"saved": 0, "no_time": 0, "unit": 0, "no_code": 0}
        for f in sorted(self.hist_dir.glob("*.jsonl")):
            hk = f.stem
            lines = f.read_text("utf-8").splitlines()
            start = done.get(hk, 0)
            kind = HISTORY_KIND.get(hk)
            while start < len(lines):
                chunk, items = lines[start:start + 2000], []
                for line in chunk:
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    if kind is None:
                        total["no_code"] += 1
                    elif r.get("value") is None or r.get("ts") is None:
                        total["no_time"] += 1
                    elif UNITS.get(r.get("unit") or "") != KINDS[kind][1]:
                        total["unit"] += 1
                    else:
                        items.append(self._item(kind, r["value"], r["ts"], f"SOMALOOP:{r.get('device') or '-'}:history:{hk}:{r['id']}"))
                got = self._save(items, "SOMALOOP-HISTORY")
                total["saved"] += got.get("CREATED", 0)
                start += len(chunk)
                done[hk] = start
                mark.write_text(json.dumps(done), "utf-8")
                k = self.history["kinds"].setdefault(hk, {"received": 0, "new": 0})
                k["saved"] = k.get("saved", 0) + got.get("CREATED", 0)
        self.history["formal"] = total
        return total

    def request_sync(self) -> dict:
        with self.lock:
            self.sync_req = time.time()
            return {"ok": True, "requested_at": self.sync_req}

    def cmd(self) -> dict:
        return {"sync": self.sync_req, "reconnect": self.reconnect_req}

    def request_reconnect(self) -> dict:
        with self.lock:
            self.reconnect_req = time.time()
            return {"ok": True, "requested_at": self.reconnect_req}

    def tail_snapshot(self) -> dict:
        """Pure display copy: never flush, save, sync, or initialise a store."""
        with self.lock:
            readings = self._live_latest if self.status.get("data_policy") == "daily" else self._latest
            latest = {kind: {k: readings[kind][k] for k in ("value", "unit", "at")}
                      for kind in TAIL if kind in readings}
            status = {"connection": self.status.get("connection"),
                      "data_policy": self.status.get("data_policy", "full"),
                      "alive": bool(self.status.get("at") and time.time() - self.status["at"] < ALIVE_S)}
        return {"status": status, "tiles": [{"kind": k, "latest": latest.get(k)} for k in TAIL]}

    # ---- 读
    def view(self) -> dict:
        now = time.time()
        with self.lock:
            if (self.async_flush and self.pending) or (not self.async_flush and self._stale_pending(int(now // 60))):
                self._flush()
            readings = self._live_latest if self.status.get("data_policy") == "daily" else self._latest
            latest = {kind: dict(row) for kind, row in readings.items()}
            alive = bool(self.status["at"] and now - self.status["at"] < ALIVE_S)
            tiles = [{"kind": k, "zh": KINDS[k][0], "unit": KINDS[k][1], "code": CODES[k], "latest": latest.get(k)} for k in TAIL]
            return {"label": LABEL, "mode": "continuous_personal", "latest": latest, "tiles": tiles,
                    "status": dict(self.status, alive=alive), "count": self._row_count,
                    "total": self._row_count,
                    "history": dict(self.history, stored=dict(self.hist_counts)), "sync_requested_at": self.sync_req,
                    "saved": dict(self.saved), "pending_formal": len(self.pending)}
