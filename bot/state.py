"""Per-user state machine store (Section 5): persisted sessions, per-(user, chat)
asyncio locks, TTL expiry and a 60-second background sweeper."""
from __future__ import annotations

from pathlib import Path
import asyncio
import json
import os
import time


from loguru import logger


DEFAULT_TTL_SECONDS = 300
SESSION_TTL_SECONDS = 3600
SWEEP_INTERVAL_SECONDS = 60

class MemoryStateBackend:
    """In-memory state (development, demos, and the fallback backend)."""

    def __init__(self) -> None:
        self._data: dict[tuple[int, int], dict] = {}

    async def get(self, user_id: int, chat_id: int) -> dict | None:
        value = self._data.get((user_id, chat_id))
        return json.loads(json.dumps(value)) if value else None

    async def set(self, user_id: int, chat_id: int, state: dict) -> None:
        self._data[(user_id, chat_id)] = json.loads(json.dumps(state))

    async def delete(self, user_id: int, chat_id: int) -> None:
        self._data.pop((user_id, chat_id), None)

    async def sweep_expired(self, now: int) -> int:
        expired = [k for k,
            v in self._data.items() if v.get("expires_at") and v["expires_at"] < now]
        for k in expired:
            del self._data[k]
        return len(expired)

    async def close(self) -> None:
        self._data.clear()


class SQLiteStateBackend:
    """Persistent sessions in SQLite via aiosqlite (restart-safe, NNG-7)."""

    DDL = (
        "CREATE TABLE IF NOT EXISTS sessions ("
        " user_id INTEGER NOT NULL,"
        " chat_id INTEGER NOT NULL,"
        " state_json TEXT NOT NULL,"
        " updated_at INTEGER NOT NULL,"
        " expires_at INTEGER,"
        " PRIMARY KEY (user_id, chat_id))"
    )

    def __init__(self, path: str) -> None:
        self._path = path
        self._db = None

    async def _conn(self):
        if self._db is None:
            import aiosqlite

            Path(self._path).parent.mkdir(parents=True, exist_ok=True)
            self._db = await aiosqlite.connect(self._path)
            await self._db.execute("PRAGMA journal_mode=WAL")
            await self._db.execute(self.DDL)
            await self._db.commit()
        return self._db

    async def get(self, user_id: int, chat_id: int) -> dict | None:
        db = await self._conn()
        async with db.execute(
            "SELECT state_json FROM sessions WHERE user_id = ? AND chat_id = ?",
            (user_id, chat_id),
        ) as cur:
            row = await cur.fetchone()
        return json.loads(row[0]) if row else None

    async def set(self, user_id: int, chat_id: int, state: dict) -> None:
        db = await self._conn()
        await db.execute(
            "INSERT INTO sessions (user_id, chat_id, state_json, updated_at, expires_at)"
            " VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT(user_id, chat_id) DO UPDATE SET"
            " state_json = excluded.state_json, updated_at = excluded.updated_at,"
            " expires_at = excluded.expires_at",
            (user_id, chat_id, json.dumps(state, ensure_ascii=False), int(time.time()),
                state.get("expires_at")),
        )
        await db.commit()

    async def delete(self, user_id: int, chat_id: int) -> None:
        db = await self._conn()
        await db.execute("DELETE FROM sessions WHERE user_id = ? AND chat_id = ?", (user_id,
            chat_id))
        await db.commit()

    async def sweep_expired(self, now: int) -> int:
        db = await self._conn()
        cur = await db.execute(
            "DELETE FROM sessions WHERE expires_at IS NOT NULL AND expires_at < ?", (now,)
        )
        await db.commit()
        return cur.rowcount or 0

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None


class PostgresStateBackend:
    """PostgreSQL-backed sessions via asyncpg."""

    DDL = (
        "CREATE TABLE IF NOT EXISTS bot_sessions ("
        " user_id BIGINT NOT NULL, chat_id BIGINT NOT NULL,"
        " state_json JSONB NOT NULL, updated_at BIGINT NOT NULL, expires_at BIGINT,"
        " PRIMARY KEY (user_id, chat_id))"
    )

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
        self._pool = None

    async def _p(self):
        if self._pool is None:
            import asyncpg

            self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=10)
            async with self._pool.acquire() as conn:
                await conn.execute(self.DDL)
        return self._pool

    async def get(self, user_id: int, chat_id: int) -> dict | None:
        pool = await self._p()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT state_json FROM bot_sessions WHERE user_id = $1 AND chat_id = $2",
                user_id, chat_id,
            )
        return json.loads(row["state_json"]) if row else None

    async def set(self, user_id: int, chat_id: int, state: dict) -> None:
        pool = await self._p()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO bot_sessions (user_id, chat_id, state_json, updated_at, expires_at)"
                " VALUES ($1, $2, $3, $4, $5)"
                " ON CONFLICT (user_id, chat_id) DO UPDATE SET"
                " state_json = EXCLUDED.state_json, updated_at = EXCLUDED.updated_at,"
                " expires_at = EXCLUDED.expires_at",
                user_id, chat_id, json.dumps(state, ensure_ascii=False),
                int(time.time()), state.get("expires_at"),
            )

    async def delete(self, user_id: int, chat_id: int) -> None:
        pool = await self._p()
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM bot_sessions WHERE user_id = $1 AND chat_id = $2", user_id, chat_id
            )

    async def sweep_expired(self, now: int) -> int:
        pool = await self._p()
        async with pool.acquire() as conn:
            res = await conn.execute(
                "DELETE FROM bot_sessions WHERE expires_at IS NOT NULL AND expires_at < $1", now
            )
        return int(res.split()[-1]) if res and res.split()[-1].isdigit() else 0

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None


def build_state_backend():
    """Create the state backend for the configured database."""
    dsn = os.environ.get("DATABASE_URL", "")
    if not dsn:
        logger.warning("DATABASE_URL not set; sessions fall back to memory")
        return MemoryStateBackend()
    return PostgresStateBackend(dsn)


class StateManager:
    """Per-(user, chat) state with serialization locks and expiry sweeping.

    Concurrency safety (Section 5): two updates for the SAME (user_id,
    chat_id) are serialized through an asyncio.Lock; different users run
    fully in parallel. A background sweeper removes expired sessions every
    60 seconds.
    """

    def __init__(self, backend) -> None:
        self.backend = backend
        self._locks: dict[tuple[int, int], asyncio.Lock] = {}
        self._sweeper: asyncio.Task | None = None

    def lock_for(self, user_id: int, chat_id: int) -> asyncio.Lock:
        key = (int(user_id), int(chat_id))
        lock = self._locks.get(key)
        if lock is None:
            if len(self._locks) > 5000:
                # Opportunistic cleanup: drop unlocked entries to bound memory.
                for k in [k for k, v in self._locks.items() if not v.locked()][:2500]:
                    del self._locks[k]
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    def fresh(self, flow_id: str = "", node_id: str = "", lang: str = "en") -> dict:
        now = int(time.time())
        return {
            "flow_id": flow_id,
            "node_id": node_id,
            "screen_id": "",
            "waiting": "",
            "wait_kind": "",
            "wait_cfg": {},
            "vars": {},
            "history": [],
            "call_stack": [],
            "loop": None,
            "lang": lang,
            "created_at": now,
            "updated_at": now,
            "expires_at": None,
        }

    async def load(self, user_id: int, chat_id: int) -> dict | None:
        """Load a session; expired sessions are removed and reported as None."""
        try:
            state = await self.backend.get(user_id, chat_id)
        except Exception:
            logger.exception("state backend unreachable on get; using in-memory fallback")
            state = await _fallback_get(user_id, chat_id)
        if not state:
            return None
        exp = state.get("expires_at")
        if exp and exp < int(time.time()):
            await self.delete(user_id, chat_id)
            return None
        return state

    async def save(self, user_id: int, chat_id: int, state: dict) -> None:
        state["updated_at"] = int(time.time())
        if not state.get("expires_at") and not state.get("waiting"):
            state["expires_at"] = int(time.time()) + SESSION_TTL_SECONDS
        try:
            await self.backend.set(user_id, chat_id, state)
        except Exception:
            logger.exception("state backend unreachable on set; using in-memory fallback")
            await _fallback_set(user_id, chat_id, state)

    async def clear(self, user_id: int, chat_id: int) -> None:
        try:
            await self.backend.delete(user_id, chat_id)
        except Exception:
            logger.exception("state backend unreachable on delete; using in-memory fallback")
        _FALLBACK.pop((user_id, chat_id), None)

    def start_sweeper(self) -> None:
        if self._sweeper is None:
            self._sweeper = asyncio.get_running_loop().create_task(self._sweep_loop())

    async def _sweep_loop(self) -> None:
        while True:
            await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
            try:
                removed = await self.backend.sweep_expired(int(time.time()))
                if removed:
                    logger.debug("state sweeper removed {} expired session(s)", removed)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("state sweep failed")

    async def stop(self) -> None:
        if self._sweeper is not None:
            self._sweeper.cancel()
            try:
                await self._sweeper
            except asyncio.CancelledError:
                pass
            self._sweeper = None
        try:
            await self.backend.close()
        except Exception:
            logger.exception("state backend close failed")


_FALLBACK: dict[tuple[int, int], dict] = {}


async def _fallback_get(user_id: int, chat_id: int) -> dict | None:
    return _FALLBACK.get((user_id, chat_id))


async def _fallback_set(user_id: int, chat_id: int, state: dict) -> None:
    _FALLBACK[(user_id, chat_id)] = state
