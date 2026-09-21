#!/bin/bash
# PRODUCTION: one operations-only Kometa run with the live config.yml (mass_*_rating_update etc.).
set -euo pipefail
docker run --rm -v /mnt/user/appdata/Kometa/config:/config kometateam/kometa --config /config/config.yml --run --operations-only --read-only-config
