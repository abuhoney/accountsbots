"""Database session/driver layer for backend: postgresql. All queries are parameterized."""
from __future__ import annotations

from pathlib import Path
import os



from loguru import logger
from sqlalchemy import Table
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from bot.db.models import SQL_TABLES, metadata
from bot.errors import InternalError, UserInputError


_engine: AsyncEngine | None = None


def database_url() -> str:
    """Build the SQLAlchemy async URL for this backend."""
    raw = os.environ.get("DATABASE_URL", "")
    if not raw:
        raise RuntimeError(
            "database URL/path is not configured; set the env var from .env.example"
        )
    url = raw.replace("postgresql://",
        "postgresql+asyncpg://") if raw.startswith("postgresql://") else raw
    return url


async def init_db() -> None:
    """Create the engine (pool_size=10 for server backends) and all tables."""
    global _engine
    url = database_url()
    if url.startswith("sqlite"):
        Path(url.replace("sqlite+aiosqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_async_engine(url, echo=False)
    else:
        _engine = create_async_engine(url, echo=False, pool_size=10, max_overflow=5,
            pool_pre_ping=True)
    async with _engine.begin() as conn:
        await conn.run_sync(metadata.create_all)
    logger.info("database ready: {}", url.split("://")[0])


async def close_db() -> None:
    """Dispose the connection pool on shutdown."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None


def engine() -> AsyncEngine:
    """Return the initialized engine (RuntimeError when not initialized)."""
    if _engine is None:
        raise RuntimeError("init_db() must be awaited before using the database")
    return _engine


class SQLAlchemyDriver:
    """Async Core driver — parameterized statements only (Section 27/32)."""

    async def init(self) -> None:
        await init_db()

    async def close(self) -> None:
        await close_db()

    def _table(self, name: str) -> Table:
        table = SQL_TABLES.get(name)
        if table is None:
            raise InternalError(f"unknown table {name!r}")
        return table

    def _where(self, table: Table, where: dict):
        clause = None
        for key in sorted(where or {}):
            if key not in table.c:
                raise UserInputError(f"table has no column {key!r}")
            cond = table.c[key] == where[key]
            clause = cond if clause is None else clause & cond
        return clause

    def _order(self, table: Table, order_by: str):
        parts = [p for p in str(order_by or "").split(",") if p.strip()]
        clauses = []
        for part in parts[:4]:
            tokens = part.split()
            col_name = tokens[0].strip()
            if col_name not in table.c:
                logger.warning("ignoring unknown order-by column {!r}", col_name)
                continue
            col = table.c[col_name]
            want_desc = len(tokens) > 1 and tokens[1].upper() == "DESC"
            clauses.append(col.desc() if want_desc else col.asc())
        return clauses

    async def insert(self, table_name: str, row: dict):
        table = self._table(table_name)
        clean = {k: v for k, v in (row or {}).items() if k in table.c}
        async with engine().begin() as conn:
            result = await conn.execute(table.insert().values(**clean))
        return result.inserted_primary_key[0] if result.inserted_primary_key else None

    async def find(self, table_name: str, where: dict, limit: int = 100,
                   offset: int = 0, order_by: str = "") -> list[dict]:
        table = self._table(table_name)
        stmt = table.select()
        clause = self._where(table, where)
        if clause is not None:
            stmt = stmt.where(clause)
        for col in self._order(table, order_by):
            stmt = stmt.order_by(col)
        if limit:
            stmt = stmt.limit(int(limit))
        if offset:
            stmt = stmt.offset(int(offset))
        async with engine().connect() as conn:
            rows = (await conn.execute(stmt)).mappings().all()
        return [dict(r) for r in rows]

    async def update(self, table_name: str, where: dict, fields: dict) -> int:
        table = self._table(table_name)
        clean = {k: v for k, v in (fields or {}).items() if k in table.c}
        if not clean:
            return 0
        stmt = table.update()
        clause = self._where(table, where)
        if clause is not None:
            stmt = stmt.where(clause)
        async with engine().begin() as conn:
            result = await conn.execute(stmt.values(**clean))
        return int(result.rowcount or 0)

    async def delete(self, table_name: str, where: dict) -> int:
        table = self._table(table_name)
        stmt = table.delete()
        clause = self._where(table, where)
        if clause is not None:
            stmt = stmt.where(clause)
        async with engine().begin() as conn:
            result = await conn.execute(stmt)
        return int(result.rowcount or 0)

    async def count(self, table_name: str, where: dict) -> int:
        from sqlalchemy import func

        table = self._table(table_name)
        stmt = table.select().with_only_columns(func.count())
        clause = self._where(table, where)
        if clause is not None:
            stmt = stmt.where(clause)
        async with engine().connect() as conn:
            return int((await conn.execute(stmt)).scalar_one())


def build_driver():
    """Return the driver instance for this backend."""
    return SQLAlchemyDriver()
