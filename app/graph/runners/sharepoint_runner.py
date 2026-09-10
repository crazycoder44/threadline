"""SharePoint runner — one job per site; internally crawls every document library (drive)
in that site. delta_token is a JSON dict keyed by drive_id since a site can have several libraries.
"""
import json
from datetime import datetime, timezone

from app.db.base import SessionLocal
from app.db.models import CrawlJob
from app.graph.client import GraphClient
from app.graph.domains import classify
from app.graph.item_store import upsert_item
from app.logging_config import get_job_logger


def run_sharepoint_job(site_id: str, max_items: int | None = None) -> None:
    """max_items caps total files across all libraries — for test slices only.
    When set, the delta token is NOT saved (the crawl is intentionally partial).
    """
    logger = get_job_logger("sharepoint", site_id)
    logger.info("job_started target=%s max_items=%s", site_id, max_items or "unlimited")
    client = GraphClient(logger=logger)
    session = SessionLocal()
    job = None
    try:
        job = session.query(CrawlJob).filter_by(source_type="sharepoint", account_or_site_id=site_id).one()
        job.status = "running"
        session.commit()

        tokens = json.loads(job.delta_token) if job.delta_token else {}
        total_count = 0
        capped = False
        drives = client.get(f"/sites/{site_id}/drives").get("value", [])

        for drive in drives:
            if capped:
                break
            drive_id = drive["id"]
            start_url = tokens.get(drive_id) or f"/drives/{drive_id}/root/delta"
            for item in client.run_delta(start_url):
                _store_drive_item(session, site_id, drive_id, item)
                total_count += 1
                if total_count % 1000 == 0:
                    logger.info("progress items=%s drive=%s", total_count, drive_id)
                if max_items is not None and total_count >= max_items:
                    capped = True
                    break
            if not capped:
                tokens[drive_id] = client.last_delta_link

        if not capped:
            job.delta_token = json.dumps(tokens)
        job.status = "done"
        job.last_run_at = datetime.now(timezone.utc)
        job.last_item_count = total_count
        job.last_error = None
        session.commit()
        logger.info("job_completed target=%s items=%s drives=%s capped=%s", site_id, total_count, len(drives), capped)
    except Exception as exc:
        if job is not None:
            job.status = "error"
            job.last_error = str(exc)
            session.commit()
        logger.exception("job_failed target=%s items=%s", site_id, total_count if "total_count" in locals() else 0)
        raise
    finally:
        session.close()


def _store_drive_item(session, site_id: str, drive_id: str, item: dict) -> None:
    if "file" not in item:
        return  # skip folders
    owner = (item.get("createdBy") or {}).get("user", {}).get("email")
    upsert_item(
        session,
        source_type="file",
        graph_id=item["id"],
        graph_url=item.get("webUrl", ""),
        parent_ref=f"{site_id}:{drive_id}",
        sender_or_owner=owner,
        classification=classify(owner),
        subject_or_filename=item.get("name"),
        item_type="file",
        created_at=item.get("createdDateTime"),
        modified_at=item.get("lastModifiedDateTime"),
    )
