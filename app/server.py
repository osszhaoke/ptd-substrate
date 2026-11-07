"""PTDS 本机进程（10-17 演示版）：星炬、星轨、星簇三个模块在一个进程里，各写各的库。

    python3 app/server.py                 # 默认 127.0.0.1:8780，实例根目录 ~/PTDS-instances
    python3 app/server.py --port 8780 --root ~/PTDS-instances

星炬保存（正式库 + 同事务 outbox）→ 立即导出 H1 文件 → 星轨导入并计算（新时点与更正过的时点都算）。
启动时先补导出、补导入、补计算，"保存了但没算"的时点不会丢。只监听 127.0.0.1。
"""
from __future__ import annotations

import argparse
import base64
import socket
import hashlib
import json
import os
import re
import sys
import threading
import time
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from dataclasses import asdict
from http.server import ThreadingHTTPServer
from read_view import ReadResponseHandler
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent / "core"))
import tzcompat  # noqa: E402 — 要在任何模块导入 zoneinfo 之前：Windows 缺时区库时 Asia/Shanghai 用固定东八区兜底

TZ_FALLBACK = tzcompat.install()
from zoneinfo import ZoneInfo  # noqa: E402

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP / "core"))

from cards import (ALERT_SUFFIX, BannerNotifier, MacOSNotifier, _obs_json, ack_alert, card_state, current_sensitivity, deliver_pending,  # noqa: E402
                   load_card, open_startrack, recompute, save_delivery_scope, set_sensitivity, sync, take_snapshot)
from h1_common import (DictionaryRegistry, H1Error, canonical_bytes, init_instance, load_dictionary, load_instance,  # noqa: E402
                       strict_loads, time_key)
from startorch_outbox import (ObservationInput, export_pending, export_status, open_startorch,  # noqa: E402
                              repair_exports, retract_observation, save_batch)
from startorch_table import parse_table, unique_key_for_lab  # noqa: E402
from startrack_import import h1_status, import_pending  # noqa: E402
from vitals import vitals_state  # noqa: E402
from observation_read import ObservationRead
import compete  # noqa: E402
import compete_ai  # noqa: E402
import card_thresholds
import wall_display
import vitals_cards
import custom_cards  # noqa: E402
import sleep_card  # noqa: E402
import bioage  # noqa: E402
import engines  # noqa: E402
import rule_registry  # noqa: E402
import device_watch  # noqa: E402
import device_watch_read
import evidence_graph  # noqa: E402
import evidence_navigation
import preview_session
import main_db_policy, trial_target
import device_links
import graph_read  # noqa: E402
import data_read_http  # noqa: E402
import starling_status  # noqa: E402
from background_read import BackgroundRead
import read_bundle, snapshot_projection
from home_badge import offset_revision
import evidence_pack  # noqa: E402
import gene_assets
import gene_db  # noqa: E402
import gene_profile  # noqa: E402
import recognize  # noqa: E402
import retro  # noqa: E402
import starling  # noqa: E402
import starling_page  # noqa: E402
import meds  # noqa: E402
import gene_targets  # noqa: E402
import starling_ask  # noqa: E402
import starling_history  # noqa: E402
import rule_notice  # noqa: E402
import share  # noqa: E402
import starling_memory  # noqa: E402
from bridge import Bridge  # noqa: E402
from cluster import ClusterStore  # noqa: E402
import oura  # noqa: E402
import oura_sync
import oura_erase
import compute_jobs, compute_http, compute_pipeline
import guest_band  # noqa: E402
import desktop_tail  # noqa: E402
import pillbox
import phone_tail, phone_lifecycle  # noqa: E402
import band_cards
import obs_time
import input_guard, device_targets
import home_texts
import vitals_ledger  # noqa: E402
import starling_baseline
import starling_weekly
import state_reports
import report_phone
import baseline_view  # noqa: E402
import deid  # noqa: E402
from sqlite_util import transaction  # noqa: E402
import batch  # noqa: E402
import garmin_ingest
import qkeer_ingest
import somaloop_agent_ingest
import muse_sessions  # noqa: E402
from oauth_states import OAuthStates
from instance_services import GeneReader, SourceReader, oura_authorize, oura_connect, oura_disconnect, oura_sources
from source_registry import SourceRegistry
CORE = APP / "core"
DEFAULT_INSTANCES = []
METHOD_SOURCE = {"manual": "MANUAL", "table": "TABLE", "ocr": "OCR_LLM"}


def sync_policy(root: Path, accept: list, app) -> None:
    """Existing instance policy is authoritative; startup must not rewrite it."""
    doc = strict_loads((root / "instance.json").read_bytes().decode("utf-8"))
    old = (doc.get("data_policy") or {}).get("accept")
    if old != list(accept):
        app.log("data_policy_config_mismatch", doc["instance_id"], "existing_policy_retained")


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def all_observations(track, ctx, registry, *, read=None) -> list:
    """没有启用关注卡的实例（我的真实数据）：星轨里每条当前有效观测，形状同关注卡快照的 timeline。"""
    labels = {code: c.label_zh for code, c in registry.current.codes.items()}
    snap = take_snapshot(track, ctx, SimpleNamespace(codes=set(), labels=labels), read=read)
    order = lambda o: (o.day or "~", o.instant.astimezone(timezone.utc).isoformat() if o.instant else "", o.code)  # noqa: E731
    return [_obs_json(o, SimpleNamespace(labels=labels)) for o in sorted(snap.observations, key=order)]



# 设备小尾巴能选的读数：只要动态读数，不要厂商评分（产品负责人 2026-10-14）
TAIL_CODES = {"garmin": ("GARMIN_HR", "GARMIN_STEPS", "GARMIN_SPO2_AVG", "GARMIN_HRV_NIGHT", "GARMIN_CAL_TOTAL"), "oura": ("OURA_HR", "OURA_STEPS", "OURA_CAL_TOTAL", "OURA_CAL_ACTIVE", "OURA_SPO2", "OURA_HRV", "OURA_LOWEST_HR",
                       "OURA_RESP_RATE", "OURA_TEMP_DEV", "OURA_TOTAL_SLEEP", "OURA_WORKOUT_MIN")}

def page_ctx(app, inst, snap, pg, card="sjia-mas", tp="", dk="", authorization=None):
    """星灵三页和来龙去脉浮窗的记录事实（只用记录、不含健康数值）。卡被隐藏或时点没有结果 → None；未知页面 → KeyError。"""
    hidden = evidence_graph.hidden_cards(inst)
    if pg == "trace" and card in hidden:
        return None
    if pg in ("graph", "trace"):
        records, grants = authorization if authorization is not None else inst.cluster.authorization_view(snap, inst.now())
    if pg == "graph":
        records = [r for r in records if not r.get("hidden")]  # 测试时记、已隐藏的授权不交给星灵（对象写的是“11 / 111”，会被当成数值挡下）
        cards = ([{"card_id": "sjia-mas", "name": "sJIA 关注卡"}] if inst.sjia and "sjia-mas" not in hidden else []) + \
            [{"card_id": c["card_id"], "name": c["name"]} for c in snap.get("custom_cards") or []] + evidence_graph.engine_cards(inst)
        return starling_page.graph_page(inst, evidence_graph.traceable(inst, hidden), snap, records, cards)
    if pg == "trace":
        t = evidence_graph.trace(inst, tp, [r for r in records if not r.get("hidden")], grants, card_id=card)
        if not t.get("found"):
            return None
        t["verify"] = evidence_pack.verify_one(inst, t["card_id"], t["tp"], t["run"]["run_id"])
        return starling_page.trace(inst, t)
    if pg == "data":
        labels = {o["code"]: o.get("label_zh") or o["code"] for o in snap.get("timeline") or []}
        return starling_page.data_page(inst, snap, datetime.now(ZoneInfo(inst.ctx.tz)), labels)
    if pg == "sources":
        try:
            br = app.bridge(inst).state()
        except Exception:  # noqa: BLE001
            br = None
        return starling_page.sources_page(inst, snap, read_bundle.source_view(snap, lambda: Sources(inst).read()), br, len(GeneStore(inst).list()))
    if pg == "alert":  # 规则提醒小卡上的“星灵讲讲”：为什么触发（只给规则名、各路结论、变化方向、发提醒的规矩）
        c = rule_notice.why_ctx(inst, snap, dk)
        if c is not None:
            starling.check_context([f for f, _ in c["facts"]], c.pop("literals"))
        return c
    raise KeyError(pg)


def ask_facts(app, inst, snap, page):
    """问星灵：按块拼记录事实（只用记录、不含健康数值），先拼好，问模型时不再碰实例。→ facts_for(area)。"""
    hidden = evidence_graph.hidden_cards(inst)
    out = {}
    authorization = inst.cluster.authorization_view(snap, inst.now())
    lits = set(evidence_graph.SRC_ZH.values())
    def safe(x):  # 某一页的记录里混进了数值就不用那一页，问星灵照样能答，不再整条请求断掉（产品负责人 2026-10-15 演示前排查）
        try:
            return page_ctx(app, inst, snap, x, authorization=authorization) or {"facts": []}
        except starling.RawValueInContext:
            app.log("starling_ask_page_blocked", x)
            return {"facts": []}
    t, d, s_ = (safe(x) for x in ("graph", "data", "sources"))
    tf = [f for f, _ in d["facts"]] + [f for f, _ in s_["facts"]] + \
        [f for f, _ in t["facts"] if f.startswith(("状态结论", "星炬里的正式数据", "追不全"))]
    lits |= {x for x in (snap.get("timeline") and {o.get("label_zh") for o in snap["timeline"]} or set()) if x} | {"最近 7 天", "Oura", "Somaloop", "Qkeer"}
    out["torch"] = (tf, lits)
    cards = ([("sjia-mas", "sJIA 关注卡")] if inst.sjia and "sjia-mas" not in hidden else []) + \
        [(c["card_id"], c["name"]) for c in snap.get("custom_cards") or []] + [(c["card_id"], c["name"]) for c in evidence_graph.engine_cards(inst)]
    kf = [f"我绑定的状态卡有 {len(cards)} 张" + ("：" + "、".join(n for _, n in cards[:8]) if cards else "")]
    kf += [f for f, _ in t["facts"] if f.startswith(("星轨一共算过", "星轨发过", "参与计算"))]
    if inst.sjia and "sjia-mas" not in hidden:
        tps = snap.get("timepoints") or []
        if tps:
            kf.append("sJIA 关注卡各时点的综合关注等级：" + "；".join(f"{x['tp']} {x.get('level_zh') or evidence_graph.LEVEL_ZH.get(x['level'], x['level'])}" for x in tps))
        al = snap.get("alerts") or []
        if al:
            kf.append("提醒：" + "；".join(f"{a['tp']} {evidence_graph.LEVEL_ZH.get(a['level'], a['level'])}" for a in al[-5:]))
    kf.append("状态实验室里有竞争性解释和回溯式重计算，结果只用于测试，不是结论")
    kf.append("状态规则库列出每个算法的出处、版本和原文链接")
    out["track"] = (kf, lits | {n for _, n in cards} | {"规则包 0.1", "规则包 0.2"})
    cl = starling.build(inst, {"page": "cluster"}, snap, *authorization, [])
    out["cluster"] = ([f for f in cl["facts"] if not f.startswith("数据性质")] + [f for f, _ in t["facts"] if f.startswith("数据离开本机")], cl["literals"] | lits)
    if page.get("page"):
        pc = starling.build(inst, page, snap, *authorization, GeneStore(inst).list())
        pf = [f"当前页面：{pc['page_zh']}", f"页面说明：{pc['what']}"] + pc["facts"]
        if "sjia-mas" in hidden:
            pf = [f for f in pf if "sJIA" not in f]  # 隐藏的卡不能漏到别的页面
        out["page"] = (pf, pc["literals"] | lits)
    else:
        out["page"] = ([], set())
    return lambda area: out[area]


MEM_STORES: dict = {}


def mem_store(app, inst):
    """星灵记忆（独立 SQLite）。开关关着 → None。"""
    if not starling_memory.enabled(app.config):
        return None
    root = str(inst.ctx.root)
    if root not in MEM_STORES:
        cfg = dict({"server": app.config.get("llm", {}).get("server", "llama-server"),
                    "embed_model": "~/Models/bge-m3/bge-m3-Q8_0.gguf"}, **(app.config.get("starling_memory") or {}))
        MEM_STORES[root] = starling_memory.Store(inst.ctx.root, cfg)
    return MEM_STORES[root]


class NextStepMacNotifier(MacOSNotifier):
    """Mac 通知：关注卡的提醒在固定结尾前带上“带去问医生”（只改发出去的文字，提醒记录本身不动）。"""

    def __init__(self, app):
        self.app = app

    def send(self, title: str, body: str, level: str) -> None:
        super().send(title, self.app.with_next(body), level)

    def prepare(self, title: str, body: str, level: str):
        prepared_body = self.app.with_next(body)
        return lambda: MacOSNotifier.send(self, title, prepared_body, level)


class Instance:
    def __init__(self, app: "App", spec: dict):
        self.app, self.spec = app, spec
        root = app.root / spec["id"]
        if not (root / "instance.json").exists():
            init_instance(app.root, spec["id"], spec["kind"], spec["tz"], spec["name"],
                          datetime.now(ZoneInfo(spec["tz"])).isoformat(timespec="seconds"),
                          {"accept": spec["accept"]})
        else:
            sync_policy(root, spec["accept"], app)
        self.ctx = load_instance(root)
        trial_target.check_data_policy(self.ctx, spec)
        with gene_assets.session(GeneStore(self)):
            pass  # Finish a pending per-file erasure before exposing this instance.
        self.nature = input_guard.nature(spec.get("default_nature", input_guard.MISSING),
                                         default="SYNTHETIC" if self.ctx.accept == ("SYNTHETIC",) else "REAL")
        self.last_sync = None
        self.sjia = "SJIA_FOCUS" in spec["cards"]
        self.cluster = ClusterStore(self.ctx.root, app.product_config, tz=self.ctx.tz)  # 星簇：授权与出域记录

    def now(self) -> str:
        return datetime.now(ZoneInfo(self.ctx.tz)).isoformat(timespec="seconds")


    def setup(self) -> "device_watch.CardSetup":
        return device_watch.CardSetup(self.ctx.root, self.spec["cards"])

    def watch_devices(self, *, periodic: bool = False) -> list:
        """"设备断开"检查：读星轨的我的体征读模型 + 星炬的 Oura 接入状态，有变化才记事件、发通知。"""
        if self.spec.get("replay"):
            return []
        if periodic:
            with self.app.lock:
                captured = device_watch_read.capture(self)
            vit = device_watch_read.read(self, captured)
        else:
            with self.app.lock:
                vit = device_watch_read.read(self)
        status = (Sources(self).read().get("oura") or {}).get("status")
        out = device_watch.check(self, vit, status, notifiers=self.app.notifiers,
                                 offline_hours=float(self.app.config.get("device_offline_hours", 36)))
        for ev in out:
            self.app.log("device_event", self.ctx.instance_id, ev["kind"], ev["source"],
                         ",".join(d["channel"] + ":" + d["outcome"] for d in ev["deliveries"]) or "-")
        return out

    def card(self, track):
        sens = current_sensitivity(track, "sjia-mas", self.app.dynamic["default_sensitivity"])
        return load_card(self.app.registry, self.ctx, self.app.rulepack, self.app.dynamic, sens)

    # ---- 星炬 → H1 → 星轨
    def export(self, repair: bool = False) -> list:
        torch = open_startorch(self.ctx)
        try:
            if repair:
                repair_exports(torch, self.ctx, exported_at=self.now())
            return export_pending(torch, self.ctx, exported_at=self.now())
        finally:
            torch.close()

    def vitals_view(self, track, setup: dict, *, read=None, vit=None) -> tuple:
        """“我的体征”卡上实际显示的读数：解绑的来源从卡上消失（已有记录保留在星炬与星轨）。返回 (vitals, 见过的设备来源)。"""
        vit = dict(vit if vit is not None else vitals_state(track, self.ctx, self.app.registry, read=read))
        known = sorted({i.get("family") for i in vit.get("items") or []} & set(device_watch.SOURCES))
        if setup["vitals_sources"] is not None:
            vit["items"] = [i for i in vit.get("items") or [] if setup["vitals_sources"].get(i.get("family"), False)
                            or i.get("family") not in device_watch.SOURCES]
        return vit, known

    def wall_preferences(self, track):
        """Read the same append-only wall preferences for full and graph views."""
        prefs = {"pin": {}, "hide": {}}
        for cid, key, value, at in track.execute("SELECT card_id, key, value, set_at FROM card_setting "
                                                "WHERE key IN ('wall_pin', 'wall_hide') ORDER BY id"):
            v = json.loads(value)
            bucket = prefs["pin" if key == "wall_pin" else "hide"]
            if v.get("on"):
                bucket.setdefault(cid, {"at": at, "name": v.get("name") or cid})
            else:
                bucket.pop(cid, None)
        result = {"pins": [c for c, _ in sorted(prefs["pin"].items(), key=lambda kv: kv[1]["at"])],
                              "hidden": [{"card": c, "name": v["name"], "at": v["at"]} for c, v in prefs["hide"].items()]}
        display = wall_display.load(track)
        if display:
            result["display"] = display
        return result

    def sync_track(self, trigger: str) -> dict:
        return compute_pipeline.run(self, trigger, open_track=open_startrack, read_type=ObservationRead,
            primary_sync=sync, import_packages=import_pending, deliver=deliver_pending)

    def after_save(self) -> dict:
        self.export()
        pending = compute_jobs.pending_after_save(self)
        return pending if pending is not None else self.sync_track("SAVE")

    def startup(self) -> dict:
        self.export(repair=True)
        return self.sync_track("STARTUP")

    # ---- 状态快照（界面只渲染）
    def refresh_snapshot(self) -> dict:
        """Read-only home projection; independent of full historical responses."""
        if not hasattr(self, "_background_read"):
            self._background_read = BackgroundRead(self)
        snap = self._background_read.snapshot(lambda read, bundle: self.snapshot(home=True, read=read, bundle=bundle), scoped=True)
        return read_bundle.overlay(snap, self.live_overlay(snap))

    def live_overlay(self, snap):
        """Volatile display data never becomes a formal observation or run input."""
        policy = self.app.daily_policy(self.spec['key']) if hasattr(self.app, "daily_policy") else {"enabled": False}
        if not policy['enabled']:
            return snap
        import device_daily
        return dict(snap, device_policy=policy, device_latest=device_daily.realtime(self))

    def snapshot(self, *, home=False, read=None, bundle=None) -> dict:
        if not hasattr(self, "_background_read"):
            self._background_read = BackgroundRead(self)
        def build(captured):
            return snapshot_projection.project(self, captured, home=home, read=read,
                observation_factory=ObservationRead, observations=all_observations, offset=offset_revision)
        if bundle is not None:
            return build(bundle)
        with self.app.lock, read_bundle.capture(self, self._background_read,
                track_factory=open_startrack, torch_factory=open_startorch) as captured:
            snap = build(captured)
        return snap if home else read_bundle.overlay(snap, self.live_overlay(snap))

    # ---- 星炬保存
    def temporal(self, body: dict) -> dict:
        mode = body.get("tpMode", "INSTANT")
        if mode == "INSTANT":
            date, time = body.get("date") or "", body.get("time") or ""
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) or not re.fullmatch(r"\d{2}:\d{2}(:\d{2})?", time):
                raise H1Error("TIME_INVALID", "请填日期和时刻")
            local = datetime.fromisoformat(f"{date}T{time}" + (":00" if len(time) == 5 else ""))
            return {"role": "INSTANT",
                    "observed_at": local.replace(tzinfo=ZoneInfo(self.ctx.tz)).isoformat(timespec="seconds")}
        if mode == "DAY":
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", body.get("date") or ""):
                raise H1Error("TIME_INVALID", "请填日期")
            return {"role": "DAY", "observed_date": body["date"], "tz": self.ctx.tz}
        return {"role": "UNKNOWN"}

    def save_rows(self, body: dict) -> dict:
        input_guard.require_writable(self)
        request_id = body.get("request_id") or "R-" + uuid.uuid4().hex[:16]
        method = body.get("method", "manual")
        synthetic = input_guard.nature(body.get("nature", input_guard.MISSING), default=self.nature) == "SYNTHETIC"
        temporal = self.temporal(body)
        if obs_time.is_future(temporal, self.ctx.tz):  # 手工录入、化验单识别：观测时间不能晚于现在（产品负责人 2026-10-15）
            raise H1Error("TIME_FUTURE", obs_time.FUTURE_ZH)
        items = []
        for n, row in enumerate(body.get("rows", []), start=1):
            code = row["code"]
            cdef = self.app.registry.current.codes.get(code)
            source_ref = f"{METHOD_SOURCE.get(method, 'MANUAL')}:{request_id}#row{n}"
            if row.get("source_ref"):
                source_ref = row["source_ref"]
            kind = "SYNTHETIC" if synthetic else METHOD_SOURCE.get(method, "MANUAL")
            trust = "SYNTHETIC" if synthetic else ("SELF_REPORT" if cdef and cdef.family == "FLAG" else "CLINICAL_LAB")
            items.append(ObservationInput(unique_key_for_lab(code, temporal, source_ref), code, str(row["value"]),
                                          row.get("cmp") or row.get("comparator") or None, row.get("unit") or None,
                                          temporal, kind, source_ref, trust))
        return self.save_items(items, batch_id=body.get("batch_id") or "B-" + request_id[-8:],
                               request_id=request_id)

    def save_items(self, items, *, batch_id: str, request_id: str) -> dict:
        input_guard.require_writable(self)
        torch = open_startorch(self.ctx)
        try:
            results = save_batch(torch, self.ctx, self.app.registry, items, batch_id=batch_id,
                                 request_id=request_id, saved_at=self.now())
        finally:
            torch.close()
        sync_result = self.after_save()
        return {"request_id": request_id, "batch_id": batch_id,
                "results": [{"outcome": r.outcome, "observation_id": r.observation_id, "revision": r.revision}
                            for r in results],
                "export": "WRITTEN", "sync": sync_result}

    def save_table(self, data: bytes, synthetic, request_id=None) -> dict:
        input_guard.require_writable(self)
        if synthetic is None:
            synthetic = input_guard.nature(default=self.nature) == "SYNTHETIC"
        elif type(synthetic) is not bool:
            raise H1Error("NATURE_INVALID", "")
        if request_id is not None and not re.fullmatch(r"CSV-[a-f0-9-]{36}", request_id):
            raise H1Error("REQUEST_INVALID", "invalid CSV confirmation identifier")
        request_id = request_id or "T-" + hashlib.sha256(data).hexdigest()[:24]
        batch_id, items = parse_table(data, self.ctx, synthetic=synthetic)
        items, rejected = obs_time.split(items, self.ctx.tz)  # 表格里日期在今天之后的行不收，其余照常导入，逐行报出来
        if not items:
            if rejected:
                raise H1Error("TIME_FUTURE", obs_time.FUTURE_ZH + "（" + "、".join(sorted({f"第 {r['row']} 行" for r in rejected if r["row"]})) + "）")
            return self.save_items(items, batch_id=batch_id, request_id=request_id)
        res = self.save_items(items, batch_id=batch_id, request_id=request_id)
        res["rejected"] = rejected
        return res

    def correct(self, observation_id: str, value: str) -> dict:
        """更正 = 同一观测的新版本（同一 unique_key），旧版本保留；星轨随后自动更新受影响的时点。"""
        input_guard.require_writable(self)
        torch = open_startorch(self.ctx)
        try:
            row = torch.execute("SELECT unique_key, payload FROM formal_observation WHERE observation_id = ? "
                                "ORDER BY revision DESC LIMIT 1", (observation_id,)).fetchone()
        finally:
            torch.close()
        if row is None:
            raise H1Error("OBSERVATION_UNKNOWN", observation_id)
        p = json.loads(row[1])
        item = ObservationInput(row[0], p["code"], str(value), p["comparator"], p["unit_raw"], p["temporal"],
                                p["source_kind"], p["source_ref"], p["trust_tier"])
        return self.save_items([item], batch_id="CORRECT", request_id="C-" + uuid.uuid4().hex[:16])

    def retract(self, observation_id: str) -> dict:
        input_guard.require_writable(self)
        torch = open_startorch(self.ctx)
        try:
            r = retract_observation(torch, self.ctx, self.app.registry, observation_id, batch_id="RETRACT",
                                    request_id="X-" + observation_id + "-" + uuid.uuid4().hex[:6],
                                    saved_at=self.now())
        finally:
            torch.close()
        return {"outcome": r.outcome, "sync": self.after_save()}

    # ---- 星轨动作
    def track_action(self, name: str, body: dict) -> dict:
        track = open_startrack(self.ctx)
        try:
            if name == "recompute":
                r = recompute(track, self.ctx, self.card(track), now=self.now(), notifiers=self.app.notifiers)
                return {"evaluated": r["evaluated"], "run_id": r["run_id"]}
            if name == "sensitivity":
                set_sensitivity(track, "sjia-mas", body["value"], set_at=self.now())
            if name == "ack":
                ack_alert(track, str(body["dedupe_key"]), acked_at=self.now())
                return {"ok": True}
        finally:
            track.close()
        return self.sync_track(name.upper())


class Sources(SourceRegistry):
    """星炬的来源登记与接入许可（连接、获取、保存分开记）。不含令牌。"""


def oura_client(inst: Instance) -> "oura.OuraClient":
    return oura.client_for(inst.app, inst.ctx.instance_id)


def oura_pull(inst: Instance, lock=None) -> dict:
    return oura_sync.pull(inst, lock=lock, pull_once=_oura_pull_once)


def _oura_pull_once(inst: Instance, lock=None) -> dict:
    return oura_sync.pull_once(inst, lock=lock, sources=Sources, client_factory=oura_client,
                               clock=datetime, save=_oura_save)


def _oura_save(inst: Instance, src, got: dict, today) -> dict:
    return oura_sync.save(inst, src, got, today)


def evidence_hooks() -> SimpleNamespace:
    """证据包要读的来源登记、基因纳管、Oura 客户端（只拿来计数和自检，不出值）。"""
    return SimpleNamespace(sources=lambda inst: Sources(inst).read(), gene=GeneStore, oura_client=oura_client)


def gene_catch_up(app) -> None:
    for inst in list(app.instances.values()):
        try:
            store = GeneStore(inst)
            with gene_assets.session(store):
                n = store.catch_up()
            if n:
                app.log("gene_catch_up", inst.ctx.instance_id, n)
        except Exception as exc:  # noqa: BLE001
            app.log("gene_catch_up_failed", inst.ctx.instance_id, type(exc).__name__)


def code_stamp() -> str:
    """程序文件的指纹（改动时间+大小）：页面据此提示"程序已更新、需要重启"，免得新页面配旧进程。"""
    files = sorted(list(APP.glob("*.py")) + list((APP / "core").glob("*.py")))
    return hashlib.sha256("|".join(f"{f.name}:{f.stat().st_mtime_ns}:{f.stat().st_size}" for f in files).encode()).hexdigest()


STARTED_CODE = code_stamp()


GeneStore = gene_assets.GeneStore


class App:
    # Advertised by the running backend, not by hot-reloaded JavaScript.
    data_read_version = 1
    write_receipt_version = 1
    graph_read_version = 2
    home_read_version = 1
    compute_queue_version = 1 if compute_jobs.ENABLED else 0

    def __init__(self, root: Path, config: dict):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.config = config; self.trial = trial_target.Policy.build(config, root)
        self.registry = DictionaryRegistry([load_dictionary(CORE / "h1-dictionary-0.1.json"),
                                            load_dictionary(CORE / "h1-dictionary-0.2.json"), load_dictionary(CORE / "h1-dictionary-0.3.json"),
                                            load_dictionary(CORE / "h1-dictionary-0.4.json"), load_dictionary(CORE / "h1-dictionary-0.5.json"), load_dictionary(CORE / "h1-dictionary-0.6.json"),
                                            load_dictionary(CORE / "h1-dictionary-0.7.json"),
                                            load_dictionary(CORE / "h1-dictionary-0.8.json"), load_dictionary(CORE / "h1-dictionary-0.9.json"), load_dictionary(CORE / "h1-dictionary-0.10.json"), load_dictionary(CORE / "h1-dictionary-0.11.json"), load_dictionary(CORE / "h1-dictionary-0.12.json"), load_dictionary(CORE / "h1-dictionary-0.13.json"), load_dictionary(CORE / "h1-dictionary-0.15.json")])
        self.rulepack = json.loads((CORE / "sjia-rulepack-0.1.json").read_text("utf-8"))
        self.dynamic = json.loads((CORE / "dynamic-config-0.2.json").read_text("utf-8"))
        self.notifiers = [BannerNotifier()]
        if config.get("macos_notify") and sys.platform == "darwin":
            self.notifiers.append(NextStepMacNotifier(self))
        self.lock = threading.RLock()  # one writer at a time across all three modules
        self._band_init_lock = threading.Lock()
        self.pack_lock = threading.Lock()  # 证据包一次只生成一个
        self.logfile = root / "ptds-app.log"
        # 星灵开关（产品负责人 2026-10-15 分发测试版）：config 里 starling.enabled=false 时不连、不启动本机千问，星灵入口如实显示“本机未启用星灵”
        self.starling_on = bool((config.get("starling") or {}).get("enabled", True))
        self.llm = recognize.LocalLLM(config.get("llm", {}) if self.starling_on else {})
        if not self.starling_on:
            self.llm.healthy = lambda: False
            self.llm.ensure = lambda: False
        self.port = config.get("port", 8780)
        self.oauth_states = OAuthStates()
        self.product_config = json.loads((APP / "web" / "product_config.json").read_text("utf-8"))
        self.bridges = {}
        self.main_stores = main_db_policy.Stores(self, self.trial.specs(config), Instance)
        self.instances = self.main_stores.instances
        self.pillbox = pillbox.Manager(root)
        self.desktop_panels = desktop_tail.Panels(self)
        self.phone_tail = phone_tail.Manager(self)
        self.state_reports = state_reports.Manager(self)
        self.report_phone = report_phone.Manager(self)
        self.state_reports.on_report = lambda key, doc: self.report_phone.notify(doc, key)
        self.batches = {}
        self._batch_init_lock = threading.Lock()
        self.batch_worker = batch.Worker(self)
        self.compute_jobs = compute_jobs.Manager(self)

    def daily_policy(self, key):
        cfg = self.config.get("device_daily") or {}
        enabled = cfg.get("enabled") is True and key == cfg.get("instance_key") and key in self.instances
        inst = self.instances.get(key)
        return {"enabled": enabled, "mode": "daily" if enabled else "full",
                "schema": "ptds-device-day/1", "timezone": inst.ctx.tz if inst else "Asia/Shanghai",
                "cutover_day": cfg.get("cutover_day") if enabled else None}

    def band_daily(self):
        with self._band_init_lock:
            if getattr(self, "_band_daily", None) is None:
                import device_daily
                target = self.config.get("band_instance_key")
                if not self.daily_policy(target)["enabled"]:
                    raise ValueError("DAILY_POLICY_DISABLED")
                inst = self.inst(target)
                self._band_daily = device_daily.SomaloopAccumulator(inst.ctx.root, inst.ctx.tz,
                    self.config.get("band_device_id") or "configured-band", key=target)
            return self._band_daily

    def require_device_raw(self, key, body=None, *, band=False):
        """Only finish band deliveries created before the explicit switch.

        Old cloud request files remain intact; they cannot silently re-enable
        per-point imports. Status heartbeats are handled separately.
        """
        if not self.daily_policy(key)["enabled"]:
            return
        if band and isinstance(body, dict) and body.get("delivery_id"):
            cutoff = (self.config.get("device_daily") or {}).get("cutover_at")
            try:
                moment = datetime.fromisoformat(cutoff)
                stamp = float(body["at"])
                if moment.tzinfo is not None and 0 < stamp < moment.timestamp():
                    return
            except (ValueError, TypeError, KeyError):
                pass
        raise H1Error("DEVICE_DAILY_RAW_DISABLED", "已切换每日汇总；逐点读数仅供小尾巴显示")

    def band_live(self, body):
        target = self.config.get("band_instance_key")
        if not self.daily_policy(target)["enabled"]:
            raise ValueError("DAILY_POLICY_DISABLED")
        if not self.band_binding()["enabled"] or body.get("binding_generation") != self.band_binding()["generation"]:
            raise ValueError("BAND_BINDING_CHANGED")
        if self.config.get("band_paused") is True:
            raise ValueError("BAND_PAUSED")
        inst = self.inst(target)
        input_guard.require_writable(inst)
        def receive(kind, value, at):
            import device_daily
            if kind not in guest_band.CODES:
                return
            if datetime.fromtimestamp(at, ZoneInfo(inst.ctx.tz)).date().isoformat() < self.daily_policy(target)["cutover_day"]:
                raise ValueError("BEFORE_DAILY_CUTOVER")
            self.band_daily().consume(kind, value, at, delivery_id=body.get("delivery_id"))
            device_daily.cache_latest(inst, "DEVICE_SOMALOOP", guest_band.CODES[kind],
                str(value), guest_band.KINDS[kind][1], datetime.fromtimestamp(at, timezone.utc).isoformat(),
                device_key=self.config.get("band_device_id") or "configured-band")
        return self.band().live(body, receive)

    def band_daily_admit(self, body):
        import device_daily
        binding = self.band_binding()
        target = self.config.get("band_instance_key")
        if not binding["enabled"] or not self.daily_policy(target)["enabled"] or self.config.get("band_paused"):
            raise ValueError("BAND_DAILY_DISABLED")
        if body.get("binding_generation") != binding["generation"]:
            raise ValueError("BAND_BINDING_CHANGED")
        inst = self.inst(target)
        input_guard.require_writable(inst)
        normalized = device_daily.somaloop_sdk_day(body, key=target, timezone=inst.ctx.tz,
                                                  device_key=self.config["band_device_id"])
        return device_daily.admit(inst, normalized)

    def close_daily_days(self):
        target = self.config.get("band_instance_key")
        if not self.daily_policy(target)["enabled"]:
            return
        import device_daily
        acc = self.band_daily()
        for body in acc.due():
            if body["day"] < self.daily_policy(target)["cutover_day"]:
                continue
            with self.lock:
                receipt = device_daily.admit(self.inst(target), body)
            acc.mark(body["day"], receipt)
            if getattr(self, "_band", None):
                with self._band.lock:
                    self._band.status["last_daily_saved_at"] = time.time()

    def band_binding(self):
        target = self.config.get("band_instance_key")
        inst = self.instances.get(target)
        enabled = self.config.get("band_bridge") is True and inst is not None
        generation = self.config.get("band_binding_generation") or hashlib.sha256(
            (str(target) + ":" + (inst.ctx.instance_id if inst else "none") + ":band-v1").encode()).hexdigest()[:24]
        return {"transport": "band_bridge", "generation": generation, "instance_key": target or "",
                "display_name": inst.ctx.display_name if inst else "未配置接收实例",
                "device_id": self.config.get("band_device_id", ""),
                "enabled": enabled, "paused": self.config.get("band_paused") is True,
                "data_policy": "daily" if self.daily_policy(target)["enabled"] else "full"}

    def band_commands(self):
        binding = self.band_binding()
        bridge = getattr(self, "_band", None)
        return dict(bridge.cmd() if bridge else {}, binding=binding, enabled=binding["enabled"], paused=binding["paused"])

    def start_band_bridge(self):
        import subprocess
        target = Path.home() / "Applications" / "PTDS 腕带桥.app"
        if not target.is_dir() or target.is_symlink():
            raise ValueError("BAND_BRIDGE_NOT_INSTALLED")
        subprocess.run(["/usr/bin/open", str(target)], check=True, timeout=8,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def retry_oura(self, inst):
        def run():
            try:
                oura_pull(inst, lock=self.lock)
            except Exception:
                pass  # Existing pull records a sanitized failure and preserves its checkpoint.
        threading.Thread(target=run, daemon=True, name="oura-manual-retry").start()
        return {"ok": True, "status": "scheduled"}

    def band(self) -> "guest_band.BandTrial":
        """沿用既有接收实例；按连续个人读数保存，不切换体验者、不迁移旧数据。"""
        if getattr(self, "_band", None) is not None:
            return self._band
        # Durable reception must not wait for the application's computation lock.
        # Formal saving runs in the receiver's single background worker below.
        with self._band_init_lock:
            if getattr(self, "_band", None) is None:
                target = self.config.get("band_instance_key")
                receiver = self.instances.get(target)
                if receiver is None:
                    raise ValueError("BAND_NOT_BOUND")

                def saver(items, batch_id):  # 星炬正式保存（持全局写锁），随后自动交给星轨
                    request_id = batch_id + "-" + hashlib.sha256(canonical_bytes({
                        "instance_id": receiver.ctx.instance_id, "batch_id": batch_id,
                        "items": [asdict(item) for item in items]})).hexdigest()
                    with self.lock:
                        res = receiver.save_items(items, batch_id=batch_id, request_id=request_id)
                    out = {}
                    for r in res["results"]:
                        out[r["outcome"]] = out.get(r["outcome"], 0) + 1
                    self.log("band_saved", receiver.ctx.instance_id, batch_id, out.get("CREATED", 0))
                    return out
                self._band = guest_band.BandTrial(receiver.ctx.root, saver, async_flush=True)
                self._band.status["data_policy"] = "daily" if self.daily_policy(receiver.spec["key"])["enabled"] else "full"
            return self._band

    def batch(self, inst) -> "batch.Batch":
        """批量入库队列（R20）。重启后没做完的接着做：识别 / 读取中断的重新排队，保存中断的照保存计划接着存。"""
        return batch.get_queue(self, inst)

    def batch_wake(self) -> None:
        self.batch_worker.wake.set()

    def recognize(self, key: str, name: str, data: bytes) -> dict:
        """原件留存在实例目录（只新建不覆盖）→ 本机识别 → 待本人逐项确认的候选。不写正式库。"""
        inst = self.inst(key)
        input_guard.require_writable(inst)
        if len(data) > input_guard.limit(self.config, "recognize_bytes"):
            raise H1Error("FILE_TOO_LARGE", "")
        if not data:
            raise H1Error("FILE_EMPTY", "")
        sha = hashlib.sha256(data).hexdigest()
        ext = Path(name).suffix.lower() if Path(name).suffix.lower() in (".png", ".jpg", ".jpeg", ".heic", ".pdf",
                                                                       ".tif", ".tiff", ".webp") else ".bin"
        folder = inst.ctx.root / "startorch" / "originals"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{sha[:16]}{ext}"
        if not target.exists():
            with open(target, "xb") as handle:
                handle.write(data)
        result = recognize.recognize_file(target, sha, self.registry, self.llm)
        result.update({"name": name, "original": target.name, "sha256": sha,
                       "nature": inst.nature})
        # 识别记录（候选、参考范围、总结、原文行）和原件放在一起，留作寻源依据；不进正式库
        record = dict(result, recognized_at=inst.now())
        (folder / f"{sha[:16]}.recognition.json").write_text(json.dumps(record, ensure_ascii=False, indent=1), "utf-8")
        result.pop("source_lines", None)
        self.log("recognized", inst.ctx.instance_id, sha[:16], len(result["rows"]), result["engine"]["model"],
                 result["summary"]["rejected"] or "-")
        return result

    def engine(self) -> dict:
        return {"ocr": "macOS Vision（本机）" if sys.platform == "darwin" else "不可用（需要 macOS）",
                "model": starling_page.sign(self.llm) if self.llm.cfg.get("model") else "同义词对照",
                "version": "ptds-local-0.1", "local": True}

    def with_next(self, body: str) -> str:
        return body

    def log(self, event: str, *fields) -> None:  # HR-31: codes and ids only, never values or tokens
        with gene_assets.directory_lock(self.root), open(self.logfile, "a", encoding="utf-8") as handle:
            handle.write("\t".join(input_guard.log_field(v) for v in [utcnow(), event, *fields]) + "\n")

    def oura_callback_path(self) -> str:
        return urlparse(self.config.get("oura", {}).get("redirect_uri") or "").path or "/oauth/oura/callback"

    def bridge(self, inst) -> Bridge:  # 苹果健康局域网接收端：每个实例一个，按需创建；进程重启后默认关闭
        key = inst.spec["key"]
        if key not in self.bridges:
            self.bridges[key] = Bridge(inst, port=int(self.config.get("bridge_port", 8787)))
        return self.bridges[key]

    def inst(self, key) -> Instance:
        return self.main_stores.resolve(self.instances, key)

    def dict_json(self) -> dict:
        full = {}
        for code, c in self.registry.current.codes.items():
            full[code] = {"zh": c.label_zh, "family": c.family, "type": c.value_type, "canon": c.unit_canonical,
                          "cmp": c.comparators_allowed, "rules": dict(c.units),
                          "units": [{"lit": u, "rule": r} for u, r in c.units]}
        return {"version": self.registry.current.version, "full": full}


def make_handler(app: App):
    from web import page  # noqa: E402  (app/web.py)

    class Handler(ReadResponseHandler):
        server_version = "PTDS/0.3-local"

        def log_message(self, fmt, *args):
            pass

        def _redirect(self, location: str):
            return self._send(302, b"", "text/plain; charset=utf-8", (("Location", location),))

        def _muse_store(self, key):
            # Session assets stay in StarTorch; no H1 observation or device operation.
            port = self.server.server_address[1]
            hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
            host, origin = self.headers.get("Host", ""), self.headers.get("Origin")
            if host not in hosts or (origin and origin != "http://" + host):
                raise muse_sessions.MuseError("ORIGIN_REJECTED", "请从本机 PTDS 页面操作")
            if not isinstance(key, str) or not key:
                raise muse_sessions.MuseError("INSTANCE_REQUIRED", "请选择实例")
            return muse_sessions.Store(app.inst(key))

        def _muse_error(self, exc):
            if isinstance(exc, (muse_sessions.MuseError, H1Error)):
                code, detail = exc.code, exc.detail
            else:
                code, detail = "BODY_INVALID", "请求格式不正确"
            return self._json(409 if "CONFLICT" in code else 400, {"error": code, "detail": detail})

        def _muse_get(self, path, q):
            try:
                store = self._muse_store(q.get("key"))
                if path == "/api/muse/status":
                    return self._json(200, {"status": store.status(), "sessions": store.list()})
                if path == "/api/muse/review":
                    return self._json(200, {"review": store.review(q.get("review_id"))})
                if path == "/api/muse/session":
                    return self._json(200, {"session": store.detail(q.get("asset_id"))})
                if path == "/api/muse/request":
                    return self._json(200, {"result": store.request(q.get("request_id"))})
                if path == "/api/muse/replay":
                    return self._json(200, {"replay": store.replay(q.get("asset_id"), q.get("stream"),
                                                                 int(q.get("offset", "0")), int(q.get("limit", "20")))})
                return self._json(404, {"error": "NOT_FOUND"})
            except (muse_sessions.MuseError, H1Error, ValueError, TypeError, KeyError) as exc:
                return self._muse_error(exc)

        def _muse_post(self, path):
            # Bound memory before reading JSON/base64; never accept arbitrary local paths.
            try:
                size = int(self.headers.get("Content-Length") or 0)
                if size <= 0 or size > 48 * 1024 * 1024:
                    self.close_connection = True
                    return self._json(413, {"error": "UPLOAD_TOO_LARGE", "detail": "会话文件总量不得超过32 MiB"})
                body = strict_loads(self.rfile.read(size).decode("utf-8"))
                if not isinstance(body, dict):
                    raise ValueError("BODY_INVALID")
                store = self._muse_store(body.get("key"))
                if path == "/api/muse/prepare":
                    files, total = {}, 0
                    incoming = body.get("files")
                    if not isinstance(incoming, list) or not 1 <= len(incoming) <= 32:
                        raise ValueError("BODY_INVALID")
                    for item in incoming:
                        if not isinstance(item, dict) or set(item) != {"name", "base64"}:
                            raise ValueError("BODY_INVALID")
                        name = item["name"]
                        if not isinstance(name, str) or name in files or not isinstance(item["base64"], str):
                            raise ValueError("BODY_INVALID")
                        data = base64.b64decode(item["base64"], validate=True)
                        total += len(data)
                        if total > 32 * 1024 * 1024:
                            raise muse_sessions.MuseError("UPLOAD_TOO_LARGE", "会话文件总量不得超过32 MiB")
                        files[name] = data
                    return self._json(200, {"review": store.prepare(files)})
                if path == "/api/muse/save":
                    # This explicit endpoint is the user Save action; no background admission.
                    receipt = store.save(body.get("review_id"), body.get("request_id"), body.get("review_sha256"))
                    return self._json(200, {"receipt": receipt})
                if path == "/api/muse/cancel":
                    return self._json(200, {"review": store.cancel(body.get("review_id"))})
                return self._json(404, {"error": "NOT_FOUND"})
            except (muse_sessions.MuseError, H1Error, ValueError, TypeError, KeyError) as exc:
                return self._muse_error(exc)

        def starling_off(self, path: str):
            """星灵没启用时，所有要用千问的接口统一如实回答，不连千问、不用规则拼一个答案冒充。"""
            if app.starling_on:
                return None
            if path == "/api/starling/state":
                return {"llm": False, "starting": False, "model": None, "disabled": True, "why": STARLING_OFF}
            if path in STARLING_PATHS:
                return {"state": "off", "why": STARLING_OFF}
            return None

        def _state_push(self, method, path, query):
            if not phone_tail.local_control_allowed(self):
                return self._json(403, {"error": "LOCAL_ONLY"})
            try:
                if method == "POST":
                    size = input_guard.content_length(self.headers, 8192)
                    if not size:
                        raise ValueError()
                    body = input_guard.json_object(self.rfile.read(size))
                else:
                    body = query
                key = body.get("key")
                if not isinstance(key, str) or key not in app.instances:
                    return self._json(400, {"error": "INSTANCE_UNKNOWN", "detail": "请选择有效实例"})
                route = path.removeprefix("/api/state-push/")
                if method == "GET":
                    if route == "status":
                        result = app.state_reports.status(key)
                    elif route == "report" and set(body) <= {"key", "id"}:
                        result = app.state_reports.report(key, body.get("id"))
                    elif route == "phone/status":
                        result = app.report_phone.status(key)
                    else:
                        return self._json(404, {"error": "NOT_FOUND"})
                elif route in ("save", "preview"):
                    if set(body) - {"key", "card_ids", "period_days", "time", "local_notification", "enabled"}:
                        raise ValueError()
                    params = {k: v for k, v in body.items() if k != "key"}
                    result = getattr(app.state_reports, route)(key, params)
                elif route == "pause" and set(body) == {"key", "paused"} and type(body["paused"]) is bool:
                    result = app.state_reports.pause(key, body["paused"])
                elif route == "phone/start" and set(body) == {"key"}:
                    result = app.report_phone.start(key)
                elif route == "phone/approve" and set(body) == {"key", "device_id"}:
                    result = app.report_phone.approve(key, body["device_id"])
                elif route == "phone/revoke" and set(body) == {"key", "grant_id"}:
                    result = app.report_phone.revoke(key, body["grant_id"])
                else:
                    return self._json(400, {"error": "BODY_INVALID", "detail": "请检查提交的内容"})
                return self._json(200, result)
            except (report_phone.ReportPhoneError, phone_tail.ViewerError) as exc:
                return self._json(400, {"error": "REPORT_PHONE_UNAVAILABLE", "detail": str(exc)})
            except (state_reports.ReportError, H1Error) as exc:
                return self._json(400, {"error": exc.code, "detail": exc.detail})
            except (ValueError, TypeError, KeyError) as exc:
                return self._json(400, {"error": getattr(exc, "code", "BODY_INVALID"),
                                        "detail": getattr(exc, "detail", "操作未完成，请检查配置与当前授权")})

        def do_GET(self):
            return self.dispatch_response(self._get)

        def _get(self):
            url = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            if compute_http.endpoint(self, app, "GET", url.path, q): return
            if oura_erase.asset(self, url.path): return
            if url.path == "/api/health":  # Liveness must not wait for a data transaction or snapshot build.
                return self._json(200, {"ok": True, "pid": os.getpid(), "instances": list(app.instances),
                                        "code_changed": code_stamp() != STARTED_CODE})
            if url.path.startswith('/api/state-push/'):
                return self._state_push('GET', url.path, q)
            if pillbox.handle_http(self, app, 'GET', url.path, q): return
            if url.path.startswith("/api/muse/"):
                return self._muse_get(url.path, q)
            off = self.starling_off(url.path)
            if off is not None:
                return self._json(200, off)
            if url.path in ("/api/batch/list", "/api/batch/item", "/api/batch/page"):  # 批量入库：队列、按类型确认、逐页识别结果（只读，不占全局锁）
                try:
                    inst = app.inst(q.get("key"))
                    b = app.batch(inst)
                    if url.path == "/api/batch/list":
                        return self._json(200, b.view())
                    if url.path == "/api/batch/item":
                        return self._json(200, b.detail(q["id"]))
                    return self._json(200, b.page(q["id"], int(q.get("page", "1"))))
                except H1Error as exc:
                    return self._json(400, {"error": exc.code, "detail": exc.detail})
                except (KeyError, ValueError) as exc:
                    return self._json(400, {"error": "BAD_REQUEST", "detail": str(exc)[:100]})
            if url.path == "/api/home":  # 首页文字：大标题和每张实例卡（默认 + 本机追加的改动）
                return self._json(200, home_texts.view(app.root, list(app.instances)))
            if url.path == "/api/phone-tail/status":
                if not phone_tail.local_control_allowed(self):
                    return self._json(403, {"error": "LOCAL_ONLY"})
                return self._json(200, app.phone_tail.status())
            if url.path == "/api/desktop-tail/data":
                if self.client_address[0] not in ("127.0.0.1", "::1"):
                    return self._json(403, {"error": "LOCAL_ONLY"})
                try:
                    return self._json(200, app.desktop_panels.data(q.get("panel")))
                except desktop_tail.PanelError as exc:
                    return self._json(404, {"error": "PANEL_CLOSED", "detail": str(exc)})
            if url.path == "/api/device-policy":
                return self._json(200, app.daily_policy(q.get("key")))
            if url.path == "/api/device-links":
                return self._json(200, device_links.snapshot(app, lambda inst: Sources(inst).read()))
            if url.path == "/api/band":  # Somaloop 连续个人读数及连接状态
                binding = app.band_binding()
                if not binding["instance_key"] or binding["instance_key"] not in app.instances:
                    return self._json(200, {"bridge": False, "enabled": False, "binding": binding, "error": "BAND_NOT_BOUND"})
                return self._json(200, dict(app.band().view(), bridge=bool(app.config.get("band_bridge", True))))  # 队友测试版不带腕带桥：如实说
            if url.path == "/api/band/cmd":  # 桥接 App 每几秒来问：页面有没有点“立即同步”
                return self._json(200, app.band_commands())
            if url.path == "/oauth/oura/start":  # 本人在 Oura 官方页面登录并同意
                variant = q.get("variant", app.config.get("oura", {}).get("authorize_variant", ""))
                try: client, link = oura_authorize(app, q.get("key"), variant, oura_client)
                except H1Error as exc: return self._json(400, {"error": exc.code, "detail": exc.detail})
                if link is None: return self._send(400, "Oura 接入尚未配置，请到设备的 Oura 页面复制接入提示词。".encode(), "text/plain; charset=utf-8")
                return self._redirect(link)
            if url.path in ("/oauth/oura/callback", app.oura_callback_path()):
                back = "/" if self.server.server_address[1] == app.port else f"http://127.0.0.1:{app.port}/"
                try:
                    inst = oura_connect(app, q.get("state", ""), q.get("code"), oura_client, Sources)
                    if inst is None:
                        return self._send(400, ("接入没有完成：" + q.get("error", "state 不匹配")).encode(),
                                          "text/plain; charset=utf-8")
                except Exception as exc:  # noqa: BLE001
                    code = exc.code if isinstance(exc, H1Error) else type(exc).__name__
                    app.log("oura_connect_failed", code)
                    return self._send(400, f"接入没有完成：{code}".encode(), "text/plain; charset=utf-8")
                try:  # 已接入；首次拉取失败不算接入失败，"接入设备"页显示失败原因，可以点立即同步再试
                    oura_pull(inst, lock=app.lock)
                    return self._redirect(back + "?oura=connected")
                except Exception as exc:  # noqa: BLE001
                    code = exc.code if isinstance(exc, H1Error) else type(exc).__name__
                    return self._redirect(back + "?oura=connected&pull=" + code)
            try:
                if url.path in ("/api/gene", "/api/gene/db", "/api/gene/lookup", "/api/gene/coverage"):
                    return self._json(200, gene_assets.read(GeneStore(app.inst(q["key"])), url.path, q))
                if url.path == "/api/data/read" and data_read_http.unlocked(q): return self._data_read(q)
                if url.path == "/api/starling/state": return self._json(200, starling_status.view(app))
                if url.path == "/api/sources": return self._json(200, oura_sources(app, q["key"], oura_client, Sources))
                if url.path in ("/api/torch/original", "/api/evidence/file"):
                    return preview_session.download(self, app, q, pack=url.path == "/api/evidence/file")
                with app.lock:
                    if url.path == "/favicon.ico":
                        return self._send(204, b"", "image/x-icon")
                    if url.path in ("/", "/index.html"):
                        return self._send(200, page(app), "text/html; charset=utf-8")
                    if url.path == "/api/data/read": return self._data_read(q)
                    if url.path == "/api/state/refresh":
                        return self._json(200, app.inst(q.get("key")).refresh_snapshot())
                    if url.path == "/api/state":
                        if "key" in q:
                            return self._json(200, app.inst(q["key"]).snapshot())
                        return self._json(200, {k: i.snapshot() for k, i in app.instances.items()})
                    if url.path == "/api/dict":
                        return self._json(200, app.dict_json())
                    if url.path == "/api/torch/engine":
                        return self._json(200, app.engine())
                    if url.path == "/api/cluster/list":
                        inst = app.inst(q["key"])
                        return self._json(200, inst.cluster.list(inst.now()))
                    if url.path == "/api/cluster/find":
                        inst = app.inst(q["key"])
                        grant = inst.cluster.find(q.get("id", ""), inst.now())
                        return self._json(200, grant) if grant else self._json(404, {"error": "CLUSTER_GRANT_UNKNOWN"})
                    if url.path == "/api/torch/versions":
                        return self._json(200, {"versions": evidence_graph.versions(app.inst(q["key"]), q.get("oid", ""))})
                    if url.path == "/api/track/thresholds":
                        inst = app.inst(q["key"])
                        track = open_startrack(inst.ctx)
                        try:
                            return self._json(200, {"configs": card_thresholds.configs(track), "available": custom_cards.available(track, inst.ctx, app.registry), "mac_available": any(n.channel == "MACOS" for n in app.notifiers)})
                        finally:
                            track.close()
                    if url.path == "/api/track/custom":  # 自定义状态卡：可选的指标 + 每张卡的定义、时点、提醒
                        inst = app.inst(q["key"])
                        track = open_startrack(inst.ctx)
                        try:
                            return self._json(200, {"cards": custom_cards.state(track, inst.ctx, include_off=True),
                                                    "available": custom_cards.available(track, inst.ctx, app.registry),
                                                    "methods": custom_cards.METHODS, "levels": custom_cards.LEVELS})
                        finally:
                            track.close()
                    if url.path == "/api/track/baseline":  # 状态实验室 · 整体基线洞察（只读，只在 sJIA 演示里）
                        inst = app.inst(q["key"])
                        return self._json(200, baseline_view.view(inst, lambda day: meds.on_day(inst.ctx.root, day)))
                    if url.path == "/api/track/retro":  # 回溯式重计算：历次计算并排（只读）
                        inst = app.inst(q["key"])
                        if not inst.sjia:
                            return self._json(200, {"tps": [], "why": "NO_SJIA_CARD"})
                        return self._json(200, retro.history(inst))
                    if url.path == "/api/track/compete":  # 竞争性解释：内存里按不同规则 / 假设各算一遍，不写星轨
                        inst = app.inst(q["key"])
                        if not inst.sjia:
                            return self._json(200, {"found": False, "tps": [], "why": "NO_SJIA_CARD"})
                        tp = q.get("tp") or (compete.tps_of(inst) or [""])[-1]
                        return self._json(200, compete.explain(inst, tp))
                    if url.path == "/api/starling/page":  # 星灵解读：只在我点了按钮后写（start=1）；只用记录，不含健康数值
                        inst = app.inst(q["key"])
                        pg, snap = q.get("page", ""), inst.snapshot()
                        try:
                            c = page_ctx(app, inst, snap, pg, q.get("card") or "sjia-mas", q.get("tp", ""), q.get("dk", ""))
                            if c is None:
                                return self._json(200, {"state": "none"})
                        except KeyError:
                            return self._json(400, {"error": "PAGE_UNKNOWN"})
                        except starling.RawValueInContext:
                            app.log("starling_page_blocked", pg)
                            return self._json(200, {"state": "blocked", "why": "记录里混进了健康数值，这次不交给星灵"})
                        return self._json(200, dict(compete_ai.status(app.llm, inst.ctx.root, c, q.get("start") == "1"), page=pg, facts=[f for f, _ in c["facts"]],
                                                    sign=starling_page.sign(app.llm) if app.llm else "星灵"))
                    if url.path in ("/api/track/retro_branches", "/api/track/retro_ai"):  # 回溯式重计算的时间分叉（内存里算，不写库）+ 千问版本
                        inst = app.inst(q["key"])
                        if not inst.sjia:
                            return self._json(200, {"found": False, "why": "NO_SJIA_CARD", "state": "none"})
                        b = retro.branches(inst)
                        if url.path == "/api/track/retro_branches" or not b.get("found"):
                            return self._json(200, b if url.path == "/api/track/retro_branches" else {"state": "none"})
                        return self._json(200, dict(compete_ai.status(app.llm, inst.ctx.root, b, q.get("start") != "0"), tp="RETRO"))
                    if url.path == "/api/track/compete_ai":  # 竞争性解释的千问版本：后台写、逐句核对，只读
                        inst = app.inst(q["key"])
                        if not inst.sjia:
                            return self._json(200, {"state": "none"})
                        tp = q.get("tp") or (compete.tps_of(inst) or [""])[-1]
                        c = compete.explain(inst, tp)
                        if not c.get("found"):
                            return self._json(200, {"state": "none"})
                        return self._json(200, dict(compete_ai.status(app.llm, inst.ctx.root, c, q.get("start") != "0"), tp=tp))
                    if url.path == "/api/graph/document":
                        return self._json(200, evidence_navigation.document(app.inst(q.get("key")), q.get("doc", "")))
                    if url.path == "/api/graph/observation":
                        return self._json(200, evidence_navigation.observation(app.inst(q.get("key")), q.get("oid", ""), q.get("revision")))
                    if url.path == "/api/graph/related":
                        inst = app.inst(q.get("key"))
                        if q.get("kind") == "party":
                            selected = [dict(id=g["id"], grant_id=g["id"], title=g.get("purpose") or g["id"],
                                             status=g.get("status"), at=g.get("created_at"))
                                        for g in inst.cluster.list(inst.now()) if g.get("object") == q.get("id")]
                            selected.sort(key=lambda r: str(r.get("at") or r["id"]), reverse=True)
                            total = len(selected)
                        elif q.get("kind") == "channel":
                            track = open_startrack(inst.ctx)
                            try:
                                total = track.execute("SELECT count(*) FROM alert_delivery WHERE channel=?", (q.get("id"),)).fetchone()[0]
                                selected = [dict(zip(("id", "dedupe_key", "card_id", "tp", "title", "status", "at"), r))
                                    for r in track.execute("SELECT d.id,d.dedupe_key,a.card_id,a.tp_date,a.title,d.outcome,d.attempted_at "
                                        "FROM alert_delivery d JOIN alert_log a USING(dedupe_key) WHERE d.channel=? ORDER BY d.id DESC LIMIT 100", (q.get("id"),))]
                            finally:
                                track.close()
                        else:
                            raise H1Error("GRAPH_TARGET_INVALID", "关联内容类型无效")
                        return self._json(200, {"total": total, "items": selected[:100]})
                    if url.path == "/api/graph/read":
                        inst = app.inst(q["key"])
                        try:
                            limit = int(q.get("limit", "50"))
                        except (TypeError, ValueError):
                            raise H1Error("GRAPH_LIMIT_INVALID", "每页记录数无效")
                        receipts = []
                        if q.get("view") != "cards" and q.get("lane", "data") == "data":
                            try:
                                receipts = app.bridge(inst).receipts()
                            except Exception:  # noqa: BLE001 — same optional bridge as legacy graph
                                pass
                        return self._json(200, graph_read.read(inst, q.get("view", ""),
                            lane=q.get("lane", ""), cursor=q.get("cursor", ""), limit=limit, receipts=receipts))
                    if url.path in ("/api/graph", "/api/graph/trace", "/api/graph/kg"):  # 证据图谱：只读拼接各账本已有的记录
                        inst = app.inst(q.get("key"))
                        # A trace needs delivery evidence, not every observation or card computation.
                        snap = (graph_read.audit_context(inst) if url.path == "/api/graph/trace" else
                                graph_read.knowledge_context(inst) if url.path == "/api/graph/kg" else inst.snapshot())
                        records, grants = inst.cluster.authorization_view(snap, inst.now())
                        if url.path == "/api/graph/kg":
                            return self._json(200, evidence_graph.hide_kg(evidence_graph.knowledge(
                                inst, snap, records, grants, GeneStore(inst).list(), inst.cluster.objects), evidence_graph.hidden_cards(inst)))
                        if url.path == "/api/graph/trace":
                            if (q.get("card") or "sjia-mas") in evidence_graph.hidden_cards(inst):
                                return self._json(200, {"tp": q.get("tp", ""), "found": False})
                            tr = evidence_graph.trace(inst, q.get("tp", ""), records, grants, card_id=q.get("card") or "sjia-mas", run_id=q.get("run_id"))
                            if tr.get("found"):  # 这个数可信吗：现场按同一版定义再算一遍，和存下的比（不写库）
                                try:
                                    tr["verify"] = evidence_pack.verify_one(inst, tr["card_id"], tr["tp"], tr["run"]["run_id"])
                                except Exception as exc:  # noqa: BLE001
                                    app.log("verify_failed", type(exc).__name__)
                                    tr["verify"] = {"state": "NONE"}
                            return self._json(200, tr)
                        try:
                            receipts = app.bridge(inst).receipts()
                        except Exception:  # noqa: BLE001
                            receipts = []
                        hidden = evidence_graph.hidden_cards(inst)
                        return self._json(200, {
                            "metric": evidence_graph.traceable(inst, hidden),
                            "timepoints": [{"tp": t["tp"], "level": t["level"], "level_zh": t.get("level_zh"),
                                            "status": t["status"]} for t in snap.get("timepoints") or []],
                            "cards": ([{"card_id": "sjia-mas", "name": "sJIA 关注卡",
                                        "timepoints": [{"tp": t["tp"], "level": t["level"], "level_zh": t.get("level_zh"),
                                                        "status": t["status"]} for t in snap.get("timepoints") or []]}]
                                      if inst.sjia and "sjia-mas" not in hidden else []) +
                                     [{"card_id": c["card_id"], "name": c["name"],
                                       "timepoints": [{"tp": t["tp"], "level": t["level"], "level_zh": t["level_zh"], "status": t["status"]}
                                                      for t in reversed(c["timepoints"]) if t["level"]]}
                                      for c in snap.get("custom_cards") or []] +
                                     evidence_graph.engine_cards(inst),
                            "events": [e for e in evidence_graph.events(inst, records, GeneStore(inst).list(), receipts,
                                                                        snap.get("device_events") or [], Sources(inst).read())
                                       if (e.get("ref") or {}).get("card") not in hidden]})
                    if url.path == "/api/starling/memory":  # 我的记忆：当前主体下保存的记忆和删除凭证
                        inst = app.inst(q["key"])
                        ms = None if inst.spec.get("replay") else mem_store(app, inst)
                        if ms is None:
                            return self._json(200, {"enabled": False, "items": [], "deleted": []})
                        try:
                            out = ms.list(q.get("subject") or "default")
                        except starling_memory.MemoryError_ as exc:
                            return self._json(400, {"error": exc.code, "detail": exc.detail})
                        return self._json(200, dict(out, enabled=True, embed_ready=ms.emb.available(),
                                                    embed_model=Path(ms.emb.model).name if ms.emb.model else ""))
                    if url.path == "/api/cluster/shares":  # 授权图片：能选什么 + 记过的授权
                        inst = app.inst(q["key"])
                        snap = inst.snapshot()
                        hidden = evidence_graph.hidden_cards(inst)
                        tps = compete.tps_of(inst) if inst.sjia and "sjia-mas" not in hidden else []
                        return self._json(200, dict(share.listing(inst.ctx.root), options=share.options(snap, tps, hidden),
                                                    replay=bool(inst.spec.get("replay"))))
                    if url.path == "/api/cluster/records":
                        inst = app.inst(q["key"])
                        return self._json(200, inst.cluster.records(None if q.get("lifecycle") == "1" else inst.snapshot(), egress_only=q.get("egress") == "1"))
                    if url.path == "/api/bridge/state":
                        return self._json(200, app.bridge(app.inst(q["key"])).state())
                    if url.path == "/api/evidence/last":  # 系统自检：最近一次的结果（证据包留在后台，不在界面下载）
                        return self._json(200, {"last": evidence_pack.last_check(app.root)})
                    if url.path == "/api/evidence/list":
                        return self._json(200, {"packs": evidence_pack.list_packs(app.root), "folder": str(app.root / "evidence")})
                    if url.path == "/api/profile":
                        return self._json(200, bioage.load_profile(app.inst(q.get("key")).ctx.root))
                    if url.path == "/api/meds":  # 用药记录（只读）：疗程、事件、用药区间、指纹链核对
                        with app.lock:
                            return self._json(200, meds.courses(app.inst(q.get("key")).ctx.root))
                    if url.path in ("/api/rules", "/api/track/engines/check"):  # 状态规则库（只读）/ 状态工程“绑数据”一键检查
                        inst = app.inst(q.get("key"))
                        track = open_startrack(inst.ctx)
                        try:
                            if url.path == "/api/rules":
                                custom = custom_cards.cards(track)
                                for c in custom:
                                    c["rule_zh"] = custom_cards.rule_zh(c["definition"])
                                return self._json(200, {"sets": rule_registry.SETS, "rules": rule_registry.rows(
                                    app.registry, engines.used_by(track, False), custom)})
                            try:
                                return self._json(200, engines.check(custom_cards.by_code(track, inst.ctx), app.registry,
                                                                     inst.ctx.root, q.get("tpl", ""), sjia=False))
                            except engines.EngineError as exc:
                                return self._json(400, {"error": exc.code, "detail": exc.detail})
                        finally:
                            track.close()
                    if url.path == "/api/notes":
                        import ui_notes
                        if q.get("format") == "md":
                            data = ui_notes.markdown(app.root).encode("utf-8")
                            return self._send(200, data, "text/markdown; charset=utf-8",
                                              (("Content-Disposition", 'attachment; filename="ptds-ui-notes.md"'),))
                        return self._json(200, {"notes": ui_notes.list_notes(app.root), "file": str(ui_notes.path(app.root))})
            except H1Error as exc:
                return self._json(400, {"error": exc.code, "detail": exc.detail})
            return self._json(404, {"error": "NOT_FOUND"})

        def _data_read(self, q):
            return self._json(200, data_read_http.dispatch(app, q, GeneStore))

        def _torch_result(self, inst, body, operation, result):
            return compute_http.result(self, inst, body, operation, result)

        def do_POST(self):
            return self.dispatch_response(self._guarded_post)

        def _guarded_post(self):
            try:
                with input_guard.request_body(self, urlparse(self.path).path, app.config), save_delivery_scope(
                        urlparse(self.path).path in ("/api/torch/table", "/api/torch/save", "/api/torch/correct", "/api/torch/retract"),
                        lambda exc: app.log("delivery_failed", type(exc).__name__)):
                    return self._post()
            except input_guard.RequestError as exc:
                self.close_connection = True
                return self._json(exc.status, {"error": exc.code})
            except H1Error as exc:
                self.close_connection = True
                return self._json(400, {"error": exc.code, "detail": exc.detail})

        def _post(self):
            if self.headers.get("X-PTDS") != "1":
                return self._json(403, {"error": "MISSING_X_PTDS_HEADER"})
            url = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(url.query, keep_blank_values=True).items()}
            if compute_http.endpoint(self, app, "POST", url.path, q): return
            if oura_erase.endpoint(self, app, url.path): return
            if url.path == "/api/data/read":
                # Read transport only: existing body admission applies before the
                # business lock. No save, sync, or write receipt is involved.
                body = input_guard.json_object(self.rfile.read())
                if set(body) != {"preview_receipts"} or not isinstance(body["preview_receipts"], str):
                    raise input_guard.RequestError("BODY_INVALID")
                q["preview_receipts"] = body["preview_receipts"]
                if data_read_http.unlocked(q): return self._data_read(q)
                with app.lock: return self._data_read(q)
            if url.path.startswith('/api/state-push/'):
                return self._state_push('POST', url.path, q)
            if pillbox.handle_http(self, app, 'POST', url.path, q): return
            if url.path.startswith("/api/phone-tail/"):
                if not phone_tail.local_control_allowed(self):
                    return self._json(403, {"error": "LOCAL_ONLY"})
                try:
                    size = int(self.headers.get("Content-Length") or 0)
                    if not 1 <= size <= 8192 or self.headers.get("Transfer-Encoding"):
                        return self._json(413, {"error": "BODY_TOO_LARGE"})
                    body = input_guard.json_object(self.rfile.read(size))
                    if not isinstance(body, dict):
                        raise ValueError()
                    if url.path == "/api/phone-tail/start":
                        result = app.phone_tail.start(body)
                    elif url.path == "/api/phone-tail/approve":
                        with app.phone_tail.lock:
                            app.phone_tail.require_control(body)
                            result = app.phone_tail.approve(body.get("confirmation"))
                    elif url.path == "/api/phone-tail/remove-device":
                        with app.phone_tail.lock:
                            app.phone_tail.require_control(body)
                            result = app.phone_tail.remove_device(body.get("device_id"))
                    elif url.path == "/api/phone-tail/invite":
                        result = app.phone_tail.invite(body)
                    elif url.path == "/api/phone-tail/stop":
                        with app.phone_tail.lock:
                            app.phone_tail.require_control(body)
                            result = app.phone_tail.end_share()
                    else:
                        return self._json(404, {"error": "NOT_FOUND"})
                    return self._json(200, result)
                except (phone_tail.ViewerError, desktop_tail.PanelError, H1Error) as exc:
                    return self._json(400, {"error": "PHONE_VIEW_UNAVAILABLE", "detail": str(exc)})
                except (ValueError, TypeError, KeyError):
                    return self._json(400, {"error": "BODY_INVALID", "detail": "请求格式不正确"})
            if url.path.startswith("/api/muse/"):
                return self._muse_post(url.path)
            off = self.starling_off(url.path)
            if off is not None:
                return self._json(200, off)
            length = int(self.headers.get("Content-Length") or 0)
            if url.path == "/api/garmin/sync-state":
                if not phone_tail.local_control_allowed(self):
                    return self._json(403, {"error": "LOCAL_ONLY"})
                if not 0 < length <= 4096:
                    return self._json(413, {"error": "BODY_TOO_LARGE"})
                try:
                    body = input_guard.json_object(self.rfile.read(length))
                    if set(body) != {"key","status","last_error","last_success","last_attempt"}:
                        raise ValueError()
                    if body["status"] not in ("CONNECTED","SYNCING","RETRY_WAIT","NEEDS_REAUTH"):
                        raise ValueError()
                    if body["last_error"] is not None and not re.fullmatch(r"[A-Z0-9_]{1,80}",body["last_error"]):
                        raise ValueError()
                    for field in ("last_success","last_attempt"):
                        if body[field] is not None:
                            parsed = datetime.fromisoformat(body[field])
                            if parsed.tzinfo is None: raise ValueError()
                    with app.lock:
                        inst=device_targets.resolve(app, 'garmin', body.get('key'))
                        Sources(inst).update("garmin",status="NEEDS_REAUTH" if body["status"]=="NEEDS_REAUTH" else "CONNECTED",
                                             sync_status=body["status"],sync_error=body["last_error"],
                                             last_pull_at=body["last_success"],last_attempt_at=body["last_attempt"],poll_seconds=300)
                    return self._json(200,{"ok":True})
                except (H1Error,ValueError,TypeError,KeyError) as exc:
                    return self._json(400,{"error":exc.code if isinstance(exc,H1Error) else "GARMIN_STATE_INVALID"})
            if url.path in ("/api/somaloop-agent/admit", "/api/somaloop-agent/state"):
                if app.config.get("band_bridge") is True and device_targets.configured_key(app, "somaloop_agent") is not None and app.config.get("band_instance_key") == device_targets.configured_key(app, "somaloop_agent"):
                    return self._json(409, {"error":"SOMALOOP_PHONE_PAUSED", "detail":"当前使用 Mac 腕带桥，手机同步已暂停"})
                if not phone_tail.local_control_allowed(self):
                    return self._json(403, {"error":"LOCAL_ONLY"})
                if not 0 < length <= 12*1024*1024:
                    return self._json(413, {"error":"BODY_TOO_LARGE"})
                try:
                    body=input_guard.json_object(self.rfile.read(length))
                    with app.lock:
                        inst=device_targets.resolve(app, 'somaloop_agent', body.get('key'))
                    if url.path.endswith('/admit'):
                        app.require_device_raw(inst.spec['key'])
                        result=somaloop_agent_ingest.admit(inst,body,lock=app.lock)
                        with app.lock:
                            Sources(inst).update('somaloop',transport='phone_agent',display_name='Somaloop',last_import_at=inst.now())
                    else:
                        with app.lock:
                            if set(body)!={'key','status','device_connected'} or body['status'] not in ('CONNECTED','ERROR','NEEDS_REAUTH') or type(body['device_connected']) is not bool:
                                raise ValueError()
                            fields=dict(status=body['status'],transport='phone_agent',display_name='Somaloop',device_connected=body['device_connected'],poll_seconds=60,last_attempt_at=inst.now())
                            if body['status']=='CONNECTED':fields.update(last_pull_at=inst.now(),last_error=None,sync_error=None)
                            Sources(inst).update('somaloop',**fields)
                            result={'ok':True}
                    return self._json(200,result)
                except (H1Error,ValueError,TypeError,KeyError) as exc:
                    return self._json(400,{'error':exc.code if isinstance(exc,H1Error) else 'SOMALOOP_AGENT_INVALID'})
            if url.path == "/api/qkeer/sync-state":
                if not phone_tail.local_control_allowed(self):
                    return self._json(403, {"error": "LOCAL_ONLY"})
                if not 0 < length <= 4096:
                    return self._json(413, {"error": "BODY_TOO_LARGE"})
                try:
                    body = input_guard.json_object(self.rfile.read(length))
                    if set(body) != {"key", "status"} or body["status"] not in ("CONNECTED", "ERROR", "NEEDS_REAUTH"):
                        raise ValueError()
                    with app.lock:
                        inst = device_targets.resolve(app, 'qkeer', body.get('key'))
                        fields = {"status": body["status"], "display_name": "QKeer", "last_attempt_at": inst.now()}
                        if body["status"] == "CONNECTED": fields["last_pull_at"] = inst.now()
                        Sources(inst).update("qkeer", **fields)
                    return self._json(200, {"ok": True})
                except (H1Error, ValueError, TypeError, KeyError) as exc:
                    return self._json(400, {"error": exc.code if isinstance(exc,H1Error) else "QKEER_STATE_INVALID"})
            if url.path == "/api/qkeer/admit":
                if not phone_tail.local_control_allowed(self):
                    return self._json(403, {"error": "LOCAL_ONLY"})
                if not 0 < length <= 2 * 1024 * 1024:
                    return self._json(413, {"error": "BODY_TOO_LARGE"})
                try:
                    body = input_guard.json_object(self.rfile.read(length))
                    with app.lock:
                        inst = device_targets.resolve(app, 'qkeer', body.get('key'))
                        app.require_device_raw(inst.spec['key'])
                        result = qkeer_ingest.admit(inst, body)
                        Sources(inst).update("qkeer", status="CONNECTED", last_import_at=inst.now(),
                                             last_pull_at=inst.now(), display_name="QKeer")
                    return self._json(200, result)
                except (H1Error, ValueError, TypeError, KeyError) as exc:
                    return self._json(400, {"error": exc.code if isinstance(exc, H1Error) else "QKEER_BODY_INVALID"})
            if url.path == "/api/garmin/admit":
                if not phone_tail.local_control_allowed(self):
                    return self._json(403, {"error": "LOCAL_ONLY"})
                if not 0 < length <= 16 * 1024 * 1024:
                    return self._json(413, {"error": "BODY_TOO_LARGE"})
                try:
                    body = input_guard.json_object(self.rfile.read(length))
                    with app.lock:
                        inst = device_targets.resolve(app, 'garmin', body.get('key'))
                        app.require_device_raw(inst.spec['key'])
                        result = garmin_ingest.admit(inst, body)
                        Sources(inst).update("garmin", status="CONNECTED", last_import_at=inst.now(),
                                             last_receipt={k:result[k] for k in ("category","day","status","projected")})
                    return self._json(200, result)
                except (H1Error, ValueError, TypeError, KeyError) as exc:
                    return self._json(400, {"error": exc.code if isinstance(exc, H1Error) else "GARMIN_BODY_INVALID"})
            if url.path == "/api/desktop-tail/open":
                origin = self.headers.get("Origin")
                allowed = (f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}")
                if self.client_address[0] not in ("127.0.0.1", "::1") or (origin and origin not in allowed):
                    return self._json(403, {"error": "LOCAL_ONLY"})
                if length < 1 or length > 8192:
                    return self._json(413, {"error": "BODY_TOO_LARGE"})
                try:
                    body = input_guard.json_object(self.rfile.read(length))
                    if not isinstance(body, dict):
                        raise desktop_tail.PanelError("请求需要一个对象")
                    if body.get("device") == "pillbox" and not phone_tail.local_control_allowed(self):
                        return self._json(403, {"error": "LOCAL_ONLY"})
                    return self._json(200, app.desktop_panels.open(body, self.server.server_port))
                except (desktop_tail.PanelError, ValueError, TypeError, OSError) as exc:
                    return self._json(400, {"error": "PANEL_UNAVAILABLE", "detail": str(exc)[:160]})
            if url.path == "/api/starling/weekly-focus":
                if not phone_tail.local_control_allowed(self):
                    return self._json(403, {"state":"error", "why":"仅允许本机页面请求"})
                if length > 4096:
                    return self._json(413, {"state":"error", "why":"请求过大"})
                try:
                    body = input_guard.json_object(self.rfile.read(length))
                    if set(body) != {"key"} or not isinstance(body["key"], str):
                        raise ValueError("BODY_INVALID")
                    with app.lock:
                        inst = app.inst(body["key"])
                        report = starling_weekly.build(inst.snapshot(), inst.now(), inst.ctx.tz)
                except (ValueError, KeyError, TypeError):
                    return self._json(400, {"state":"error", "why":"当前关注或实例不可用，请刷新后重试"})
                return self._json(200, starling_weekly.summarize(app.llm, report))
            if url.path == "/api/starling/baseline":
                if length > 32768:
                    return self._json(413, {"error": "SELECTION_TOO_LARGE"})
                try:
                    body = input_guard.json_object(self.rfile.read(length))
                    inst = app.inst(body["key"])
                    b = baseline_view.view(inst)
                    facts = starling_baseline.context(b, body["rows"])
                except (ValueError, KeyError, TypeError, StopIteration):
                    return self._json(400, {"error": "SELECTION_STALE", "why": "当前选择已变化或不可用，请刷新后重新总结"})
                return self._json(200, starling_baseline.summarize(app.llm, facts))
            if url.path == "/api/home":  # 首页齿轮：改大标题 / 改一张卡 / 恢复默认（只追加）
                try:
                    body = input_guard.json_object(self.rfile.read(length))
                    home_texts.save(app.root, body, datetime.now(timezone.utc).isoformat(timespec="seconds"))
                    app.log("home_text", str(body.get("target"))[:40], "reset" if body.get("reset") else "edit")
                    return self._json(200, home_texts.view(app.root, list(app.instances)))
                except home_texts.HomeError as exc:
                    return self._json(400, {"error": exc.code, "detail": exc.detail})
                except ValueError:
                    return self._json(400, {"error": "BODY_INVALID"})
            if url.path == "/api/gene/delete":
                try:
                    body = input_guard.json_object(self.rfile.read(length))
                    return self._json(200, gene_assets.erase(GeneStore(app.inst(q["key"])), body.get("sha256")))
                except H1Error as exc:
                    return self._json(400, {"error": exc.code})
            if url.path == "/api/gene":  # 基因原始数据可能很大：边收边写，不整份读进内存，也不占全局锁
                from urllib.parse import unquote
                try:
                    name = unquote(self.headers.get("X-File-Name", "upload.bin"))
                    return self._json(200, GeneStore(app.inst(q["key"])).write_stream(name, self.rfile, length, q.get("nature")))
                except H1Error as exc:
                    self.close_connection = True
                    return self._json(400, {"error": exc.code, "detail": exc.detail})
            if url.path == "/api/batch/add":  # 批量入库：边收边写，几百 MB 的导出也不整份读进内存；不占全局锁
                from urllib.parse import unquote
                try:
                    inst = app.inst(q.get("key"))
                    input_guard.require_writable(inst)
                    b = app.batch(inst)
                    it = b.add_stream(unquote(self.headers.get("X-File-Name", "file")), unquote(self.headers.get("X-File-Rel", "")),
                                      self.rfile, length)
                    return self._json(200, {"item": it})
                except H1Error as exc:
                    return self._json(400, {"error": exc.code, "detail": exc.detail})
            raw = self.rfile.read(length) if length else b""
            if url.path in ("/api/device/latest", "/api/device/daily/admit", "/api/band/live", "/api/band/daily"):
                if not phone_tail.local_control_allowed(self):
                    return self._json(403, {"error": "LOCAL_CONTROL_REQUIRED"})
                try:
                    import device_daily
                    if len(raw) > 262144:
                        raise ValueError("DAILY_BODY_TOO_LARGE")
                    body = input_guard.json_object(raw)
                    if url.path == "/api/band/daily":
                        with app.lock:
                            return self._json(200, app.band_daily_admit(body))
                    if url.path == "/api/band/live":
                        return self._json(200, app.band_live(body))
                    key = body.get("key")
                    if not app.daily_policy(key)["enabled"]:
                        raise ValueError("DAILY_POLICY_DISABLED")
                    inst = app.inst(key)
                    input_guard.require_writable(inst)
                    if url.path == "/api/device/latest":
                        if set(body) != {"key", "source_kind", "items"} or not isinstance(body["items"], list) or len(body["items"]) > 64:
                            raise ValueError("LATEST_BODY_INVALID")
                        if body["items"]:
                            device_daily.cache_latest_batch(inst, body["source_kind"], body["items"])
                        return self._json(200, {"ok": True, "persisted": False})
                    if body.get("day", "") < app.daily_policy(key)["cutover_day"]:
                        raise ValueError("BEFORE_DAILY_CUTOVER")
                    with app.lock:
                        result = device_daily.admit(inst, body)
                    return self._json(200, result)
                except (ValueError, TypeError, KeyError, H1Error) as exc:
                    return self._json(400, {"error": getattr(exc, "code", "DAILY_INPUT_INVALID"), "detail": "日汇总或最近读数格式不符合当前接收策略"})
            if url.path == "/api/device-links/action":
                if not phone_tail.local_control_allowed(self):
                    return self._json(403, {"error": "LOCAL_ONLY"})
                try:
                    result = device_links.retry(app, input_guard.json_object(raw), lambda inst: Sources(inst).read(),
                                                oura_retry=app.retry_oura, bridge_retry=app.start_band_bridge)
                    return self._json(200, result)
                except ValueError as exc:
                    return self._json(409, {"error": str(exc), "detail": "当前设备需要处理连接设置，请查看详情"})
                except Exception:
                    return self._json(503, {"error": "DEVICE_RETRY_UNAVAILABLE", "detail": "暂时无法启动恢复，请查看连接详情"})
            if url.path in ("/api/band/push", "/api/band/next", "/api/band/history", "/api/band/sync"):
                # 连续个人读数：旧切换入口明确停用，不清空、不增加分段
                try:
                    if app.config.get("band_bridge", True) is False and url.path != "/api/band/next":
                        return self._json(409, {"error": "BAND_BRIDGE_DISABLED", "detail": "当前演示已关闭腕带数据接入"})
                    binding = app.band_binding()
                    if binding["paused"]:
                        return self._json(409, {"error": "BAND_PAUSED"})
                    if url.path in ("/api/band/push", "/api/band/history"):
                        payload = input_guard.json_object(raw)
                        if ((app.config.get("band_require_generation") is True or payload.get("delivery_id")) and
                                payload.get("binding_generation") != binding["generation"]):
                            return self._json(409, {"error": "BAND_BINDING_CHANGED", "detail": "接收目标已变化，请核对腕带桥待发送记录"})
                    if url.path == "/api/band/next":
                        return self._json(410, {"error": "CONTINUOUS_PERSONAL", "detail": "已改为连续个人读数，不再切换体验者"})
                    if url.path == "/api/band/sync":
                        return self._json(200, app.band().request_sync())
                    if url.path == "/api/band/history":
                        app.require_device_raw(binding["instance_key"])
                        return self._json(200, app.band().push_history(input_guard.json_object(raw)))
                    if payload.get("type") != "status":
                        app.require_device_raw(binding["instance_key"], payload, band=True)
                    return self._json(200, app.band().push(input_guard.json_object(raw)))
                except H1Error as exc:
                    return self._json(409, {"error": exc.code, "detail": exc.detail})
                except (ValueError, TypeError) as exc:
                    return self._json(400, {"error": "BAD_REQUEST", "detail": str(exc)[:100]})
            if url.path.startswith("/api/batch/"):  # 批量入库：确认、配列、暂停（只改队列，保存在后台按计划做）
                body = input_guard.json_object(raw)
                try:
                    inst = app.inst(body.get("key") or q.get("key"))
                    input_guard.require_writable(inst)
                    b = app.batch(inst)
                    if url.path == "/api/batch/confirm":
                        return self._json(200, {"item": b.confirm(body["id"], body.get("decisions") or {}, body.get("conflicts") or {})})
                    if url.path == "/api/batch/mapping":
                        return self._json(200, {"item": b.set_mapping(body["id"], body.get("columns") or [])})
                    if url.path == "/api/batch/page_saved":
                        return self._json(200, {"item": b.mark_page(body["id"], int(body["page"]), body.get("counts") or {})})
                    if url.path == "/api/batch/skip":
                        return self._json(200, {"item": b.skip(body["id"])})
                    if url.path == "/api/batch/retry":
                        return self._json(200, {"item": b.retry(body["id"])})
                    if url.path == "/api/batch/pause":
                        return self._json(200, b.set_paused(bool(body.get("on"))))
                    return self._json(404, {"error": "NOT_FOUND"})
                except H1Error as exc:
                    return self._json(400, {"error": exc.code, "detail": exc.detail})
                except (KeyError, ValueError) as exc:
                    return self._json(400, {"error": "BAD_REQUEST", "detail": str(exc)[:100]})
            if url.path == "/api/profile":  # 个人信息（出生日期、性别）：生物年龄引擎用，实例目录旁路文件，只追加
                body = input_guard.json_object(raw)
                try:
                    with app.lock:
                        inst = app.inst(body.get("key"))
                        input_guard.require_writable(inst)
                        row = bioage.save_profile(inst.ctx.root, body)
                        if not inst.spec.get("replay"):  # 个人信息变了 = 用到它的规则定义变了，按新定义重算（旧结果保留）
                            inst.sync_track("PROFILE")
                        return self._json(200, {"profile": row, "snapshot": inst.snapshot()})
                except ValueError as exc:
                    return self._json(400, {"error": str(exc)})
            if url.path in ("/api/meds", "/api/meds/amend"):  # 用药记录：只追加；不交给星灵，不进任何阈值（产品负责人 2026-10-14）
                try:
                    body = input_guard.json_object(raw)
                    if not isinstance(body, dict):
                        raise meds.MedError("BODY_INVALID", "内容格式不对")
                    with app.lock:
                        inst = app.inst(body.get("key"))
                        if inst.spec.get("replay"):
                            return self._json(400, {"error": "REPLAY_INSTANCE"})
                        nature = inst.nature
                        now = inst.now()
                        fn = meds.record if url.path == "/api/meds" else meds.amend
                        return self._json(200, fn(inst.ctx.root, body, now=now, today=now[:10], nature=nature))
                except meds.MedError as exc:
                    return self._json(400, {"error": exc.code, "detail": exc.detail})
                except H1Error as exc:
                    return self._json(400, {"error": exc.code})
                except ValueError:
                    return self._json(400, {"error": "BODY_INVALID"})
            if url.path == "/api/alerts/calendar":  # 规则提醒 → 加到日历：Mac 上用“日历”打开，我点“添加”才加（不写数值）
                try:
                    body = input_guard.json_object(raw)
                    if not isinstance(body, dict):
                        raise ValueError("BODY_INVALID")
                    with app.lock:
                        inst = app.inst(body.get("key"))
                        if inst.spec.get("replay"):
                            return self._json(400, {"error": "REPLAY_INSTANCE"})
                        dk = str(body.get("dedupe_key") or "")
                        if not any(a["dedupe_key"] == dk for a in inst.snapshot().get("alerts") or []):  # 提醒列表里有就行（卡组新结果的提醒等级是 NONE，原来会被拒，产品负责人 2026-10-15 报错）
                            return self._json(400, {"error": "ALERT_UNKNOWN"})
                        now = datetime.now(ZoneInfo(inst.ctx.tz))
                        res = rule_notice.calendar(inst.ctx.root, dk, str(body.get("date") or ""), str(body.get("time") or ""),
                                                   now.date(), now, inst.ctx.tz)
                    opened = False
                    if sys.platform == "darwin" and not body.get("download"):
                        import subprocess  # noqa: PLC0415
                        opened = subprocess.run(["open", res["path"]], check=False, timeout=10).returncode == 0
                    app.log("calendar_ics", inst.ctx.instance_id, res["day"], "opened" if opened else "download")
                    return self._json(200, {"opened": opened, "day": res["day"], "time": res["time"], "file": res["file"],
                                            "ics": None if opened else res["ics"]})
                except H1Error as exc:
                    return self._json(400, {"error": exc.code})
                except ValueError as exc:
                    return self._json(400, {"error": str(exc) if str(exc) in ("DATE_RANGE", "BODY_INVALID") else "BODY_INVALID"})
            if url.path in ("/api/cluster/share", "/api/cluster/share/revoke"):  # 授权图片：记一条授权（只追加）；回放实例不记
                try:
                    body = input_guard.json_object(raw)
                    if not isinstance(body, dict):
                        raise share.ShareError("BODY_INVALID", "")
                    with app.lock:
                        inst = app.inst(body.get("key"))
                        if inst.spec.get("replay"):
                            return self._json(400, {"error": "REPLAY_INSTANCE"})
                        now = inst.now()
                        if url.path.endswith("/revoke"):
                            return self._json(200, share.revoke(inst.ctx.root, str(body.get("share_id") or ""), now))
                        snap = inst.snapshot()
                        hidden = evidence_graph.hidden_cards(inst)
                        ok_x = inst.sjia and "sjia-mas" not in hidden
                        content = share.payload(snap, body.get("items") or [], bool(body.get("with_change")),
                                                lambda tp: compete.explain(inst, tp) if ok_x else None, hidden)
                        nature = inst.nature
                        res = share.create(inst.ctx.root, body, content, now, nature)
                        app.log("share_image", inst.ctx.instance_id, res["share"]["share_id"])
                        return self._json(200, res)
                except share.ShareError as exc:
                    return self._json(400, {"error": exc.code, "detail": exc.detail})
                except H1Error as exc:
                    return self._json(400, {"error": exc.code})
                except ValueError:
                    return self._json(400, {"error": "BODY_INVALID"})
            if url.path == "/api/starling/memory":  # 星灵记忆：记住 / 更正 / 忘记 / 核对删除（只写独立的 memory.db）
                try:
                    body = input_guard.json_object(raw)
                    if not isinstance(body, dict):
                        raise starling_memory.MemoryError_("BODY_INVALID")
                    inst = app.inst(body.get("key"))
                    ms = None if inst.spec.get("replay") else mem_store(app, inst)
                    if ms is None:
                        return self._json(400, {"error": "FEATURE_OFF" if not inst.spec.get("replay") else "REPLAY_INSTANCE"})
                    op, subj, now = body.get("op"), body.get("subject") or "default", inst.now()
                    if op == "remember":
                        if body.get("confirmed") is not True:  # 只有我明确点了“确认记住”才写
                            return self._json(400, {"error": "NOT_CONFIRMED"})
                        out = ms.remember(subj, body.get("text"), body.get("source") or "星灵浮窗 · 用户确认", now)
                    elif op == "correct":
                        if body.get("confirmed") is not True:
                            return self._json(400, {"error": "NOT_CONFIRMED"})
                        out = ms.correct(subj, str(body.get("chain_id") or ""), body.get("text"), body.get("source") or "我的记忆 · 用户更正", now)
                    elif op == "forget":
                        out = ms.forget(subj, str(body.get("chain_id") or ""), now)
                    elif op == "verify":
                        out = ms.verify_deleted(ms._subject(subj), str(body.get("chain_id") or ""))
                    else:
                        return self._json(400, {"error": "OP_UNKNOWN"})
                    app.log("starling_memory", inst.ctx.instance_id, op)
                    return self._json(200, dict(ms.list(subj), result=out))
                except starling_memory.MemoryError_ as exc:
                    return self._json(400, {"error": exc.code, "detail": exc.detail})
                except H1Error as exc:
                    return self._json(400, {"error": exc.code})
                except ValueError:
                    return self._json(400, {"error": "BODY_INVALID"})
            if url.path == "/api/notes":  # 界面批注：不碰任何实例数据
                import ui_notes
                body = input_guard.json_object(raw)
                try:
                    if body.get("op") == "delete":
                        ui_notes.delete(app.root, body.get("id"))
                    elif body.get("op") == "clear":
                        ui_notes.clear(app.root)
                    else:
                        return self._json(200, {"note": ui_notes.add(app.root, body)})
                    return self._json(200, {"ok": True})
                except ValueError as exc:
                    return self._json(400, {"error": str(exc)})
            if url.path == "/api/starling/ask":  # 问星灵（右下角浮窗）：拼记录事实时占锁一下，问本机千问时不占锁；一次只答一个
                body = input_guard.json_object(raw)
                try:
                    page = body.get("page") or {}
                    question = str(body.get("question") or "")[:300]
                    if starling_ask.route(question, {})["kind"] == "history":
                        with app.lock:
                            inst = app.inst(body.get("key"))
                            labels = {c: getattr(r, "label_zh", "") for c, r in app.registry.current.codes.items()}
                            res = starling_ask.ask(None, question, labels, {"instance": {"tz": inst.ctx.tz}},
                                lambda _: ([], set()), "", now=inst.now(),
                                history_query=lambda start, end: starling_history.read(inst, start, end, labels))
                        res["id"] = starling_ask.log(inst.ctx.root, inst.now(), page, res)
                        app.log("starling_ask", inst.ctx.instance_id, res["state"], "saved_records", res["query_status"])
                        res["nav"] = {g: starling_ask.NAV[g] for g in res["go"]}
                        return self._json(200, res)
                    with app.lock:
                        inst = app.inst(body.get("key"))
                        snap = inst.snapshot()
                        facts = ask_facts(app, inst, snap, page)
                    labels = {c: getattr(r, "label_zh", "") for c, r in (inst.app.registry.current.codes or {}).items()}  # 没有记录的指标也认得，好照实说“没有记录”
                    labels.update({o["code"]: o.get("label_zh") or o["code"] for o in snap.get("timeline") or []})
                    sign = starling_page.sign(app.llm) if app.llm else "星灵"
                    ms = None if inst.spec.get("replay") else mem_store(app, inst)
                    memory = ms.recall(body.get("subject") or "default", str(body.get("question") or "")) if ms else None
                    res = starling_ask.ask(app.llm, str(body.get("question") or ""), labels, snap, facts, sign, memory)
                    if memory:
                        res["memory_method"] = memory.get("method")
                    res["id"] = starling_ask.log(inst.ctx.root, inst.now(), page, res)
                    app.log("starling_ask", inst.ctx.instance_id, res["state"], res.get("area") or "-")
                    res["nav"] = {g: starling_ask.NAV[g] for g in res["go"]}
                    return self._json(200, res)
                except H1Error as exc:
                    return self._json(400, {"error": exc.code, "detail": exc.detail})
            if url.path == "/api/evidence/pack":  # 证据包：先跑测试（不占全局锁），再占锁读计数、出包
                body = input_guard.json_object(raw)
                if not app.pack_lock.acquire(blocking=False):
                    return self._json(409, {"error": "PACK_BUSY", "detail": "上一个证据包还在生成"})
                try:
                    tests = evidence_pack.run_tests() if body.get("tests", True) else None
                    with app.lock:
                        res = evidence_pack.build(app, tests=tests, now=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
                                                  hooks=evidence_hooks())
                    app.log("evidence_pack", res.get("name") or "-", "ok" if res["ok"] else res.get("error"),
                            "tests:" + ("-" if tests is None else f"{tests.get('passed')}/{tests.get('total')}"))
                    return self._json(200 if res["ok"] else 500, res)
                except Exception as exc:  # noqa: BLE001
                    app.log("evidence_pack_failed", type(exc).__name__)
                    traceback.print_exc()
                    return self._json(500, {"ok": False, "error": type(exc).__name__, "detail": str(exc)[:300]})
                finally:
                    app.pack_lock.release()
            if url.path == "/api/torch/recognize":  # 识别不写库，不占全局锁
                try:
                    return self._json(200, app.recognize(q["key"], q.get("name", "化验单"), raw))
                except Exception as exc:  # noqa: BLE001
                    code = exc.code if isinstance(exc, H1Error) else (str(exc) if str(exc).isupper() else type(exc).__name__)
                    app.log("recognize_failed", code)
                    return self._json(400, {"error": code, "detail": str(exc)[:200]})
            try:
                if url.path in ("/api/oura/sync", "/api/oura/disconnect", "/api/graph/reveal"):
                    body = input_guard.json_object(raw)
                    with app.lock:
                        inst = app.inst(body.get("key") or q.get("key"))
                        local = phone_tail.local_control_allowed(self) if url.path.endswith("/reveal") else False
                    result = (oura_pull(inst, lock=app.lock) if url.path.endswith("/sync") else
                              oura_disconnect(app, inst, oura_client, Sources) if url.path.endswith("/disconnect") else
                              evidence_navigation.reveal(inst, body.get("doc", ""), local_allowed=local))
                    return self._json(200, result)
                with app.lock:
                    if url.path == "/api/torch/table":
                        return compute_http.table(self, app, q, raw)
                    body = input_guard.json_object(raw)
                    inst = app.inst(body.get("key") or q.get("key"))
                    if url.path in ("/api/torch/save", "/api/torch/correct", "/api/torch/retract"):
                        return compute_http.write(self, inst, url.path, body)
                    if url.path == "/api/sources/tail":  # 设备小尾巴显示哪四项（产品负责人 2026-10-14）：只存选择，不动数据
                        dev, codes = str(body.get("device") or ""), body.get("codes")
                        if dev not in TAIL_CODES or not isinstance(codes, list) or len(codes) != 4 or len(set(codes)) != 4 \
                                or not all(isinstance(c, str) and c in TAIL_CODES[dev] for c in codes):
                            return self._json(400, {"error": "TAIL_CODES", "detail": "要选 4 项不同的动态读数"})
                        return self._json(200, {"tail": Sources(inst).update(dev, tail=codes)["tail"]})
                    if url.path == "/api/track/vitals-card":
                        input_guard.require_writable(inst)
                        track = open_startrack(inst.ctx)
                        try:
                            result = vitals_cards.save(track, body, inst.refresh_snapshot(), at=inst.now())
                        except vitals_cards.VitalsCardError as exc:
                            return self._json(exc.status, {"error": exc.code, "detail": exc.detail})
                        finally:
                            track.close()
                        return self._json(200, dict(result, snapshot=inst.refresh_snapshot()))
                    if url.path == "/api/track/card":  # 状态工程"创建"：卡、绑定的数据、配通知写回本机（N15）
                        if body.get("card") != "VITALS":
                            return self._json(400, {"error": "TEMPLATE_NOT_READY"})
                        st = inst.setup().create_card("VITALS", body.get("sources") or {}, body.get("notify") or {},
                                                      inst.now())
                        app.log("card_created", inst.ctx.instance_id, "VITALS",
                                ",".join(k for k, v in (st["vitals_sources"] or {}).items() if v))
                        inst.watch_devices()
                        return self._json(200, {"setup": st, "snapshot": inst.snapshot()})
                    if url.path == "/api/track/thresholds":
                        if inst.spec.get("replay"):
                            return self._json(400, {"error": "REPLAY_INSTANCE"})
                        track = open_startrack(inst.ctx)
                        try:
                            definition = card_thresholds.save(track, inst.ctx, app.registry, body, inst.now())
                        except ValueError as exc:
                            return self._json(400, {"error": "THRESHOLD_INVALID", "detail": str(exc)})
                        finally:
                            track.close()
                        return self._json(200, {"definition": definition, "snapshot": inst.snapshot()})
                    if url.path == "/api/track/custom":  # 自定义状态卡：新建 / 改规则（新定义，旧结果保留）/ 停用
                        if inst.spec.get("replay"):
                            return self._json(400, {"error": "REPLAY_INSTANCE"})
                        track = open_startrack(inst.ctx)
                        try:
                            if body.get("action") == "stop":
                                custom_cards.stop(track, str(body.get("card_id")), at=inst.now())
                                app.log("custom_card_stopped", inst.ctx.instance_id, body.get("card_id"))
                                return self._json(200, {"card_id": body.get("card_id"), "snapshot": inst.snapshot()})
                            edit = bool(body.get("card_id"))
                            card = custom_cards.save(track, app.registry, inst.ctx, body, at=inst.now())
                            res = custom_cards.sync_all(track, inst.ctx, now=inst.now(), notifiers=app.notifiers,
                                                        only=card["card_id"], trigger="RECOMPUTE" if edit else "SYNC")
                            deliver_pending(track, app.notifiers, inst.now())
                        except custom_cards.CustomError as exc:
                            return self._json(400, {"error": exc.code, "detail": exc.detail})
                        finally:
                            track.close()
                        app.log("custom_card_saved", inst.ctx.instance_id, card["card_id"], card["card_def_id"][:12])
                        return self._json(200, {"card_id": card["card_id"], "result": res, "snapshot": inst.snapshot()})
                    if url.path == "/api/track/engines":  # 状态工程：引擎模板 创建 / 停用 / 看过（只追加）
                        if inst.spec.get("replay"):
                            return self._json(400, {"error": "REPLAY_INSTANCE"})
                        track = open_startrack(inst.ctx)
                        tpl, act = str(body.get("tpl") or ""), body.get("action") or "create"
                        try:
                            if tpl not in engines.TEMPLATES:
                                return self._json(404, {"error": "NOT_FOUND"})
                            if act == "seen":
                                engines.mark_seen(track, tpl, at=inst.now())
                                return self._json(200, {"ok": True})
                            if act == "stop":
                                engines.stop(track, tpl, at=inst.now())
                            else:
                                if engines.TEMPLATES.get(tpl, {}).get("notify") == "required" and not body.get("notify_self"):
                                    return self._json(400, {"error": "NOTIFY_REQUIRED", "detail": "预警引擎必须配置通知"})
                                conf = engines.create(track, tpl, body, at=inst.now(), sjia=False)
                                app.log("engine_created", inst.ctx.instance_id, tpl, ",".join(conf["refs"]))
                        except engines.EngineError as exc:
                            return self._json(400, {"error": exc.code, "detail": exc.detail})
                        finally:
                            track.close()
                        res = inst.sync_track("ENGINE")
                        return self._json(200, {"tpl": tpl, "sync": res.get("engines"), "snapshot": inst.snapshot()})
                    if url.path == "/api/track/bind":  # 星炬里绑定 / 解绑一个来源（N3）
                        try:
                            st = inst.setup().bind(str(body.get("source")), bool(body.get("bound")), inst.now())
                        except ValueError as exc:
                            return self._json(400, {"error": str(exc)})
                        app.log("source_bound" if body.get("bound") else "source_unbound", inst.ctx.instance_id,
                                body.get("source"))
                        inst.watch_devices()
                        return self._json(200, {"setup": st, "snapshot": inst.snapshot()})
                    if url.path == "/api/cluster/create":
                        if body["form"].get("card") == phone_tail.auth.RESOURCE or body["form"].get("object") == "phone_browser":
                            if not phone_tail.local_control_allowed(self):
                                return self._json(403, {"error": "LOCAL_ONLY"})
                            try:
                                grant = app.phone_tail.create_grant(body["key"], body["form"])
                            except phone_tail.ViewerError as exc:
                                return self._json(400, {"error": "PHONE_VIEW_UNAVAILABLE", "detail": str(exc)})
                        else:
                            grant = inst.cluster.create(body["form"], inst.now())
                        app.log("cluster_create", inst.ctx.instance_id, grant["id"], grant["status"])
                        return self._json(200, grant)
                    if url.path == "/api/cluster/revoke":
                        grant = phone_lifecycle.revoke(app, inst, body["key"], body["id"], inst.now())
                        if grant["card"] == report_phone.RESOURCE:
                            app.report_phone.revoked(body["key"], grant["id"])
                        app.log("cluster_revoke", inst.ctx.instance_id, grant["id"])
                        return self._json(200, grant)
                    if url.path == "/api/cluster/read":  # 本机 MCP 与界面"让智能体读取"共用；拒绝也是 200 + 留痕
                        res = inst.cluster.read(body["grant_id"], inst.snapshot(), inst.now(), via="LOCAL_API",
                                                rsids=body.get("rsids"), gene_path=GeneStore(inst).db_path)
                        app.log("cluster_read", inst.ctx.instance_id, body["grant_id"], res["outcome"])
                        return self._json(200, res)
                    if url.path == "/api/bridge/enable":
                        return self._json(200, app.bridge(inst).enable())
                    if url.path == "/api/bridge/code":  # 显示配对码 = 打开接收
                        bridge = app.bridge(inst)
                        bridge.enable()
                        return self._json(200, dict(bridge.code(), state=bridge.state()))
                    if url.path == "/api/bridge/disable":
                        return self._json(200, app.bridge(inst).disable())
                    if url.path == "/api/bridge/unpair":
                        bridge = app.bridge(inst)
                        return self._json(200, dict(bridge.unpair(body["phone_id"]), state=bridge.state()))
                    if url.path == "/api/track/retro":  # 回溯式重计算：按现在的方法重算全部过去时点，或换灵敏度后重算
                        if not inst.sjia:
                            return self._json(400, {"error": "NO_SJIA_CARD"})
                        want = body.get("sensitivity")
                        cur = retro.history(inst)["sensitivity"]
                        if want and want != cur:
                            if want not in [x["id"] for x in retro.history(inst)["sensitivities"]]:
                                return self._json(400, {"error": "SENSITIVITY_UNKNOWN"})
                            track = open_startrack(inst.ctx)
                            try:
                                set_sensitivity(track, "sjia-mas", want, set_at=inst.now())
                            finally:
                                track.close()
                            result = retro.rerun(inst)  # 换回以前用过的灵敏度也要重算（旧定义的结果虽在，但不是最新一次）
                        else:
                            result = retro.rerun(inst)
                        app.log("retro", inst.ctx.instance_id, want or cur, result.get("run_id"))
                        return self._json(200, {"result": result, "history": retro.history(inst), "snapshot": inst.snapshot()})
                    if url.path == "/api/track/wall":  # 我的状态墙：钉 / 取消钉、隐藏 / 恢复（只追加，不动卡片本身）
                        card = str(body.get("card") or "")[:80]
                        if not card or sum(k in body for k in ("pin", "hide", "display")) != 1:
                            return self._json(400, {"error": "BAD_REQUEST"})
                        if "display" in body:
                            if inst.spec.get("replay"):
                                return self._json(400, {"error": "REPLAY_INSTANCE"})
                            try:
                                value = wall_display.validate(card, body["display"], inst.refresh_snapshot())
                            except ValueError as exc:
                                return self._json(400, {"error": "CARD_DISPLAY_INVALID", "detail": str(exc)})
                            key = "wall_display"
                        else:
                            key, on = ("wall_pin", bool(body["pin"])) if "pin" in body else ("wall_hide", bool(body["hide"]))
                            value = {"on": on, "name": str(body.get("name") or "")[:40]}
                        track = open_startrack(inst.ctx)
                        try:
                            with transaction(track):
                                track.execute("INSERT INTO card_setting (card_id, key, value, set_at) VALUES (?, ?, ?, ?)",
                                              (card, key, json.dumps(value, ensure_ascii=False), inst.now()))
                        finally:
                            track.close()
                        return self._json(200, {"snapshot": inst.refresh_snapshot()})
                    if url.path == "/api/track/alert_hide":  # 从提醒历史列表隐藏一条（只追加隐藏记录，提醒原记录、送达记录都不动）
                        dk = str(body.get("dedupe_key") or "")
                        track = open_startrack(inst.ctx)
                        try:
                            row = track.execute("SELECT card_id FROM alert_log WHERE dedupe_key = ?", (dk,)).fetchone()
                            if row is None:
                                return self._json(400, {"error": "ALERT_UNKNOWN"})
                            with transaction(track):
                                track.execute("INSERT INTO card_setting (card_id, key, value, set_at) VALUES (?, 'alert_hidden', ?, ?)",
                                              (row[0], dk, inst.now()))
                        finally:
                            track.close()
                        app.log("alert_hidden", inst.ctx.instance_id, dk)
                        return self._json(200, {"hidden": dk, "snapshot": inst.snapshot()})
                    if url.path == "/api/track/baseline/rule":  # 整体基线洞察：本人自定“偏离大”（只在这一页，只追加，不动发布规则）
                        if inst.spec.get("kind") != "DEMO" or not inst.sjia:
                            return self._json(400, {"error": "DEMO_ONLY"})
                        try:
                            out = baseline_view.save_rule(inst, str(body.get("clue") or ""), body.get("thresholds") or {}, reset=bool(body.get("reset")))
                        except (ValueError, TypeError) as exc:
                            return self._json(400, {"error": "BAD_REQUEST", "detail": str(exc)[:80]})
                        app.log("patient_rule", inst.ctx.instance_id, body.get("clue"), out["saved"])
                        return self._json(200, dict(out, view=baseline_view.view(inst, lambda day: meds.on_day(inst.ctx.root, day))))
                    if url.path == "/api/track/sync":
                        inst.export()
                        return self._json(200, inst.sync_track("MANUAL"))
                    if url.path in ("/api/track/recompute", "/api/track/sensitivity", "/api/track/ack"):
                        return self._json(200, inst.track_action(url.path.rsplit("/", 1)[1], body))
            except H1Error as exc:
                app.log("rejected", url.path, exc.code)
                return self._json(400, {"error": exc.code, "detail": exc.detail})
            except input_guard.RequestError:
                raise
            except Exception as exc:  # noqa: BLE001
                app.log("error", url.path, type(exc).__name__)
                traceback.print_exc()
                return self._json(500, {"error": type(exc).__name__, "detail": str(exc)[:300]})
            return self._json(404, {"error": "NOT_FOUND"})

    return trial_target.install(Handler, app)


def poll_devices(app: App) -> None:
    """持续保存（DC-16）：已接入的 Oura 按间隔拉取；断开的不碰。失败记在来源状态里，界面可见。"""
    interval = int(app.config.get("oura", {}).get("poll_seconds", 300))
    while True:
        time.sleep(interval)
        for inst in app.instances.values():
            if not app.trial.may_poll(inst) or Sources(inst).read().get("oura", {}).get("status") != "CONNECTED":
                continue
            try:
                oura_pull(inst, lock=app.lock)  # 联网时不占全局锁，保存时才占
            except Exception:  # noqa: BLE001  — recorded by oura_pull / log
                pass


def close_device_days(app: App) -> None:
    while True:
        try:
            app.close_daily_days()
        except Exception as exc:
            app.log("daily_save_pending", type(exc).__name__)
        time.sleep(60)


def watch_devices(app: App) -> None:
    interval = int(app.config.get("device_watch_seconds", 60))
    while True:
        time.sleep(interval)
        for inst in list(app.instances.values()):
            try:
                inst.watch_devices(periodic=True)
            except Exception as exc:  # noqa: BLE001
                app.log("device_watch_failed", inst.ctx.instance_id, type(exc).__name__)


STARLING_OFF = "本机未启用星灵（这个版本没有装千问）"
STARLING_PATHS = {"/api/starling/weekly-focus", "/api/starling/baseline", "/api/starling/page", "/api/starling/ask", "/api/starling/memory", "/api/track/compete_ai", "/api/track/retro_ai"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(os.environ.get("PTDS_INSTANCES", "~/PTDS-instances")))
    parser.add_argument("--port", type=int, default=8780)
    parser.add_argument("--config", type=Path, default=Path(os.environ.get("PTDS_CONFIG") or APP / "config.json"))
    args = parser.parse_args()
    config = json.loads(args.config.read_text("utf-8")) if args.config.exists() else {}
    config["port"] = args.port
    preview_session.clean_preview_on_startup()
    app = App(args.root.expanduser(), config)
    threading.Thread(target=poll_devices, args=(app,), daemon=True).start()
    threading.Thread(target=gene_catch_up, args=(app,), daemon=True).start()
    threading.Thread(target=watch_devices, args=(app,), daemon=True).start()
    threading.Thread(target=close_device_days, args=(app,), daemon=True, name="PTDS-daily-close").start()
    app.main_stores.start()
    app.compute_jobs.start()
    app.batch_worker.start()
    app.state_reports.start()
    # Report gateway stays closed unless explicitly configured; product survives setup errors.
    if (config.get("state_report_phone") or {}).get("enabled"):
        try:
            app.report_phone.start_gateway()
        except (report_phone.ReportPhoneError, phone_tail.ViewerError, OSError):
            app.log("report_phone_setup_required")
    app.log("started", os.getpid())
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(app))
    # Oura 回调地址登记在别的本机端口（例如 localhost:8773）时，在那个端口另开监听接住回调（只听本机）
    cb = urlparse(config.get("oura", {}).get("redirect_uri") or "")
    if cb.hostname in ("localhost", "127.0.0.1", "::1") and cb.port and cb.port != args.port:
        for host, family in (("127.0.0.1", socket.AF_INET), ("::1", socket.AF_INET6)):
            try:
                extra = type("S", (ThreadingHTTPServer,), {"address_family": family})((host, cb.port), make_handler(app))
            except OSError as exc:
                print(f"Oura 回调端口 {host}:{cb.port} 没能打开：{exc}", flush=True)
                continue
            threading.Thread(target=extra.serve_forever, daemon=True).start()
    print(f"PTDS 本机进程 pid={os.getpid()} http://127.0.0.1:{args.port}/  实例目录 {app.root}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # 终端里按 Ctrl+C：正常停止
        app.log("stopped", os.getpid())
    finally:
        app.compute_jobs.stop()
        app.state_reports.stop()
        app.report_phone.stop()
        app.phone_tail.stop()
        app.pillbox.close()
        server.server_close()
        app.main_stores.close()


if __name__ == "__main__":
    main()
