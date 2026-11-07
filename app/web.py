"""把 UX v2.6 原型变成产品页：视图层原样保留，数据换成本机进程的实时快照，模拟层方法换成真实接口。

原型里所有页面读 DATA.snapshots[...]。首次页面只带实例身份与待加载标记：
1. 不生成、序列化所有实例的观测历史；前端选中实例后从已有 /api/state 读取完整快照；
2. 在原型闭包末尾挂钩，把 MockTorch 等对象交给 ptds_live.js 的本机接口适配层。
"""
from __future__ import annotations

import json
import re
import home_texts
from pathlib import Path

WEB = Path(__file__).resolve().parent / "web"
HOOK_AT = "window.__ptds = {"
HOOK = ("window.__ptds_core = { MockTorch: MockTorch, SNAPS: SNAPS, DATA: DATA, st: st, S: S, render: render, "
        "FULL: FULL, DICT: DICT, LV: LV, isLive: isLive, isReplay: isReplay, toast: toast, renderMainOnly: renderMainOnly, renderAppbar: renderAppbar, closeDrawer: closeDrawer, ic: ic, esc: esc, tzTime: tzTime, setSeg: setSeg, "
        "MockCluster: MockCluster, MockBridge: MockBridge, PKEY: PKEY, renderApple: renderApple, levelSvg: levelSvg, pgh: pgh, mtag: mtag, openTorchDetail: openTorchDetail, goTrack: goTrack, goTorch: goTorch, torchRows: torchRows, recentSources: recentSources, graphEvents: graphEvents, ago: ago, srcText: srcText, "
        "PROD: PROD, newEntry: newEntry, stepsHtml: stepsHtml, modeSwitch: modeSwitch, instId: instId, setKeys: function (k) { KEYS = k; } };\n"
        "if (window.PTDS_LIVE) window.PTDS_LIVE.install(window.__ptds_core);\n")
ENTRY_FAMILIES = ("LAB", "VITAL", "FLAG")



# 产品负责人 2026-10-15 r59：导航改名、星簇导航收拢。只在送出页面时改内存里的副本，product_config.json 不动
NAV_RENAME = {"星炬导航": "数据导航", "状态轨迹": "我的状态"}  # r60（产品负责人 2026-10-15 10:39）：状态追踪 → 我的状态


def nav_r59(product: dict) -> dict:
    p = json.loads(json.dumps(product, ensure_ascii=False))
    for m in p["modules"]:
        for n in m["nav"]:
            n["zh"] = NAV_RENAME.get(n["zh"], n["zh"])
        if m["id"] == "torch":                       # r62：证据图谱升为一级「星痕」（侧栏单独一项，页面还是原来的 torch/graph）
            m["nav"] = [n for n in m["nav"] if n["id"] != "graph"]
        if m["id"] == "track":                       # r60：状态工程不再占导航，从「我的状态」页右上角的「增加我的状态」进
            m["nav"] = [n for n in m["nav"] if n["id"] != "eng"]
        if m["id"] == "cluster":                     # 授权协作放第一个、去掉“规划中”；授权总览、授权记录并进我的授权，入口去掉
            space = [dict(n, zh="授权协作", maturity="ready") for n in m["nav"] if n["id"] == "space"]
            m["nav"] = space + [n for n in m["nav"] if n["id"] not in ("space", "overview", "records")]
    order = {"track": 0, "torch": 1, "cluster": 2}  # r64（产品负责人 2026-10-15 13:49）：星轨放第一，患者一进来先看到「我的状态」
    p["modules"].sort(key=lambda m: order.get(m["id"], 9))
    sp = p.get("onepagers", {}).get("space")
    if isinstance(sp, dict) and isinstance(sp.get("relation"), str):
        sp["relation"] = sp["relation"].replace("星簇协作", "授权协作")
    return p

def pending_snapshot(inst, setup: dict) -> dict:
    """Navigation metadata, explicitly not an empty authoritative snapshot.

    No observation, rule, history or authorization store is read here. The UI
    must resolve ``_pending`` through the existing per-instance state endpoint
    before rendering data or allowing data-dependent actions.
    """
    return {
        "_pending": True,
        "instance": {
            "instance_id": inst.ctx.instance_id, "kind": inst.ctx.kind,
            "display_name": inst.ctx.display_name, "tz": inst.ctx.tz,
            "replay": inst.spec.get("replay", False), "accept": list(inst.ctx.accept),
            "default_nature": inst.nature, "cards": list(setup["cards"]),
        },
        "disclaimer": "关注信号，不构成诊断或治疗建议",
        "card": None, "h1": {}, "timeline": [], "unknown_time": [],
        "timepoints": [], "current": None, "stale_count": 0,
        "level_history": [], "alerts": [], "banner": None,
        "known_sources": [], "vitals": {"items": []}, "band_cards": [],
        "card_setup": setup, "device_events": [], "torch": {}, "runs": [],
        "runs_by_tp": {}, "card_thresholds": {},
        "wall_prefs": {"pins": [], "hidden": []},
        "custom_cards": [], "sleep": None, "bioage": None,
        "series": {}, "engines": None, "notice": None,
    }


def page(app) -> bytes:
    html = (WEB / "product.html").read_text("utf-8")
    m = re.search(r'(<script id="data" type="application/json">)(.*?)(</script>)', html, re.S)
    data = json.loads(m.group(2))
    # BOOTSTRAP_LAZY_R06: retain the same instance identities and card setup,
    # but never build all histories just to display the application entrance.
    setups = {key: inst.setup().state() for key, inst in app.instances.items()}
    snaps = {key: pending_snapshot(inst, setups[key]) for key, inst in app.instances.items()}
    data["snapshots"] = snaps
    d = app.dict_json()["full"]
    labels, full = {}, {}
    for code, c in d.items():
        labels[code] = {"zh": c["zh"], "src": "字典 " + app.registry.current.version}
        if c["family"] in ENTRY_FAMILIES:
            full[code] = c
    # E1：实例启用哪些卡来自本机配置（回放实例保留原型的"在状态工程里新建"流程）
    for key, inst in app.instances.items():
        if not inst.spec.get("replay"):
            data["product"]["instance_cards"][inst.ctx.instance_id] = setups[key]["cards"]
    # 产品配置（成熟度标签、卡片事件含 Δ2"设备断开"……）以本机 product_config.json 为准：产品负责人改配置即生效
    data["product"] = nav_r59(dict(app.product_config, instance_cards=data["product"]["instance_cards"]))
    data["dict"] = {"_note": "实时字典（本机进程）", "labels": labels, "full": full}
    # Preserve the real identity and pending marker before the prototype installs
    # its unbound placeholders. No medical observations are embedded here.
    data["ptds_live"] = {"keys": list(app.trial.instances(app)), "lazy": True, "dict_version": app.registry.current.version,
                         "compute_queue_version": getattr(app, "compute_queue_version", 0), "write_receipt_version": getattr(app, "write_receipt_version", 0), "data_read_version": getattr(app, "data_read_version", 0), "home_read_version": getattr(app, "home_read_version", 0), "graph_read_version": getattr(app, "graph_read_version", 0),
                         "home": home_texts.view(app.root, list(snaps)),
                         "snapshot_keys": [k for k, snap in snaps.items() if not snap['instance']['replay']] }
    # The standalone prototype supplies demonstration slots. The running product
    # gets its clickable keys exclusively from the initialized instance registry.
    launch_cards = "card(liveKey) + (SNAPS.UNBOUND_OTHER ? card('UNBOUND_OTHER') : '')"
    assert html.count(launch_cards) == 1
    html = html.replace(launch_cards,
        "DATA.ptds_live.keys.filter(function(k) { "
        "return k === " + json.dumps(app.trial.target) + "; }).map(card).join('')")
    data["ptds_live"]["capabilities"] = app.trial.ui_capabilities(); blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    html = html[:m.start(2)] + blob + html[m.end(2):]
    anchor = "var SNAPS = DATA.snapshots, KEYS = Object.keys(SNAPS), DICT = DATA.dict.labels, ERRT = DATA.err;"
    assert html.count(anchor) == 1, "BOOTSTRAP_SNAPSHOT_ANCHOR_CHANGED"
    html = html.replace(anchor, anchor + "\n" +
        "if (DATA.ptds_live) { window.PTDS_TRIAL_UI.install(document, DATA.ptds_live.capabilities); DATA.ptds_live.snapshots = {}; "
        "(DATA.ptds_live.snapshot_keys || []).forEach(function (k) { "
        "DATA.ptds_live.snapshots[k] = SNAPS[k]; }); }", 1)
    # The registry owns product snapshots. Standalone HTML keeps its prototype slots.
    html, removed = re.subn(r"^SNAPS\.UNBOUND_(?:REAL|REPLAY) = liveSnap\(.*?\);$", "", html, flags=re.M)
    assert removed == 2
    initial = "if (!SNAPS[st.key]) st.key = 'UNBOUND_REAL';"
    assert html.count(initial) == 1
    html = html.replace(initial, "st.key = " + json.dumps(app.trial.target) + ";")
    entry = "var i = SNAPS[k].instance; if (!i.replay) return PTDS_LIVE.launchCard(k, SNAPS[k]);"
    assert html.count(entry) == 1
    html = html.replace(entry,
        "var i = SNAPS[k].instance, real = i.kind === 'REAL'; "
        "if (!i.replay && DATA.ptds_live.home.cards[k]) return PTDS_LIVE.launchCard(k, SNAPS[k]); "
        """if (!i.replay) return '<div class="icard"><div class="nm">' + esc(i.display_name) +
        '</div><button class="chip" data-launch="' + esc(k) + '">' + ic('external-link') + '打开</button></div>';""")
    launch_disc = "document.getElementById('disc').textContent = S().disclaimer;"
    html = html.replace(launch_disc,
        "document.getElementById('disc').textContent = st.key ? S().disclaimer : '';")
    assert html.count(HOOK_AT) == 1
    shim = (WEB / "body_front.js").read_text("utf-8") + "\n" + (WEB / "ptds_live.js").read_text("utf-8")  # 人体轮廓（整体基线洞察）先装
    # 钩子要在闭包里才能拿到 MockTorch 等变量；shim 先于原型脚本定义 window.PTDS_LIVE
    html = html.replace(HOOK_AT, HOOK + HOOK_AT, 1)
    shim = (WEB / "trial_ui.js").read_text("utf-8") + "\n" + (WEB / "home_layout.js").read_text("utf-8") + "\n" + (WEB / "partner_language_catalog.js").read_text("utf-8") + "\n" + (WEB / "language_resources.js").read_text("utf-8") + "\n" + (WEB / "language_pages.js").read_text("utf-8") + "\n" + (WEB / "language_start.js").read_text("utf-8") + "\n" + (WEB / "language_switch.js").read_text("utf-8") + "\n" + (WEB / "data_read_session.js").read_text("utf-8") + "\n" + shim
    shim = (WEB / "compute_status.js").read_text("utf-8") + "\n" + (WEB / "state_push.js").read_text("utf-8") + "\n" + shim
    html = html.replace("</head>", "<style>" + (WEB / "state_push.css").read_text("utf-8") + "\n" + (WEB / "home_layout.css").read_text("utf-8") + "\n" + (WEB / "language_start.css").read_text("utf-8") + "</style></head>", 1)
    first_script = html.index("<script>")
    html = html[:first_script] + "<script>" + shim + "</script>\n" + html[first_script:]
    return html.encode("utf-8")
