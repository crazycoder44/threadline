"""Central configuration loaded from environment / .env."""
import os
from dotenv import load_dotenv

load_dotenv()


class GraphConfig:
    tenant_id = os.environ.get("GRAPH_TENANT_ID", "")
    client_id = os.environ.get("GRAPH_CLIENT_ID", "")
    client_secret = os.environ.get("GRAPH_CLIENT_SECRET", "")


class DBConfig:
    url = os.environ.get("DATABASE_URL")


# Comma-separated org email domains, e.g. "acme.com,acme.co.uk" — edit in .env
INTERNAL_DOMAINS = {
    d.strip().lower()
    for d in os.environ.get("INTERNAL_DOMAINS", "").split(",")
    if d.strip()
}
