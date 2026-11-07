"""「我的体征」进星轨账本（产品负责人 2026-10-15 批准 r63）：星痕「状态记录」要能看到个人基座的计算。

我的体征卡本来每次打开现算（core/vitals.vitals_state：每项取最近一条读数），不留痕。这里在每次同步后，把卡上实际显示的那组读数
（绑定了的来源才算）按本地日期记一次：一个 run、一个 run_tp（结果 = 每项的值、单位、观测时间、观测编号@版本）、run_input 钉住输入。
同一天输入和上次一样就不记；只追加，不改表结构。以前没留下结果的时刻不补（没有当时的结果可依）。
"""
from __future__ import annotations

import compute_snapshot
from h1_common import canonical_bytes, canonical_json, sha256_hex
from sqlite_util import transaction
from cards import latest_results
from engines import _nofloat

ENGINE = "vitals/0.1"
CARD_ID = "VITALS"


def definition() -> dict:
    return {"kind": "VITALS_STATE", "engine_version": ENGINE, "card_id": CARD_ID, "name": "我的体征",
            "method": "每项取最近一条在用的读数；只描述，不定级、不提醒"}


def apply_result(track, d, def_id, day, now, it, inputs, res):
    text = canonical_json(_nofloat(res))
    track.execute("INSERT OR IGNORE INTO card_def (card_def_id, card_id, definition, registered_at) VALUES (?, ?, ?, ?)",
                  (def_id, CARD_ID, canonical_json(d), now))
    run_id = track.execute("INSERT INTO run (card_def_id, trigger, started_at) VALUES (?, ?, ?)",
                           (def_id, "SYNC" if it is None else "AUTO_UPDATE", now)).lastrowid
    track.execute("INSERT INTO run_tp (run_id, tp_date, status, level, result, result_sha256) VALUES (?, ?, 'EVALUATED', 'NONE', ?, ?)",
                  (run_id, day, text, sha256_hex(text.encode())))
    track.executemany("INSERT INTO run_input (run_id, tp_date, observation_id, revision, role) VALUES (?, ?, ?, ?, ?)",
                      [(run_id, day, oid, rev, role) for oid, rev, role in sorted(inputs)])
    return run_id


def record(track, ctx, items: list, *, day: str, now: str, computed=None, guard=None) -> dict | None:
    """items：卡上显示的读数（vitals_state 的 items，已按绑定来源过滤）。输入变了才记一条，返回 {run_id, tp, n}；没变返回 None。"""
    if not items:
        return None
    d = definition()
    def_id = sha256_hex(canonical_bytes(d))
    inputs = {(i["observation_id"], i["revision"], "TP") for i in items}  # 账本的 role 只有 TP / HISTORY：卡上显示的读数都是这个时点的输入
    with transaction(track):
        if guard is not None:
            guard.before(track)
        it = latest_results(track, def_id).get(day)
        if it is not None and it["status"] == "EVALUATED" and it["inputs"] == inputs:
            if guard is not None:
                guard.advance(track)
            return None
        if computed is None:
            prepared = compute_snapshot.capture(items, day)
            res = compute_snapshot.vitals_result(*prepared)
        else:
            res = computed.unwrap()
        run_id = apply_result(track, d, def_id, day, now, it, inputs, res)
        if guard is not None:
            guard.advance(track)
    return {"run_id": run_id, "tp": day, "n": len(items)}
