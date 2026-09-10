"""OneDrive runner — one delta cursor per user's drive."""
from datetime import datetime, timezone

from app.db.base import SessionLocal
from app.db.models import CrawlJob
from app.graph.client import GraphClient
from app.graph.domains import classify
from app.graph.item_store import upsert_item
from app.logging_config import get_job_logger


def run_onedrive_job(user_id: str, max_items: int | None = None) -> None:
    """max_items caps total files fetched — for test slices only.
    When set, the delta token is NOT saved (the crawl is intentionally partial).
    """
    logger = get_job_logger("onedrive", user_id)
    logger.info("job_started target=%s max_items=%s", user_id, max_items or "unlimited")
    client = GraphClient(logger=logger)
    session = SessionLocal()
    job = None
    try:
        job = session.query(CrawlJob).filter_by(source_type="onedrive", account_or_site_id=user_id).one()
        job.status = "running"
        session.commit()

        start_url = job.delta_token or f"/users/{user_id}/drive/root/delta"
        count = 0
        capped = False
        for item in client.run_delta(start_url):
            _store_drive_item(session, user_id, item)
            count += 1
            if count % 1000 == 0:
                logger.info("progress items=%s", count)
            if max_items is not None and count >= max_items:
                capped = True
                break

        if not capped:
            job.delta_token = client.last_delta_link
        job.status = "done"
        job.last_run_at = datetime.now(timezone.utc)
        job.last_item_count = count
        job.last_error = None
        session.commit()
        logger.info("job_completed target=%s items=%s capped=%s", user_id, count, capped)
    except Exception as exc:
        if job is not None:
            job.status = "error"
            job.last_error = str(exc)
            session.commit()
        logger.exception("job_failed target=%s items=%s", user_id, count if "count" in locals() else 0)
        raise
    finally:
        session.close()


def _store_drive_item(session, user_id: str, item: dict) -> None:
    if "file" not in item:
        return  # skip folders
    owner = (item.get("createdBy") or {}).get("user", {}).get("email")
    upsert_item(
        session,
        source_type="file",
        graph_id=item["id"],
        graph_url=item.get("webUrl", ""),
        parent_ref=user_id,
        sender_or_owner=owner,
        classification=classify(owner),
        subject_or_filename=item.get("name"),
        item_type="file",
        created_at=item.get("createdDateTime"),
        modified_at=item.get("lastModifiedDateTime"),
    )
