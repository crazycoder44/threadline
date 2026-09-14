"""Mail runner — Inbox and Sent Items only, per decision (plan open questions).

delta_token is stored as a JSON dict keyed by folder ("inbox", "sentitems") since one
job row covers two independent delta cursors.
"""
import json
from datetime import datetime, timezone

from app.db.base import SessionLocal
from app.db.models import CrawlJob
from app.graph.client import GraphClient, InvalidDeltaTokenError
from app.graph.domains import classify
from app.graph.item_store import upsert_item
from app.logging_config import get_job_logger

FOLDERS = {"inbox": "Inbox", "sentitems": "SentItems"}


def run_mail_job(user_id: str, max_items: int | None = None) -> None:
    """max_items caps total messages across both folders — for test slices only.
    When set, the delta token is NOT saved (the crawl is intentionally partial).
    """
    logger = get_job_logger("mail", user_id)
    logger.info("job_started target=%s max_items=%s", user_id, max_items or "unlimited")
    client = GraphClient(logger=logger)
    session = SessionLocal()
    job = None
    try:
        job = session.query(CrawlJob).filter_by(source_type="mail", account_or_site_id=user_id).one()
        job.status = "running"
        session.commit()

        tokens = json.loads(job.delta_token) if job.delta_token else {}
        total_count = 0
        capped = False

        for key, folder in FOLDERS.items():
            if max_items is not None and total_count >= max_items:
                break
            default_url = f"/users/{user_id}/mailFolders/{folder}/messages/delta"
            for attempt in range(2):
                start_url = tokens.get(key) or default_url
                try:
                    for message in client.run_delta(start_url):
                        _store_message(session, user_id, message)
                        total_count += 1
                        if total_count % 1000 == 0:
                            logger.info("progress items=%s folder=%s", total_count, folder)
                        if max_items is not None and total_count >= max_items:
                            capped = True
                            break
                    break
                except InvalidDeltaTokenError:
                    if attempt:
                        raise
                    tokens.pop(key, None)
                    logger.warning("delta_token_reset target=%s folder=%s", user_id, folder)
            if not capped:
                tokens[key] = client.last_delta_link

        if not capped:
            job.delta_token = json.dumps(tokens)
        job.status = "done"
        job.last_run_at = datetime.now(timezone.utc)
        job.last_item_count = total_count
        job.last_error = None
        session.commit()
        logger.info("job_completed target=%s items=%s capped=%s", user_id, total_count, capped)
    except Exception as exc:
        if job is not None:
            job.status = "error"
            job.last_error = str(exc)
            session.commit()
        logger.exception("job_failed target=%s items=%s", user_id, total_count if "total_count" in locals() else 0)
        raise
    finally:
        session.close()


def _store_message(session, user_id: str, message: dict) -> None:
    sender = (message.get("from") or {}).get("emailAddress", {}).get("address")
    upsert_item(
        session,
        source_type="email",
        graph_id=message["id"],
        graph_url=message.get("webLink", ""),
        parent_ref=user_id,
        sender_or_owner=sender,
        classification=classify(sender),
        subject_or_filename=message.get("subject"),
        item_type="message",
        created_at=message.get("createdDateTime"),
        modified_at=message.get("lastModifiedDateTime"),
    )
