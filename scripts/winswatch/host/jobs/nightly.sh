#!/bin/bash
# NIGHTLY (scheduled by the Unraid user script "winswatch", 04:30, before Kometa's 05:00 run):
# refresh the NewEp_/ReturnsIn_/Returns_ labels on the production libraries from Sonarr.
# User ratings come from Kometa itself (mass_user_rating_update: mdb); DaysLeft_ labels from the update_days_left script.
set -euo pipefail
ROOT=/mnt/user/appdata/scripts/winswatch
SECTIONS=$(cat "$ROOT/host/prod_sections")
docker run --rm -v "$ROOT":/app -w /app --env-file "$ROOT/.env" python:3.12-slim bash -c \
  "pip install -q -r requirements-runtime.txt >/dev/null && python airdates.py --sections $SECTIONS"
