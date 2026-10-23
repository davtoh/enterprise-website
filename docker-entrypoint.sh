#!/bin/sh
set -e

echo "==> Running Enterprise Website container entrypoint..."

# Wait for relational database if not in SQLite mode
if [ "$USE_SQLITE" != "True" ] && [ "$USE_SQLITE" != "true" ] && [ -n "$DB_HOST" ]; then
    DB_PORT_VAL=${DB_PORT:-5432}
    echo "==> Waiting for database at $DB_HOST:$DB_PORT_VAL..."
    max_retries=30
    count=0
    while ! python -c "
import socket, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(2)
try:
    s.connect(('$DB_HOST', int('$DB_PORT_VAL')))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
        count=$((count + 1))
        if [ "$count" -ge "$max_retries" ]; then
            echo "==> ERROR: Timed out waiting for database at $DB_HOST:$DB_PORT_VAL"
            exit 1
        fi
        sleep 1
    done
    echo "==> Database is reachable and accepting connections!"
fi

# Apply migrations
echo "==> Applying database migrations..."
python manage.py migrate --noinput

# Synchronize dynamic menus from plugin registry
echo "==> Synchronizing dynamic navigation menus..."
python manage.py sync_menus || true

# Collect static files in production / non-debug mode
if [ "$DEBUG" != "True" ] && [ "$DEBUG" != "true" ]; then
    echo "==> Collecting static files for production..."
    python manage.py collectstatic --noinput --clear || true
fi

echo "==> Launching server process: $@"
exec "$@"
