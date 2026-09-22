# Wins Watch Home — design

Decided with Chase on 2026-09-21 on the mock https://claude.ai/artifact/36ETWc5YKNEJBELc5qXjEF. Scope: the Home screen a shared
user sees in the Plex apps. Nothing else (library tabs, collections browsing) is a goal. Builds on the poster work in
`2026-09-18-wins-watch-posters-design.md` (same repo, same scripts tree, same nightly hook).

## 1. Rows

Plex renders Home as Plex's own pinned rows (Continue Watching …) then the **Movies block** then the **TV Shows block**. We
control the row set and the order *inside* each block; we cannot interleave the two blocks. Per block, top to bottom:

| # | Movies | TV Shows | Owner | Order of items |
|---|---|---|---|---|
| 1 | ✨ Movies for you | ✨ Shows for you | Shortlist (per person) | Shortlist rank |
| 2 | 🔥 Trending Movies | 🔥 Trending Shows | Kometa (`mdblist_list`, existing) | list order |
| 3 | 📥 New Movies · Your Requests | 📥 New Shows · Your Requests | **ours**, per person (§3) | newest first, requests woven in |
| 4 | 👥 Popular Movies on Wins Watch | 👥 Popular Shows on Wins Watch | Shortlist (shared) | Shortlist rank |
| 5 | ⏳ Movies Leaving Wins Watch | ⏳ Shows Leaving Wins Watch | Maintainerr collection (renamed) | days left, soonest first |
| 6 | today's shelf 1 | today's shelf 1 | Kometa smart collection (§2) | random, reshuffled nightly |
| 7 | today's shelf 2 | today's shelf 2 | Kometa smart collection (§2) | random, reshuffled nightly |
| 8 | 🎯 Because you watched … | 🎯 Because you watched … | Shortlist (per person) | Shortlist rank |

Rules:
- **Emoji on every row**, one fixed icon per row, never changing: ✨ 🔥 📥 👥 ⏳ 🎯 for the fixed rows; themes as listed in §2.
- **Library word only where the name would otherwise repeat** (rows 1–5). Theme names are unique per library and carry none.
- **Row size 30–40** where the source has that many (Trending, Popular, themes, New); Leaving and personal rows show whatever they
  have. Random shuffle applies **only** to the theme shelves and seasonal (rows 6–7); every other row keeps its meaningful order.
- Row 5 disappears when Maintainerr has nothing expiring in that library (today true for TV). Rows 1/8 disappear for a user with no
  history (Shortlist's cold-start rule).
- Gone from Home: Plex's own Recently Added, Kometa stock charts (IMDb/TMDb Popular/Top Rated/Trending, genre, network, streaming,
  universe, franchise …), `Just Dropped` and `Raunchy Comedy` as always-on rows (both join the rotation pool), the other always-on tone rows, Agregarr's `{name}'s requests` and `My Requests`
  (folded into row 3). They stay as library collections where they already exist; only `visible_home` / `visible_shared` change.

## 2. Rotating shelves

Pool (existing Kometa tone rows, renamed only by adding the emoji; filters unchanged unless noted):

- Movies: 💥 Adrenaline Rush · 🕵️ Crime Files · 🚀 Sci-Fi Odyssey · 💎 Hidden Gems · 💘 Love & Laughs · 🌀 Mind Benders ·
  📰 Based on a True Story · 🎬 Director's Spotlight · 🍿 Fresh Picks · 🍺 Raunchy Comedy (10; Raunchy Comedy moves from owner-only
  Home into the pool)
- TV: 🪐 Worlds Beyond · 🏔️ Peak TV · 🚔 Crime Beat · 🛋️ Comfort Binge · 📺 Just Dropped (5, promoted from always-on to the pool),
  plus 🎢 Edge of Your Seat and 🎨 Not Just Cartoons **retuned** — today their `smart_filter` matches zero shows (Plex genre names
  differ from the file); the implementer inspects the library's actual genre list and rewrites the filters so each returns ≥ 15 shows.

Calendar: a fixed 14-day table (week A / week B × Mon–Sun) in one YAML, two themes per library per day; no theme two days running;
every theme appears at least twice a fortnight. Kometa expresses it as `visible_home: weekly(...)` on each collection, generated from
the table by `gen_home.py` so the table is the source of truth. Reshuffle: the smart filter sorts `random` (Plex re-sorts a smart
collection on every fetch, so a friend sees a fresh order each visit; no `collection_order` on smart collections — that key is what
has been silently failing Halloween / Date Night / Sunday Slow Burn since they were written).

Weekend extras (Movies only): 🍷 Date Night Fri+Sat, ☕ Sunday Slow Burn Sun — they take shelf 2's slot on those days.
Seasonal (Kometa, existing files, fixed): 🎃 Halloween Sep 15–Oct 31, 🎄 Christmas Nov 1–Dec 31, 💘 Valentine's Feb 1–14,
🏆 Awards Season Jan 1–Mar 15 — a seasonal row takes shelf 1's slot for its window. Shortlist's Seasonal template stays off.

## 3. New · Your Requests (ours)

One Plex collection per user per library, rebuilt nightly by `scripts/winswatch/home.py`:

- Items: the 40 most recently added titles in that library (top level: movies / shows), newest first, with the user's own Overseerr
  requests from the last 90 days woven in — every 4th slot starting at slot 2, remaining requests appended. A request that has
  landed is the real Plex item; a request still pending is skipped (Plex collections hold only library items — the mock's
  "on the way" tile is not possible).
- Naming: `📥 New Movies · Your Requests` / `📥 New Shows · Your Requests`, made unique per user the way Shortlist does it
  (trailing zero-width characters) so Plex accepts one per user.
- Visibility: the Shortlist mechanism verbatim — the collection gets label `winswatch_<userslug>`; every *other* account's share
  filter gets `label!=winswatch_<userslug>` **merged** into its existing `filterMovies` / `filterTelevision` (never overwritten —
  Shortlist and Agregarr also write those filters). Plex ≥ 1.43.2 required (server is 1.43.4). Owner sees all rows on the library
  shelf by design (no share with self); managed Home profiles get the same treatment Shortlist gives them.
- Order in Plex: `collectionSort` = custom, items added in the order above; Plex keeps insertion order. Promoted to the user's Home
  (hub `promotedToSharedHome`) after the filters are in place.
- Overseerr: `requestedBy` = the Plex account id mapped through Overseerr's `/user` list; `createdAt ≥ now − 90 d`; media status
  available (5) or partially available (4).

## 4. REQUESTED poster badge

Server-wide (a poster is one image for everyone). Top-level items only (movies, shows — never seasons/episodes). Same plate as NEW
(58 px Avenir Black, radius 15, padding 18, top-left 40/40), fill `#a78bfa` (the DV chip purple), ink `#120a2a`, text `REQUESTED`.
Precedence: **any top-edge tab suppresses every badge** — a title showing LEAVING, NEW EP …, RETURNS … never also shows REQUESTED or
NEW (the bare ended/canceled edge lines carry no text and do not count as tabs). Below that, REQUESTED › NEW. Implementation:
NEW and REQUESTED share Kometa group `ww_tl` (REQUESTED weight 20, NEW weight 10); both carry the exclusion
`label.not: [DaysLeft_1..30, NewEp_*, ReturnsIn_*, Returns_*]` (`validate: false`) so a tab wins outright. Source: label `Requested` written by `home.py` for any title that
has an Overseerr request (any user) whose media became available within the last **30 days**; removed after that so posters
don't carry it forever. Kometa `movies.yml` / `shows.yml` gain `ww_requested` (`plex_search: {all: {label: Requested}}`,
`validate: false`); NEW on shows stays off (a show with a request shows REQUESTED, nothing else changes).

## 5. Collection cards

Every Home row gets a generated poster (`kometa/overlays/winswatch/cards/<slug>.png`, 1000×1500) from one template: row emoji +
name set in Bricolage Grotesque 800 on a two-tone plate, Wins Watch paw top-right, tint by row kind (personal blue ring, trending
violet, new blue, popular gold, leaving red, themes slate, seasonal per season). Kometa rows use `file_poster`; Shortlist rows get
theirs through Shortlist's poster setting (`poster.mode`) if it accepts a file/URL per row, otherwise `home.py` uploads the PNG to
the collection nightly after Shortlist's run (Shortlist runs 03:30, ours 04:30). Maintainerr's collections likewise.

## 6. Row order inside a block

Kometa cannot order hubs. `home.py` ends by ordering each library's promoted hubs with Plex's manage endpoints
(`PUT /hubs/sections/{id}/manage/{hubId}/move?after=…`) to the §1 order, matching hub titles by prefix (the per-user rows are
matched by their label). Anything promoted that is not in §1 is demoted (`promotedToSharedHome=0`) — that is how the stock charts
leave Home without deleting them.

## 7. Shortlist settings (per row, Rows → Edit)

- Movies/Shows for you: sources = TMDB discover-by-taste + TMDB recommendations; rebuild every 8 days (default); size 40.
- Because you watched: sources = TMDB similar only; **seed window 3**; rebuild daily; size 30.
- Popular on Wins Watch: rename; size 40.
- Row names as §1 (emoji + library word). Chase's own account first (Chase_Test), everyone else after the first comparison.

## 8. Nightly order

All times are the **server clock, which is UTC-7** (the Unraid host and the Kometa container both run 2 h behind
America/Chicago; `home.py` itself computes "today" in Chicago, and the two dates agree throughout this window).

03:30 Shortlist (then every 30 min) · 04:30 `winswatch` user script: `scores.py` → `airdates.py` → `home.py requested` →
`home.py rows` → `home.py cards` · ~04:40 `update_days_left` (Maintainerr DaysLeft labels) · 05:00 Kometa (collections →
overlays → operations; ~17 min) · **`winswatch-order` user script hourly at :50: `home.py order`** (Shortlist rebuilds rows and
re-promotes hubs at odd times — a rebuild was seen at 22:30 the first night — so the order is re-asserted every hour; a pass is a
few API calls).

Kometa runs after the 04:30 script so the REQUESTED badge and the theme calendar are current on the same morning. Hub
order runs *after* Kometa (Task 5 finding): Kometa re-promotes every collection whose schedule matches and appends any
newly promoted hub at the end of the list, so an order pass before it would be undone. `order` demotes whatever Kometa
promoted outside today's pair (week A/B narrowing) and Plex's own Recently Added.

## 9. Not doing

No Trakt (VIP-only API since Aug 2026), no LLM, no Shortlist rewatch/unstarted/seasonal rows, no per-user poster badges, no changes
to the library tabs beyond `visible_*` flags, no deleting existing collections.
