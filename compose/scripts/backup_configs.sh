#!/usr/bin/env bash
# =============================================================================
# Home Lab Backup Script
# =============================================================================
# This script backs up application configuration folders without stopping
# containers. It creates a timestamped tarball of the appdata directory.
#
# For SQLite databases, this performs a hot backup which may not be fully
# consistent. For critical data, consider stopping containers or using
# proper database backup tools.
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default configuration
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
KEEP_BACKUPS=${KEEP_BACKUPS:-5}

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# -----------------------------------------------------------------------------
# Determine Environment
# -----------------------------------------------------------------------------

detect_environment() {
    if [[ -f "$PROJECT_ROOT/.env.local" ]] && [[ -f "$PROJECT_ROOT/.env.unraid" ]]; then
        # Try to detect which environment we're in
        if [[ -d "/mnt/user" ]]; then
            ENV_FILE="$PROJECT_ROOT/.env.unraid"
            log_info "Detected Unraid environment"
        else
            ENV_FILE="$PROJECT_ROOT/.env.local"
            log_info "Detected local environment"
        fi
    elif [[ -f "$PROJECT_ROOT/.env.local" ]]; then
        ENV_FILE="$PROJECT_ROOT/.env.local"
    elif [[ -f "$PROJECT_ROOT/.env.unraid" ]]; then
        ENV_FILE="$PROJECT_ROOT/.env.unraid"
    else
        log_error "No environment file found"
        exit 1
    fi
    
    # Source the environment file to get APPDATA_ROOT
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    
    # Resolve relative paths
    if [[ ! "$APPDATA_ROOT" = /* ]]; then
        APPDATA_ROOT="$PROJECT_ROOT/$APPDATA_ROOT"
    fi
    
    log_info "APPDATA_ROOT: $APPDATA_ROOT"
}

# -----------------------------------------------------------------------------
# Create Backup Directory
# -----------------------------------------------------------------------------

setup_backup_dir() {
    mkdir -p "$BACKUP_DIR"
    log_info "Backup directory: $BACKUP_DIR"
}

# -----------------------------------------------------------------------------
# Backup Application Configs
# -----------------------------------------------------------------------------

backup_app_configs() {
    local backup_name="homelab_appdata_${TIMESTAMP}.tar.gz"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    log_info "Starting backup of application configs..."
    log_warn "This is a hot backup - containers remain running"
    
    if [[ ! -d "$APPDATA_ROOT" ]]; then
        log_error "APPDATA_ROOT does not exist: $APPDATA_ROOT"
        exit 1
    fi
    
    # List directories to backup
    log_info "Backing up directories in $APPDATA_ROOT:"
    local total_size
    total_size=$(du -sh "$APPDATA_ROOT" 2>/dev/null | cut -f1)
    log_info "Total size: $total_size"
    
    # Create the backup
    log_info "Creating tarball: $backup_name"
    
    if tar -czf "$backup_path" -C "$(dirname "$APPDATA_ROOT")" "$(basename "$APPDATA_ROOT")" 2>/dev/null; then
        local backup_size
        backup_size=$(du -h "$backup_path" | cut -f1)
        log_success "Backup created: $backup_path ($backup_size)"
    else
        log_error "Failed to create backup"
        exit 1
    fi
}

# -----------------------------------------------------------------------------
# Backup Individual SQLite Databases
# -----------------------------------------------------------------------------

backup_sqlite_databases() {
    log_info "Backing up SQLite databases..."
    
    local db_backup_dir="$BACKUP_DIR/sqlite_${TIMESTAMP}"
    mkdir -p "$db_backup_dir"
    
    # List of apps with SQLite databases
    local sqlite_apps=(
        "sonarr:sonarr.db"
        "radarr:radarr.db"
        "prowlarr:prowlarr.db"
        "tautulli:tautulli.db"
        "overseerr:db/db.sqlite3"
    )
    
    for app_db in "${sqlite_apps[@]}"; do
        local app="${app_db%%:*}"
        local db_file="${app_db##*:}"
        local db_path="$APPDATA_ROOT/$app/$db_file"
        
        if [[ -f "$db_path" ]]; then
            local dest="$db_backup_dir/${app}_$(basename "$db_file")"
            
            # Use sqlite3 to create a consistent backup if available
            if command -v sqlite3 &>/dev/null; then
                if sqlite3 "$db_path" ".backup '$dest'" 2>/dev/null; then
                    log_success "SQLite backup: $app -> $(basename "$dest")"
                else
                    # Fallback to copy
                    cp "$db_path" "$dest"
                    log_warn "File copy backup: $app (sqlite3 backup failed)"
                fi
            else
                # Fallback to copy
                cp "$db_path" "$dest"
                log_warn "File copy backup: $app (sqlite3 not installed)"
            fi
        else
            log_info "Database not found: $app ($db_path)"
        fi
    done
    
    # Compress SQLite backups
    if [[ "$(ls -A "$db_backup_dir" 2>/dev/null)" ]]; then
        tar -czf "$BACKUP_DIR/sqlite_${TIMESTAMP}.tar.gz" -C "$BACKUP_DIR" "sqlite_${TIMESTAMP}"
        rm -rf "$db_backup_dir"
        log_success "SQLite backups compressed: sqlite_${TIMESTAMP}.tar.gz"
    fi
}

# -----------------------------------------------------------------------------
# Backup Traefik Config
# -----------------------------------------------------------------------------

backup_traefik_config() {
    log_info "Backing up Traefik configuration..."
    
    local traefik_backup="$BACKUP_DIR/traefik_config_${TIMESTAMP}.tar.gz"
    
    if [[ -d "$PROJECT_ROOT/traefik" ]]; then
        tar -czf "$traefik_backup" -C "$PROJECT_ROOT" "traefik"
        log_success "Traefik config backup: traefik_config_${TIMESTAMP}.tar.gz"
    else
        log_warn "Traefik config directory not found"
    fi
}

# -----------------------------------------------------------------------------
# Cleanup Old Backups
# -----------------------------------------------------------------------------

cleanup_old_backups() {
    log_info "Cleaning up old backups (keeping last $KEEP_BACKUPS)..."
    
    # Cleanup appdata backups
    local count
    count=$(find "$BACKUP_DIR" -name "homelab_appdata_*.tar.gz" -type f 2>/dev/null | wc -l)
    
    if [[ "$count" -gt "$KEEP_BACKUPS" ]]; then
        local to_delete=$((count - KEEP_BACKUPS))
        find "$BACKUP_DIR" -name "homelab_appdata_*.tar.gz" -type f -printf '%T+ %p\n' 2>/dev/null | \
            sort | head -n "$to_delete" | cut -d' ' -f2- | \
            while read -r file; do
                rm -f "$file"
                log_info "Deleted old backup: $(basename "$file")"
            done
    fi
    
    # Cleanup SQLite backups
    count=$(find "$BACKUP_DIR" -name "sqlite_*.tar.gz" -type f 2>/dev/null | wc -l)
    
    if [[ "$count" -gt "$KEEP_BACKUPS" ]]; then
        local to_delete=$((count - KEEP_BACKUPS))
        find "$BACKUP_DIR" -name "sqlite_*.tar.gz" -type f -printf '%T+ %p\n' 2>/dev/null | \
            sort | head -n "$to_delete" | cut -d' ' -f2- | \
            while read -r file; do
                rm -f "$file"
                log_info "Deleted old SQLite backup: $(basename "$file")"
            done
    fi
}

# -----------------------------------------------------------------------------
# List Backups
# -----------------------------------------------------------------------------

list_backups() {
    echo ""
    log_info "Available backups in $BACKUP_DIR:"
    echo ""
    
    if [[ -d "$BACKUP_DIR" ]]; then
        ls -lh "$BACKUP_DIR"/*.tar.gz 2>/dev/null || echo "  No backups found"
    else
        echo "  Backup directory does not exist"
    fi
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

main() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║           Home Lab Backup Script                               ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    local action="${1:-backup}"
    
    case "$action" in
        backup)
            detect_environment
            setup_backup_dir
            backup_app_configs
            backup_sqlite_databases
            backup_traefik_config
            cleanup_old_backups
            list_backups
            echo ""
            log_success "Backup completed successfully!"
            ;;
        list)
            setup_backup_dir
            list_backups
            ;;
        *)
            echo "Usage: $0 [backup|list]"
            echo ""
            echo "Commands:"
            echo "  backup  Create a new backup (default)"
            echo "  list    List existing backups"
            echo ""
            echo "Environment Variables:"
            echo "  BACKUP_DIR    Backup destination directory (default: ./backups)"
            echo "  KEEP_BACKUPS  Number of backups to keep (default: 5)"
            exit 1
            ;;
    esac
}

main "$@"
