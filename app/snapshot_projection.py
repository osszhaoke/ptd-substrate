"""State projection extracted from Instance.snapshot; supplied read scope only."""
import json
from cards import card_state
from startorch_outbox import export_status
from startrack_import import h1_status
from vitals import vitals_state
import band_cards, card_thresholds, custom_cards, sleep_card, bioage, engines
import vitals_cards, rule_notice, evidence_graph, starling_page
from read_bundle import Snapshot


def project(self, bundle, *, home, read, observation_factory, observations, offset):
    track, torch = bundle.track, bundle.torch
    read_version = bundle.metadata[2][0]
    read = read if read is not None else observation_factory(track, self.ctx.tz)
    from display_retention import display_read
    read = display_read(read, self.spec.get("archived_streams"))
    if self.sjia:
        snap = card_state(track, self.ctx, self.card(track), self.last_sync, read=read, history=not home)
    else:
        snap = {"instance": {}, "disclaimer": "关注信号，不构成诊断或治疗建议", "card": None,
                "h1": dict(h1_status(track, self.ctx), last_sync=self.last_sync),
                "timeline": [] if home else observations(track, self.ctx, self.app.registry, read=read),
                "unknown_time": [], "timepoints": [], "current": None, "stale_count": 0,
                "level_history": [], "alerts": [], "banner": None}
    snap["instance"] = {"instance_id": self.ctx.instance_id, "kind": self.ctx.kind,
                        "display_name": self.ctx.display_name, "tz": self.ctx.tz,
                        "replay": self.spec.get("replay", False), "accept": list(self.ctx.accept),
                        "default_nature": self.nature,
                        "cards": self.spec["cards"]}
    setup = bundle.setup
    snap["instance"]["cards"] = setup["cards"]
    snap["vitals_all"] = vitals_state(track, self.ctx, self.app.registry, read=read)
    vit, known = self.vitals_view(track, setup, read=read, vit=snap["vitals_all"])
    snap["known_sources"] = known
    snap["vitals"] = vit
    # 体验腕带的三张卡（产品负责人 10:51）：只有存了 Somaloop 读数的实例才有（个人基座没有，返回空）
    snap["band_cards"] = band_cards.build(track, self.ctx, since=None, read=read)
    snap["card_setup"] = setup
    snap["vitals_catalogue"] = vitals_cards.catalogue(snap)
    snap["device_events"] = bundle.events.rows()[-20:]
    snap["torch"] = export_status(torch)
    snap["torch"]["formal_rows"] = torch.execute("SELECT count(*) FROM formal_observation").fetchone()[0]
    snap["runs"] = [dict(zip(("run_id", "trigger", "started_at"), r)) for r in track.execute(
        "SELECT r.run_id, r.trigger, r.started_at FROM run r JOIN card_def c USING (card_def_id) "
        "WHERE c.card_id = 'sjia-mas' ORDER BY r.run_id DESC LIMIT 50")] if self.sjia and not home else []
    # A3：每个时点的历次计算（星轨 run_tp 原样取出，最近 3 次），界面拿来做新旧并排，不再拼接
    by_tp = {}
    if self.sjia and not home:
        for rid, trig, at, tp, status, level, result in track.execute(
                "SELECT r.run_id, r.trigger, r.started_at, t.tp_date, t.status, t.level, t.result "
                "FROM run_tp t JOIN run r USING (run_id) JOIN card_def c ON c.card_def_id = r.card_def_id "
                "WHERE c.card_id = 'sjia-mas' ORDER BY t.tp_date, r.run_id"):
            by_tp.setdefault(tp, []).append({"run_id": rid, "trigger": trig, "started_at": at, "status": status,
                                             "level": level, "result": json.loads(result)})
    snap["runs_by_tp"] = {tp: runs[-3:] for tp, runs in by_tp.items()}
    snap["card_thresholds"] = card_thresholds.configs(track)
    existing_alerts = {a["dedupe_key"] for a in snap.get("alerts", [])}
    snap["alerts"].extend(a for a in card_thresholds.alerts(track) if a["dedupe_key"] not in existing_alerts)
    owner = dict(track.execute("SELECT dedupe_key, card_id FROM alert_log"))
    # 我的状态墙：钉到「我的关注」、从轨迹隐藏（产品负责人 2026-10-15）。card_setting 只追加，每张卡取最新一条
    snap["wall_prefs"] = self.wall_preferences(track)
    # 从历史列表隐藏（产品负责人 2026-10-15）：card_setting 里追加 alert_hidden 一行，提醒原记录不动
    hidden = {v for (v,) in track.execute("SELECT value FROM card_setting WHERE key = 'alert_hidden'")}
    snap["alerts"] = [a for a in snap.get("alerts") or [] if a["dedupe_key"] not in hidden]
    if snap.get("banner") and snap["banner"].get("dedupe_key") in hidden:
        snap["banner"] = None
    for a in snap.get("alerts") or []:
        a["card_id"] = owner.get(a["dedupe_key"])
    if snap.get("banner") and owner.get(snap["banner"]["dedupe_key"]) != "sjia-mas":  # 横幅只放关注卡的（点开去它的时点）
        snap["banner"] = next((a for a in reversed(snap["alerts"]) if not a["acked"] and a["card_id"] == "sjia-mas"), None)
    if self.spec.get("replay"):
        snap["custom_cards"], snap["sleep"], snap["bioage"], snap["series"], snap["engines"] = [], None, None, {}, None
    else:  # 自定义状态卡、睡眠卡：同一次读星轨（按代码、时点分好组）
        groups = custom_cards.by_code(track, self.ctx, read=read)
        snap["custom_cards"] = custom_cards.state(track, self.ctx, groups=groups)
        snap["sleep"] = sleep_card.state(groups, self.app.registry, setup["vitals_sources"])
        snap["bioage"] = bioage.state(groups, self.ctx.root, profile=bundle.profile)
        snap["engines"] = engines.state(track, self.ctx.root, groups, sjia=False, profile=bundle.profile)
        # 卡片缩略图：每个数值代码按天取当天最新一条，最近 30 天
        snap["series"] = {code: [{"tp": d, "v": format(max(days[d], key=lambda o: (o.instant.isoformat() if o.instant else "", o.observation_id)).value, "f")}
                                 for d in sorted(days)[-30:]] for code, days in groups.items()}
    # 规则触发，星灵转告（产品负责人 2026-10-14）：最新一条没读过的观察 / 关注提醒
    snap["notice"] = rule_notice.notice(snap, evidence_graph.hidden_cards(self), bool(self.spec.get("replay")))
    if snap["notice"]:
        snap["notice"]["sign"] = starling_page.sign(self.app.llm) if getattr(self.app, "llm", None) else "星灵"
    snap["vitals_cards"] = vitals_cards.state(track, snap)
    snap["offset_refs"] = offset(self, read, snap.get("timepoints") or [])
    if home:
        # Explicitly scoped view, never accepted by history/detail readers.
        for field in ("timeline", "unknown_time", "level_history", "runs", "runs_by_tp"):
            snap.pop(field, None)
        snap["timepoints"] = snap.get("timepoints", [])[-1:]
        for card in snap["custom_cards"]:
            for field in ("timepoints", "runs", "versions", "alerts"):
                card.pop(field, None)
        for group in (snap.get("engines") or {}).get("groups", []):
            for card in group["cards"]:
                card.pop("runs", None)
        for card in (snap.get("bioage") or {}).get("cards", []):
            card["series"] = card.get("series", [])[-60:]
    if not home:
        snap["_read_version"] = read_version
    return Snapshot(snap).bind(bundle)
