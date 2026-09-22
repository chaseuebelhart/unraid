#!/bin/bash
# DAYS LEFT (hostexec.py run days-left). Wrapper around Chase's Maintainerr DaysLeft labeler
# (/mnt/user/appdata/scripts/maintainerr) — it has its own ~04:40 schedule; this exists only so the labeler can be
# triggered ad hoc, e.g. after a `home.py check` FAIL on the days-left line.
set -euo pipefail
bash /mnt/user/appdata/scripts/maintainerr/shscripts/run_days_left.sh /mnt/user/appdata/scripts/maintainerr
