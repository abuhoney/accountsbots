"""N01 TRIGGER — flow entry point; continues to the default edge.

Handler contract: async handle(node, ctx, eng, st) -> instruction tuple."""
from __future__ import annotations

async def handle(node: dict, ctx, eng, st: dict):
    """Continue from the flow entry point."""
    return eng.goto(st, node)
