#!/bin/bash
# LAB ONLY (hostexec run labels). Run scores.py + airdates.py against the lab sections in a throwaway python container.
set -euo pipefail
ROOT=/mnt/user/appdata/scripts/winswatch
SECTIONS=$(cat "$ROOT/host/lab_sections")        # e.g. "10,11" written by create_lab_libraries.py
docker run --rm -v "$ROOT":/app -w /app --env-file "$ROOT/.env" python:3.12-slim bash -c \
  "pip install -q -r requirements.txt >/dev/null && { rc=0; python scores.py --sections $SECTIONS || rc=\$?; python airdates.py --sections $SECTIONS || rc=\$?; exit \$rc; }"
