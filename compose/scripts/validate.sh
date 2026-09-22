#!/usr/bin/env bash
# =============================================================================
# Home Lab Configuration Validation Script
# =============================================================================
# This script validates the Docker Compose configuration and verifies that
# Traefik routing matches the expected NPM proxy host list.
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

# Counters
PASS=0
FAIL=0
WARN=0

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

log_pass() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
    ((PASS++))
}

log_fail() {
    echo -e "${RED}✗ FAIL:${NC} $1"
    ((FAIL++))
}

log_warn() {
    echo -e "${YELLOW}⚠ WARN:${NC} $1"
    ((WARN++))
}

log_info() {
    echo -e "${BLUE}ℹ INFO:${NC} $1"
}

log_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# -----------------------------------------------------------------------------
# Check Prerequisites
# -----------------------------------------------------------------------------

check_prerequisites() {
    log_section "Checking Prerequisites"
    
    if ! command -v docker &> /dev/null; then
        log_fail "Docker is not installed"
        exit 1
    fi
    log_pass "Docker is installed"
    
    if ! docker compose version &> /dev/null; then
        log_fail "Docker Compose V2 is not available"
        exit 1
    fi
    log_pass "Docker Compose V2 is available"
    
    # Check for required files
    local required_files=(
        "compose.yml"
        "compose.local.yml"
        "compose.unraid.yml"
        ".env.common"
        ".env.local"
        ".env.unraid"
        ".env.secrets"
        "traefik/traefik.yml"
        "traefik/dynamic/middlewares.yml"
    )
    
    for file in "${required_files[@]}"; do
        if [[ -f "$PROJECT_ROOT/$file" ]]; then
            log_pass "Found: $file"
        else
            log_fail "Missing: $file"
        fi
    done
}

# -----------------------------------------------------------------------------
# Validate Compose Configuration
# -----------------------------------------------------------------------------

validate_compose_config() {
    log_section "Validating Docker Compose Configuration"
    
    cd "$PROJECT_ROOT"
    
    # Validate LOCAL configuration
    log_info "Validating LOCAL environment..."
    if docker compose \
        --env-file .env.common \
        --env-file .env.local \
        --env-file .env.secrets \
        -f compose.yml \
        -f compose.local.yml \
        config > /dev/null 2>&1; then
        log_pass "LOCAL compose configuration is valid"
        LOCAL_CONFIG_VALID=true
    else
        log_fail "LOCAL compose configuration has errors"
        docker compose \
            --env-file .env.common \
            --env-file .env.local \
            --env-file .env.secrets \
            -f compose.yml \
            -f compose.local.yml \
            config 2>&1 | head -20
        LOCAL_CONFIG_VALID=false
    fi
    
    # Validate UNRAID configuration
    log_info "Validating UNRAID environment..."
    if docker compose \
        --env-file .env.common \
        --env-file .env.unraid \
        --env-file .env.secrets \
        -f compose.yml \
        -f compose.unraid.yml \
        config > /dev/null 2>&1; then
        log_pass "UNRAID compose configuration is valid"
        UNRAID_CONFIG_VALID=true
    else
        log_fail "UNRAID compose configuration has errors"
        docker compose \
            --env-file .env.common \
            --env-file .env.unraid \
            --env-file .env.secrets \
            -f compose.yml \
            -f compose.unraid.yml \
            config 2>&1 | head -20
        UNRAID_CONFIG_VALID=false
    fi
}

# -----------------------------------------------------------------------------
# Verify Traefik Routers
# -----------------------------------------------------------------------------

verify_traefik_routers() {
    log_section "Verifying Traefik Routers"
    
    # Expected services that need Traefik routers
    local expected_services=(
        "sonarr"
        "radarr"
        "prowlarr"
        "qb"
        "maintainerr"
        "notifiarr"
        "overseerr"
        "plex"
        "tautulli"
        "stash"
    )
    
    cd "$PROJECT_ROOT"
    
    # Check LOCAL config
    log_info "Checking LOCAL Traefik routers (*.local.lan)..."
    local local_config
    local_config=$(docker compose \
        --env-file .env.common \
        --env-file .env.local \
        --env-file .env.secrets \
        -f compose.yml \
        -f compose.local.yml \
        config 2>/dev/null)
    
    for service in "${expected_services[@]}"; do
        if echo "$local_config" | grep -q "Host(\`${service}.local.lan\`)"; then
            log_pass "LOCAL router found: ${service}.local.lan"
        else
            log_fail "LOCAL router missing: ${service}.local.lan"
        fi
    done
    
    # Check UNRAID config
    log_info "Checking UNRAID Traefik routers (*.lan)..."
    local unraid_config
    unraid_config=$(docker compose \
        --env-file .env.common \
        --env-file .env.unraid \
        --env-file .env.secrets \
        -f compose.yml \
        -f compose.unraid.yml \
        config 2>/dev/null)
    
    for service in "${expected_services[@]}"; do
        if echo "$unraid_config" | grep -q "Host(\`${service}.lan\`)"; then
            log_pass "UNRAID router found: ${service}.lan"
        else
            log_fail "UNRAID router missing: ${service}.lan"
        fi
    done
}

# -----------------------------------------------------------------------------
# Verify qBittorrent Routes Through Gluetun
# -----------------------------------------------------------------------------

verify_qbittorrent_routing() {
    log_section "Verifying qBittorrent VPN Routing"
    
    cd "$PROJECT_ROOT"
    
    local config
    config=$(docker compose \
        --env-file .env.common \
        --env-file .env.local \
        --env-file .env.secrets \
        -f compose.yml \
        -f compose.local.yml \
        config 2>/dev/null)
    
    # Check that qbittorrent uses gluetun network_mode
    if echo "$config" | grep -A 50 "qbittorrent:" | grep -q 'network_mode:.*service:gluetun'; then
        log_pass "qBittorrent uses gluetun network namespace"
    else
        log_fail "qBittorrent does NOT use gluetun network namespace"
    fi
    
    # Check that gluetun has traefik labels for qbittorrent
    if echo "$config" | grep -A 100 "gluetun:" | grep -q "traefik.http.routers.qbittorrent"; then
        log_pass "Traefik routes qb.* to gluetun container"
    else
        log_fail "Traefik qbittorrent router not found on gluetun"
    fi
    
    # Check that qbittorrent service port is 8080 on gluetun
    if echo "$config" | grep -A 100 "gluetun:" | grep -q "loadbalancer.server.port=8080"; then
        log_pass "qBittorrent service points to port 8080"
    else
        log_fail "qBittorrent service port configuration not found"
    fi
}

# -----------------------------------------------------------------------------
# Verify Arr Apps NOT Behind VPN
# -----------------------------------------------------------------------------

verify_arr_not_vpn() {
    log_section "Verifying Arr Apps NOT Behind VPN"
    
    cd "$PROJECT_ROOT"
    
    local config
    config=$(docker compose \
        --env-file .env.common \
        --env-file .env.local \
        --env-file .env.secrets \
        -f compose.yml \
        -f compose.local.yml \
        config 2>/dev/null)
    
    local arr_services=("sonarr" "radarr" "prowlarr")
    
    for service in "${arr_services[@]}"; do
        # Extract service config and check for network_mode
        local service_config
        service_config=$(echo "$config" | sed -n "/^  ${service}:/,/^  [a-z]/p" | head -n -1)
        
        if echo "$service_config" | grep -q "network_mode"; then
            log_fail "$service has network_mode set (should NOT be behind VPN)"
        else
            log_pass "$service does NOT use network_mode (correct - not behind VPN)"
        fi
        
        # Check that they have their own network connections
        if echo "$service_config" | grep -q "networks:"; then
            log_pass "$service has its own network configuration"
        else
            log_warn "$service may not have explicit network configuration"
        fi
    done
}

# -----------------------------------------------------------------------------
# Verify Unpackerr Uses Service DNS
# -----------------------------------------------------------------------------

verify_unpackerr_urls() {
    log_section "Verifying Unpackerr Uses Service DNS"
    
    cd "$PROJECT_ROOT"
    
    local config
    config=$(docker compose \
        --env-file .env.common \
        --env-file .env.local \
        --env-file .env.secrets \
        -f compose.yml \
        -f compose.local.yml \
        config 2>/dev/null)
    
    # Check Sonarr URL
    if echo "$config" | grep -q "UN_SONARR_0_URL=http://sonarr:"; then
        log_pass "Unpackerr uses service DNS for Sonarr (http://sonarr:...)"
    elif echo "$config" | grep "UN_SONARR_0_URL" | grep -qE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+"; then
        log_fail "Unpackerr uses hard-coded IP for Sonarr"
    else
        log_warn "Could not verify Unpackerr Sonarr URL"
    fi
    
    # Check Radarr URL
    if echo "$config" | grep -q "UN_RADARR_0_URL=http://radarr:"; then
        log_pass "Unpackerr uses service DNS for Radarr (http://radarr:...)"
    elif echo "$config" | grep "UN_RADARR_0_URL" | grep -qE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+"; then
        log_fail "Unpackerr uses hard-coded IP for Radarr"
    else
        log_warn "Could not verify Unpackerr Radarr URL"
    fi
}

# -----------------------------------------------------------------------------
# Verify Local Basic Auth Middleware
# -----------------------------------------------------------------------------

verify_local_basic_auth() {
    log_section "Verifying Local Basic Auth Middleware"
    
    cd "$PROJECT_ROOT"
    
    local config
    config=$(docker compose \
        --env-file .env.common \
        --env-file .env.local \
        --env-file .env.secrets \
        -f compose.yml \
        -f compose.local.yml \
        config 2>/dev/null)
    
    local routers=(
        "sonarr"
        "radarr"
        "prowlarr"
        "qbittorrent"
        "maintainerr"
        "notifiarr"
        "overseerr"
        "plex"
        "tautulli"
        "stash"
    )
    
    for router in "${routers[@]}"; do
        if echo "$config" | grep -q "traefik.http.routers.${router}.middlewares=local-auth"; then
            log_pass "LOCAL $router router has basic-auth middleware"
        else
            log_fail "LOCAL $router router missing basic-auth middleware"
        fi
    done
}

# -----------------------------------------------------------------------------
# Verify UNRAID Has No Basic Auth
# -----------------------------------------------------------------------------

verify_unraid_no_basic_auth() {
    log_section "Verifying UNRAID Has No Forced Basic Auth"
    
    cd "$PROJECT_ROOT"
    
    # Note: UNRAID uses base compose.yml which doesn't have middlewares
    # The compose.local.yml adds the middlewares
    # So we just verify the base config doesn't have them
    
    local config
    config=$(docker compose \
        --env-file .env.common \
        --env-file .env.unraid \
        --env-file .env.secrets \
        -f compose.yml \
        -f compose.unraid.yml \
        config 2>/dev/null)
    
    if echo "$config" | grep -q "local-auth@file"; then
        log_warn "UNRAID config references local-auth middleware (may be intentional for some services)"
    else
        log_pass "UNRAID config does not force local-auth middleware on routers"
    fi
}

# -----------------------------------------------------------------------------
# Curl Test Commands
# -----------------------------------------------------------------------------

generate_curl_tests() {
    log_section "Curl Test Commands (Run After Stack is Up)"
    
    echo ""
    echo "# LOCAL environment tests (requires local-dns running or /etc/hosts entries)"
    echo "# These commands test routing with Host headers"
    echo ""
    
    local local_services=(
        "sonarr.local.lan:8989"
        "radarr.local.lan:7878"
        "prowlarr.local.lan:9696"
        "qb.local.lan:8080"
        "maintainerr.local.lan:6246"
        "notifiarr.local.lan:5454"
        "overseerr.local.lan:5055"
        "plex.local.lan:32400"
        "tautulli.local.lan:8181"
        "stash.local.lan:9999"
    )
    
    echo "# Test via Traefik (port 80) with Host header:"
    for svc in "${local_services[@]}"; do
        local host="${svc%%:*}"
        echo "curl -s -o /dev/null -w '%{http_code}' -H 'Host: $host' http://localhost:80/"
    done
    
    echo ""
    echo "# UNRAID environment tests:"
    
    local unraid_services=(
        "sonarr.lan"
        "radarr.lan"
        "prowlarr.lan"
        "qb.lan"
        "maintainerr.lan"
        "notifiarr.lan"
        "overseerr.lan"
        "plex.lan"
        "tautulli.lan"
        "stash.lan"
    )
    
    echo "# Test via Traefik (port 80) with Host header:"
    for host in "${unraid_services[@]}"; do
        echo "curl -s -o /dev/null -w '%{http_code}' -H 'Host: $host' http://localhost:80/"
    done
}

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

print_summary() {
    log_section "Validation Summary"
    
    echo ""
    echo -e "  ${GREEN}Passed:${NC}  $PASS"
    echo -e "  ${RED}Failed:${NC}  $FAIL"
    echo -e "  ${YELLOW}Warnings:${NC} $WARN"
    echo ""
    
    if [[ $FAIL -gt 0 ]]; then
        echo -e "${RED}❌ Validation FAILED - Please fix the issues above${NC}"
        exit 1
    elif [[ $WARN -gt 0 ]]; then
        echo -e "${YELLOW}⚠️  Validation PASSED with warnings${NC}"
        exit 0
    else
        echo -e "${GREEN}✅ Validation PASSED${NC}"
        exit 0
    fi
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

main() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║           Home Lab Configuration Validator                     ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    
    check_prerequisites
    validate_compose_config
    verify_traefik_routers
    verify_qbittorrent_routing
    verify_arr_not_vpn
    verify_unpackerr_urls
    verify_local_basic_auth
    verify_unraid_no_basic_auth
    generate_curl_tests
    print_summary
}

main "$@"
