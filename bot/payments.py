"""Payment helpers: button invoices and successful-payment routing."""
from __future__ import annotations


from loguru import logger

from bot import config as cfg
from bot.errors import InternalError, UserInputError


DEFAULT_CURRENCY = "XTR"
DEFAULT_AMOUNT = 100
DEFAULT_TITLE = "دفع مضمون"
DEFAULT_DESCRIPTION = "دفع محمي عبر Escrow"
PROVIDER_TOKEN_VAR = "PAYMENT_PROVIDER_TOKEN"
DEFAULT_SHIPPING = {
    "id": "none",
    "title": "بلا شحن",
    "label": "الشحن",
    "amount": 0,
}


def _stars(currency: str) -> bool:
    return str(currency).upper() == "XTR"


def build_prices(prices_text: str, currency: str, amount: int) -> list[dict]:
    """Parse 'Label:amount' lines into a price list; fall back to one price."""
    out = []
    for line in str(prices_text or "").splitlines():
        if ":" not in line:
            continue
        label, _, raw_amount = line.partition(":")
        label = label.strip()
        try:
            value = int(str(raw_amount).strip())
        except ValueError:
            continue
        if label and value > 0:
            out.append({"label": label[:64], "amount": value})
    if not out:
        out = [{"label": (DEFAULT_TITLE or "Item")[:64], "amount": int(amount)}]
    return out


async def auto_answer_shipping(ctx) -> None:
    """No shipping_query trigger bound: answer with the default option, or
    refuse cleanly when shipping is not configured."""
    amount = int(DEFAULT_SHIPPING.get("amount") or 0)
    if amount > 0:
        option = {
            "id": DEFAULT_SHIPPING["id"],
            "title": DEFAULT_SHIPPING["title"],
            "prices": [{"label": DEFAULT_SHIPPING["label"], "amount": amount}],
        }
        await ctx.adapter.answer_shipping(ctx, ok=True, options=[option])
    else:
        await ctx.adapter.answer_shipping(
            ctx, ok=False, error="Shipping is not available for this order")


async def send_button_invoice(ctx, eng, st: dict, button: dict) -> None:
    """Send the invoice attached to a payment button on a screen."""
    from bot.engine import _to_int

    amount_raw = button.get("pay_amount") or str(DEFAULT_AMOUNT)
    amount = _to_int(await eng.resolve(amount_raw, ctx, st))
    if amount <= 0:
        raise UserInputError("invoice amount must be positive")
    title = str(button.get("text") or DEFAULT_TITLE)[:64]
    payload = ("btn_" + str(button.get("id", "")))[:60]
    provider_token = "" if _stars(DEFAULT_CURRENCY) else cfg.env(PROVIDER_TOKEN_VAR)
    if not _stars(DEFAULT_CURRENCY) and not provider_token:
        raise InternalError("provider payments need " + PROVIDER_TOKEN_VAR + " to be set")
    await ctx.adapter.send_invoice(
        ctx, title, DEFAULT_DESCRIPTION, payload, DEFAULT_CURRENCY, amount,
        provider_token, _stars(DEFAULT_CURRENCY),
    )


async def on_successful_payment(ctx, eng, payload: str, amount: int, currency: str) -> None:
    """Log + confirm a successful payment; triggers may route it into a flow."""
    logger.info("successful payment: {} {} (payload={!r}) from user {}", amount, currency,
        payload, ctx.user_id)
    await eng.db.events.log(ctx.user_id, "payment", {"payload": payload, "amount": amount,
        "currency": currency})
    text = eng._t(ctx, "payment.success", "✅ Payment received, thank you!")
    await ctx.adapter.send_text(ctx, text)
