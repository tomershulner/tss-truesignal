"""decouple messages from users

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-20
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Payload already exists from 0001, just migrate data if needed
    # Check if verbal_messages/nonverbal_messages exist, if so migrate
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'verbal_messages') THEN
                UPDATE messages m
                SET payload = jsonb_build_object(
                    'type', m.message_type::text,
                    'content', vm.content,
                    'language', vm.language,
                    'classified_at', vm.classified_at,
                    'classification_raw', vm.classification_raw
                )
                FROM verbal_messages vm
                WHERE vm.message_id = m.message_id;
            END IF;
        END $$;
    """)
    
    # Set default for any messages without data
    op.execute("UPDATE messages SET payload = '{\"type\": \"nonverbal\"}'::jsonb WHERE payload IS NULL OR payload::text = '{}'")

    # 2. Drop tables that are now folded into payload (if they exist)
    op.execute("DROP TABLE IF EXISTS nonverbal_messages")
    op.execute("DROP TABLE IF EXISTS verbal_messages")

    # 3. Drop indexes referencing user_id / session_id (if they exist)
    op.execute("DROP INDEX IF EXISTS ix_messages_user_id")
    op.execute("DROP INDEX IF EXISTS ix_messages_user_id_received_at")
    op.execute("DROP INDEX IF EXISTS ix_messages_session_id")
    op.execute("DROP INDEX IF EXISTS ix_messages_message_type")

    # 4. Drop FK constraints (if they exist)
    op.execute("ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_user_id_fkey")
    op.execute("ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_session_id_fkey")

    # 5. Drop columns (if they exist)
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS user_id")
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS session_id")
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS message_type")
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS metadata")

    # 6. Drop the now-unused enum type
    op.execute("DROP TYPE IF EXISTS message_type")


def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported for this migration")