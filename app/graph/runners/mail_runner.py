"""Mail runner — Inbox and Sent Items only, per decision (plan open questions).

delta_token is stored as a JSON dict keyed by folder ("inbox", "sentitems") since one
job row covers two independent delta cursors.
"""
import json
from datetime import datetime, timezone

from app.db.base import SessionLocal
from app.db.models import CrawlJob
from app.graph.client import GraphClient
from app.graph.domains import classify
from app.graph.item_store import upsert_item

FOLDERS = {"inbox": "Inbox", "sentitems": "SentItems"}


def run_mail_job(user_id: str, max_items: int | None = None) -> None:
    """max_items caps total messages across both folders — for test slices only.
    When set, the delta token is NOT saved (the crawl is intentionally partial).
    """
    client = GraphClient()
    session = SessionLocal()
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
            start_url = tokens.get(key) or f"/users/{user_id}/mailFolders/{folder}/messages/delta"
            for message in client.run_delta(start_url):
                _store_message(session, user_id, message)
                total_count += 1
                if max_items is not None and total_count >= max_items:
                    capped = True
                    break
            if not capped:
                tokens[key] = client.last_delta_link

        if not capped:
            job.delta_token = json.dumps(tokens)
        job.status = "done"
        job.last_run_at = datetime.now(timezone.utc)
        job.last_item_count = total_count
        job.last_error = None
        session.commit()
    except Exception as exc:
        job.status = "error"
        job.last_error = str(exc)
        session.commit()
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
