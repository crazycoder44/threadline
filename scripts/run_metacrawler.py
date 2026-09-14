"""Run discovery, then crawl every known Microsoft 365 target."""
from app.graph.discovery import discover_jobs
from scripts.run_crawler import main as run_crawler


def main() -> None:
    discover_jobs()
    run_crawler()


if __name__ == "__main__":
    main()