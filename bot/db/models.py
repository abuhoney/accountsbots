"""Database models: auto-provisioned tables (users/sessions/events_log/rate_limit)
plus every table declared in the visual Data Model designer."""
from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    JSON,
    MetaData,
    String,
    Table,
    Text,
)


TABLE_SCHEMAS: dict[str, dict] = {
    "accounts": {
        "auto": False,
        "columns": [
            "id",
            "seller_id",
            "title",
            "description",
            "country",
            "account_age_days",
            "subscribers_count",
            "is_premium",
            "has_2fa",
            "phone_prefix",
            "price_stars",
            "category",
            "status",
            "screenshots",
            "session_encrypted",
            "view_count",
            "published_at"
        ],
        "pk": "id",
        "soft_delete": True,
        "timestamps": True,
        "types": {
            "account_age_days": "int",
            "category": "enum",
            "country": "string",
            "description": "text",
            "has_2fa": "bool",
            "id": "int",
            "is_premium": "bool",
            "phone_prefix": "string",
            "price_stars": "bigint",
            "published_at": "datetime",
            "screenshots": "json",
            "seller_id": "bigint",
            "session_encrypted": "text",
            "status": "enum",
            "subscribers_count": "int",
            "title": "string",
            "view_count": "int"
        }
    },
    "disputes": {
        "auto": False,
        "columns": [
            "id",
            "order_id",
            "opened_by",
            "reason",
            "evidence",
            "status",
            "resolution_note"
        ],
        "pk": "id",
        "soft_delete": False,
        "timestamps": True,
        "types": {
            "evidence": "json",
            "id": "int",
            "opened_by": "bigint",
            "order_id": "int",
            "reason": "text",
            "resolution_note": "text",
            "status": "enum"
        }
    },
    "events_log": {
        "auto": True,
        "columns": [
            "id",
            "user_id",
            "kind",
            "payload_json"
        ],
        "pk": "id",
        "soft_delete": False,
        "timestamps": True,
        "types": {
            "id": "int",
            "kind": "string",
            "payload_json": "text",
            "user_id": "bigint"
        }
    },
    "orders": {
        "auto": False,
        "columns": [
            "id",
            "account_id",
            "buyer_id",
            "seller_id",
            "price_stars",
            "fee_stars",
            "net_to_seller_stars",
            "status",
            "escrow_charge_id",
            "buyer_confirmed_at",
            "seller_paid_at",
            "dispute_reason",
            "notes"
        ],
        "pk": "id",
        "soft_delete": False,
        "timestamps": True,
        "types": {
            "account_id": "int",
            "buyer_confirmed_at": "datetime",
            "buyer_id": "bigint",
            "dispute_reason": "text",
            "escrow_charge_id": "string",
            "fee_stars": "bigint",
            "id": "int",
            "net_to_seller_stars": "bigint",
            "notes": "text",
            "price_stars": "bigint",
            "seller_id": "bigint",
            "seller_paid_at": "datetime",
            "status": "enum"
        }
    },
    "rate_limit": {
        "auto": True,
        "columns": [
            "key",
            "window_start",
            "count"
        ],
        "pk": "key",
        "soft_delete": False,
        "timestamps": False,
        "types": {
            "count": "int",
            "key": "string",
            "window_start": "bigint"
        }
    },
    "reviews": {
        "auto": False,
        "columns": [
            "id",
            "order_id",
            "buyer_id",
            "seller_id",
            "rating",
            "comment"
        ],
        "pk": "id",
        "soft_delete": False,
        "timestamps": True,
        "types": {
            "buyer_id": "bigint",
            "comment": "text",
            "id": "int",
            "order_id": "int",
            "rating": "int",
            "seller_id": "bigint"
        }
    },
    "sessions": {
        "auto": True,
        "columns": [
            "id",
            "user_id",
            "chat_id",
            "state_json",
            "updated_at",
            "expires_at"
        ],
        "pk": "id",
        "soft_delete": False,
        "timestamps": False,
        "types": {
            "chat_id": "bigint",
            "expires_at": "bigint",
            "id": "int",
            "state_json": "text",
            "updated_at": "bigint",
            "user_id": "bigint"
        }
    },
    "support_tickets": {
        "auto": False,
        "columns": [
            "id",
            "user_id",
            "subject",
            "message",
            "status",
            "admin_reply"
        ],
        "pk": "id",
        "soft_delete": False,
        "timestamps": True,
        "types": {
            "admin_reply": "text",
            "id": "int",
            "message": "text",
            "status": "enum",
            "subject": "string",
            "user_id": "bigint"
        }
    },
    "users": {
        "auto": True,
        "columns": [
            "id",
            "user_id",
            "username",
            "first_name",
            "last_name",
            "language",
            "is_admin",
            "is_banned",
            "is_active"
        ],
        "pk": "id",
        "soft_delete": False,
        "timestamps": True,
        "types": {
            "first_name": "string",
            "id": "int",
            "is_active": "bool",
            "is_admin": "bool",
            "is_banned": "bool",
            "language": "string",
            "last_name": "string",
            "user_id": "bigint",
            "username": "string"
        }
    },
    "wallet_tx": {
        "auto": False,
        "columns": [
            "id",
            "user_id",
            "kind",
            "amount",
            "order_id",
            "charge_id",
            "balance_after",
            "note"
        ],
        "pk": "id",
        "soft_delete": False,
        "timestamps": True,
        "types": {
            "amount": "bigint",
            "balance_after": "bigint",
            "charge_id": "string",
            "id": "int",
            "kind": "enum",
            "note": "string",
            "order_id": "int",
            "user_id": "bigint"
        }
    },
    "wallets": {
        "auto": False,
        "columns": [
            "id",
            "user_id",
            "balance_stars",
            "locked_stars",
            "lifetime_earned",
            "lifetime_spent"
        ],
        "pk": "id",
        "soft_delete": False,
        "timestamps": True,
        "types": {
            "balance_stars": "bigint",
            "id": "int",
            "lifetime_earned": "bigint",
            "lifetime_spent": "bigint",
            "locked_stars": "bigint",
            "user_id": "bigint"
        }
    }
}


TABLE_SCOPES: dict[str, str] = {
    "accounts": "global",
    "disputes": "global",
    "orders": "global",
    "reviews": "global",
    "support_tickets": "user",
    "wallet_tx": "global",
    "wallets": "global"
}


AUTO_TABLES = [
    "users",
    "sessions",
    "events_log",
    "rate_limit"
]


metadata = MetaData()


users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger, unique=True, nullable=False),
    Column("username", String(255), nullable=True),
    Column("first_name", String(255), nullable=True),
    Column("last_name", String(255), nullable=True),
    Column("language", String(255), nullable=True),
    Column("is_admin", Boolean, nullable=False),
    Column("is_banned", Boolean, nullable=False),
    Column("is_active", Boolean, nullable=False),
    Column("created_at", DateTime, nullable=True),
    Column("updated_at", DateTime, nullable=True),
)

sessions = Table(
    "sessions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger, nullable=False),
    Column("chat_id", BigInteger, nullable=False),
    Column("state_json", Text, nullable=False),
    Column("updated_at", BigInteger, nullable=False),
    Column("expires_at", BigInteger, nullable=True),
    Index("ix_sessions_user_chat", "user_id", "chat_id", unique=True),
)

events_log = Table(
    "events_log",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", BigInteger, nullable=False),
    Column("kind", String(255), nullable=False),
    Column("payload_json", Text, nullable=True),
    Column("created_at", DateTime, nullable=True),
    Column("updated_at", DateTime, nullable=True),
)

rate_limit = Table(
    "rate_limit",
    metadata,
    Column("key", String(255), primary_key=True),
    Column("window_start", BigInteger, nullable=False),
    Column("count", Integer, nullable=False),
)

accounts = Table(
    "accounts",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, unique=True),
    Column("seller_id", BigInteger, nullable=False),
    Column("title", String(200), nullable=False),
    Column("description", Text, nullable=True),
    Column("country", String(8), nullable=False),
    Column("account_age_days", Integer, nullable=False),
    Column("subscribers_count", Integer, nullable=False),
    Column("is_premium", Boolean, nullable=False),
    Column("has_2fa", Boolean, nullable=False),
    Column("phone_prefix", String(8), nullable=False),
    Column("price_stars", BigInteger, nullable=False),
    Column("category", String(32), nullable=False),
    Column("status", String(32), nullable=False),
    Column("screenshots", JSON, nullable=True),
    Column("session_encrypted", Text, nullable=True),
    Column("view_count", Integer, nullable=False),
    Column("published_at", DateTime, nullable=True),
    Column("created_at", DateTime, nullable=True),
    Column("updated_at", DateTime, nullable=True),
    Column("deleted_at", DateTime, nullable=True),
    Index("ix_accounts_status", "status"),
    Index("ix_accounts_category", "category"),
    Index("ix_accounts_price", "price_stars"),
    Index("ix_accounts_seller", "seller_id"),
)

orders = Table(
    "orders",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, unique=True),
    Column("account_id", Integer, nullable=False),
    Column("buyer_id", BigInteger, nullable=False),
    Column("seller_id", BigInteger, nullable=False),
    Column("price_stars", BigInteger, nullable=False),
    Column("fee_stars", BigInteger, nullable=False),
    Column("net_to_seller_stars", BigInteger, nullable=False),
    Column("status", String(32), nullable=False),
    Column("escrow_charge_id", String(128), nullable=True),
    Column("buyer_confirmed_at", DateTime, nullable=True),
    Column("seller_paid_at", DateTime, nullable=True),
    Column("dispute_reason", Text, nullable=True),
    Column("notes", Text, nullable=True),
    Column("created_at", DateTime, nullable=True),
    Column("updated_at", DateTime, nullable=True),
    Index("ix_orders_buyer", "buyer_id"),
    Index("ix_orders_seller", "seller_id"),
    Index("ix_orders_status", "status"),
    Index("ix_orders_account", "account_id"),
)

reviews = Table(
    "reviews",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, unique=True),
    Column("order_id", Integer, unique=True, nullable=False),
    Column("buyer_id", BigInteger, nullable=False),
    Column("seller_id", BigInteger, nullable=False),
    Column("rating", Integer, nullable=False),
    Column("comment", Text, nullable=True),
    Column("created_at", DateTime, nullable=True),
    Column("updated_at", DateTime, nullable=True),
    Index("ix_reviews_seller", "seller_id"),
)

disputes = Table(
    "disputes",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, unique=True),
    Column("order_id", Integer, nullable=False),
    Column("opened_by", BigInteger, nullable=False),
    Column("reason", Text, nullable=False),
    Column("evidence", JSON, nullable=True),
    Column("status", String(32), nullable=False),
    Column("resolution_note", Text, nullable=True),
    Column("created_at", DateTime, nullable=True),
    Column("updated_at", DateTime, nullable=True),
    Index("ix_disputes_status", "status"),
)

wallets = Table(
    "wallets",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, unique=True),
    Column("user_id", BigInteger, nullable=False),
    Column("balance_stars", BigInteger, nullable=False),
    Column("locked_stars", BigInteger, nullable=False),
    Column("lifetime_earned", BigInteger, nullable=False),
    Column("lifetime_spent", BigInteger, nullable=False),
    Column("created_at", DateTime, nullable=True),
    Column("updated_at", DateTime, nullable=True),
    Index("ix_wallets_user", "user_id", unique=True),
)

wallet_tx = Table(
    "wallet_tx",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, unique=True),
    Column("user_id", BigInteger, nullable=False),
    Column("kind", String(32), nullable=False),
    Column("amount", BigInteger, nullable=False),
    Column("order_id", Integer, nullable=True),
    Column("charge_id", String(128), nullable=True),
    Column("balance_after", BigInteger, nullable=False),
    Column("note", String(200), nullable=True),
    Column("created_at", DateTime, nullable=True),
    Column("updated_at", DateTime, nullable=True),
    Index("ix_wallet_tx_user", "user_id"),
    Index("ix_wallet_tx_order", "order_id"),
)

support_tickets = Table(
    "support_tickets",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True, unique=True),
    Column("user_id", BigInteger, nullable=False),
    Column("subject", String(200), nullable=False),
    Column("message", Text, nullable=False),
    Column("status", String(32), nullable=False),
    Column("admin_reply", Text, nullable=True),
    Column("created_at", DateTime, nullable=True),
    Column("updated_at", DateTime, nullable=True),
)


SQL_TABLES: dict[str, Table] = {
    "users": users,
    "sessions": sessions,
    "events_log": events_log,
    "rate_limit": rate_limit,
    "accounts": accounts,
    "orders": orders,
    "reviews": reviews,
    "disputes": disputes,
    "wallets": wallets,
    "wallet_tx": wallet_tx,
    "support_tickets": support_tickets,
}
