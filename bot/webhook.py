"""aiohttp webhook + /health server shared by every library target."""
from __future__ import annotations

import asyncio
import signal
import time



from loguru import logger

from bot import config as cfg


_STARTED = time.time()


async def start_server(feed, host: str = "0.0.0.0", port: int = 8443,
                       path: str = "/webhook", secret: str = "",
                       handler_count: int = 0, layer: int = 0):
    """Serve the webhook endpoint + /health (Section 17/27/28).

    The secret token header X-Telegram-Bot-Api-Secret-Token is verified on
    every request when a secret is configured.
    """
    from aiohttp import web

    async def webhook_handler(request: web.Request) -> web.Response:
        if secret and request.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
            logger.warning("webhook request with invalid secret token from {}", request.remote)
            return web.Response(status=403)
        try:
            data = await request.json()
        except ValueError:
            return web.Response(status=400)
        try:
            await feed(data)
        except Exception:
            logger.exception("webhook update processing failed")
        return web.Response(text="OK")

    async def health_handler(request: web.Request) -> web.Response:
        from bot.errors import ERROR_COUNTERS

        payload = {
            "status": "ok",
            "uptime_s": int(time.time() - _STARTED),
            "handlers": handler_count,
            "errors": ERROR_COUNTERS.get("total", 0),
            "layer": layer,
            "version": cfg.BOT_VERSION,
        }
        return web.json_response(payload)

    app = web.Application()
    app.router.add_post(path, webhook_handler)
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("HTTP server listening on {}:{} ({} + /health)", host, port, path)
    return runner


async def wait_for_stop() -> None:
    """Block until SIGINT/SIGTERM arrives (graceful shutdown, Section 28)."""
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except (NotImplementedError, RuntimeError):
            pass
    await stop.wait()
