#!/bin/bash
# Strip lab overlays (restores Kometa's backed-up originals for the lab libraries only).
set -euo pipefail
sed 's/remove_overlays: false/remove_overlays: true/' /mnt/user/appdata/Kometa/config/lab.yml > /mnt/user/appdata/Kometa/config/lab-remove.yml
docker run --rm -v /mnt/user/appdata/Kometa/config:/config kometateam/kometa --config /config/lab-remove.yml --run --overlays-only --read-only-config
