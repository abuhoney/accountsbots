"""Message/inline/special update dispatch for python-telegram-bot."""
from __future__ import annotations


from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers import build_ctx


async def on_message(engine, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route a text/media message into the universal flow engine."""
    ctx = build_ctx(engine.adapter, update, "message")
    await engine.handle_message(ctx)


async def on_channel_post(engine, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route a channel post into the engine (channel_post triggers)."""
    ctx = build_ctx(engine.adapter, update, "channel_post")
    if update.channel_post is not None:
        ctx.chat_id = update.channel_post.chat_id
        ctx.message_id = update.channel_post.message_id
        ctx.text = update.channel_post.text or update.channel_post.caption or ""
    await engine.handle_special("channel_post", ctx)


async def on_inline(engine, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route an inline query into the engine."""
    ctx = build_ctx(engine.adapter, update, "inline")
    if update.inline_query is not None:
        ctx.inline_query_id = update.inline_query.id
        ctx.text = update.inline_query.query or ""
    await engine.handle_inline(ctx)


async def on_chat_member(engine, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route a chat-member update into the engine."""
    ctx = build_ctx(engine.adapter, update, "chat_member")
    await engine.handle_special("chat_member", ctx)


async def on_join_request(engine, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route a join request into the engine."""
    ctx = build_ctx(engine.adapter, update, "join_request")
    if update.chat_join_request is not None:
        ctx.user_id = update.chat_join_request.from_user.id
        ctx.chat_id = update.chat_join_request.chat.id
    await engine.handle_special("join_request", ctx)


async def on_poll_answer(engine, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route a poll answer into the engine."""
    ctx = build_ctx(engine.adapter, update, "poll_answer")
    if update.poll_answer is not None:
        ctx.text = ",".join(str(i) for i in update.poll_answer.option_ids)
    await engine.handle_special("poll_answer", ctx)


async def on_pre_checkout(engine, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Answer pre-checkout queries (always OK after validation)."""
    ctx = build_ctx(engine.adapter, update, "pre_checkout")
    await engine.handle_special("pre_checkout", ctx)


async def on_successful_payment(engine, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route a successful payment into the engine + payments module."""
    from bot import payments

    ctx = build_ctx(engine.adapter, update, "successful_payment")
    message = update.effective_message
    sp = getattr(message, "successful_payment", None)
    if sp is not None:
        ctx.text = sp.invoice_payload or ""
        await payments.on_successful_payment(ctx, engine, sp.invoice_payload,
            sp.total_amount, sp.currency)
    await engine.handle_special("successful_payment", ctx)


async def on_shipping(engine, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route a shipping query into the engine (auto-answered when unbound)."""
    ctx = build_ctx(engine.adapter, update, "shipping_query")
    await engine.handle_special("shipping_query", ctx)


async def on_passport(engine, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route a Telegram Passport message into the engine."""
    ctx = build_ctx(engine.adapter, update, "passport_data")
    await engine.handle_special("passport_data", ctx)


async def on_web_app_data(engine, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route WebApp data into the engine."""
    ctx = build_ctx(engine.adapter, update, "web_app_data")
    message = update.effective_message
    if message is not None and message.web_app_data is not None:
        ctx.text = message.web_app_data.data or ""
    await engine.handle_special("web_app_data", ctx)
