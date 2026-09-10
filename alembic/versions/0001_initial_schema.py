"""Create the initial crawl inventory schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


crawl_job_source_type = sa.Enum(
    "mail", "onedrive", "sharepoint", name="crawljobsourcetype"
)
crawl_job_status = sa.Enum(
    "pending", "running", "done", "error", name="crawljobstatus"
)
item_source_type = sa.Enum("email", "file", name="itemsourcetype")
item_classification = sa.Enum(
    "internal", "external", name="itemclassification"
)


def upgrade() -> None:
    op.create_table(
        "crawl_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "source_type",
            crawl_job_source_type,
            nullable=False,
        ),
        sa.Column("account_or_site_id", sa.String(), nullable=False),
        sa.Column("delta_token", sa.Text(), nullable=True),
        sa.Column("status", crawl_job_status, nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_item_count", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_type",
            "account_or_site_id",
            name="uq_crawl_job_source",
        ),
    )
    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_type", item_source_type, nullable=False),
        sa.Column("graph_id", sa.String(), nullable=False),
        sa.Column("graph_url", sa.Text(), nullable=True),
        sa.Column("parent_ref", sa.String(), nullable=False),
        sa.Column("sender_or_owner", sa.String(), nullable=True),
        sa.Column("classification", item_classification, nullable=True),
        sa.Column("subject_or_filename", sa.Text(), nullable=True),
        sa.Column("item_type", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "discovered_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("processing_status", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_type",
            "parent_ref",
            "graph_id",
            name="uq_item_identity",
        ),
    )


def downgrade() -> None:
    op.drop_table("items")
    op.drop_table("crawl_jobs")

    bind = op.get_bind()
    item_classification.drop(bind, checkfirst=True)
    item_source_type.drop(bind, checkfirst=True)
    crawl_job_status.drop(bind, checkfirst=True)
    crawl_job_source_type.drop(bind, checkfirst=True)
