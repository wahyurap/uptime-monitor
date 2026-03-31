#!/bin/bash
set -e

echo "Waiting for database to be ready..."
for i in {1..30}; do
    if pg_isready -h db -U uptime -d uptime_monitor 2>/dev/null; then
        echo "Database is ready!"
        break
    fi
    echo "Attempt $i/30: Waiting for database..."
    sleep 2
done

echo "Running database migrations..."
alembic upgrade head || {
    echo "Migration failed, but continuing startup..."
    # Don't exit on migration error - database might already be initialized
}

echo "Starting application..."
exec "$@"
