#!/bin/bash
set -e

echo "Running database migrations..."
if alembic upgrade head; then
    echo "Migrations completed successfully"
else
    echo "Warning: Migration failed, attempting to continue anyway"
fi

echo "Starting application..."
exec "$@"
