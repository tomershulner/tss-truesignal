"""unique external_id on users

Revision ID: 0008
Revises: 0007
Create Date: 2026-03-20
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_users_external_id", "users", ["external_id"])


def downgrade() -> None:
    op.drop_constraint("uq_users_external_id", "users")
