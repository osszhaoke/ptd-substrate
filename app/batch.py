"""批量入库（R20，产品负责人 2026-10-14 批准“四步全做”“按类型确认”“明细另存 + 日汇总”）。

一次拖进很多文件，后台一份一份排队认、读、核对；保存永远要本人确认（L-36）：
- 化验单（图片、PDF）：识别出来后进现有的逐项确认页；大 PDF 一页一页读，先按规则判断每页是不是化验单。
- 苹果健康、Withings、连续血糖、已认识格式的表格：按类型确认（条数、时间段、来源、抽样原文），确认一类存一类。
- 新格式的表格：本机千问只看列名和“这一列像什么”（数字 / 时间 / 日期 / 文字），不看数值，猜每一列是什么；
  本人确认一次存成模板，以后同样的表直接用。
- 核对：和星炬里已有的同一指标、同一时间比，一样的不再存，不一样的标“有冲突”，本人选用哪个。
- 队列、每份文件的状态、保存计划都写在实例目录（<实例>/startorch/batch/），关掉再开从没做完的那份接着做。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import threading
import time
import traceback
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

import batch_parse as bp
import recognize
import series
from h1_common import H1Error, apply_rule, make_observation_id, time_key
from startorch_outbox import ObservationInput, open_startorch, save_batch
import obs_time  # noqa: E402
import input_guard
from startorch_table import parse_table, unique_key_for_lab

CHUNK = 5000
MAX_FILE = 4 * 1024 ** 3
SRC_ZH = {"OCR_LLM": "识别录入", "MANUAL": "手工录入", "TABLE": "表格导入", "TEXT_LLM": "文字录入", "SYNTHETIC": "合成数据",
          "APPLE_HEALTH": "苹果健康", "DEVICE_WITHINGS": "Withings", "DEVICE_CGM": "连续血糖", "OURA": "Oura"}
DEVICE_KINDS = ("apple_health", "withings", "cgm")
SHAPE_ZH = {"数字": "数字", "时间": "时间", "日期": "日期", "文字": "文字", "空": "空"}


def _atomic(path: Path, obj) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:6]}.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _clean(text, limit: int) -> str:
    return re.sub(r"[\x00-\x1f]", " ", str(text or "")).strip()[:limit]


def get_queue(app, inst):
    """One constructor/recovery owner, published only after full initialization.

    Independent of global A; recovery never calls app.batch recursively or takes A.
    The app creates this ownership lock before publishing itself to any workers.
    """
    key = str(inst.ctx.root)
    with app._batch_init_lock:
        if key not in app.batches:
            queue = Batch(app, inst)
            if not inst.spec.get("replay"):
                for item in queue.items():
                    if item["status"] == "working":
                        queue.update(item["id"], status="queued", note="")
                queue.reread_notlab()
            app.batches[key] = queue
        return app.batches[key]


class Batch:
    """一个实例的批量队列。所有状态都在磁盘上；内存里只有“识别到第几页”这类进度文字。"""

    def __init__(self, app, inst):
        self.app, self.inst = app, inst
        self.root = inst.ctx.root / "startorch" / "batch"
        if not getattr(inst, "spec", {}).get("replay"):
            for d in ("files", "items", "results", "stage", "plans"):
                (self.root / d).mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.progress = {}

    # ------------------------------------------------------------------ 存取
    def _log(self, ev: str, **kw) -> None:
        with open(self.root / "log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(dict(at=self.inst.now(), ev=ev, **kw), ensure_ascii=False) + "\n")

    def get(self, item_id: str) -> dict:
        if not isinstance(item_id, str) or not re.fullmatch(r"[0-9a-f]{12}", item_id):
            raise H1Error("BATCH_ITEM_UNKNOWN", "")
        p = self.root / "items" / f"{item_id}.json"
        if not p.exists():
            raise H1Error("BATCH_ITEM_UNKNOWN", "")
        return json.loads(p.read_text("utf-8"))

    def put(self, item: dict) -> dict:
        input_guard.require_writable(self.inst)
        with self.lock:
            _atomic(self.root / "items" / f"{item['id']}.json", item)
        return item

    def update(self, item_id: str, **kw) -> dict:
        with self.lock:
            it = self.get(item_id)
            it.update(kw)
            return self.put(it)

    def items(self) -> list:
        out = [json.loads(p.read_text("utf-8")) for p in (self.root / "items").glob("*.json")]
        return sorted(out, key=lambda i: (i["added_at"], i["seq"]))

    def settings(self) -> dict:
        p = self.root / "settings.json"
        return json.loads(p.read_text("utf-8")) if p.exists() else {"paused": False}

    def set_paused(self, on: bool) -> dict:
        input_guard.require_writable(self.inst)
        _atomic(self.root / "settings.json", dict(self.settings(), paused=bool(on)))
        self._log("pause" if on else "resume")
        if not on:
            self.app.batch_wake()
        return self.settings()

    def result(self, item_id: str, part: str = "") -> dict:
        if not isinstance(item_id, str) or not re.fullmatch(r"[0-9a-f]{12}", item_id):
            raise H1Error("BATCH_ITEM_UNKNOWN", "")
        if not isinstance(part, str) or not re.fullmatch(r"(?:\.p[1-9][0-9]{0,8})?", part):
            raise H1Error("BATCH_PAGE_UNKNOWN", "")
        folder = self.root / "results"
        p = folder / f"{item_id}{part}.json"
        if folder.is_symlink() or p.is_symlink() or not p.resolve().is_relative_to(folder.resolve()):
            raise H1Error("BATCH_PATH_INVALID", "")
        return json.loads(p.read_text("utf-8")) if p.exists() else {}

    def file_path(self, it: dict) -> Path:
        return self.root / "files" / it["file"]

    def templates(self) -> dict:
        p = self.root / "templates.jsonl"
        out = {}
        if p.exists():
            for line in p.read_text("utf-8").splitlines():
                if line.strip():
                    t = json.loads(line)
                    out[t["sig"]] = t
        return out

    # ------------------------------------------------------------------ 加文件
    def add_stream(self, name: str, rel: str, rfile, length: int) -> dict:
        """边收边写、边算指纹，不整份读进内存。同一个文件加两次只处理一次。"""
        input_guard.require_writable(self.inst)
        if length <= 0:
            raise H1Error("FILE_EMPTY", "")
        if length > min(MAX_FILE, input_guard.limit(self.app.config, "batch_bytes")):
            raise H1Error("FILE_TOO_LARGE", "")
        name = _clean(Path(name).name, 200) or "文件"
        rel = _clean(rel, 400)
        ext = Path(name).suffix.lower()[:8]
        tmp = self.root / "files" / f".up-{uuid.uuid4().hex}"
        h, left = hashlib.sha256(), length
        try:
            with open(tmp, "wb") as f:
                while left > 0:
                    chunk = rfile.read(min(left, 1 << 20))
                    if not chunk:
                        break
                    h.update(chunk)
                    f.write(chunk)
                    left -= len(chunk)
                f.flush()
                os.fsync(f.fileno())
            if left:
                tmp.unlink(missing_ok=True)
                raise H1Error("UPLOAD_INCOMPLETE", "")
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
        sha = h.hexdigest()
        target = self.root / "files" / f"{sha[:16]}{re.sub(r'[^.a-z0-9]', '', ext)}"
        if target.exists():
            tmp.unlink()
        else:
            os.replace(tmp, target)
        with self.lock:
            all_items = self.items()
            same = next((i for i in all_items if i["sha"] == sha and i["status"] != "failed"), None)
            group = rel.split("/")[0] if "/" in rel else ""
            it = {"id": uuid.uuid4().hex[:12], "seq": len(all_items), "name": name, "rel": rel, "group": group, "sha": sha,
                  "size": length, "file": target.name, "added_at": self.inst.now(), "kind": "", "label": "", "why": "",
                  "status": "queued", "note": "", "saved": {}, "decisions": {}}
            if same:
                it.update(status="duplicate", kind=same["kind"], label=same["label"], dup_of=same["id"], dup_name=same["name"],
                          note="和“" + same["name"] + "”是同一个文件")
            else:
                d = bp.detect(target, name, self.templates())
                it.update(kind=d["kind"], label=d["label"], why=d.get("why", ""), detect={k: v for k, v in d.items() if k in ("spec", "format", "template")})
                if d["kind"] in ("skip", "gene"):
                    it.update(status="skipped", note=d.get("why", ""))
                elif d["kind"] in DEVICE_KINDS + ("table_ptds", "table_template", "table_unknown") and self.inst.nature != "REAL":
                    it.update(status="skipped", note="这份数据只收合成数据；真实设备和表格数据请在“我的真实数据”里导入")
            self.put(it)
        self._log("add", id=it["id"], sha=sha[:16], kind=it["kind"], status=it["status"])
        self.app.batch_wake()
        return it

    # ------------------------------------------------------------------ 后台：一次做一份
    def next_job(self):
        if self.settings().get("paused"):
            return None
        for it in self.items():
            if it["status"] in ("queued", "saving"):
                return it
        return None

    def run(self, it: dict) -> None:
        input_guard.require_writable(self.inst)
        try:
            if it["status"] == "saving":
                return self._save(it)
            self.update(it["id"], status="working", note="")
            kind = it["kind"]
            if kind == "lab_image":
                self._lab(it, pages=None)
            elif kind == "lab_pdf":
                self._lab_pdf(it)
            elif kind in DEVICE_KINDS:
                self._device(it)
            elif kind == "table_ptds":
                self._ptds(it)
            elif kind == "table_template":
                self._generic(it, it["detect"]["template"])
            elif kind == "table_unknown":
                self._propose(it)
            else:
                self.update(it["id"], status="skipped", note=it.get("why") or "不入库")
        except Exception as exc:  # noqa: BLE001 - 一份文件出错不挡后面的，如实写原因
            code = exc.code if isinstance(exc, H1Error) else type(exc).__name__
            self.app.log("batch_failed", self.inst.ctx.instance_id, it["id"], code)
            (self.root / "results" / f"{it['id']}.error.txt").write_text(traceback.format_exc()[-4000:], "utf-8")
            self.update(it["id"], status="failed", note=FAIL_ZH.get(code, "没读成（" + code + "）"))
        finally:
            self.progress.pop(it["id"], None)

    # ---- 化验单
    def _recognize(self, it: dict, page: int | None) -> dict:
        src = self.file_path(it)
        originals = self.inst.ctx.root / "startorch" / "originals"
        originals.mkdir(parents=True, exist_ok=True)
        ext = Path(it["name"]).suffix.lower() if Path(it["name"]).suffix.lower() in recognize.ORIGINAL_EXT else ".bin"
        target = originals / f"{it['sha'][:16]}{ext}"
        if not target.exists():
            try:
                os.link(src, target)
            except OSError:
                shutil.copyfile(src, target)
        raw = recognize.ocr(target, page=page)
        res = recognize.parse(raw, it["sha"], self.app.registry, self.app.llm)
        res.update({"name": it["name"] + (f" · 第 {page} 页" if page else ""), "original": target.name, "sha256": it["sha"],
                    "nature": self.inst.nature, "batch": {"id": it["id"], "page": page or 1}})
        record = dict(res, recognized_at=self.inst.now())
        (originals / f"{it['sha'][:16]}{'.p' + str(page) if page else ''}.recognition.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=1), "utf-8")
        res.pop("source_lines", None)
        return res

    def _page_summary(self, it: dict, page: int, res: dict) -> dict:
        _atomic(self.root / "results" / f"{it['id']}.p{page}.json", res)
        return {"page": page, "kind": res.get("kind", "lab"), "rows": len(res["rows"]), "date": res.get("date") or "",
                "notice": res.get("notice", ""), "saved": None}

    def _lab(self, it: dict, pages) -> None:
        self.progress[it["id"]] = "识别中"
        res = self._recognize(it, None)
        self._finish_lab(it, [self._page_summary(it, 1, res)], 1)

    def _lab_pdf(self, it: dict) -> None:
        n = recognize.pdf_pages(self.file_path(it))
        if n is None:  # 识别程序是旧版（不会一页一页读）：小 PDF 整份读，大的照实说
            if it["size"] > 30 * 1024 ** 2:
                return self.update(it["id"], status="failed", note="这个 PDF 太大，识别程序需要更新后才能一页一页读")
            return self._lab(it, None)
        done = self.result(it["id"]).get("pages") or []
        for page in range(len(done) + 1, n + 1):
            if self.settings().get("paused"):
                _atomic(self.root / "results" / f"{it['id']}.json", {"pages": done, "total": n})
                return self.update(it["id"], status="queued", note=f"暂停了，读到第 {page - 1} / {n} 页")
            self.progress[it["id"]] = f"识别中 · 第 {page} / {n} 页"
            res = self._recognize(it, page)
            done.append(self._page_summary(it, page, res))
            _atomic(self.root / "results" / f"{it['id']}.json", {"pages": done, "total": n})  # 断了从下一页接着读
        self._finish_lab(it, done, n)

    def _finish_lab(self, it: dict, pages: list, total: int) -> None:
        _atomic(self.root / "results" / f"{it['id']}.json", {"pages": pages, "total": total})
        lab = [p for p in pages if p["kind"] == "lab" and p["rows"]]
        if not lab:
            notice = next((p["notice"] for p in pages if p["notice"]), "") or "没有认出化验指标"
            return self.update(it["id"], status="notlab", note=notice, pages=total, dict=self.app.registry.current.version)
        dup = self._same_report(it, lab)
        self.update(it["id"], status="ready", pages=total, lab_pages=len(lab), rows=sum(p["rows"] for p in lab),
                    note="", **({"dup_of": dup["id"], "dup_name": dup["name"]} if dup else {}))

    def _same_report(self, it: dict, lab: list):
        """另拍一张、或 PDF 和照片是同一份报告：认出的指标、日期、数值都一样，就标“重复”（还是可以点开看）。"""
        mine = self._row_set(it["id"], lab)
        if len(mine) < 3:
            return None
        for other in self.items():
            if other["id"] == it["id"] or other["kind"] not in ("lab_image", "lab_pdf") or other["status"] not in ("ready", "saved"):
                continue
            theirs = self._row_set(other["id"], [p for p in self.result(other["id"]).get("pages") or [] if p["kind"] == "lab"])
            if theirs and len(mine & theirs) >= 0.8 * len(mine):
                return other
        return None

    def _row_set(self, item_id: str, pages: list) -> set:
        out = set()
        for p in pages:
            r = self.result(item_id, f".p{p['page']}")
            for row in r.get("rows") or []:
                out.add((row["code"], r.get("date") or "", (row.get("cmp") or "") + row["value"]))
        return out

    def page(self, item_id: str, page: int) -> dict:
        """逐项确认页用的识别结果，带上和星炬已有数据的核对。"""
        res = self.result(item_id, f".p{int(page)}")
        if not res:
            raise H1Error("BATCH_PAGE_UNKNOWN", "")
        res["checks"] = lab_check(self.inst, self.app.registry, res["rows"], res.get("date") or "")
        res["phase"] = "done"
        return res

    def mark_page(self, item_id: str, page: int, counts: dict) -> dict:
        input_guard.require_writable(self.inst)
        with self.lock:
            it = self.get(item_id)
            r = self.result(item_id)
            for p in r.get("pages") or []:
                if p["page"] == int(page):
                    p["saved"] = {k: int(v) for k, v in (counts or {}).items() if k in ("CREATED", "REVISED", "UNCHANGED")}
            _atomic(self.root / "results" / f"{item_id}.json", r)
            lab = [p for p in r.get("pages") or [] if p["kind"] == "lab" and p["rows"]]
            left = [p for p in lab if not p.get("saved")]
            n = sum(sum(p["saved"].values()) for p in lab if p.get("saved"))
            it.update(status="ready" if left else "saved", saved_rows=n)
            self.put(it)
        self._log("page_saved", id=item_id, page=int(page))
        return it

    # ---- 按类型确认的数据源
    def _skip_sources(self) -> set:
        p = self.inst.ctx.root / "startorch" / "sources.json"
        src = json.loads(p.read_text("utf-8")) if p.exists() else {}
        return {"Oura"} if src.get("oura") else set()

    def _device(self, it: dict) -> None:
        stage = self.root / "stage" / it["id"]
        if stage.exists():
            shutil.rmtree(stage)
        path, tz = self.file_path(it), self.inst.ctx.tz
        self.progress[it["id"]] = "读取中"
        if it["kind"] == "apple_health":
            res = bp.parse_apple_health(path, stage, self._skip_sources())
            skipped = [(t["label"], sum(t["skipped_sources"].values())) for t in res["types"] if t["skipped_sources"]]
            if skipped:
                res["overlap"] = "、".join(f"{lab}里有 {n:,} 条" for lab, n in skipped) + "来自 Oura，星炬里已经从 Oura 直接接过，这部分不会重复保存"
        elif it["kind"] == "withings":
            res = bp.parse_withings(path, it["detect"]["spec"], stage, tz)
        else:
            res = bp.parse_cgm(path, it["detect"]["format"], stage, tz)
        self._ready_types(it, res)

    def _ready_types(self, it: dict, res: dict) -> None:
        # 一条都没留下的类型（比如全是戒指记的、已从戒指直接接入）先去掉，再做比对
        res["types"] = [t for t in res["types"] if t["count"]]
        for t in res["types"]:
            t["check"] = self._preview(it, t)
        _atomic(self.root / "results" / f"{it['id']}.json", res)
        if not res["types"]:
            return self.update(it["id"], status="skipped", note="没有能入库的数据")
        self.update(it["id"], status="ready", types=len(res["types"]), rows=sum(t["count"] for t in res["types"]), note="")

    def _preview(self, it: dict, t: dict) -> dict:
        """确认前先看一眼：和已有的数据比，多少是新的、多少一样、多少不一样。"""
        if t["mode"].startswith("series"):
            conn = series.open_series(self.inst.ctx.root)
            try:
                have = conn.execute("SELECT count(*) FROM sample WHERE series=?", (t["code"],)).fetchone()[0]
            finally:
                conn.close()
            return {"series_have": have}
        items, internal = self._each_items(it, t)
        c = reconcile(self.inst, items)
        return {"new": len(c["new"]), "same": len(c["same"]), "conflict": len(c["conflict"]), "internal": internal,
                "conflicts": [x["show"] for x in c["conflict"][:20]]}

    def _ptds(self, it: dict) -> None:
        data = self.file_path(it).read_bytes()
        _, items = parse_table(data, self.inst.ctx, synthetic=input_guard.nature(default=self.inst.nature) == "SYNTHETIC")
        res = {"kind": "table", "label": "PTDS 标准格式表格", "types": [{
            "key": "TABLE", "label": "表格里的数据", "mode": "table", "code": "", "unit": "", "count": len(items),
            "first": None, "last": None, "sources": {"表格导入": len(items)}, "skipped_sources": {}, "bad": 0, "samples": [],
            "source_kind": "TABLE"}], "not_imported": []}
        self._ready_types(it, res)

    # ---- 新格式的表格：千问配列，本人确认，存成模板
    def _propose(self, it: dict) -> None:
        rows = bp.read_table(self.file_path(it), limit=60)
        shapes = bp.column_shapes(rows)
        targets = mapping_targets(self.app.registry)
        cols, by = propose_columns(self.app.llm, shapes, targets, self.app.registry)
        for c, s in zip(cols, shapes):
            c["shape"] = s["shape"]
        examples = [[r[i] if i < len(r) else "" for r in rows[1:4]] for i in range(len(shapes))]
        _atomic(self.root / "results" / f"{it['id']}.json", {"kind": "mapping", "columns": cols, "examples": examples, "by": by,
                                                            "rows": len(bp.read_table(self.file_path(it))) - 1,
                                                            "header": rows[0], "tz": self.inst.ctx.tz})
        self.update(it["id"], status="mapping", note="")

    def set_mapping(self, item_id: str, columns: list) -> dict:
        input_guard.require_writable(self.inst)
        it = self.get(item_id)
        if it["status"] != "mapping":
            raise H1Error("BATCH_STATE", it["status"])
        prop = self.result(item_id)
        targets = {t["id"] for t in mapping_targets(self.app.registry)}
        cols = []
        for i, c in enumerate(columns):
            tgt = c.get("target") or "skip"
            if tgt not in targets:
                raise H1Error("MAPPING_INVALID", tgt)
            cols.append({"col": i, "name": prop["header"][i] if i < len(prop["header"]) else "", "target": tgt,
                         "unit": _clean(c.get("unit"), 20)})
        if not any(c["target"] in ("time", "date") for c in cols):
            raise H1Error("MAPPING_NO_TIME", "")
        if not any(c["target"] not in ("time", "date", "skip") for c in cols):
            raise H1Error("MAPPING_NO_VALUE", "")
        tpl = {"sig": bp.signature(prop["header"]), "columns": cols, "tz": self.inst.ctx.tz, "saved_at": self.inst.now(),
               "by": prop.get("by", "")}
        with open(self.root / "templates.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(tpl, ensure_ascii=False) + "\n")
        self._log("template", id=item_id, sig=hashlib.sha256(tpl["sig"].encode()).hexdigest()[:12])
        it.update(status="queued", kind="table_template", label="表格 · 已认识的格式", detect={"template": tpl})
        self.put(it)
        # 同一批里表头一样、还在等配列的表，一起用这个模板
        for other in self.items():
            if other["status"] == "mapping" and other["id"] != item_id and \
                    bp.signature(self.result(other["id"]).get("header") or []) == tpl["sig"]:
                other.update(status="queued", kind="table_template", label="表格 · 已认识的格式", detect={"template": tpl})
                self.put(other)
        self.app.batch_wake()
        return it

    def _generic(self, it: dict, tpl: dict) -> None:
        res = parse_generic(self.file_path(it), tpl, self.root / "stage" / it["id"], self.app.registry,
                            self.inst.nature)
        self._ready_types(it, res)

    # ---- 确认、保存
    def confirm(self, item_id: str, decisions: dict, conflicts: dict) -> dict:
        """decisions: {类型: true 存 / false 不存}；conflicts: {类型: keep 留原来的 / new 用这份文件的}。"""
        input_guard.require_writable(self.inst)
        with self.lock:
            it = self.get(item_id)
            if it["status"] not in ("ready",):
                raise H1Error("BATCH_STATE", it["status"])
            res = self.result(item_id)
            keys = {t["key"] for t in res.get("types") or []}
            dec = {k: bool(v) for k, v in (decisions or {}).items() if k in keys and k not in it["saved"]}
            if not any(dec.values()):
                raise H1Error("BATCH_NOTHING", "")
            it["decisions"] = dict(it.get("decisions") or {}, **dec)
            it["conflicts"] = {k: ("new" if v == "new" else "keep") for k, v in (conflicts or {}).items() if k in keys}
            it["status"] = "saving"
            it["plan_no"] = int(it.get("plan_no") or 0) + 1
            self.put(it)
        self._log("confirm", id=item_id, types=sorted(k for k, v in dec.items() if v), skip=sorted(k for k, v in dec.items() if not v))
        self.app.batch_wake()
        return it

    def skip(self, item_id: str) -> dict:
        input_guard.require_writable(self.inst)
        it = self.get(item_id)
        if it["status"] in ("saving", "working"):
            raise H1Error("BATCH_STATE", it["status"])
        self._log("skip", id=item_id)
        return self.update(item_id, status="skipped", note="你选了不导入")

    def reread_notlab(self) -> int:
        """字典加了新指标以后，之前“没认出化验指标”的图片和 PDF 重新识别一遍（产品负责人 2026-10-14 07:01Z：测试集里的指标都要归集）。"""
        input_guard.require_writable(self.inst)
        n = 0
        for it in self.items():
            if it["status"] == "notlab" and it.get("dict") != self.app.registry.current.version:
                _atomic(self.root / "results" / f"{it['id']}.json", {})
                self.update(it["id"], status="queued", note="指标字典更新了，重新识别")
                n += 1
        return n

    def retry(self, item_id: str) -> dict:
        input_guard.require_writable(self.inst)
        it = self.get(item_id)
        if it["status"] != "failed":
            raise H1Error("BATCH_STATE", it["status"])
        self.app.batch_wake()
        return self.update(item_id, status="queued", note="")

    def _plan_path(self, it: dict) -> Path:
        return self.root / "plans" / f"{it['id']}.{it['plan_no']}.json"

    def _save(self, it: dict) -> None:
        input_guard.require_writable(self.inst)
        pp = self._plan_path(it)
        if not pp.exists():  # 先把要存什么算好、写下来；断了以后照这份计划接着存，请求号不变（重放安全）
            self.progress[it["id"]] = "核对中"
            _atomic(pp, self._build_plan(it))
        plan = json.loads(pp.read_text("utf-8"))
        items = [ObservationInput(**x) for x in plan["items"]]
        total = (len(items) + CHUNK - 1) // CHUNK
        counts = plan.setdefault("counts", {"CREATED": 0, "REVISED": 0, "UNCHANGED": 0})
        for i in range(plan.get("done", 0), total):
            self.progress[it["id"]] = f"保存中 · {i + 1} / {total}" if total > 1 else "保存中"
            part, future = obs_time.split(items[i * CHUNK:(i + 1) * CHUNK], self.inst.ctx.tz)  # 日期在今天之后的不收（产品负责人 2026-10-15）
            if future:
                counts["FUTURE"] = counts.get("FUTURE", 0) + len(future)
            with self.app.lock:
                torch = open_startorch(self.inst.ctx)
                try:
                    rs = save_batch(torch, self.inst.ctx, self.app.registry, part, batch_id=f"BATCH-{it['sha'][:16]}",
                                    request_id=f"BATCH-{it['sha'][:16]}-{it['id']}-{it['plan_no']}-{i}", saved_at=self.inst.now()) if part else []
                finally:
                    torch.close()
            for r in rs:
                counts[r.outcome] = counts.get(r.outcome, 0) + 1
            plan["done"] = i + 1
            _atomic(pp, plan)
        with self.app.lock:
            sync = self.inst.after_save() if items else None
        with self.lock:
            cur = self.get(it["id"])
            for k in plan["types"]:
                cur["saved"][k] = plan["types"][k]
            res = self.result(it["id"])
            left = [t["key"] for t in res.get("types") or [] if t["key"] not in cur["saved"] and cur["decisions"].get(t["key"]) is not False]
            cur.update(status="ready" if left else "saved", note="", saved_rows=sum(v.get("saved", 0) for v in cur["saved"].values()),
                       last_sync_ok=bool(sync and sync.get("ok")) if items else None)
            self.put(cur)
        self._log("saved", id=it["id"], plan=it["plan_no"], counts=counts)
        self.app.log("batch_saved", self.inst.ctx.instance_id, it["id"], counts.get("CREATED", 0), counts.get("REVISED", 0))

    def _build_plan(self, it: dict) -> dict:
        res = self.result(it["id"])
        todo = [t for t in res.get("types") or [] if it["decisions"].get(t["key"]) and t["key"] not in it["saved"]]
        items, per_type = [], {}
        for t in todo:
            if t["mode"].startswith("series"):
                got, info = self._series_items(it, t)
                per_type[t["key"]] = info
                items += got
                continue
            if t["mode"] == "table":
                _, raw = parse_table(self.file_path(it).read_bytes(), self.inst.ctx, synthetic=input_guard.nature(default=self.inst.nature) == "SYNTHETIC")
                internal = 0
            else:
                raw, internal = self._each_items(it, t)
            c = reconcile(self.inst, raw)
            use_new = it.get("conflicts", {}).get(t["key"]) == "new"
            keep = c["new"] + (c["conflict"] if use_new else [])
            items += [x["item"] for x in keep]
            per_type[t["key"]] = {"saved": len(keep), "same": len(c["same"]), "conflict": len(c["conflict"]),
                                  "conflict_used": "new" if use_new else "keep", "internal": internal}
        seen, uniq = set(), []
        for x in items:  # 同一次保存里不能有重复的 unique_key（DUPLICATE_KEY_IN_BATCH）
            if x.unique_key not in seen:
                seen.add(x.unique_key)
                uniq.append(x)
        return {"items": [x.__dict__ for x in uniq], "types": per_type, "built_at": self.inst.now()}

    def _rows(self, it: dict, t: dict):
        p = self.root / "stage" / it["id"] / f"{t['key']}.jsonl"
        if not p.exists():
            return
        with open(p, encoding="utf-8") as f:
            for line in f:
                yield json.loads(line)

    def _series_items(self, it: dict, t: dict):
        conn = series.open_series(self.inst.ctx.root)
        try:
            got = series.add(conn, t["code"], self._rows(it, t), it["sha"], self.inst.ctx.tz, self.inst.now())
            sums = series.summarize(conn, t["code"], got["days"])
        finally:
            conn.close()
        kind = series.SERIES[t["code"]][3]
        items = []
        for s in sums:
            temporal = {"role": "DAY", "observed_date": s["day"], "tz": self.inst.ctx.tz}
            items.append(ObservationInput(f"SERIES|{s['code']}|DAY:{s['day']}", s["code"], s["value"], None, s["unit"], temporal,
                                          kind, f"SERIES:{t['code']}:{s['day']}:{_clean(s['source'], 60)}", "DEVICE_CONSUMER"))
        c = reconcile(self.inst, items)
        keep = c["new"] + c["conflict"]  # 汇总是从明细库重新算的：变了就是更新（新版本，旧版本保留），不是冲突
        return [x["item"] for x in keep], {"saved": len(keep), "same": len(c["same"]), "updated": len(c["conflict"]),
                                           "added": got["added"], "had": got["same"], "days": len(got["days"])}

    def _each_items(self, it: dict, t: dict):
        """一条一条存的类型 → ObservationInput；文件里同一时刻两个不同的数：两条都不存，照实计数。"""
        out, internal, short = {}, 0, it["sha"][:16]
        bad = set()
        for start, end, value, unit, source, loc in self._rows(it, t):
            if t["mode"] == "each_day":
                temporal = {"role": "DAY", "observed_date": start, "tz": self.inst.ctx.tz}
            else:
                temporal = {"role": "INSTANT", "observed_at": start}
            ref = f"FILE:{short}#L{loc}"
            sk = t["source_kind"]
            if sk == "APPLE_HEALTH":
                src = _clean(source, 80) or "Health"
                key = f"AH|{t['code']}|{time_key(temporal, ref)}|{src}"
                trust = "DEVICE_CONSUMER"
            elif sk in ("DEVICE_WITHINGS", "DEVICE_CGM"):
                key = f"{'WITHINGS' if sk == 'DEVICE_WITHINGS' else 'CGM'}|{t['code']}|{time_key(temporal, ref)}"
                trust = "DEVICE_CONSUMER"
            else:  # 表格（模板）：和化验单同一套 unique_key，跨文件能对上
                key = unique_key_for_lab(t["code"], temporal, ref)
                fam = self.app.registry.current.codes[t["code"]].family
                trust = "SYNTHETIC" if sk == "SYNTHETIC" else ("SELF_REPORT" if fam == "FLAG" else "CLINICAL_LAB")
            item = ObservationInput(key, t["code"], value, None, unit, temporal, sk, ref, trust)
            if key in out:
                if out[key].value_raw != value or out[key].unit_raw != unit:
                    bad.add(key)
                continue
            out[key] = item
        for k in bad:
            internal += 1
            out.pop(k, None)
        return list(out.values()), internal

    # ------------------------------------------------------------------ 给界面
    def view(self) -> dict:
        items = self.items()
        for it in items:
            it["progress"] = self.progress.get(it["id"], "")
        checks = []
        for it in items:
            if it["kind"] in ("lab_image", "lab_pdf") and it["status"] == "ready" and not it.get("dup_of"):
                for p in self.result(it["id"]).get("pages") or []:
                    if p["kind"] != "lab" or p.get("saved"):
                        continue
                    r = self.result(it["id"], f".p{p['page']}")
                    for c in lab_check(self.inst, self.app.registry, r.get("rows") or [], r.get("date") or ""):
                        if c["state"] != "new":
                            checks.append(dict(c, item=it["id"], name=it["name"], page=p["page"], date=r.get("date") or ""))
        return {"items": items, "paused": self.settings().get("paused", False), "checks": checks[:50]}

    def detail(self, item_id: str) -> dict:
        it = self.get(item_id)
        it["progress"] = self.progress.get(item_id, "")
        return {"item": it, "result": self.result(item_id)}


FAIL_ZH = {"OCR_UNSUPPORTED": "本机不支持化验单识别（需要 macOS），可以改用表格导入或手工录入",
           "OCR_ENGINE_UNAVAILABLE": "识别程序没编译出来（需要装 Xcode 命令行工具：xcode-select --install）", "OCR_FAILED": "识别程序没读出来",
           "encoding": "表格的文字编码认不出", "BadZipFile": "Excel 文件打不开"}


# ---------------------------------------------------------------------------- 核对

def _latest(torch, oid: str):
    return torch.execute("SELECT payload FROM formal_observation WHERE observation_id = ? ORDER BY revision DESC LIMIT 1",
                         (oid,)).fetchone()


def reconcile(inst, items: list) -> dict:
    """和星炬里同一 unique_key 的最新版本比：没有 → 新；数值、单位、比较符、时间都一样 → 一样（不再存）；不一样 → 冲突。"""
    out = {"new": [], "same": [], "conflict": []}
    torch = open_startorch(inst.ctx)
    try:
        for x in items:
            row = _latest(torch, make_observation_id(inst.ctx.instance_id, x.unique_key))
            if row is None:
                out["new"].append({"item": x})
                continue
            p = json.loads(row[0])
            same = p["status"] == "ACTIVE" and p["unit_raw"] == x.unit_raw and p["comparator"] == x.comparator \
                and p["temporal"] == x.temporal and _dec(p["value_raw"]) == _dec(x.value_raw)
            if same:
                out["same"].append({"item": x})
            else:
                when = x.temporal.get("observed_at") or x.temporal.get("observed_date") or ""
                out["conflict"].append({"item": x, "show": {"code": x.code, "when": when, "new": x.value_raw, "unit": x.unit_raw or "",
                                                            "old": p["value_raw"], "old_unit": p["unit_raw"] or "",
                                                            "old_src": SRC_ZH.get(p["source_kind"], p["source_kind"]),
                                                            "old_status": p["status"]}})
    finally:
        torch.close()
    return out


def _dec(v):
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return v


def _canon(registry, code: str, value: str, unit: str):
    try:
        cdef = registry.current.codes[code]
        return apply_rule(dict(cdef.units)[unit], Decimal(value)).normalize()
    except Exception:  # noqa: BLE001
        return None


def lab_check(inst, registry, rows: list, date: str) -> list:
    """识别出来的化验项，和星炬里同一指标、同一天的记录比（不管是手工录的、表格导的还是另一张单子识别的）。
    一样 → same（不会重复存）；不一样 → conflict（列出原来的值和来源，本人选）。"""
    if not date or not rows:
        return [{"i": i, "state": "new"} for i in range(len(rows))]
    codes = sorted({r["code"] for r in rows})
    torch = open_startorch(inst.ctx)
    try:
        latest = {}
        q = "SELECT observation_id, revision, payload FROM formal_observation WHERE json_extract(payload, '$.code') IN (%s)" % \
            ",".join("?" * len(codes))
        for oid, rev, payload in torch.execute(q, codes):
            if oid not in latest or rev > latest[oid][0]:
                latest[oid] = (rev, payload)
    finally:
        torch.close()
    tz = ZoneInfo(inst.ctx.tz)
    have = {}
    for _, payload in latest.values():
        p = json.loads(payload)
        if p["status"] != "ACTIVE":
            continue
        t = p["temporal"]
        day = t.get("observed_date") or (datetime.fromisoformat(t["observed_at"]).astimezone(tz).date().isoformat()
                                         if t.get("observed_at") else None)
        if day == date:
            have.setdefault(p["code"], []).append(p)
    out = []
    for i, r in enumerate(rows):
        olds = have.get(r["code"]) or []
        if not olds:
            out.append({"i": i, "state": "new"})
            continue
        mine = _canon(registry, r["code"], r.get("value") or "", r.get("unit") or "")
        match = [p for p in olds if p.get("comparator") == (r.get("cmp") or None) and mine is not None
                 and _dec(p["value_canonical"]).normalize() == mine]
        p = (match or olds)[-1]
        out.append({"i": i, "code": r["code"], "state": "same" if match else "conflict", "new": (r.get("cmp") or "") + (r.get("value") or ""),
                    "unit": r.get("unit") or "", "old": (p.get("comparator") or "") + p["value_raw"], "old_unit": p["unit_raw"] or "",
                    "old_src": SRC_ZH.get(p["source_kind"], p["source_kind"])})
    return out


# ---------------------------------------------------------------------------- 新格式表格：配列

def mapping_targets(registry) -> list:
    out = [{"id": "time", "label": "采样时间"}, {"id": "date", "label": "日期（只有日期）"}, {"id": "skip", "label": "不导入这一列"},
           {"id": "series:CGM_GLUCOSE", "label": "连续血糖（CGM）"}]
    for c, d in sorted(registry.current.codes.items()):
        if d.family in ("LAB", "VITAL") and d.value_type == "DECIMAL":
            out.append({"id": c, "label": d.label_zh})
    return out


def _units_of(registry, target: str) -> list:
    if target == "series:CGM_GLUCOSE":
        return ["mmol/L", "mg/dL"]
    cdef = registry.current.codes.get(target)
    return [u for u, _ in cdef.units] if cdef else []


def _header_unit(name: str, units: list) -> str:
    m = re.search(r"[（(]([^（）()]{1,15})[）)]\s*$", name or "")
    if m:
        u = m.group(1).strip()
        for x in units:
            if x.lower() == u.lower():
                return x
    return ""


def propose_columns(llm, shapes: list, targets: list, registry):
    """本机千问只看列名和这一列像什么（不看数值），从选项里挑；千问不可用就按同义词对照猜，如实标出来。"""
    ids = {t["id"] for t in targets}
    pick = {}
    by = ""
    if llm is not None and llm.ensure():
        catalog = "\n".join(f"{t['id']}: {t['label']}" for t in targets)
        cols = "\n".join(f"{i}. {s['col']}（{SHAPE_ZH.get(s['shape'], s['shape'])}）" for i, s in enumerate(shapes))
        system = ("你只做一件事：判断表格每一列是什么。只能从给定的选项代码里选；拿不准就选 skip。"
                  "时间列选 time，只有日期的列选 date。不要输出数值，不要解释。输出 JSON：{\"cols\":[{\"col\":列号,\"target\":\"选项代码\"}]}")
        try:
            raw = llm.chat(system, f"选项：\n{catalog}\n\n表格的列（列名和这一列像什么）：\n{cols}")
            m = re.search(r"\{.*\}", raw, re.S)
            doc = json.loads(m.group(0)) if m else {}
            for c in doc.get("cols", []) if isinstance(doc, dict) else []:
                if isinstance(c, dict) and isinstance(c.get("col"), int) and 0 <= c["col"] < len(shapes) and c.get("target") in ids:
                    pick[c["col"]] = c["target"]
            if pick:
                import starling_page  # noqa: PLC0415
                by = starling_page.sign(llm)
        except Exception:  # noqa: BLE001 - 千问出错就退到同义词，如实标出来
            pick = {}
    if not pick:
        by = "同义词对照（本机千问没有给结果）"
        for i, s in enumerate(shapes):
            pick[i] = guess_column(s, registry)
    out = []
    for i, s in enumerate(shapes):
        tgt = pick.get(i, "skip")
        # 千问选的和这一列的样子对不上（时间列却是数字……）：程序不采用，改成“不导入”，本人可以再改
        if tgt == "time" and s["shape"] not in ("时间",) or tgt == "date" and s["shape"] not in ("日期", "时间") or \
                tgt not in ("time", "date", "skip") and s["shape"] != "数字":
            tgt = "skip"
        units = _units_of(registry, tgt)
        out.append({"col": i, "name": s["col"], "target": tgt, "unit": _header_unit(s["col"], units) or (units[0] if units else ""),
                    "unit_from": "表头" if _header_unit(s["col"], units) else ("字典默认" if units else "")})
    return out, by


def guess_column(s: dict, registry) -> str:
    name = s["col"]
    if s["shape"] == "时间":
        return "time"
    if s["shape"] == "日期":
        return "date"
    if s["shape"] != "数字":
        return "skip"
    n = recognize.norm_name(re.sub(r"[（(][^（）()]*[）)]\s*$", "", name))
    if "血糖" in n and not re.search(r"糖化|餐", n):
        return "series:CGM_GLUCOSE"
    for c, d in registry.current.codes.items():
        if d.family in ("LAB", "VITAL") and d.value_type == "DECIMAL":
            names = [d.label_zh] + recognize.ALIASES.get(c, [])
            if any(recognize.norm_name(x) == n for x in names if x):
                return c
    return "skip"


def parse_generic(path: Path, tpl: dict, stage: Path, registry, nature: str) -> dict:
    rows = bp.read_table(path)
    header, body = rows[0], rows[1:]
    tz = tpl.get("tz") or "Asia/Shanghai"
    tcol = next((c["col"] for c in tpl["columns"] if c["target"] == "time"), None)
    dcol = next((c["col"] for c in tpl["columns"] if c["target"] == "date"), None)
    if stage.exists():
        shutil.rmtree(stage)
    stagers = []
    sk = "SYNTHETIC" if nature == "SYNTHETIC" else "TABLE"
    for c in tpl["columns"]:
        if c["target"] in ("time", "date", "skip"):
            continue
        if c["target"] == "series:CGM_GLUCOSE":
            s = bp.Stager(stage, "CGM_GLUCOSE", "连续血糖", "series:minmaxavg", "CGM_GLUCOSE", c["unit"], "DEVICE_CGM",
                          "单位按你确认的 " + c["unit"] + "；没写时区的按 " + tz + " 算")
        else:
            d = registry.current.codes[c["target"]]
            s = bp.Stager(stage, c["target"], d.label_zh, "each" if tcol is not None else "each_day", c["target"], c["unit"], sk,
                          "按你确认过的列导入" + ("；没写时区的按 " + tz + " 算" if tcol is not None else ""))
        stagers.append((c["col"], s))
    for n, r in enumerate(body, 2):
        if tcol is not None:
            at = bp.parse_time(r[tcol], tz) if tcol < len(r) else None
            start = at
        else:
            start = bp.parse_day(r[dcol]) if dcol < len(r) else None
        for col, s in stagers:
            v = r[col].strip() if col < len(r) else ""
            if v == "":
                continue
            if not start or not bp._is_number(v):
                s.t["bad"] += 1
                continue
            s.add(start, start, v, s.t["unit"], "表格导入" if s.t["source_kind"] != "DEVICE_CGM" else "连续血糖仪导出", n, ",".join(r))
    return {"kind": "table", "label": "表格 · 已认识的格式", "types": [s.close() for _, s in stagers], "not_imported":
            [{"label": c["name"], "count": None} for c in tpl["columns"] if c["target"] == "skip"]}


# ---------------------------------------------------------------------------- 后台线程

class Worker:
    """一个后台线程，按加入的先后一份一份做；没活就睡，有新文件或确认时叫醒。"""

    def __init__(self, app):
        self.app = app
        self.wake = threading.Event()
        self.stop = False
        self.thread = threading.Thread(target=self.loop, name="ptds-batch", daemon=True)

    def start(self):
        self.thread.start()

    def loop(self):
        while not self.stop:
            did = False
            for inst in list(self.app.instances.values()):
                if inst.spec.get("replay"):
                    continue
                b = self.app.batch(inst)
                job = b.next_job()
                if job:
                    b.run(job)
                    did = True
                    break
            if not did:
                self.wake.wait(30)
                self.wake.clear()

    def run_pending(self, limit: int = 100) -> int:
        """测试用：在当前线程里把排队的做完。"""
        n = 0
        for _ in range(limit):
            did = False
            for inst in list(self.app.instances.values()):
                if inst.spec.get("replay"):
                    continue
                b = self.app.batch(inst)
                job = b.next_job()
                if job:
                    b.run(job)
                    did, n = True, n + 1
                    break
            if not did:
                break
        return n
