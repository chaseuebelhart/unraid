#!/bin/bash
# READ-ONLY: Appdata.Backup plugin config + what it excludes, and the size of Plex's regenerable dirs.
set -uo pipefail
for f in /boot/config/plugins/appdata.backup/config.json /boot/config/plugins/appdata.backup/*.cfg /boot/config/plugins/appdata.backup/*.json; do
  [ -f "$f" ] && { echo "=== $f ==="; cat "$f"; echo; }
done
echo "=== Plex appdata sizes ==="
P="/mnt/user/appdata/Plex-Media-Server/Library/Application Support/Plex Media Server"
du -sh "$P" 2>/dev/null
for d in Media Metadata Cache "Plug-in Support"; do du -sh "$P/$d" 2>/dev/null; done
echo "=== backups share ==="; du -sh /mnt/user/backups 2>/dev/null; ls -1 /mnt/user/backups 2>/dev/null | tail -5
