#!/bin/bash
# READ-ONLY: size of Plex's regenerable appdata dirs (run on the host — du over NFS is far too slow).
set -uo pipefail
P="/mnt/user/appdata/Plex-Media-Server/Library/Application Support/Plex Media Server"
du -sh "$P" 2>/dev/null
for d in Media Metadata Cache "Plug-in Support"; do du -sh "$P/$d" 2>/dev/null; done
find "$P/Media" -name "*.bif" 2>/dev/null | wc -l | xargs echo "bif files:"
df -h /mnt/cache 2>/dev/null | tail -1
