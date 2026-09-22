#!/bin/bash
# PRODUCTION: one operations-only Kometa run with the live config.yml (mass_*_rating_update, delete_collections: managed etc.). TZ pinned (see kometa-prod-collections.sh).
set -euo pipefail
docker run --rm -e TZ=America/Chicago -v /mnt/user/appdata/Kometa/config:/config kometateam/kometa --config /config/config.yml --run --operations-only --read-only-config
