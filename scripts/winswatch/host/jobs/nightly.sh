#!/bin/bash
# NIGHTLY (scheduled by the Unraid user script "winswatch", 04:30, before Kometa's 05:00 run):
# 1. scores.py: MDBList score -> user-rating slot (metadata edit; Kometa's mdb writer goes via /:/rate and gets rounded by plex.tv)
# 2. airdates.py: NewEp_/ReturnsIn_/Returns_ labels from Sonarr.   DaysLeft_ labels come from the update_days_left script.
set -euo pipefail
ROOT=/mnt/user/appdata/scripts/winswatch
SECTIONS=$(cat "$ROOT/host/prod_sections")
docker run --rm -v "$ROOT":/app -w /app --env-file "$ROOT/.env" python:3.12-slim bash -c \
  "pip install -q -r requirements-runtime.txt >/dev/null && { rc=0; python scores.py --sections $SECTIONS || rc=\$?; python airdates.py --sections $SECTIONS || rc=\$?; exit \$rc; }"
