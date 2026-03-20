"""simplify schema

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-20
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- users: drop external_id ---
    op.drop_index("ix_users_external_id", table_name="users")
    op.drop_column("users", "external_id")

    # --- messages: drop payload + client_ts, add content ---
    op.drop_column("messages", "client_ts")
    op.drop_column("messages", "payload")
    op.add_column("messages", sa.Column("content", sa.Text(), nullable=False, server_default=""))
    op.alter_column("messages", "content", server_default=None)
    op.create_index("ix_messages_content", "messages", ["content"])

    # --- session_messages: drop and recreate ---
    op.drop_table("session_messages")
    op.create_table(
        "session_messages",
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(always=True),
            primary_key=True,
        ),
        sa.Column(
            "session_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.session_id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.user_id"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "sent_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    # --- session_messages: restore original ---
    op.drop_table("session_messages")
    op.create_table(
        "session_messages",
        sa.Column(
            "session_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.session_id"),
            primary_key=True,
        ),
        sa.Column(
            "message_id",
            sa.BigInteger(),
            sa.ForeignKey("messages.message_id"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.user_id"),
            nullable=False,
        ),
        sa.Column(
            "added_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- messages: restore payload + client_ts ---
    op.drop_index("ix_messages_content", table_name="messages")
    op.drop_column("messages", "content")
    op.add_column("messages", sa.Column("client_ts", sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column(
        "messages",
        sa.Column(
            "payload",
            sa.dialects.postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
    )

    # --- users: restore external_id ---
    op.add_column("users", sa.Column("external_id", sa.Text(), nullable=False, server_default=""))
    op.alter_column("users", "external_id", server_default=None)
    op.create_index("ix_users_external_id", "users", ["external_id"])
    op.create_unique_constraint("uq_users_external_id", "users", ["external_id"])
