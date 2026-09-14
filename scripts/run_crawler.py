"""Dispatcher: runs pending, completed, and failed crawl_jobs one at a time (plan §7).
Run scripts/run_discovery.py first to populate crawl_jobs.
"""
from app.db.base import SessionLocal
from app.db.models import CrawlJob
from app.graph.runners.mail_runner import run_mail_job
from app.graph.runners.onedrive_runner import run_onedrive_job
from app.graph.runners.sharepoint_runner import run_sharepoint_job
from app.logging_config import get_logger

RUNNERS = {
    "mail": run_mail_job,
    "onedrive": run_onedrive_job,
    "sharepoint": run_sharepoint_job,
}


def main() -> None:
    logger = get_logger()
    session = SessionLocal()
    try:
        jobs = session.query(CrawlJob).filter(CrawlJob.status.in_(["pending", "done", "error"])).all()
        job_refs = [(j.source_type, j.account_or_site_id) for j in jobs]
    finally:
        session.close()

    for source_type, account_or_site_id in job_refs:
        logger.info("dispatcher_job_started source=%s target=%s", source_type, account_or_site_id)
        try:
            RUNNERS[source_type](account_or_site_id)
        except Exception as exc:
            logger.error(
                "dispatcher_job_failed source=%s target=%s error=%s",
                source_type,
                account_or_site_id,
                exc,
            )


if __name__ == "__main__":
    main()
