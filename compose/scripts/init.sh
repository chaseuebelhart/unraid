#!/usr/bin/env bash
# =============================================================================
# Home Lab Initialization Script
# =============================================================================
# Run this script ONCE before starting the stack for the first time.
# It creates required directories with proper permissions.
#
# Usage: ./scripts/init.sh [local|unraid]
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

# -----------------------------------------------------------------------------
# Determine environment
# -----------------------------------------------------------------------------
ENV="${1:-local}"

if [[ "$ENV" == "local" ]]; then
    source "$PROJECT_ROOT/.env.common"
    source "$PROJECT_ROOT/.env.local"
    log_info "Initializing for LOCAL environment"
elif [[ "$ENV" == "unraid" ]]; then
    source "$PROJECT_ROOT/.env.common"
    source "$PROJECT_ROOT/.env.unraid"
    log_info "Initializing for UNRAID environment"
else
    log_error "Unknown environment: $ENV"
    echo "Usage: $0 [local|unraid]"
    exit 1
fi

# Resolve relative paths
if [[ ! "$DATA_ROOT" = /* ]]; then
    DATA_ROOT="$PROJECT_ROOT/$DATA_ROOT"
fi
if [[ ! "$APPDATA_ROOT" = /* ]]; then
    APPDATA_ROOT="$PROJECT_ROOT/$APPDATA_ROOT"
fi

log_info "DATA_ROOT: $DATA_ROOT"
log_info "APPDATA_ROOT: $APPDATA_ROOT"

# -----------------------------------------------------------------------------
# Create directories
# -----------------------------------------------------------------------------
log_info "Creating appdata directories..."

APPDATA_DIRS=(
    "gluetun"
    "grafana"
    "govee2mqtt"
    "homeassistant"
    "influxdb"
    "kometa"
    "maintainerr"
    "mosquitto/data"
    "mosquitto/log"
    "notifiarr"
    "overseerr"
    "plex"
    "plex/transcode"
    "prowlarr"
    "qbittorrent"
    "radarr"
    "sonarr"
    "stash/config"
    "stash/generated"
    "stash/metadata"
    "stash/cache"
    "tautulli"
    "traefik/acme"
)

for dir in "${APPDATA_DIRS[@]}"; do
    mkdir -p "$APPDATA_ROOT/$dir"
done
log_success "Created appdata directories"

# -----------------------------------------------------------------------------
# Create data directories
# -----------------------------------------------------------------------------
log_info "Creating data directories..."

DATA_DIRS=(
    "downloads"
    "media"
    "stash"
)

for dir in "${DATA_DIRS[@]}"; do
    mkdir -p "$DATA_ROOT/$dir"
done
log_success "Created data directories"

# -----------------------------------------------------------------------------
# Set permissions
# -----------------------------------------------------------------------------
log_info "Setting directory permissions..."

# Default ownership (PUID:PGID from env)
PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

# Most directories use PUID:PGID
chown -R "$PUID:$PGID" "$APPDATA_ROOT" 2>/dev/null || sudo chown -R "$PUID:$PGID" "$APPDATA_ROOT"
chown -R "$PUID:$PGID" "$DATA_ROOT" 2>/dev/null || sudo chown -R "$PUID:$PGID" "$DATA_ROOT"

# Grafana runs as UID 472
chown -R 472:472 "$APPDATA_ROOT/grafana" 2>/dev/null || sudo chown -R 472:472 "$APPDATA_ROOT/grafana"

# InfluxDB runs as UID 1000 but needs write access
chmod 755 "$APPDATA_ROOT/influxdb" 2>/dev/null || sudo chmod 755 "$APPDATA_ROOT/influxdb"

# Mosquitto needs specific permissions
chmod 755 "$APPDATA_ROOT/mosquitto" 2>/dev/null || sudo chmod 755 "$APPDATA_ROOT/mosquitto"
chmod 755 "$APPDATA_ROOT/mosquitto/data" 2>/dev/null || sudo chmod 755 "$APPDATA_ROOT/mosquitto/data"
chmod 755 "$APPDATA_ROOT/mosquitto/log" 2>/dev/null || sudo chmod 755 "$APPDATA_ROOT/mosquitto/log"

log_success "Set directory permissions"

# -----------------------------------------------------------------------------
# Create placeholder configs
# -----------------------------------------------------------------------------
log_info "Creating placeholder config files..."

# Kometa config
if [[ ! -f "$APPDATA_ROOT/kometa/config.yml" ]]; then
    cat > "$APPDATA_ROOT/kometa/config.yml" << 'EOF'
## Kometa Configuration File
## See kometa/README.md for full documentation

libraries:
  Movies:
    collection_files:
      - pmm: basic
    # overlay_files:
    #   - pmm: resolution

settings:
  cache: true
  cache_expiration: 60

plex:
  url: http://plex:32400
  token: YOUR_PLEX_TOKEN  # Get from plex.tv/claim or existing Plex setup

# tmdb:
#   apikey: YOUR_TMDB_API_KEY
#   language: en
EOF
    log_success "Created kometa/config.yml placeholder"
else
    log_info "kometa/config.yml already exists, skipping"
fi

# -----------------------------------------------------------------------------
# Generate basic auth credentials
# -----------------------------------------------------------------------------
log_info "Checking basic auth setup..."

USERS_FILE="$PROJECT_ROOT/traefik/dynamic/users.txt"
if grep -q "PLACEHOLDER" "$USERS_FILE" 2>/dev/null; then
    log_warn "Basic auth credentials need to be set!"
    echo ""
    echo "  Generate a password hash with:"
    echo "    htpasswd -nB admin"
    echo ""
    echo "  Then update: traefik/dynamic/users.txt"
    echo ""
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Initialization Complete!                             ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Set up basic auth (if not done):"
echo "   htpasswd -nB admin > traefik/dynamic/users.txt"
echo ""
echo "2. Review and fill in secrets:"
echo "   nano .env.secrets"
echo ""
echo "3. Start the stack:"
if [[ "$ENV" == "local" ]]; then
    echo "   docker compose --env-file .env.common --env-file .env.local --env-file .env.secrets -f compose.yml -f compose.local.yml up -d"
else
    echo "   docker compose --env-file .env.common --env-file .env.unraid --env-file .env.secrets -f compose.yml -f compose.unraid.yml up -d"
fi
echo ""
echo "4. Access services at:"
echo "   http://sonarr.${BASE_DOMAIN}"
echo "   http://radarr.${BASE_DOMAIN}"
echo "   http://plex.${BASE_DOMAIN}"
echo "   etc."
echo ""
