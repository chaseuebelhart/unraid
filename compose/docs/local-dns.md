# Accessing Your Home Lab Services

## Quick Access (Recommended for Local Testing)

The easiest way to access your services locally is to add entries to your `/etc/hosts` file.

### Option 1: Add /etc/hosts entries (Simplest)

Add these lines to `/etc/hosts` (Linux/macOS) or `C:\Windows\System32\drivers\etc\hosts` (Windows):

```
127.0.0.1 sonarr.local.lan
127.0.0.1 radarr.local.lan
127.0.0.1 prowlarr.local.lan
127.0.0.1 qb.local.lan
127.0.0.1 maintainerr.local.lan
127.0.0.1 overseerr.local.lan
127.0.0.1 plex.local.lan
127.0.0.1 tautulli.local.lan
127.0.0.1 stash.local.lan
127.0.0.1 notifiarr.local.lan
127.0.0.1 grafana.local.lan
127.0.0.1 ha.local.lan
127.0.0.1 speedtest.local.lan
127.0.0.1 traefik.local.lan
```

On Linux/macOS:
```bash
sudo nano /etc/hosts
# Add the lines above, save and exit
```

Then access services at:
- http://sonarr.local.lan
- http://radarr.local.lan
- http://plex.local.lan
- etc.

**Username:** admin  
**Password:** (the password you set when running `htpasswd`)

### Option 2: Use the Local DNS Container

If you want automatic wildcard resolution for `*.local.lan`:

1. **Start the DNS container** (uses port 5353 to avoid conflicts):
   ```bash
   docker compose --env-file .env.common --env-file .env.local --env-file .env.secrets \
     -f compose.yml -f compose.local.yml --profile dns up -d local-dns
   ```

2. **Configure your system to use it:**

   **Linux (NetworkManager):**
   ```bash
   nmcli connection modify "Your Connection" ipv4.dns "127.0.0.1"
   nmcli connection modify "Your Connection" ipv4.dns-search "local.lan"
   nmcli connection down "Your Connection" && nmcli connection up "Your Connection"
   ```

   **Linux (systemd-resolved - add custom DNS):**
   ```bash
   sudo mkdir -p /etc/systemd/resolved.conf.d/
   sudo tee /etc/systemd/resolved.conf.d/local-dns.conf << EOF
   [Resolve]
   DNS=127.0.0.1:5353
   Domains=~local.lan
   EOF
   sudo systemctl restart systemd-resolved
   ```

   **macOS:**
   ```bash
   sudo mkdir -p /etc/resolver
   sudo tee /etc/resolver/local.lan << EOF
   nameserver 127.0.0.1
   port 5353
   EOF
   ```

3. **Verify resolution:**
   ```bash
   dig @127.0.0.1 -p 5353 sonarr.local.lan
   nslookup -port=5353 sonarr.local.lan 127.0.0.1
   ```

## Service URLs

| Service | Local URL | Description |
|---------|-----------|-------------|
| Sonarr | http://sonarr.local.lan | TV show management |
| Radarr | http://radarr.local.lan | Movie management |
| Prowlarr | http://prowlarr.local.lan | Indexer management |
| qBittorrent | http://qb.local.lan | Torrent client |
| Maintainerr | http://maintainerr.local.lan | Plex maintenance |
| Overseerr | http://overseerr.local.lan | Request management |
| Plex | http://plex.local.lan | Media server |
| Tautulli | http://tautulli.local.lan | Plex statistics |
| Stash | http://stash.local.lan | Media organizer |
| Notifiarr | http://notifiarr.local.lan | Notifications |
| Grafana | http://grafana.local.lan | Dashboards |
| Home Assistant | http://ha.local.lan | Home automation |
| Speedtest | http://speedtest.local.lan | Network speed test |
| Traefik Dashboard | http://traefik.local.lan | Reverse proxy dashboard |

## Authentication

All services are protected by HTTP Basic Authentication in the local environment.

- **Username:** `admin`
- **Password:** The password you configured in `traefik/dynamic/users.txt`

To change the password:
```bash
htpasswd -nB admin > traefik/dynamic/users.txt
```

Traefik will automatically pick up the change (no restart needed).

## Troubleshooting

### Services return 404
- Check that Traefik is running: `docker ps | grep traefik`
- Check Traefik logs: `docker logs traefik`
- Verify the Host header matches: `curl -H "Host: sonarr.local.lan" http://localhost/`

### Services return 502/503
- The backend service might be starting up or unhealthy
- Check service logs: `docker logs sonarr`
- Run health check: `./scripts/healthcheck.sh`

### Can't resolve *.local.lan
- Verify /etc/hosts entries or DNS setup
- Test with explicit Host header: `curl -H "Host: sonarr.local.lan" http://localhost/`

### Authentication not working
- Verify users.txt has valid htpasswd format
- Restart Traefik if needed: `docker restart traefik`
