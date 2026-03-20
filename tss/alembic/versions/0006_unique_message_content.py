"""unique message content

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-20
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_messages_content", table_name="messages")
    op.create_unique_constraint("uq_messages_content", "messages", ["content"])


def downgrade() -> None:
    op.drop_constraint("uq_messages_content", "messages")
    op.create_index("ix_messages_content", "messages", ["content"])
