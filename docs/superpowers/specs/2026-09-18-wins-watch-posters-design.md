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
| Bar, left → right | codec chips | text, letter-spacing 0.1 em, 46 px font, colored per codec (§4), separated by 30 px. Video first (4K / 1080p / 720p / SD), then HDR flavor (DV / DV·HDR / HDR10+ / HDR), then audio (best track). |
| Bar, right end | gauge | half-circle arc PNG (§3.1), 220 × 130, number `<<user_rating%>>` centered in the arc at 62 px, ratings count under it at 31 px (`1.6M RATINGS`). Gauge may rise ~60 px above the bar's dark region; the PNG carries its own halo. |
| Top edge | status (shows only) / leaving | see §2.2, §2.4 |
| Top-left | NEW | light-blue tag `#5ac8fa`, ink `#06131c`, 58 px, radius 15, when added ≤ 14 days. **Never shown while the title is on the delete list.** |
| Top-right | after-credits | reel: 95 px circle, 72 % black fill, 6 px gold `#f5c518` ring, inner dotted gold ring. From `mediastinger`. |

Unrated (no MDBList score): bar shows codecs only; no gauge, no number, no count.

### 2.2 Shows (series level)

Same as movies except:
- **No codec chips.** Bar left carries the **streaming service / network name** in its brand color (§4.2). Unknown service → white.
- **Status edge + tab** at the top edge, left-aligned at x = 40:
  - airing within 7 days: light-blue `#5ac8fa` line (16 px) + tab `NEW EP WED` (ink `#06131c`)
  - returning ≤ 120 days: deep-blue `#1b5e8a` line + tab `RETURNS NOV 14`
  - returning > 120 days: deep-blue line + tab `RETURNS FEB 2027`
  - returning, no date: deep-blue line + tab `RETURNS TBA`
  - ended: gray `#5f6b7a` line, **no tab, no words**
  - canceled: red `#c62828` line, **no tab, no words**
  - tab: 42 px text, letter-spacing 0.1 em, padding 16/26/14, bottom corners radius 15, drop shadow.
- Reel applies to shows too if mediastinger has data.

### 2.3 Seasons

- NEW SEASON tag (same style as NEW) bottom-left when any episode added ≤ 14 days.
- Nothing else. No season number (Plex labels seasons), no codecs (vary per episode), no score.
- Real per-season art via Kometa `assets` so S2 ≠ S1 (separate task, same run).

### 2.4 Episodes

- **Top bar** (mirror of the fade, dark at top → transparent): codec chips left, runtime right (`<<runtime>>m`, 46 px white).
- Nothing at the bottom — Plex draws the title card and progress there.
- No NEW tag, no score.

### 2.5 LEAVING (Maintainerr)

- Gold `#e8b84a` line across the top + **bookmark** tab at x = 40: `LEAVING 12 DAYS` (singular at 1), ink `#1a1200`, notched bottom (clip-path polygon), 42 px text, count in display font 52 px.
- **Precedence:** LEAVING replaces the status tab and line entirely while the `DaysLeft_N` label exists. When the label is removed, the status tab (or nothing) returns. NEW is suppressed while leaving.

## 3. Score

### 3.1 Source and bands

- Number = **MDBList `score`** (their combined, vote-aware score), written nightly to Plex's *user* rating slot → Kometa reads it as `<<user_rating%>>`. Kometa's own `mass_user_rating_update: mdb` does the same thing; the script is preferred only because it also produces the vote-count labels in one pass (§5.1). Either is acceptable for day one.
- Critic slot: `mass_critic_rating_update: mdb_metacritic`; audience slot: `mdb_letterboxd` for movies, `mdb_trakt` for TV. Not drawn on the poster; shown on Plex detail pages.
- **Bands (solid arc color):** gray `#8a94a6` < 65 · white `#ffffff` 65–72 · light blue `#5ac8fa` 73–84 · **gold `#f5c518` ≥ 85** (gold applies to arc, track remainder at 38 % gold, number, and the ratings line).
- Below 85 the number is white; track remainder 14 % white.
- Vote floor: none needed — MDBList's `score` already discounts thin votes (Scary Movie 2025: average 67 → score 56).

### 3.2 Arc assets

101 PNGs `arc_00.png … arc_100.png`, 220 × 130, halo baked in (5.4 px dark under-stroke, digit shadow drawn by Kometa text `stroke_color` 3 px). Selected with `value_filter: user_rating.gte: 8.6, user_rating.lt: 8.7` etc. (Plex stores 0–10 with one decimal → exactly 101 buckets). Generated by a script (§6), never hand-edited.

### 3.3 Ratings count

`{votes} RATINGS`, where votes = max(Letterboxd, IMDb, Trakt) vote count from MDBList, formatted `20K`, `1.6M`, `4.6M`. Written as a label `Votes_1.6M` from ~28 buckets (100K … 900K step 100K; 1.0M … 7.0M step 0.5M; plus `<100K` shown as e.g. `20K` from 10K/20K/50K buckets). One text overlay per bucket, all in the gauge queue below the arc.

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
For every movie and show: `GET https://api.mdblist.com/tmdb/{movie|show}/{tmdb_id}` → write `score` to user rating (÷10), set label `Votes_<bucket>` (remove other `Votes_*`). ~580 calls/night, under the 1,000/day free limit; cache by `updated` field and only refetch weekly for items older than 90 days to leave headroom for Kometa's own MDBList calls.

### 5.2 `airdates.py` — Sonarr → Plex
For every show: next unaired episode date from Sonarr (`/api/v3/episode?seriesId=…` or calendar). Labels, exactly one per show: `NewEp_Mon…Sun` (≤ 7 days), `Returns_<Mon>` (≤ 120 days), `Returns_<YYYY>` (> 120 days), `Returns_TBA` (continuing, no date), `Ended`, `Canceled` (TMDB/Sonarr status). Also `Weekday` in the tab comes from the label, not computed by Kometa.

### 5.3 `days_left_label.py` — Maintainerr → Plex (existing)
Unchanged. `DaysLeft_1 … DaysLeft_30`.

## 6. Kometa files

New directory `kometa/overlays/winswatch/`:

- `assets/` — `bar_bottom.png`, `bar_top.png` (episodes), `arc_00…100.png`, `tab_plate_{lightblue,deepblue}.png`, `bookmark.png`, `edge_{lightblue,deepblue,gold,gray,red}.png`, `reel.png`. All generated by `scripts/winswatch/gen_assets.py` (Pillow).
- `queues.yml` — named queues: `bar_left` (chips, x from 40 stepping right, y 1400), `gauge` (x 830, y 1330 + count at y 1440), `top_edge` (x 40, y 0), `tl` (x 40, y 40), `tr` (x 960 right-aligned, y 40).
- `movies.yml`, `shows.yml`, `seasons.yml`, `episodes.yml` — hand-written, small.
- `generated/arcs.yml`, `generated/votes.yml`, `generated/status.yml` — emitted by `scripts/winswatch/gen_overlays.py`. Committed so the run is reproducible.

Precedence is expressed with `group` + `weight` inside the `top_edge` queue: `DaysLeft_*` overlays weight 300, status overlays weight 200, NEW overlay excluded via `filters: label.not: DaysLeft_*` (explicit, not just weight).

`config.yml` changes: remove every current `overlay_files` entry for both libraries; add the four files above; keep `mass_*_rating_update` per §3.1; keep `assets_for_all`; set `remove_overlays: true` for **one** run to strip the old stack, then back to `false`.

## 7. Test plan — small batch, live in Plex

Goal: see real posters in the Plex app on a phone and a TV, without touching the production libraries' art.

1. **Create a Plex library "Wins Watch Lab"** (type Movies) and "Wins Watch Lab TV" (type Shows), each pointing at a new folder on the array that contains **symlinks** to ~12 titles' folders: the ten from the lab page plus a 720p/SD file and an unrated new release. Same scanner/agent as production. Plex will match them fresh (separate rating keys, separate labels, separate posters), so nothing in production changes.
2. **`kometa/lab.yml`** — a second Kometa config with only those two libraries, pointing at the same `winswatch/` overlay files, `mass_*_rating_update` on, `reapply_overlays: false`.
3. Run the three label scripts against the lab section IDs (they take a `--sections` arg).
4. Run Kometa one-shot against the lab config:
   `docker run --rm -v /mnt/user/appdata/Kometa/config:/config kometateam/kometa --config /config/lab.yml --run --overlays-only`
   (~1–2 minutes for 12 items). From the Unraid web terminal.
5. Review in Plex: the lab libraries show up like any other; open on TV and phone; screenshot anything off. Force states by editing labels in Plex's web UI (add `DaysLeft_3`, swap `Returns_Feb` for `NewEp_Wed`, add `Votes_4.6M`) and re-run step 4 — this is how every Go-live-check state gets a live look.
6. Iterate on assets/YAML until the lab matches the artifact's Winner row.
7. **Promote:** point production `config.yml` at the same files, run once with `remove_overlays: true`, then a normal run. Delete the lab libraries (Plex → delete library removes its posters/labels; the symlink folder goes too).

Rollback at any point: `remove_overlays: true` restores Kometa's backed-up originals; the old overlay files are still in git history.

## 8. Open questions (not blocking)

- Ratings count buckets: 28 is a guess; adjust after seeing the lab distribution.
- Service color for `HBO` vs `Max`: the network field says HBO, the streaming list says Max. Rule: network wins for network originals; streaming list only when no network.
- `RETURNS TBA` volume: if Sonarr lacks dates for many continuing shows, consider showing the deep-blue line only (no tab) for TBA.
