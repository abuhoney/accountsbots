"""N12 COMPUTE — evaluate a safe expression into a variable.

Handler contract: async handle(node, ctx, eng, st) -> instruction tuple."""
from __future__ import annotations

from bot.errors import InternalError


async def handle(node: dict, ctx, eng, st: dict):
    """Assign the value of an expression or binding to a state variable."""
    cfgd = node.get("cfg") or {}
    variable = cfgd.get("variable", "")
    if not variable:
        raise InternalError("COMPUTE node without a target variable (E015)")
    expression = str(cfgd.get("expression", ""))
    if expression.startswith("@"):
        value = await eng.resolve(expression, ctx, st)
    else:
        value = await eng.eval_expr(expression, st, ctx)
    st["vars"][variable] = value
    return eng.goto(st, node)
