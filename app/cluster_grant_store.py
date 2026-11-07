"""Grant SQL delegates; caller owns the connection, transaction and locks."""
import json
from datetime import timedelta


def insert_grant(conn, gid, f, now, origin, note, durations, iso):
    hours = durations[f["duration"]].get("hours")
    expires = iso(now + timedelta(hours=hours)) if hours else None
    conn.execute("INSERT INTO grant_def VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (gid, f["object"], f["channel"], f["method"], f["level"], f["card"],
                  json.dumps(f.get("events", "*"), ensure_ascii=False), f.get("view"), f["duration"],
                  iso(now), expires, origin, note))
    conn.execute("INSERT INTO grant_event (grant_id, event, at) VALUES (?, 'CREATED', ?)", (gid, iso(now)))


def row(conn, gid):
    cur = conn.execute("SELECT * FROM grant_def WHERE grant_id = ?", (gid,))
    row = cur.fetchone()
    if row is None:
        return None
    g = dict(zip([c[0] for c in cur.description], row))
    rev = conn.execute("SELECT at FROM grant_event WHERE grant_id = ? AND event = 'REVOKED'", (gid,)).fetchone()
    g["revoked_at"] = rev[0] if rev else None
    return g


def record(conn, now, action, via, g, outcome, reason, summary, iso):
    conn.execute("INSERT INTO access_record (at, grant_id, action, via, object, channel, method, level, card, "
                 "outcome, reason, summary) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (iso(now), g.get("grant_id"), action, via, g.get("object"), g.get("channel"),
                  g.get("method"), g.get("level"), g.get("card"), outcome, reason, summary))
