"""cascade ingestion jobs when a document is deleted"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ingestion_jobs_doc_id_fkey", "ingestion_jobs", type_="foreignkey")
    op.create_foreign_key(
        "ingestion_jobs_doc_id_fkey",
        "ingestion_jobs",
        "documents",
        ["doc_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade():
    op.drop_constraint("ingestion_jobs_doc_id_fkey", "ingestion_jobs", type_="foreignkey")
    op.create_foreign_key(
        "ingestion_jobs_doc_id_fkey", "ingestion_jobs", "documents", ["doc_id"], ["id"]
    )
