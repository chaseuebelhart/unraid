# Wins Watch poster overlays — design

**Status:** decided (visual), ready for build plan
**Reference:** interactive lab at https://claude.ai/artifact/4sG9CBJQuovfe8FpZfUTTD (Posters → Winner, Go-live check)
**Owner tool:** Kometa. Agregarr and Shortlist do not touch posters.

## 1. Goal

Replace today's Kometa overlay stack (ratings ×3, DV/HDR + Atmos pills, streaming logo, status banner, ribbons, stinger "S", DaysLeft text) with one calm, brand-consistent layout that answers four viewer questions per poster — *what format, how good, when's more coming, is there something after the credits* — plus NEW and LEAVING when they apply. Nothing else on the art.

Non-goals: per-user artwork (Plex has one poster per item), collection art, Home row order, Agregarr/Shortlist changes. Those are separate specs.

## 2. The decided layout

Canvas: Plex poster 1000 × 1500 (2:3). Episode still 1000 × 562 (16:9). All sizes below are in canvas px; `u` = 10 px (1% of poster width).

### 2.1 Movies

| Zone | Content | Spec |
|---|---|---|
| Bottom bar | fade, "a tinge higher" | full-width PNG, alpha gradient: transparent at top → 35 % black at 30 % → 92 % black at 72 % → bottom. Height 240 px. Bar content sits in the bottom ~110 px. |
| Bar, left → right | codec chips | one pre-rendered row PNG per video/HDR/audio combination (`chip_<video>_<hdr>_<audio>.png`, 168 rows, `group: ww_chips`, weight = video·1000 + HDR·100 + audio), 46 px Avenir Black, 0.1 em tracking, 30 px gaps. Kometa forbids `group` + `queue` on one overlay and does not merge a definition's `overlay:` block into its template's, so text chips are not possible. Detection: `resolution.regex`, `hdr`, `has_dolby_vision`; audio `audio_track_title.regex` OR `filepath.regex`; DV·HDR and HDR10+ require the filename token. |
| Bar, right end | gauge | half-circle arc PNG (§3.1), 220 × 130, number `<<user_rating%>>` centered in the arc at 62 px, ratings count under it at 31 px (`1.5M RATINGS`). Gauge may rise ~60 px above the bar's dark region; the PNG carries its own halo. |
| Top edge | status (shows only) / leaving | see §2.2, §2.4 |
| Top-left | NEW | light-blue tag `#5ac8fa`, ink `#06131c`, 58 px, radius 15, when added ≤ 14 days. **Never shown while the title is on the delete list.** |
| Top-right | after-credits | reel: 95 px circle, 72 % black fill, 6 px gold `#f5c518` ring, inner dotted gold ring. From `mediastinger`. |

Unrated (no MDBList score): bar shows codecs only; no gauge, no number, no count.

### 2.2 Shows (series level)

Same as movies except:
- **No codec chips.** Bar left carries the **streaming service / network name** in its brand color (§4.2). Unknown service → white.
- **Status edge + tab** at the top edge, left-aligned at x = 40:
  - airing ≤ 7 days: `NEW EP WED`; 8–30 days: `RETURNS IN 13 DAYS`; 31–120 days: `RETURNS NOV` (month only); > 120 days: `RETURNS 2027`; no date: `RETURNS TBA`. Tab text is baked into the PNG (`tab_<Label>.png`) because Kometa cannot size a plate to its text; no drop shadow.
  - ended: gray `#5f6b7a` line, **no tab, no words**
  - canceled: red `#c62828` line, **no tab, no words**
  - tab: 42 px text, letter-spacing 0.1 em, padding 16/26/14, bottom corners radius 15.
- NEW on shows = title added ≤ 14 days (same as movies).
- Unknown network → no service name (Kometa has no network text variable).
- Reel applies to shows too if mediastinger has data.

### 2.3 Seasons

- NEW SEASON tag (same style as NEW) bottom-left when any episode added ≤ 14 days.
- Nothing else. No season number (Plex labels seasons), no codecs (vary per episode), no score.
- Real per-season art via Kometa `assets` so S2 ≠ S1 (separate task, same run).

### 2.4 Episodes

- **Top bar** (mirror of the fade, dark at top → transparent): codec chips left, runtime right (`<<runtime>>m`, 46 px white).
- Nothing at the bottom — Plex draws the title card and progress there.
- No NEW tag, no score.
- Kometa composes episode stills on a 1920×1080 canvas; `bar_top.png` is 1920×269, chips/runtime 88 px at offsets 77/65 (1.92× the poster values).

### 2.5 LEAVING (Maintainerr)

- Gold `#e8b84a` line across the top + **bookmark** tab at x = 40: `LEAVING 12 DAYS` (singular at 1), ink `#1a1200`, notched bottom (clip-path polygon), 42 px text, count in display font 52 px.
- **Precedence:** LEAVING replaces the status tab and line entirely while the `DaysLeft_N` label exists. When the label is removed, the status tab (or nothing) returns. NEW is suppressed while leaving.
- `bookmark_<n>.png` (30 files), count in 52 px. Precedence is one `topedge` group: bookmark 300+n > NEW EP 210 > RETURNS IN 205 > RETURNS 204 > canceled 110 > ended 100.

## 3. Score

### 3.1 Source and bands

- Number = **MDBList `score`** (their combined, vote-aware score), written nightly to Plex's *user* rating slot via the metadata edit endpoint (`editField('userRating', v, locked=True)`), never `/:/rate` — that path triggers a plex.tv ViewStateSync echo that rounds to whole numbers → Kometa reads it as `<<user_rating%>>`. Kometa's own `mass_user_rating_update: mdb` does the same thing; the script is preferred only because it also produces the vote-count labels in one pass (§5.1). Either is acceptable for day one.
- Critic slot: `mass_critic_rating_update: mdb_metacritic`; audience slot: `mdb_letterboxd` for movies, `mdb_trakt` for TV. Not drawn on the poster; shown on Plex detail pages.
- **Bands (solid arc color):** gray `#8a94a6` < 65 · white `#ffffff` 65–72 · light blue `#5ac8fa` 73–84 · **gold `#f5c518` ≥ 85** (gold applies to arc, track remainder at 38 % gold, number, and the ratings line).
- Below 85 the number is white; track remainder 14 % white.
- Vote floor: none needed — MDBList's `score` already discounts thin votes (Scary Movie 2025: average 67 → score 56).

### 3.2 Arc assets

101 PNGs `arc_00.png … arc_100.png`, 220 × 130, halo baked in (5.4 px dark under-stroke). Selected with `plex_all` + `filters: user_rating.gte/.lt` (Kometa 2.4.8's `value_filter` rejects `user_rating`) (Plex stores 0–10 with one decimal → exactly 101 buckets). Digit shadow not implemented. Generated by a script (§6), never hand-edited.

### 3.3 Ratings count

`{votes} RATINGS`, where votes = max(Letterboxd, IMDb, Trakt) vote count from MDBList, formatted `20K`, `1.5M`, `4.5M`. Written as a label `Votes_<bucket>` from 25 buckets (10K, 20K, 50K, 100K–900K, 1.0M–7.0M step 0.5M); nearest bucket; e.g. `Votes_1.5M`. One text overlay per bucket, all in the gauge queue below the arc.

## 4. Colors

### 4.1 Brand
- Brand light blue `#5ac8fa`; ink on it `#06131c`. Deep blue `#1b5e8a`. Gold `#f5c518` (score) / `#e8b84a` (leaving). Red `#c62828` = canceled only. Gray `#5f6b7a` = ended.

### 4.2 Codec chips (text color)
4K / 1080p / 720p / SD `#ffffff` · DV `#a78bfa` · DV·HDR `#c084fc` · HDR10+ `#fbbf24` · HDR `#e8b84a` · Atmos `#60a5fa` · DD+ Atmos `#7dd3fc` · TrueHD `#2dd4bf` · DTS:X `#f87171` · DTS-HD MA `#fb923c` · DTS `#ef4444` · DD+ `#4ade80` · DD `#a3a3a3` · AAC / FLAC / PCM / Opus `#9ca3af`.

### 4.3 Service names (shows)
Netflix `#e50914` · Prime Video `#00a8e1` · Apple TV+ `#f5f5f7` · HBO `#ffffff` · Max `#b535f6` · Hulu `#1ce783` · Disney+ `#5b9bff` · Paramount+ `#0064ff` · Peacock `#ffcf00` · FX `#ffffff` · Showtime `#ff2a2a` · AMC `#ffcc00` · CBS `#3b82f6` · NBC `#f37021` · ABC `#ffffff` · Fox `#3b82f6` · BBC `#ffffff` · Comedy Central `#ffc800` · Crunchyroll `#f47521` · Bravo `#8b5cf6` · Syfy `#a855f7` · The CW `#22c55e` · MGM+ `#f5c518` · Lionsgate+ `#ff8a00` · unknown `#ffffff`. Source: the same MDBList streaming lists Kometa's `streaming` default uses, plus TMDB network for non-streaming originals.

## 5. Data pipeline (nightly, before Kometa's 05:00 run)

All three are the same shape as the existing `scripts/maintainerr/pyscripts/days_left_label.py`: read a source, write Plex labels (and one rating field), idempotent, log one line per change.

### 5.1 `scores.py` — MDBList → Plex
For every movie and show: `GET https://api.mdblist.com/tmdb/{movie|show}/{tmdb_id}` → write `score` to user rating (÷10), set label `Votes_<bucket>` (remove other `Votes_*`). ~580 calls/night, under the 1,000/day free limit; cache policy = 7-day TTL in `cache/mdblist.json`; per-item errors are skipped (rating/labels untouched), not fatal.

### 5.2 `airdates.py` — Sonarr → Plex
For every show: next unaired episode date from Sonarr (`/api/v3/series`, `nextAiring`). Labels, exactly one per show: `NewEp_Mon…Sun`, `ReturnsIn_8…30`, `Returns_<Mon>`, `Returns_<YYYY>` (this year..+6), `Returns_TBA`; ended/canceled get no label (Kometa draws those edges from `tmdb_status`). Dates converted to `TZ` (America/Chicago) before bucketing.

### 5.3 `days_left_label.py` — Maintainerr → Plex (existing)
Unchanged. `DaysLeft_1 … DaysLeft_30`.

## 6. Kometa files

New directory `kometa/overlays/winswatch/`:

- `assets/` — 522 PNGs incl. `chip_*`/`chipl_*`, `tab_*`, `bookmark_*`, plus `bar_bottom.png`, `bar_top.png` (episodes), `arc_00…100.png`, `edge_{lightblue,deepblue,gold,gray,red}.png`, `reel.png`. All generated by `scripts/winswatch/gen_assets.py` (Pillow).
- `movies.yml`, `shows.yml`, `seasons.yml`, `episodes.yml` — hand-written, small.
- `generated/{gauge,topedge,status,chips_movies,chips_episodes}.yml` — emitted by `scripts/winswatch/gen_overlays.py`. Committed so the run is reproducible.

Precedence is expressed with `group` + `weight`: `DaysLeft_*` overlays weight 300, status overlays weight 200. NEW exclusion via `label.not: DaysLeft_1..30`; every label/network search carries `validate: false` + `ignore_blank_results: true` — without them one missing label fails the whole overlay (production night one).

`config.yml` changes: remove every current `overlay_files` entry for both libraries; add the files above; keep `mass_*_rating_update` per §3.1; keep `assets_for_all`; set `remove_overlays: true` for **one** run to strip the old stack, then back to `false`.

## 7. Test plan — small batch, live in Plex

Goal: see real posters in the Plex app on a phone and a TV, without touching the production libraries' art.

1. **Create a Plex library "Wins Watch Lab"** (type Movies) and "Wins Watch Lab TV" (type Shows), each pointing at a new folder on the array that contains **symlinks** to ~12 titles' folders: the ten from the lab page plus a 720p/SD file and an unrated new release. Same scanner/agent as production. Plex will match them fresh (separate rating keys, separate labels, separate posters), so nothing in production changes.
2. **`kometa/lab.yml`** — a second Kometa config with only those two libraries, pointing at the same `winswatch/` overlay files, `mass_*_rating_update` on, `reapply_overlays: false`.
3. Run the three label scripts against the lab section IDs (they take a `--sections` arg).
4. Run Kometa one-shot against the lab config:
   `python3 scripts/winswatch/hostexec.py run kometa-lab`
   (~1–2 minutes for 12 items). Lab items share GUIDs with production, so `scores.py` user ratings also land on the production copies (disclosed side effect; self-heals when production runs its own labels).
5. Review in Plex: the lab libraries show up like any other; open on TV and phone; screenshot anything off. Force states by editing labels in Plex's web UI (add `DaysLeft_3`, swap `Returns_Feb` for `NewEp_Wed`, add `Votes_4.5M`) and re-run step 4 — this is how every Go-live-check state gets a live look.
6. Iterate on assets/YAML until the lab matches the artifact's Winner row.
7. **Promote:** point production `config.yml` at the same files, run once with `remove_overlays: true`, then a normal run. Delete the lab libraries (Plex → delete library removes its posters/labels; the symlink folder goes too).

Rollback at any point: `remove_overlays: true` restores Kometa's backed-up originals; the old overlay files are still in git history.

## 8. Open questions (not blocking)

- Ratings count buckets: 28 is a guess; adjust after seeing the lab distribution.
- Service color for `HBO` vs `Max`: the network field says HBO, the streaming list says Max. Rule: network wins for network originals; streaming list only when no network.
- `RETURNS TBA` volume: if Sonarr lacks dates for many continuing shows, consider showing the deep-blue line only (no tab) for TBA.
