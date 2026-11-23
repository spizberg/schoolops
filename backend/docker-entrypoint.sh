#!/bin/sh
# Apply migrations once the database is reachable, then start the API.
set -eu

echo "Applying database migrations..."
alembic upgrade head

exec "$@"
