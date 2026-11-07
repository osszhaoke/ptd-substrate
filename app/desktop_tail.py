"""Local-only wearable panels. No acquisition, identity switching or data writes.

The page supplies its existing four display choices; the panel independently reads
the same local projection after the browser is closed. AppKit owns window level.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

SOURCE = Path(__file__).with_name("desktop_tail") / "WearablePanel.swift"
COMPONENT = Path(__file__).with_name("web") / "ptds_live.js"
TEMPLATE = SOURCE.with_name("panel.html")
PRODUCT = COMPONENT.with_name("product.html")


def component_js():
    source = COMPONENT.read_text()
    return source.split("// PTDS_TAIL_COMPONENT_BEGIN\n", 1)[1].split("\n// PTDS_TAIL_COMPONENT_END", 1)[0]


def panel_html():
    # Reuse the product's bundled fonts; never fetch remote fonts or load the whole app.
    fonts = "\n".join(re.findall(r"@font-face\s*\{[^}]*\}", PRODUCT.read_text()))
    return TEMPLATE.read_text().replace("/*FONTS*/", fonts).replace("/*COMPONENT*/", component_js())


class PanelError(ValueError):
    pass


def build(root: Path) -> Path:
    if sys.platform != "darwin":
        raise PanelError("跨应用置顶目前需要在运行 PTDS 的 Mac 上使用")
    html = panel_html()
    digest = hashlib.sha256(SOURCE.read_bytes() + html.encode()).hexdigest()[:20]
    bundle = root / "desktop-tail" / digest / "PTDSWearablePanel.app"
    executable = bundle / "Contents/MacOS/PTDSWearablePanel"
    if not executable.exists():
        executable.parent.mkdir(parents=True, exist_ok=True)
        temporary = executable.with_suffix(".building")
        try:
            subprocess.run(["/usr/bin/xcrun", "swiftc", str(SOURCE), "-o", str(temporary),
                            "-framework", "AppKit", "-framework", "WebKit"], capture_output=True, check=True, timeout=90)
        except (OSError, subprocess.SubprocessError) as exc:
            raise PanelError("置顶小窗尚未构建成功；请检查本机 Swift 编译工具") from exc
        (bundle / "Contents/Info.plist").write_bytes(plistlib.dumps({
            "CFBundleIdentifier": "local.ptds.wearablepanel", "CFBundleName": "PTDS Wearable Panel",
            "CFBundleDisplayName": "PTDS 近期读数", "CFBundleExecutable": "PTDSWearablePanel",
            "CFBundlePackageType": "APPL", "LSUIElement": True, "NSHighResolutionCapable": True,
        }))
        resources = bundle / "Contents/Resources"
        resources.mkdir(exist_ok=True)
        (resources / "panel.html").write_text(html)
        os.replace(temporary, executable)
    return executable


class Panels:
    def __init__(self, app):
        self.app = app
        self.lock = threading.Lock()
        self.sessions = {}

    def validate(self, body):
        instance_key, device = body.get("key"), body.get("device")
        if instance_key not in self.app.instances or not isinstance(device, str) or not re.fullmatch(r"[a-z0-9_-]{1,32}", device):
            raise PanelError("请选择已有实例及可穿戴设备")
        pillbox = device == "pillbox"
        if pillbox and getattr(self.app.instances[instance_key], "spec", {}).get("replay"):
            raise PanelError("回放基座不能连接药盒")
        tiles = [] if pillbox else body.get("tiles")
        if not isinstance(tiles, list) or (not pillbox and len(tiles) != 4):
            raise PanelError("小尾巴需要四个已有指标")
        choices = []
        for tile in tiles:
            if not isinstance(tile, dict) or tile.get("code") not in self.app.dict_json()["full"]:
                raise PanelError("指标不在当前字典中")
            if tile.get("when", "instant") not in ("instant", "today", "night", "dayavg"):
                raise PanelError("读数时间类型不支持")
            choices.append({k: str(tile.get(k, ""))[:80] for k in ("code", "label", "unit", "when")})
        source = body.get("source")
        if pillbox:
            source = "LOCAL_PILLBOX"
        elif device == "somaloop":
            import guest_band
            if [x["code"] for x in choices] != [guest_band.CODES[k] for k in guest_band.TAIL]:
                raise PanelError("Somaloop 指标选择不匹配")
            source = "DEVICE_SOMALOOP"
        elif not isinstance(source, str) or not source.startswith("DEVICE_"):
            raise PanelError("仅支持已有可穿戴设备来源")
        given = body.get("visual") or {}
        if not isinstance(given, dict):
            raise PanelError("窗体规格需要一个对象")
        dark = body.get("theme") != "light"
        visual = {"width": 300, "font": '"Source Sans 3", "Noto Sans SC", sans-serif', "size": "15px", "line": "1.6", "tokens": {
            "--theme-surface-raised": "#111a36" if dark else "#fbfaf6",
            "--theme-text-primary": "#e8e8e0" if dark else "#293029",
            "--theme-text-secondary": "#a9b2c8" if dark else "#687066",
            "--theme-text-tertiary": "#8f9db6" if dark else "#687066",
            "--scale-type-meta": "14px", "--primitive-border-hairline": "1px"}}
        width = given.get("width", 300)
        if not isinstance(width, (int, float)) or not 200 <= width <= 600:
            raise PanelError("窗体宽度超出允许范围")
        visual["width"] = width
        height = given.get("height")
        if height is not None:
            if not isinstance(height, (int, float)) or not 100 <= height <= 900:
                raise PanelError("窗体高度超出允许范围")
            visual["height"] = height
        ratio = given.get("pixelRatio", 2)
        if not isinstance(ratio, (int, float)) or not .25 <= ratio <= 8:
            raise PanelError("窗体缩放规格无效")
        visual["pixelRatio"] = ratio
        for key in ("font", "size", "line"):
            value = str(given.get(key, visual[key]))
            if not re.fullmatch(r"[\w\s.,\-\"']{1,200}", value):
                raise PanelError("窗体文字规格无效")
            visual[key] = value
        tokens = given.get("tokens") or {}
        if not isinstance(tokens, dict):
            raise PanelError("窗体颜色规格无效")
        for key in visual["tokens"]:
            if key in tokens:
                value = str(tokens[key])
                if not re.fullmatch(r"[a-zA-Z0-9#.,%()\s-]{1,100}", value) or "url" in value.lower() or "var" in value.lower():
                    raise PanelError("窗体颜色规格无效")
                visual["tokens"][key] = value
        return {"key": instance_key, "device": device, "name": str(body.get("name") or device)[:40],
                "source": source, "tiles": choices, "visual": visual, "footer": str(body.get("footer") or "最近读数 · 本机展示")[:200], "theme": "light" if body.get("theme") == "light" else "dark"}

    def open(self, body, port):
        spec = self.validate(body)
        with self.lock:
            # One live window for each instance/device. Repeat clicks do not spawn duplicates.
            for token, entry in list(self.sessions.items()):
                if entry["process"].poll() is not None:
                    del self.sessions[token]
                elif (entry["spec"]["key"], entry["spec"]["device"]) == (spec["key"], spec["device"]):
                    entry["spec"] = spec
                    entry["pin_revision"] += 1
                    return {"ok": True, "existing": True}
            executable = build(self.app.root)
            token = uuid.uuid4().hex
            url = f"http://127.0.0.1:{int(port)}/api/desktop-tail/data?panel={token}"
            log = executable.parents[3] / ("window-" + token + ".log")
            with log.open("wb") as output:
                process = subprocess.Popen([str(executable), url, spec["theme"]], stdout=output, stderr=output)
            self.sessions[token] = {"spec": spec, "process": process, "pin_revision": 1}
        # Release the session lock before waiting: the window requests its first
        # payload before it can measure and show the shared component.
        for _ in range(60):
            if process.poll() is not None:
                with self.lock:
                    self.sessions.pop(token, None)
                raise PanelError("原生读数窗口未启动，请检查本机窗口日志")
            if b"PTDS_PANEL_READY" in log.read_bytes():
                return {"ok": True, "existing": False}
            time.sleep(.1)
        process.terminate()
        with self.lock:
            self.sessions.pop(token, None)
        raise PanelError("原生读数窗口启动超时")

    def data(self, token):
        with self.lock:
            entry = self.sessions.get(token)
            if not entry or entry["process"].poll() is not None:
                raise PanelError("置顶窗口已关闭")
            spec = dict(entry["spec"])
            revision = entry["pin_revision"]
        result = dict(self.readings(spec), pin_revision=revision)
        if spec["device"] == "somaloop":
            state = self.app.phone_tail.status()
            result["sharing"] = {k: state.get(k) for k in ("running", "approved_count", "pending_count")}
            result["sharing"]["grant"] = {"status": (state.get("grant") or {}).get("status")}
        return result

    def find(self, token):
        with self.lock:
            entry = self.sessions.get(token)
            if not entry or entry["process"].poll() is not None or entry["spec"]["device"] != "pillbox":
                raise PanelError("药盒窗口已关闭或不匹配")
            key = entry["spec"]["key"]
        return self.app.pillbox.find(key)

    def readings(self, spec, *, band_view=None):
        inst = self.app.instances[spec["key"]]
        if spec["device"] == "pillbox":
            return dict(self.app.pillbox.status(spec["key"]), visual=spec["visual"], theme=spec["theme"], tiles=[])
        tz = ZoneInfo(inst.ctx.tz)
        now = datetime.now(tz)
        tiles = []
        if spec["device"] == "somaloop":
            view = self.app.band().tail_snapshot() if band_view is None else band_view
            state = view["status"]
            status = "已连接" if state.get("alive") and state.get("connection") == "ready" else "未连接"
            for choice, row in zip(spec["tiles"], view["tiles"]):
                latest = row["latest"]
                stamp = datetime.fromtimestamp(latest["at"], tz) if latest else None
                value = (f'{latest["value"]:.1f}' if row["kind"] == "SKIN_TEMP" else str(round(latest["value"]))) if latest else "—"
                tiles.append({"label": choice["label"], "value": value, "kind": row["kind"], "raw": latest["value"] if latest else None, "unit": choice["unit"],
                              "note": stamp.strftime("%H:%M") + " 的读数" if stamp else "等待最近读数" if state.get("data_policy") == "daily" else "还没有数据",
                              "old": bool(latest and time.time() - latest["at"] > 600)})
        else:
            # Latest cache is presentation only: never promote it into formal vitals/history.
            snapshot = inst.refresh_snapshot()
            items = snapshot.get("vitals", {}).get("items", [])
            latest_by_code = (snapshot.get("device_latest") or {}).get(spec["source"], {})
            daily = (snapshot.get("device_policy") or {}).get("mode") == "daily"
            status = "已有设备读数 · 自动更新"
            for choice in spec["tiles"]:
                cached = latest_by_code.get(choice["code"])
                cached = cached if isinstance(cached, dict) and cached.get("code") == choice["code"] and cached.get("value_raw") is not None and cached.get("observed_at") else None
                item = cached or next((o for o in items if o.get("code") == choice["code"] and
                    (o.get("family") or o.get("source_kind")) == spec["source"] and
                    (not daily or (not o.get("observed_at") and o.get("observed_date")))), None)
                raw = item.get("value_raw") if item else None
                stamp = item.get("observed_at") if item else None
                day = item.get("observed_date") if item else None
                at = datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(tz) if stamp else None
                day = day or (at.date().isoformat() if at else None)
                note = (at.strftime("%m-%d %H:%M") + " 的读数") if at else (day + " 的日汇总" if day else "等待最近读数" if daily else "还没有数据")
                value = str(raw) if raw is not None else "—"
                if not cached and raw is not None and choice["unit"] in ("千卡", "步"):
                    value = str(int(float(raw) + .5))
                unit = (cached.get("unit_raw") or "") if cached else choice["unit"]
                tiles.append({"label": choice["label"], "value": value, "unit": unit, "note": note,
                              "old": bool(day and day != now.date().isoformat() and choice["when"] != "night")})
            if daily and not any(tile["value"] != "—" for tile in tiles):
                status = "等待最近读数"
        return {"name": spec["name"], "device": spec["device"], "share_key": spec["key"] if spec["device"] == "somaloop" else None, "status": status, "tiles": tiles, "theme": spec["theme"],
                "visual": spec["visual"], "footer": spec["footer"]}
