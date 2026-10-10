"""N14 SEND_AND_WAIT — send a screen and pause for a callback/text.

Handler contract: async handle(node, ctx, eng, st) -> instruction tuple."""
from __future__ import annotations

async def handle(node: dict, ctx, eng, st: dict):
    """Send the screen, then wait for a callback (or text) response."""
    cfgd = node.get("cfg") or {}
    screen_id = cfgd.get("screenId", "")
    if screen_id:
        await eng.render_screen(ctx, st, screen_id, edit=ctx.update_kind == "callback")
    else:
        await ctx.adapter.send_text(ctx, await eng.render_text(cfgd.get("text", ""), ctx, st,
            "HTML"))
    expect = "text" if cfgd.get("expect") == "text" else "callback"
    ttl = int(cfgd.get("timeoutSeconds") or 300)
    return ("wait", expect, ttl, {"variable": cfgd.get("variable", "")})
