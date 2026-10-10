"""N05 CONDITION — first true edge wins; default edge is the else branch.

Handler contract: async handle(node, ctx, eng, st) -> instruction tuple."""
from __future__ import annotations

async def handle(node: dict, ctx, eng, st: dict):
    """Evaluate outgoing edge conditions in declaration order."""
    return ("goto", await eng.choose_branch(ctx, st, node))
