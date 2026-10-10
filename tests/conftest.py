"""Shared fixtures: fake update/context, in-memory database driver.

Library-agnostic: the engine talks to adapters, so tests never import a
Telegram library — they run on every target (Section 24)."""
from __future__ import annotations

import os
import sys




import pytest
os.environ.setdefault("BOT_TOKEN", "123456:TEST-TOKEN")
os.environ.setdefault("LOG_LEVEL", "ERROR")
os.environ.setdefault("MBM_TEST", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeAdapter:
    """Records everything the engine sends; never touches the network."""

    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.edited: list[dict] = []
        self.callbacks: list[dict] = []
        self.invoices: list[dict] = []
        self.ratelimit = None
        self.http_client = None

    async def send_text(self, ctx, text, parse_mode="HTML", rows=None,
                        reply_to=False, disable_preview=False):
        self.sent.append({"text": text, "rows": rows, "chat_id": ctx.chat_id})
        return len(self.sent)

    async def send_to_chat(self, chat_id, text, parse_mode="HTML", rows=None):
        self.sent.append({"text": text, "rows": rows, "chat_id": chat_id})
        return len(self.sent)

    async def edit_text(self, ctx, text, parse_mode="HTML", rows=None):
        self.edited.append({"text": text, "rows": rows})

    async def answer_callback(self, ctx, text="", alert=False, cache_time=0, url=""):
        self.callbacks.append({"text": text, "alert": alert})

    async def send_media(self, ctx, media_type, source, caption="", parse_mode="HTML", rows=None):
        self.sent.append({"media": media_type, "source": source, "caption": caption})
        return len(self.sent)

    async def remove_keyboard(self, ctx, kind="reply"):
        self.sent.append({"remove_keyboard": kind})

    async def send_invoice(self, ctx, title, description, payload, currency,
                           amount, provider_token="", stars=True):
        self.invoices.append({"title": title, "amount": amount, "currency": currency})

    async def answer_pre_checkout(self, ctx, ok=True, error=""):
        self.callbacks.append({"pre_checkout": ok})

    async def chat_member_status(self, channel, user_id):
        return "member"

    async def delete_message(self, ctx, message_id):
        self.sent.append({"deleted": message_id})

    async def download(self, ctx, file_ref, dest):
        return str(dest)

    async def answer_inline(self, ctx, results):
        self.sent.append({"inline_results": results})

    async def send_album(self, ctx, media_type, sources, caption="", parse_mode="HTML"):
        self.sent.append({"album": media_type, "count": len(sources), "caption": caption})

    async def answer_shipping(self, ctx, ok=True, options=None, error=""):
        self.callbacks.append({"shipping_ok": ok, "options": options, "error": error})

    async def refund_payment(self, ctx, user_id, charge_id, stars=True):
        self.invoices.append({"refund": charge_id, "user": user_id})

    async def call_action(self, action, params):
        self.sent.append({"call": action})
        return {"id": 111, "access_hash": 222, "title": params.get("title", "")}

    async def story_action(self, action, params):
        self.sent.append({"story": action})
        return {"posted": action == "send", "deleted": params.get("ids", [])}

    @staticmethod
    def make_jsonable(obj):
        return obj

    async def invoke_raw(self, method_full, kwargs, userbot=False):
        raise AssertionError("raw MTProto calls are not exercised in smoke tests")


class MemoryDriver:
    """In-memory driver implementing the five repository primitives."""

    def __init__(self) -> None:
        self.tables: dict[str, list[dict]] = {}
        self.seq: dict[str, int] = {}

    async def init(self) -> None:
        return None

    async def close(self) -> None:
        self.tables.clear()

    async def insert(self, table, row):
        rows = self.tables.setdefault(table, [])
        self.seq[table] = self.seq.get(table, 0) + 1
        record = dict(row or {})
        record.setdefault("id", self.seq[table])
        rows.append(record)
        return record["id"]

    async def find(self, table, where, limit=100, offset=0, order_by=""):
        rows = [dict(r) for r in self.tables.get(table, [])
                if all(str(r.get(k)) == str(v) for k, v in (where or {}).items())]
        return rows[int(offset): int(offset) + int(limit)] if limit else rows[int(offset):]

    async def update(self, table, where, fields):
        n = 0
        for row in self.tables.get(table, []):
            if all(str(row.get(k)) == str(v) for k, v in (where or {}).items()):
                row.update(fields or {})
                n += 1
        return n

    async def delete(self, table, where):
        rows = self.tables.get(table, [])
        kept = [
            r for r in rows
            if not all(str(r.get(k)) == str(v) for k, v in (where or {}).items())
        ]
        self.tables[table] = kept
        return len(rows) - len(kept)

    async def count(self, table, where):
        rows = await self.find(table, where, limit=0)
        return len(rows)


def make_ctx(adapter, user_id=42, chat_id=42, text="", callback_data="",
             kind="message", message_id=1):
    """Build an engine Ctx without any Telegram library."""
    from bot.engine import Ctx

    return Ctx(adapter, user_id=user_id, chat_id=chat_id, text=text,
               callback_data=callback_data, update_kind=kind,
               message_id=message_id, first_name="Test", language="en",
               chat_type="private", is_admin=user_id in (1,))


@pytest.fixture()
def fake_adapter():
    """A recording adapter stand-in."""
    return FakeAdapter()


@pytest.fixture()
def fake_update():
    """A dict shaped like a minimal incoming update (library-agnostic)."""
    return {"update_id": 1, "message": {"message_id": 1, "text": "/start",
            "from": {"id": 42, "first_name": "Test", "language_code": "en"},
            "chat": {"id": 42, "type": "private"}}}


@pytest.fixture()
def fake_context(fake_adapter):
    """A ready Ctx built on the fake adapter."""
    return make_ctx(fake_adapter, text="/start", kind="command")


@pytest.fixture()
def in_memory_db():
    """A Database facade over the in-memory driver."""
    from bot.db import Database

    return Database(MemoryDriver())


@pytest.fixture()
def engine(fake_adapter, in_memory_db):
    """A FlowEngine wired to memory-only state and repositories."""
    from bot.engine import FlowEngine
    from bot.state import MemoryStateBackend, StateManager

    return FlowEngine(fake_adapter, StateManager(MemoryStateBackend()), in_memory_db)
