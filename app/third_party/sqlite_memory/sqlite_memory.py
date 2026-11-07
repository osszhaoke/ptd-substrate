"""
sqlite-memory — persistent long-term memory for local LLMs, in one file.

LLMs forget everything between messages and across sessions. This gives them a
durable memory: conversation turns (or arbitrary facts) are embedded with a
local Ollama model and stored in a single SQLite file. Before answering, you
`recall()` the most relevant memories and inject them into the prompt; after
each exchange you `remember()` what was said. The memory survives restarts —
it's just a `.db` file.

No vector database, no server, no framework — standard library only.

API:
    m = Memory("memory.db")
    m.remember("The user's dog is called Pluto", role="fact", tags="pets")
    hits = m.recall("what is the pet's name?", k=5)     # semantic search
    m.recent(10)                                         # last N memories
    m.forget(id=3)          # or forget(tag="pets") / forget(before_ts=...)
"""

import json
import math
import os
import sqlite3
import time
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")


def _embed(text):
    body = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        OLLAMA_URL + "/api/embeddings", body, {"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())["embedding"]


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


class Memory:
    def __init__(self, db_path="memory.db"):
        self.db = sqlite3.connect(db_path)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS memories ("
            "id INTEGER PRIMARY KEY, ts REAL, role TEXT, text TEXT, "
            "tags TEXT, embedding TEXT)"
        )
        self.db.commit()

    def remember(self, text, role="note", tags=None, ts=None):
        """Store one memory (a fact, a chat turn, anything). Returns its id."""
        emb = _embed(text)
        cur = self.db.execute(
            "INSERT INTO memories (ts, role, text, tags, embedding) VALUES (?,?,?,?,?)",
            (ts or time.time(), role, text, tags or "", json.dumps(emb)),
        )
        self.db.commit()
        return cur.lastrowid

    def recall(self, query, k=5, min_score=0.0):
        """Return the k memories most semantically similar to `query`."""
        q = _embed(query)
        rows = self.db.execute(
            "SELECT id, ts, role, text, tags, embedding FROM memories"
        ).fetchall()
        scored = []
        for _id, ts, role, text, tags, emb in rows:
            s = _cosine(q, json.loads(emb))
            if s >= min_score:
                scored.append((s, _id, ts, role, text, tags))
        scored.sort(reverse=True)
        return [
            {"id": i, "score": round(s, 3), "ts": ts, "role": r, "text": t, "tags": g}
            for s, i, ts, r, t, g in scored[:k]
        ]

    def recent(self, n=10):
        rows = self.db.execute(
            "SELECT id, ts, role, text, tags FROM memories ORDER BY ts DESC LIMIT ?",
            (n,),
        ).fetchall()
        return [
            {"id": i, "ts": ts, "role": r, "text": t, "tags": g}
            for i, ts, r, t, g in rows
        ]

    def forget(self, id=None, tag=None, before_ts=None):
        """Delete memories by id, by tag, or older than a timestamp. Returns count."""
        if id is not None:
            cur = self.db.execute("DELETE FROM memories WHERE id=?", (id,))
        elif tag is not None:
            cur = self.db.execute("DELETE FROM memories WHERE tags LIKE ?", (f"%{tag}%",))
        elif before_ts is not None:
            cur = self.db.execute("DELETE FROM memories WHERE ts < ?", (before_ts,))
        else:
            return 0
        self.db.commit()
        return cur.rowcount

    def count(self):
        return self.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
