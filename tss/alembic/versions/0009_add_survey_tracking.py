"""add survey tracking

Revision ID: 0009
Revises: 0008
Create Date: 2026-03-20
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Survey responses - tracks who voted
    op.execute("""
        CREATE TABLE survey_responses (
            response_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            user_id         BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
            submitted_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            responses       JSONB NOT NULL
        )
    """)
    op.execute("CREATE INDEX ix_survey_responses_submitted_at ON survey_responses (submitted_at DESC)")
    
    # Survey stats - vote counts per message
    op.execute("""
        CREATE TABLE survey_stats (
            message_id          BIGINT PRIMARY KEY REFERENCES messages(message_id) ON DELETE CASCADE,
            times_shown         INT NOT NULL DEFAULT 0,
            times_selected      INT NOT NULL DEFAULT 0,
            last_updated        TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS survey_stats")
    op.execute("DROP TABLE IF EXISTS survey_responses")
