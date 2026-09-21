#!/bin/bash
# PRODUCTION: one overlays-only Kometa run with the live config.yml (what the 05:00 schedule does for overlays).
set -euo pipefail
docker run --rm -v /mnt/user/appdata/Kometa/config:/config kometateam/kometa --config /config/config.yml --run --overlays-only --read-only-config
