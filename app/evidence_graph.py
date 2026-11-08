"""证据图谱（只读观察视图，PRD 4.5 / DC-03）：把星炬、星轨、星簇各自已经留下的记录拼成可追溯的链。

- 不写任何事件，不推断补边：每条边都来自某个账本里已经写着的字段（run_input、source_ref、授权记录……）。
- trace(tp)：一条状态结论 → 哪次计算 → 用了哪些数据（哪一版）→ 来自哪里（原件、识别记录、设备、表格）
  → 交给星轨的批次 → 之后谁经哪个授权用过它。
- traceable()：北极星指标"可追溯状态结论数"——当前结论里，全部输入都能追到正式资产
  （来源、版本、信度齐全）的条数。
"""
from __future__ import annotations

import json
import re
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from cards import open_startrack
from startorch_outbox import open_startorch
from h1_common import H1Error
import evidence_navigation

SRC_ZH = {"MANUAL": "手工录入", "TABLE": "表格导入", "OCR_LLM": "化验单识别", "SYNTHETIC": "合成", "DEVICE_GARMIN": "Garmin", "DEVICE_OURA": "Oura",
          "APPLE_HEALTH": "苹果健康", "DEVICE_SOMALOOP": "Somaloop 手环", "DEVICE_QKEER": "Qkeer", "TEXT_LLM": "文本抽取",
          "DEVICE_WITHINGS": "Withings", "DEVICE_CGM": "连续血糖"}
TRIGGER_ZH = {"SYNC": "数据到达后计算", "AUTO_UPDATE": "来源更新后自动更新", "RECOMPUTE": "手动重新计算"}
LEVEL_ZH = {"ALERT": "关注", "WATCH": "观察", "UNDETERMINED": "无法判定", "NONE": "无"}
CHAN_ZH = {"MACOS": "Mac 通知", "SOMALOOP": "手环", "BANNER": "站内横幅", "TEST": "测试通道"}


def _origin(inst, source_ref: str, observation=None, unique_key=None) -> dict:
    """source_ref 写着原件在哪；这里只按它去找，找不到就如实说找不到。"""
    out = {"ref": source_ref, "kind": source_ref.split(":", 1)[0] if source_ref else ""}
    m = re.match(r"OCR:([0-9a-f]{16})#p(\d+)l(\d+)$", source_ref or "")
    if m:
        doc_id = "doc:OCR:" + m.group(1)
        meta = evidence_navigation.document(inst, doc_id)
        out.update(zh="化验单原件", original=None, line=None, page=int(m.group(2)),
                   line_no=int(m.group(3)), found=meta["found"], document_id=doc_id,
                   destination=evidence_navigation.destination({"kind": "document", "id": doc_id}))
        if not meta["found"]:
            out.update(error=meta.get("error"), reason=meta.get("reason"))
            return out
        try:
            original = evidence_navigation.resolve_original(inst, doc_id)
            out["original"] = original.name
            folder = Path("startorch/originals")
            doc, line = evidence_navigation.ocr_line(inst, m.group(1), int(m.group(2)), int(m.group(3)), observation, unique_key)
            out.update(line=line.replace("\t", "　"), recognized_at=doc.get("recognized_at"),
                       engine=(doc.get("engine") or {}).get("model"), file_name=doc.get("name"))
            try:
                deid = evidence_navigation._json(inst, folder / (m.group(1) + ".deid.json"))
                if deid.get("deidentified"):
                    out.update(zh="化验单原件 · 真实·已脱敏", deidentified=True)
            except H1Error as exc:
                if exc.code != "ORIGINAL_NOT_FOUND":
                    raise
        except H1Error as exc:
            out.update(found=False, original=None, error=exc.code, reason=exc.detail)
    elif source_ref.startswith("OURA:"):
        out.update(zh="Oura 官方接口 · " + source_ref.split(":", 2)[1], found=True)
    elif source_ref.startswith("SOMALOOP:"):  # 体验腕带：SOMALOOP:设备:live|history:种类:…（原始记录在 band_trial.jsonl）
        parts = source_ref.split(":")
        how = {"live": "实时读数", "history": "腕带存的历史"}.get(parts[2] if len(parts) > 2 else "", "读数")
        out.update(zh="Somaloop 体验腕带 · 腕带桥直连 · " + how, found=True)
    elif source_ref.startswith("AH:"):
        out.update(zh="苹果健康 · " + source_ref.split(":")[1], found=True)
    elif source_ref.startswith(("TABLE:", "FILE:")):
        out.update(zh="表格导入 · " + source_ref.split("#")[-1].replace("row", "第 ") + " 行", found=True)
        match = re.match(r"(TABLE|FILE):([0-9a-f]{16})#", source_ref)
        if match:
            doc_id = "doc:" + match.group(1) + ":" + match.group(2)
            out.update(document_id=doc_id, destination=evidence_navigation.destination({"kind": "document", "id": doc_id}))
    elif source_ref.startswith("SYN:"):
        out.update(zh="合成数据 · " + source_ref, found=True)
    elif source_ref.startswith("MANUAL:"):
        out.update(zh="手工录入 · " + source_ref.split("#")[-1].replace("row", "第 ") + " 行", found=True)
    else:
        out.update(zh=source_ref or "来源未记录", found=bool(source_ref))
    return out


def _versions(torch, oid: str) -> list:
    rows = torch.execute("SELECT revision, payload, saved_at FROM formal_observation WHERE observation_id = ? "
                         "ORDER BY revision", (oid,)).fetchall()
    return [dict(json.loads(p), revision=r, saved_at=s) for r, p, s in rows]


def versions(inst, oid: str) -> list:
    """一条数据的全部版本（只追加，旧版保留），以及每一版被哪几次计算用过。"""
    with closing(open_startrack(inst.ctx)) as track, closing(open_startorch(inst.ctx)) as torch:
        out = []
        import engines  # noqa: PLC0415 - 卡名（sJIA 关注卡、自定义卡、引擎算法卡）
        names = engines.card_names(track)
        for v in _versions(torch, oid):
            rows = track.execute("SELECT DISTINCT i.run_id, c.card_id FROM run_input i JOIN run r USING (run_id) "
                                 "JOIN card_def c ON c.card_def_id = r.card_def_id WHERE i.observation_id = ? AND i.revision = ? "
                                 "ORDER BY i.run_id", (oid, v["revision"])).fetchall()
            cards = []
            for _, cid in rows:
                n = names.get(cid, cid)
                if n not in cards:
                    cards.append(n)
            out.append({"revision": v["revision"], "status": v.get("status"), "value": v.get("value_raw"),
                        "unit": v.get("unit_raw"), "comparator": v.get("comparator"), "saved_at": v["saved_at"],
                        "source_zh": SRC_ZH.get(v.get("source_kind"), v.get("source_kind")), "runs": [r for r, _ in rows],
                        "cards": cards})
        return out


def _commit_of(torch, oid: str, rev: int):
    r = torch.execute("SELECT c.commit_id, c.batch_id, c.committed_at FROM h1_outbox o JOIN h1_commit c USING (commit_id) "
                      "WHERE o.observation_id = ? AND o.revision = ?", (oid, rev)).fetchone()
    if not r:
        return None
    ex = torch.execute("SELECT data_file, file_sha256, exported_at FROM h1_export_log WHERE commit_id = ? ORDER BY id DESC",
                       (r[0],)).fetchone()
    return {"commit_id": r[0], "batch_id": r[1], "committed_at": r[2],
            "export": {"file": Path(ex[0]).name, "sha256": ex[1], "at": ex[2]} if ex else None}


def _complete(p: dict) -> list:
    """正式资产三要素：来源、版本、信度。缺哪个就列哪个。"""
    miss = []
    if not p.get("source_kind") or not p.get("source_ref"):
        miss.append("来源")
    if not p.get("revision"):
        miss.append("版本")
    if not p.get("trust_tier"):
        miss.append("信度")
    return miss


def _utc(t) -> str:
    try:
        return datetime.fromisoformat(t).astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError):
        return ""


def _card_names(track) -> dict:
    """card_id → 卡名：sJIA 关注卡、引擎算法卡（规则库里的名字），或自定义卡定义里写的名字。"""
    out = {"sjia-mas": "sJIA 关注卡"}
    for cid, d in track.execute("SELECT card_id, definition FROM card_def WHERE card_id != 'sjia-mas' ORDER BY registered_at"):
        out[cid] = json.loads(d).get("name") or cid
    import engines  # noqa: PLC0415
    for cid, n in engines.card_names(track).items():
        if cid.startswith(engines.CARD_PREFIX):
            out[cid] = n.split(" · ")[-1]  # 图上只写算法名，卡组名在节点详情里
    for tpl, t in engines.TEMPLATES.items():  # 引擎模板的“有新结果”通知按模板记
        out[engines.TPL_PREFIX + tpl] = t["zh"]
    return out


def _rule_name(ref) -> str | None:
    import rule_registry as RR  # noqa: PLC0415
    r = RR.BY_ID.get(str(ref or "").split("@")[0])
    return r["name"] if r else None


def engine_cards(inst) -> list:
    """R08：引擎模板建出来的卡（生物年龄、睡眠、炎症……）也能在证据图谱里逐条追。每个时点取最新一次计算。"""
    import engines  # noqa: PLC0415
    with closing(open_startrack(inst.ctx)) as track:
        names = engines.card_names(track)
        on = [engines.CARD_PREFIX + r for tpl, t in sorted(engines.active(track).items(),
                                                            key=lambda kv: engines.ORDER.index(kv[0]) if kv[0] in engines.ORDER else 99)
              if tpl != "MAS" for r in t["conf"]["rules"]]
        # 体验腕带卡（band_cards）：不是引擎模板，账本里有就列出来
        on += [cid for (cid,) in track.execute("SELECT DISTINCT card_id FROM card_def WHERE json_extract(definition, '$.template') = 'LIVE' "
                                               "ORDER BY card_id") if cid not in on]
        out = []
        for cid in on:
            cur = {}
            for tp, st, lv, result in track.execute(
                    "SELECT t.tp_date, t.status, t.level, t.result FROM run_tp t JOIN run r USING (run_id) "
                    "JOIN card_def c ON c.card_def_id = r.card_def_id WHERE c.card_id = ? ORDER BY t.run_id", (cid,)):
                cur[tp] = (st, lv, result)
            tps = []
            for tp in sorted(cur):
                st, lv, result = cur[tp]
                if st != "EVALUATED":
                    continue
                res = json.loads(result)
                tps.append({"tp": tp, "level": lv, "level_zh": res.get("text") or res.get("reason") or "算不了",
                            "status": res.get("status"), "value": res.get("value"), "unit": res.get("unit")})
            if tps:
                out.append({"card_id": cid, "name": names.get(cid, cid), "engine": True, "timepoints": tps})
        return out


def trace(inst, tp: str, records: list | None = None, grants: list | None = None, card_id: str = "sjia-mas", run_id=None) -> dict:
    if run_id not in (None, ""):
        if isinstance(run_id, bool) or not re.fullmatch(r"[1-9][0-9]{0,18}", str(run_id)) or int(run_id) > 2**63 - 1:
            raise H1Error("GRAPH_RUN_INVALID", "计算记录标识无效")
        run_id = int(run_id)
    else:
        run_id = None
    with closing(open_startrack(inst.ctx)) as track, closing(open_startorch(inst.ctx)) as torch:
        runs = track.execute("SELECT r.run_id, r.trigger, r.started_at, t.status, t.level, t.result FROM run_tp t "
                             "JOIN run r USING (run_id) JOIN card_def c ON c.card_def_id = r.card_def_id "
                             "WHERE t.tp_date = ? AND c.card_id = ? " + ("AND r.run_id = ? " if run_id is not None else "") +
                             "ORDER BY r.run_id", (tp, card_id, run_id) if run_id is not None else (tp, card_id)).fetchall()
        if not runs:
            return dict({"tp": tp, "found": False}, **({"run_id": run_id, "card_id": card_id} if run_id is not None else {}))
        rid, trig, at, status, level, result = runs[-1]
        res = json.loads(result)
        cdef = json.loads(track.execute("SELECT c.definition FROM run r JOIN card_def c ON c.card_def_id = r.card_def_id "
                                        "WHERE r.run_id = ?", (rid,)).fetchone()[0])
        inputs = []
        for oid, rev, role in track.execute("SELECT observation_id, revision, role FROM run_input WHERE run_id = ? "
                                            "AND tp_date = ? ORDER BY role DESC, observation_id", (rid, tp)):
            exact = torch.execute("SELECT payload,saved_at,unique_key FROM formal_observation WHERE observation_id=? AND revision=?",
                                  (oid, rev)).fetchone()
            used = dict(json.loads(exact[0]), revision=rev, saved_at=exact[1]) if exact else None
            if used is None:
                inputs.append({"observation_id": oid, "revision": rev, "role": role, "found": False,
                               "missing": ["正式资产"]})
                continue
            latest_raw = torch.execute("SELECT revision,payload,saved_at FROM formal_observation WHERE observation_id=? "
                                       "ORDER BY revision DESC LIMIT 1", (oid,)).fetchone()
            latest = dict(json.loads(latest_raw[1]), revision=latest_raw[0], saved_at=latest_raw[2])
            version_count = torch.execute("SELECT count(*) FROM formal_observation WHERE observation_id=?", (oid,)).fetchone()[0]
            inputs.append({
                "observation_id": oid, "revision": rev, "role": role, "found": True, "code": used["code"],
                "label": getattr(inst.app.registry.current.codes.get(used["code"]), "label_zh", used["code"]),
                "value": used["value_raw"], "unit": used.get("unit_raw"), "comparator": used.get("comparator"),
                "observed": (used.get("temporal") or {}).get("observed_at") or (used.get("temporal") or {}).get("observed_date"),
                "source_kind": used.get("source_kind"), "source_zh": SRC_ZH.get(used.get("source_kind"), used.get("source_kind")),
                "trust_tier": used.get("trust_tier"), "saved_at": used["saved_at"], "status": used.get("status"),
                "versions": version_count, "superseded": latest["revision"] != rev,
                "destination": evidence_navigation.destination({"kind": "observation", "observation_id": oid, "revision": rev}),
                "latest": {"revision": latest["revision"], "value": latest["value_raw"], "status": latest.get("status"),
                           "saved_at": latest["saved_at"]} if latest["revision"] != rev else None,
                "origin": _origin(inst, used.get("source_ref") or "", used, exact[2]), "handoff": _commit_of(torch, oid, rev),
                "missing": _complete(used)})
        alerts = []
        card_name = cdef.get("name") or _card_names(track).get(card_id, card_id)
        q = [(tp, card_id, None)]
        if cdef.get("kind") == "ENGINE_RULE" and cdef.get("template"):  # 引擎卡的“有新结果”通知按模板记，正文里写着算法名
            import engines  # noqa: PLC0415
            q.append((tp, engines.TPL_PREFIX + cdef["template"], _rule_name(cdef.get("rule"))))
        found = []
        for qtp, qcard, must in q:
            for key, lv, title, created, body in track.execute(
                    "SELECT dedupe_key, level, title, created_at, body FROM alert_log WHERE tp_date = ? AND card_id = ? ORDER BY created_at",
                    (qtp, qcard)):
                if must is None or must in (body or ""):
                    found.append((key, lv, title, created))
        for key, lv, title, created in found:
            dl = [{"channel": c, "zh": CHAN_ZH.get(c, c), "outcome": o, "at": a} for c, o, a in track.execute(
                "SELECT channel, outcome, attempted_at FROM alert_delivery WHERE dedupe_key = ? ORDER BY id", (key,))]
            alerts.append({"dedupe_key": key, "level": lv, "level_zh": LEVEL_ZH.get(lv, lv), "title": title,
                           "created_at": created, "deliveries": dl})
    # 之后谁用过：授权记录里读取了这张卡（或全部卡）的，以及这条结论的提醒推送（星簇补记）
    gcard = {g["id"]: g.get("card") for g in grants or []}
    titles = {a["title"] for a in alerts}
    used_by = [r for r in records or [] if r.get("egress") and _utc(r.get("at")) >= _utc(at)
               and ((r.get("action") == "READ" and gcard.get(r.get("grant")) in ("*", "SJIA_FOCUS") and card_id == "sjia-mas")
                    or (r.get("action") == "PUSH" and tp in (r.get("summary") or "")
                        and any(t in (r.get("summary") or "") for t in titles)))]
    missing = sorted({m for i in inputs for m in i["missing"]})
    return {"tp": tp, "found": True, "card_id": card_id, "card_zh": card_name,
            "conclusion": {"level": level, "level_zh": LEVEL_ZH.get(level, level), "status": status,
                           "drivers": res.get("drivers") or [], "engine_version": res.get("engine_version"),
                           # R08 证据回执：引擎卡的数值和规则（sJIA 关注卡、自定义卡没有这些字段时为空）
                           "value": res.get("value"), "unit": res.get("unit"), "text": res.get("text"),
                           "value_status": res.get("status"), "rule": res.get("rule") or cdef.get("rule"),
                           "rule_name": _rule_name(res.get("rule") or cdef.get("rule")),
                           "fingerprint": res.get("fingerprint") or cdef.get("fingerprint")},
            "run": {"run_id": rid, "trigger": trig, "trigger_zh": TRIGGER_ZH.get(trig, trig), "started_at": at,
                    "history": [{"run_id": r[0], "trigger": r[1], "trigger_zh": TRIGGER_ZH.get(r[1], r[1]), "at": r[2],
                                 "level_zh": LEVEL_ZH.get(r[4], r[4])} for r in runs]},
            "inputs": inputs, "alerts": alerts, "used_by": used_by,
            "traceable": bool(inputs) and not missing, "missing": missing}


def hidden_cards(inst) -> set:
    """界面上不出现的卡：个人基座（REAL）里 sJIA 关注卡是隐藏的（产品负责人 2026-10-14），证据图谱也不列它、不算它。"""
    return {"sjia-mas"} if inst.ctx.kind == "REAL" else set()


def hide_kg(g: dict, hidden: set) -> dict:
    if not hidden:
        return g
    drop = {n["id"] for n in g["nodes"] if n["id"] in {"card:" + c for c in hidden}
            or n.get("card") in hidden or n.get("card_id") in hidden or n.get("wall_id") in hidden}
    nodes = [n for n in g["nodes"] if n["id"] not in drop]
    edges = [e for e in g["edges"] if e["from"] not in drop and e["to"] not in drop]
    linked = {e["from"] for e in edges} | {e["to"] for e in edges}
    nodes = [n for n in nodes if n["id"] in linked or n["kind"] in ("source", "indicator", "store")]
    kinds = {}
    for n in nodes:
        kinds[n["kind"]] = kinds.get(n["kind"], 0) + 1
    return {"nodes": nodes, "edges": edges, "kinds": kinds}


def traceable(inst, hidden: set = frozenset()) -> dict:
    """北极星：当前每个时点的最新结论里，全部输入都能追到正式资产（来源、版本、信度齐全）的条数。"""
    with closing(open_startrack(inst.ctx)) as track, closing(open_startorch(inst.ctx)) as torch:
        latest = track.execute("SELECT t.tp_date, max(t.run_id) FROM run_tp t JOIN run r USING (run_id) "
                               "JOIN card_def c ON c.card_def_id = r.card_def_id "
                               "WHERE c.card_id NOT IN (%s) GROUP BY c.card_id, t.tp_date" % ",".join("?" * len(hidden) or ["''"]),
                               tuple(hidden)).fetchall()
        ok, bad = 0, []
        for tp, rid in latest:
            st = track.execute("SELECT status FROM run_tp WHERE run_id = ? AND tp_date = ?", (rid, tp)).fetchone()[0]
            if st != "EVALUATED":
                continue
            good = True
            n = 0
            for oid, rev in track.execute("SELECT observation_id, revision FROM run_input WHERE run_id = ? AND tp_date = ?",
                                          (rid, tp)):
                n += 1
                row = torch.execute("SELECT payload FROM formal_observation WHERE observation_id = ? AND revision = ?",
                                    (oid, rev)).fetchone()
                if row is None or _complete(dict(json.loads(row[0]), revision=rev)):
                    good = False
            if good and n:
                ok += 1
            else:
                bad.append(tp)
        return {"traceable": ok, "total": ok + len(bad), "not_traceable": bad}


def events(inst, records: list, gene: list, bridge_receipts: list, device_events: list, sources: dict) -> list:
    """按时间倒序的事件轨迹（每条都是某个账本里已有的一行）。lane：source 数据源 / data 数据 / state 计算 / auth 授权。"""
    ev = []
    with closing(open_startrack(inst.ctx)) as track, closing(open_startorch(inst.ctx)) as torch:
        for oid, rev, p, saved in torch.execute("SELECT observation_id, revision, payload, saved_at FROM formal_observation ORDER BY rowid"):
            d = json.loads(p)
            verb = "保存" if rev == 1 else ("撤回" if d.get("status") != "ACTIVE" else "更正")
            zh = getattr(inst.app.registry.current.codes.get(d["code"]), "label_zh", d["code"])
            ev.append({"lane": "data", "at": saved, "text": f"{verb} {zh} {d['value_raw']}{(' ' + d['unit_raw']) if d.get('unit_raw') else ''} · 第 {rev} 版 · {SRC_ZH.get(d.get('source_kind'), d.get('source_kind'))}",
                       "ref": {"observation": oid, "revision": rev}})
        for cid, batch, n, at in torch.execute("SELECT commit_id, batch_id, count, committed_at FROM h1_commit ORDER BY rowid"):
            ev.append({"lane": "data", "at": at, "text": f"交给星轨 · 批次 {batch} · {n} 条", "ref": {"commit": cid}})
        names = _card_names(track)
        for rid, trig, at, cid in track.execute("SELECT r.run_id, r.trigger, r.started_at, c.card_id FROM run r "
                                                "JOIN card_def c USING (card_def_id) ORDER BY r.run_id"):
            tps = [f"{t} {LEVEL_ZH.get(lv, lv)}" for t, lv in track.execute(
                "SELECT tp_date, level FROM run_tp WHERE run_id = ? ORDER BY tp_date", (rid,))]
            if cid == "VITALS":  # 我的体征只描述、不定级（r63）：不写“无”，写取了几项读数
                tps = [t.split()[0] for t in tps]
                n = track.execute("SELECT count(*) FROM run_input WHERE run_id = ?", (rid,)).fetchone()[0]
                tps = [f"{t} · 取最近读数 {n} 项" for t in tps]
            shown = tps if len(tps) <= 6 else tps[:3] + [f"…共 {len(tps)} 个时点"]
            ev.append({"lane": "state", "at": at, "text": f"计算 #{rid} · {names.get(cid, cid)} · {TRIGGER_ZH.get(trig, trig)} · " + "、".join(shown),
                       "ref": {"run": rid, "card": cid, "tps": [t.split()[0] for t in tps]}})
        for key, tp, lv, title, at, cid in track.execute("SELECT dedupe_key, tp_date, level, title, created_at, card_id FROM alert_log"):
            ev.append({"lane": "state", "at": at, "text": f"提醒 · {tp} {LEVEL_ZH.get(lv, lv)} · {title}", "ref": {"tp": tp, "card": cid}})
    for r in reversed(records):  # 授权记录是新的在前，这里按发生先后放
        ev.append({"lane": "auth", "at": r["at"], "text": f"{r['summary']} · {r['obj']} · {r['how']} · {r['result']}",
                   "ref": {"grant": r.get("grant")}})
    for g in gene:
        ev.append({"lane": "source", "at": g["received_at"], "text": f"纳管基因数据 {g['file_name']} · 指纹 {g['sha256'][:12]}",
                   "ref": {"gene": g["receipt_id"]}})
    for r in bridge_receipts:
        ev.append({"lane": "source", "at": r.get("when") or r.get("at") or "", "text": "苹果健康同步 · 收到 %s 条" % r.get("received", "?"),
                   "ref": {}})
    for d in device_events:
        ev.append({"lane": "source", "at": d["at"], "text": d["title"] + " · " + (d.get("reason") or d.get("body", "")), "ref": {}})
    folder = inst.ctx.root / "startorch" / "originals"
    if folder.exists():
        for f in folder.glob("*.recognition.json"):
            doc = json.loads(f.read_text("utf-8"))
            ev.append({"lane": "source", "at": doc.get("recognized_at", ""),
                       "text": f"识别化验单 {doc.get('name', '')} · {len(doc.get('rows') or [])} 项候选 · 原件 {doc.get('original', '')}",
                       "ref": {"original": doc.get("original")}})
    o = sources.get("oura") or {}
    if o.get("connected_at"):
        ev.append({"lane": "source", "at": o["connected_at"], "text": "接入 Oura（官方授权）", "ref": {}})
    if o.get("disconnected_at"):
        ev.append({"lane": "source", "at": o["disconnected_at"], "text": "断开 Oura", "ref": {}})
    order = {id(e): n for n, e in enumerate(ev)}  # 同一秒内按账本里的先后
    ev.sort(key=lambda e: (_utc(e["at"]), order[id(e)]), reverse=True)
    for n, e in enumerate(ev, start=1):
        e["id"] = "E%03d" % (len(ev) - n + 1)
    return ev


def _local_short(inst, at: str) -> str:
    try:
        from zoneinfo import ZoneInfo
        return datetime.fromisoformat(at.replace("Z", "+00:00")).astimezone(ZoneInfo(inst.ctx.tz)).strftime("%m-%d %H:%M")
    except Exception:  # noqa: BLE001
        return (at or "")[5:16].replace("T", " ")


KIND_ORDER = ["source", "document", "indicator", "card", "conclusion", "alert", "channel", "grant", "party", "store"]
BASIS_ZH = {"formal_observation.source_ref": "星炬正式记录的原件引用", "formal_observation.source_kind": "星炬正式记录的来源",
            "run_input": "星轨计算的输入记录", "run_tp": "星轨计算结果", "vitals": "我的体征的数据绑定", "alert_log": "星轨提醒记录",
            "alert_delivery": "提醒送达记录", "gene receipts": "基因纳管回执", "genotypes.db": "基因位点库",
            "grant_def.card": "星簇授权的范围", "grant_def.object": "星簇授权的对象", "access_record": "星簇授权记录"}
GRANT_CARD_ZH = {"*": "全部状态卡", "SJIA_FOCUS": "sJIA 关注卡", "VITALS": "我的体征", "GENE_LOCI": "基因位点"}


def _current_formal_rows(conn):
    # Sort only identity/row references. Joining payload before ORDER BY makes
    # SQLite spill complete observations into its temporary sorter. A separate
    # cursor preserves first-seen order without materializing all payloads.
    references = conn.execute("SELECT observation_id,min(rowid),max(rowid) "
        "FROM formal_observation GROUP BY observation_id ORDER BY min(rowid)")
    payloads = conn.cursor()
    for _oid, _first, last in references:
        yield payloads.execute("SELECT observation_id,revision,payload,saved_at "
            "FROM formal_observation WHERE rowid=?", (last,)).fetchone()


def knowledge(inst, snap: dict, records: list, grants: list, gene: list, objects: dict) -> dict:
    """知识图谱：把同一批账本记录按"东西"（来源、原件、指标、状态卡、结论、提醒、授权、对象）归并成点，
    按账本里写着的关系连边。和 trace 一样只读、不推断：每条边都能说出来自哪张表的哪个字段。"""
    nodes, edges = {}, {}

    def node(nid, kind, label, **kw):
        if nid not in nodes:
            nodes[nid] = dict(id=nid, kind=kind, label=label, **kw)
        return nid

    def edge(a, b, rel, basis, n=1, source_kind=None):
        key = (a, b, rel, source_kind)
        e = edges.get(key)
        if e:
            e["n"] += n
        else:
            edges[key] = {"from": a, "to": b, "rel": rel, "n": n, "basis": BASIS_ZH.get(basis, basis) + "（" + basis + "）"}
            if source_kind:
                edges[key]["source_kind"] = source_kind

    codes = inst.app.registry.current.codes
    zh = lambda c: getattr(codes.get(c), "label_zh", c)  # noqa: E731
    with closing(open_startrack(inst.ctx)) as track, closing(open_startorch(inst.ctx)) as torch:
        # Keep legacy last-inserted selection and first-seen identity order.
        # Select references first; stream one current payload at a time rather
        # than decoding every historical version and retaining all payloads.
        latest = _current_formal_rows(torch)
        per_code = {}
        for oid, rev, raw, saved in latest:
            d = dict(json.loads(raw), _saved=saved)
            if d.get("status") != "ACTIVE":
                continue
            code, sk, ref = d["code"], d.get("source_kind") or "", d.get("source_ref") or ""
            src = node("src:" + sk, "source", SRC_ZH.get(sk, sk))
            ind = node("code:" + code, "indicator", zh(code))
            t = d.get("temporal") or {}
            when = t.get("observed_at") or t.get("observed_date") or ""
            pc = per_code.setdefault(code, {"count": 0, "corrected": 0, "last": None, "sources": set()})
            pc["sources"].add(sk)
            pc["count"] += 1
            pc["corrected"] += rev > 1
            if pc["last"] is None or when > pc["last"]["when"]:
                pc["last"] = {"when": when, "value": d.get("value_raw"), "unit": d.get("unit_raw") or ""}
            m = (re.match(r"(OCR):([0-9a-f]{16})#", ref) or re.match(r"(TABLE):([^#:]+)", ref)
                 or re.match(r"(FILE):([0-9a-f]{16})#", ref))
            if m:  # 化验单原件、表格批次单独成点：来源 → 原件 → 指标
                doc_id = "doc:" + m.group(1) + ":" + m.group(2)
                label = "化验单" if m.group(1) == "OCR" else "表格导入 " + _local_short(inst, d["_saved"])
                if m.group(1) == "OCR" and doc_id not in nodes:
                    try:
                        rec, _ = evidence_navigation._original_record(inst, m.group(2))
                        label = "化验单 " + (rec.get("name") or "")[:16]
                    except H1Error:
                        pass  # Missing/unsafe originals remain visible with an honest click-time explanation.
                doc = node(doc_id, "document", label.strip())
                edge(src, doc, "原件", "formal_observation.source_ref")
                edge(doc, ind, "记录了", "formal_observation.source_ref")
            else:
                edge(src, ind, "提供", "formal_observation.source_kind")
        for code, pc in per_code.items():
            nodes["code:" + code].update(count=pc["count"], corrected=pc["corrected"], last=pc["last"], sources=sorted(pc["sources"]))

        # 状态卡：每张卡用到的指标来自最新计算的 run_input；结论是最新时点的等级
        names = _card_names(track)
        for cid, in track.execute("SELECT DISTINCT c.card_id FROM run r JOIN card_def c USING (card_def_id)"):
            card = node("card:" + cid, "card", names.get(cid, cid))
            row = track.execute("SELECT t.tp_date, t.level, t.status, r.run_id FROM run_tp t JOIN run r USING (run_id) "
                                "JOIN card_def c ON c.card_def_id = r.card_def_id WHERE c.card_id = ? "
                                "ORDER BY t.tp_date DESC, r.run_id DESC LIMIT 1", (cid,)).fetchone()
            used = {}
            for (code,) in track.execute(
                    "SELECT DISTINCT o.code FROM run_input i JOIN run r USING (run_id) JOIN card_def c ON c.card_def_id = r.card_def_id "
                    "JOIN h1_inbox o ON o.observation_id = i.observation_id AND o.revision = i.revision WHERE c.card_id = ?", (cid,)):
                used[code] = 1
            for code in used:
                edge(node("code:" + code, "indicator", zh(code)), card, "用于计算", "run_input")
            if row:
                tp, level, status, rid = row
                con = node("con:" + cid, "conclusion", tp + " · " + LEVEL_ZH.get(level, level or "—"),
                           tp=tp, card=cid, level=level, run_id=rid)
                edge(card, con, "最新结论", "run_tp")
        if (snap.get("card_setup") or {}).get("cards") and "VITALS" in snap["card_setup"]["cards"]:
            vit = node("card:VITALS", "card", "我的体征")
            for it in [i for i in (snap.get("vitals") or {}).get("items") or [] if str(i.get("family", "")).startswith(("DEVICE_", "PHONE_"))]:
                edge(node("code:" + it["code"], "indicator", it.get("label_zh") or zh(it["code"])), vit, "显示读数", "vitals")
        # A view card exists independently of live readings and has no synthetic
        # calculation run. Keep its exact source+metric bindings on each edge.
        for definition in snap.get("vitals_cards") or []:
            cid = definition.get("card_id")
            if not cid:
                continue
            card = node("card:" + cid, "card", definition.get("name") or "我的体征",
                        card_id=cid, wall_id=definition.get("wall_id") or cid,
                        revision=definition.get("revision"), template="VITALS_VIEW",
                        items=[{"family": item.get("family"), "code": item.get("code")}
                               for item in definition.get("items") or []])
            for item in definition.get("items") or []:
                if not item.get("code") or not item.get("family"):
                    continue
                code, family = item["code"], item["family"]
                indicator = node("code:" + code, "indicator", item.get("label_zh") or zh(code))
                edge(indicator, card, "显示读数", "vitals", source_kind=family)
        for key, tp, lv, title, at, cid in track.execute(
                "SELECT dedupe_key, tp_date, level, title, created_at, card_id FROM alert_log ORDER BY created_at DESC LIMIT 12"):
            al = node("alert:" + key, "alert", "提醒 · " + tp + " " + LEVEL_ZH.get(lv, lv), tp=tp, card=cid, at=at, title=title)
            edge("card:" + cid if "card:" + cid in nodes else node("card:" + cid, "card", names.get(cid, cid)), al, "发出提醒", "alert_log")
            for ch, ok in track.execute("SELECT channel, max(outcome = 'SENT') FROM alert_delivery WHERE dedupe_key = ? GROUP BY channel", (key,)):
                edge(al, node("chan:" + ch, "channel", CHAN_ZH.get(ch, ch)), "已送达" if ok else "未送达", "alert_delivery")

    # 基因：原件 → 位点库（PTDS 不解读）
    for g in gene:
        f = node("gene:" + g["receipt_id"], "document", "基因文件 " + (g.get("file_name") or "")[:18])
        edge(node("src:GENE", "source", "基因测序数据"), f, "原件", "gene receipts")
        if g.get("db_now"):
            edge(f, node("store:gene", "store", "基因位点库"), "装入 %s 个位点" % g["db_now"].get("rows", "?"), "genotypes.db")

    # 授权：哪张卡（或位点库）经哪个授权给了谁；读取次数来自授权记录
    reads = {}
    for r in records or []:
        if r.get("action") in ("READ", "PUSH") and r.get("outcome") != "DENIED" and r.get("grant"):
            reads[(r["grant"], r["action"])] = reads.get((r["grant"], r["action"]), 0) + 1
    for g in grants or []:
        if g.get("example"):
            continue
        targets = {"*": [n for n in nodes if n.startswith("card:")], "GENE_LOCI": ["store:gene"],
                   "SJIA_FOCUS": ["card:sjia-mas"], "VITALS": ["card:VITALS"]}.get(g["card"], ["card:" + str(g["card"])])
        if g.get("preset") and not any(t in nodes for t in targets):
            if (g["id"], "READ") not in reads and (g["id"], "PUSH") not in reads:
                continue
        obj = objects.get(g["object"], {})
        party = node("party:" + g["object"], "party", obj.get("zh", g["object"]))
        gr = node("grant:" + g["id"], "grant", "授权 " + g["id"] + " · " + ("读取" if g["method"] == "read" else "推送"),
                  status=g["status"], card=g["card"])
        for t in targets:
            if t in nodes:
                edge(t, gr, "授权给出", "grant_def.card")
        edge(gr, party, "给", "grant_def.object")
        for act, rel in (("READ", "读取"), ("PUSH", "推送")):
            if reads.get((g["id"], act)):
                edge(gr, party, "%s %d 次" % (rel, reads[(g["id"], act)]), "access_record")
    kinds = {}
    for n in nodes.values():
        n["destination"] = evidence_navigation.destination(n)
        kinds[n["kind"]] = kinds.get(n["kind"], 0) + 1
    return {"nodes": sorted(nodes.values(), key=lambda n: (KIND_ORDER.index(n["kind"]), n["id"])),
            "edges": list(edges.values()), "kinds": kinds}
