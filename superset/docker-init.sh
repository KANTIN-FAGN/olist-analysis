#!/bin/sh
set -e

superset db upgrade

superset fab create-admin \
  --username "${SUPERSET_ADMIN_USER}" \
  --firstname Admin \
  --lastname User \
  --email "${SUPERSET_ADMIN_EMAIL}" \
  --password "${SUPERSET_ADMIN_PASSWORD}" || true

superset init

gunicorn \
  --bind 0.0.0.0:8088 \
  --workers 2 \
  --timeout 300 \
  "superset.app:create_app()"