"""Universal flow engine (Sections 5 & 6): graph walking runtime shared by all
four libraries. Node handlers live in bot/nodes/ and are dispatched by type.
Expressions run through an AST whitelist walker — eval/exec are never used."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import ast
import base64
import binascii
import hashlib
import operator
import os
import re
import secrets
import time
import uuid



from loguru import logger

from bot import config as cfg
from bot.errors import (AccessDeniedError, BotError, InternalError, RateLimitError, UserInputError,
    handle_exception)
from bot.flows import FLOWS, I18N_ENABLED, SCREENS, TRIGGERS
from bot.i18n import SUPPORTED_LANGUAGES, t as i18n_t
from bot.state import DEFAULT_TTL_SECONDS, StateManager


MAX_STEPS = 500
CB_SEP = "|"
CB_MAX_BYTES = 64

_NODE_HANDLERS: dict[str, Any] | None = None


def node_handlers() -> dict[str, Any]:
    """Lazily import the node registry (bot.nodes imports bot.engine)."""
    global _NODE_HANDLERS
    if _NODE_HANDLERS is None:
        from bot.nodes import NODE_HANDLERS as _registry

        _NODE_HANDLERS = _registry
    return _NODE_HANDLERS

_INPUT_PATTERNS = {
    "number": re.compile(r"^-?\d+(\.\d+)?$"),
    "url": re.compile(r"^https?://[^\s]+$", re.IGNORECASE),
    "email": re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"),
    "phone": re.compile(r"^\+?[0-9][0-9\s\-()]{6,19}$"),
    "channel": re.compile(
        r"^(@[A-Za-z][A-Za-z0-9_]{3,31}|https?://t\.me/[A-Za-z][A-Za-z0-9_]{3,31}"
        r"|-?\d{5,20})$"
    ),
}
# __MBM_EXT_BOOL_ARABIC__
_TRUE_STRINGS = {"true", "1", "yes", "y", "on", "نعم", "صحيح", "موافق"}
_FALSE_STRINGS = {"false", "0", "no", "n", "off", "", "لا", "خطأ", "مرفوض"}


# ═══════════════════ safe expression evaluation (Section 6.3) ═══════════════════
# The engine NEVER calls eval()/exec(). Expressions are parsed with ast and
# walked against a strict whitelist: literals, names (state variables),
# attribute access on ctx.* / env.* only, arithmetic/comparison/boolean
# operators, subscripts, list/dict/tuple/set literals and whitelisted calls.


def _now() -> int:
    """Current unix epoch (whitelisted expression function)."""
    return int(time.time())


def _b64encode(value: Any) -> str:
    raw = value if isinstance(value, (bytes, bytearray)) else str(value).encode("utf-8")
    return base64.b64encode(bytes(raw)).decode("ascii")


def _b64decode(value: Any) -> bytes:
    raw = value if isinstance(value, (bytes, bytearray)) else str(value).encode("ascii")
    try:
        return base64.b64decode(bytes(raw), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise UserInputError(f"invalid base64 value: {exc}") from exc


def _sha256(value: Any) -> str:
    raw = value if isinstance(value, (bytes, bytearray)) else str(value).encode("utf-8")
    return hashlib.sha256(bytes(raw)).hexdigest()


# === Patched: marketplace-design helpers (Section 5.1 of audit) ===
def _encrypt_session(raw: str) -> str:
    """Encrypt a Telethon/Pyrogram session string with Fernet key from SESSION_ENCRYPTION_KEY env var."""
    from cryptography.fernet import Fernet
    key = os.environ.get("SESSION_ENCRYPTION_KEY", "").encode()
    if not key:
        raise UserInputError("SESSION_ENCRYPTION_KEY env var is not set; cannot encrypt session string")
    return Fernet(key).encrypt(str(raw).encode("utf-8")).decode("ascii")


def _format_orders(orders: Any) -> str:
    """Render a list of order dicts as a Telegram-friendly multi-line summary. Falls back to Arabic 'no orders' string."""
    if not orders:
        return "لا توجد طلبات بعد."
    try:
        return "\n".join(
            f'#{o["id"]} — {o["price_stars"]} ⭐ — {o["status"]}' for o in orders
        )
    except (KeyError, TypeError, IndexError):
        return "لا توجد طلبات بعد."


def _is_yes(value: Any) -> bool:
    """Bilingual boolean coercion: yes/y/نعم/true/1 → True; everything else → False."""
    if not isinstance(value, str):
        return bool(value)
    return value.strip().lower() in {"yes", "y", "نعم", "true", "1"}


# __MBM_EXT_REGROUP_CLEANED__ — legacy _re_group removed (F45)

# __MBM_EXT_REGROUP__ — dict-aware regex extraction
def _re_group(name_or_pattern: str, text: Any, pattern: str | None = None) -> str | None:
    """Extract a named or numbered regex group from text."""
    if isinstance(text, dict):
        text = text.get("payload") or text.get("text") or ""
    if isinstance(text, (bytes, bytearray)):
        try:
            text = bytes(text).decode("utf-8", "replace")
        except Exception:
            text = ""
    text = str(text or "")
    try:
        if pattern:
            m = re.search(pattern, text)
            if not m:
                return None
            if name_or_pattern in (m.groupdict() or {}):
                return m.group(name_or_pattern)
            try:
                idx = int(name_or_pattern)
                return m.group(idx)
            except (ValueError, IndexError):
                try:
                    return m.group(1)
                except IndexError:
                    return m.group(0)
        m = re.search(r"(\d+)", text)
        return m.group(1) if m else None
    except re.error:
        return None


def _str_lower(value: Any) -> str:
    """str_lower — alias for lower() that accepts non-string input gracefully."""
    return str(value).lower() if value is not None else ""


def _is_admin(user_id: Any) -> bool:
    """Check whether user_id is in the ADMINS env var (comma-separated)."""
    admins = os.environ.get("ADMINS", "")
    if not admins:
        return False
    try:
        admin_ids = {int(x.strip()) for x in admins.split(",") if x.strip()}
        return int(user_id) in admin_ids
    except (ValueError, TypeError):
        return str(user_id) in {x.strip() for x in admins.split(",")}


def _fmt_stars(amount: Any) -> str:
    """Format a Stars amount with thousands separator and ⭐ suffix."""
    try:
        return f"{int(amount):,} ⭐"
    except (ValueError, TypeError):
        return f"{amount} ⭐"


def _esc_html(text: Any) -> str:
    """Escape HTML special characters in user-provided text for safe HTML parseMode rendering."""
    return (str(text) if text is not None else "").replace("&", "&amp;").replace("<",
        "&lt;").replace(">", "&gt;")


def _default(value: Any, fallback: Any) -> Any:
    """Return value if it's not None/empty, else fallback. Useful for templates with optional fields."""
    if value is None or value == "" or (isinstance(value, (list, dict, str)) and len(value) == 0):
        return fallback
    return value


_SAFE_CALLS: dict[str, Any] = {
    "len": len, "int": int, "float": float, "str": str, "bool": bool,
    "list": list, "dict": dict, "set": set, "tuple": tuple,
    "min": min, "max": max, "sum": sum, "abs": abs, "round": round,
    "sorted": sorted, "reversed": reversed,
    "now": _now,
    "rlong": lambda: secrets.randbits(64),
    "rbytes": lambda: secrets.token_bytes(16),
    "uuid4": lambda: str(uuid.uuid4()),
    "b64encode": _b64encode,
    "b64decode": _b64decode,
    "sha256": _sha256,
    "re.match": re.match, "re.search": re.search, "re.findall": re.findall,
    # === Patched: marketplace helpers registered on the runtime side ===
    "encrypt_session": _encrypt_session,
    "format_orders": _format_orders,
    "is_yes": _is_yes,
    "re_group": _re_group,
    "str_lower": _str_lower,
    "is_admin": _is_admin,
    "fmt_stars": _fmt_stars,
    "esc_html": _esc_html,
    "default": _default,
}
_VALUE_METHODS = {"startswith", "endswith", "lower", "upper", "strip", "split", "join"}
_BIN_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}
_CMP_OPS = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
    ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b,
    ast.Is: operator.is_, ast.IsNot: operator.is_not,
}
_CTX_FIELDS = (
    "chat_id", "user_id", "message_id", "text", "reply_to", "is_admin",
    "language", "username", "first_name", "chat_type", "is_premium",
    "callback_data", "inline_query_id", "args", "start_param",
    "payment_charge_id", "passport", "shipping", "payment", "media", "raw",
)


class _CtxView:
    """Read-only view exposing whitelisted ctx fields to expressions."""

    def __init__(self, ctx: Any) -> None:
        object.__setattr__(self, "_ctx", ctx)

    def __getattr__(self, name: str) -> Any:
        if name in _CTX_FIELDS:
            return getattr(object.__getattribute__(self, "_ctx"), name, None)
        raise UserInputError(f"ctx has no field '{name}'")


class _EnvView:
    """Read-only view exposing declared environment variables."""

    def __getattr__(self, name: str) -> str:
        return cfg.env(name)


def _eval_node(node: ast.AST, env: dict[str, Any]) -> Any:
    """Walk a whitelisted AST. Anything outside the subset raises."""
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, env)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id == "True":
            return True
        if node.id == "False":
            return False
        if node.id == "None":
            return None
        if node.id in env:
            return env[node.id]
        raise UserInputError(f"unknown name '{node.id}' in expression")
    if isinstance(node, ast.Attribute):
        base = _eval_node(node.value, env)
        if isinstance(base, (_CtxView, _EnvView)):
            return getattr(base, node.attr)
        if isinstance(base, dict):
            # derived/nested access: ctx.payment.amount, row.balance, …
            return base.get(node.attr)
        raise UserInputError(
            "attribute access is allowed on ctx.*, env.* and dict values only")
    if isinstance(node, ast.BoolOp):
        result: Any = False
        if isinstance(node.op, ast.And):
            for value in node.values:
                result = _eval_node(value, env)
                if not result:
                    return result
            return result
        for value in node.values:
            result = _eval_node(value, env)
            if result:
                return result
        return result
    if isinstance(node, ast.UnaryOp):
        value = _eval_node(node.operand, env)
        if isinstance(node.op, ast.Not):
            return not value
        if isinstance(node.op, ast.USub):
            return -value
        if isinstance(node.op, ast.UAdd):
            return +value
        raise UserInputError("unsupported unary operator")
    if isinstance(node, ast.BinOp):
        func = _BIN_OPS.get(type(node.op))
        if func is None:
            raise UserInputError("unsupported binary operator")
        left = _eval_node(node.left, env)
        right = _eval_node(node.right, env)
        if isinstance(node.op, ast.Pow) and (abs(right if isinstance(right, (int,
            float)) else 0) > 64):
            raise UserInputError("exponent too large (max 64)")
        try:
            return func(left, right)
        except (TypeError, ValueError, ZeroDivisionError) as exc:
            raise UserInputError(f"cannot compute expression: {exc}") from exc
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, env)
        for op_node, comparator in zip(node.ops, node.comparators):
            func = _CMP_OPS.get(type(op_node))
            if func is None:
                raise UserInputError("unsupported comparison")
            right = _eval_node(comparator, env)
            try:
                ok = bool(func(left, right))
            except TypeError as exc:
                raise UserInputError(f"cannot compare values: {exc}") from exc
            if not ok:
                return False
            left = right
        return True
    if isinstance(node, ast.Call):
        fname = None
        if isinstance(node.func, ast.Name):
            fname = node.func.id
        elif (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "re"
        ):
            fname = "re." + node.func.attr
        if fname and fname in _SAFE_CALLS and not node.keywords:
            args = [_eval_node(a, env) for a in node.args]
            try:
                return _SAFE_CALLS[fname](*args)
            except (TypeError, ValueError) as exc:
                raise UserInputError(f"call failed: {exc}") from exc
        is_value_method = (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in _VALUE_METHODS
            and not node.keywords
        )
        if is_value_method:
            target = _eval_node(node.func.value, env)
            method = getattr(target, node.func.attr, None)
            if callable(method):
                args = [_eval_node(a, env) for a in node.args]
                try:
                    return method(*args)
                except (TypeError, ValueError) as exc:
                    raise UserInputError(f"method call failed: {exc}") from exc
        raise UserInputError("call is not in the safe-function whitelist")
    if isinstance(node, ast.Subscript):
        target = _eval_node(node.value, env)
        if isinstance(node.slice, ast.Slice):
            low = _eval_node(node.slice.lower, env) if node.slice.lower else None
            high = _eval_node(node.slice.upper, env) if node.slice.upper else None
            try:
                return target[low:high]
            except TypeError as exc:
                raise UserInputError(f"cannot slice value: {exc}") from exc
        index = _eval_node(node.slice, env)
        try:
            return target[index]
        except (KeyError, IndexError, TypeError) as exc:
            raise UserInputError(f"cannot index value: {exc}") from exc
    if isinstance(node, ast.List):
        return [_eval_node(e, env) for e in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_eval_node(e, env) for e in node.elts)
    if isinstance(node, ast.Set):
        return {_eval_node(e, env) for e in node.elts}
    if isinstance(node, ast.Dict):
        return {_eval_node(k, env): _eval_node(v, env) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.IfExp):
        return _eval_node(node.body, env) if _eval_node(node.test,
            env) else _eval_node(node.orelse, env)
    raise UserInputError(f"unsupported expression element: {type(node).__name__}")


def _safe_eval(expr: str, env: dict[str, Any]) -> Any:
    """Evaluate a whitelisted expression. Never uses eval/exec/import."""
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise UserInputError(f"expression syntax error: {exc.msg}") from exc
    return _eval_node(tree, env)


# ═══════════════════ explicit type coercions (Section 13) ═══════════════════


# __MBM_EXT_ENV_COERCE__ — safe env coercion for numeric env vars
def _env_int(name: str, default: int = 0) -> int:
    """Read an int env var, falling back to default on missing/invalid."""
    try:
        return int(cfg.env(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float = 0.0) -> float:
    """Read a float env var, falling back to default on missing/invalid."""
    try:
        return float(cfg.env(name, str(default)))
    except (TypeError, ValueError):
        return default


def _to_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value).strip(), 10)
    except (TypeError, ValueError) as exc:
        raise UserInputError(f"expected a whole number, got {value!r}") from exc


def _to_float(value: Any) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise UserInputError(f"expected a number, got {value!r}") from exc


def _to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode("utf-8", "replace")
    return str(value)


def _to_bool(value: Any) -> bool:
    """Accept true/1/yes/y/on (case-insensitive); reject everything else."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value or "").strip().lower()
    if text in _TRUE_STRINGS:
        return True
    if text in _FALSE_STRINGS:
        return False
    raise UserInputError(
        f"cannot interpret {value!r} as a boolean "
        "(accepted: true/1/yes/y/on, false/0/no/n/off)"
    )


def _to_bytes(value: Any) -> bytes:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    return str(value).encode("utf-8")


# ═══════════════════ callback codec (Section 10) ═══════════════════


def _cb(verb: str, ref: str = "", key: str = "", payload: str = "") -> str:
    """Encode callback data as '<verb>|<ref>|<key>|<payload>' (max 64 bytes)."""
    parts = [verb]
    if ref or key or payload:
        parts.append(ref)
    if key or payload:
        parts.append(key)
    if payload:
        parts.append(payload)
    data = CB_SEP.join(parts)
    if len(data.encode("utf-8")) > CB_MAX_BYTES:
        raise InternalError(f"callback_data exceeds {CB_MAX_BYTES} bytes: {data!r}")
    return data


def _cb_parse(data: str) -> dict[str, str]:
    """Decode callback data produced by _cb()."""
    parts = (data or "").split(CB_SEP)
    while len(parts) < 4:
        parts.append("")
    return {"verb": parts[0], "ref": parts[1], "key": parts[2], "payload": CB_SEP.join(parts[3:])}


# ═══════════════════ template formatting (Section 10) ═══════════════════


class _SafeDict(dict):
    """format_map mapping that turns unknown keys into empty strings."""

    def __missing__(self, key: str) -> str:
        return ""


class _DictFormatProxy:
    """Renders nested dicts inside templates: {ctx.payment.amount}."""

    def __init__(self, data: dict, parse_mode: str) -> None:
        object.__setattr__(self, "_data", data or {})
        object.__setattr__(self, "_pm", parse_mode)

    def _wrap(self, value: Any) -> Any:
        if isinstance(value, dict):
            return _DictFormatProxy(value, object.__getattribute__(self, "_pm"))
        return _escape_value(value, object.__getattribute__(self, "_pm"))

    def __getattr__(self, name: str) -> Any:
        return self._wrap(object.__getattribute__(self, "_data").get(name, ""))

    def __getitem__(self, name: Any) -> Any:
        return self._wrap(object.__getattribute__(self, "_data").get(name, ""))


class _CtxFormatProxy:
    """Makes {ctx.field} work inside str.format_map: the formatter treats
    'ctx.field' as getattr(mapping['ctx'], 'field'); dict-valued fields
    (payment/shipping/passport/media) return a nested proxy."""

    def __init__(self, ctx: Any, parse_mode: str) -> None:
        object.__setattr__(self, "_ctx", ctx)
        object.__setattr__(self, "_pm", parse_mode)

    def __getattr__(self, name: str) -> Any:
        if name in _CTX_FIELDS:
            value = getattr(object.__getattribute__(self, "_ctx"), name, "")
            if isinstance(value, dict):
                return _DictFormatProxy(value, object.__getattribute__(self, "_pm"))
            return _escape_value(value, object.__getattribute__(self, "_pm"))
        return ""

    def __getitem__(self, name: str) -> Any:
        return self.__getattr__(str(name))


_MD2_ESCAPES = set('_*[]()~`>#+-=|{}.!')


def _escape_value(value: Any, parse_mode: str) -> str:
    # __MBM_EXT_INT_TEMPLATE__ — dicts/lists render as compact JSON instead of str()
    if isinstance(value, dict):
        try:
            import json as _json
            text = _json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            text = str(value)
    elif isinstance(value, (list, tuple)):
        try:
            import json as _json
            text = _json.dumps(list(value), ensure_ascii=False, default=str)
        except Exception:
            text = str(value)
    else:
        text = _to_str(value)
    if parse_mode == "HTML":
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if parse_mode == "MarkdownV2":
        return "".join("\\" + ch if ch in _MD2_ESCAPES else ch for ch in text)
    if parse_mode == "Markdown":
        for ch in ("\\", "*", "_", "`", "["):
            text = text.replace(ch, "\\" + ch)
        return text
    return text


def _format_template(tmpl: str, variables: dict, ctx: Any, parse_mode: str = "", lang: str = "en",
    t_func=None) -> str:
    """Substitute {var} / {ctx.field} / {env.VAR} / {t:key}; {{ and }} stay literal braces.

    Unknown keys become empty strings (never raises KeyError) and every
    substituted value is escaped for the active parse mode (Section 27).
    """
    # __MBM_EXT_T_KEY__ — pre-substitute {t:key} BEFORE format_map
    tmpl = _apply_t_key(str(tmpl or ""), lang, t_func)
    mapping = _SafeDict()
    for name, value in (variables or {}).items():
        mapping[str(name)] = _escape_value(value, parse_mode)
    for name in _CTX_FIELDS:
        mapping["ctx." + name] = _escape_value(getattr(ctx, name, ""), parse_mode)
    mapping["ctx"] = _CtxFormatProxy(ctx, parse_mode)
    # === Patched: substitute {env.VAR_NAME} templates from os.environ (Section 5.5 of audit) ===
    env_proxy = _SafeDict()
    for env_name in ("BOT_TOKEN", "ADMINS", "LOG_LEVEL", "DATABASE_URL",
                      "ESCROW_STARS_PROVIDER_TOKEN", "PLATFORM_FEE_PERCENT",
                      "SUPPORT_CHAT_ID", "REVIEWS_CHANNEL_ID", "SESSION_ENCRYPTION_KEY",
                      "MIN_LISTING_PRICE", "MAX_LISTING_PRICE", "AUTO_RELEASE_HOURS",
                      "PAYMENT_PROVIDER_TOKEN", "WEBHOOK_URL", "WEBHOOK_SECRET",
                      "OPENAI_API_KEY", "CHANNEL"):
        env_proxy[env_name] = _escape_value(os.environ.get(env_name, ""), parse_mode)
    # Also dynamically expose any env var referenced in the template that we haven't pre-listed
    import re as _re
    for m in _re.finditer(r"{env.([A-Z_][A-Z0-9_]*)}", str(tmpl or "")):
        env_proxy.setdefault(m.group(1), _escape_value(os.environ.get(m.group(1), ""), parse_mode))
    mapping["env"] = env_proxy
    try:
        return str(tmpl or "").format_map(mapping)
    except (ValueError, IndexError, AttributeError, KeyError) as exc:
        logger.warning("template formatting failed ({}); sending raw template", exc)
        return str(tmpl or "")


def _dhash(text: str, length: int = 8) -> str:
    """Deterministic hash — mirrors the generator's U.dhash (UTF-16 units)."""
    data = text.encode("utf-16-le")
    units = [int.from_bytes(data[i:i + 2], "little") for i in range(0, len(data), 2)]
    h1 = 0x811C9DC5
    h2 = 0x1000193
    mask = 0xFFFFFFFF
    for i, unit in enumerate(units):
        h1 = ((h1 ^ unit) * 16777619) & mask
        h2 = (((h2 + unit + i) & mask) * 2654435761) & mask
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"

    def base36(num: int) -> str:
        if num == 0:
            return "0"
        out = ""
        while num > 0:
            num, rem = divmod(num, 36)
            out = alphabet[rem] + out
        return out

    return (base36(h1) + base36(h2)).ljust(12, "0")[:length]


# __MBM_EXT_T_KEY__ — support {t:key} translation in ANY template
_T_KEY_RE = re.compile(r"{t:([A-Za-z0-9_.]+)}")


def _apply_t_key(text, lang, t_func):
    """Replace {t:key} markers with translated strings."""
    if t_func is None:
        return text
    # __MBM_EXT_T_ESCAPE__ — translator values are trusted
    # they are NOT re-escaped to preserve inline HTML tags
    return _T_KEY_RE.sub(lambda m: t_func(lang, m.group(1)) or m.group(0), text)


_PATH_SEG_RE = re.compile(
    r"""\[(?:"([^"]*)"|'([^']*)'|(-?\d+))\]|\.([A-Za-z0-9_]+)""")


def _row_to_dict(item: Any) -> Any:
    """__MBM_EXT_ROW_NORM__ — convert SQLAlchemy Row / named tuple to dict."""
    if isinstance(item, dict):
        return item
    if hasattr(item, "_mapping"):
        return dict(item._mapping)
    if hasattr(item, "_asdict"):
        return item._asdict()
    return item


def _resolve_path(container: Any, path: str) -> Any:
    """Walk 'name', 'name.field', 'name[0]', 'name[0]["key"]' paths safely."""
    # __MBM_EXT_RESOLVE_PATH_FIXED__
    head_match = re.match(r"^\s*([A-Za-z0-9_]+)", path or "")
    if head_match is None:
        return None
    head = head_match.group(1)
    if isinstance(container, dict):
        value = container.get(head)
    else:
        value = getattr(container, head, None)
    for seg in _PATH_SEG_RE.finditer(path, head_match.end()):
        if value is None:
            return None
        if seg.group(1) is not None:
            key: Any = seg.group(1)
        elif seg.group(2) is not None:
            key = seg.group(2)
        elif seg.group(3) is not None:
            key = int(seg.group(3))
        else:
            key = seg.group(4)
        if isinstance(value, dict):
            if key in value:
                value = value[key]
            else:
                value = value.get(str(key))
        elif isinstance(value, (list, tuple)) and isinstance(key, int):
            try:
                value = value[key]
            except IndexError:
                return None
        else:
            value = getattr(value, str(key), None)
        if value is not None:
            value = _row_to_dict(value)
    return value


def _parse_literal(rest: str) -> Any:
    if rest in ("true", "True"):
        return True
    if rest in ("false", "False"):
        return False
    if rest in ("None", "null"):
        return None
    try:
        return int(rest, 10)
    except ValueError:
        pass
    try:
        return float(rest)
    except ValueError:
        return rest


_FULL_BINDING_RE = re.compile(
    r"^@(?:random_long|random_bytes|now_iso|now|uuid4)$"
    r"|^@(?:ctx|input|steps|env)\.[A-Za-z0-9_.]+$"
    r"|^@db\.[A-Za-z0-9_.]+$"
    r"|^@literal\.[^\s].*$"
    r"|^@expr\.[^\s].*$"
)
_BINDING_EXPR_RE = re.compile(r"@(ctx|input|steps|env|db)\.([A-Za-z0-9_.]+)")
_BINDING_BARE_RE = re.compile(r"@(random_long|random_bytes|now_iso|now|uuid4)\b")


def _normalize_expr(expr: str) -> str:
    """Rewrite @bindings inside an expression into evaluable names."""
    def repl_dotted(match: re.Match) -> str:
        root, rest = match.group(1), match.group(2)
        if root == "ctx":
            return "ctx." + rest
        if root == "env":
            return "env." + rest
        if root == "db":
            raise UserInputError(
                "@db bindings are not supported inside expressions; use a DB_QUERY node first"
            )
        return rest  # keep the full path: row.field evaluates via dict-aware attr access

    out = _BINDING_EXPR_RE.sub(repl_dotted, expr)
    out = _BINDING_BARE_RE.sub(lambda m: {"now": "now()", "now_iso": "now_iso()",
        "random_long": "rlong()", "random_bytes": "rbytes()", "uuid4": "uuid4()"}[m.group(1)], out)
    return out


# ═══════════════════ context object ═══════════════════


class Ctx:
    """Library-neutral update context filled in by the library handlers."""

    __slots__ = (
        "adapter", "user_id", "chat_id", "message_id", "text", "username",
        "first_name", "language", "chat_type", "is_premium", "reply_to",
        "callback_data", "inline_query_id", "args", "raw", "is_admin",
        "update_kind", "media", "pre_checkout", "start_param",
        "payment_charge_id", "passport", "shipping", "payment",
        "_answered",  # __MBM_EXT_CTX_ANSWERED__
    )

    def __init__(self, adapter: Any, **kwargs: Any) -> None:
        self.adapter = adapter
        self.user_id: int = int(kwargs.get("user_id") or 0)
        self.chat_id: int = int(kwargs.get("chat_id") or 0)
        self.message_id: int = int(kwargs.get("message_id") or 0)
        self.text: str = str(kwargs.get("text") or "")
        self.username: str = str(kwargs.get("username") or "")
        self.first_name: str = str(kwargs.get("first_name") or "")
        self.language: str = str(kwargs.get("language") or "en")
        self.chat_type: str = str(kwargs.get("chat_type") or "private")
        self.is_premium: bool = bool(kwargs.get("is_premium"))
        self.reply_to: int = int(kwargs.get("reply_to") or 0)
        self.callback_data: str = str(kwargs.get("callback_data") or "")
        self.inline_query_id: str = str(kwargs.get("inline_query_id") or "")
        self.args: list[str] = list(kwargs.get("args") or [])
        self.raw: Any = kwargs.get("raw")
        self.is_admin: bool = bool(kwargs.get("is_admin"))
        self.update_kind: str = str(kwargs.get("update_kind") or "message")
        self.media: dict[str, Any] = dict(kwargs.get("media") or {})
        self.pre_checkout: dict[str, Any] = dict(kwargs.get("pre_checkout") or {})
        self.start_param: str = str(kwargs.get("start_param") or "")
        self.payment_charge_id: str = str(kwargs.get("payment_charge_id") or "")
        self.passport: dict[str, Any] = dict(kwargs.get("passport") or {})
        self.shipping: dict[str, Any] = dict(kwargs.get("shipping") or {})
        self.payment: dict[str, Any] = dict(kwargs.get("payment") or {})


# ═══════════════════ the engine ═══════════════════


class FlowEngine:
    """Walks the flow graph, keeps per-user state and dispatches updates.

    Semantics (Section 6.5): every node type has a handler in bot/nodes/;
    handlers return instruction tuples:
      ("goto", node_id | None) — continue at node_id (None = dead end)
      ("wait", kind, ttl)      — pause for user input/callback
      ("end",)                 — flow finished, state cleared
      ("ret", value)           — return from a sub-flow
      ("jump", node_id)        — unconditional jump
    """

    def __init__(self, adapter: Any, state: StateManager, db: Any, ratelimit: Any = None) -> None:
        self.adapter = adapter
        self.state = state
        self.db = db
        self.ratelimit = ratelimit
        self.t = i18n_t if I18N_ENABLED else None
        self._cooldowns: dict[str, float] = {}
        self.http_client = None
        self.userbot = None

    async def startup(self) -> None:
        """Create shared resources (single httpx client, Section 28)."""
        try:
            import httpx

            self.http_client = httpx.AsyncClient(timeout=20.0, follow_redirects=True)
        except Exception:
            logger.exception("httpx unavailable; HTTP_REQUEST nodes will create per-call clients")
        self.state.start_sweeper()

    async def shutdown(self) -> None:
        """Close shared resources on graceful shutdown."""
        if self.http_client is not None:
            await self.http_client.aclose()
            self.http_client = None
        await self.state.stop()

    # ─────────────────────── update entry points ───────────────────────

    async def handle_command(self, name: str, ctx: Ctx) -> None:
        """Entry point for command updates (library handlers call this)."""
        async with self.state.lock_for(ctx.user_id, ctx.chat_id):
            try:
                await self._command(name, ctx)
            except Exception as exc:
                await self._fail(ctx, exc)

    async def handle_message(self, ctx: Ctx) -> None:
        """Entry point for plain text/media messages."""
        async with self.state.lock_for(ctx.user_id, ctx.chat_id):
            try:
                await self._message(ctx)
            except Exception as exc:
                await self._fail(ctx, exc)

    async def handle_callback(self, ctx: Ctx) -> None:
        """Entry point for callback queries."""
        async with self.state.lock_for(ctx.user_id, ctx.chat_id):
            try:
                await self._callback(ctx)
            except Exception as exc:
                await self._fail(ctx, exc)

    async def handle_inline(self, ctx: Ctx) -> None:
        """Entry point for inline queries."""
        async with self.state.lock_for(ctx.user_id, ctx.chat_id):
            try:
                trigger = self._match_trigger("inline_query", ctx.text, ctx)
                if trigger is None:
                    await self.adapter.answer_inline(ctx,
                        [{"title": "No results", "text": "Send /start to the bot first."}])
                    return
                await self._start_flow(trigger, ctx)
            except Exception as exc:
                await self._fail(ctx, exc)

    async def handle_special(self, kind: str, ctx: Ctx) -> None:
        """Entry point for channel_post/chat_member/join_request/poll_answer/
        pre_checkout/successful_payment/web_app_data/custom updates."""
        async with self.state.lock_for(ctx.user_id, ctx.chat_id):
            try:
                if kind == "pre_checkout":
                    await self.adapter.answer_pre_checkout(ctx, ok=True)
                    return
                trigger = self._match_trigger(kind, ctx.text, ctx)
                if trigger is not None:
                    await self._start_flow(trigger, ctx)
                    return
                if kind == "shipping_query":
                    from bot import payments as payments_mod

                    await payments_mod.auto_answer_shipping(ctx)
                    return
                if kind == "successful_payment":
                    logger.info("successful payment from {} (no trigger bound)", ctx.user_id)
            except Exception as exc:
                await self._fail(ctx, exc)

    async def run_flow_for_chat(self, flow_id: str, chat_id: int,
        variables: dict | None = None) -> None:
        """Run a flow against a stored chat (used by the scheduler)."""
        ctx = Ctx(self.adapter, chat_id=chat_id, user_id=chat_id, update_kind="scheduler")
        flow = FLOWS.get(flow_id)
        if flow is None:
            logger.error("scheduled flow {} not found", flow_id)
            return
        async with self.state.lock_for(ctx.user_id, ctx.chat_id):
            try:
                st = self.state.fresh(flow_id=flow_id, node_id=flow["start"])
                st["vars"].update(variables or {})
                await self.state.save(ctx.user_id, ctx.chat_id, st)
                await self._flow_run(ctx, st, flow["start"])
            except Exception as exc:
                await self._fail(ctx, exc)

    async def _fail(self, ctx: Ctx, exc: BaseException) -> None:
        await handle_exception(ctx, exc, self.adapter, self.t)

    # ─────────────────────── command routing ───────────────────────

    async def _command(self, name: str, ctx: Ctx) -> None:
        if name == "start" and ctx.args and not ctx.start_param:
            ctx.start_param = str(ctx.args[0])
        if name == "cancel":
            await self.state.clear(ctx.user_id, ctx.chat_id)
            await self.adapter.send_text(ctx, self._t(ctx, "cancel.done",
                "Cancelled. Send /start to begin again."))
            return
        if name == "back":
            await self._back(ctx)
            return
        if I18N_ENABLED and name == "language":
            await self._set_language(ctx)
            return
        if self.ratelimit is not None and not await self.ratelimit.allow(ctx):
            return
        trigger = self._match_trigger("command", name, ctx)
        if trigger is None:
            if name == "help":
                await self.adapter.send_text(ctx, self._help_text(ctx), "HTML")
            else:
                await self.adapter.send_text(ctx, self._t(ctx, "cmd.unknown",
                    "Unknown command. Send /help to see what I can do."))
            return
        await self._start_flow(trigger, ctx)

    def _help_text(self, ctx: Ctx) -> str:
        lines = ["<b>" + _escape_value("Telegram Accounts Marketplace", "HTML") + "</b>", ""]
        if self.t is not None:
            localized = self.t(ctx.language or "en", "help.body")
            if localized and localized != "help.body":
                return localized
        lines.append(_escape_value("منصة بيع وشراء حسابات/اشتراكات تيليجرام مع ضمان (Escrow) ولوحة إدارة — patched against master_bot_maker.html audit (17-error fix)",
            "HTML"))
        lines.append("")
        lines.append("<b>Commands:</b>")
        for trg in TRIGGERS:
            if trg["kind"] != "command" or trg.get("admin_only"):
                continue
            lines.append("/" + trg["pattern"] + " — " + _escape_value(trg.get("name", ""), "HTML"))
        lines.append("/cancel — abort the current action")
        lines.append("/back — go one step back")
        if I18N_ENABLED:
            langs = ", ".join(SUPPORTED_LANGUAGES)
            lines.append("/language &lt;code&gt; — switch language (" + langs + ")")
        return "\n".join(lines)

    async def _set_language(self, ctx: Ctx) -> None:
        code = (ctx.args[0] if ctx.args else "").strip().lower()
        if code not in SUPPORTED_LANGUAGES:
            await self.adapter.send_text(ctx,
                "Available languages: " + ", ".join(SUPPORTED_LANGUAGES))
            return
        st = await self.state.load(ctx.user_id, ctx.chat_id) or self.state.fresh()
        st["lang"] = code
        await self.state.save(ctx.user_id, ctx.chat_id, st)
        await self.db.users.set_language(ctx.user_id, code)
        await self.adapter.send_text(ctx, self.t(code, "language.set",
            language=code) if self.t else f"Language set to {code}.")

    async def _back(self, ctx: Ctx) -> None:
        """Pop one history entry and re-render that screen (Section 5)."""
        st = await self.state.load(ctx.user_id, ctx.chat_id)
        if not st or not st.get("history"):
            await self.adapter.send_text(ctx, self._t(ctx, "back.nothing",
                "Nothing to go back to. Send /start to begin again."))
            return
        st["history"].pop()
        entry = st["history"][-1] if st["history"] else None
        if entry is None:
            await self.state.clear(ctx.user_id, ctx.chat_id)
            await self.adapter.send_text(ctx, self._t(ctx, "back.start",
                "You are at the start. Send /start to begin again."))
            return
        st["node_id"] = entry.get("node_id") or st.get("node_id")
        st["waiting"] = ""
        st["wait_kind"] = ""
        st["expires_at"] = None
        screen_id = entry.get("screen_id") or st.get("screen_id")
        # __MBM_EXT_BACK_VALID__ — fall back to main if target screen was deleted
        if screen_id and screen_id not in SCREENS:
            screen_id = next(iter(SCREENS), None)
        if screen_id and screen_id in SCREENS:
            if st["history"]:
                st["history"].pop()
            await self.render_screen(ctx, st, screen_id, edit=False)
        await self.state.save(ctx.user_id, ctx.chat_id, st)

    # ─────────────────────── message routing ───────────────────────

    async def _message(self, ctx: Ctx) -> None:
        st = await self._load_or_expire(ctx)
        if st and st.get("waiting") and st.get("wait_kind") == "text":
            await self._resume_input(ctx, st)
            return
        if self.ratelimit is not None and not await self.ratelimit.allow(ctx):
            return
        for kind in ("text", "regex", "custom", "channel_post"):
            trigger = self._match_text_trigger(kind, ctx)
            if trigger is not None:
                await self._start_flow(trigger, ctx)
                return
        if st and st.get("screen_id"):
            screen = SCREENS.get(st["screen_id"])
            if screen and screen.get("next_on_text"):
                await self.render_screen(ctx, st, screen["next_on_text"])
                return
        if st and st.get("flow_id") and st.get("node_id"):
            await self._flow_run(ctx, st, st["node_id"])
            return
        logger.debug("no trigger matched a message from user {} in chat {}", ctx.user_id,
            ctx.chat_id)

    async def _load_or_expire(self, ctx: Ctx) -> dict | None:
        raw = await self.state.backend.get(ctx.user_id, ctx.chat_id)
        if not raw:
            return None
        exp = raw.get("expires_at")
        if exp and exp < int(time.time()):
            await self.state.clear(ctx.user_id, ctx.chat_id)
            # __MBM_EXT_WAIT_TIMEOUT__ — always notify on wait timeout
            if raw.get("waiting"):
                await self.adapter.send_text(
                    ctx,
                    self._t(ctx, "input.expired",
                            "⏰ Input timed out. Send /start to begin again."))
            return None
        return raw

    # ─────────────────────── callback routing ───────────────────────

    async def _callback(self, ctx: Ctx) -> None:
        parsed = _cb_parse(ctx.callback_data)
        verb, ref, key, payload = parsed["verb"], parsed["ref"], parsed["key"], parsed["payload"]
        st = await self._load_or_expire(ctx) or self.state.fresh(lang=ctx.language)
        if self.ratelimit is not None and not await self.ratelimit.allow(ctx):
            await self.adapter.answer_callback(ctx)
            return

        if verb == "nav":
            # __MBM_EXT_CB_ROUTE__ — check callback triggers BEFORE screen navigation
            _early = self._match_trigger("callback", ctx.callback_data, ctx)
            if _early is not None:
                await self._start_flow(_early, ctx)
                await self.adapter.answer_callback(ctx)
                return
            screen = SCREENS.get(ref)
            button = self._button_at(screen, key)
            if screen is None or button is None:
                await self.adapter.answer_callback(ctx,
                    "This menu is outdated, send /start", alert=True)
                return
            await self._button_action(ctx, st, screen, button, key, payload)
            return

        if verb == "kb":
            if st.get("waiting") and st.get("wait_kind") == "callback":
                wait_cfg = st.get("wait_cfg") or {}
                if wait_cfg.get("variable"):
                    st["vars"][wait_cfg["variable"]] = payload or key
                node = self._node_of(st, st["waiting"])
                await self.adapter.answer_callback(ctx)
                st["waiting"] = ""
                st["wait_kind"] = ""
                st["expires_at"] = None
                st.setdefault("history", []).append({"screen_id": st.get("screen_id",
                    ""), "node_id": st["waiting"] or "", "at": int(time.time())})
                await self.state.save(ctx.user_id, ctx.chat_id, st)
                if node is not None:
                    await self._flow_run(ctx, st,
                        self._default_next(FLOWS.get(st["flow_id"], {}), node))
                return
            await self.adapter.answer_callback(ctx)
            return

        if verb == "back":
            await self.adapter.answer_callback(ctx)
            await self._back(ctx)
            return

        if verb == "sub":
            await self._subscribe_retry(ctx, st, ref)
            return

        trigger = self._match_trigger("callback", ctx.callback_data, ctx)
        if trigger is not None:
            await self._start_flow(trigger, ctx)
            return
        await self.adapter.answer_callback(ctx)

    def _button_at(self, screen: dict | None, key: str) -> dict | None:
        if not screen or not key:
            return None
        try:
            ri, bi = key.split(".")
            row = screen["buttons"][int(ri)]
            return row[int(bi)]
        except (ValueError, IndexError, KeyError):
            pass
        for row in screen.get("buttons", []):
            for button in row:
                if _dhash(str(button.get("id", "")) + "|" + str(button.get("text", "")), 6) == key:
                    return button
        return None

    async def _button_action(self, ctx: Ctx, st: dict, screen: dict, button: dict, key: str,
        payload: str) -> None:
        action = button.get("action", "navigate")
        if action == "navigate":
            target = button.get("target")
            if target and target in SCREENS:
                await self.adapter.answer_callback(ctx)
                await self.render_screen(ctx, st, target, edit=ctx.update_kind == "callback")
                return
            await self.adapter.answer_callback(ctx, "Screen not available", alert=True)
            return
        if action == "input":
            st["waiting"] = "screen_button:" + screen["id"] + ":" + key
            st["wait_kind"] = "text"
            st["wait_cfg"] = {
                "variable": button.get("input_var", ""),
                "validation": button.get("input_validation", ""),
                "input_type": button.get("input_type", "text"),
                "error_message": "",
                "screen_button": True,
                "screen_id": screen["id"],
                "button_key": key,
            }
            btn_ttl = int(button.get("input_timeout") or DEFAULT_TTL_SECONDS)
            st["expires_at"] = int(time.time()) + btn_ttl
            await self.state.save(ctx.user_id, ctx.chat_id, st)
            prompt = button.get("input_prompt") or "Please type your answer:"
            await self.adapter.send_text(ctx, prompt)
            await self.adapter.answer_callback(ctx)
            return
        if action in ("callback", "toggle"):
            wait_cfg = st.get("wait_cfg") or {}
            if st.get("waiting") and st.get("wait_kind") == "callback":
                if wait_cfg.get("variable"):
                    st["vars"][wait_cfg["variable"]] = payload or button.get("payload", "")
                node = self._node_of(st, st["waiting"])
                st["waiting"] = ""
                st["wait_kind"] = ""
                st["expires_at"] = None
                await self.adapter.answer_callback(ctx)
                await self.state.save(ctx.user_id, ctx.chat_id, st)
                if node is not None:
                    await self._flow_run(ctx, st,
                        self._default_next(FLOWS.get(st["flow_id"], {}), node))
                return
            if button.get("input_var"):
                st["vars"][button["input_var"]] = payload or button.get("payload", "")
            await self.adapter.answer_callback(ctx, payload or "OK")
            await self.state.save(ctx.user_id, ctx.chat_id, st)
            return
        if action == "close":
            await self.adapter.answer_callback(ctx)
            await self.adapter.delete_message(ctx, ctx.message_id)
            await self.state.clear(ctx.user_id, ctx.chat_id)
            return
        if action == "delete_message":
            await self.adapter.answer_callback(ctx)
            await self.adapter.delete_message(ctx, ctx.message_id)
            return
        if action == "payment":
            from bot import payments as payments_mod

            await self.adapter.answer_callback(ctx)
            await payments_mod.send_button_invoice(ctx, self, st, button)
            return
        # url / share / callback_game are client-side: just acknowledge.
        await self.adapter.answer_callback(ctx)

    async def _subscribe_retry(self, ctx: Ctx, st: dict, node_id: str) -> None:
        node = self._node_of(st, node_id)
        if node is None:
            await self.adapter.answer_callback(ctx, "Session expired, send /start", alert=True)
            return
        st["waiting"] = ""
        st["wait_kind"] = ""
        st["expires_at"] = None
        await self.state.save(ctx.user_id, ctx.chat_id, st)
        await self._flow_run(ctx, st, node_id)

    # ─────────────────────── trigger matching ───────────────────────

    def _scope_ok(self, trigger: dict, ctx: Ctx) -> bool:
        scope = trigger.get("scope", "any")
        if scope == "any":
            return True
        return ctx.chat_type == scope

    def _filters_ok(self, trigger: dict, ctx: Ctx) -> bool:
        for f in trigger.get("filters", []):
            kind, value = f.get("kind"), f.get("value")
            if kind == "language" and (ctx.language or "en") != value:
                return False
            if kind == "user_id" and str(ctx.user_id) != str(value):
                return False
            if kind == "username":
                if (ctx.username or "").lower() != str(value).lower().lstrip("@"):
                    return False
            if kind == "chat_id" and str(ctx.chat_id) != str(value):
                return False
            truthy_value = str(value).lower() in ("1", "true", "yes")
            if kind == "is_bot" and truthy_value != (ctx.username or "").endswith("bot"):
                return False
            if kind == "has_photo" and truthy_value != bool(ctx.media.get("file_id")):
                return False
            if kind == "text_length":
                try:
                    if len(ctx.text) != int(value):
                        return False
                except ValueError:
                    return False
            if kind == "custom_expr":
                try:
                    if not _safe_eval(_normalize_expr(str(value)), self._expr_env({}, ctx)):
                        return False
                except BotError:
                    return False
        return True

    def _match_trigger(self, kind: str, value: str, ctx: Ctx) -> dict | None:
        for trigger in TRIGGERS:
            if trigger["kind"] != kind:
                continue
            pattern = trigger.get("pattern", "")
            if kind == "command" and pattern != value:
                continue
            if kind == "callback" and pattern and not value.startswith(pattern):
                continue
            if kind == "inline_query" and pattern and not (value or "").startswith(pattern):
                continue
            # __MBM_EXT_ESCROW__ — successful_payment / web_app_data prefix match
            if kind in ("successful_payment", "web_app_data", "shipping_query"):
                if pattern:
                    _val = str(value or "")
                    if not _val.startswith(pattern) and pattern not in _val:
                        continue
            if not self._scope_ok(trigger, ctx):
                continue
            if not self._filters_ok(trigger, ctx):
                continue
            return trigger
        return None

    def _match_text_trigger(self, kind: str, ctx: Ctx) -> dict | None:
        for trigger in TRIGGERS:
            tkind = trigger["kind"]
            if kind == "channel_post" and tkind != "channel_post":
                continue
            if kind != "channel_post" and tkind not in ("text", "regex", "custom"):
                continue
            if kind in ("text", "regex", "custom") and tkind != kind:
                continue
            pattern = trigger.get("pattern", "")
            if tkind == "text" and (ctx.text or "").strip().lower() != pattern.strip().lower():
                continue
            if tkind == "regex":
                try:
                    if not re.search(pattern, ctx.text or ""):
                        continue
                except re.error:
                    logger.error("trigger {} has an invalid regex", trigger.get("id"))
                    continue
            if tkind == "custom":
                try:
                    if not _safe_eval(_normalize_expr(pattern), self._expr_env({}, ctx)):
                        continue
                except BotError as exc:
                    logger.warning("custom trigger expression failed: {}", exc)
                    continue
            if not self._scope_ok(trigger, ctx):
                continue
            if not self._filters_ok(trigger, ctx):
                continue
            return trigger
        return None

    # ─────────────────────── flow start / gates ───────────────────────

    async def _start_flow(self, trigger: dict, ctx: Ctx) -> None:
        flow = FLOWS.get(trigger.get("flow_id", ""))
        if flow is None:
            logger.error("trigger {} points to missing flow {}", trigger.get("id"),
                trigger.get("flow_id"))
            await self.adapter.send_text(ctx, "This feature is temporarily unavailable.")
            return
        # __MBM_EXT_AUTH_ENFORCE__
        if flow.get("requires_auth"):
            _u = await self.db.users.get(ctx.user_id)
            if _u is None or _u.get("is_banned"):
                raise AccessDeniedError("registration required")
            await self.db.users.touch(ctx)
        if trigger.get("admin_only") or flow.get("admin_only"):
            if not ctx.is_admin:
                raise AccessDeniedError("admin-only command")
        if trigger.get("premium_only") and not ctx.is_premium:
            raise AccessDeniedError("premium-only feature")
        if self.ratelimit is not None and int(trigger.get("rate_count") or 0) > 0:
            if not await self.ratelimit.allow_trigger(trigger, ctx):
                return
        cooldown = int(trigger.get("cooldown") or flow.get("cooldown") or 0)
        if cooldown > 0:
            ckey = trigger["id"] + ":" + str(ctx.user_id)
            last = self._cooldowns.get(ckey, 0.0)
            now = time.time()
            if now - last < cooldown:
                wait_s = int(cooldown - (now - last)) + 1
                raise RateLimitError(f"cooldown active, retry in {wait_s}s", retry_after=wait_s)
            self._cooldowns[ckey] = now
        for channel in trigger.get("channels", []):
            status = await self.adapter.chat_member_status(channel, ctx.user_id)
            if status not in ("member", "administrator", "creator"):
                rows = [[{"kind": "url", "text": "📢 " + channel,
                    "url": "https://t.me/" + channel}]]
                await self.adapter.send_text(
                    ctx,
                    self._t(ctx, "gate.subscribe",
                        "Please subscribe to continue:") + "\n@" + channel,
                    "HTML", rows,
                )
                return
        await self.db.users.touch(ctx)
        st = self.state.fresh(flow_id=flow["id"], node_id=flow["start"],
            lang=await self._detect_lang(ctx))
        await self.state.save(ctx.user_id, ctx.chat_id, st)
        await self._flow_run(ctx, st, flow["start"])

    async def _detect_lang(self, ctx: Ctx) -> str:
        if not I18N_ENABLED:
            return ctx.language or "en"
        stored = await self.db.users.get_language(ctx.user_id)
        if stored:
            return stored
        return ctx.language or "en"

    def _t(self, ctx: Ctx, key: str, default: str, **fmt) -> str:
        if self.t is None:
            return default.format(**fmt) if fmt else default
        value = self.t(getattr(ctx, "language", "en") or "en", key, **fmt)
        return default if value == key else value

    # ─────────────────────── the graph walker (Section 6.5) ───────────────────────

    async def _finish(self, ctx: Ctx, st: dict) -> None:
        """Flow finished: drop runtime state but KEEP the rendered screen and
        history so callback navigation, screen text-chains and /back keep
        working until the session TTL expires. /cancel clears everything."""
        st["flow_id"] = ""
        st["node_id"] = ""
        st["waiting"] = ""
        st["wait_kind"] = ""
        st["wait_cfg"] = {}
        st["loop"] = None
        st["call_stack"] = []
        st["expires_at"] = None
        await self.state.save(ctx.user_id, ctx.chat_id, st)

    async def _flow_run(self, ctx: Ctx, st: dict, node_id: str | None) -> None:
        steps = 0
        while node_id and steps < MAX_STEPS:
            steps += 1
            flow = FLOWS.get(st.get("flow_id", ""))
            if flow is None:
                logger.error("state references missing flow {}", st.get("flow_id"))
                await self.state.clear(ctx.user_id, ctx.chat_id)
                return
            node = flow["nodes"].get(node_id)
            if node is None:
                logger.error("flow {} references missing node {}", flow["id"], node_id)
                await self.state.clear(ctx.user_id, ctx.chat_id)
                return
            st["node_id"] = node_id
            node_cfg = node.get("cfg") or {}
            if node_cfg.get("disabled"):
                node_id = self._default_next(flow, node)
                continue
            handler = node_handlers().get(node["type"])
            if handler is None:
                raise InternalError(f"no runtime handler for node type {node['type']}")
            instruction = await handler(node, ctx, self, st)
            kind = instruction[0]
            if kind == "goto":
                node_id = instruction[1]
                if node_id is None:
                    loop = st.get("loop")
                    if loop and loop.get("active") and loop.get("node_id") != st.get("node_id"):
                        node_id = loop["node_id"]
                        continue
                    break
            elif kind == "wait":
                st["waiting"] = node_id
                st["wait_kind"] = instruction[1]
                st["wait_cfg"] = instruction[3] if len(instruction) > 3 else {}
                st["expires_at"] = int(time.time()) + int(instruction[2] or DEFAULT_TTL_SECONDS)
                await self.state.save(ctx.user_id, ctx.chat_id, st)
                return
            elif kind == "end":
                await self._finish(ctx, st)
                return
            elif kind == "ret":
                stack = st.get("call_stack") or []
                frame = stack.pop() if stack else None
                value = instruction[1] if len(instruction) > 1 else None
                if frame is None:
                    node_id = None
                    break
                if frame.get("return_var"):
                    st.setdefault("vars", {})[frame["return_var"]] = value
                st["flow_id"] = frame["flow_id"]
                node_id = frame["node_id"]
                continue
            elif kind == "jump":
                node_id = instruction[1]
            else:
                raise InternalError(f"unknown instruction kind: {kind}")
        if steps >= MAX_STEPS:
            logger.error("flow stopped after {} steps (possible infinite loop); state cleared",
                MAX_STEPS)
            await self.state.clear(ctx.user_id, ctx.chat_id)
            return
        await self._finish(ctx, st)

    # ─────────────────────── graph helpers used by node handlers ───────────────────────

    def _node_of(self, st: dict, node_id: str) -> dict | None:
        flow = FLOWS.get(st.get("flow_id", ""))
        if not flow:
            return None
        return flow["nodes"].get(node_id)

    def out_edges(self, st: dict, node: dict) -> list[dict]:
        flow = FLOWS.get(st.get("flow_id", "")) or {}
        return [e for e in flow.get("edges", []) if e.get("from") == node["id"]]

    def _default_next(self, flow: dict, node: dict) -> str | None:
        edges = [e for e in flow.get("edges", []) if e.get("from") == node["id"]]
        for e in edges:
            if not e.get("condition") and not e.get("match") and not e.get("label"):
                return e["to"]
        for e in edges:
            if not e.get("condition") and not e.get("match"):
                return e["to"]
        return node.get("next") or None

    def goto(self, st: dict, node: dict) -> tuple:
        """Instruction: continue with this node's default outgoing edge."""
        flow = FLOWS.get(st.get("flow_id", "")) or {}
        return ("goto", self._default_next(flow, node))

    def edge_by_label(self, st: dict, node: dict, label: str) -> str | None:
        for e in self.out_edges(st, node):
            if e.get("label") == label:
                return e["to"]
        return None

    def edge_by_match(self, st: dict, node: dict, value: str) -> str | None:
        edges = self.out_edges(st, node)
        for e in edges:
            if e.get("match") == value:
                return e["to"]
        for e in edges:
            if e.get("match") in (None, "") and not e.get("condition") and not e.get("label"):
                return e["to"]
        return self._default_next(FLOWS.get(st.get("flow_id", "")) or {}, node)

    async def choose_branch(self, ctx: Ctx, st: dict, node: dict) -> str | None:
        """CONDITION semantics: first true edge wins, else the default next."""
        for e in self.out_edges(st, node):
            condition = e.get("condition")
            if condition and await self.truthy(condition, ctx, st):
                return e["to"]
        return self.goto(st, node)[1]

    # ─────────────────────── values: bindings, expressions, templates ───────────────────────

    def _expr_env(self, st: dict, ctx: Ctx) -> dict:
        env = dict(st.get("vars") or {})
        env["ctx"] = _CtxView(ctx)
        env["env"] = _EnvView()
        return env

    async def eval_expr(self, expr: str, st: dict, ctx: Ctx) -> Any:
        return _safe_eval(_normalize_expr(expr), self._expr_env(st, ctx))

    async def truthy(self, expr_or_binding: str, ctx: Ctx, st: dict) -> bool:
        """Whole-string bindings resolve directly; anything else is an
        expression (bindings inside expressions are normalized first)."""
        text = str(expr_or_binding or "")
        if _FULL_BINDING_RE.match(text):
            return bool(await self.resolve(text, ctx, st))
        return bool(await self.eval_expr(text, st, ctx))

    async def resolve(self, value: Any, ctx: Ctx, st: dict) -> Any:
        """Resolve @bindings (Section 13); other values pass through.

        Path syntax after the variable name is fully supported:
          @input.rows[0]["col"] · @input.row.col · @ctx.payment.amount
          @ctx.media["photo_file_id"] · @steps.a.b[2]
        """
        if not isinstance(value, str) or not value.startswith("@"):
            return value
        body = value[1:]
        if body == "random_long":
            return secrets.randbits(64)
        if body == "random_bytes":
            return secrets.token_bytes(16)
        if body == "now":
            return int(time.time())
        if body == "now_iso":
            return datetime.now(timezone.utc).isoformat()
        if body == "uuid4":
            return str(uuid.uuid4())
        root, _, rest = body.partition(".")
        if root == "ctx":
            return _resolve_path(ctx, rest)
        if root in ("input", "steps"):
            return _resolve_path(st.get("vars") or {}, rest)
        if root == "env":
            return cfg.env(rest)
        if root == "literal":
            return _parse_literal(rest)
        if root == "db":
            table, _, column = rest.partition(".")
            return await self.db_lookup(table, column or "id", st, ctx)
        if root == "expr":
            return await self.eval_expr(rest, st, ctx)
        logger.warning("unknown binding {!r}; passing through as text", value)
        return value

    async def resolve_many(self, mapping: dict, ctx: Ctx, st: dict) -> dict:
        out = {}
        for key in sorted(mapping or {}):
            out[key] = await self.resolve(mapping[key], ctx, st)
        return out

    async def db_lookup(self, table: str, column: str, st: dict, ctx: Ctx) -> Any:
        """@db.<table>.<column>: current user's row value, or None."""
        repo = self.db.custom(table)
        row = await repo.get_for_user(ctx.user_id, column)
        return row

    async def render_text(self, template: Any, ctx: Ctx, st: dict, parse_mode: str = "HTML",
                          i18n_key: str = "", count: Any = None) -> str:
        """i18n key (with CLDR plurals when count is given) → template →
        binding → {var} substitution (escaped for the parse mode)."""
        text = template
        if i18n_key and self.t is not None:
            lang = st.get("lang") or ctx.language or "en"
            localized = ""
            if count is not None:
                from bot.i18n import t_plural

                plural = t_plural(lang, i18n_key, _to_int(count))
                if plural != i18n_key:
                    localized = plural
            if not localized:
                candidate = self.t(lang, i18n_key)
                if candidate != i18n_key:
                    localized = candidate
            if localized:
                text = localized
        if isinstance(text, str) and text.startswith("@"):
            text = _to_str(await self.resolve(text, ctx, st))
        # __MBM_EXT_FMT_CALLS__ — pass lang and translator to _format_template
        _lang = st.get("lang") or ctx.language or "en"
        return _format_template(_to_str(text), st.get("vars") or {}, ctx, parse_mode,
                                lang=_lang, t_func=self.t)

    # ─────────────────────── screens & buttons ───────────────────────

    async def build_buttons(self, ctx: Ctx, st: dict, screen: dict) -> list[list[dict]]:
        """Neutral button rows; visibleIf=false buttons and empty rows are
        omitted at RUNTIME (variables may change visibility)."""
        rows: list[list[dict]] = []
        for ri, row in enumerate(screen.get("buttons", [])):
            out_row: list[dict] = []
            for bi, b in enumerate(row):
                if b.get("visible_if"):
                    try:
                        if not await self.truthy(b["visible_if"], ctx, st):
                            continue
                    except BotError as exc:
                        logger.warning("visibleIf failed for button {!r}: {}", b.get("text"), exc)
                        continue
                button = {
                    "kind": b.get("kind", "inline"),
                    "text": _to_str(await self.render_text(b.get("text", ""), ctx, st, "")),
                    "url": _to_str(await self.resolve(b.get("url", ""), ctx, st)),
                    "copy_text": _to_str(await self.resolve(b.get("copy_text", ""), ctx, st)),
                    "switch_inline": _to_str(b.get("switch_inline", "")),
                }
                action = b.get("action", "navigate")
                if b.get("kind") == "inline" and action not in ("url",):
                    payload = b.get("payload", "")
                    if action == "input":
                        payload = "ask"
                    button["callback"] = _cb("nav", screen["id"], f"{ri}.{bi}", payload)
                out_row.append(button)
            if out_row:
                rows.append(out_row)
        if screen.get("backable") and st.get("history"):
            rows.append([{"kind": "inline", "text": self._t(ctx, "button.back",
                "← Back"), "callback": _cb("back", screen["id"])}])
        return rows

    async def render_screen(self, ctx: Ctx, st: dict, screen_id: str, edit: bool = False) -> None:
        screen = SCREENS.get(screen_id)
        if screen is None:
            raise InternalError(f"screen '{screen_id}' not found in the generated data")
        st["screen_id"] = screen_id
        history = st.setdefault("history", [])
        history.append({"screen_id": screen_id, "node_id": st.get("node_id", ""),
            "at": int(time.time())})
        st["history"] = history[-30:]
        parse_mode = screen.get("parse_mode") or ""
        text = await self.render_text(screen.get("message", ""), ctx, st, parse_mode,
            screen.get("i18n_key", ""))
        rows = await self.build_buttons(ctx, st, screen)
        media_type = screen.get("media_type", "")
        if media_type and screen.get("media_source"):
            source = _to_str(await self.resolve(screen["media_source"], ctx, st))
            await self.adapter.send_media(ctx, media_type, source, text, parse_mode, rows)
        elif edit and ctx.update_kind == "callback":
            await self.adapter.edit_text(ctx, text, parse_mode, rows)
        else:
            await self.adapter.send_text(ctx, text, parse_mode, rows)
        await self.state.save(ctx.user_id, ctx.chat_id, st)

    # ─────────────────────── ASK input resume & validation ───────────────────────

    async def _resume_input(self, ctx: Ctx, st: dict) -> None:
        waiting = st.get("waiting", "")
        if waiting.startswith("screen_button:"):
            _, screen_id, key = waiting.split(":", 2)
            screen = SCREENS.get(screen_id)
            button = self._button_at(screen, key)
            if button is None:
                await self.state.clear(ctx.user_id, ctx.chat_id)
                await self.adapter.send_text(ctx, "Session expired. Send /start to begin again.")
                return
            wait_cfg = st.get("wait_cfg") or {}
            raw_value = self._extract_input(ctx, wait_cfg.get("input_type", "text"))
            ok, value = self._validate_input(raw_value, wait_cfg.get("input_type",
                "text"), wait_cfg.get("validation", ""))
            if not ok:
                await self.adapter.send_text(ctx, value or "Invalid input, please try again.")
                return
            variable = wait_cfg.get("variable") or button.get("input_var") or ""
            if variable:
                st["vars"][variable] = value
            st["waiting"] = ""
            st["wait_kind"] = ""
            st["wait_cfg"] = {}
            st["expires_at"] = None
            await self.state.save(ctx.user_id, ctx.chat_id, st)
            target = st.get("node_id") or ""
            node = self._node_of(st, target)
            if node is not None:
                await self._flow_run(ctx, st,
                    self._default_next(FLOWS.get(st.get("flow_id", "")) or {}, node))
            return
        node = self._node_of(st, waiting)
        if node is None:
            await self.state.clear(ctx.user_id, ctx.chat_id)
            await self.adapter.send_text(ctx, "Session expired. Send /start to begin again.")
            return
        cfgd = node.get("cfg") or {}
        input_type = cfgd.get("inputType", "text")
        raw_value = self._extract_input(ctx, input_type)
        ok, value = self._validate_input(raw_value, input_type, cfgd.get("validation", ""))
        if not ok:
            message = cfgd.get("errorMessage") or self._t(ctx, "input.invalid",
                "Invalid input, please try again.")
            await self.adapter.send_text(ctx, message)
            return
        variable = cfgd.get("variable", "")
        if variable:
            st["vars"][variable] = value
        st.setdefault("history", []).append({"screen_id": st.get("screen_id", ""),
            "node_id": node["id"], "at": int(time.time())})
        st["waiting"] = ""
        st["wait_kind"] = ""
        st["wait_cfg"] = {}
        st["expires_at"] = None
        await self.state.save(ctx.user_id, ctx.chat_id, st)
        await self._flow_run(ctx, st, self._default_next(FLOWS.get(st.get("flow_id",
            "")) or {}, node))

    def _extract_input(self, ctx: Ctx, input_type: str) -> Any:
        media = ctx.media or {}
        if input_type == "photo":
            return media.get("photo_file_id") or ctx.text
        if input_type == "document":
            return media.get("document_file_id") or ctx.text
        if input_type == "location":
            if media.get("latitude") is not None:
                return f"{media['latitude']},{media['longitude']}"
            return ctx.text
        if input_type == "contact":
            return media.get("phone_number") or ctx.text
        return ctx.text

    def _validate_input(self, value: Any, input_type: str, regex: str) -> tuple[bool, Any]:
        """Return (ok, converted_value_or_error_message)."""
        text = _to_str(value).strip()
        if not text and input_type not in ("photo", "document", "location", "contact"):
            return False, "Empty input is not accepted, please try again."
        converted: Any = text
        if input_type == "number":
            pattern = _INPUT_PATTERNS["number"]
            if not pattern.match(text):
                return False, "Please send a valid number."
            converted = float(text) if "." in text else int(text)
        elif input_type in _INPUT_PATTERNS:
            if not _INPUT_PATTERNS[input_type].match(text):
                return False, f"That does not look like a valid {input_type}."
        if regex:
            try:
                if not re.search(regex, _to_str(converted)):
                    return False, ""
            except re.error as exc:
                logger.error("ASK validation regex invalid: {}", exc)
                return False, "The bot has a configuration error (invalid validation regex)."
        return True, converted

    # ─────────────────────── sub-flows & loops ───────────────────────

    async def call_subflow(self, ctx: Ctx, st: dict, node: dict, target_flow_id: str,
                           input_map: dict | None = None, return_var: str = "") -> tuple:
        """BRANCH_TO_FLOW / TRY_CATCH helper: push the call frame and jump."""
        target = FLOWS.get(target_flow_id)
        if target is None:
            raise InternalError(f"sub-flow '{target_flow_id}' not found")
        if input_map:
            resolved = await self.resolve_many(input_map, ctx, st)
            st.setdefault("vars", {}).update(resolved)
        stack = st.setdefault("call_stack", [])
        if len(stack) >= 12:
            raise InternalError("sub-flow nesting too deep (max 12)")
        flow = FLOWS.get(st.get("flow_id", "")) or {}
        stack.append({
            "flow_id": st.get("flow_id", ""),
            "node_id": self._default_next(flow, node),
            "return_var": return_var,
        })
        st["flow_id"] = target_flow_id
        await self.state.save(ctx.user_id, ctx.chat_id, st)
        return ("goto", target["start"])

    async def shutdown_flow(self, ctx: Ctx, st: dict) -> None:
        await self.state.clear(ctx.user_id, ctx.chat_id)
