"""APScheduler integration: design-time jobs + runtime SCHEDULE nodes."""
from __future__ import annotations

from datetime import datetime, timezone


from loguru import logger


_scheduler = None
_engine = None

DESIGN_JOBS: list[dict] = [
    {
        "chat_id": "@env.SUPPORT_CHAT_ID",
        "cron": "",
        "flow_id": "flw_auto_release",
        "interval_seconds": 3600,
        "kind": "interval",
        "name": "auto_release_escrow"
    }
]


def _trigger_for(spec: dict):
    """Build the APScheduler trigger declared by a job spec."""
    kind = spec.get("kind", "interval")
    if kind == "cron":
        from apscheduler.triggers.cron import CronTrigger

        parts = str(spec.get("cron", "")).split()
        if len(parts) != 5:
            raise ValueError(f"cron expression must have 5 fields: {spec.get('cron')!r}")
        return CronTrigger(minute=parts[0], hour=parts[1], day=parts[2], month=parts[3],
            day_of_week=parts[4], timezone="UTC")
    if kind == "date":
        from apscheduler.triggers.date import DateTrigger

        run_at = spec.get("run_at")
        if not run_at:
            raise ValueError("one-shot job without run_at")
        return DateTrigger(run_date=datetime.fromtimestamp(int(run_at), tz=timezone.utc))
    from apscheduler.triggers.interval import IntervalTrigger

    return IntervalTrigger(seconds=int(spec.get("interval_seconds") or 3600))


async def _run_job(engine, flow_id: str, chat_id: int, variables: dict) -> None:
    try:
        await engine.run_flow_for_chat(flow_id, int(chat_id), variables)
    except Exception:
        logger.exception("scheduled job for flow {} failed", flow_id)


def register_flow_job(engine, name: str, kind: str, cron: str = "",
                      interval_seconds: int = 3600, run_at=None,
                      flow_id: str = "", chat_id: int = 0, variables=None) -> None:
    """Register (or replace) a job — used by SCHEDULE nodes at runtime."""
    global _scheduler
    # __MBM_EXT_SCHED_NO_RECURSION__ — lazy-create without re-entering design registration
    if _scheduler is None:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        _scheduler = AsyncIOScheduler(timezone="UTC")
        if not _scheduler.running:
            _scheduler.start()
    spec = {"kind": kind, "cron": cron, "interval_seconds": interval_seconds, "run_at": run_at}
    try:
        trigger = _trigger_for(spec)
    except ValueError as exc:
        logger.error("cannot schedule job {!r}: {}", name, exc)
        return
    _scheduler.add_job(
        _run_job, trigger,
        args=[engine, flow_id, int(chat_id or 0), dict(variables or {})],
        id=name, name=name, replace_existing=True, misfire_grace_time=120,
        coalesce=True, max_instances=1,
    )
    logger.info("scheduled job {!r} ({}) -> flow {}", name, kind, flow_id)


def init_scheduler(engine) -> None:
    """Start the AsyncIOScheduler and register every design-time job."""
    global _scheduler, _engine
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    _engine = engine
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
    # __MBM_EXT_SCHED_NO_RECURSION__ — guard against double design registration
    if getattr(_scheduler, "_mbm_design_loaded", False):
        if not _scheduler.running:
            _scheduler.start()
        return
    for spec in DESIGN_JOBS:
        chat_raw = str(spec.get("chat_id") or "")
        chat_id = int(chat_raw) if chat_raw.lstrip("-").isdigit() else 0
        if not chat_id:
            logger.warning("job {!r} has no numeric chat id; it will run without a chat context",
                spec.get("name"))
        try:
            register_flow_job(
                engine, name=str(spec.get("name")), kind=str(spec.get("kind")),
                cron=str(spec.get("cron",
                    "")), interval_seconds=int(spec.get("interval_seconds") or 3600),
                flow_id=str(spec.get("flow_id", "")), chat_id=chat_id,
            )
        except Exception:
            logger.exception("failed to register design job {!r}", spec.get("name"))
    _scheduler._mbm_design_loaded = True
    if not _scheduler.running:
        _scheduler.start()
        logger.info("scheduler started with {} job(s)", len(_scheduler.get_jobs()))


# __MBM_EXT_SCHED_ONESHOT__
async def _run_job_and_cleanup(engine, flow_id: str, chat_id: int, variables: dict, job_name: str,
    one_shot: bool) -> None:
    """Wrapper: removes the job after a one-shot ('date') execution."""
    try:
        await engine.run_flow_for_chat(flow_id, int(chat_id), variables)
    finally:
        if one_shot:
            try:
                manage_job("remove", job_name)
            except Exception:
                logger.exception("failed to remove one-shot job {!r}", job_name)


def manage_job(action: str, name: str) -> None:
    """Remove/pause/resume a job by name (used by SCHEDULE node actions)."""
    if _scheduler is None:
        logger.warning("scheduler not started; cannot {} job {!r}", action, name)
        return
    job = _scheduler.get_job(name)
    if job is None:
        logger.warning("job {!r} not found for action {}", name, action)
        return
    if action == "remove":
        job.remove()
    elif action == "pause":
        job.pause()
    elif action == "resume":
        job.resume()
    logger.info("scheduler job {!r}: {} applied", name, action)


def shutdown_scheduler() -> None:
    """Stop the scheduler on graceful shutdown."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
