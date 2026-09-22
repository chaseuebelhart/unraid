#!/bin/bash
# HEALTH CHECK (hostexec.py run check; also the last step of nightly.sh): read-only post-condition check of everything
# the nightly writes — DaysLeft labels vs Maintainerr, air-date labels vs Sonarr, score coverage, REQUESTED labels, the
# Home row set/order, the per-user rows and the collection cards (home.py check -> ww/health.py). Exits non-zero on any
# FAIL. Output is kept in host/check.log as well as host/last.log.
set -euo pipefail
ROOT=/mnt/user/appdata/scripts/winswatch
SECTIONS=$(cat "$ROOT/host/prod_sections")
exec > >(tee "$ROOT/host/check.log") 2>&1
docker run --rm -v "$ROOT":/app/scripts/winswatch -v "$ROOT/cache":/app/cache -w /app/scripts/winswatch --env-file "$ROOT/.env" python:3.12-slim bash -c \
  "pip install -q -r requirements-runtime.txt >/dev/null && python home.py check --sections $SECTIONS"
