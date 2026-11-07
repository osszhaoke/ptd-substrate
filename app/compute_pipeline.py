"""Original sync orchestration, same caller-owned lock and failure boundaries."""
from background_read import BackgroundRead
from h1_common import H1Error
import custom_cards, engines, card_thresholds, band_cards, vitals_ledger


def run(self, trigger, *, open_track, read_type, primary_sync, import_packages, deliver, captured_at=None):
    """Import every pending H1 package and compute. A failure is recorded and shown, never hidden (N8)."""
    track = open_track(self.ctx)
    at = self.now() if captured_at is None else captured_at
    # Acquire only after import has committed. Keep this cycle's complete
    # view, without display-retention filters; consumers must not mutate it.
    read = None
    def imported_read():
        nonlocal read
        if read is None:
            if not hasattr(self, "_background_read"):
                self._background_read = BackgroundRead(self)
            read = self._background_read.read_for_sync(lambda: read_type(track, self.ctx.tz))
        return read
    try:
        if self.sjia:
            result = primary_sync(track, self.ctx, self.app.registry, self.card(track), now=at,
                          notifiers=self.app.notifiers, read_provider=imported_read)
            imported = result["import"]
            summary = {"new": result["new"], "updated": result["updated"], "run_id": result["run_id"],
                       "alert": result["alert"]}
        else:
            imported = import_packages(track, self.ctx, self.app.registry, imported_at=at)
            summary = {"new": [], "updated": [], "run_id": None, "alert": None}
        self.last_sync = {"at": at, "trigger": trigger, "ok": imported.error is None,
                          "inserted": imported.inserted, "pending_commits": imported.pending_commits,
                          "error": imported.error, **summary}
        if not self.spec.get("replay"):  # 自定义状态卡：同一份星轨数据，各卡按自己的定义算
            try:
                groups = custom_cards.by_code(track, self.ctx, read=imported_read())
                self.last_sync["custom"] = custom_cards.sync_all(track, self.ctx, now=at, notifiers=self.app.notifiers,
                                                              groups=groups)
                self.last_sync["engines"] = engines.sync_all(track, self.ctx, self.ctx.root, now=at, notifiers=self.app.notifiers,
                                                             groups=groups)
                self.last_sync["thresholds"] = card_thresholds.evaluate_all(track, self.ctx, at, groups=groups)
                deliver(track, self.app.notifiers, at)
                # 体验腕带三张卡：结果进星轨账本（输入变了才记；没有 Somaloop 读数的实例什么都不写）
                self.last_sync["band_cards"] = band_cards.record(track, self.ctx, now=at, since=None, read=imported_read())
                # 我的体征：卡上显示的那组读数进账本（r63，输入变了才记），星痕「状态记录」里能看到每次计算
                setup = self.setup().state()
                if "VITALS" in setup["cards"] and not self.spec.get("replay"):
                    self.last_sync["vitals_run"] = vitals_ledger.record(track, self.ctx, self.vitals_view(track, setup, read=imported_read())[0]["items"],
                                                                        day=at[:10], now=at)
            except Exception as exc:  # noqa: BLE001 - 自定义卡算不了不影响关注卡，如实记下
                self.last_sync["custom_error"] = {"code": getattr(exc, "code", type(exc).__name__), "detail": str(exc)[:200]}
                self.app.log("custom_sync_failed", self.ctx.instance_id, type(exc).__name__)
    except Exception as exc:  # shown as 失败 + 再试一次
        code = exc.code if isinstance(exc, H1Error) else type(exc).__name__
        self.last_sync = {"at": at, "trigger": trigger, "ok": False,
                          "error": {"code": code, "detail": str(exc)[:300]}}
        self.app.log("sync_failed", self.ctx.instance_id, code)
    finally:
        track.close()
    return self.last_sync


def run_locked(inst, trigger):
    """P1 opt-in internal path. Caller retains A over capture, compute and apply."""
    import compute_cycle, compute_commit
    at = inst.now()
    try:
        cycle = compute_cycle.capture(inst, trigger)
        proposal = compute_cycle.evaluate(cycle)
        result = compute_commit.apply(inst, cycle, proposal)
    except compute_cycle.CapacityFallback:
        if 'cycle' not in locals():
            return inst.sync_track(trigger)
        # Capture already imported and collected historical intents. Continue the
        # original computation without a second import or notification prepare.
        from functools import partial
        from startrack_import import ImportSummary
        from cards import open_startrack, sync, deliver_pending
        from observation_read import ObservationRead
        imported = ImportSummary(**cycle.imported)
        return run(inst, trigger, open_track=open_startrack, read_type=ObservationRead,
                   primary_sync=partial(sync, imported_summary=imported, recover=False),
                   import_packages=lambda *a, **kw: imported, deliver=deliver_pending, captured_at=cycle.at)
    except compute_cycle.StaleCycle:
        raise
    except Exception as exc:
        result = compute_commit.failure(inst, at, trigger, exc)
    inst.last_sync = result
    return result
