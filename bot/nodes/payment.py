"""N24 PAYMENT — Telegram Stars / provider invoice (Section 16).

Handler contract: async handle(node, ctx, eng, st) -> instruction tuple."""
from __future__ import annotations

from bot import config as cfgmod
from bot.engine import _to_int
from bot.errors import InternalError, UserInputError


async def handle(node: dict, ctx, eng, st: dict):
    """Send an invoice; success arrives via the successful_payment trigger."""
    cfgd = node.get("cfg") or {}
    currency = str(cfgd.get("currency") or "")
    amount_raw = cfgd.get("amount")
    if not currency or amount_raw in (None, ""):
        raise InternalError("PAYMENT node without a currency and amount (E021)")
    amount = _to_int(await eng.resolve(amount_raw, ctx, st))
    if amount <= 0:
        raise UserInputError("invoice amount must be positive")
    title = await eng.render_text(cfgd.get("title", "Purchase"), ctx, st, "")
    description = await eng.render_text(cfgd.get("description", ""), ctx, st, "")
    payload = str(cfgd.get("payload") or node["id"])[:60]
    stars = bool(cfgd.get("stars", True))
    provider_token = ""
    if not stars:
        provider_token = cfgmod.env(str(cfgd.get("providerTokenVar") or "PAYMENT_PROVIDER_TOKEN"))
        if not provider_token:
            raise InternalError("provider payments need the provider token env var to be set")
    from bot.payments import build_prices

    prices = build_prices(cfgd.get("prices", ""), currency, amount)
    await ctx.adapter.send_invoice(
        ctx, title, description, payload, currency, amount, provider_token, stars,
        prices=prices, need_shipping=bool(cfgd.get("needShipping")),
        start_param=str(cfgd.get("startParam") or "invoice"),
    )
    return eng.goto(st, node)
