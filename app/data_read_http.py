"""Existing read-route business body; caller retains its original A lock."""
import data_read


def _prepare_sources(inst, q, receipt_supplier, gene_supplier):
    """One preparation order; suppliers defer parsing until its original step."""
    extras = []
    if q.get("view", "") not in ("observation", "versions"):
        nature = inst.nature or ("REAL" if "REAL" in inst.ctx.accept else "SYNTHETIC")
        receipts = receipt_supplier() if nature == "REAL" else data_read.preview_receipts(inst, q.get("preview_receipts", ""))
        extras = data_read.extra_rows(inst, gene_supplier(), receipts)
    return extras


def read_locked(app, q, gene_reader):
    inst = app.inst(q["key"])
    view = q.get("view", "")
    extras = _prepare_sources(inst, q, lambda: app.bridge(inst).receipts(),
        lambda: gene_reader(inst).asset_receipts())
    return data_read.read(inst, view, cursor=q.get("cursor", ""),
        limit=q.get("limit", "50"), extra_rows=extras,
        **{k: q[k] for k in ("category", "code", "sources", "from", "to", "oid", "revision") if k in q})


# Isolated rollout switch. History views retain the original locked path.
READ_OUTSIDE_LOCK = True
CURRENT_VIEWS = ('summary', 'metrics', 'rows', 'series')


def unlocked(q):
    return READ_OUTSIDE_LOCK and q.get('view','') in CURRENT_VIEWS


def dispatch(app, q, gene_reader):
    if not unlocked(q):
        with app.lock:
            return read_locked(app, q, gene_reader)
    import data_read_scope
    for attempt in range(2):
        capture = None
        try:
            with app.lock:
                capture = data_read_scope.Capture(app, q, gene_reader)
            try:
                body = data_read.read(capture.inst, q.get('view',''), cursor=q.get('cursor',''),
                    limit=q.get('limit','50'), extra_rows=capture.extras(q),
                    **{k:q[k] for k in ('category','code','sources','from','to','oid','revision') if k in q})
            finally:
                capture.close()
            with app.lock:
                if capture.valid():
                    capture.publish_cache()
                    return body
        except data_read_scope.Changed:
            pass
        if q.get('cursor'):
            break
    data_read._fail('DATA_VIEW_CHANGED', '数据已更新，请重新读取当前筛选')
