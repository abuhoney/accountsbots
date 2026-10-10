"""Callback-query dispatch for python-telegram-bot."""
from __future__ import annotations


from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers import build_ctx


async def on_callback(engine, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route a callback query into the universal flow engine."""
    ctx = build_ctx(engine.adapter, update, "callback")
    await engine.handle_callback(ctx)
