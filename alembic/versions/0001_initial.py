"""Initial schema — auto-provisioned tables plus every designed table."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the initial schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), unique=True),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=255), nullable=True),
        sa.Column("is_admin", sa.Boolean()),
        sa.Column("is_banned", sa.Boolean()),
        sa.Column("is_active", sa.Boolean()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True, unique=True),
        sa.Column("seller_id", sa.BigInteger()),
        sa.Column("title", sa.String(length=200)),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("country", sa.String(length=8)),
        sa.Column("account_age_days", sa.Integer()),
        sa.Column("subscribers_count", sa.Integer()),
        sa.Column("is_premium", sa.Boolean()),
        sa.Column("has_2fa", sa.Boolean()),
        sa.Column("phone_prefix", sa.String(length=8)),
        sa.Column("price_stars", sa.BigInteger()),
        sa.Column("category", sa.String(length=32)),
        sa.Column("status", sa.String(length=32)),
        sa.Column("screenshots", sa.JSON(), nullable=True),
        sa.Column("session_encrypted", sa.Text(), nullable=True),
        sa.Column("view_count", sa.Integer()),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_accounts_status", "accounts", ["status"])
    op.create_index("ix_accounts_category", "accounts", ["category"])
    op.create_index("ix_accounts_price", "accounts", ["price_stars"])
    op.create_index("ix_accounts_seller", "accounts", ["seller_id"])
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True, unique=True),
        sa.Column("account_id", sa.Integer()),
        sa.Column("buyer_id", sa.BigInteger()),
        sa.Column("seller_id", sa.BigInteger()),
        sa.Column("price_stars", sa.BigInteger()),
        sa.Column("fee_stars", sa.BigInteger()),
        sa.Column("net_to_seller_stars", sa.BigInteger()),
        sa.Column("status", sa.String(length=32)),
        sa.Column("escrow_charge_id", sa.String(length=128), nullable=True),
        sa.Column("buyer_confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("seller_paid_at", sa.DateTime(), nullable=True),
        sa.Column("dispute_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_orders_buyer", "orders", ["buyer_id"])
    op.create_index("ix_orders_seller", "orders", ["seller_id"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_account", "orders", ["account_id"])
    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), primary_key=True, unique=True),
        sa.Column("order_id", sa.Integer(), unique=True),
        sa.Column("buyer_id", sa.BigInteger()),
        sa.Column("seller_id", sa.BigInteger()),
        sa.Column("rating", sa.Integer()),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_reviews_seller", "reviews", ["seller_id"])
    op.create_table(
        "disputes",
        sa.Column("id", sa.Integer(), primary_key=True, unique=True),
        sa.Column("order_id", sa.Integer()),
        sa.Column("opened_by", sa.BigInteger()),
        sa.Column("reason", sa.Text()),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32)),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_disputes_status", "disputes", ["status"])
    op.create_table(
        "wallets",
        sa.Column("id", sa.Integer(), primary_key=True, unique=True),
        sa.Column("user_id", sa.BigInteger()),
        sa.Column("balance_stars", sa.BigInteger()),
        sa.Column("locked_stars", sa.BigInteger()),
        sa.Column("lifetime_earned", sa.BigInteger()),
        sa.Column("lifetime_spent", sa.BigInteger()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_wallets_user", "wallets", ["user_id"], unique=True)
    op.create_table(
        "wallet_tx",
        sa.Column("id", sa.Integer(), primary_key=True, unique=True),
        sa.Column("user_id", sa.BigInteger()),
        sa.Column("kind", sa.String(length=32)),
        sa.Column("amount", sa.BigInteger()),
        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column("charge_id", sa.String(length=128), nullable=True),
        sa.Column("balance_after", sa.BigInteger()),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_wallet_tx_user", "wallet_tx", ["user_id"])
    op.create_index("ix_wallet_tx_order", "wallet_tx", ["order_id"])
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Integer(), primary_key=True, unique=True),
        sa.Column("user_id", sa.BigInteger()),
        sa.Column("subject", sa.String(length=200)),
        sa.Column("message", sa.Text()),
        sa.Column("status", sa.String(length=32)),
        sa.Column("admin_reply", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    """Drop the initial schema."""
    op.drop_table("support_tickets")
    op.drop_table("wallet_tx")
    op.drop_table("wallets")
    op.drop_table("disputes")
    op.drop_table("reviews")
    op.drop_table("orders")
    op.drop_table("accounts")
    op.drop_table("users")
