# Wins Watch — Plex curation runbook

Everything that makes Chase's Plex server ("Wins Watch") look and behave like a streaming service: poster overlays, Home
rows, the nightly data pipeline. Written 2026-09-22, live in production since 2026-09-21.

Design decisions live in the two specs — `docs/superpowers/specs/2026-09-18-wins-watch-posters-design.md` (posters) and
`2026-09-21-wins-watch-home-design.md` (Home rows). **This file is the operations view: what runs when, how to change it,
how to fix it.** When they disagree, the specs are the intent and this file is the fact — reconcile and fix both.

---

## 1. The moving parts

| Piece | Where | Owns |
|---|---|---|
| **Kometa** | container `Kometa` (br0 `.23`), config `/mnt/user/appdata/Kometa/config` | draws every overlay; builds the server-wide collections; `mass_*_rating_update` (except user rating) |
| **our scripts** | repo `scripts/winswatch/`, deployed to `/mnt/user/appdata/scripts/winswatch` | everything Kometa can't: MDBList scores, air-date labels, REQUESTED labels, per-user rows, collection cards, hub order, health check |
| **Shortlist** | container `shortlist` (`:5959`), db `appdata/shortlist/shortlist.db` | the three personal rows (`✨ for you`, `🎯 Because you watched`, `👥 Popular`), per-user share-filter privacy |
| **Maintainerr** | container in the gluetun netns, API `http://192.168.0.30:6246` (unauthenticated) | membership of `⏳ … Leaving Wins Watch`; deletes expired media |
| **`update_days_left`** | Unraid user script → `appdata/scripts/maintainerr/pyscripts/days_left_label.py` | `DaysLeft_N` labels that drive the LEAVING plate |
| **Overseerr** | container `overseerr` (`.6:5055`), winswatch.com | requests; the source for REQUESTED labels and the per-user rows |
| **Agregarr** | **retired 2026-09-21** (container deleted) | was: per-user request rows, hub promotion |

Plex libraries: **1 = Movies, 2 = TV Shows** (production). 4/5 were the Wins Watch Lab libraries — delete them when the
lab is no longer wanted (`create_lab_libraries.py` made them; symlinks under `/mnt/user/data/media/_winswatch-lab`).

## 2. Nightly timeline

**The server clock is UTC-7** (Unraid host and the scheduled Kometa container). `home.py` computes "today" in
America/Chicago. The two agree inside the 04:30–21:50 window, which is why hub ordering stops at 21:50.

| Server clock | What | Trigger |
|---|---|---|
| 00:00 / 12:00 | Maintainerr fills the Leaving collections | Maintainerr's own cron |
| 03:30 + every 30 min | Shortlist builds its rows, writes share filters, promotes its hubs, sweeps "orphan" collections | Shortlist |
| 04:30 | `nightly.sh`: `scores.py` → `airdates.py` → `home.py requested` → `rows` → `cards` → `check` | user script **`winswatch`** (`30 4 * * *`) |
| ~04:40 | `DaysLeft_N` labels | user script **`update_days_left`** |
| 05:00 | Kometa: collections → overlays → operations (~16 min) | Kometa container's own schedule |
| :50 of 05–21 | `home.py order` — sorts Home hubs, demotes everything else | user script **`winswatch-order`** (`50 5-21 * * *`) |

Order matters: Kometa re-promotes its scheduled collections and appends new ones at the **end** of the hub list, so
ordering has to run after it — and hourly, because Shortlist re-promotes at unpredictable times.

## 3. Working on it

```bash
cd ~/projects/homelab/unraid                       # branch winswatch-posters (not merged, not pushed)
scripts/winswatch/.venv/bin/python -m pytest scripts/winswatch/tests -q    # 118 tests
bash scripts/winswatch/deploy.sh                   # rsync scripts + kometa/overlays/winswatch + kometa/collections
python3 scripts/winswatch/hostexec.py run <job>    # run a host job, waits for "=== exit N ==="
```

Host jobs (`scripts/winswatch/host/jobs/`): `nightly` · `order` · `check` · `days-left` · `kometa-prod-collections` ·
`kometa-prod-overlays` · `kometa-prod-operations` · `kometa-lab*` · `lab-media` · `us-create-order` (one-off).
Output of the last run is always `/mnt/nastower/appdata/scripts/winswatch/host/last.log`; `order`/`check` also tee to
`host/order.log` / `host/check.log`.

Every script takes `--sections` and `--dry-run`. **Always dry-run against 1,2 first.** Kometa's own log:
`/mnt/nastower/appdata/Kometa/config/logs/meta.log`.

### Changing the look
- Poster overlays: edit `gen_assets.py` (PNGs) / `gen_overlays.py` (YAML) → `python3 gen_assets.py && python3 gen_overlays.py`
  → deploy → `hostexec.py run kometa-prod-overlays`. Prove it on the lab first if the lab libraries still exist.
- Home rotation: edit `scripts/winswatch/home_calendar.yml` → `python3 gen_home.py` → commit both → deploy →
  `run kometa-prod-collections` → `run order`.
- Collection cards: `gen_cards.py` (theme names/emoji are derived from `gen_home.THEMES`, don't duplicate them) →
  `python3 gen_cards.py` → deploy → `run nightly` (or just `home.py cards`).
- Row order / which rows are on Home: `ww/plexhome.py` `FIXED_TOP`/`desired_order` and spec §1.

### The health check
`home.py check` (runs last in the nightly, or `hostexec.py run check`) compares our output against the systems of record:
DaysLeft labels vs Maintainerr membership, air-date labels vs Sonarr, score coverage, REQUESTED labels, promoted Home
rows vs the expected order, per-user rows vs the user list, cards vs the upload cache. **Non-zero exit on any FAIL.**
Read it first when something looks wrong — it names the broken link.

## 4. Things that have actually broken

1. **Renaming a Plex object breaks consumers that match on its name.** Twice: `ww/plexhome.py` read stale hub titles from
   `/hubs/sections/N/manage` (fixed — titles resolved from the section's collections), and renaming the Leaving
   collections silently stopped `days_left_label.py`, which killed every LEAVING plate (fixed — it matches Maintainerr's
   media *type* now). **Spec §10 is the checklist: grep before you rename.**
2. **Kometa's `mass_user_rating_update: mdb` rounds to whole numbers.** It writes through `/:/rate`, and plex.tv's sync
   echoes the value back rounded (7.3 → 7.0 → every poster shows a multiple of 10). `scores.py` owns that slot instead,
   via `editField('userRating', v, locked=True)`. Keep the Kometa key commented out.
3. **Shortlist deletes collections it thinks are its orphans** — any label-less collection whose last 64 characters are
   zero-width. Our per-user rows use a 40-char marker for that reason (`home.row_title`, enforced with a raise).
4. **`collection_order` is invalid on a Kometa smart collection** and silently fails the whole collection. That's what
   kept Halloween, Date Night and Sunday Slow Burn off Home for months before anyone noticed.
5. **`group` and `queue` can't be used on the same Kometa overlay**, and a definition's `overlay:` block does not merge
   into its template's — that's why codec chips are pre-rendered row PNGs.
6. **plex_search on a label that doesn't exist fails the whole overlay.** Every label search carries
   `validate: false` + `ignore_blank_results: true`.
7. **MDBList's free tier is 1000 calls/day** and `scores.py` shares the key with Kometa. A 429 blanks scores for the day.
8. **Overseerr's Plex scan** was dead 2025-11 → 2026-09-22 (it held a plex.direct hostname its container couldn't
   resolve); requests had no `ratingKey`/`mediaAddedAt`, so `home.py requested` falls back to matching by tmdb guid and
   windowing on the item's Plex `addedAt`. Fixed by pointing Overseerr at `192.168.0.20` + SSL off and restarting it.
9. **`hostexec.py` shares one `job.sh` / `last.log`** — two concurrent host jobs clobber each other. Run them serially.

## 5. Preroll

A bumper plays before every **movie** (never episodes, never on resume): `/mnt/user/appdata/Plex-Media-Server/prerolls/winswatch-preroll.mp4`,
pointed at by the Plex setting `CinemaTrailersPrerollID` = `/config/prerolls/winswatch-preroll.mp4` (the container's view of the same
path). Swap it by dropping a new file there; disable it by blanking that preference:
`curl -X PUT "$PLEX_URL/:/prefs?CinemaTrailersPrerollID=&X-Plex-Token=$PLEX_TOKEN"`. The current one is 8 s, 1920×1080 h264/aac,
generated from a photo of Win with 0.4 s fades top and tail.

## 6. Video preview thumbnails (BIF)

Enabled 2026-09-22: `GenerateBIFBehavior=scheduled`, `ButlerTaskGenerateMediaIndexFiles=true`,
`GenerateIndexFilesDuringAnalysis=true` (new items get them at scan), frame interval 2 s, keyframes only, hardware
accelerated. Generated in the butler window, set to **05:00–08:00** (server clock): clear of the Monday 03:00 appdata backup, the
03:40 mover and the 04:30 nightly, overlapping only Kometa's ~16-minute run, which is API-bound while this is QSV-bound. Files land in `appdata/Plex-Media-Server/Library/.../Media/` — the appdata share is
`use_cache: prefer` on the 1 TB NVMe pool (596 GB free), so they stay on the cache pool and never touch the array.
Expect ~45 GB for the current 3,200 hours. Turn it off with `GenerateBIFBehavior=never`; delete the existing files by
removing the per-item `Contents/Indexes` folders.

The weekly **Appdata.Backup** (Mondays 03:00, containers stopped, then `backup_appdata` zips + rclones to Cloudflare R2)
excludes Plex's regenerable dirs so those 45 GB never reach the backup — `containerSettings → Plex-Media-Server → exclude`
in `/boot/config/plugins/appdata.backup/config.json` lists `Library/Application Support/Plex Media Server/Media` and
`…/Cache` (set 2026-09-22; a timestamped `.bak` of the config sits beside it). The library database, watch history and
settings live in `Plug-in Support/Databases` and `Preferences.xml` and are still backed up.

## 7. Credentials and access

- Scripts read `/mnt/nastower/appdata/scripts/winswatch/.env` (`PLEX_URL/TOKEN`, `MDBLIST_API_KEY`, `SONARR_*`,
  `OVERSEERR_*`, `TZ=America/Chicago`). `deploy.sh` creates it from Kometa's `.env` only when missing.
- Unraid management agent: `~/.config/nastower/api_token` (bearer) — container state, logs, user-script execution.
- Overseerr API key: `json.load(open('/mnt/nastower/appdata/overseerr/settings.json'))['main']['apiKey']`.
- Maintainerr API: unauthenticated on the LAN. Shortlist API: owner session (CSRF header needed for writes).
- No SSH to the server. Host commands go through `hostexec.py` → the `winswatch` user script.
