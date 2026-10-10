"""N04 ASK — pause the flow, wait for validated user input.

Handler contract: async handle(node, ctx, eng, st) -> instruction tuple."""
from __future__ import annotations

from bot.errors import InternalError


async def handle(node: dict, ctx, eng, st: dict):
    """Ask a question and wait; the answer lands in the state variable."""
    cfgd = node.get("cfg") or {}
    variable = cfgd.get("variable", "")
    if not variable:
        raise InternalError("ASK node without an input variable (E015)")
    screen_id = cfgd.get("screenId", "")
    if screen_id:
        await eng.render_screen(ctx, st, screen_id)
    else:
        prompt = cfgd.get("prompt", "")
        if prompt:
            text = await eng.render_text(prompt, ctx, st, "")
        else:
            text = "Please send " + cfgd.get("inputType", "text") + ":"
        await ctx.adapter.send_text(ctx, text)
    ttl = int(cfgd.get("timeoutSeconds") or 300)
    return ("wait", "text", ttl, {"variable": variable})
