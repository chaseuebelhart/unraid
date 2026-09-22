#!/bin/bash
# NIGHTLY (scheduled by the Unraid user script "winswatch" at 04:30 server clock, before Kometa's 05:00 run):
# 1. scores.py: MDBList score -> user-rating slot (metadata edit; Kometa's mdb writer goes via /:/rate and gets rounded by plex.tv)
# 2. airdates.py: NewEp_/ReturnsIn_/Returns_ labels from Sonarr.   DaysLeft_ labels come from the update_days_left script.
# 3. home.py requested: `Requested` labels (Kometa's REQUESTED badge) from Overseerr
# 4. home.py rows: per-user "📥 New · Your Requests" collections + plex.tv share filters (merge); exits non-zero on any !! line
# 5. home.py cards: card posters for the Home rows we own (Shortlist / Maintainerr / per-user rows)
# Hub ORDER is not here: Kometa (05:00) re-promotes its rows and appends new ones at the end, so home.py order runs from
# the "winswatch-order" user script at :50 of every server hour from 05 to 21 (host/jobs/order.sh).
# Mounts mirror the repo layout (scripts/winswatch + kometa/overlays/winswatch) because gen_cards/gen_home resolve the
# card and font files relative to __file__ (parents[2]/kometa/...); the cards dir is the deployed Kometa copy.
set -euo pipefail
ROOT=/mnt/user/appdata/scripts/winswatch
KCFG=/mnt/user/appdata/Kometa/config
SECTIONS=$(cat "$ROOT/host/prod_sections")
docker run --rm -v "$ROOT":/app/scripts/winswatch -v "$KCFG/winswatch":/app/kometa/overlays/winswatch:ro -v "$ROOT/cache":/app/cache \
  -w /app/scripts/winswatch --env-file "$ROOT/.env" python:3.12-slim bash -c \
  "pip install -q -r requirements-runtime.txt >/dev/null && { rc=0; \
   python scores.py --sections $SECTIONS || rc=\$?; \
   python airdates.py --sections $SECTIONS || rc=\$?; \
   python home.py requested --sections $SECTIONS || rc=\$?; \
   python home.py rows --sections $SECTIONS || rc=\$?; \
   python home.py cards --sections $SECTIONS || rc=\$?; \
   exit \$rc; }"
