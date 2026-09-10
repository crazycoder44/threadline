"""Populate crawl_jobs: two rows per user (mail, onedrive), one row per site (plan §3).
Safe to re-run — never duplicates existing job rows.
"""
from app.db.base import SessionLocal
from app.db.models import CrawlJob
from app.graph.client import GraphClient


def discover_jobs() -> None:
    client = GraphClient()
    session = SessionLocal()
    try:
        for user in client.paged_get("/users", params={"$select": "id,mail,userPrincipalName"}):
            upsert_job(session, "mail", user["id"])
            upsert_job(session, "onedrive", user["id"])

        # GET /sites requires `search` to enumerate sites in v1.0 — a bare GET returns empty, not an error.
        for site in client.paged_get("/sites", params={"search": "*", "$select": "id,displayName"}):
            upsert_job(session, "sharepoint", site["id"])

        session.commit()
    finally:
        session.close()


def upsert_job(session, source_type: str, account_or_site_id: str) -> None:
    existing = (
        session.query(CrawlJob)
        .filter_by(source_type=source_type, account_or_site_id=account_or_site_id)
        .first()
    )
    if not existing:
        session.add(CrawlJob(source_type=source_type, account_or_site_id=account_or_site_id, status="pending"))
