"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-20
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE users (
            user_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            external_id TEXT NOT NULL UNIQUE,
            vibe_score  DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ix_users_external_id ON users (external_id)")

    op.execute("""
        CREATE TABLE messages (
            message_id  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            user_id     BIGINT NOT NULL REFERENCES users(user_id),
            vibe_score  DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            payload     JSONB NOT NULL,
            received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            client_ts   TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX ix_messages_user_id ON messages (user_id)")
    op.execute("CREATE INDEX ix_messages_received_at ON messages (received_at DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TABLE IF EXISTS users")
