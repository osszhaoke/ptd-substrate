"""Minimal local UI for 星轨 (reference). Stdlib http.server, bound to 127.0.0.1 only.

    python3 startrack_server.py --instance ~/PTDS-instances/synthetic-example [--port 8765] [--auto-sync 10] [--macos]

GET  /                 one page that renders /api/state (it never computes anything itself)
GET  /api/state        card_state() as JSON
POST /api/sync         import H1 files + evaluate new time points
POST /api/recompute    re-evaluate STALE time points
POST /api/sensitivity  {"value": "LOW" | "MEDIUM" | "HIGH"}
POST /api/ack          {"dedupe_key": "..."}

POSTs must carry the header "X-PTDS: 1" (a web page on another origin cannot add it without CORS).
One lock serializes the auto-sync thread and the request handlers; each operation opens its own
connection. Never point an AI coding session at a REAL instance.
"""
from __future__ import annotations

import argparse
import json
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

from cards import (BannerNotifier, MacOSNotifier, ack_alert, card_state, current_sensitivity, load_card,
                   open_startrack, recompute, set_sensitivity, sync)
from h1_common import DictionaryRegistry, H1Error, load_dictionary, load_instance

REF = Path(__file__).resolve().parent

PAGE = """<!doctype html><html lang="zh"><meta charset="utf-8"><title>星轨 · sJIA 状态卡</title>
<style>body{font:14px/1.5 -apple-system,system-ui,sans-serif;margin:16px;max-width:980px}
table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ddd;padding:4px 6px;text-align:left}
.banner{background:#fff3cd;padding:8px;margin:8px 0}.muted{color:#666}button{margin-right:6px}</style>
<h2 id="inst"></h2><p class="muted" id="disc"></p><div id="banner"></div>
<p><button onclick="post('/api/sync')">同步</button><button onclick="post('/api/recompute')">重算</button>
灵敏度 <select id="sens" onchange="post('/api/sensitivity',{value:this.value})">
<option>LOW</option><option>MEDIUM</option><option>HIGH</option></select></p>
<p id="cur"></p><p class="muted" id="h1"></p>
<table><thead><tr><th>时点</th><th>状态</th><th>综合</th><th>R1</th><th>R2</th><th>MS</th><th>动态</th></tr></thead>
<tbody id="tps"></tbody></table>
<script>
const el=(t,txt)=>{const e=document.createElement(t);e.textContent=txt??'';return e};
async function post(u,b){await fetch(u,{method:'POST',headers:{'X-PTDS':'1','Content-Type':'application/json'},
 body:JSON.stringify(b||{})});load()}
async function load(){const s=await (await fetch('/api/state')).json();
 document.getElementById('inst').textContent=s.instance.display_name+' ['+s.instance.kind+']';
 document.getElementById('disc').textContent=s.disclaimer+' · 规则包 '+s.card.rulepack_version+
  ' · 动态配置 '+s.card.dynamic_version+'（'+s.card.dynamic_provenance+'）';
 document.getElementById('sens').value=s.card.sensitivity;
 const b=document.getElementById('banner');b.replaceChildren();
 if(s.banner){const d=el('div',s.banner.body);d.className='banner';const k=el('button','知道了');
  k.onclick=()=>post('/api/ack',{dedupe_key:s.banner.dedupe_key});d.append(' ',k);b.append(d)}
 document.getElementById('cur').textContent=s.current?('当前 '+s.current.tp+'：'+s.current.level_zh+
  (s.current.stale?'（来源已更新，请重算）':'')):'暂无时点';
 const h=s.h1;document.getElementById('h1').textContent='H1 已导入到提交 '+h.cursor_commit+
  (h.outdated?'；有 '+h.pending_commits+' 个提交未导入，结果可能不是最新':'')+
  (h.last_sync&&h.last_sync.error?'；同步错误 '+h.last_sync.error.code:'');
 const tb=document.getElementById('tps');tb.replaceChildren();
 for(const t of s.timepoints){const r=t.result||{};const R=r.rules||{};const tr=document.createElement('tr');
  tr.append(el('td',t.tp),el('td',t.status),el('td',t.level_zh),el('td',R.R1&&R.R1.result),
   el('td',R.R2&&R.R2.result),el('td',R.R3&&(R.R3.score??R.R3.result)),el('td',r.dynamic&&r.dynamic.level));tb.append(tr)}}
load();setInterval(load,5000);
</script></html>"""


class App:
    def __init__(self, instance_root: Path, notifiers: list):
        self.ctx = load_instance(instance_root)
        self.registry = DictionaryRegistry([load_dictionary(REF / "h1-dictionary-0.1.json")])
        self.rulepack = json.loads((REF / "sjia-rulepack-0.1.json").read_text("utf-8"))
        self.dynamic = json.loads((REF / "dynamic-config-0.1.json").read_text("utf-8"))
        self.notifiers = notifiers
        self.lock = threading.Lock()
        self.last_sync = None

    def now(self) -> str:
        return datetime.now(ZoneInfo(self.ctx.tz)).isoformat(timespec="seconds")

    def run(self, action):
        with self.lock:
            conn = open_startrack(self.ctx)
            try:
                sensitivity = current_sensitivity(conn, "sjia-mas", self.dynamic["default_sensitivity"])
                card = load_card(self.registry, self.ctx, self.rulepack, self.dynamic, sensitivity)
                return action(conn, card)
            finally:
                conn.close()

    def sync(self):
        def act(conn, card):
            result = sync(conn, self.ctx, self.registry, card, now=self.now(), notifiers=self.notifiers)
            imported = result["import"]
            self.last_sync = {"at": self.now(), "inserted": imported.inserted,
                              "pending_commits": imported.pending_commits, "error": imported.error}
            return {"evaluated": result["evaluated"], "stale": result["stale"]}
        return self.run(act)


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, kind: str = "application/json; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, obj):
            self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"))

        def do_GET(self):
            if self.path == "/":
                return self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            if self.path == "/api/state":
                return self._json(200, app.run(lambda conn, card: card_state(conn, app.ctx, card, app.last_sync)))
            return self._json(404, {"error": "NOT_FOUND"})

        def do_POST(self):
            if self.headers.get("X-PTDS") != "1":
                return self._json(403, {"error": "MISSING_X_PTDS_HEADER"})
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}") if length else {}
            try:
                if self.path == "/api/sync":
                    return self._json(200, app.sync())
                if self.path == "/api/recompute":
                    return self._json(200, app.run(lambda conn, card: {"evaluated": recompute(
                        conn, app.ctx, card, now=app.now(), notifiers=app.notifiers)["evaluated"]}))
                if self.path == "/api/sensitivity":
                    app.run(lambda conn, card: set_sensitivity(conn, card.card_id, body.get("value"), set_at=app.now()))
                    return self._json(200, app.sync())  # a new definition is evaluated right away
                if self.path == "/api/ack":
                    app.run(lambda conn, card: ack_alert(conn, str(body.get("dedupe_key")), acked_at=app.now()))
                    return self._json(200, {"ok": True})
            except H1Error as exc:
                return self._json(400, {"error": exc.code, "detail": exc.detail})
            return self._json(404, {"error": "NOT_FOUND"})

        def log_message(self, fmt, *args):  # no request logging: URLs and bodies stay out of logs
            return None
    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--auto-sync", type=int, default=10, help="seconds; 0 disables")
    parser.add_argument("--macos", action="store_true", help="also send macOS notifications")
    args = parser.parse_args()
    notifiers = [BannerNotifier()] + ([MacOSNotifier()] if args.macos else [])
    app = App(args.instance.expanduser(), notifiers)
    app.sync()
    if args.auto_sync:
        def loop():
            while True:
                threading.Event().wait(args.auto_sync)
                try:
                    app.sync()
                except Exception as exc:  # noqa: BLE001 - keep the loop alive; the error is in h1_sync_error
                    app.last_sync = {"at": app.now(), "error": {"code": type(exc).__name__}}
        threading.Thread(target=loop, daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(app))
    print(f"星轨 UI: http://127.0.0.1:{args.port}/  instance={app.ctx.instance_id} ({app.ctx.kind})")
    server.serve_forever()


if __name__ == "__main__":
    main()
