#!/bin/bash
# Entry point of the Unraid user script "winswatch".
#   * scheduled run (no request pending)  -> host/jobs/nightly.sh  (fixed, committed)
#   * hostexec.py run <job>               -> writes host/job.sh + host/.request, then triggers this script
set -uo pipefail
ROOT=/mnt/user/appdata/scripts/winswatch
LOG=$ROOT/host/last.log
if [ -f "$ROOT/host/.request" ]; then
  rm -f "$ROOT/host/.request"; JOB=$ROOT/host/job.sh
else
  JOB=$ROOT/host/jobs/nightly.sh
fi
{
  echo "=== $(date -Is) $JOB ==="
  cat "$JOB"
  echo "=== output ==="
  bash "$JOB"
  echo "=== exit $? ==="
} > "$LOG" 2>&1
cat "$LOG"
