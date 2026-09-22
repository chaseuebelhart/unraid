#!/bin/bash
# ONE-OFF: remove the lab media symlink tree after the lab Plex libraries (sections 4/5) have been deleted.
set -euo pipefail
D=/mnt/user/data/media/_winswatch-lab
[ -d "$D" ] || { echo "already gone: $D"; exit 0; }
echo "contents (symlinks only — real media is untouched):"; find "$D" -maxdepth 2 | head -20
n=$(find "$D" -type l | wc -l); r=$(find "$D" -type f ! -type l | wc -l)
echo "symlinks: $n | real files: $r"
[ "$r" -eq 0 ] || { echo "REFUSING: real files present, not a pure symlink tree"; exit 1; }
rm -rf "$D" && echo "removed $D"
