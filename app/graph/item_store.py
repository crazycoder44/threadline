"""Upsert helper shared by all runners — writes discovered items as it pages, not batched at the end."""
from datetime import datetime, timezone

from app.db.models import Item


def upsert_item(session, *, source_type: str, graph_id: str, graph_url: str, parent_ref: str,
                 sender_or_owner: str | None, classification: str, subject_or_filename: str | None,
                 item_type: str | None, created_at, modified_at) -> None:
    existing = (
        session.query(Item)
        .filter_by(source_type=source_type, parent_ref=parent_ref, graph_id=graph_id)
        .first()
    )
    if existing:
        existing.sender_or_owner = sender_or_owner
        existing.classification = classification
        existing.subject_or_filename = subject_or_filename
        existing.item_type = item_type
        existing.modified_at = modified_at
        return

    session.add(Item(
        source_type=source_type,
        graph_id=graph_id,
        graph_url=graph_url,
        parent_ref=parent_ref,
        sender_or_owner=sender_or_owner,
        classification=classification,
        subject_or_filename=subject_or_filename,
        item_type=item_type,
        created_at=created_at,
        modified_at=modified_at,
        discovered_at=datetime.now(timezone.utc),
    ))
