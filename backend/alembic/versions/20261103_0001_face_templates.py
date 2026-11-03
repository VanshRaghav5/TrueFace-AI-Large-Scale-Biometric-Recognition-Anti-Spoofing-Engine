"""Create persistent subjects and face biometric templates."""

from alembic import op

revision = "20261103_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS subjects (
            id UUID PRIMARY KEY,
            pseudonymous_id VARCHAR(64) NOT NULL UNIQUE,
            consent_granted BOOLEAN NOT NULL DEFAULT FALSE,
            consent_timestamp TIMESTAMP NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_subjects_pseudonymous_id "
        "ON subjects (pseudonymous_id)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS biometric_templates (
            id UUID PRIMARY KEY,
            subject_id UUID NOT NULL REFERENCES subjects(id),
            modality VARCHAR(16) NOT NULL,
            model_name VARCHAR(64) NOT NULL,
            model_version VARCHAR(32) NOT NULL,
            vector_store_index INTEGER,
            template_hash VARCHAR(64) NOT NULL,
            embedding BYTEA,
            embedding_dimension INTEGER NOT NULL DEFAULT 512,
            created_at TIMESTAMP NOT NULL
        )
        """
    )
    op.execute(
        "ALTER TABLE biometric_templates ADD COLUMN IF NOT EXISTS embedding BYTEA"
    )
    op.execute(
        "ALTER TABLE biometric_templates ADD COLUMN IF NOT EXISTS "
        "embedding_dimension INTEGER NOT NULL DEFAULT 512"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_biometric_templates_subject_id "
        "ON biometric_templates (subject_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_face_template_hash "
        "ON biometric_templates (subject_id, modality, template_hash)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_face_template_hash")
    op.execute("DROP TABLE IF EXISTS biometric_templates")
    op.execute("DROP INDEX IF EXISTS ix_subjects_pseudonymous_id")
    op.execute("DROP TABLE IF EXISTS subjects")
