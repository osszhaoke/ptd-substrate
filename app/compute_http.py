"""HTTP save/computation adapter. Legacy writes keep their original response semantics."""
import compute_jobs
import input_guard
from h1_common import H1Error


def result(handler, inst, body, operation, value):
    if body.get("response_view", "full") == "receipt-v1":
        target = ({"request_id": value["request_id"]} if operation == "save" else
                  {"observation_id": body["observation_id"]})
        return handler._json(200, dict(value, projection="write-receipt/1",
            instance_id=inst.ctx.instance_id, operation=operation, target=target,
            invalidates=["home", "data", "graph", "versions"]))
    value["snapshot"] = inst.snapshot()
    return handler._json(200, value)


def write(handler, inst, path, body):
    if body.get("response_view", "full") not in ("full", "receipt-v1"):
        raise H1Error("RESPONSE_VIEW_INVALID", "保存回执格式无效")
    mode = body.get("compute_mode")
    if mode and body.get("response_view") != "receipt-v1":
        raise H1Error("COMPUTE_MODE_INVALID", "")
    operation = path.rsplit("/", 1)[1]
    with compute_jobs.selected(inst, mode):
        if operation == "save":
            value = inst.save_rows(body)
        elif operation == "correct":
            value = inst.correct(body["observation_id"], body["value"])
        else:
            value = inst.retract(body["observation_id"])
    return handler._torch_result(inst, body, operation, value)


def table(handler, app, q, raw):
    inst = app.inst(q["key"])
    nature = input_guard.nature(q.get("nature", input_guard.MISSING), default=inst.nature)
    with compute_jobs.selected(inst, q.get("compute_mode")):
        return handler._json(200, inst.save_table(raw, nature == "SYNTHETIC", q.get("request_id")))


def endpoint(handler, app, method, path, q):
    if path not in ("/api/compute/status", "/api/compute/retry"):
        return False
    try:
        manager = getattr(app, "compute_jobs", None)
        if manager is None:
            raise H1Error("COMPUTE_UNAVAILABLE", "")
        if method == "GET" and path == "/api/compute/status":
            key = q.get("key")
            app.inst(key)  # validate identity, without a health-data read
            handler._json(200, manager.status(key))
        elif method == "POST" and path == "/api/compute/retry":
            body = input_guard.json_object(handler.rfile.read())
            if set(body) != {"key"}:
                raise H1Error("BODY_INVALID", "")
            with app.lock:
                inst = app.inst(body["key"])
                input_guard.require_writable(inst)
                state = manager.status(body["key"])
                if state["state"] == "FAILED":
                    manager.enqueue(inst, retry=True)
                handler._json(200, manager.status(body["key"]))
        else:
            handler._json(405, {"error": "METHOD_NOT_ALLOWED"})
    except input_guard.RequestError as exc:
        handler._json(exc.status, {"error": exc.code})
    except (H1Error, KeyError) as exc:
        handler._json(400, {"error": getattr(exc, "code", "INSTANCE_UNKNOWN")})
    except Exception as exc:
        app.log("compute_api_failed", type(exc).__name__)
        handler._json(500, {"error": "COMPUTE_STATE_UNAVAILABLE"})
    return True
