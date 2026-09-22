#!/bin/bash
# Lab Kometa run for collection files only (kometa-lab.sh is overlays-only). TZ pinned so weekly()/range() schedules
# resolve on the same calendar day as home.py (a bare docker run is UTC — 5 h ahead of America/Chicago).
set -euo pipefail
docker run --rm -e TZ=America/Chicago -v /mnt/user/appdata/Kometa/config:/config kometateam/kometa --config /config/lab.yml --run --collections-only --read-only-config
