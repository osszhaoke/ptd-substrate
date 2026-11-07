"""星簇（授权 · 数据离开 PTDS）· 本机进程版（10-17 演示）。

数据或状态只要离开 PTDS，都要经过星簇授权，并留下记录。规则：
- 星簇有自己的库 <instance_root>/cluster/cluster.db，只有星簇写它；
- 所有表只追加（BEFORE UPDATE / DELETE 触发器拒绝）：撤销是一条新事件，当前状态由事件和时间推出来；
- 每次新建、撤销、读取、拒绝都记一条：时间、授权编号、对象、结果、内容摘要。摘要只用配置里的名称拼，
  不含任何健康数值（写入前检查：摘要里不能出现数字）；
- read() 按披露级别给最小投影：仅信号 = 不含健康信息；摘要 = 不带数值；依据 = 摘要 + 驱动指标数值 + 规则结论；
  数据 = 结构化状态卡（只给智能体）。
- 基因位点（GENE_LOCI）单独授权，"全部状态卡"不含它：只给本人的本机智能体、只读、披露级别"数据"，可限定到具体
  rs 号（授权的 events 列存位点清单或 "*"）。读取只搬运原始文件里写着的基因型，不解读、不计算；每次读了哪些位点
  另记在 cluster/gene_reads.jsonl（授权记录的摘要不许有数字，rs 号放不进去）。

返回对象的字段名和界面原型 MockCluster 一致（product.html），界面把 MockCluster 换成 HTTP 调用即可。
通用入口仍由调用方持 app.lock；运行期授权写入及手机检查先取共享 P 再开库。
records/组合视图在 P 内复制原始行，锁外投影；未发布的独立 Store 保留调用方串行约定。
存储委托不取 P，禁止 SQL→P；每次调用自己开库、关库，可跨线程使用。
"""
from __future__ import annotations

import json
import re
import sys
import uuid
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

APP = Path(__file__).resolve().parent
if str(APP / "core") not in sys.path:
    sys.path.insert(0, str(APP / "core"))

from h1_common import H1Error  # noqa: E402
from dynamic import change_word  # noqa: E402
from sqlite_util import append_only_ddl, open_db, transaction  # noqa: E402

import gene_db  # noqa: E402
import phone_tail_auth  # noqa: E402
import cluster_grant_store  # noqa: E402
import phone_lifecycle  # noqa: E402

SCHEMA_ID = "ptds-cluster-0.1"
DDL = """CREATE TABLE grant_def (
  grant_id TEXT PRIMARY KEY,
  object TEXT NOT NULL,
  channel TEXT NOT NULL,
  method TEXT NOT NULL CHECK (method IN ('read', 'push')),
  level TEXT NOT NULL CHECK (level IN ('signal', 'summary', 'basis', 'data')),
  card TEXT NOT NULL,
  events TEXT NOT NULL,
  view TEXT,
  duration TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT,
  origin TEXT NOT NULL CHECK (origin IN ('USER', 'PRESET', 'EXAMPLE')),
  note TEXT
);
CREATE TABLE grant_event (
  id INTEGER PRIMARY KEY,
  grant_id TEXT NOT NULL REFERENCES grant_def (grant_id),
  event TEXT NOT NULL CHECK (event IN ('CREATED', 'REVOKED')),
  at TEXT NOT NULL
);
CREATE UNIQUE INDEX grant_event_once ON grant_event (grant_id, event);
CREATE TABLE access_record (
  id INTEGER PRIMARY KEY,
  at TEXT NOT NULL,
  grant_id TEXT,
  action TEXT NOT NULL CHECK (action IN ('CREATE', 'REVOKE', 'READ')),
  via TEXT NOT NULL,
  object TEXT,
  channel TEXT,
  method TEXT,
  level TEXT,
  card TEXT,
  outcome TEXT NOT NULL CHECK (outcome IN ('CREATED', 'WAIT_CHANNEL', 'REVOKED', 'READ', 'DENIED')),
  reason TEXT,
  summary TEXT NOT NULL
);
""" + append_only_ddl(["grant_def", "grant_event", "access_record"])

GSTATE_ZH = {"ACTIVE": "生效中", "WAIT_CHANNEL": "等接入", "REVOKED": "已撤销", "EXPIRED": "已到期"}
# 拒绝原因：界面显示为"读取被拒绝：授权" + 中文
DENY_ZH = {"NOT_FOUND": "不存在", "REVOKED": "已撤销", "EXPIRED": "已到期", "WAIT_CHANNEL": "等接入",
           "NOT_READ": "不含读取", "OUT_OF_SCOPE": "范围不含这张卡", "NOT_GENE": "范围不含基因位点",
           "LOCI_REQUIRED": "没有指定位点，这次要说明读哪些 rs 号", "LOCI_OUT_OF_SCOPE": "范围不含这些位点",
           "LOCI_INVALID": "收到的位点不是 rs 号", "LOCI_TOO_MANY": "一次最多读五十个位点"}
GENE = "GENE_LOCI"
STATE_REPORT = "STATE_REPORT"
RS_RE = re.compile(r"^rs\d{1,12}$")
MAX_LOCI_GRANT, MAX_LOCI_READ = 200, 50
GENE_NOTE = "只搬运原始文件里写着的基因型，不解读、不计算；遗传倾向，非诊断。"
RESULT_ZH = {"CREATED": "已授权", "WAIT_CHANNEL": "已保存，等接入", "REVOKED": "已撤销授权", "READ": "已读取"}
STATUS_ZH = {"NEW": "新时点", "FRESH": "最新", "STALE": "来源已更新", "UNVERIFIED": "结果未核实", "VANISHED": "已无数据"}
RULE_RES_ZH = {"MET": "达到", "NOT_MET": "未达到", "INDETERMINATE": "无法判定", "NOT_APPLICABLE": "不适用"}
SJIA_NOTE_EMPTY = "还没有任何时点"
VITALS_NOTE = "只显示读数，不算等级"
VITAL_FAMILIES = {"DEVICE_OURA", "PHONE_HEALTH", "DEVICE_SOMALOOP", "DEVICE_QKEER"}
ALL_CARDS_ZH = "全部状态卡"


def _rule_names() -> dict:
    try:
        pack = json.loads((APP / "core" / "sjia-rulepack-0.1.json").read_text("utf-8"))
        return {rid: r.get("short_zh", rid) for rid, r in pack["rules"].items()}
    except (OSError, ValueError, KeyError):
        return {}


def _loci(items) -> list:
    """rs 号清单：去空白、小写、去重、保序；有一个不是 rs 号就整份作废（返回空）。"""
    if not isinstance(items, list):
        return []
    out = []
    for x in items:
        x = str(x).strip().lower()
        if not RS_RE.match(x):
            return []
        if x not in out:
            out.append(x)
    return out


def _dt(value) -> datetime:
    """now 可以是带时区的 datetime 或 ISO 字符串（Instance.now() 的格式）。"""
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise H1Error("CLUSTER_TIME_NAIVE", "time must carry an offset")
    return dt


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


class ClusterStore:
    def __init__(self, instance_root: Path, product_config: dict, *, tz: str | None = None):
        self.root = Path(instance_root)
        self.cfg = product_config["cluster"]
        self.cards = product_config.get("cards", {})
        self.gene_zh = self.cfg.get("gene_scope_zh", "基因位点（原始基因型，未解读）")
        self.levels = self.cfg["levels"]
        self.objects = {o["id"]: o for o in self.cfg["objects"]}
        self.durations = {d["id"]: d for d in self.cfg["durations"]}
        self.rule_zh = _rule_names()
        if tz is None:
            try:
                tz = json.loads((self.root / "instance.json").read_text("utf-8")).get("tz")
            except (OSError, ValueError):
                tz = None
        self.tz = tz or "UTC"
        self.path = self.root / "cluster" / "cluster.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._open()) as conn:
            if conn.execute("SELECT count(*) FROM grant_def").fetchone()[0] == 0:
                self._seed(conn, datetime.now(timezone.utc))

    # ------------------------------------------------------------------ storage
    def _open(self):
        return open_db(self.path, SCHEMA_ID, DDL, root=self.root)

    def _seed(self, conn, now: datetime) -> None:
        """配置里的预置授权（G-001 本机通道等）在新库里登记一次，和 MockCluster 一样出现在列表里。"""
        with transaction(conn):
            for p in self.cfg.get("preset_grants", []):
                origin = "PRESET" if p.get("preset") else "EXAMPLE"
                self._insert_grant(conn, p["id"], p, now, origin, p.get("note"))
                self._record(conn, now, "CREATE", "SYSTEM", self._row(conn, p["id"]),
                             "CREATED", None, "系统预置授权 · " + self._card_zh(p["card"]))

    def _insert_grant(self, conn, gid: str, f: dict, now: datetime, origin: str, note) -> None:
        return cluster_grant_store.insert_grant(conn, gid, f, now, origin, note, self.durations, _iso)

    def _row(self, conn, gid: str):
        return cluster_grant_store.row(conn, gid)

    def _record(self, conn, now: datetime, action: str, via: str, g, outcome: str, reason, summary: str) -> None:
        if re.search(r"\d", summary):  # 摘要只用名称拼；出现数字就说明有值混进来了
            raise H1Error("CLUSTER_SUMMARY_UNSAFE", action)
        g = g or {}
        return cluster_grant_store.record(conn, now, action, via, g, outcome, reason, summary, _iso)

    # ------------------------------------------------------------------ labels
    def _chan(self, obj_id, chan_id) -> dict:
        o = self.objects.get(obj_id) or {"channels": []}
        return next((c for c in o["channels"] if c["id"] == chan_id), {})

    def _card_zh(self, card) -> str:
        if card == STATE_REPORT:
            return self.cfg.get("state_report", {}).get("zh", "状态报告")
        if card == phone_tail_auth.RESOURCE:
            return self.cfg["phone_tail"]["zh"]
        if card == GENE:
            return self.gene_zh
        return ALL_CARDS_ZH if card == "*" else self.cards.get(card, {}).get("zh", str(card))

    def _when(self, iso: str) -> str:
        local = _dt(iso).astimezone(ZoneInfo(self.tz))
        return local.strftime("%Y-%m-%d %H:%M:%S") + "（" + self.tz + "）"

    # ------------------------------------------------------------------ grants
    def _status(self, g: dict, now: datetime) -> str:
        if g["revoked_at"]:
            return "REVOKED"
        if g["expires_at"] and now >= _dt(g["expires_at"]):
            return "EXPIRED"
        return "ACTIVE" if self._chan(g["object"], g["channel"]).get("maturity") == "ready" else "WAIT_CHANNEL"

    def _public(self, g: dict, now: datetime) -> dict:
        """MockCluster 的授权形状：id object channel method level card events view duration created_at
        expires_at status (+ revoked_at preset example note)。"""
        out = {"id": g["grant_id"], "object": g["object"], "channel": g["channel"], "method": g["method"],
               "level": g["level"], "card": g["card"], "events": json.loads(g["events"]), "view": g["view"],
               "duration": g["duration"], "created_at": g["created_at"], "expires_at": g["expires_at"],
               "status": self._status(g, now)}
        if g["revoked_at"]:
            out["revoked_at"] = g["revoked_at"]
        if g["card"] == GENE:
            out["loci"] = out["events"]
        if g["origin"] == "PRESET":
            out["preset"] = True
        if g["origin"] == "EXAMPLE":
            out["example"] = True
        if g["note"]:
            out["note"] = g["note"]
        return out

    def _validate(self, f: dict) -> dict:
        def bad(field):
            raise H1Error("CLUSTER_FORM_INVALID", field)
        o = self.objects.get(f.get("object")) or bad("object")
        c = self._chan(o["id"], f.get("channel")) or bad("channel")
        f.get("method") in ("read", "push") or bad("method")
        (f["method"] == "read") == (o["form"] == "machine") or bad("method")
        order = self.levels["order"]
        f.get("level") in order or bad("level")
        order.index(f["level"]) <= order.index(c["max_level"]) or bad("level")
        (f["level"] != "data" or o["form"] == "machine") or bad("level")
        card = f.get("card")
        if card == STATE_REPORT or f.get("object") == self.cfg.get("state_report", {}).get("object", "report_phone"):
            bad("report_requires_pair_confirmation")
        phone = self.cfg.get("phone_tail", {})
        if card == phone_tail_auth.RESOURCE or f.get("object") == phone.get("object"):
            expected = {"object": phone.get("object"), "channel": phone.get("channel"), "method": "read",
                        "level": "data", "card": phone_tail_auth.RESOURCE, "events": phone.get("codes"),
                        "view": "dynamic", "duration": phone.get("duration")}
            phone and all(f.get(k) == v for k, v in expected.items()) or bad("phone_scope")
            return expected
        if card == GENE:  # 基因位点：只给机器读、只读、披露级别"数据"，可限定 rs 号
            (o["form"] == "machine" and f["method"] == "read" and f["level"] == "data") or bad("card")
            loci = f.get("loci", f.get("events", "*"))
            if loci != "*":
                loci = _loci(loci)
                (loci and len(loci) <= MAX_LOCI_GRANT) or bad("loci")
            f.get("duration") in self.durations or bad("duration")
            return {"object": o["id"], "channel": c["id"], "method": "read", "level": "data", "card": GENE,
                    "events": loci, "view": "dynamic", "duration": f["duration"]}
        (card == "*" or card in self.cards) or bad("card")
        events = f.get("events", "*")
        if events != "*":
            known = {e["id"] for k, cd in self.cards.items() if card in ("*", k) for e in cd.get("events", [])}
            (isinstance(events, list) and events and set(events) <= known) or bad("events")
        f.get("duration") in self.durations or bad("duration")
        f.get("view") in (None, "dynamic", "snapshot") or bad("view")
        return {"object": o["id"], "channel": c["id"], "method": f["method"], "level": f["level"], "card": card,
                "events": events, "view": f.get("view") or ("dynamic" if f["method"] == "read" else None),
                "duration": f["duration"]}

    @phone_lifecycle.serialized
    def create(self, form: dict, now) -> dict:
        """新建授权（七要素）。返回授权（同 find）。表单不合法 → H1Error CLUSTER_FORM_INVALID（detail=字段名）。"""
        now = _dt(now)
        f = self._validate(dict(form))
        with closing(self._open()) as conn, transaction(conn):
            nums = [int(m.group(1)) for (gid,) in conn.execute("SELECT grant_id FROM grant_def")
                    if (m := re.fullmatch(r"G-(\d+)", gid))]
            gid = "G-%03d" % (max(nums, default=0) + 1)
            self._insert_grant(conn, gid, f, now, "USER", self.cfg["phone_tail"]["purpose"] if f["card"] == phone_tail_auth.RESOURCE else None)
            g = self._row(conn, gid)
            status = self._status(g, now)
            self._record(conn, now, "CREATE", "UI", g, "WAIT_CHANNEL" if status == "WAIT_CHANNEL" else "CREATED",
                         None, "新建授权 · " + self._card_zh(f["card"]))
        return self._public(g, now)

    @phone_lifecycle.serialized
    def find(self, grant_id: str, now=None):
        now = _dt(now) if now is not None else datetime.now(timezone.utc)
        with closing(self._open()) as conn:
            g = self._row(conn, str(grant_id))
        return self._public(g, now) if g else None

    def list(self, now) -> list:
        """全部授权：新建的在前（最新的最前），系统预置 / 示例按配置顺序在后，和 MockCluster 一致。"""
        now = _dt(now)
        with phone_lifecycle.guard(self):
            rows = self._grant_rows()
        return self._project_grants(rows, now)

    def _grant_rows(self):
        with closing(self._open()) as conn:
            ids = [r[0] for r in conn.execute("SELECT grant_id FROM grant_def ORDER BY rowid")]
            rows = [self._row(conn, gid) for gid in ids]
        return rows

    def _project_grants(self, rows, now):
        user = [g for g in rows if g["origin"] == "USER"][::-1]
        seeded = [g for g in rows if g["origin"] != "USER"]
        return [self._public(g, now) for g in user + seeded]

    @phone_lifecycle.serialized
    def revoke(self, grant_id: str, now, *, via="UI") -> dict:
        """撤销 = 追加一条 REVOKED 事件。已撤销的再撤销不再写；不存在 → H1Error CLUSTER_GRANT_UNKNOWN。"""
        now = _dt(now)
        with closing(self._open()) as conn, transaction(conn):
            g = self._row(conn, str(grant_id))
            if g is None:
                raise H1Error("CLUSTER_GRANT_UNKNOWN", str(grant_id)[:40])
            if not g["revoked_at"]:
                conn.execute("INSERT INTO grant_event (grant_id, event, at) VALUES (?, 'REVOKED', ?)",
                             (g["grant_id"], _iso(now)))
                self._record(conn, now, "REVOKE", via, g, "REVOKED", None, "撤销授权 · " + self._card_zh(g["card"]))
                g["revoked_at"] = _iso(now)
        return self._public(g, now)

    def _read_denial(self, g, now):
        if g is None:
            return "NOT_FOUND"
        status = self._status(g, now)
        if status != "ACTIVE":
            return status
        return "NOT_READ" if g["method"] != "read" else None

    @phone_lifecycle.serialized
    def phone_check(self, grant_id, codes, now):
        """Same grant/status authority; exact phone-only projection, no snapshot/data writes."""
        now = _dt(now)
        with closing(self._open()) as conn:
            g = self._row(conn, str(grant_id))
        code = self._read_denial(g, now)
        phone = self.cfg.get("phone_tail", {})
        if not code:
            expected = {"card": phone_tail_auth.RESOURCE, "object": phone.get("object"),
                        "channel": phone.get("channel"), "level": "data", "view": "dynamic",
                        "duration": phone.get("duration")}
            if (not all(g.get(k) == v for k, v in expected.items()) or not g["expires_at"]
                    or codes != phone.get("codes") or json.loads(g["events"]) != codes):
                code = "OUT_OF_SCOPE"
        return code, self._public(g, now) if g else None

    @phone_lifecycle.serialized
    def create_report_grant(self, subscription_id, revision, card_ids, now):
        """Private Mac-confirmation path; never accepted by the general create form."""
        now = _dt(now)
        cfg = self.cfg.get("state_report", {})
        scope = {"schema": "STATE_REPORT_SCOPE_V1", "subscription_id": subscription_id,
                 "revision": revision, "card_ids": card_ids, "after": now.isoformat(timespec="microseconds")}
        if not self._report_scope_valid(scope) or not cfg:
            raise H1Error("CLUSTER_FORM_INVALID", "report_scope")
        f = {"object": cfg["object"], "channel": cfg["channel"], "method": "read", "level": "data",
             "card": STATE_REPORT, "events": scope, "view": "snapshot", "duration": "30d"}
        with closing(self._open()) as conn, transaction(conn):
            nums = [int(m.group(1)) for (gid,) in conn.execute("SELECT grant_id FROM grant_def")
                    if (m := re.fullmatch(r"G-(\d+)", gid))]
            gid = "G-%03d" % (max(nums, default=0) + 1)
            self._insert_grant(conn, gid, f, now, "USER", cfg.get("purpose"))
            g = self._row(conn, gid)
            self._record(conn, now, "CREATE", "UI", g, "CREATED", None, "新建授权 · 状态报告")
        return self._public(g, now)

    @staticmethod
    def _report_scope_valid(scope):
        if not isinstance(scope, dict) or set(scope) != {"schema", "subscription_id", "revision", "card_ids", "after"}:
            return False
        ids = scope.get("card_ids")
        if (scope.get("schema") != "STATE_REPORT_SCOPE_V1"
                or not isinstance(scope.get("subscription_id"), str)
                or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", scope["subscription_id"])
                or type(scope.get("revision")) is not int or scope["revision"] < 1
                or not isinstance(ids, list) or not 1 <= len(ids) <= 32
                or not all(isinstance(i, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", i) for i in ids)
                or len(set(ids)) != len(ids)):
            return False
        try:
            _dt(scope["after"])
        except (ValueError, TypeError, H1Error):
            return False
        return True

    def check_report_grant(self, grant_id, now):
        """Report-only authority: the ordinary card/MCP projection never consumes this grant."""
        now = _dt(now)
        with closing(self._open()) as conn:
            g = self._row(conn, str(grant_id))
        code = self._read_denial(g, now)
        cfg = self.cfg.get("state_report", {})
        if not code:
            expected = {"object": cfg.get("object"), "channel": cfg.get("channel"), "method": "read",
                        "card": STATE_REPORT, "level": "data", "view": "snapshot", "duration": "30d"}
            try:
                scope = json.loads(g["events"])
                valid = (all(g.get(k) == v for k, v in expected.items()) and g["expires_at"]
                         and self._report_scope_valid(scope)
                         and 0 <= (_dt(scope["after"]) - _dt(g["created_at"])).total_seconds() < 1)
            except (ValueError, TypeError, KeyError):
                valid = False
            if not valid:
                code = "OUT_OF_SCOPE"
        return code, self._public(g, now) if g else None

    # ------------------------------------------------------------------ read (本机 MCP 只读)
    @phone_lifecycle.serialized
    def read(self, grant_id: str, snapshot: dict, now, via: str = "MCP", *, rsids=None, gene_path=None) -> dict:
        """READ → {outcome:'READ', grant, level, at, payload}；
        否则 → {outcome:'DENIED', grant, at, code, reason(中文)}。两种都写一条记录。
        rsids：读基因位点时要读的 rs 号（基因授权限定了位点、又没给 rsids 时，读授权里的全部位点）。"""
        now = _dt(now)
        detail = None
        with closing(self._open()) as conn, transaction(conn):
            g = self._row(conn, str(grant_id))
            code, card = self._read_denial(g, now), None
            if not code:
                if g["card"] in (phone_tail_auth.RESOURCE, STATE_REPORT):
                    code = "OUT_OF_SCOPE"  # Phone grant never opens the ordinary MCP/card projection.
                elif g["card"] == GENE or rsids is not None:
                    card = GENE
                    code, want, detail = self._gene_check(g, rsids)
                else:
                    have = self._cards_in(snapshot)
                    card = next((c for c in have if g["card"] in ("*", c)), None)
                    code = None if card else "OUT_OF_SCOPE"
            label = self._card_zh(card or (g or {}).get("card", "*"))
            if code:
                self._record(conn, now, "READ", via, g, "DENIED", code,
                             ("读取 " + label) if g else "读取（授权不存在）")
                if card == GENE or (g or {}).get("card") == GENE:
                    self._gene_log(now, grant_id, via, rsids, "DENIED", code, [])
                out = {"outcome": "DENIED", "grant": str(grant_id), "at": _iso(now), "code": code,
                       "reason": DENY_ZH[code]}
                if detail:
                    out["detail"] = detail
                return out
            if card == GENE:
                payload = self.project_gene(want, gene_path)
                self._gene_log(now, g["grant_id"], via, want, "READ", None,
                               sorted({x["rsid"] for x in payload["loci"]}))
            else:
                payload = self.project(g["level"], card, snapshot)
            self._record(conn, now, "READ", via, g, "READ", None, "读取 " + label)
        return {"outcome": "READ", "grant": g["grant_id"], "level": g["level"], "at": _iso(now), "payload": payload}

    def _gene_check(self, g: dict, rsids):
        """→ (拒绝代码或 None, 要读的 rs 号, 给调用方的细节)。"""
        if g["card"] != GENE:
            return "NOT_GENE", None, None
        scope = json.loads(g["events"])
        if rsids is None:
            if scope == "*":
                return "LOCI_REQUIRED", None, None
            rsids = scope
        if not isinstance(rsids, list) or not all(isinstance(x, str) for x in rsids):
            return "LOCI_INVALID", None, None
        bad = [x for x in rsids if not RS_RE.match(x.strip().lower())]
        if bad or not rsids:
            return "LOCI_INVALID", None, {"not_rs": bad[:20]}
        want = _loci(rsids)
        if len(want) > MAX_LOCI_READ:
            return "LOCI_TOO_MANY", None, None
        if scope != "*":
            outside = [x for x in want if x not in scope]
            if outside:
                return "LOCI_OUT_OF_SCOPE", None, {"outside": outside[:50]}
        return None, want, None

    def project_gene(self, want: list, gene_path) -> dict:
        rows, missing = [], []
        for rs in want:
            hits = gene_db.lookup(Path(gene_path), rsid=rs) if gene_path else []
            if not hits:
                missing.append(rs)
            for h in hits:
                rows.append({"rsid": h["rsid"], "chrom": h["chrom"], "pos": h["pos"], "genotype": h["genotype"],
                             "build": h["build"] or "未注明", "file": h["file_name"], "file_sha": h["file_sha"][:12]})
        return {"scope": self.gene_zh, "disclosure": self.levels["data"]["zh"], "loci": rows,
                "not_found": "、".join(missing), "note": GENE_NOTE}

    def _gene_log(self, now, grant_id, via, rsids, outcome, code, found) -> None:
        rec = {"id": uuid.uuid4().hex[:12], "at": _iso(now), "grant": str(grant_id), "via": via, "outcome": outcome,
               "code": code, "rsids": rsids if isinstance(rsids, list) else None, "found": found}
        with open(self.root / "cluster" / "gene_reads.jsonl", "a", encoding="utf-8") as handle:
            handle.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def gene_reads(self) -> list:
        path = self.root / "cluster" / "gene_reads.jsonl"
        if not path.exists():
            return []
        return [json.loads(x) for x in path.read_text("utf-8").splitlines() if x.strip()]

    @staticmethod
    def _cards_in(snapshot: dict) -> list:
        cards = (snapshot.get("instance") or {}).get("cards")
        if cards is None:
            cards = (["SJIA_FOCUS"] if snapshot.get("card") else []) + (["VITALS"] if "vitals" in snapshot else [])
        return list(cards)

    def project(self, level: str, card: str, snapshot: dict) -> dict:
        """最小披露投影。每升一级只多给下一级说明里写的内容。"""
        if level == "signal":
            return {"disclosure": self.levels["signal"]["zh"], "message": self.levels["signal"]["template"]}
        lv = self.levels[level]["zh"]
        if card == "VITALS":
            items = []
            for x in (snapshot.get("vitals") or {}).get("items", []):
                if x.get("family") not in VITAL_FAMILIES:  # 我的体征只含设备读数；化验、症状不在这个范围里
                    continue
                item = {"metric": x.get("label_zh") or x.get("code"), "source": x.get("source_kind"),
                        "at": x.get("observed_at") or x.get("observed_date"), "fresh": x.get("fresh")}
                if level in ("basis", "data"):
                    item.update(value=x.get("value"), unit=x.get("unit"))
                items.append(item)
            return {"card": self._card_zh("VITALS"), "disclosure": lv, "items": items, "note": VITALS_NOTE}
        return self._project_sjia(level, lv, snapshot)

    def _project_sjia(self, level: str, lv: str, s: dict) -> dict:
        zh = self._card_zh("SJIA_FOCUS")
        cur = s.get("current")
        if not cur:
            return {"card": zh, "disclosure": lv, "note": SJIA_NOTE_EMPTY}
        tp = next((t for t in s.get("timepoints", []) if t.get("tp") == cur["tp"]), {}) or {}
        drivers = (tp.get("result") or {}).get("drivers", [])
        timeline = [o for o in s.get("timeline", []) if o.get("tp") == cur["tp"]]
        labels = {o["code"]: o.get("label_zh") or o["code"] for o in s.get("timeline", []) if o.get("code")}
        dyn = [d for d in drivers if d.get("kind") == "DYNAMIC"]
        out = {"card": zh, "disclosure": lv, "tp": cur["tp"], "level": cur.get("level_zh"),
               "status": STATUS_ZH.get(tp.get("status"), "")}
        out["changes"] = [{"metric": labels.get(d["code"], d["code"]),
                           "direction": change_word(d.get("direction"), d.get("measure"))} for d in dyn]
        alert = next((a for a in reversed(s.get("alerts") or []) if a.get("tp") == cur["tp"]), None)
        if alert:
            out["alert"] = alert["title"] + "\n" + alert["body"]
        if level in ("basis", "data"):
            for c, d in zip(out["changes"], dyn):
                c["change"] = d.get("change")
            out["rules"] = [{"rule": self.rule_zh.get(d["rule"], d["rule"]),
                             "result": RULE_RES_ZH.get(d.get("result"), d.get("result"))}
                            for d in drivers if d.get("kind") == "RULE"]
            driven = {d["code"] for d in dyn}
            out["values"] = [{"metric": o.get("label_zh") or o["code"],
                              "value": (o.get("comparator") or "") + str(o.get("value_raw")),
                              "unit": o.get("unit_raw") or "", "tp": o["tp"]}
                             for o in timeline if level == "data" or o["code"] in driven]
        out["disclaimer"] = s.get("disclaimer", "")
        if (s.get("instance") or {}).get("kind") == "DEMO":
            out["nature"] = "合成"
        return out

    # ------------------------------------------------------------------ records
    def records(self, snapshot: dict | None = None, *, egress_only: bool = False) -> list:
        """授权记录，最新在前。形状同 MockCluster.records()：grant when obj how level summary result ok，
        另加 id at action via outcome reason（代码）egress（是否出域：读取 / 推送）。
        给 snapshot 时，把星轨 alerts[].deliveries（预置授权的推送，站内横幅除外）一并列出，同原型。"""
        with phone_lifecycle.guard(self):
            rows, phone_rows = self._record_rows()
        return self._project_records(rows, phone_rows, snapshot, egress_only=egress_only)

    def _record_rows(self):
        with closing(self._open()) as conn:
            cur = conn.execute("SELECT * FROM access_record ORDER BY id DESC")
            cols = [c[0] for c in cur.description]
            rows = [dict(zip(cols, r)) for r in cur]
        return rows, phone_tail_auth.events(self)

    def _project_records(self, rows, phone_rows, snapshot=None, *, egress_only=False, auxiliary=None):
        out = []
        for r in rows:
            o = self.objects.get(r["object"]) or {}
            c = self._chan(r["object"], r["channel"])
            if r["outcome"] == "DENIED":
                result = "已拒绝（授权" + DENY_ZH.get(r["reason"], r["reason"]) + "）"
            else:
                result = RESULT_ZH[r["outcome"]]
            action_zh = {"CREATE": "新建授权", "REVOKE": "撤销授权"}.get(r["action"], "读取")
            how = action_zh + " · " + (c.get("zh") or r["via"])
            out.append({"id": r["id"], "grant": r["grant_id"], "at": r["at"], "when": self._when(r["at"]),
                        "obj": o.get("zh", "—"), "how": how,
                        "level": self.levels[r["level"]]["zh"] if r["level"] in self.levels else "—",
                        "summary": r["summary"], "result": result, "ok": r["outcome"] != "DENIED",
                        "action": r["action"], "via": r["via"], "outcome": r["outcome"], "reason": r["reason"],
                        "egress": r["action"] == "READ"})
        import share  # noqa: PLC0415  授权图片（产品负责人 2026-10-14）：记在 cluster/shares.jsonl，这里并进来
        out += share.records(self.root, self._when) if auxiliary is None else auxiliary[0]
        out += phone_tail_auth.records(self, phone_rows)
        import report_phone
        out += report_phone.audit_records(self) if auxiliary is None else auxiliary[1]
        if snapshot:
            out += self._push_records(snapshot)
        out.sort(key=lambda x: _dt(x["at"]).astimezone(timezone.utc), reverse=True)
        return [r for r in out if r["egress"]] if egress_only else out


    def authorization_view(self, snapshot, now):
        """One P collection for a composite response; all projection follows release."""
        now = _dt(now)
        captured = getattr(snapshot, "_authorization_capture", None)
        if captured is not None and captured[0] == id(self):
            rows, phone_rows, grants, auxiliary = captured[1:]
            if isinstance(auxiliary, Exception):
                raise auxiliary
            return self._project_records(rows, phone_rows, snapshot, auxiliary=auxiliary), self._project_grants(grants, now)
        with phone_lifecycle.guard(self):
            rows, phone_rows = self._record_rows()
            grants = self._grant_rows()
        return self._project_records(rows, phone_rows, snapshot), self._project_grants(grants, now)

    def capture_authorization_locked(self):
        """Caller holds A and P before any SQL. Display only, never a permission."""
        import share, report_phone
        rows, phone_rows = self._record_rows()
        grants = self._grant_rows()
        try:
            auxiliary = (share.records(self.root, self._when), report_phone.audit_records(self))
        except Exception as error:
            # Unrelated home snapshots did not previously parse these records.
            # Defer that same display error until the authorization view is used.
            auxiliary = error
        return id(self), rows, phone_rows, grants, auxiliary

    def _push_records(self, s: dict) -> list:
        preset = next((p for p in self.cfg.get("preset_grants", []) if p.get("preset")), None)
        if preset is None:
            return []
        chan_zh = {"BANNER": "横幅", "MACOS": "Mac 通知", "SOMALOOP": "手环", "TEST": "测试通道"}
        out_zh = {"SENT": "已送达", "FAILED": "未送达"}
        me = self.objects.get(preset["object"], {}).get("zh", "")
        lv = self.levels[preset["level"]]["zh"]
        out = []
        for a in s.get("alerts") or []:
            base = {"grant": preset["id"], "at": a["created_at"], "when": self._when(a["created_at"]), "obj": me,
                    "level": lv, "summary": "推送 " + a["title"] + " · " + a["tp"], "action": "PUSH",
                    "via": "STARTRACK", "reason": None, "egress": True, "id": None}
            for x in a.get("deliveries") or []:
                if x["channel"] == "BANNER":  # 站内横幅不算出域
                    continue
                out.append(dict(base, how="推送 · " + chan_zh.get(x["channel"], x["channel"]),
                                result=out_zh.get(x["outcome"], x["outcome"]), ok=x["outcome"] == "SENT",
                                outcome=x["outcome"]))
            for x in a.get("pending_channels") or []:
                ch = x if isinstance(x, str) else x.get("channel")
                if ch == "BANNER":
                    continue
                out.append(dict(base, how="推送 · " + chan_zh.get(ch, ch), result="等待中", ok=False,
                                outcome="PENDING"))
        for ev in s.get("device_events") or []:  # "设备断开"通知：星轨照发，星簇补记（DC-22）
            base = {"grant": preset["id"], "at": ev["at"], "when": self._when(ev["at"]), "obj": me, "level": lv,
                    "summary": "推送 " + ev["title"], "action": "PUSH", "via": "STARTRACK", "reason": None,
                    "egress": True, "id": None}
            for x in ev.get("deliveries") or []:
                if x["channel"] == "BANNER":
                    continue
                out.append(dict(base, how="推送 · " + chan_zh.get(x["channel"], x["channel"]),
                                result=out_zh.get(x["outcome"], x["outcome"]), ok=x["outcome"] == "SENT",
                                outcome=x["outcome"]))
        return out
