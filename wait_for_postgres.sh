#!/bin/bash

# Wait until Postgres is ready
until pg_isready -h db -p 5432 -U postgres; do
  echo "Waiting for Postgres..."
  sleep 2
done

echo "Postgres is ready"
