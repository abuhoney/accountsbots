"""N02 MESSAGE — send text (template + parse mode + optional other chat).

Handler contract: async handle(node, ctx, eng, st) -> instruction tuple."""
from __future__ import annotations

from bot.engine import _to_int


async def handle(node: dict, ctx, eng, st: dict):
    """Send a text message; consumes a pending keyboard from KEYBOARD nodes."""
    cfgd = node.get("cfg") or {}
    parse_mode = cfgd.get("parseMode", "HTML")
    count = None
    if cfgd.get("i18nCount"):
        count = await eng.resolve(cfgd.get("i18nCount"), ctx, st)
    text = await eng.render_text(
        cfgd.get("text", ""), ctx, st, parse_mode, cfgd.get("i18nKey", ""), count=count
    )
    rows = st.pop("pending_keyboard", None)
    chat_binding = cfgd.get("chatId", "")
    if chat_binding:
        target = _to_int(await eng.resolve(chat_binding, ctx, st))
        await ctx.adapter.send_to_chat(target, text, parse_mode, rows)
    else:
        await ctx.adapter.send_text(
            ctx,
            text,
            parse_mode,
            rows,
            reply_to=bool(cfgd.get("replyTo")),
            disable_preview=bool(cfgd.get("disablePreview")),
        )
    return eng.goto(st, node)
