"""crawl_jobs (job-control) and items (inventory) tables — Step 1 metadata sweep only.
See meta_crawler_implementation_plan.md §1-2 for the schema this mirrors.
"""
import enum

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, UniqueConstraint
from sqlalchemy.sql import func

from app.db.base import Base


class CrawlJobSourceType(str, enum.Enum):
    mail = "mail"
    onedrive = "onedrive"
    sharepoint = "sharepoint"


class CrawlJobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    error = "error"


class ItemSourceType(str, enum.Enum):
    email = "email"
    file = "file"


class ItemClassification(str, enum.Enum):
    internal = "internal"
    external = "external"


class CrawlJob(Base):
    """One row per (mailbox, mail), (mailbox, onedrive), (site, sharepoint) target.

    delta_token stores a JSON blob when a job has more than one sub-cursor
    (e.g. mail's Inbox + Sent folders, or a site's several document libraries).
    """
    __tablename__ = "crawl_jobs"
    __table_args__ = (UniqueConstraint("source_type", "account_or_site_id", name="uq_crawl_job_source"),)

    id = Column(Integer, primary_key=True)
    source_type = Column(Enum(CrawlJobSourceType), nullable=False)
    account_or_site_id = Column(String, nullable=False)
    delta_token = Column(Text)
    status = Column(Enum(CrawlJobStatus), nullable=False, default=CrawlJobStatus.pending)
    last_run_at = Column(DateTime(timezone=True))
    last_item_count = Column(Integer, default=0)
    last_error = Column(Text)


class Item(Base):
    """One row per email/file discovered. Metadata only — no content read at this stage."""
    __tablename__ = "items"
    __table_args__ = (UniqueConstraint("source_type", "parent_ref", "graph_id", name="uq_item_identity"),)

    id = Column(Integer, primary_key=True)
    source_type = Column(Enum(ItemSourceType), nullable=False)
    graph_id = Column(String, nullable=False)
    graph_url = Column(Text)
    parent_ref = Column(String, nullable=False)  # mailbox user id or site/drive id
    sender_or_owner = Column(String)
    classification = Column(Enum(ItemClassification))
    subject_or_filename = Column(Text)
    item_type = Column(String)
    created_at = Column(DateTime(timezone=True))
    modified_at = Column(DateTime(timezone=True))
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())
    processing_status = Column(String, nullable=False, default="discovered")
