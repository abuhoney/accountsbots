"""Entry point for python-telegram-bot v21.

Run:  python main.py            (long polling)
      python main.py --webhook  (aiohttp webhook + /health)"""
from __future__ import annotations

import sys



from loguru import logger
from telegram import Update
from telegram.ext import Application

from bot import config as cfg
from bot import webhook
from bot.adapter import Adapter
from bot.db import build_database
from bot.engine import FlowEngine
from bot.handlers import register_all, set_menu_commands
from bot.middleware.ratelimit import RateLimiter
from bot.scheduler import shutdown_scheduler
from bot.state import StateManager, build_state_backend


database = build_database()


async def _post_init(app: Application) -> None:
    """Async startup: database, state, engine, handlers (Section 16 order)."""
    await database.init()
    engine = _build_engine(app)
    app.bot_data["engine"] = engine
    app.bot_data["__adapter__"] = engine.adapter
    await engine.startup()
    handlers = register_all(app, engine)
    await set_menu_commands(app)
    logger.info("{} ready — {} handler(s) registered", app.bot.username or "bot", handlers)


async def _noop_feed(data: dict) -> None:
    """Health-only server feed: polling mode processes updates itself."""
    return None


def _build_engine(app: Application) -> FlowEngine:
    """Wire adapter + state + repositories into the FlowEngine."""
    state = StateManager(build_state_backend())
    adapter = Adapter(app)
    ratelimit = RateLimiter(adapter, t_func=_i18n_t)
    adapter.ratelimit = ratelimit
    engine = FlowEngine(adapter, state, database, ratelimit)
    return engine


def _i18n_t(lang: str, key: str, **fmt) -> str:
    from bot.i18n import t

    return t(lang, key, **fmt)


async def _post_shutdown(app: Application) -> None:
    """Graceful shutdown: engine resources, scheduler, database."""
    engine = app.bot_data.get("engine")
    shutdown_scheduler()
    if engine is not None and getattr(engine.adapter, "userbot", None) is not None:
        await engine.adapter.userbot.close()
    if engine is not None:
        await engine.shutdown()
    runner = app.bot_data.get("health_runner")
    if runner is not None:
        await runner.cleanup()
    await database.close()
    logger.info("shutdown complete")


def run_webhook_mode(app: Application) -> None:
    """Webhook mode via the shared aiohttp server (secret token verified)."""
    import asyncio

    async def amain() -> None:
        await app.initialize()
        await app.start()
        engine = app.bot_data.get("engine")
        if engine is None:
            await _post_init(app)
            engine = app.bot_data.get("engine")

        async def feed(data: dict) -> None:
            update = Update.de_json(data, app.bot)
            if update is not None:
                await app.process_update(update)

        url = cfg.env("WEBHOOK_URL", "").rstrip("/")
        secret = cfg.env("WEBHOOK_SECRET", "")
        if not url:
            raise SystemExit("webhook mode needs " + "WEBHOOK_URL" + " to be set")
        runner = await webhook.start_server(
            feed, port=int(cfg.env("PORT") or 8443), path="/webhook",
            secret=secret, layer=cfg.MT_PROTO_LAYER,
        )
        await app.bot.set_webhook(url=url + "/webhook", secret_token=secret or None,
                                  allowed_updates=Update.ALL_TYPES)
        logger.info("webhook mode active at {}", url)
        await webhook.wait_for_stop()
        await app.bot.delete_webhook(drop_pending_updates=True)
        await runner.cleanup()
        await _post_shutdown(app)
        await app.stop()
        await app.shutdown()

    asyncio.run(amain())


def main() -> None:
    """Entrypoint: python main.py [--webhook]."""
    cfg.check_python_version()
    token = cfg.require_bot_token()
    cfg.setup_logging()
    missing = [name for name in cfg.check_required_env(report_missing=False) if name != "BOT_TOKEN"]
    if missing:
        logger.warning("required env vars missing: {}", ", ".join(missing))
    app = (
        Application.builder()
        .token(token)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )
    if "--webhook" in sys.argv:
        run_webhook_mode(app)
        return
    # PTB quirk: never wrap run_polling in asyncio.run; close_loop=False on v20+.
    app.run_polling(close_loop=False, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
