#!/bin/bash
# Copy scripts, overlay files and the Home collection files to the server over NFS. Creates .env on the server from Kometa's .env if missing.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/../.." && pwd)
APP=/mnt/nastower/appdata/scripts/winswatch
KCFG=/mnt/nastower/appdata/Kometa/config
mkdir -p "$APP/host/jobs" "$APP/cache" "$KCFG/winswatch/collections"
rsync -rlt --delete --exclude .venv --exclude tests --exclude __pycache__ --exclude cache --exclude .env --exclude host/last.log --exclude host/order.log --exclude host/check.log --exclude host/job.sh --exclude host/.request --exclude host/lab_sections \
  "$REPO/scripts/winswatch/" "$APP/"
rsync -rlt --delete --exclude /collections "$REPO/kometa/overlays/winswatch/" "$KCFG/winswatch/"
# Kometa collection files referenced by config.yml (promote_config.py --phase home): the generated Home rotation plus the
# four hand-written row files, flat in config/winswatch/collections/.
HOME_COLLECTIONS=(trending_movies.yml movies_leaving_soon.yml shows_trending.yml shows_leaving_soon.yml)
rsync -rlt --delete "${HOME_COLLECTIONS[@]/#/--exclude=/}" "$REPO/kometa/collections/winswatch/" "$KCFG/winswatch/collections/"
cp "${HOME_COLLECTIONS[@]/#/$REPO/kometa/collections/}" "$KCFG/winswatch/collections/"
chmod +x "$APP"/host/*.sh "$APP"/host/jobs/*.sh
# Overseerr API key lives in overseerr/settings.json; only read it when .env actually needs it (a missing/locked file must not
# fail a routine deploy).
overseerr_key() { python3 -c "import json; print(json.load(open('/mnt/nastower/appdata/overseerr/settings.json'))['main']['apiKey'])"; }
if [ ! -f "$APP/.env" ]; then
  KE="$KCFG/.env"
  v() { grep -m1 "^$1=" "$KE" | cut -d= -f2-; }
  cat > "$APP/.env" <<EOF
PLEX_URL=http://192.168.0.20:32400
PLEX_TOKEN=$(v KOMETA_PlexToken)
MDBLIST_API_KEY=$(v KOMETA_MDBListApiKey)
SONARR_URL=http://192.168.0.30:8989
SONARR_API_KEY=$(v KOMETA_SonarrApiKey)
OVERSEERR_URL=http://192.168.0.6:5055
OVERSEERR_API_KEY=$(overseerr_key)
CACHE_DIR=/app/cache
TZ=America/Chicago
EOF
  chmod 600 "$APP/.env"; echo "created $APP/.env"
elif ! grep -q "^OVERSEERR_URL=" "$APP/.env"; then
  # .env predates the Home work (2026-09-21): append the Overseerr pair once
  printf 'OVERSEERR_URL=http://192.168.0.6:5055\nOVERSEERR_API_KEY=%s\n' "$(overseerr_key)" >> "$APP/.env"
  chmod 600 "$APP/.env"; echo "appended OVERSEERR_* to $APP/.env"
fi
python3 "$REPO/scripts/winswatch/build_lab_config.py" "$KCFG/config.yml" "$KCFG/lab.yml"
echo "deployed to $APP and $KCFG/winswatch; lab.yml written"
