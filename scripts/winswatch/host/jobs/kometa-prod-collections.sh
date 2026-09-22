#!/bin/bash
# PRODUCTION: one collections-only Kometa run with the live config.yml (what the 05:00 schedule does for collections).
# TZ pinned: a bare docker run is UTC, and Kometa's weekly()/range() schedules would flip a day early after 19:00 Chicago.
set -euo pipefail
docker run --rm -e TZ=America/Chicago -v /mnt/user/appdata/Kometa/config:/config kometateam/kometa --config /config/config.yml --run --collections-only --read-only-config
