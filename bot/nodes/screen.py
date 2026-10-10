"""N03 SCREEN — render a designed screen (message + media + buttons).

Handler contract: async handle(node, ctx, eng, st) -> instruction tuple."""
from __future__ import annotations

from bot.errors import InternalError


async def handle(node: dict, ctx, eng, st: dict):
    """Render the configured screen; optionally edit the current message."""
    cfgd = node.get("cfg") or {}
    screen_id = cfgd.get("screenId", "")
    if not screen_id:
        raise InternalError("SCREEN node without a screen id")
    await eng.render_screen(ctx, st, screen_id, edit=bool(cfgd.get("editMessage")))
    return eng.goto(st, node)
