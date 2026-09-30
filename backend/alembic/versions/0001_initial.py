"""initial schema"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("n_chunks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
    )
    op.create_table("ingestion_jobs",
        sa.Column("job_id", sa.String(length=64), primary_key=True),
        sa.Column("doc_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ingestion_jobs_doc_id", "ingestion_jobs", ["doc_id"])
    op.create_table("query_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("doc_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("detected_language", sa.Text(), nullable=True),
        sa.Column("retrieved_chunks", sa.JSON(), nullable=False),
        sa.Column("final_answer", sa.Text(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_query_logs_doc_id", "query_logs", ["doc_id"])


def downgrade():
    op.drop_index("ix_query_logs_doc_id", table_name="query_logs")
    op.drop_table("query_logs")
    op.drop_index("ix_ingestion_jobs_doc_id", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")
    op.drop_table("documents")
