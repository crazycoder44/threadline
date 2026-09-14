#!/bin/sh
set -eu

: "${DATABASE_URL:?DATABASE_URL must be set}"

max_attempts="${DB_CONNECT_MAX_ATTEMPTS:-60}"
retry_seconds="${DB_CONNECT_RETRY_SECONDS:-5}"
attempt=1

echo "Waiting for database connectivity..."
while ! python -c 'from sqlalchemy import create_engine, text; import os; engine = create_engine(os.environ["DATABASE_URL"]); connection = engine.connect(); connection.execute(text("SELECT 1")); connection.close()' 2>/dev/null; do
    if [ "$attempt" -ge "$max_attempts" ]; then
        echo "Database is not reachable after $max_attempts attempts." >&2
        exit 1
    fi
    echo "Database is not ready (attempt $attempt/$max_attempts); retrying in ${retry_seconds}s..."
    attempt=$((attempt + 1))
    sleep "$retry_seconds"
done

echo "Database connectivity confirmed."

if [ "${1:-crawl}" = "migrate" ]; then
    echo "Applying migrations..."
    exec alembic upgrade head
fi

: "${GRAPH_TENANT_ID:?GRAPH_TENANT_ID must be set}"
: "${GRAPH_CLIENT_ID:?GRAPH_CLIENT_ID must be set}"
: "${GRAPH_CLIENT_SECRET:?GRAPH_CLIENT_SECRET must be set}"

echo "Starting metacrawler..."
exec python -m scripts.run_metacrawler