#!/bin/bash
# Called by the Unraid user script "winswatch". Runs whatever host/job.sh currently is.
set -uo pipefail
ROOT=/mnt/user/appdata/scripts/winswatch
LOG=$ROOT/host/last.log
{
  echo "=== $(date -Is) job.sh ==="
  cat "$ROOT/host/job.sh"
  echo "=== output ==="
  bash "$ROOT/host/job.sh"
  echo "=== exit $? ==="
} > "$LOG" 2>&1
cat "$LOG"
