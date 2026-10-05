#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install python dependencies
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi

# Collect static files
python manage.py collectstatic --no-input

# Apply database migrations if a production database URL is available
if [ -n "$DATABASE_URL" ] || [ -n "$POSTGRES_URL" ] || [ -n "$INTERNAL_DATABASE_URL" ]; then
    echo "Applying database migrations..."
    python manage.py migrate --no-input
else
    echo "Notice: Remote database URL not detected during build step. Skipping migrations."
fi
