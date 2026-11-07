"""验收证据包（FR-X-006）：一键生成，交给评审、自己留底。

- 只放计数、代码、指纹和日期，不放任何健康数值、令牌、密钥、原始文件名（NFR-02 / HR-31）；
- 每项能力按准则 §6 给证据等级：M1 源码在（位置 + 指纹）；M3 这次跑的自动测试通过（真实进程、合成数据、重启读回）；
  M4 "我的真实数据"里有这项能力经产品入口留下的真实记录；M5 只能本人签字，包里留签字栏；
- 标签核对（HR-54）：产品配置里的成熟度标签不得高于证据（可用 ≥ M4，只用合成数据的入口 ≥ M3；已适配 ≥ M3；早期测试 ≥ M2）；
- 可复现核对：每张卡"输入没变"的时点，在内存里按同一定义重算，结果指纹应与星轨记录逐字一致。不写任何库；
- 追溯核对：每个时点最新一次计算用到的每条数据，在星轨收件箱、星炬交接记录、星炬正式库里都找得到同一版本，指纹一致；
- 出包前自检：包里不得出现令牌、密钥、原始文件名，也不得出现数值类字段；自检不过就不出包。
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from contextlib import closing
from datetime import datetime
from pathlib import Path

from cards import classify, evaluate_tp, latest_results, open_startrack, take_snapshot, values_at
from h1_common import canonical_bytes, canonical_json, sha256_hex
from startorch_outbox import open_startorch
import custom_cards
import device_watch
import gene_db
import sleep_card
import oura_raw
import erasure_service
import phone_lifecycle

APP = Path(__file__).resolve().parent
LEVELS = ["M0", "M1", "M2", "M3", "M4", "M5"]
FLOOR = {"ready": "M4", "adapted": "M3", "beta": "M2"}
LABEL_ZH = {"ready": "可用", "adapted": "已适配", "beta": "早期测试", "dev": "开发中", "plan": "规划中", "view": "查看"}
NAME_RE = re.compile(r"PTDS-evidence-\d{8}-\d{6}(-\d{1,3})?\.zip")
# 包里不许出现这些字段名：出现就说明有数值或原文混进来了
FORBIDDEN_KEYS = {"value", "value_raw", "value_canonical", "values", "answer", "question", "sent", "rsids", "genotype",
                  "file_name", "stored_as", "name", "source_lines", "token", "access_token", "refresh_token"}

# 能力清单：标签 = 产品配置里的入口 id（或位置）；测试 = 证明它的测试文件；m4 = 在"我的真实数据"里找什么记录
CAPABILITIES = [
    {"id": "manual", "zh": "手工录入 → 星炬正式保存", "labels": ["manual"], "files": ["server.py", "core/startorch_outbox.py"],
     "tests": ["test_stage_paths"], "m4": lambda f: _n(f, "torch", "by_source", "MANUAL"), "m4_zh": "手工录入保存的真实记录"},
    {"id": "table", "zh": "表格导入", "labels": ["csv"], "files": ["core/startorch_table.py"],
     "tests": ["test_stage_paths"], "m4": lambda f: _n(f, "torch", "by_source", "TABLE"), "m4_zh": "表格导入的真实记录"},
    {"id": "ocr", "zh": "化验单识别（本机识别 + 本人逐项确认）", "labels": ["ocr"], "files": ["recognize.py", "tools/ocr_vision.swift"],
     "tests": ["test_recognize"], "m4": lambda f: _n(f, "torch", "by_source", "OCR_LLM"), "m4_zh": "识别后确认保存的真实记录"},
    {"id": "oura", "zh": "Oura 接入与自动拉取", "labels": ["oura"], "files": ["oura.py"],
     "tests": ["test_oura"], "m4": lambda f: _n(f, "torch", "by_source", "DEVICE_OURA"), "m4_zh": "Oura 拉取保存的真实记录"},
    {"id": "apple", "zh": "苹果健康（局域网接收）", "labels": ["apple"], "files": ["bridge.py"],
     "tests": ["test_bridge"], "m4": lambda f: _n(f, "torch", "by_source", "APPLE_HEALTH"), "m4_zh": "苹果健康上传保存的真实记录"},
    {"id": "gene", "zh": "基因原始数据纳管与位点库", "labels": ["gene"], "files": ["gene_db.py", "gene_profile.py"],
     "tests": ["test_gene"], "m4": lambda f: min(_n(f, "gene", "receipts"), _n(f, "gene", "db_rows")), "m4_zh": "纳管回执且位点库有行"},
    {"id": "data", "zh": "我的数据 / 数据导航（正式库、版本、交接）", "labels": ["data", "guard"], "files": ["server.py", "core/startorch_outbox.py"],
     "tests": ["test_stage_paths"], "m4": lambda f: _n(f, "torch", "by_nature", "REAL"), "m4_zh": "正式库里的真实记录"},
    {"id": "vitals", "zh": "我的体征（星轨读模型）", "labels": ["VITALS", "wall"], "files": ["core/vitals.py"],
     "tests": ["test_oura", "test_device_watch"], "m4": lambda f: _n(f, "track", "inbox_real_device"), "m4_zh": "星轨收到的真实设备读数"},
    {"id": "sjia", "zh": "sJIA 关注卡（演示规则，未经临床验证）", "labels": ["SJIA_FOCUS"], "synthetic_only": True,
     "files": ["core/cards.py", "core/rules.py", "core/dynamic.py"], "tests": ["test_stage_paths", "test_reference"],
     "m4": lambda f: _n(f, "track", "cards", "sjia-mas", "tps"), "m4_zh": "关注卡在真实数据上算过的时点"},
    {"id": "alerts", "zh": "状态通知（只发一次、投递留痕、确认）", "labels": ["alerts"], "files": ["core/cards.py"],
     "tests": ["test_stage_paths", "test_custom_cards"], "m4": lambda f: _n(f, "track", "alerts_sent_real"), "m4_zh": "真实数据触发并送达的提醒"},
    {"id": "custom", "zh": "自定义状态卡", "labels": ["CUSTOM"], "files": ["custom_cards.py"],
     "tests": ["test_custom_cards"], "m4": lambda f: _n(f, "track", "custom_tps"), "m4_zh": "自定义卡在真实数据上算过的时点"},
    {"id": "sleep", "zh": "睡眠卡（只读，不打分）", "labels": ["SLEEP"], "files": ["sleep_card.py"],
     "tests": ["test_oura"], "m4": lambda f: _n(f, "sleep", "nights"), "m4_zh": "睡眠卡能显示的真实夜数"},
    {"id": "graph", "zh": "证据图谱（只读追溯）", "labels": ["graph"], "files": ["evidence_graph.py"],
     "tests": ["test_custom_cards", "test_stage_paths"], "m4": lambda f: _n(f, "trace", "real_tps_traced"), "m4_zh": "能完整追到星炬正式记录的真实时点"},
    {"id": "retro", "zh": "回溯式重计算", "labels": ["retro"], "files": ["retro.py"],
     "tests": ["test_stage_paths", "test_custom_cards"], "m4": lambda f: _n(f, "track", "cards", "sjia-mas", "runs", "RECOMPUTE"),
     "m4_zh": "在真实数据上做过的重新计算"},
    {"id": "compete", "zh": "竞争性解释（内存里算，不写库）", "labels": ["compete"], "files": ["compete.py"],
     "tests": ["test_stage_paths", "test_starling"], "m4": None, "m4_zh": "不留记录，包里证明不了真实数据跑过，需本人看过签字"},
    {"id": "cluster", "zh": "星簇授权（建、撤、读、拒绝都留痕）", "labels": ["overview", "objects", "records", "self", "other", "agent"],
     "files": ["cluster.py"], "tests": ["test_cluster"], "m4": lambda f: _n(f, "cluster", "user_grants"), "m4_zh": "本人建的授权"},
    {"id": "mcp", "zh": "本机 MCP 只读供给", "labels": ["mcp"], "files": ["mcp_cluster.py"],
     "tests": ["test_cluster"], "m4": lambda f: _n(f, "cluster", "mcp_reads"), "m4_zh": "经本机 MCP 的读取记录"},
    {"id": "gene_supply", "zh": "基因位点经星簇供给（不解读）", "labels": [], "files": ["cluster.py", "mcp_cluster.py"],
     "tests": ["test_cluster", "test_gene"], "m4": lambda f: _n(f, "cluster", "gene_reads", "READ"), "m4_zh": "按授权读到位点的记录"},
    {"id": "starling", "zh": "星灵（本机千问，只看标签不看数值）", "labels": ["spirit"], "files": ["starling.py"],
     "tests": ["test_starling"], "m4": lambda f: _n(f, "starling", "by_model"), "m4_zh": "本机千问回答过的问答"},
    {"id": "device_watch", "zh": "设备断开 / 恢复提醒", "labels": [], "files": ["device_watch.py"],
     "tests": ["test_device_watch"], "m4": lambda f: sum((f.get("device_events") or {}).values()), "m4_zh": "真实设备的断开 / 恢复事件"},
    {"id": "evidence_pack", "zh": "验收证据包（本包）", "labels": [], "files": ["evidence_pack.py", "tools/run_tests.py"],
     "tests": ["test_evidence_pack"], "m4": None, "m4_zh": "本包就是它在真实数据上的产物"},
]


def _n(f: dict, *path) -> int:
    for k in path:
        f = (f or {}).get(k) if isinstance(f, dict) else None
    return int(f or 0)


def _sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def code_hashes() -> dict:
    files = sorted(list(APP.glob("*.py")) + list((APP / "core").glob("*.py")) + list((APP / "core").glob("*.json"))
                   + list((APP / "tools").glob("*.py")) + list((APP / "tools").glob("*.swift")) + list((APP / "tests").glob("*.py"))
                   + [p for p in (APP / "web").glob("*") if p.is_file()])
    return {str(p.relative_to(APP)): _sha_file(p) for p in files}


# ----------------------------------------------------------------------------- tests

def run_tests(timeout: int = 900) -> dict:
    """在单独的进程里跑全部测试；用空配置、临时密钥目录，不碰钥匙串、不发真通知、不碰本机实例目录。"""
    with tempfile.TemporaryDirectory() as tmp:
        cfg, out = Path(tmp) / "config.json", Path(tmp) / "tests.json"
        cfg.write_text("{}", "utf-8")
        env = dict(os.environ, PTDS_CONFIG=str(cfg), PTDS_SECRETS=str(Path(tmp) / "secrets"), TMPDIR=tmp,
                   PTDS_OURA_CLIENT_SECRET="", PYTHONDONTWRITEBYTECODE="1")
        try:
            p = subprocess.run([sys.executable, "-B", str(APP / "tools" / "run_tests.py"), str(out)], cwd=str(APP.parent),
                               env=env, capture_output=True, text=True, timeout=timeout)
            text = p.stdout + p.stderr
        except subprocess.TimeoutExpired:
            return {"ok": False, "total": 0, "passed": 0, "modules": {}, "error": "TIMEOUT", "text": ""}
        res = json.loads(out.read_text("utf-8")) if out.exists() else {"ok": False, "total": 0, "passed": 0, "modules": {},
                                                                       "error": "NO_RESULT"}
        res["text"] = text
        return res


# ----------------------------------------------------------------------------- facts (counts only)

def _torch_facts(inst, registry) -> tuple:
    torch = open_startorch(inst.ctx)
    try:
        rows = torch.execute("SELECT observation_id, revision, payload FROM formal_observation").fetchall()
        outbox = {(o, r): s for o, r, s in torch.execute("SELECT observation_id, revision, payload_sha256 FROM h1_outbox")}
        commits = torch.execute("SELECT count(*) FROM h1_commit").fetchone()[0]
        exports = torch.execute("SELECT count(DISTINCT commit_id), count(*) FROM h1_export_log").fetchone()
        last = torch.execute("SELECT file_sha256 FROM h1_export_log ORDER BY id DESC LIMIT 1").fetchone()
    finally:
        torch.close()
    newest, by_source, by_family, by_nature = {}, Counter(), Counter(), Counter()
    nature = {}
    for oid, rev, payload in rows:
        if oid not in newest or rev > newest[oid][0]:
            newest[oid] = (rev, payload)
    formal = {(oid, rev) for oid, rev, _ in rows}
    retracted = 0
    for oid, (rev, payload) in newest.items():
        p = json.loads(payload)
        if p.get("status") != "ACTIVE":
            retracted += 1
            continue
        real = p.get("source_kind") != "SYNTHETIC"
        nature[oid] = real
        by_source[p.get("source_kind")] += 1
        cdef = registry.current.codes.get(p.get("code"))
        by_family[cdef.family if cdef else "UNKNOWN"] += 1
        by_nature["REAL" if real else "SYNTHETIC"] += 1
    facts = {"formal_rows": len(rows), "observations": len(newest), "active": sum(by_nature.values()), "retracted": retracted,
             "revised": sum(1 for rev, _ in newest.values() if rev > 1), "by_source": dict(by_source),
             "by_family": dict(by_family), "by_nature": dict(by_nature), "h1_commits": commits, "h1_exported_commits": exports[0], "h1_export_checks": exports[1],
             "last_export_sha256": last[0] if last else None}
    return facts, formal, outbox, nature


def _track_facts(inst, formal: set, outbox: dict, nature: dict) -> tuple:
    track = open_startrack(inst.ctx)
    try:
        inbox = {(o, r): (s, c) for o, r, s, c in track.execute("SELECT observation_id, revision, payload_sha256, code FROM h1_inbox")}
        def_card = dict(track.execute("SELECT card_def_id, card_id FROM card_def"))
        cards, custom_tps = {}, 0
        for cdid, trig, n in track.execute("SELECT card_def_id, trigger, count(*) FROM run GROUP BY card_def_id, trigger"):
            c = cards.setdefault(def_card[cdid], {"runs": Counter(), "tps": 0, "levels": Counter()})
            c["runs"][trig] += n
        latest = {}
        for rid, tp, status, level, cdid in track.execute(
                "SELECT rt.run_id, rt.tp_date, rt.status, rt.level, r.card_def_id FROM run_tp rt JOIN run r USING (run_id) ORDER BY rt.run_id"):
            latest[(def_card[cdid], tp)] = (rid, status, level)
        integrity_bad = sum(1 for text, sha in track.execute("SELECT result, result_sha256 FROM run_tp")
                            if sha256_hex(text.encode()) != sha)
        trace = {"tps": 0, "tps_traced": 0, "real_tps": 0, "real_tps_traced": 0, "inputs": 0, "in_inbox": 0,
                 "same_in_handover": 0, "in_formal": 0, "untraced": []}
        for (card_id, tp), (rid, status, level) in sorted(latest.items()):
            if status != "EVALUATED":
                continue
            c = cards.setdefault(card_id, {"runs": Counter(), "tps": 0, "levels": Counter()})
            ins = track.execute("SELECT observation_id, revision FROM run_input WHERE run_id = ? AND tp_date = ?", (rid, tp)).fetchall()
            real = any(nature.get(o) for o, _ in ins)
            if real:
                c["tps"] += 1
                c["levels"][level] += 1
                if card_id.startswith(custom_cards.PREFIX):
                    custom_tps += 1
            ok = bool(ins)
            for o, r in ins:
                trace["inputs"] += 1
                got = inbox.get((o, r))
                trace["in_inbox"] += got is not None
                same = got is not None and outbox.get((o, r)) == got[0]
                trace["same_in_handover"] += same
                trace["in_formal"] += (o, r) in formal
                ok = ok and same and (o, r) in formal
            trace["tps"] += 1
            trace["tps_traced"] += ok
            trace["real_tps"] += real
            trace["real_tps_traced"] += real and ok
            if not ok and len(trace["untraced"]) < 20:
                trace["untraced"].append({"card": card_id, "tp": tp})
        alerts = track.execute("SELECT count(*) FROM alert_log").fetchone()[0]
        deliveries = Counter()
        for outcome, n in track.execute("SELECT outcome, count(*) FROM alert_delivery GROUP BY outcome"):
            deliveries[outcome] += n
        by_channel = {f"{ch}:{oc}": n for ch, oc, n in track.execute(
            "SELECT channel, outcome, count(*) FROM alert_delivery GROUP BY channel, outcome")}
        acks = track.execute("SELECT count(*) FROM alert_ack").fetchone()[0]
        real_sent = 0  # 送达的提醒里，那个时点的计算用到了真实数据的
        for rid, tp in track.execute("SELECT DISTINCT l.run_id, l.tp_date FROM alert_log l JOIN alert_delivery d USING (dedupe_key) "
                                     "WHERE d.outcome = 'SENT'").fetchall():
            ins = track.execute("SELECT observation_id FROM run_input WHERE run_id = ? AND tp_date = ?", (rid, tp)).fetchall()
            real_sent += any(nature.get(o) for (o,) in ins)
        repro = reproduce(inst, track)
        groups = custom_cards.by_code(track, inst.ctx)
        sleep = sleep_card.state(groups, inst.app.registry, inst.setup().state()["vitals_sources"])
        custom = custom_cards.cards(track, include_off=True)
    finally:
        track.close()
    inbox_real = sum(1 for (o, _r) in inbox if nature.get(o))
    fam = {code: c.family for code, c in inst.app.registry.current.codes.items()}
    device_real = sum(1 for (o, _r), (_s, code) in inbox.items() if nature.get(o) and fam.get(code) in device_watch.SOURCES)
    facts = {"inbox": len(inbox), "inbox_real": inbox_real, "inbox_real_device": device_real, "result_sha_mismatch": integrity_bad,
             "cards": {cid: {"zh": "sJIA 关注卡" if cid == "sjia-mas" else "自定义卡", "runs": dict(c["runs"]),
                             "tps": c["tps"], "levels": dict(c["levels"])} for cid, c in sorted(cards.items())},
             "custom_cards": len(custom), "custom_active": sum(1 for c in custom if c["active"]), "custom_tps": custom_tps,
             "alerts": alerts, "deliveries": dict(deliveries), "deliveries_by_channel": by_channel, "acks": acks,
             "alerts_sent_real": real_sent}
    return facts, trace, repro, {"nights": sleep["night_count"], "metrics": [m["code"] for m in sleep["metrics"]],
                                 "last_day": sleep["last_day"]}


def reproduce(inst, track) -> dict:
    """输入没变的时点，按同一定义在内存里重算一遍，结果指纹应与星轨记录逐字一致（不写库）。"""
    out = {"checked": 0, "identical": 0, "differ": [], "cards": {}}
    if inst.sjia:
        card = inst.card(track)
        snap = take_snapshot(track, inst.ctx, card)
        status, latest = classify(track, snap, card)
        cache = {tp: values_at(card, obs) for tp, obs in snap.tps.items()}
        _compare(out, "sjia-mas", [(tp, latest[tp]["result"], canonical_json(evaluate_tp(card, tp, cache)[1]))
                                   for tp, s in sorted(status.items()) if s == "FRESH" and latest[tp]["status"] == "EVALUATED"])
    groups = custom_cards.by_code(track, inst.ctx)
    for c in custom_cards.cards(track):
        d, days = c["definition"], groups.get(c["definition"]["code"], {})
        status, latest = custom_cards._status(track, c, days)
        _compare(out, c["card_id"], [(tp, latest[tp]["result"], canonical_json(custom_cards.evaluate(d, tp, days)[1]))
                                     for tp, s in sorted(status.items()) if s == "FRESH" and latest[tp]["status"] == "EVALUATED"])
    return out


def verify_one(inst, card_id: str, tp: str, run_id: int | None = None) -> dict:
    """一条结论现场核对（不写库）：按同一版定义在内存里再算这个时点，和星轨存下的结果比指纹。
    state = SAME 一字不差 / DIFFER 不一样 / STALE 数据在这次计算后有更新（等下次计算）/ NONE 这类卡不支持现场重算。"""
    import engines  # noqa: PLC0415
    import bioage  # noqa: PLC0415
    with closing(open_startrack(inst.ctx)) as track:
        stored, again = None, None
        if card_id == "sjia-mas" and inst.sjia:
            card = inst.card(track)
            snap = take_snapshot(track, inst.ctx, card)
            status, latest = classify(track, snap, card)
            if tp not in latest:
                return {"state": "NONE"}
            if status.get(tp) != "FRESH" or latest[tp]["status"] != "EVALUATED":
                return {"state": "STALE" if status.get(tp) == "STALE" else "NONE"}
            cache = {t: values_at(card, obs) for t, obs in snap.tps.items()}
            stored, again, rid = latest[tp]["result"], canonical_json(evaluate_tp(card, tp, cache)[1]), latest[tp]["run_id"]
        elif card_id.startswith(engines.CARD_PREFIX):
            rule_id = card_id[len(engines.CARD_PREFIX):]
            tpl = next((t for t, v in engines.active(track).items() if rule_id in v["conf"]["rules"]), None)
            if tpl is None or rule_id not in engines.CALC:
                return {"state": "NONE"}
            prof = bioage.load_profile(inst.ctx.root)
            d = engines._definition(tpl, rule_id, prof)
            latest = latest_results(track, sha256_hex(canonical_bytes(d))).get(tp)
            if latest is None or latest["status"] != "EVALUATED":
                return {"state": "NONE"}
            res, inputs = engines.evaluate(rule_id, custom_cards.by_code(track, inst.ctx), tp, prof)
            if latest["inputs"] != inputs:
                return {"state": "STALE"}
            stored, again, rid = latest["result"], canonical_json(res), latest["run_id"]
        else:
            c = next((x for x in custom_cards.cards(track) if x["card_id"] == card_id), None)
            if c is None:
                return {"state": "NONE"}
            days = custom_cards.by_code(track, inst.ctx).get(c["definition"]["code"], {})
            status, latest = custom_cards._status(track, c, days)
            if tp not in latest:
                return {"state": "NONE"}
            if status.get(tp) != "FRESH" or latest[tp]["status"] != "EVALUATED":
                return {"state": "STALE" if status.get(tp) == "STALE" else "NONE"}
            stored, again, rid = latest[tp]["result"], canonical_json(custom_cards.evaluate(c["definition"], tp, days)[1]), latest[tp]["run_id"]
    if run_id is not None and rid != run_id:
        return {"state": "STALE"}
    same = sha256_hex(stored.encode()) == sha256_hex(again.encode())
    return {"state": "SAME" if same else "DIFFER", "run_id": rid}


def last_check(root: Path) -> dict | None:
    """最近一次可信度自检（最新的证据包里的 summary.json）：只取计数和是否通过，不含健康数值。"""
    for p in list_packs(root):
        try:
            with zipfile.ZipFile(root / "evidence" / p["name"]) as z:
                s = json.loads(z.read("summary.json"))
        except (OSError, KeyError, ValueError, zipfile.BadZipFile):
            continue
        t = s.get("tests") or {}
        checks = [{"id": "tests", "ok": bool(t.get("ok")), "passed": t.get("passed"), "total": t.get("total"), "ran": bool(t)},
                  {"id": "labels", "ok": not s.get("labels_above_evidence"), "n": s.get("labels_above_evidence") or 0},
                  {"id": "scrub", "ok": bool((s.get("scrub") or {}).get("ok"))}]
        return {"at": s.get("generated_at"), "ok": all(c["ok"] for c in checks), "checks": checks}
    return None


def _compare(out: dict, card_id: str, items: list) -> None:
    same = 0
    for tp, stored, again in items:
        if sha256_hex(stored.encode()) == sha256_hex(again.encode()):
            same += 1
        elif len(out["differ"]) < 20:
            out["differ"].append({"card": card_id, "tp": tp})
    out["checked"] += len(items)
    out["identical"] += same
    out["cards"][card_id] = {"checked": len(items), "identical": same}


def _side_facts(inst, hooks, bridge) -> dict:
    root = inst.ctx.root
    originals = root / "startorch" / "originals"
    recs = list(originals.glob("*.recognition.json")) if originals.exists() else []
    n_orig = sum(1 for p in originals.iterdir() if p.is_file() and not p.name.endswith(".json")) if originals.exists() else 0
    store = hooks.gene(inst)
    receipts = store.list()
    db = gene_db.stats(store.db_path)
    gene = {"receipts": len(receipts), "files_stored": len({r["sha256"] for r in receipts}), "db_files": db.get("files", 0),
            "db_rows": db.get("rows", 0),
            "items": [{"receipt_id": r["receipt_id"], "sha256_16": r["sha256"][:16], "bytes": r["bytes"], "outcome": r.get("outcome"),
                       "format_code": (r.get("profile") or {}).get("format_code"), "received_at": r.get("received_at"),
                       "db": (r.get("db_now") or {}).get("status") or (r.get("db") or {}).get("status"),
                       "db_rows": (r.get("db_now") or {}).get("rows") or (r.get("db") or {}).get("rows")} for r in receipts]}
    with phone_lifecycle.guard(inst.cluster), closing(inst.cluster._open()) as conn:
        grants = Counter(o for (o,) in conn.execute("SELECT origin FROM grant_def"))
        revoked = conn.execute("SELECT count(*) FROM grant_event WHERE event = 'REVOKED'").fetchone()[0]
        acc = Counter()
        for action, via, outcome, n in conn.execute("SELECT action, via, outcome, count(*) FROM access_record GROUP BY action, via, outcome"):
            acc[f"{action}:{via}:{outcome}"] += n
        mcp_reads = conn.execute("SELECT count(*) FROM access_record WHERE action = 'READ' AND via = 'MCP' AND outcome = 'READ'").fetchone()[0]
    gene_reads = Counter(r.get("outcome") for r in inst.cluster.gene_reads())
    sessions = []
    sp = root / "starling" / "sessions.jsonl"
    if sp.exists():
        sessions = [json.loads(x) for x in sp.read_text("utf-8").splitlines() if x.strip()]
    o = hooks.sources(inst).get("oura") or {}
    pull = o.get("last_pull") or {}
    events = Counter(e.get("kind") for e in device_watch.DeviceEvents(root).list())
    return {
        "originals": {"files": n_orig, "recognitions": len(recs)},
        "gene": gene,
        "cluster": {"grants": dict(grants), "user_grants": grants.get("USER", 0), "revoked": revoked, "access": dict(acc),
                    "mcp_reads": mcp_reads, "gene_reads": dict(gene_reads)},
        "starling": {"sessions": len(sessions), "by_model": sum(1 for s in sessions if str(s.get("by", "")).startswith("千问")),
                     "by_rules": sum(1 for s in sessions if not str(s.get("by", "")).startswith("千问")),
                     "rejected": sum(1 for s in sessions if s.get("rejected")), "masked": sum(1 for s in sessions if s.get("masked"))},
        "oura": {"status": o.get("status"), "connected_at": o.get("connected_at"), "last_pull_at": o.get("last_pull_at"),
                 "last_error": (o.get("last_error") or {}).get("code"), "last_pull_collections": pull.get("collections"),
                 "last_pull_saved": pull.get("saved"), "originals": oura_raw.counts(root),
                 "erasure_evidence": erasure_service.reconcile(root, inst.ctx.instance_id)},
        "apple": {"receipts": len(bridge.receipts()), "phones": len(bridge.phones())},
        "device_events": dict(events),
    }


def instance_facts(app, inst, hooks) -> dict:
    torch, formal, outbox, nature = _torch_facts(inst, app.registry)
    track, trace, repro, sleep = _track_facts(inst, formal, outbox, nature)
    out = {"instance_id": inst.ctx.instance_id, "kind": inst.ctx.kind, "replay": bool(inst.spec.get("replay")),
           "accept": list(inst.ctx.accept), "cards": inst.spec["cards"], "torch": torch, "track": track, "trace": trace,
           "reproduce": repro, "sleep": sleep}
    out.update(_side_facts(inst, hooks, app.bridge(inst)))
    return out


# ----------------------------------------------------------------------------- ledger, labels, scrub

def _config_entries(doc):
    def walk(node, path=""):
        if isinstance(node, dict):
            if "id" in node and "maturity" in node:
                yield path, node
            for k, v in node.items():
                yield from walk(v, f"{path}.{k}" if path else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                yield from walk(v, f"{path}[{i}]")
    return list(walk(doc))


def ledger(tests: dict | None, real: dict | None, hashes: dict) -> list:
    mods = (tests or {}).get("modules") or {}
    out = []
    for cap in CAPABILITIES:
        files = {f: hashes.get(f) for f in cap["files"]}
        level, basis = ("M1", ["源码在：" + "、".join(f"{f}（{(h or '缺')[:12]}）" for f, h in files.items())]) \
            if all(files.values()) else ("M0", ["源码缺：" + "、".join(f for f, h in files.items() if not h)])
        if level == "M1":
            if tests is None:
                basis.append("这次没跑自动测试")
            else:
                got = [mods.get(t) for t in cap["tests"]]
                if got and all(g and g["ran"] > 0 and g.get("passed", 0) == g["ran"]
                               and not g.get("skipped", 0) and not g["failed"] for g in got):
                    level = "M3"
                    basis.append("自动测试通过：" + "、".join(f"{t}（{g['passed']} 条）" for t, g in zip(cap["tests"], got)))
                else:
                    basis.append("自动测试没全过：" + "、".join(t for t, g in zip(cap["tests"], got) if not g or g["failed"] or not g["ran"] or g.get("skipped", 0) or g.get("passed", 0) != g["ran"]))
        real_n = cap["m4"](real) if cap["m4"] and real else 0
        if cap["m4"] is None:
            basis.append(cap["m4_zh"])
        elif real_n and level == "M3":
            level = "M4"
            basis.append(f"我的真实数据：{cap['m4_zh']} {real_n}")
        elif real_n:
            basis.append(f"我的真实数据：{cap['m4_zh']} {real_n}（这次测试没过或没跑，不算 M4）")
        else:
            basis.append(f"我的真实数据：{cap['m4_zh']} 还没有")
        out.append({"id": cap["id"], "zh": cap["zh"], "level": level, "basis": basis, "labels": cap["labels"],
                    "synthetic_only": bool(cap.get("synthetic_only")), "files": files, "tests": cap["tests"],
                    "real_count": real_n, "m5": "待本人签字"})
    return out


def label_check(product_config: dict, caps: list) -> list:
    """HR-54：标签不得高于证据。没登记能力的入口只列出来，不算违规。"""
    by_label = {}
    for c in caps:
        for lab in c["labels"]:
            by_label.setdefault(lab, []).append(c)
    out = []
    for path, e in _config_entries(product_config):
        m = e["maturity"]
        mine = by_label.get(e["id"]) or by_label.get(path) or []
        floor = FLOOR.get(m)
        if mine and floor:
            if all(c["synthetic_only"] for c in mine) and m == "ready":
                floor = "M3"
            have = min((c["level"] for c in mine), key=LEVELS.index)
            ok = LEVELS.index(have) >= LEVELS.index(floor)
            verdict = "OK" if ok else "LABEL_ABOVE_EVIDENCE"
        else:
            have, ok = (min((c["level"] for c in mine), key=LEVELS.index) if mine else None), True
            verdict = "NO_FLOOR" if mine else "NOT_REGISTERED"
        out.append({"id": e["id"], "path": path, "zh": e.get("zh"), "maturity": m, "maturity_zh": LABEL_ZH.get(m, m),
                    "needs": floor, "evidence": have, "verdict": verdict,
                    "capabilities": [c["id"] for c in mine]})
    return out


def secrets_to_check(app, hooks) -> list:
    """令牌、密钥、原始文件名：只在内存里拿来比对，不写进任何地方。"""
    out = []
    for inst in app.instances.values():
        try:
            client = hooks.oura_client(inst)
            raw = client.store.get(client.account)
            if raw:
                tok = json.loads(raw)
                out += [("OURA_TOKEN", tok.get("access_token")), ("OURA_TOKEN", tok.get("refresh_token"))]
            out.append(("OURA_CLIENT_SECRET", client.client_secret()))
        except Exception:  # noqa: BLE001 — 取不到就没有可比的
            pass
        try:
            out += [("BRIDGE_CREDENTIAL", h) for h in app.bridge(inst)._hashes().values()]
        except Exception:  # noqa: BLE001
            pass
        for r in hooks.gene(inst).list():
            out += [("GENE_FILE_NAME", r.get("file_name")), ("GENE_FILE_NAME", r.get("stored_as"))]
        originals = inst.ctx.root / "startorch" / "originals"
        for p in originals.glob("*.recognition.json") if originals.exists() else []:
            try:
                out.append(("ORIGINAL_FILE_NAME", json.loads(p.read_text("utf-8")).get("name")))
            except ValueError:
                pass
    return [(k, v) for k, v in out if isinstance(v, str) and len(v.strip()) >= 6]


def scrub(texts: dict, secrets: list) -> dict:
    hits = Counter()
    for kind, s in secrets:
        for name, text in texts.items():
            if s in text:
                hits[f"{kind}@{name}"] += 1
    keys = Counter()

    def walk(node, where):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in FORBIDDEN_KEYS:
                    keys[f"{k}@{where}"] += 1
                walk(v, where)
        elif isinstance(node, list):
            for v in node:
                walk(v, where)
    for name, text in texts.items():
        if name.endswith(".json"):
            walk(json.loads(text), name)
    return {"ok": not hits and not keys, "checked_strings": len(secrets), "string_hits": sorted(hits),
            "forbidden_keys": sorted(keys), "files": sorted(texts),
            "note": "比对过令牌、密钥、原始文件名（只在内存里比，不写出），以及数值类字段名；出现任何一项就不出包。"}


# ----------------------------------------------------------------------------- build

def build(app, *, tests: dict | None, now: str, hooks) -> dict:
    """tests = run_tests() 的结果（不跑测试就传 None）；hooks = 来源登记、基因纳管、Oura 客户端（server 提供）。
    调用方持有 app.lock。"""
    hashes = code_hashes()
    disk_cfg = json.loads((APP / "web" / "product_config.json").read_text("utf-8"))
    facts = {inst.ctx.instance_id: instance_facts(app, inst, hooks) for inst in app.instances.values()}
    real_key = next((i.ctx.instance_id for i in app.instances.values()
                     if not i.spec.get("replay") and i.nature == "REAL"), None)
    caps = ledger(tests, facts.get(real_key), hashes)
    labels = label_check(disk_cfg, caps)
    over = [x for x in labels if x["verdict"] == "LABEL_ABOVE_EVIDENCE"]
    stamp = datetime.fromisoformat(now).strftime("%Y%m%d-%H%M%S")
    folder = app.root / "evidence"
    name = f"PTDS-evidence-{stamp}.zip"
    for i in range(2, 100):  # 同一秒里再生成一次：加序号，不覆盖
        if not (folder / name).exists():
            break
        name = f"PTDS-evidence-{stamp}-{i}.zip"
    summary = {"generated_at": now, "pack": name, "python": sys.version.split()[0], "platform": sys.platform,
               "code_sha256": sha256_hex(canonical_json(hashes).encode()),
               "product_config_sha256": hashes.get("web/product_config.json"),
               "config_changed_since_start": canonical_json(disk_cfg) != canonical_json(app.product_config),
               "real_instance": real_key,
               "tests": None if tests is None else {k: tests.get(k) for k in ("ok", "total", "passed", "seconds", "python", "platform", "error")},
               "levels": dict(Counter(c["level"] for c in caps)), "labels_above_evidence": len(over),
               "reproduce": {k: {"checked": f["reproduce"]["checked"], "identical": f["reproduce"]["identical"]} for k, f in facts.items()},
               "trace": {k: {"tps": f["trace"]["tps"], "traced": f["trace"]["tps_traced"]} for k, f in facts.items()},
               "result_sha_mismatch": {k: f["track"]["result_sha_mismatch"] for k, f in facts.items()}}
    texts = {"summary.json": _dump(summary), "ledger.json": _dump(caps), "labels.json": _dump(labels),
             "code_hashes.json": _dump(hashes)}
    for k, f in facts.items():
        texts[f"instances/{k}.json"] = _dump(f)
    if tests is not None:
        texts["tests.json"] = _dump({k: v for k, v in tests.items() if k != "text"})
        texts["tests.txt"] = tests.get("text") or ""
    texts["README.md"] = readme(summary, caps, labels, facts)
    sc = scrub(texts, secrets_to_check(app, hooks))
    summary["scrub"] = {k: sc[k] for k in ("ok", "checked_strings", "string_hits", "forbidden_keys")}
    if not sc["ok"]:
        return {"ok": False, "error": "SCRUB_FAILED", "summary": summary, "ledger": caps, "labels": over}
    texts["scrub.json"] = _dump(sc)
    texts["summary.json"] = _dump(summary)
    folder.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n in sorted(texts):
            z.writestr(n, texts[n])
    data = buf.getvalue()
    target = folder / name
    with open(target, "xb") as handle:  # 只新建不覆盖
        handle.write(data)
    return {"ok": True, "name": name, "path": str(target), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(),
            "summary": summary, "ledger": caps, "labels": over}


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=False)


def readme(summary: dict, caps: list, labels: list, facts: dict) -> str:
    t = summary["tests"]
    lines = ["# PTDS 验收证据包", "",
             f"生成时间：{summary['generated_at']}　包名：{summary['pack']}　代码指纹：{summary['code_sha256'][:16]}", "",
             "包里只有计数、代码、指纹和日期，没有任何健康数值、令牌、密钥或原始文件名（出包前已自检，见 scrub.json）。", "",
             "## 自动测试", "",
             ("这次没跑。" if t is None else f"{t['total']} 条，通过 {t['passed']} 条，{'全部通过' if t['ok'] else '有失败'}"
              f"（Python {t.get('python')}，{t.get('platform')}，{t.get('seconds')} 秒）。逐条见 tests.txt。"), "",
             "## 能力与证据等级（准则 §6）", "",
             "M1 源码在；M3 自动测试通过（真实进程、合成数据、重启读回）；M4 我的真实数据里有这项能力经产品入口留下的记录；M5 本人签字。", "",
             "| 能力 | 等级 | 依据 |", "|---|---|---|"]
    for c in caps:
        lines.append(f"| {c['zh']} | {c['level']} | {'；'.join(c['basis'])} |")
    over = [x for x in labels if x["verdict"] == "LABEL_ABOVE_EVIDENCE"]
    lines += ["", "## 标签核对（HR-54：标签不得高于证据）", ""]
    lines += [f"- {x['zh']}（{x['path']}）标为「{x['maturity_zh']}」，需要 {x['needs']}，现在 {x['evidence']}" for x in over] or ["没有标签高于证据。"]
    if summary["config_changed_since_start"]:
        lines.append("- 注意：产品配置文件在服务启动后改过，页面上的标签要重启后才和文件一致。")
    lines += ["", "## 可复现与追溯", ""]
    for k, f in facts.items():
        r, tr = f["reproduce"], f["trace"]
        lines.append(f"- {k}：输入没变的时点重算 {r['checked']} 个，逐字一致 {r['identical']} 个；"
                     f"最新计算的时点 {tr['tps']} 个，能完整追到星炬正式记录 {tr['tps_traced']} 个；"
                     f"结果指纹不符 {f['track']['result_sha_mismatch']} 条。")
    lines += ["", "## 本人签字（M5）", "", "以上能力我在本机用自己的数据看过、走过：", "",
              "签字：＿＿＿＿＿＿＿＿　　日期：＿＿＿＿＿＿＿＿", "",
              "## 文件", "", "- summary.json 摘要　- ledger.json 能力与等级　- labels.json 标签核对",
              "- instances/*.json 每个实例的计数（无数值）　- code_hashes.json 每个程序文件的指纹",
              "- tests.json / tests.txt 自动测试结果　- scrub.json 出包前自检", ""]
    return "\n".join(lines)


def list_packs(root: Path) -> list:
    folder = root / "evidence"
    if not folder.exists():
        return []
    return [{"name": p.name, "bytes": p.stat().st_size} for p in sorted(folder.glob("PTDS-evidence-*.zip"), reverse=True)
            if NAME_RE.fullmatch(p.name)][:20]
