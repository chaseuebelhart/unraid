# Migration from Nginx Proxy Manager (NPM)

This guide documents how the Traefik configuration matches your existing NPM proxy host setup and provides steps to verify the migration.

## NPM to Traefik Route Mapping

### Original NPM Proxy Hosts (Production)

| NPM Domain | NPM Backend | Traefik Domain | Traefik Backend |
|------------|-------------|----------------|-----------------|
| maintainerr.lan | maintainerr:6246 | maintainerr.lan | maintainerr:6246 |
| notifiarr.lan | notifiarr:5454 | notifiarr.lan | notifiarr:5454 |
| overseerr.lan | overseerr:5055 | overseerr.lan | overseerr:5055 |
| plex.lan | plex:32400 | plex.lan | plex:32400 |
| prowlarr.lan | prowlarr:9696 | prowlarr.lan | prowlarr:9696 |
| qb.lan | qbittorrent:8080 | qb.lan | **gluetun:8080** |
| radarr.lan | radarr:7878 | radarr.lan | radarr:7878 |
| sonarr.lan | sonarr:8989 | sonarr.lan | sonarr:8989 |
| stash.lan | stash:9999 | stash.lan | stash:9999 |
| tautulli.lan | tautulli:8181 | tautulli.lan | tautulli:8181 |

### Key Difference: qBittorrent Routing

**NPM Configuration**:
```
qb.lan → qbittorrent:8080
```

**Traefik Configuration**:
```
qb.lan → gluetun:8080
```

The qBittorrent container shares Gluetun's network namespace (`network_mode: service:gluetun`), so:
- qBittorrent doesn't have its own IP/port exposed
- The WebUI is accessible through Gluetun's IP on port 8080
- Traefik labels are placed on the `gluetun` service, not `qbittorrent`

## How Traefik Routing Works

### Labels vs NPM GUI

NPM uses a database and GUI to configure routes. Traefik uses Docker labels:

**NPM Approach**:
```
1. Go to NPM dashboard
2. Add Proxy Host
3. Fill in domain, scheme, IP, port
4. Save
```

**Traefik Approach** (in compose.yml):
```yaml
services:
  sonarr:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.sonarr.rule=Host(`sonarr.${BASE_DOMAIN}`)"
      - "traefik.http.routers.sonarr.entrypoints=web"
      - "traefik.http.services.sonarr.loadbalancer.server.port=8989"
```

### Traefik Label Breakdown

| Label | NPM Equivalent | Description |
|-------|----------------|-------------|
| `traefik.enable=true` | N/A | Enable Traefik for this container |
| `traefik.http.routers.X.rule=Host(...)` | Domain Name | Matching rule for incoming requests |
| `traefik.http.routers.X.entrypoints=web` | Scheme (HTTP) | Entry point (port 80 for HTTP) |
| `traefik.http.services.X.loadbalancer.server.port=Y` | Forward Port | Backend service port |

## Migration Checklist

### Pre-Migration

- [ ] Document all NPM proxy hosts
- [ ] Note any custom configurations (SSL, access lists, advanced settings)
- [ ] Backup NPM database
- [ ] Test Traefik configuration locally first

### Migration Steps

1. **Parallel Running Period**:
   ```bash
   # Keep NPM running on port 80
   # Run Traefik on a different port temporarily
   # Edit traefik/traefik.yml:
   entryPoints:
     web:
       address: ":8080"  # Temporary port
   ```

2. **Test Each Route**:
   ```bash
   # Test via curl with Host header
   curl -H "Host: sonarr.lan" http://traefik-ip:8080/
   ```

3. **Switch Over**:
   ```bash
   # Stop NPM
   docker stop nginx-proxy-manager
   
   # Update Traefik to use port 80
   # Edit traefik/traefik.yml:
   entryPoints:
     web:
       address: ":80"
   
   # Restart Traefik
   docker restart traefik
   ```

4. **Verify All Routes**:
   ```bash
   ./scripts/validate.sh
   ```

### Post-Migration

- [ ] Verify each domain resolves correctly
- [ ] Check SSL certificates (if using HTTPS)
- [ ] Monitor for 502/503 errors
- [ ] Update any DNS records if needed
- [ ] Remove NPM container after verification period

## Verification Commands

### Check Traefik Routers

```bash
# Via API
curl http://traefik.lan/api/http/routers | jq

# Or check dashboard
open http://traefik.lan/dashboard/
```

### Test Each Route

```bash
# Quick test all routes
for domain in sonarr radarr prowlarr qb maintainerr overseerr plex tautulli stash notifiarr; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -H "Host: ${domain}.lan" http://localhost/)
  echo "${domain}.lan: HTTP $code"
done
```

### Compare Responses

```bash
# Get response from old NPM setup
curl -I http://sonarr.lan/ > npm_response.txt

# Get response from Traefik setup  
curl -I -H "Host: sonarr.lan" http://traefik-ip/ > traefik_response.txt

# Compare
diff npm_response.txt traefik_response.txt
```

## Common Migration Issues

### Issue: 404 Not Found

**Cause**: Router rule not matching or service not found.

**Solution**:
```bash
# Check router exists
curl http://traefik.lan/api/http/routers | jq '.[] | select(.name | contains("sonarr"))'

# Verify labels in compose config
docker compose config | grep -A 10 "traefik.http.routers.sonarr"
```

### Issue: 502 Bad Gateway

**Cause**: Backend service unreachable.

**Solution**:
```bash
# Check service is running
docker ps | grep sonarr

# Check Traefik can reach service
docker exec traefik wget -qO- http://sonarr:8989/ping

# Verify networks
docker network inspect proxy
```

### Issue: 503 Service Unavailable

**Cause**: Service not healthy or starting up.

**Solution**:
```bash
# Check service health
docker inspect --format='{{.State.Health.Status}}' sonarr

# View service logs
docker logs sonarr --tail=50
```

### Issue: qBittorrent Not Accessible

**Cause**: qBittorrent shares Gluetun network namespace.

**Solution**:
```bash
# Verify gluetun is healthy
docker inspect --format='{{.State.Health.Status}}' gluetun

# Check qbittorrent labels are on gluetun, not qbittorrent service
docker inspect gluetun | jq '.[].Config.Labels' | grep qbittorrent

# Verify port is exposed through gluetun
curl http://gluetun:8080/
```

## Feature Comparison

| Feature | NPM | Traefik | Notes |
|---------|-----|---------|-------|
| GUI Dashboard | ✅ | ✅ | Traefik dashboard at /dashboard/ |
| Auto SSL (Let's Encrypt) | ✅ | ✅ | Configure certificatesResolvers |
| Access Lists | ✅ | ✅ | Use middleware (ipWhiteList) |
| Basic Auth | ✅ | ✅ | Use basicAuth middleware |
| Websockets | ✅ | ✅ | Automatic |
| Custom Headers | ✅ | ✅ | Use headers middleware |
| Redirects | ✅ | ✅ | Use redirectRegex middleware |
| Docker Auto-Discovery | ❌ | ✅ | Traefik's key advantage |
| Multiple Domains | ✅ | ✅ | Use multiple Host() rules |

## Rollback Procedure

If migration fails:

1. **Stop Traefik**:
   ```bash
   docker stop traefik
   ```

2. **Restart NPM**:
   ```bash
   docker start nginx-proxy-manager
   ```

3. **Verify NPM is working**:
   ```bash
   curl http://sonarr.lan/
   ```

4. **Investigate Traefik issues**:
   ```bash
   docker logs traefik
   ./scripts/validate.sh
   ```

## Additional Resources

- [Traefik Documentation](https://doc.traefik.io/traefik/)
- [Traefik Docker Provider](https://doc.traefik.io/traefik/providers/docker/)
- [Traefik Middlewares](https://doc.traefik.io/traefik/middlewares/overview/)
- [NPM to Traefik Migration Guide](https://www.smarthomebeginner.com/traefik-docker-compose-guide/)
