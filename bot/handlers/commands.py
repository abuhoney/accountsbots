"""Command dispatch for python-telegram-bot."""
from __future__ import annotations


from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers import build_ctx


async def on_command(engine, name: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route a command update into the universal flow engine."""
    ctx = build_ctx(engine.adapter, update, "command")
    if context.args:
        ctx.args = [str(a) for a in context.args]
    await engine.handle_command(name, ctx)
