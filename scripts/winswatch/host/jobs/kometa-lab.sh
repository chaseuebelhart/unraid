#!/bin/bash
set -euo pipefail
docker run --rm -v /mnt/user/appdata/Kometa/config:/config kometateam/kometa --config /config/lab.yml --run --overlays-only --read-only-config
