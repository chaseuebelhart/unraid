# How Plex actually works (the parts we keep hitting)

Written 2026-09-22 from things learned the hard way on NASTower. Not a manual — the mental model and the API calls you
need to work on Wins Watch without breaking something. Operations for our stack are in `docs/wins-watch.md`.

Everything below assumes `PLEX_URL=http://192.168.0.20:32400` and `PLEX_TOKEN` from
`/mnt/nastower/appdata/scripts/winswatch/.env`. Add `-H "Accept: application/json"` to any call or you get XML.

---

## 1. The object model

- **Server → sections (libraries) → items.** Sections are numbered: **1 = Movies, 2 = TV Shows**. Everything is addressed
  by `ratingKey`, an integer unique per server, *not* stable across servers or restores.
- **Items nest**: show → season → episode, each its own ratingKey with `parentRatingKey` / `grandparentRatingKey`. A
  "top-level" item means a movie or a show — the thing that carries the poster people browse.
- **GUIDs** are the portable identity: `tmdb://157336`, `imdb://tt0816692`, `tvdb://…`. Match across systems (Overseerr,
  Sonarr, MDBList) on the GUID, never on the title. `GET /library/metadata/{key}?includeGuids=1`.
- **Labels** are free-text tags on an item, invisible to users, queryable in searches — the universal join key between
  our scripts and Kometa. Plex **title-cases new tags on creation** (`winswatch_x` → `Winswatch_x`) and matches them
  case-insensitively. Write with plexapi `item.addLabel/removeLabel`; after a removal, `item.reload()` before adding or
  the removed tag comes back.
- **Collections** are first-class objects with their own ratingKey, poster, sort title and *sort mode*
  (`collectionSort`: release / alpha / custom). Two kinds: **manual** (a fixed member list) and **smart** (a saved
  filter). A fresh collection returns its children alphabetically regardless of `collectionSort=custom` until you walk
  the items with `moveItem`.
- **Hubs** are the rows on Home and in a library's Recommended tab. A collection is not a row until it is *promoted*.
  `GET /hubs/sections/{id}/manage` lists the managed hubs with `promotedToOwnHome` (the owner's Home),
  `promotedToSharedHome` (everyone else's) and `promotedToRecommended`. plexapi: `section.managedHubs()`,
  `hub.move(after=…)`, `hub.updateVisibility(home=, shared=, recommended=)`.
  - **A hub only exists in that list while it is promoted** — you cannot pre-position tomorrow's row.
  - **The manage endpoint reports the title the hub had when it was promoted.** Rename the collection and this list goes
    stale; resolve current titles from `section.collections()` by ratingKey instead.
  - Home renders Plex's own pinned rows (Continue Watching…), then the Movies block, then the TV block. Order *within*
    a block is ours; the blocks themselves are not.

## 2. Where it keeps things on disk

Under `appdata/Plex-Media-Server/Library/Application Support/Plex Media Server/` (19 GB here):

| Directory | Size | Precious? |
|---|---|---|
| `Plug-in Support/Databases/` | ~1 GB | **Yes** — the library, watch history, ratings, users, collections. This *is* your server. |
| `Preferences.xml` | tiny | **Yes** — server identity, token, every setting |
| `Metadata/` | 13 GB | No — posters, art, metadata bundles; re-downloadable |
| `Media/` | 2 GB → ~45 GB | No — derived artifacts incl. video preview thumbnails (BIF) |
| `Cache/` | 1.6 GB | No — transient |

Practical consequence: back up Databases + Preferences religiously, exclude `Media` and `Cache` (we do — see
`wins-watch.md` §6). A restore rebuilds the rest on its own time.

## 3. Settings (`/:/prefs`)

Read: `GET /:/prefs` → `MediaContainer.Setting[]`, each with `id`, `value`, `type`, and `enumValues` for pick-lists.
Write: `PUT /:/prefs?<id>=<url-encoded value>`. No restart needed; the value is live immediately and lands in
`Preferences.xml`. Ones that matter to us:

- `GenerateBIFBehavior` — `never` / `scheduled` / `asap`: video preview thumbnails (scrubbing). `scheduled` = only in
  the butler window; `asap` = as soon as an item is analysed, which is how you burn through a backlog.
  `GenerateBIFFrameInterval` (seconds between frames, 2 default), `GenerateBIFKeyframesOnly`, and
  `GenerateIndexFilesDuringAnalysis` (new items get thumbnails at scan time).
- `ButlerStartHour` / `ButlerEndHour` — the nightly maintenance window, and the only time `scheduled` tasks run.
  `ButlerTask*` booleans switch individual jobs on. Trigger one now: `POST /butler/{TaskName}` e.g.
  `POST /butler/GenerateMediaIndexFiles`. It runs outside the window when triggered by hand.
- `CinemaTrailersPrerollID` — path (as the *container* sees it) to a video played before movies only, never episodes,
  never on resume. Blank it to disable.
- `GenerateIntroMarkerBehavior` / `GenerateCreditsMarkerBehavior` — skip-intro / skip-credits detection.
- `HardwareAcceleratedCodecs` — QSV on this box; also speeds thumbnail generation.

## 4. Ratings — the trap that cost us a day

Plex has three rating slots per item: **critic** (`rating`), **audience** (`audienceRating`) and **user**
(`userRating`). We use the user slot for the Wins Watch score.

- Writing through `PUT /:/rate?key=…&rating=7.3` triggers a plex.tv ViewStateSync round-trip that **echoes the value
  back rounded to a whole number** a few seconds later. Every score becomes a multiple of 10 on the poster.
- Writing through the metadata edit endpoint keeps the decimal:
  `item.editField("userRating", 7.3, locked=True)`. Kometa's `mass_user_rating_update` uses the `/:/rate` path, so we
  keep that key commented out and let `scores.py` own the slot.
- `locked=True` matters: an unlocked field is fair game for the next metadata refresh.

## 5. Sharing and per-user visibility

Per-user rows are not a Plex feature; they are a **share filter** trick (Shortlist's invention, we copied it):

- Every shared user has `filterMovies` / `filterTelevision` strings on their share of this server. Grammar:
  `label!=a,b,c` — comma-separated values, conditions joined with `&` (AND) or `|` (OR). A `label!=` condition ANDed in
  hides anything carrying those labels *from that user only*.
- So: label a collection `Winswatch_<slug>`, then add `label!=Winswatch_<slug>` to **every other** user's filter. The
  owner has no share with themselves, so the owner sees all of them on the library shelf (not on Home).
- **Always merge, never overwrite** — Shortlist writes these too. Parse, add, re-serialise, and refuse to write anything
  that doesn't round-trip byte-for-byte.
- plexapi's `updateFriend` no longer writes these (plex.tv answers 404). The working call is
  `PUT https://plex.tv/api/users/{plexAccountId}?filterMovies=…&filterTelevision=…` with the owner token.
- **The server debounces sharing-change pushes** (~1 per 6 s, the rest dropped). Write all users, wait ~10 s, then send
  one more no-op PUT, or only the first user's filter actually takes effect.
- Plex ≥ 1.43.2 is required for label exclusions to be enforced at all. This server is 1.43.4.
- Titles must be unique per collection, so per-user rows are distinguished by a run of **zero-width characters**
  appended to the title. Shortlist encodes the Plex account id that way — and its "orphan sweep" **deletes any
  label-less collection whose last 64 characters are all zero-width**, which ate all 16 of our rows the first night.
  Ours use a 40-char marker for that reason.

## 6. Posters and overlays

- Item posters: `POST /library/metadata/{key}/posters` (plexapi `item.uploadPoster(filepath=|url=)`). The current one is
  `item.thumb`; alternatives from agents live at `/library/metadata/{key}/posters`.
- Kometa composites overlays onto the *source* poster and uploads the result; it keeps the original so `remove_overlays`
  can restore it. It will not re-composite an item whose overlay set is unchanged, which is why a poster change needs
  the underlying label/asset to change too.
- Episode stills are composed on a **1920×1080** canvas, posters on **1000×1500** — any overlay geometry has to be
  scaled per level (we use 1.92×).

## 7. Searching and filtering from the API

- `GET /library/sections/{id}/all?type=1|2|3|4` — 1 movie, 2 show, 3 season, 4 episode. `X-Plex-Container-Start/Size`
  paginate; `totalSize` comes back in the container.
- Filters are query params: `label=<id>`, `genre=<id>`, `userRating>=7.3`, `addedAt>=…`. **Tag filters want the tag's
  numeric id**, not its name — fetch ids from `/library/sections/{id}/label` or `/genre`. plexapi's
  `section.search(filters={...})` handles that mapping for you.
- Sorting: `sort=addedAt:desc`, `titleSort`, `random`. Smart collections re-sort on every fetch when sorted randomly,
  which is how the rotating shelves look fresh without anyone rebuilding them.
- Live sessions: `GET /status/sessions` (`MediaContainer.size` = how many people are watching — check before anything
  disruptive). Background work: `GET /activities` shows type, subtitle and a progress %.

## 8. Things that bite

1. `/:/rate` rounds. Use `editField`. (§4)
2. Renaming a collection breaks anything matching on its name — the manage-hub list, other services' scripts, Kometa
   YAML. Grep before renaming.
3. Removing then re-adding a label in the same object without `reload()` silently re-adds the old value.
4. A fresh collection ignores `collectionSort=custom` until you `moveItem` the members into place.
5. Tag filters need ids, not names.
6. Smart-collection order cannot be set (`collection_order` is invalid on them in Kometa and fails the whole
   collection silently).
7. Share-filter writes are debounced; batch them and nudge.
8. plex.direct hostnames are real DNS names that resolve to LAN IPs — but a container with its own resolver may not see
   them, and Plex caches the URI it learned at startup (Overseerr scanned nothing for ten months because of this).
9. Butler tasks only run inside the window unless you POST them by hand.
10. The Unraid host clock here is **UTC-7** while our scripts think in America/Chicago; anything comparing "today"
    across both needs care after 22:00 local.
