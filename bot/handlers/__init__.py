"""Handler aggregation for python-telegram-bot: Ctx builder + register_all."""
from __future__ import annotations

import functools




from loguru import logger
from telegram import BotCommand, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    ShippingQueryHandler,
    filters,
)

from bot import config as cfg
from bot.engine import Ctx
from bot.flows import MENU_COMMANDS, TRIGGERS


_RESERVED_COMMANDS = {"cancel", "back", "language", "start", "help"}


def build_ctx(adapter, update: Update, kind: str = "message") -> "Ctx":
    """Build the library-neutral Ctx from a PTB Update."""
    sq = getattr(update, "shipping_query", None)
    if sq is not None:
        return Ctx(
            adapter,
            user_id=sq.from_user.id,
            chat_id=sq.from_user.id,
            text=sq.invoice_payload or "",
            username=sq.from_user.username or "",
            first_name=sq.from_user.first_name or "",
            language=sq.from_user.language_code or "en",
            chat_type="private",
            is_admin=sq.from_user.id in cfg.ADMINS,
            update_kind=kind,
            raw=update,
            shipping={"id": sq.id, "payload": sq.invoice_payload or "",
                      "order_info": _jsonable_order(getattr(sq, "order_info", None))},
        )
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message
    cq = update.callback_query
    user_id = user.id if user else 0
    text = ""
    if message is not None:
        text = message.text or message.caption or ""
    elif cq is not None and cq.message is not None:
        text = getattr(cq.message, "text", "") or getattr(cq.message, "caption", "") or ""
    pre = {}
    if update.pre_checkout_query is not None:
        pre = {
            "id": update.pre_checkout_query.id,
            "payload": update.pre_checkout_query.invoice_payload,
            "amount": update.pre_checkout_query.total_amount,
            "currency": update.pre_checkout_query.currency,
        }
    cq_message_id = 0
    if cq is not None and cq.message is not None:
        cq_message_id = getattr(cq.message, "message_id", 0) or 0
    passport: dict = {}
    passport_data = getattr(message, "passport_data", None) if message is not None else None
    if passport_data is not None:
        elements = getattr(passport_data, "data", None) or []
        passport = {
            "types": [getattr(e, "type", "") for e in elements],
            "elements_count": len(elements),
            "credentials_hash": getattr(getattr(passport_data, "credentials", None), "hash", ""),
            "encrypted": adapter.make_jsonable(passport_data) if adapter is not None else None,
            "credentials": (adapter.make_jsonable(passport_data.credentials)
                            if (adapter is not None and passport_data.credentials) else None),
        }
    payment: dict = {}
    charge_id = ""
    sp_msg = getattr(message, "successful_payment", None) if message is not None else None
    if sp_msg is not None:
        charge_id = sp_msg.telegram_payment_charge_id or ""
        payment = {"payload": sp_msg.invoice_payload or "", "amount": sp_msg.total_amount,
                   "currency": sp_msg.currency, "charge_id": charge_id}
    return Ctx(
        adapter,
        user_id=user_id,
        chat_id=chat.id if chat else user_id,
        message_id=message.message_id if message is not None else cq_message_id,
        text=text,
        username=(user.username or "") if user else "",
        first_name=(user.first_name or "") if user else "",
        language=((user.language_code or "en") if user else "en"),
        chat_type=chat.type if chat else "private",
        is_premium=bool(user.premium) if user else False,
        reply_to=(message.reply_to_message.message_id
                  if (message is not None and message.reply_to_message is not None) else 0),
        callback_data=(cq.data or "") if cq is not None else "",
        args=(text.split()[1:] if text.startswith("/") else []),
        raw=update,
        is_admin=user_id in cfg.ADMINS,
        update_kind=kind,
        media=_media_of(message),
        pre_checkout=pre,
        passport=passport,
        payment=payment,
        payment_charge_id=charge_id,
    )


def _jsonable_order(order_info) -> dict:
    """Order info (shipping address etc.) → JSON-safe dict."""
    if order_info is None:
        return {}
    out = {"name": getattr(order_info, "name", "") or "",
           "phone_number": getattr(order_info, "phone_number", "") or "",
           "email": getattr(order_info, "email", "") or ""}
    address = getattr(order_info, "shipping_address", None)
    if address is not None:
        out["shipping_address"] = {
            "country_code": getattr(address, "country_code", ""),
            "state": getattr(address, "state", ""),
            "city": getattr(address, "city", ""),
            "street_line1": getattr(address, "street_line1", ""),
            "street_line2": getattr(address, "street_line2", ""),
            "post_code": getattr(address, "post_code", ""),
        }
    return out


def _media_of(message) -> dict:
    """Extract file ids / location / contact for ASK media input types."""
    if message is None:
        return {}
    media: dict = {}
    if getattr(message, "photo", None):
        media["photo_file_id"] = message.photo[-1].file_id
    if getattr(message, "document", None):
        media["document_file_id"] = message.document.file_id
    if getattr(message, "video", None):
        media["video_file_id"] = message.video.file_id
    if getattr(message, "animation", None):
        media["animation_file_id"] = message.animation.file_id
    if getattr(message, "voice", None):
        media["voice_file_id"] = message.voice.file_id
    if getattr(message, "location", None):
        media["latitude"] = message.location.latitude
        media["longitude"] = message.location.longitude
    if getattr(message, "contact", None):
        media["phone_number"] = message.contact.phone_number or ""
    return media


# Imported AFTER build_ctx and helpers are defined: the submodules import
# build_ctx from this package, so it must already exist on the module.
from bot.handlers import callbacks, commands, errors, messages  # noqa: E402


def register_all(app: Application, engine) -> int:
    """Register every handler this design needs; returns the handler count."""
    count = 2
    app.add_handler(CommandHandler("cancel", functools.partial(commands.on_command, engine,
        "cancel")))
    app.add_handler(CommandHandler("back", functools.partial(commands.on_command, engine, "back")))
    app.add_handler(CommandHandler("language", functools.partial(commands.on_command, engine,
        "language")))
    command_names = {
        t["pattern"] for t in TRIGGERS if t["kind"] == "command" and t.get("pattern")
    }
    for name in sorted(command_names):
        if name in _RESERVED_COMMANDS:
            continue
        app.add_handler(CommandHandler(name, functools.partial(commands.on_command, engine, name)))
        count += 1
    app.add_handler(CallbackQueryHandler(functools.partial(callbacks.on_callback, engine)))
    count += 1
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, functools.partial(messages.on_message, engine)))
    count += 1
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.DOCUMENT | filters.VIDEO | filters.VIDEO_NOTE
        | filters.VOICE | filters.ANIMATION | filters.LOCATION | filters.CONTACT,
        functools.partial(messages.on_message, engine)))
    count += 1
    app.add_handler(PreCheckoutQueryHandler(functools.partial(messages.on_pre_checkout, engine)))
    count += 1
    app.add_handler(ShippingQueryHandler(functools.partial(messages.on_shipping, engine)))
    count += 1
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT,
        functools.partial(messages.on_successful_payment, engine)))
    count += 1
    app.add_error_handler(errors.on_error)
    return count


async def set_menu_commands(app: Application) -> None:
    """Publish the bot menu (setMyCommands)."""
    commands = [BotCommand(c["command"], str(c["description"])[:256]) for c in MENU_COMMANDS]
    commands.append(BotCommand("cancel", "Cancel the current action"))
    commands.append(BotCommand("back", "Go one step back"))
    commands.append(BotCommand("language", "Change language"))
    try:
        await app.bot.set_my_commands(commands)
    except Exception:
        logger.exception("set_my_commands failed (ignored)")
