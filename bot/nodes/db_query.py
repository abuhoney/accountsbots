"""N10 DB_QUERY — repository operation on a designed table.

Handler contract: async handle(node, ctx, eng, st) -> instruction tuple."""
from __future__ import annotations

from bot.engine import _to_bool, _to_float, _to_int, _to_str
from bot.errors import InternalError


async def handle(node: dict, ctx, eng, st: dict):
    """Run insert/select/update/delete/count via the repository interface."""
    cfgd = node.get("cfg") or {}
    op = cfgd.get("op", "select")
    table = cfgd.get("table", "")
    if not table:
        raise InternalError("DB_QUERY node without a table (E013)")
    repo = eng.db.custom(table)
    fields = await eng.resolve_many(cfgd.get("fields") or {}, ctx, st)
    where = await eng.resolve_many(cfgd.get("where") or {}, ctx, st)
    col_types = cfgd.get("__dbcoerce") or {}
    for target in (fields, where):
        for col in sorted(target):
            if target[col] is None or col not in col_types:
                continue
            ctype = col_types[col]
            if ctype in ("int", "bigint"):
                target[col] = _to_int(target[col])
            elif ctype in ("float", "decimal"):
                target[col] = _to_float(target[col])
            elif ctype == "bool":
                target[col] = _to_bool(target[col])
            elif ctype in ("string", "text", "enum", "uuid"):
                target[col] = _to_str(target[col])
    scope = eng.db.tenant_scope(table)
    if scope == "user":
        where.setdefault("user_id", ctx.user_id)
    elif scope == "chat":
        where.setdefault("chat_id", ctx.chat_id)
    limit = int(cfgd.get("limit") or 100)
    offset = int(cfgd.get("offset") or 0)
    order_by = str(cfgd.get("orderBy") or "")
    if op == "insert":
        result = await repo.insert(fields)
    elif op == "select":
        result = await repo.list(where, limit=limit, offset=offset, order_by=order_by)
    elif op == "update":
        result = await repo.update_where(where, fields)
    elif op == "delete":
        result = await repo.delete_where(where)
    elif op == "count":
        result = await repo.count(where)
    else:
        raise InternalError(f"unknown DB operation {op!r}")
    variable = cfgd.get("resultVar", "")
    if variable:
        st["vars"][variable] = result
    return eng.goto(st, node)
