# Home Lab Docker Compose Project

A production-ready Docker Compose setup for a home media server and home automation stack, featuring Traefik as a reverse proxy, VPN routing for torrent traffic, and comprehensive observability.

## Features

- **Traefik Reverse Proxy**: Automatic service discovery and routing
- **VPN Integration**: qBittorrent traffic routed through Gluetun (ProtonVPN)
- **Dual Environment**: Local testing and Unraid production configurations
- **Basic Auth**: Protect local environment with HTTP basic authentication
- **Comprehensive Stack**: Media automation, home automation, and observability

## Quick Start

### Prerequisites

- Docker Engine 24.0+
- Docker Compose V2 (included with Docker Engine)
- Git

### Local Development

1. **Clone and configure**:
   ```bash
   git clone <repository-url>
   cd home-lab
   
   # Copy and edit secrets file
   cp .env.secrets.example .env.secrets
   # Edit .env.secrets with your values
   ```

2. **Generate basic auth credentials**:
   ```bash
   # Install htpasswd if needed (apt install apache2-utils)
   htpasswd -nB admin > traefik/dynamic/users.txt
   ```

3. **Start the stack**:
   ```bash
   docker compose \
     --env-file .env.common \
     --env-file .env.local \
     --env-file .env.secrets \
     -f compose.yml \
     -f compose.local.yml \
     up -d
   ```

4. **Configure local DNS** (see [docs/local-dns.md](docs/local-dns.md))

5. **Validate configuration**:
   ```bash
   ./scripts/validate.sh
   ```

### Unraid Production

1. **Upload files** to your Unraid server (e.g., `/mnt/user/docker/home-lab/`)

2. **Configure paths** in `.env.unraid`:
   ```bash
   DATA_ROOT=/mnt/user/data
   APPDATA_ROOT=/mnt/user/appdata/homelab
   ```

3. **Configure secrets** in `.env.secrets`

4. **Start the stack**:
   ```bash
   docker compose \
     --env-file .env.common \
     --env-file .env.unraid \
     --env-file .env.secrets \
     -f compose.yml \
     -f compose.unraid.yml \
     up -d
   ```

5. **Enable optional profiles** (PiHole, Cloudflared):
   ```bash
   docker compose \
     --env-file .env.common \
     --env-file .env.unraid \
     --env-file .env.secrets \
     -f compose.yml \
     -f compose.unraid.yml \
     --profile dns \
     --profile tunnel \
     up -d
   ```

## Architecture

### Networks

| Network | Type | Purpose |
|---------|------|---------|
| `proxy` | Bridge | External-facing services (Traefik routes here) |
| `apps` | Internal | Internal service communication |

### VPN Routing

```
                    ┌─────────────┐
                    │   Traefik   │
                    │  (proxy)    │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │   Gluetun   │ │   Sonarr    │ │   Radarr    │
    │    (VPN)    │ │ (No VPN)    │ │ (No VPN)    │
    └──────┬──────┘ └─────────────┘ └─────────────┘
           │
    ┌──────▼──────┐
    │ qBittorrent │
    │(network_mode│
    │  :gluetun)  │
    └─────────────┘
```

- **qBittorrent**: Shares Gluetun's network namespace (all traffic via VPN)
- **Arr Apps**: Direct network access (NOT behind VPN)
- **Traefik routes qb.* to Gluetun container on port 8080**

### Service Domains

| Service | Local Domain | Prod Domain | Port |
|---------|--------------|-------------|------|
| Sonarr | sonarr.local.lan | sonarr.lan | 8989 |
| Radarr | radarr.local.lan | radarr.lan | 7878 |
| Prowlarr | prowlarr.local.lan | prowlarr.lan | 9696 |
| qBittorrent | qb.local.lan | qb.lan | 8080 |
| Maintainerr | maintainerr.local.lan | maintainerr.lan | 6246 |
| Overseerr | overseerr.local.lan | overseerr.lan | 5055 |
| Plex | plex.local.lan | plex.lan | 32400 |
| Tautulli | tautulli.local.lan | tautulli.lan | 8181 |
| Stash | stash.local.lan | stash.lan | 9999 |
| Notifiarr | notifiarr.local.lan | notifiarr.lan | 5454 |
| Grafana | grafana.local.lan | grafana.lan | 3000 |
| Home Assistant | ha.local.lan | ha.lan | 8123 |

## Configuration Files

### Environment Files

| File | Purpose |
|------|---------|
| `.env.common` | Shared configuration (TZ, ports, etc.) |
| `.env.local` | Local development overrides |
| `.env.unraid` | Unraid production overrides |
| `.env.secrets` | Secrets (API keys, passwords) - **DO NOT COMMIT** |

### Compose Files

| File | Purpose |
|------|---------|
| `compose.yml` | Base service definitions |
| `compose.local.yml` | Local overrides (DNS, basic auth) |
| `compose.unraid.yml` | Unraid overrides (paths, hardware) |

## Scripts

| Script | Description |
|--------|-------------|
| `scripts/validate.sh` | Validate compose config and routing |
| `scripts/healthcheck.sh` | Check container and service health |
| `scripts/backup_configs.sh` | Backup appdata without stopping containers |

### Running Scripts

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Validate configuration
./scripts/validate.sh

# Check health
./scripts/healthcheck.sh

# Create backup
./scripts/backup_configs.sh
```

## Tier 0 vs Tier 1 Configuration

### Tier 0: Persistent App Configs
Application configurations that survive container recreation:
- Mounted volumes under `${APPDATA_ROOT}/<app>/`
- In-app settings stored in SQLite databases or config files

### Tier 1: Codified Configs
Configuration files tracked in git:
- `traefik/traefik.yml` - Traefik static configuration
- `traefik/dynamic/*.yml` - Traefik dynamic configuration
- `mosquitto/config/mosquitto.conf` - MQTT broker config
- `dnsmasq/dnsmasq.conf` - Local DNS configuration

## VPN Configuration

The stack uses [Gluetun](https://github.com/qdm12/gluetun) for VPN connectivity.

### ProtonVPN Setup

1. Get your WireGuard credentials from ProtonVPN:
   - Log in to ProtonVPN
   - Go to Downloads → WireGuard configuration
   - Get your private key and address

2. Configure in `.env.secrets`:
   ```bash
   WIREGUARD_PRIVATE_KEY=your_private_key_here
   WIREGUARD_ADDRESSES=10.2.0.2/32
   SERVER_COUNTRIES=United States
   SERVER_CITIES=
   ```

### Verify VPN is Working

```bash
# Check Gluetun's public IP
docker exec gluetun wget -qO- http://ipinfo.io

# Check qBittorrent's IP (should match Gluetun)
docker exec gluetun wget -qO- http://ipinfo.io
```

## Troubleshooting

### Common Issues

1. **Port 53 in use** (local DNS):
   ```bash
   # Check what's using port 53
   sudo lsof -i :53
   
   # On Ubuntu, disable systemd-resolved
   sudo systemctl disable systemd-resolved
   sudo systemctl stop systemd-resolved
   ```

2. **VPN not connecting**:
   ```bash
   # Check Gluetun logs
   docker logs gluetun
   ```

3. **Traefik not routing**:
   ```bash
   # Check Traefik dashboard
   open http://traefik.local.lan
   
   # Check Traefik logs
   docker logs traefik
   ```

4. **Basic auth not working**:
   ```bash
   # Regenerate users.txt
   htpasswd -nB admin > traefik/dynamic/users.txt
   
   # Restart Traefik
   docker restart traefik
   ```

### Logs

```bash
# View all logs
docker compose logs -f

# View specific service
docker compose logs -f sonarr

# View last 100 lines
docker compose logs --tail=100 traefik
```

## Maintenance

### Updates

```bash
# Pull latest images
docker compose pull

# Recreate containers with new images
docker compose up -d --force-recreate
```

### Backups

```bash
# Create backup
./scripts/backup_configs.sh

# List backups
./scripts/backup_configs.sh list
```

## Security Considerations

1. **Local environment**: Protected by basic auth via Traefik middleware
2. **Production**: Assumes network-level security (LAN only access)
3. **Secrets**: Store in `.env.secrets`, never commit to git
4. **VPN**: All torrent traffic routed through VPN
5. **Docker socket**: Mounted read-only to Traefik

## License

MIT License - See LICENSE file for details.
