"""Create persistent audit events."""

from alembic import op

revision = "20261108_0002"
down_revision = "20261103_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_events (
            id UUID PRIMARY KEY,
            session_id VARCHAR(64) NOT NULL,
            claimed_subject_id VARCHAR(64),
            overall_decision VARCHAR(16) NOT NULL,
            reason_codes JSON NOT NULL,
            face_similarity FLOAT,
            face_liveness FLOAT,
            face_pad_spoof FLOAT,
            voice_similarity FLOAT,
            voice_antispoof FLOAT,
            fused_score FLOAT,
            latency_ms INTEGER NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_events_session_id "
        "ON audit_events (session_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_audit_events_created_at "
        "ON audit_events (created_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_audit_events_created_at")
    op.execute("DROP INDEX IF EXISTS ix_audit_events_session_id")
    op.execute("DROP TABLE IF EXISTS audit_events")
