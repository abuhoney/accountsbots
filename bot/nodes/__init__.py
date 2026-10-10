"""Node handler registry — one module per node type used by this design.

Handlers are dispatched by FlowEngine._flow_run (Section 6.5)."""
from __future__ import annotations

from typing import Any

from bot.nodes import ask
from bot.nodes import auth_check
from bot.nodes import compute
from bot.nodes import condition
from bot.nodes import db_query
from bot.nodes import end
from bot.nodes import message
from bot.nodes import payment
from bot.nodes import screen
from bot.nodes import send_and_wait
from bot.nodes import trigger


NODE_HANDLERS: dict[str, Any] = {
    "ASK": ask.handle,
    "AUTH_CHECK": auth_check.handle,
    "COMPUTE": compute.handle,
    "CONDITION": condition.handle,
    "DB_QUERY": db_query.handle,
    "END": end.handle,
    "MESSAGE": message.handle,
    "PAYMENT": payment.handle,
    "SCREEN": screen.handle,
    "SEND_AND_WAIT": send_and_wait.handle,
    "TRIGGER": trigger.handle,
}
