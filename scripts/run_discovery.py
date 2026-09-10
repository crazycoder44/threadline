"""Standalone: populate crawl_jobs from /users and /sites (plan §3). Safe to re-run."""
from app.graph.discovery import discover_jobs


def main() -> None:
    discover_jobs()


if __name__ == "__main__":
    main()
