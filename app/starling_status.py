"""Local model status: probe outside A; existing start-on-GET is intentional."""
import threading


def view(app):
    # The App owns this stable model reference for its entire lifetime.
    with app.lock:
        llm = app.llm
    up = llm.healthy()
    with app.lock:
        if not up and llm.cfg.get("model") and not getattr(app, "_llm_starting", None):
            app._llm_starting = threading.Thread(target=llm.ensure, daemon=True)
            app._llm_starting.start()
        starting = bool(getattr(app, "_llm_starting", None) and app._llm_starting.is_alive())
        return {"llm": up, "starting": starting and not up,
                "model": llm.model_name if llm.cfg.get("model") else None}
