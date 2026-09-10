"""Dispatcher: picks up pending/error crawl_jobs rows and runs them one at a time (plan §7).
Run scripts/run_discovery.py first to populate crawl_jobs.
"""
from app.db.base import SessionLocal, init_db
from app.db.models import CrawlJob
from app.graph.runners.mail_runner import run_mail_job
from app.graph.runners.onedrive_runner import run_onedrive_job
from app.graph.runners.sharepoint_runner import run_sharepoint_job

RUNNERS = {
    "mail": run_mail_job,
    "onedrive": run_onedrive_job,
    "sharepoint": run_sharepoint_job,
}


def main() -> None:
    init_db()
    session = SessionLocal()
    try:
        jobs = session.query(CrawlJob).filter(CrawlJob.status.in_(["pending", "error"])).all()
        job_refs = [(j.source_type, j.account_or_site_id) for j in jobs]
    finally:
        session.close()

    for source_type, account_or_site_id in job_refs:
        print(f"Running {source_type} job for {account_or_site_id}...")
        try:
            RUNNERS[source_type](account_or_site_id)
        except Exception as exc:
            print(f"  failed: {exc}")


if __name__ == "__main__":
    main()
