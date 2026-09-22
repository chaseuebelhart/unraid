#!/usr/bin/env bash
#
# destroy.sh - Clean up local homelab environment for fresh testing
# Usage: ./scripts/destroy.sh [--volumes] [--force]
#
# Options:
#   --volumes   Also remove Docker volumes
#   --force     Skip confirmation prompts
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

# Parse arguments
REMOVE_VOLUMES=false
FORCE=false

for arg in "$@"; do
    case $arg in
        --volumes)
            REMOVE_VOLUMES=true
            ;;
        --force)
            FORCE=true
            ;;
        *)
            echo -e "${RED}Unknown option: $arg${NC}"
            echo "Usage: $0 [--volumes] [--force]"
            exit 1
            ;;
    esac
done

echo -e "${YELLOW}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║           LOCAL ENVIRONMENT DESTROY SCRIPT                 ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Safety check - only run from project root
if [[ ! -f "$PROJECT_ROOT/compose.yml" ]]; then
    echo -e "${RED}Error: compose.yml not found. Run from project root.${NC}"
    exit 1
fi

cd "$PROJECT_ROOT"

# Confirmation
if [[ "$FORCE" != "true" ]]; then
    echo -e "${RED}WARNING: This will destroy your local homelab environment!${NC}"
    echo ""
    echo "This script will:"
    echo "  • Stop and remove all containers"
    echo "  • Remove all container images (optional)"
    echo "  • Delete ./build/appdata/* (all application data)"
    echo "  • Delete ./build/data/* (downloads, media placeholders)"
    if [[ "$REMOVE_VOLUMES" == "true" ]]; then
        echo -e "  • ${RED}Remove Docker volumes${NC}"
    fi
    echo ""
    read -p "Are you sure you want to continue? [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 0
    fi
fi

echo ""
echo -e "${YELLOW}[1/4] Stopping and removing containers...${NC}"

# Use sudo for docker commands
DOCKER_CMD="sudo docker"

# Full compose command with env files
COMPOSE_CMD="$DOCKER_CMD compose --env-file .env.common --env-file .env.local --env-file .env.secrets -f compose.yml -f compose.local.yml"

# Stop containers using local compose files
if $COMPOSE_CMD ps -q 2>/dev/null | grep -q .; then
    $COMPOSE_CMD down --remove-orphans || true
else
    echo "  No running containers found."
fi

echo ""
echo -e "${YELLOW}[2/4] Removing Docker volumes (if requested)...${NC}"

if [[ "$REMOVE_VOLUMES" == "true" ]]; then
    # Get project name (defaults to directory name)
    PROJECT_NAME=$(basename "$PROJECT_ROOT" | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]_-')
    
    # List and remove project volumes
    VOLUMES=$($DOCKER_CMD volume ls -q --filter "name=${PROJECT_NAME}" 2>/dev/null || true)
    if [[ -n "$VOLUMES" ]]; then
        echo "$VOLUMES" | xargs -r $DOCKER_CMD volume rm || true
        echo "  Removed project volumes."
    else
        echo "  No project volumes found."
    fi
else
    echo "  Skipped (use --volumes to remove)."
fi

echo ""
echo -e "${YELLOW}[3/4] Removing application data (./build/appdata/*)...${NC}"

APPDATA_DIR="$PROJECT_ROOT/build/appdata"
if [[ -d "$APPDATA_DIR" ]]; then
    # List what we're about to remove
    DIRS_TO_REMOVE=$(find "$APPDATA_DIR" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
    echo "  Found $DIRS_TO_REMOVE application directories."
    
    # Need sudo because some dirs have special ownership (grafana=472, etc.)
    if [[ $DIRS_TO_REMOVE -gt 0 ]]; then
        sudo rm -rf "$APPDATA_DIR"/*
        echo "  Removed all application data."
    fi
else
    echo "  Directory does not exist, skipping."
fi

echo ""
echo -e "${YELLOW}[4/4] Removing data directories (./build/data/*)...${NC}"

DATA_DIR="$PROJECT_ROOT/build/data"
if [[ -d "$DATA_DIR" ]]; then
    DIRS_TO_REMOVE=$(find "$DATA_DIR" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
    echo "  Found $DIRS_TO_REMOVE data directories."
    
    if [[ $DIRS_TO_REMOVE -gt 0 ]]; then
        sudo rm -rf "$DATA_DIR"/*
        echo "  Removed all data directories."
    fi
else
    echo "  Directory does not exist, skipping."
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    CLEANUP COMPLETE                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "To start fresh, run:"
echo "  1. ./scripts/init.sh local"
echo "  2. docker compose --env-file .env.common --env-file .env.local --env-file .env.secrets -f compose.yml -f compose.local.yml up -d"
echo ""
