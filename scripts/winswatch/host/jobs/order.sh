#!/bin/bash
# HUB ORDER (scheduled by the Unraid user script "winswatch-order" at 05:45 server clock, after Kometa's 05:00 run has
# promoted today's theme rows): sort each library's Home hubs into the design §1 order and demote everything else
# (home.py order -> ww/plexhome.py). Also runnable ad hoc: hostexec.py run order. Output is kept in host/order.log.
set -euo pipefail
ROOT=/mnt/user/appdata/scripts/winswatch
SECTIONS=$(cat "$ROOT/host/prod_sections")
exec > >(tee "$ROOT/host/order.log") 2>&1
docker run --rm -v "$ROOT":/app/scripts/winswatch -w /app/scripts/winswatch --env-file "$ROOT/.env" python:3.12-slim bash -c \
  "pip install -q -r requirements-runtime.txt >/dev/null && python home.py order --sections $SECTIONS"
