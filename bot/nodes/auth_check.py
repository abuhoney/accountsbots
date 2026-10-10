"""N28 AUTH_CHECK — admin/premium/allowed/not-banned assertion.

Handler contract: async handle(node, ctx, eng, st) -> instruction tuple."""
from __future__ import annotations

from bot import config as cfgmod
from bot.errors import AccessDeniedError, InternalError


async def handle(node: dict, ctx, eng, st: dict):
    """Assert the configured permission; identity is checked on EVERY call."""
    cfgd = node.get("cfg") or {}
    require = cfgd.get("require", "admin")
    ok = True
    if require == "admin":
        ok = bool(ctx.is_admin)
    elif require == "premium":
        ok = bool(ctx.is_premium)
    elif require == "not_banned":
        row = await eng.db.users.get(ctx.user_id)
        ok = not bool((row or {}).get("is_banned"))
    elif require == "allowed_users":
        raw = cfgmod.env(str(cfgd.get("allowedUsersVar") or "ALLOWED_USERS"))
        allowed = {int(p) for p in raw.replace(" ", "").split(",") if p.lstrip("-").isdigit()}
        ok = ctx.user_id in allowed
    else:
        raise InternalError(f"unknown AUTH_CHECK requirement {require!r}")
    if ok:
        return eng.goto(st, node)
    action = cfgd.get("failAction", "message")
    if action == "raise":
        raise AccessDeniedError("auth check failed: " + require)
    if action == "message":
        text = await eng.render_text(
            cfgd.get("failMessage", "You are not allowed to do this."), ctx, st, ""
        )
        await ctx.adapter.send_text(ctx, text)
    return ("end",)
