"""Database facade + repositories (Section 15). Every backend implements the
same five primitives; this module provides the shared UserRepo / SessionRepo /
CustomRepo / EventsRepo interface used by the flow engine."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json



from loguru import logger

from bot import config as cfg
from bot.db.models import TABLE_SCHEMAS, TABLE_SCOPES
from bot.db.session import build_driver
from bot.errors import InternalError


def _sanitize(value):
    """Make DB values JSON-safe so they can live inside the state store."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).hex()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(k): _sanitize(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_sanitize(v) for v in value]
    return str(value)


def _sanitize_row(row: dict) -> dict:
    return {str(k): _sanitize(v) for k, v in (row or {}).items()}


class UserRepo:
    """Repository for the auto-provisioned users table (Section 11)."""

    def __init__(self, driver) -> None:
        self._d = driver

    async def get(self, user_id: int) -> dict | None:
        rows = await self._d.find("users", {"user_id": int(user_id)}, limit=1)
        return _sanitize_row(rows[0]) if rows else None

    async def upsert(self, user_id: int, **fields) -> dict:
        existing = await self.get(user_id)
        clean = {k: _sanitize(v) for k, v in fields.items()}
        if existing is None:
            row = {"user_id": int(user_id), "is_active": True, "is_admin": False,
                "is_banned": False}
            row.update(clean)
            await self._d.insert("users", row)
        elif clean:
            await self._d.update("users", {"user_id": int(user_id)}, clean)
        return await self.get(user_id) or {"user_id": int(user_id)}

    async def set_field(self, user_id: int, field: str, value) -> None:
        await self._d.update("users", {"user_id": int(user_id)}, {field: _sanitize(value)})

    async def touch(self, ctx) -> dict:
        """Register/refresh the user after every interaction (auth middleware)."""
        fields = {
            "username": ctx.username or None,
            "first_name": ctx.first_name or None,
            "language": ctx.language or "en",
        }
        return await self.upsert(ctx.user_id, **fields)

    async def set_language(self, user_id: int, lang: str) -> None:
        await self.set_field(user_id, "language", lang)

    async def get_language(self, user_id: int) -> str:
        row = await self.get(user_id)
        return (row or {}).get("language") or ""

    async def is_admin(self, user_id: int) -> bool:
        row = await self.get(user_id)
        return bool((row or {}).get("is_admin")) or int(user_id) in cfg.ADMINS


class SessionRepo:
    """Spec interface over the active state backend (attached at startup)."""

    def __init__(self) -> None:
        self._backend = None

    def attach(self, backend) -> None:
        self._backend = backend

    async def load(self, user_id: int, chat_id: int) -> dict | None:
        if self._backend is None:
            return None
        return await self._backend.get(int(user_id), int(chat_id))

    async def save(self, user_id: int, chat_id: int, state: dict) -> None:
        if self._backend is not None:
            await self._backend.set(int(user_id), int(chat_id), state)

    async def delete(self, user_id: int, chat_id: int) -> None:
        if self._backend is not None:
            await self._backend.delete(int(user_id), int(chat_id))

    async def sweep(self, before_epoch: int) -> int:
        if self._backend is None:
            return 0
        return await self._backend.sweep_expired(int(before_epoch))


class EventsRepo:
    """Append-only events_log (used by the logging middleware)."""

    def __init__(self, driver) -> None:
        self._d = driver

    async def log(self, user_id: int, kind: str, payload: dict | None = None) -> None:
        try:
            await self._d.insert("events_log", {
                "user_id": int(user_id),
                "kind": str(kind),
                "payload_json": json.dumps(payload or {}, ensure_ascii=False, default=str)[:8000],
            })
        except Exception:
            logger.exception("failed to write events_log (ignored)")


class CustomRepo:
    """Repository for one designed table — same interface for all backends."""

    def __init__(self, driver, table: str) -> None:
        self._d = driver
        self.table = table
        schema = TABLE_SCHEMAS.get(table)
        if schema is None:
            raise InternalError(f"unknown table {table!r} (not in the data model)")
        self.pk = schema["pk"]
        self.timestamps = bool(schema.get("timestamps"))

    async def insert(self, fields: dict):
        row = {k: _sanitize(v) for k, v in (fields or {}).items()}
        if self.timestamps:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            row.setdefault("created_at", now)
            row.setdefault("updated_at", now)
        # __MBM_EXT_UPSERT__ — auto-upsert on unique-constraint failure
        try:
            return await self._d.insert(self.table, row)
        except Exception as exc:
            _msg = str(exc).lower()
            if "unique" in _msg or "duplicate" in _msg or "already exists" in _msg:
                for _key in sorted(row):
                    _res = await self._d.find(self.table, {_key: row[_key]}, limit=1)
                    if _res:
                        await self._d.update(self.table, {_key: row[_key]}, row)
                        return _res[0].get(self.pk, row[_key])
            raise

    async def get(self, pk_value) -> dict | None:
        rows = await self._d.find(self.table, {self.pk: pk_value}, limit=1)
        return _sanitize_row(rows[0]) if rows else None

    async def list(self, where: dict | None = None, limit: int = 100,
                   offset: int = 0, order_by: str = "") -> list[dict]:
        rows = await self._d.find(self.table, where or {}, limit=limit, offset=offset,
            order_by=order_by)
        return [_sanitize_row(r) for r in rows]

    async def update(self, pk_value, fields: dict) -> int:
        clean = {k: _sanitize(v) for k, v in (fields or {}).items()}
        if self.timestamps:
            clean["updated_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        return await self._d.update(self.table, {self.pk: pk_value}, clean)

    async def update_where(self, where: dict, fields: dict) -> int:
        clean = {k: _sanitize(v) for k, v in (fields or {}).items()}
        if self.timestamps:
            clean["updated_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        return await self._d.update(self.table, where or {}, clean)

    async def delete(self, pk_value) -> int:
        return await self._d.delete(self.table, {self.pk: pk_value})

    async def delete_where(self, where: dict) -> int:
        return await self._d.delete(self.table, where or {})

    async def count(self, where: dict | None = None) -> int:
        return await self._d.count(self.table, where or {})

    async def get_for_user(self, user_id: int, column: str):
        """@db.<table>.<column> lookup for the current user's row."""
        rows = await self._d.find(self.table, {"user_id": int(user_id)}, limit=1,
            order_by=(self.pk + " DESC" if self.pk != "user_id" else ""))
        if not rows:
            return None
        return _sanitize(rows[0]).get(column)


class Database:
    """Facade exposed to the engine as eng.db."""

    def __init__(self, driver) -> None:
        self.driver = driver
        self.users = UserRepo(driver)
        self.sessions = SessionRepo()
        self.events = EventsRepo(driver)
        self._custom: dict[str, CustomRepo] = {}

    def custom(self, table: str) -> CustomRepo:
        repo = self._custom.get(table)
        if repo is None:
            repo = CustomRepo(self.driver, table)
            self._custom[table] = repo
        return repo

    def tenant_scope(self, table: str) -> str:
        return TABLE_SCOPES.get(table, "global")

    async def init(self) -> None:
        await self.driver.init()

    async def close(self) -> None:
        await self.driver.close()


def build_database() -> Database:
    """Create the Database facade for the configured backend."""
    return Database(build_driver())
