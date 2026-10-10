"""python-telegram-bot v21 adapter: the only library-specific send layer.
The flow engine and node handlers talk to this interface exclusively."""
from __future__ import annotations

from typing import Any



from loguru import logger
from telegram import (
    CopyTextButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    InputTextMessageContent,
    KeyboardButton,
    LabeledPrice,
    LoginUrl,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    ShippingOption,
    WebAppInfo,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest, RetryAfter, TelegramError
from telegram.ext import Application

from bot.errors import InternalError, NetworkError, RateLimitError, UserInputError


_MODE_MAP = {
    "HTML": ParseMode.HTML,
    "MarkdownV2": ParseMode.MARKDOWN_V2,
    "Markdown": ParseMode.MARKDOWN,
    "": None,
}

class Adapter:
    """Unified send API on top of python-telegram-bot v21 (Bot API)."""

    def __init__(self, app: Application, userbot: Any = None) -> None:
        self.app = app
        self.bot = app.bot
        self.userbot = userbot
        self.ratelimit: Any = None

    @staticmethod
    def _chat_ref(ref: Any) -> Any:
        if isinstance(ref, int):
            return ref
        text = str(ref or "").strip()
        if text.lstrip("-").isdigit():
            return int(text)
        return "@" + text.lstrip("@")

    def _markup(self, rows):
        """Neutral button rows -> InlineKeyboardMarkup / ReplyKeyboardMarkup."""
        if not rows:
            return None
        is_reply = any(b.get("kind") == "reply" for row in rows for b in row)
        if is_reply:
            kb = []
            for row in rows:
                line = [KeyboardButton(b.get("text", "")) for b in row if b.get("text")]
                if line:
                    kb.append(line)
            return ReplyKeyboardMarkup(kb, resize_keyboard=True) if kb else None
        kb = []
        for row in rows:
            line = []
            for b in row:
                text = str(b.get("text", ""))[:64]
                kind = b.get("kind", "inline")
                if kind == "url":
                    line.append(InlineKeyboardButton(text, url=b.get("url", "")))
                elif kind == "web_app":
                    line.append(InlineKeyboardButton(text,
                        web_app=WebAppInfo(url=b.get("url", ""))))
                elif kind == "pay":
                    line.append(InlineKeyboardButton(text, pay=True))
                elif kind == "login_url":
                    line.append(InlineKeyboardButton(text,
                        login_url=LoginUrl(url=b.get("url", ""))))
                elif kind == "switch_inline":
                    line.append(InlineKeyboardButton(text,
                        switch_inline_query=b.get("switch_inline", "")))
                elif kind == "switch_inline_current":
                    line.append(InlineKeyboardButton(text,
                        switch_inline_query_current_chat=b.get("switch_inline", "")))
                elif kind == "copy_text":
                    line.append(InlineKeyboardButton(text,
                        copy_text=CopyTextButton(text=b.get("copy_text", ""))))
                else:
                    line.append(InlineKeyboardButton(text,
                        callback_data=str(b.get("callback", "noop"))[:64]))
            if line:
                kb.append(line)
        return InlineKeyboardMarkup(kb) if kb else None

    async def _guard(self, coro):
        """Map Telegram errors onto domain errors incl. FloodWait backoff."""
        try:
            return await coro
        except RetryAfter as exc:
            if self.ratelimit is not None:
                await self.ratelimit.note_flood_wait(exc.retry_after)
            raise RateLimitError(f"flood limit: retry in {exc.retry_after}s",
                retry_after=int(exc.retry_after)) from exc
        except BadRequest as exc:
            if "message is not modified" in str(exc).lower():
                return None
            raise UserInputError(f"Telegram rejected the request: {exc}") from exc
        except TelegramError as exc:
            raise NetworkError(f"Telegram API error: {exc}") from exc

    async def send_text(self, ctx, text: str, parse_mode: str = "HTML", rows=None,
                        reply_to: bool = False, disable_preview: bool = False):
        msg = await self._guard(self.bot.send_message(
            chat_id=ctx.chat_id,
            text=(str(text)[:4096] or " "),
            parse_mode=_MODE_MAP.get(parse_mode),
            reply_markup=self._markup(rows),
            reply_to_message_id=ctx.message_id if reply_to else None,
            disable_web_page_preview=bool(disable_preview),
        ))
        return getattr(msg, "message_id", None)

    async def send_to_chat(self, chat_id: int, text: str, parse_mode: str = "HTML", rows=None):
        msg = await self._guard(self.bot.send_message(
            chat_id=self._chat_ref(chat_id), text=(str(text)[:4096] or " "),
            parse_mode=_MODE_MAP.get(parse_mode), reply_markup=self._markup(rows),
        ))
        return getattr(msg, "message_id", None)

    async def edit_text(self, ctx, text: str, parse_mode: str = "HTML", rows=None):
        if not ctx.message_id:
            return await self.send_text(ctx, text, parse_mode, rows)
        await self._guard(self.bot.edit_message_text(
            chat_id=ctx.chat_id, message_id=ctx.message_id,
            text=(str(text)[:4096] or " "), parse_mode=_MODE_MAP.get(parse_mode),
            reply_markup=self._markup(rows),
        ))

    async def answer_callback(self, ctx, text: str = "", alert: bool = False,
                              cache_time: int = 0, url: str = "") -> None:
        query_id = getattr(getattr(ctx, "raw", None), "id", "")
        if ctx.update_kind == "callback" and getattr(ctx.raw, "id", None):
            query_id = ctx.raw.id
        if not query_id:
            return
        await self._guard(self.bot.answer_callback_query(
            callback_query_id=query_id, text=str(text)[:200] or None,
            show_alert=bool(alert), cache_time=int(cache_time or 0), url=url or None,
        ))

    async def send_media(self, ctx, media_type: str, source: str, caption: str = "",
                         parse_mode: str = "HTML", rows=None):
        senders = {
            "photo": self.bot.send_photo,
            "video": self.bot.send_video,
            "document": self.bot.send_document,
            "animation": self.bot.send_animation,
            "audio": self.bot.send_audio,
            "voice": self.bot.send_voice,
            "video_note": self.bot.send_video_note,
            "sticker": self.bot.send_sticker,
        }
        sender = senders.get(media_type)
        if sender is None:
            raise InternalError(f"unsupported media type {media_type!r}")
        field = {
            "photo": "photo", "video": "video", "document": "document",
            "animation": "animation", "audio": "audio", "voice": "voice",
            "video_note": "video_note", "sticker": "sticker",
        }[media_type]
        kwargs = {"chat_id": ctx.chat_id, field: source,
                  "reply_markup": self._markup(rows)}
        if media_type not in ("video_note", "sticker", "voice"):
            kwargs["caption"] = str(caption)[:1024] or None
            kwargs["parse_mode"] = _MODE_MAP.get(parse_mode) if caption else None
        msg = await self._guard(sender(**kwargs))
        return getattr(msg, "message_id", None)

    async def send_album(self, ctx, media_type: str, sources: list, caption: str = "",
                         parse_mode: str = "HTML"):
        """Send 2-10 items as one album (send_media_group)."""
        classes = {
            "photo": InputMediaPhoto, "video": InputMediaVideo,
            "audio": InputMediaAudio, "document": InputMediaDocument,
        }
        cls = classes.get(media_type)
        if cls is None:
            raise InternalError(f"albums do not support media type {media_type!r}")
        media = []
        for i, source in enumerate(sources[:10]):
            if i == 0 and caption:
                media.append(cls(media=source, caption=str(caption)[:1024],
                                 parse_mode=_MODE_MAP.get(parse_mode)))
            else:
                media.append(cls(media=source))
        await self._guard(self.bot.send_media_group(chat_id=ctx.chat_id, media=media))

    async def remove_keyboard(self, ctx, kind: str = "reply") -> None:
        if kind == "reply":
            await self._guard(self.bot.send_message(ctx.chat_id, " ",
                reply_markup=ReplyKeyboardRemove()))
        elif ctx.update_kind == "callback" and ctx.message_id:
            await self._guard(self.bot.edit_message_reply_markup(ctx.chat_id,
                ctx.message_id, reply_markup=None))

    async def send_invoice(self, ctx, title: str, description: str, payload: str,
                           currency: str, amount: int, provider_token: str = "",
                           stars: bool = True, prices=None, need_shipping: bool = False,
                           start_param: str = "invoice") -> None:
        if not prices:
            prices = [{"label": (str(title) or "Item")[:64], "amount": int(amount)}]
        labeled = [LabeledPrice(label=str(p["label"])[:64], amount=int(p["amount"]))
                   for p in prices]
        # __MBM_EXT_STARS_TOKEN__ — XTR MUST have empty provider_token
        _is_stars = str(currency).upper() == "XTR"
        if _is_stars:
            provider_token = ""
        await self._guard(self.bot.send_invoice(
            chat_id=ctx.chat_id, title=str(title)[:64], description=str(description)[:255],
            payload=str(payload)[:128], provider_token=provider_token or "",
            currency=str(currency), prices=labeled,
            start_parameter=str(start_param)[:64],
            need_shipping_address=bool(need_shipping),
        ))

    async def answer_shipping(self, ctx, ok: bool = True, options=None, error: str = "") -> None:
        """Answer a shipping query (ok + options, or ok=False + error)."""
        query_id = (ctx.shipping or {}).get("id")
        if not query_id:
            return
        shipping_options = None
        if ok:
            shipping_options = [
                ShippingOption(
                    id=str(o["id"])[:64], title=str(o["title"])[:64],
                    prices=[LabeledPrice(label=str(p["label"])[:64],
                                         amount=int(p["amount"]))
                            for p in o.get("prices", [])])
                for o in (options or [])
            ]
            ok = bool(shipping_options)
        await self._guard(self.bot.answer_shipping_query(
            shipping_query_id=query_id, ok=ok,
            shipping_options=shipping_options or None,
            error_message=(str(error) or "shipping is not available") if not ok else None,
        ))

    async def refund_payment(self, ctx, user_id: int, charge_id: str,
                             stars: bool = True) -> None:
        """Refund a Telegram Stars payment (Bot API refundStarPayment)."""
        if not stars:
            raise InternalError("provider refunds must go through the provider's own API")
        await self._guard(self.bot.refund_star_payment(
            user_id=int(user_id), telegram_payment_charge_id=str(charge_id)))

    async def call_action(self, action: str, params: dict):
        """Group calls need MTProto — via the hybrid userbot bridge only."""
        if self.userbot is None:
            raise InternalError(
                "CALL nodes require the Telethon/Pyrogram target or hybrid botType "
                "with API_ID/API_HASH (the Bot API has no call management)")
        return await self.userbot.call_action(action, params)

    async def story_action(self, action: str, params: dict):
        """Stories need MTProto — via the hybrid userbot bridge only."""
        if self.userbot is None:
            raise InternalError(
                "STORIES nodes require the Telethon/Pyrogram target or hybrid botType "
                "with API_ID/API_HASH (the Bot API cannot post stories)")
        return await self.userbot.story_action(action, params)

    async def answer_pre_checkout(self, ctx, ok: bool = True, error: str = "") -> None:
        query_id = (ctx.pre_checkout or {}).get("id")
        if not query_id:
            return
        await self._guard(self.bot.answer_pre_checkout_query(
            pre_checkout_query_id=query_id,
            ok=bool(ok),
            error_message=(error or None) if not ok else None,
        ))

    async def chat_member_status(self, channel: Any, user_id: int) -> str:
        try:
            member = await self.bot.get_chat_member(self._chat_ref(channel), int(user_id))
            return str(member.status)
        except TelegramError as exc:
            logger.warning("get_chat_member failed for {!r}: {}", channel, exc)
            return "left"

    async def delete_message(self, ctx, message_id: int) -> None:
        if not message_id:
            return
        try:
            await self.bot.delete_message(ctx.chat_id, int(message_id))
        except TelegramError as exc:
            logger.warning("delete_message failed: {}", exc)

    async def download(self, ctx, file_ref: str, dest) -> str:
        # __MBM_EXT_FILE_SIZE__ — pre-check when possible
        try:
            if str(file_ref).startswith(("http://", "https://")):
                import httpx as _httpx
                async with _httpx.AsyncClient(timeout=10.0, follow_redirects=True) as _hc:
                    _head = await _hc.head(str(file_ref))
                    _size = int(_head.headers.get("content-length", "0") or 0)
                    if _size and _size > 50 * 1024 * 1024:
                        raise UserInputError(
                            f"remote file is {_size / 1048576:.1f} MB — over the 50 MB limit")
        except UserInputError:
            raise
        except Exception:
            pass
        tg_file = await self._guard(self.bot.get_file(str(file_ref)))
        await tg_file.download_to_drive(custom_path=str(dest))
        return str(dest)

    async def answer_inline(self, ctx, results: list) -> None:
        if not ctx.inline_query_id:
            return
        articles = []
        for i, item in enumerate((results or [])[:50]):
            articles.append(InlineQueryResultArticle(
                id=str(i),
                title=str(item.get("title", "result"))[:64],
                input_message_content=InputTextMessageContent(str(item.get("text", ""))[:4096]),
            ))
        await self._guard(self.bot.answer_inline_query(ctx.inline_query_id, articles))

    @staticmethod
    def make_jsonable(obj: Any) -> Any:
        """Convert a library/TL object into JSON-safe data for state vars."""
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, (bytes, bytearray)):
            return bytes(obj).hex()
        if isinstance(obj, dict):
            return {str(k): Adapter.make_jsonable(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [Adapter.make_jsonable(v) for v in obj]
        to_dict = getattr(obj, "to_dict", None)
        if callable(to_dict):
            try:
                return Adapter.make_jsonable(to_dict())
            except Exception:
                logger.debug("to_dict failed for {}", type(obj).__name__)
        return str(obj)[:2000]

    async def invoke_raw(self, method_full: str, kwargs: dict, userbot: bool = False) -> Any:
        """Raw MTProto via the optional userbot client (hybrid botType)."""
        if self.userbot is None:
            raise InternalError(
                "API_CALL (raw MTProto) nodes need the Pyrogram/Telethon target, or hybrid "
                "botType with API_ID/API_HASH so a Telethon userbot client is attached."
            )
        return await self.userbot.invoke_for_bot(method_full, kwargs)
