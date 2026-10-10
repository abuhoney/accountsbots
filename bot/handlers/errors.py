"""Error handler for python-telegram-bot (Section 25)."""
from __future__ import annotations


from telegram import Update
from telegram.ext import ContextTypes

from bot.engine import Ctx
from bot.errors import handle_exception


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Application-level error handler: never leaks tracebacks to users."""
    if context and context.error is not None:
        ctx = None
        try:
            from bot.handlers import build_ctx

            if isinstance(update, Update):
                ctx = build_ctx(context.application.bot_data.get("__adapter__"), update, "error")
        except Exception:
            ctx = None
        if ctx is None:
            ctx = Ctx(context.application.bot_data.get("__adapter__"))
        await handle_exception(ctx, context.error, ctx.adapter, None)
