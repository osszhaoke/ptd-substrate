"""星灵本地长期记忆（STARSOUL-LOCAL-MEMORY-DEMO-R01，产品负责人 2026-10-14 12:48）。

- 独立的 SQLite 文件 <实例>/starling/memory.db，和星炬 / 星轨 / 星簇的库完全分开；不改任何已有库。
- 只有用户点了“确认记住”的句子才写进来（remember）；可以更正（correct：新版本替换旧版本，旧版本不再参与检索）、
  忘记（forget：整条版本链物理删除，secure_delete 覆写，只留内容指纹和删除时间作凭证，可核对删干净了）。
- 主体隔离：每条记忆带 subject_id，所有读写都按 subject_id 过滤；换一个 subject_id 什么都看不到。
- 每条带来源（谁在什么界面确认的）和创建时间。
- 检索：优先用本机 Embedding（另起一个 llama-server --embeddings，只连 127.0.0.1）+ sqlite-memory 的余弦计算；
  Embedding 模型不在或没起来，就退回中文双字匹配，并照实标出用的是哪种。检索失败就说失败，不编。
- 星灵不经过这里拿任何 PTDS 数据；记忆里不许有健康数值（和星灵的 HR-42 一致）。
- 所有出站请求只许 127.0.0.1 / localhost，每次都记在 <实例>/starling/memory_net.log。
- 开关：app/config.json 里 "starling_memory": {"enabled": false} 就整块关掉。
"""
from __future__ import annotations

from contextlib import closing

import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent / "third_party" / "sqlite_memory"))
import sqlite_memory  # noqa: E402  MIT，原文件不改；只用它的余弦

import starling  # noqa: E402

LOCK = threading.Lock()
SUBJECT = re.compile(r"^[A-Za-z0-9_\-]{1,32}$")
MAX_TEXT = 200
REMEMBER = re.compile(r"^\s*(?:请|帮我|麻烦)?\s*(?:你)?\s*(?:记住|记下|记一下|帮我记)[：:，,。\s]*(.+?)\s*$", re.S)
LOOPBACK = {"127.0.0.1", "localhost", "::1"}
DDL = """
CREATE TABLE IF NOT EXISTS memory (
  mem_id TEXT PRIMARY KEY, chain_id TEXT NOT NULL, subject_id TEXT NOT NULL, version INTEGER NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('ACTIVE','SUPERSEDED')), text TEXT NOT NULL, source TEXT NOT NULL,
  created_at TEXT NOT NULL, content_sha TEXT NOT NULL, method TEXT NOT NULL, embedding TEXT);
CREATE INDEX IF NOT EXISTS memory_subject ON memory (subject_id, status);
CREATE TABLE IF NOT EXISTS tombstone (
  chain_id TEXT NOT NULL, subject_id TEXT NOT NULL, content_shas TEXT NOT NULL, versions INTEGER NOT NULL, deleted_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS event (
  id INTEGER PRIMARY KEY, subject_id TEXT NOT NULL, op TEXT NOT NULL, chain_id TEXT, at TEXT NOT NULL, detail TEXT);
"""


class MemoryError_(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(code)
        self.code, self.detail = code, detail


def enabled(config: dict) -> bool:
    return bool((config or {}).get("starling_memory", {}).get("enabled", True))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# ----------------------------------------------------------------------------- 出站：只许本机，每次记日志

class Net:
    def __init__(self, log: Path):
        self.log = log

    def post(self, url: str, body: dict, timeout: float = 30) -> dict:
        host = urlparse(url).hostname or ""
        ok = host in LOOPBACK
        self.log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "host": host, "path": urlparse(url).path,
                                 "allowed": ok}, ensure_ascii=False) + "\n")
        if not ok:
            raise MemoryError_("EGRESS_BLOCKED", host)
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())


# ----------------------------------------------------------------------------- 本机 Embedding（替换 sqlite-memory 写死的 Ollama 调用）

class Embedder:
    """另起一个 llama-server --embeddings（默认端口 8788），只连 127.0.0.1。Qwen 那个服务不动。"""

    def __init__(self, cfg: dict, net: Net):
        self.cfg = cfg or {}
        self.port = int(self.cfg.get("embed_port", 8788))
        self.base = f"http://127.0.0.1:{self.port}"
        self.model = self.cfg.get("embed_model") or ""
        self.net = net
        self.proc = None

    def available(self) -> bool:
        return bool(self.model) and Path(self.model).expanduser().exists()

    def healthy(self) -> bool:
        try:
            with urllib.request.urlopen(self.base + "/health", timeout=2) as r:
                return r.status == 200
        except OSError:
            return False

    def ensure(self) -> bool:
        if self.healthy():
            return True
        binary = shutil.which(self.cfg.get("server", "llama-server")) or self.cfg.get("server")
        if not self.available() or not binary or not Path(binary).exists():
            return False
        if self.proc is None or self.proc.poll() is not None:
            log = open(Path(self.cfg.get("embed_log", "~/.ptds/llama-embed.log")).expanduser(), "ab")
            self.proc = subprocess.Popen([binary, "-m", str(Path(self.model).expanduser()), "--host", "127.0.0.1", "--port", str(self.port),
                                          "--embeddings", "-c", "2048", "-ngl", "99"], stdout=log, stderr=log)
        for _ in range(60):
            if self.healthy():
                return True
            time.sleep(1)
        return False

    def embed(self, text: str) -> list:
        doc = self.net.post(self.base + "/v1/embeddings", {"input": text, "model": Path(self.model).name or "embed"})
        return [float(x) for x in doc["data"][0]["embedding"]]


def _grams(text: str) -> set:
    t = re.sub(r"[\s，。、；：！？,.;:!?“”\"'（）()]+", "", text.lower())
    return {t[i:i + 2] for i in range(len(t) - 1)} or ({t} if t else set())


def _bigram(q: str, text: str) -> float:
    """问题里的双字有多少出现在记忆里；少于两个相同的双字就算 0（一个“什么”不算想起来了）。"""
    a, b = _grams(q), _grams(text)
    same = len(a & b)
    return same / len(a) if a and same >= 2 else 0.0


# ----------------------------------------------------------------------------- 记忆库

class Store:
    def __init__(self, root: Path, cfg: dict):
        self.root = Path(root)
        self.path = self.root / "starling" / "memory.db"
        self.net = Net(self.root / "starling" / "memory_net.log")
        self.emb = Embedder(cfg, self.net)
        self.cfg = cfg or {}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._open()) as c, c:
            c.executescript(DDL)

    def _open(self):
        c = sqlite3.connect(self.path)
        try:
            c.execute("PRAGMA secure_delete = ON")  # 删除时覆写页面，文件里不留原文
        except BaseException:
            try:
                c.close()
            except Exception:
                pass  # Preserve the setup error if cleanup also fails.
            raise
        return c

    def _subject(self, s) -> str:
        s = str(s or "")
        if not SUBJECT.fullmatch(s):
            raise MemoryError_("SUBJECT_INVALID", "主体编号只能用字母、数字、- 和 _，1～32 个字符")
        return s

    def _text(self, t) -> str:
        t = re.sub(r"\s+", " ", str(t or "")).strip()
        if not 2 <= len(t) <= MAX_TEXT:
            raise MemoryError_("TEXT_INVALID", f"要记的话 2～{MAX_TEXT} 个字")
        try:
            starling.check_context([t], set())  # 和星灵一样：不碰健康数值（日期、次数这类引用可以）
        except starling.RawValueInContext:
            raise MemoryError_("HEALTH_VALUE", "要记的话里有数值；星灵不接触健康数值，请换成不带数值的说法") from None
        return t

    def _vector(self, text: str):
        try:
            if self.emb.ensure():
                return "EMBED", self.emb.embed(text)
        except (OSError, ValueError, KeyError, MemoryError_):
            pass
        return "BIGRAM", None

    def _event(self, c, subject, op, chain, now, detail=""):
        c.execute("INSERT INTO event (subject_id, op, chain_id, at, detail) VALUES (?, ?, ?, ?, ?)", (subject, op, chain, now, detail))

    def remember(self, subject, text, source, now) -> dict:
        subject, text = self._subject(subject), self._text(text)
        method, vec = self._vector(text)
        mid = "M-" + uuid.uuid4().hex[:12]
        with LOCK, closing(self._open()) as c, c:
            c.execute("INSERT INTO memory VALUES (?, ?, ?, 1, 'ACTIVE', ?, ?, ?, ?, ?, ?)",
                      (mid, mid, subject, text, str(source or "")[:60], now, _sha(text), method, json.dumps(vec) if vec else None))
            self._event(c, subject, "REMEMBER", mid, now, method)
        return self.get(subject, mid)

    def correct(self, subject, chain_id, text, source, now) -> dict:
        subject, text = self._subject(subject), self._text(text)
        method, vec = self._vector(text)
        with LOCK, closing(self._open()) as c, c:
            cur = c.execute("SELECT version FROM memory WHERE subject_id = ? AND chain_id = ? AND status = 'ACTIVE'", (subject, chain_id)).fetchone()
            if cur is None:
                raise MemoryError_("MEMORY_UNKNOWN", chain_id)  # 别的主体的记忆也是“不存在”
            c.execute("UPDATE memory SET status = 'SUPERSEDED' WHERE subject_id = ? AND chain_id = ?", (subject, chain_id))
            mid = "M-" + uuid.uuid4().hex[:12]
            c.execute("INSERT INTO memory VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?, ?, ?, ?, ?)",
                      (mid, chain_id, subject, cur[0] + 1, text, str(source or "")[:60], now, _sha(text), method, json.dumps(vec) if vec else None))
            self._event(c, subject, "CORRECT", chain_id, now, f"v{cur[0] + 1}")
        return self.get(subject, chain_id)

    def forget(self, subject, chain_id, now) -> dict:
        subject = self._subject(subject)
        with LOCK, closing(self._open()) as c, c:
            rows = c.execute("SELECT content_sha, text FROM memory WHERE subject_id = ? AND chain_id = ?", (subject, chain_id)).fetchall()
            if not rows:
                raise MemoryError_("MEMORY_UNKNOWN", chain_id)
            c.execute("DELETE FROM memory WHERE subject_id = ? AND chain_id = ?", (subject, chain_id))
            shas = sorted({r[0] for r in rows})
            c.execute("INSERT INTO tombstone VALUES (?, ?, ?, ?, ?)", (chain_id, subject, json.dumps(shas), len(rows), now))
            self._event(c, subject, "FORGET", chain_id, now, f"{len(rows)} 个版本")
        texts = [r[1] for r in rows]
        with closing(self._open()) as c2:
            c2.execute("VACUUM")
        return dict(self.verify_deleted(subject, chain_id, texts), chain_id=chain_id, versions=len(rows))

    def verify_deleted(self, subject, chain_id, texts=None) -> dict:
        """删除凭证：库里按编号、按内容指纹都查不到；原文在数据库文件的字节里也找不到。"""
        with closing(self._open()) as c, c:
            t = c.execute("SELECT content_shas, deleted_at FROM tombstone WHERE subject_id = ? AND chain_id = ?", (subject, chain_id)).fetchone()
            if t is None:
                return {"deleted": False, "why": "没有删除记录"}
            shas = json.loads(t[0])
            left = c.execute("SELECT count(*) FROM memory WHERE chain_id = ? OR content_sha IN (%s)" % ",".join("?" * len(shas)),
                             [chain_id] + shas).fetchone()[0]
        raw = self.path.read_bytes()
        in_file = any(x.encode() in raw for x in texts or [])
        return {"deleted": left == 0 and not in_file, "rows_left": left, "text_in_file": in_file, "deleted_at": t[1],
                "content_shas": [s[:12] for s in shas]}

    def get(self, subject, chain_id) -> dict:
        with closing(self._open()) as c, c:
            r = c.execute("SELECT mem_id, chain_id, version, text, source, created_at, method FROM memory "
                          "WHERE subject_id = ? AND chain_id = ? AND status = 'ACTIVE'", (subject, chain_id)).fetchone()
        if r is None:
            raise MemoryError_("MEMORY_UNKNOWN", chain_id)
        return dict(zip(("mem_id", "chain_id", "version", "text", "source", "created_at", "method"), r))

    def list(self, subject) -> dict:
        subject = self._subject(subject)
        with closing(self._open()) as c, c:
            rows = c.execute("SELECT mem_id, chain_id, version, text, source, created_at, method FROM memory "
                             "WHERE subject_id = ? AND status = 'ACTIVE' ORDER BY created_at DESC", (subject,)).fetchall()
            gone = c.execute("SELECT chain_id, versions, deleted_at FROM tombstone WHERE subject_id = ? ORDER BY deleted_at DESC", (subject,)).fetchall()
        return {"items": [dict(zip(("mem_id", "chain_id", "version", "text", "source", "created_at", "method"), r)) for r in rows],
                "deleted": [dict(zip(("chain_id", "versions", "deleted_at"), r)) for r in gone]}

    def recall(self, subject, query, k: int = 3) -> dict:
        """→ {state: ok / empty / failed, method, hits[]}。失败就说失败，不猜。"""
        try:
            subject = self._subject(subject)
            with closing(self._open()) as c, c:
                rows = c.execute("SELECT chain_id, text, created_at, method, embedding FROM memory WHERE subject_id = ? AND status = 'ACTIVE'",
                                 (subject,)).fetchall()
        except (sqlite3.Error, MemoryError_) as e:
            return {"state": "failed", "why": type(e).__name__, "hits": [], "method": ""}
        if not rows:
            return {"state": "empty", "hits": [], "method": ""}
        qv, method = None, "BIGRAM"
        if any(r[4] for r in rows):
            try:
                if self.emb.ensure():
                    qv, method = self.emb.embed(query), "EMBED"
            except (OSError, ValueError, KeyError, MemoryError_):
                qv = None
        floor = float(self.cfg.get("embed_min_score", 0.55))
        bfloor = float(self.cfg.get("bigram_min_score", 0.15))
        hits = []
        for chain, text, at, m, emb in rows:
            if qv is not None and emb:
                s, how, ok = sqlite_memory._cosine(qv, json.loads(emb)), "EMBED", None
                ok = s >= floor
            else:
                s, how = _bigram(query, text), "BIGRAM"
                ok = s >= bfloor
            if ok:
                hits.append({"chain_id": chain, "text": text, "created_at": at, "score": round(s, 3), "method": how})
        hits.sort(key=lambda h: -h["score"])
        return {"state": "ok" if hits else "empty", "hits": hits[:k], "method": method}


def proposal(question: str) -> str | None:
    """“请记住……” → 要记的那句话（程序截取，不经过模型）。"""
    m = REMEMBER.match(question or "")
    return m.group(1).strip("。 ") if m else None
