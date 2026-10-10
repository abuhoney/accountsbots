"""N16 END — terminate the flow and clear the session.

Handler contract: async handle(node, ctx, eng, st) -> instruction tuple."""
from __future__ import annotations

async def handle(node: dict, ctx, eng, st: dict):
    """Optionally send a final message, then end the flow."""
    cfgd = node.get("cfg") or {}
    message = cfgd.get("endMessage", "")
    if message:
        text = await eng.render_text(message, ctx, st, "HTML")
        await ctx.adapter.send_text(ctx, text)
    return ("end",)
