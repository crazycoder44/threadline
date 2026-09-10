"""Run a capped test crawl against ONE user (mail+onedrive) and ONE SharePoint site,
instead of the full-tenant discovery/crawl path. Nothing here is resumable — it's for
validating the pipeline on a small, named slice before opening it up (plan §"build order" step 9).

Usage:
    .\\myvenv\\Scripts\\python.exe -m scripts.run_test_slice --user someone@acme.com --max-items 50

If --site is omitted, the first site returned by tenant site discovery is picked automatically.
"""
import argparse

from app.db.base import SessionLocal, init_db
from app.graph.client import GraphClient
from app.graph.discovery import upsert_job
from app.graph.runners.mail_runner import run_mail_job
from app.graph.runners.onedrive_runner import run_onedrive_job
from app.graph.runners.sharepoint_runner import run_sharepoint_job


def pick_first_site(client: GraphClient) -> dict:
    # GET /sites requires `search` to enumerate sites in v1.0 — a bare GET returns empty, not an error.
    sites = client.get("/sites", params={"search": "*", "$select": "id,displayName,webUrl"}).get("value", [])
    if sites:
        return sites[0]
    return client.get("/sites/root", params={"$select": "id,displayName,webUrl"})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", required=True, help="User email/UPN to crawl mail+onedrive for")
    parser.add_argument("--site", help="SharePoint site ID to crawl (auto-picked if omitted)")
    parser.add_argument("--max-items", type=int, default=50)
    args = parser.parse_args()

    init_db()
    client = GraphClient()
    user_id = client.get(f"/users/{args.user}")["id"]

    if args.site:
        site_id = args.site
    else:
        site = pick_first_site(client)
        site_id = site["id"]
        print(f"No --site given — picked '{site.get('displayName')}' ({site.get('webUrl')})")

    session = SessionLocal()
    try:
        upsert_job(session, "mail", user_id)
        upsert_job(session, "onedrive", user_id)
        upsert_job(session, "sharepoint", site_id)
        session.commit()
    finally:
        session.close()

    print(f"Crawling mail for {args.user} (max {args.max_items})...")
    run_mail_job(user_id, max_items=args.max_items)

    print(f"Crawling onedrive for {args.user} (max {args.max_items})...")
    run_onedrive_job(user_id, max_items=args.max_items)

    print(f"Crawling site {site_id} (max {args.max_items})...")
    run_sharepoint_job(site_id, max_items=args.max_items)

    print("Done — check the items table.")


if __name__ == "__main__":
    main()
