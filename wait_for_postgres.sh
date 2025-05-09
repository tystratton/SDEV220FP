#!/bin/sh

set -e

# Debug: show script path and shell
echo "Running: $0 with shell: $SHELL"

# Wait until Postgres is ready
until pg_isready -h "$DB_HOST" -p 5432 -U "$DB_USER"; do
  echo "Waiting for Postgres at $DB_HOST as $DB_USER..."
  sleep 2
done

echo "Postgres is ready"
