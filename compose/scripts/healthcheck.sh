#!/usr/bin/env bash
# =============================================================================
# Home Lab Health Check Script
# =============================================================================
# This script checks the health status of all running containers and services.
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
HEALTHY=0
UNHEALTHY=0
UNKNOWN=0

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

log_healthy() {
    echo -e "${GREEN}✓ HEALTHY:${NC} $1"
    ((HEALTHY++))
}

log_unhealthy() {
    echo -e "${RED}✗ UNHEALTHY:${NC} $1"
    ((UNHEALTHY++))
}

log_unknown() {
    echo -e "${YELLOW}? UNKNOWN:${NC} $1"
    ((UNKNOWN++))
}

log_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# -----------------------------------------------------------------------------
# Check Container Health
# -----------------------------------------------------------------------------

check_container_status() {
    local container=$1
    local status
    
    # Check if container exists
    if ! docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
        log_unknown "$container (not found)"
        return
    fi
    
    # Get container state
    local state
    state=$(docker inspect --format '{{.State.Status}}' "$container" 2>/dev/null || echo "unknown")
    
    # Get health status if available
    local health
    health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$container" 2>/dev/null || echo "unknown")
    
    case "$state" in
        "running")
            case "$health" in
                "healthy")
                    log_healthy "$container (running, healthy)"
                    ;;
                "unhealthy")
                    log_unhealthy "$container (running, unhealthy)"
                    ;;
                "starting")
                    log_unknown "$container (running, health starting)"
                    ;;
                "no-healthcheck")
                    log_healthy "$container (running, no healthcheck)"
                    ;;
                *)
                    log_unknown "$container (running, health: $health)"
                    ;;
            esac
            ;;
        "exited")
            log_unhealthy "$container (exited)"
            ;;
        "restarting")
            log_unhealthy "$container (restarting)"
            ;;
        *)
            log_unknown "$container (state: $state)"
            ;;
    esac
}

# -----------------------------------------------------------------------------
# Check Service Endpoints
# -----------------------------------------------------------------------------

check_service_endpoint() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}
    
    local code
    code=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 "$url" 2>/dev/null || echo "000")
    
    if [[ "$code" == "$expected_code" ]] || [[ "$code" == "401" ]] || [[ "$code" == "302" ]]; then
        log_healthy "$name ($url) - HTTP $code"
    elif [[ "$code" == "000" ]]; then
        log_unhealthy "$name ($url) - Connection failed"
    else
        log_unknown "$name ($url) - HTTP $code (expected $expected_code)"
    fi
}

# -----------------------------------------------------------------------------
# Check VPN Status
# -----------------------------------------------------------------------------

check_vpn_status() {
    log_section "VPN Status (Gluetun)"
    
    if docker ps --format '{{.Names}}' | grep -q "^gluetun$"; then
        # Check gluetun's public IP endpoint
        local vpn_ip
        vpn_ip=$(docker exec gluetun wget -qO- http://ipinfo.io/ip 2>/dev/null || echo "unknown")
        
        if [[ "$vpn_ip" != "unknown" ]] && [[ -n "$vpn_ip" ]]; then
            log_healthy "VPN connected - Public IP: $vpn_ip"
        else
            log_unhealthy "VPN may not be connected"
        fi
        
        # Check gluetun control server
        local gluetun_status
        gluetun_status=$(docker exec gluetun wget -qO- http://localhost:8000/v1/openvpn/status 2>/dev/null || echo "unknown")
        echo "  Gluetun status: $gluetun_status"
    else
        log_unknown "Gluetun container not running"
    fi
}

# -----------------------------------------------------------------------------
# Check Docker Networks
# -----------------------------------------------------------------------------

check_networks() {
    log_section "Docker Networks"
    
    local networks=("proxy" "apps")
    
    for network in "${networks[@]}"; do
        if docker network inspect "$network" &>/dev/null; then
            local count
            count=$(docker network inspect "$network" --format '{{len .Containers}}')
            log_healthy "Network '$network' exists ($count containers attached)"
        else
            log_unhealthy "Network '$network' does not exist"
        fi
    done
}

# -----------------------------------------------------------------------------
# Check Traefik Routing
# -----------------------------------------------------------------------------

check_traefik_routing() {
    log_section "Traefik Routing (via localhost:80)"
    
    # Determine which domain to use based on what's configured
    local base_domain
    if [[ -f "$PROJECT_ROOT/.env.local" ]]; then
        base_domain=$(grep "^BASE_DOMAIN=" "$PROJECT_ROOT/.env.local" | cut -d= -f2)
    else
        base_domain="local.lan"
    fi
    
    local services=(
        "sonarr"
        "radarr"
        "prowlarr"
        "qb"
        "maintainerr"
        "overseerr"
        "plex"
        "tautulli"
        "stash"
    )
    
    echo "  Testing with domain: *.$base_domain"
    
    for svc in "${services[@]}"; do
        local host="${svc}.${base_domain}"
        local code
        code=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 -H "Host: $host" http://localhost:80/ 2>/dev/null || echo "000")
        
        if [[ "$code" == "000" ]]; then
            log_unknown "$host - Traefik not reachable"
        elif [[ "$code" == "404" ]]; then
            log_unhealthy "$host - Route not found (404)"
        elif [[ "$code" == "502" ]] || [[ "$code" == "503" ]]; then
            log_unhealthy "$host - Backend unavailable ($code)"
        else
            log_healthy "$host - HTTP $code"
        fi
    done
}

# -----------------------------------------------------------------------------
# Check Disk Space
# -----------------------------------------------------------------------------

check_disk_space() {
    log_section "Disk Space"
    
    # Check Docker data root
    local docker_root
    docker_root=$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || echo "/var/lib/docker")
    
    local disk_usage
    disk_usage=$(df -h "$docker_root" 2>/dev/null | tail -1 | awk '{print $5}' | tr -d '%')
    
    if [[ -n "$disk_usage" ]]; then
        if [[ "$disk_usage" -lt 80 ]]; then
            log_healthy "Docker root ($docker_root): ${disk_usage}% used"
        elif [[ "$disk_usage" -lt 90 ]]; then
            log_unknown "Docker root ($docker_root): ${disk_usage}% used (warning)"
        else
            log_unhealthy "Docker root ($docker_root): ${disk_usage}% used (critical)"
        fi
    fi
    
    # Check DATA_ROOT if defined
    if [[ -f "$PROJECT_ROOT/.env.local" ]]; then
        local data_root
        data_root=$(grep "^DATA_ROOT=" "$PROJECT_ROOT/.env.local" | cut -d= -f2)
        if [[ -d "$data_root" ]]; then
            disk_usage=$(df -h "$data_root" 2>/dev/null | tail -1 | awk '{print $5}' | tr -d '%')
            if [[ -n "$disk_usage" ]]; then
                if [[ "$disk_usage" -lt 80 ]]; then
                    log_healthy "Data root ($data_root): ${disk_usage}% used"
                elif [[ "$disk_usage" -lt 90 ]]; then
                    log_unknown "Data root ($data_root): ${disk_usage}% used (warning)"
                else
                    log_unhealthy "Data root ($data_root): ${disk_usage}% used (critical)"
                fi
            fi
        fi
    fi
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

main() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║              Home Lab Health Check                             ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
    
    log_section "Container Status"
    
    # Core infrastructure
    local containers=(
        "traefik"
        "gluetun"
        "qbittorrent"
        "sonarr"
        "radarr"
        "prowlarr"
        "unpackerr"
        "maintainerr"
        "overseerr"
        "plex"
        "tautulli"
        "stash"
        "kometa"
        "notifiarr"
        "homeassistant"
        "govee2mqtt"
        "mosquitto"
        "influxdb"
        "grafana"
        "nut-influxdb-exporter"
        "librespeed"
    )
    
    for container in "${containers[@]}"; do
        check_container_status "$container"
    done
    
    check_vpn_status
    check_networks
    check_traefik_routing
    check_disk_space
    
    # Summary
    log_section "Health Check Summary"
    echo ""
    echo -e "  ${GREEN}Healthy:${NC}   $HEALTHY"
    echo -e "  ${RED}Unhealthy:${NC} $UNHEALTHY"
    echo -e "  ${YELLOW}Unknown:${NC}   $UNKNOWN"
    echo ""
    
    if [[ $UNHEALTHY -gt 0 ]]; then
        echo -e "${RED}❌ Some services are unhealthy${NC}"
        exit 1
    elif [[ $UNKNOWN -gt 0 ]]; then
        echo -e "${YELLOW}⚠️  Some services have unknown status${NC}"
        exit 0
    else
        echo -e "${GREEN}✅ All services are healthy${NC}"
        exit 0
    fi
}

main "$@"
