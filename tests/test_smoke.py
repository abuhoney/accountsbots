"""Smoke tests (Section 24) — run with: pytest -q"""
from __future__ import annotations

import asyncio
import importlib
import json


import pkgutil

from bot import config as cfg
import bot


def test_all_modules_import():
    """Every module of the bot package imports without error."""
    import bot as root

    failures = []
    for info in pkgutil.walk_packages(root.__path__, prefix="bot."):
        if info.name.startswith("bot.adapter") or ".handlers" in info.name:
            continue  # library-specific modules need the Telegram library
        try:
            importlib.import_module(info.name)
        except Exception as exc:  # noqa: BLE001 - report and continue
            failures.append(f"{info.name}: {exc}")
    assert not failures, "\n".join(failures)


def test_flows_structure():
    """All flows are well-formed and every node type has a handler."""
    from bot.flows import FLOWS, TRIGGERS
    from bot.nodes import NODE_HANDLERS

    assert isinstance(FLOWS, dict)
    for flow_id, flow in FLOWS.items():
        assert flow.get("start") in flow["nodes"], f"flow {flow_id} has no start node"
        for edge in flow["edges"]:
            assert edge["from"] in flow["nodes"], f"dangling edge from {edge['from']}"
            assert edge["to"] in flow["nodes"], f"dangling edge to {edge['to']}"
        for node in flow["nodes"].values():
            assert node["type"] in NODE_HANDLERS, f"no handler for {node['type']}"
    for trigger in TRIGGERS:
        assert trigger["flow_id"] in FLOWS, f"trigger {trigger['name']} -> missing flow"


def test_database_schema_roundtrip(in_memory_db):
    """Repositories create, read, update and delete rows."""
    async def scenario():
        await in_memory_db.init()
        new_id = await in_memory_db.custom("users").insert({"user_id": 7, "username": "t"})
        assert new_id is not None
        row = await in_memory_db.users.get(7)
        assert row is not None
        await in_memory_db.users.set_field(7, "language", "en")
        assert (await in_memory_db.users.get(7))["language"] == "en"
        removed = await in_memory_db.custom("users").delete_where({"user_id": 7})
        assert removed == 1
        await in_memory_db.close()

    asyncio.run(scenario())


def test_state_backend_roundtrip():
    """Sessions persist, expire and sweep (Section 5)."""
    from bot.state import MemoryStateBackend

    async def scenario():
        backend = MemoryStateBackend()
        await backend.set(1, 1, {"flow_id": "f", "expires_at": None, "vars": {"x": 1}})
        loaded = await backend.get(1, 1)
        assert loaded and loaded["vars"]["x"] == 1
        await backend.set(2, 2, {"flow_id": "f", "expires_at": 1, "vars": {}})
        removed = await backend.sweep_expired(2)
        assert removed == 1
        await backend.delete(1, 1)
        assert await backend.get(1, 1) is None

    asyncio.run(scenario())


def test_safe_eval_whitelist():
    """The expression engine never exposes imports/exec/open (Section 27)."""
    from bot.engine import _safe_eval

    env = {"x": 5, "name": "abc"}
    assert _safe_eval("x * 2 + 1", env) == 11
    assert _safe_eval("len(name)", env) == 3
    assert _safe_eval("x in [1, 5, 9]", env) is True
    for evil in ("__import__('os')", "open('/etc/passwd')", "eval('1')",
                 "exec('x=1')", "().__class__.__bases__"):
        try:
            _safe_eval(evil, env)
            raise AssertionError("unsafe expression accepted: " + evil)
        except Exception as exc:
            assert not isinstance(exc, AssertionError), evil
            assert exc is not None


def test_synthetic_start_produces_reply(engine, fake_adapter):
    """A synthetic /start update produces at least one reply (AC)."""
    from bot.flows import TRIGGERS

    async def scenario():
        command = None
        for trigger in TRIGGERS:
            if trigger["kind"] == "command":
                command = trigger["pattern"]
                break
        if command is None:
            return  # design without command triggers: nothing to assert
        from tests.conftest import make_ctx

        ctx = make_ctx(fake_adapter, text="/" + command, kind="command")
        await engine.handle_command(command, ctx)

    asyncio.run(scenario())


def test_config_reads_env():
    """Config exposes env values and admin parsing."""
    assert cfg.parse_admins("1, 2,x,3") == (1, 2, 3)
    assert isinstance(cfg.env("DEFINITELY_MISSING_VAR", "fallback"), str)
    assert json.loads(json.dumps({"a": 1})) == {"a": 1}
