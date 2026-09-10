"""Internal/external tagging by email domain (plan §5)."""
from app.config import INTERNAL_DOMAINS


def classify(email_address: str | None) -> str:
    if not email_address or "@" not in email_address:
        return "external"
    domain = email_address.rsplit("@", 1)[-1].lower()
    return "internal" if domain in INTERNAL_DOMAINS else "external"
