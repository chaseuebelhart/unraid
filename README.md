# unraid

Everything that configures or automates **NASTower**, Chase's Unraid server. One repo so the whole homelab has one
history and one place to look. The only homelab code that lives outside it is
[`unraid-management-agent`](https://github.com/chaseuebelhart/unraid-management-agent) — a fork of a third-party plugin —
and `winswatch/`, the Cloudflare-hosted site for winswatch.com.

| Directory | What | Deployed how |
|---|---|---|
| `kometa/` | Kometa collection and overlay definitions, the Wins Watch assets, fonts and generated files | `scripts/winswatch/deploy.sh`; a few collection files are also fetched by raw GitHub URL from `main`, **so paths under `kometa/` must not move** |
| `scripts/winswatch/` | The Wins Watch pipeline: MDBList scores, air-date labels, REQUESTED labels, per-user Home rows, collection cards, hub ordering, nightly health check, plus the host jobs | `deploy.sh` rsyncs to `/mnt/user/appdata/scripts/winswatch`; run on the host through `hostexec.py` |
| `compose/` | Docker Compose stack for the box — traefik, dnsmasq, mosquitto, kometa — with its own README, docs and helper scripts | applied by hand on the server (`compose.unraid.yml`) |
| `esphome/` | ESPHome device configs (`atom-lite`, `bt-proxy`) | `esphome run <file>`; `secrets.yaml` stays local and ignored |
| `vm-lab/` | Script + notes for booting Unraid in a local KVM to test changes safely | run on the workstation |
| `radarr/` | Custom list JSON for Radarr | pulled by Radarr |
| `utils/` | Small shared Python helpers (`env_loader`) | imported by scripts |
| `assets/` | Source images (Win's photo) | — |
| `docs/` | See below | — |

## Docs

- **`docs/wins-watch.md`** — the operations runbook: what runs when, how to change the posters/rows, the health check,
  and the things that have actually broken. Start here for anything Plex-facing.
- **`docs/plex-internals.md`** — how Plex itself works: object model, where it stores what, the settings API, the
  rating and share-filter traps.
- **`docs/superpowers/specs|plans/`** — the design specs and implementation plans the Wins Watch work was built from.

## Working here

```bash
scripts/winswatch/.venv/bin/python -m pytest scripts/winswatch/tests -q   # 118 tests
bash scripts/winswatch/deploy.sh                                          # push scripts + kometa config to the server
python3 scripts/winswatch/hostexec.py run <job>                           # run a host job (nightly, order, check, …)
```

Secrets never live here: the scripts read `/mnt/nastower/appdata/scripts/winswatch/.env` on the server, and
`kometa/config.yml`, `esphome/secrets.yaml` and `compose/.env.secrets` are gitignored.
