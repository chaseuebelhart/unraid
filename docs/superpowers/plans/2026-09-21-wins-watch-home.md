# Wins Watch Home Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every shared user the Home screen in the spec: 8 rows per library block in a fixed order, two rotating theme shelves a day, a per-user "New · Your Requests" row, a REQUESTED poster badge, one collection-card system, and a nightly that keeps it all in order without the four services fighting.

**Architecture:** A calendar YAML is the single source of truth for the rotation; `gen_home.py` renders it into two Kometa collection files. A new `home.py` (subcommands `requested`, `rows`, `cards`, `order`) runs in the existing `winswatch` nightly and owns everything Kometa cannot: Overseerr → `Requested` labels, per-user collections with Shortlist-style label exclusions, card uploads, and hub ordering/demotion through Plex's manage-hub API. Agregarr is retired (its only live feature, per-user request rows, is replaced by row 3). Shortlist keeps its three rows with settings changed in its UI.

**Tech Stack:** Python 3.12 (venv at `scripts/winswatch/.venv`), plexapi 4.18 (`ManagedHub`, `MyPlexAccount.updateFriend`), requests, PyYAML, Pillow, pytest; Kometa 2.4.8 collection files; Overseerr API v1; Shortlist web UI; Unraid User Scripts.

**Spec:** `docs/superpowers/specs/2026-09-21-wins-watch-home-design.md` (this plan argues from it; read §1–§8 first). Poster work it builds on: `docs/superpowers/specs/2026-09-18-wins-watch-posters-design.md`.

## Global Constraints

- Repo `~/projects/homelab/unraid`, branch `winswatch-posters` (continue on it; do not merge/push). Scripts live in `scripts/winswatch/`, run with `scripts/winswatch/.venv/bin/python`; tests `scripts/winswatch/.venv/bin/python -m pytest scripts/winswatch/tests -q` (26 pass today — keep it green).
- Server access only through: NFS `/mnt/nastower/appdata` (rw), Plex API `PLEX_URL`/`PLEX_TOKEN` from `/mnt/nastower/appdata/scripts/winswatch/.env`, Overseerr API key = `json.load(open('/mnt/nastower/appdata/overseerr/settings.json'))['main']['apiKey']` at `http://192.168.0.6:5055`, host jobs via `python3 scripts/winswatch/hostexec.py run <job>`, Kometa lab render `run kometa-lab` (sections 4 = Wins Watch Lab, 5 = Wins Watch Lab TV). `deploy.sh` rsyncs scripts + `kometa/overlays/winswatch` to the server.
- **Production libraries are sections 1 (Movies) and 2 (TV Shows). Nothing writes to them until Task 7.** Every script takes `--sections` and refuses to run without it; `--dry-run` prints and writes nothing.
- Row names (exact, emoji included): `✨ Movies for you` / `✨ Shows for you`, `🔥 Trending Movies` / `🔥 Trending Shows`, `📥 New Movies · Your Requests` / `📥 New Shows · Your Requests`, `👥 Popular Movies on Wins Watch` / `👥 Popular Shows on Wins Watch`, `⏳ Movies Leaving Wins Watch` / `⏳ Shows Leaving Wins Watch`, `🎯 Because you watched {seed}`. Themes: `💥 Adrenaline Rush`, `🕵️ Crime Files`, `🚀 Sci-Fi Odyssey`, `💎 Hidden Gems`, `💘 Love & Laughs`, `🌀 Mind Benders`, `📰 Based on a True Story`, `🎬 Director's Spotlight`, `🍿 Fresh Picks`, `🍺 Raunchy Comedy`, `🪐 Worlds Beyond`, `🏔️ Peak TV`, `🚔 Crime Beat`, `🛋️ Comfort Binge`, `📺 Just Dropped`, `🎢 Edge of Your Seat`, `🎨 Not Just Cartoons`, `🍷 Date Night`, `☕ Sunday Slow Burn`, `🎃 Halloween`, `🎄 Christmas Movies`, `💘 Valentine's Picks`, `🏆 Awards Season`.
- Row size: `limit: 40` on every smart collection; per-user New rows 40 + requests; REQUESTED window 30 days; requests window 90 days.
- Smart collections never carry `collection_order` (Kometa rejects it — that is the bug that killed Halloween / Date Night / Sunday Slow Burn). `sort_by: random` is the reshuffle.
- Share filters are **merged**, never overwritten: read the user's current `filterMovies`/`filterTelevision`, add our `label!=` values, keep every other value (Shortlist's `shortlist_*` exclusions and anything else) untouched.
- Overlay precedence: any top-edge tab (labels `DaysLeft_*`, `NewEp_*`, `ReturnsIn_*`, `Returns_*`) suppresses REQUESTED and NEW; REQUESTED beats NEW.

## Service overlap (read before Tasks 5–7 — this is the race-condition map)

| When (server clock, America/Chicago) | Who | Touches |
|---|---|---|
| 00:00 / 12:00 | Maintainerr collection handler | membership of `Movies/Shows Leaving Soon`; overlays **off** (`overlay_settings.enabled=0`) |
| 03:00, every 30 min | **Agregarr** (retired in Task 7) | today: hub promotion/order for 34 hubs, per-user request collections, overlay job (inactive) |
| 03:30 | Shortlist | its collections, **share filters (merge)**, promotes its hubs (new BYW hubs land at the end of the block) |
| 04:30 | `winswatch` user script → `nightly.sh` | `scores.py` → `airdates.py` → `home.py requested` → `home.py rows` → `home.py cards` |
| ~04:40 | `update_days_left` user script | `DaysLeft_N` labels |
| 05:00 | Kometa | collections (theme `visible_home` per calendar → promotes/demotes theme hubs), overlays (REQUESTED/NEW read labels written at 04:30) |
| 05:45 | `winswatch-order` user script (new, Task 7) → `home.py order` | hub order + demotion of anything not in §1 — **after** Kometa, so today's shelves are in place when it runs |

Rules that keep it race-free: only `home.py order` moves hubs and it runs last; only Shortlist and `home.py rows` write share filters and both merge; Kometa only toggles promotion of its own collections; nobody else promotes anything once Agregarr is stopped. Kometa's `delete_collections: managed: true` only deletes collections carrying the `Kometa` label — ours never carry it.

## File structure

```
scripts/winswatch/
  home_calendar.yml          # rotation table (source of truth)              [T1]
  gen_home.py                # calendar + theme defs -> kometa/collections/winswatch/home_{movies,shows}.yml [T1]
  gen_cards.py               # one PNG per Home row -> kometa/overlays/winswatch/cards/<slug>.png [T4]
  home.py                    # CLI: requested | rows | cards | order  (argparse subcommands; --sections, --dry-run) [T2 skeleton, T3/T4/T5 fill]
  ww/overseerr.py            # Overseerr client: users(), requests(since_days) [T2]
  ww/shares.py               # plex.tv share-filter merge (label!=) [T3]
  ww/plexhome.py             # hub listing, ordering, demotion via plexapi ManagedHub [T5]
  host/jobs/nightly.sh       # + home.py requested/rows/cards [T7]
  host/jobs/order.sh         # home.py order (05:45 script) [T7]
  tests/test_gen_home.py test_overseerr.py test_home_requested.py test_shares.py test_home_rows.py test_gen_cards.py test_plexhome.py
kometa/collections/winswatch/home_movies.yml, home_shows.yml   # GENERATED [T1]; wired into config.yml in T7
kometa/overlays/winswatch/{movies,shows}.yml                   # ww_requested + group ww_tl [T2]
kometa/overlays/winswatch/cards/*.png, fonts/BricolageGrotesque[opsz,wdth,wght].ttf + OFL [T4]
```

Task order: **T1 ∥ T2 ∥ T4** (independent), then **T3 ∥ T5** (both extend `home.py` created in T2 — T3 adds `rows`, T5 adds `order`; different files otherwise), then **T6** (Shortlist UI), then **T7** (integration + production).

---

### Task 1: Rotation calendar and generated theme collections

**Files:**
- Create: `scripts/winswatch/home_calendar.yml`, `scripts/winswatch/gen_home.py`, `scripts/winswatch/tests/test_gen_home.py`
- Create (generated): `kometa/collections/winswatch/home_movies.yml`, `kometa/collections/winswatch/home_shows.yml`
- Read for filters: `kometa/collections/movies_tone_and_style.yml`, `shows_tone_and_style.yml`, `movies_weekend.yml`, `raunchy_comedy.yml`, `seasonal_*.yml` (copy each theme's `smart_filter` block verbatim except where this task says otherwise; the old files are left in place and dropped from `config.yml` in Task 7)

**Interfaces:**
- Produces: `gen_home.load_calendar(path) -> dict` with keys `movies`, `shows`, each a list of 14 `[theme, theme]` pairs (index 0 = week A Monday … 13 = week B Sunday); `gen_home.weekly_schedule(calendar_lib, theme) -> str` e.g. `"weekly(monday|thursday)"`; `gen_home.render(calendar, themes) -> dict[str, dict]` returning `{"home_movies.yml": {...}, "home_shows.yml": {...}}` ready for `yaml.safe_dump`; `THEMES` dict `name -> {"lib": "movies"|"shows", "emoji": str, "filter": dict, "card": str}` (`card` = slug used by Task 4, e.g. `adrenaline-rush`).
- Consumed by: Task 4 (`THEMES` for card names), Task 7 (the two generated files).

- [ ] **Step 1: Write the calendar**

`scripts/winswatch/home_calendar.yml` — two themes per day, no theme on consecutive days, every theme ≥ 2× per fortnight (movies 10 themes → 28 slots; shows 7 → 28 slots):

```yaml
# Wins Watch Home rotation. Week A then week B, Mon..Sun. Two shelves a day. Edit this, run gen_home.py, commit both.
movies:
  - [Adrenaline Rush, Hidden Gems]         # A Mon
  - [Crime Files, Love & Laughs]           # A Tue
  - [Sci-Fi Odyssey, Based on a True Story]# A Wed
  - [Mind Benders, Raunchy Comedy]         # A Thu
  - [Director's Spotlight, Fresh Picks]    # A Fri  (+ Date Night)
  - [Adrenaline Rush, Crime Files]         # A Sat  (+ Date Night)
  - [Hidden Gems, Sci-Fi Odyssey]          # A Sun  (+ Sunday Slow Burn)
  - [Love & Laughs, Mind Benders]          # B Mon
  - [Raunchy Comedy, Director's Spotlight] # B Tue
  - [Fresh Picks, Based on a True Story]   # B Wed
  - [Adrenaline Rush, Love & Laughs]       # B Thu
  - [Crime Files, Hidden Gems]             # B Fri  (+ Date Night)
  - [Sci-Fi Odyssey, Raunchy Comedy]       # B Sat  (+ Date Night)
  - [Mind Benders, Fresh Picks]            # B Sun  (+ Sunday Slow Burn)
shows:
  - [Worlds Beyond, Comfort Binge]         # A Mon
  - [Peak TV, Crime Beat]                  # A Tue
  - [Just Dropped, Edge of Your Seat]      # A Wed
  - [Not Just Cartoons, Worlds Beyond]     # A Thu
  - [Comfort Binge, Peak TV]               # A Fri
  - [Crime Beat, Just Dropped]             # A Sat
  - [Edge of Your Seat, Not Just Cartoons] # A Sun
  - [Worlds Beyond, Peak TV]               # B Mon
  - [Comfort Binge, Crime Beat]            # B Tue
  - [Just Dropped, Not Just Cartoons]      # B Wed
  - [Edge of Your Seat, Worlds Beyond]     # B Thu
  - [Peak TV, Comfort Binge]               # B Fri
  - [Crime Beat, Edge of Your Seat]        # B Sat
  - [Just Dropped, Not Just Cartoons]      # B Sun
```

Kometa's `weekly()` cannot express "week A vs week B" (it has no fortnight notion). Rule: a theme's `visible_home` lists every weekday it appears in **either** week — so on a given weekday up to four themes may be promoted, and `home.py order` (Task 5) keeps only the two that belong to the current week's table (it demotes the other two). Document this in the file header.

- [ ] **Step 2: Write the failing tests**

`scripts/winswatch/tests/test_gen_home.py`:
```python
from pathlib import Path
import yaml, gen_home

CAL = Path(__file__).resolve().parents[1] / "home_calendar.yml"

def test_calendar_shape_and_rules():
    cal = gen_home.load_calendar(CAL)
    for lib, n in (("movies", 10), ("shows", 7)):
        days = cal[lib]; assert len(days) == 14 and all(len(d) == 2 for d in days)
        names = {t for d in days for t in d}; assert names == set(gen_home.THEMES_BY_LIB[lib])
        for d in days: assert d[0] != d[1]
        for i in range(1, 14): assert not set(days[i]) & set(days[i - 1]), f"{lib} day {i} repeats a theme"
        for t in names: assert sum(t in d for d in days) >= 2

def test_weekly_schedule_unions_both_weeks():
    cal = gen_home.load_calendar(CAL)
    assert gen_home.weekly_schedule(cal["movies"], "Adrenaline Rush") == "weekly(monday|thursday|saturday)"

def test_render_matches_spec():
    out = gen_home.render(gen_home.load_calendar(CAL), gen_home.THEMES)
    m = out["home_movies.yml"]["collections"]; s = out["home_shows.yml"]["collections"]
    assert "💥 Adrenaline Rush" in m and "🎢 Edge of Your Seat" in s and "🍺 Raunchy Comedy" in m
    c = m["💥 Adrenaline Rush"]
    assert c["smart_filter"]["limit"] == 40 and c["smart_filter"]["sort_by"] == "random" and "collection_order" not in c
    assert c["visible_home"] == c["visible_shared"] == "weekly(monday|thursday|saturday)" and c["visible_library"] is True
    assert c["file_poster"] == "config/winswatch/cards/adrenaline-rush.png"
    assert m["🍷 Date Night"]["visible_home"] == "weekly(friday|saturday)" and m["☕ Sunday Slow Burn"]["visible_home"] == "weekly(sunday)"
    assert m["🎃 Halloween"]["visible_home"] == "range(09/15-10/31)" and "collection_order" not in m["🎃 Halloween"]
    assert s["🎢 Edge of Your Seat"]["smart_filter"]["all"]["genre"] == ["Mystery", "Crime"]
    assert "Kids" not in yaml.safe_dump(out)
    for coll in list(m.values()) + list(s.values()):
        assert "rating.gte" not in yaml.safe_dump(coll) or "user_rating.gte" in yaml.safe_dump(coll)
```

- [ ] **Step 3: Run, expect failure** — `cd ~/projects/homelab/unraid && scripts/winswatch/.venv/bin/python -m pytest scripts/winswatch/tests/test_gen_home.py -q` → `ModuleNotFoundError: gen_home`.

- [ ] **Step 4: Implement `gen_home.py`**

Skeleton (fill `THEMES` by copying each theme's existing `smart_filter` from the old files):
```python
"""Render the Home rotation (home_calendar.yml) into Kometa collection files. Deterministic; re-run after editing the calendar."""
import sys
from pathlib import Path
import yaml

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "kometa/collections/winswatch"
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
CARD = "config/winswatch/cards/{slug}.png"

def _theme(lib, emoji, slug, sort, flt):
    return {"lib": lib, "emoji": emoji, "card": slug, "sort": sort, "filter": flt}

# smart_filter blocks copied from kometa/collections/*.yml with two changes: `rating.gte` -> `user_rating.gte` (our MDBList
# score /10 — `rating` silently meant critic rating, which is now Metacritic and often empty) and no `Kids` genre (Plex has none).
THEMES = {
    "Adrenaline Rush": _theme("movies", "💥", "adrenaline-rush", "!08_Adrenaline_Rush", {...}),
    # ... every theme in Global Constraints, in that order ...
    "Edge of Your Seat": _theme("shows", "🎢", "edge-of-your-seat", "!08_Edge_of_Your_Seat",
        {"sort_by": "random", "limit": 40, "all": {"user_rating.gte": 6.5, "genre.not": ["Animation", "Family"], "genre": ["Mystery", "Crime"]}}),
    "Not Just Cartoons": _theme("shows", "🎨", "not-just-cartoons", "!08_Not_Just_Cartoons",
        {"sort_by": "random", "limit": 40, "all": {"user_rating.gte": 6.5, "genre.not": ["Family"], "genre": ["Animation"]}}),
}
THEMES_BY_LIB = {lib: [n for n, t in THEMES.items() if t["lib"] == lib] for lib in ("movies", "shows")}
EXTRAS = {  # not in the rotation: fixed schedules
    "Date Night": ("movies", "🍷", "date-night", "!12_Date_Night", "weekly(friday|saturday)"),
    "Sunday Slow Burn": ("movies", "☕", "sunday-slow-burn", "!12_Sunday_Slow_Burn", "weekly(sunday)"),
    "Halloween": ("movies", "🎃", "halloween", "!02_Halloween", "range(09/15-10/31)"),
    "Christmas Movies": ("movies", "🎄", "christmas", "!02_Christmas", "range(11/01-12/31)"),
    "Valentine's Picks": ("movies", "💘", "valentines", "!02_Valentines", "range(02/01-02/14)"),
    "Awards Season": ("movies", "🏆", "awards-season", "!02_Awards", "range(01/01-03/15)"),
}
EXTRA_FILTERS = {...}  # copied from movies_weekend.yml / seasonal_*.yml, same two changes

def load_calendar(path):
    cal = yaml.safe_load(Path(path).read_text())
    return {lib: [list(d) for d in cal[lib]] for lib in ("movies", "shows")}

def weekly_schedule(days, theme):
    on = sorted({i % 7 for i, d in enumerate(days) if theme in d})
    return "weekly(" + "|".join(DAYS[i] for i in on) + ")"

def _coll(name, emoji, slug, sort, sched, flt):
    flt = dict(flt); flt["limit"] = 40; flt["sort_by"] = "random"
    return {"sort_title": sort, "file_poster": CARD.format(slug=slug), "visible_home": sched, "visible_shared": sched,
            "visible_library": True, "smart_filter": flt}

def render(cal, themes):
    out = {"home_movies.yml": {"collections": {}}, "home_shows.yml": {"collections": {}}}
    for name, t in themes.items():
        f = "home_movies.yml" if t["lib"] == "movies" else "home_shows.yml"
        out[f]["collections"][f"{t['emoji']} {name}"] = _coll(name, t["emoji"], t["card"], t["sort"], weekly_schedule(cal[t["lib"]], name), t["filter"])
    for name, (lib, emoji, slug, sort, sched) in EXTRAS.items():
        out["home_movies.yml"]["collections"][f"{emoji} {name}"] = _coll(name, emoji, slug, sort, sched, EXTRA_FILTERS[name])
    return out

def write(out_dir=OUT):
    out_dir.mkdir(parents=True, exist_ok=True)
    for fname, doc in render(load_calendar(HERE / "home_calendar.yml"), THEMES).items():
        (out_dir / fname).write_text("# GENERATED by scripts/winswatch/gen_home.py from home_calendar.yml — do not edit\n"
                                     + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=4096))

if __name__ == "__main__":
    write(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT); print("wrote home_movies.yml, home_shows.yml")
```

- [ ] **Step 5: Run tests → PASS**; run `scripts/winswatch/.venv/bin/python scripts/winswatch/gen_home.py`; open the generated files and eyeball one movie and one show collection against the old file.

- [ ] **Step 6: Validate the filters against Plex (read-only)** — for every generated `smart_filter`, count matches through the Plex API (`/library/sections/{1|2}/all?...` with the same predicates; `user_rating>=` is `userRating>=`) and print `name: count`. Every theme must return ≥ 15; if one doesn't, loosen *that* theme's threshold by 0.5 and re-run. Record the counts in the report.

- [ ] **Step 7: Commit** — `git add scripts/winswatch/home_calendar.yml scripts/winswatch/gen_home.py scripts/winswatch/tests/test_gen_home.py kometa/collections/winswatch && git commit -m "feat(winswatch): Home rotation calendar + generated theme collections"`

---

### Task 2: REQUESTED label + poster badge

**Files:**
- Create: `scripts/winswatch/ww/overseerr.py`, `scripts/winswatch/home.py`, `scripts/winswatch/tests/test_overseerr.py`, `scripts/winswatch/tests/test_home_requested.py`
- Modify: `kometa/overlays/winswatch/movies.yml` (ww_new → group), `kometa/overlays/winswatch/shows.yml` (add ww_requested), `scripts/winswatch/gen_assets.py` (nothing — text overlay), `scripts/winswatch/tests/test_gen_overlays.py::test_hand_written_yaml_matches_locked_look` (extend)

**Interfaces:**
- Produces: `ww.overseerr.Client(url, api_key)` with `users() -> list[dict]` (`id`, `plexId`, `plexUsername`) and `requests(since_days: int) -> list[dict]` (each: `type` "movie"|"tv", `tmdb_id`, `requested_by_plex_id`, `created_at` ISO, `status` int (Overseerr media status), `available_at` ISO|None, `plex_rating_key` str|None); `home.plan_requested(items, requests, today, window_days=30) -> list[tuple[item, bool]]` (True = should carry label `Requested`).
- `home.py` CLI skeleton: `home.py <cmd> --sections 1,2 [--dry-run] [--env PATH]`, subparsers `requested` (this task), `rows`, `cards`, `order` (stubs that `raise SystemExit("not implemented")` — Tasks 3/4/5 replace them). Shared helpers in `home.py`: `load_env(path)`, `plex(env) -> PlexLib`, `sections(arg) -> list[int]`.
- Consumes: `ww.plexlib.PlexLib.set_labels(item, add:set, remove_prefixes:tuple)` (existing).

- [ ] **Step 1: Failing tests**

`tests/test_overseerr.py` (mock `requests.get` with `monkeypatch`; fixture JSON shaped like Overseerr `/api/v1/request?take=100&skip=0`: `results[].{type, createdAt, requestedBy:{plexId}, media:{tmdbId,status,mediaAddedAt,ratingKey}}` and `pageInfo:{pages}`):
```python
def test_requests_paginates_and_maps(monkeypatch):
    pages = {0: {"pageInfo": {"pages": 2}, "results": [{"type": "movie", "createdAt": "2026-09-01T00:00:00.000Z", "requestedBy": {"plexId": 1}, "media": {"tmdbId": 155, "status": 5, "mediaAddedAt": "2026-09-05T00:00:00.000Z", "ratingKey": "1252"}}]},
             100: {"pageInfo": {"pages": 2}, "results": [{"type": "tv", "createdAt": "2026-05-01T00:00:00.000Z", "requestedBy": {"plexId": 6}, "media": {"tmdbId": 95396, "status": 4, "mediaAddedAt": None, "ratingKey": None}}]}}
    monkeypatch.setattr(overseerr.requests, "get", lambda url, headers, params, timeout: _Resp(pages[params["skip"]]))
    got = overseerr.Client("http://x", "k").requests(since_days=90)   # today is patched to 2026-09-21
    assert [r["tmdb_id"] for r in got] == [155]          # the tv one is older than 90 days
    assert got[0] == {"type": "movie", "tmdb_id": 155, "requested_by_plex_id": 1, "created_at": "2026-09-01T00:00:00.000Z", "status": 5, "available_at": "2026-09-05T00:00:00.000Z", "plex_rating_key": "1252"}
```
`tests/test_home_requested.py`:
```python
def test_plan_requested_window():
    today = date(2026, 9, 21)
    items = [_it("1252", labels=[]), _it("99", labels=["Requested"]), _it("7", labels=[])]
    reqs = [{"plex_rating_key": "1252", "available_at": "2026-09-05T00:00:00.000Z", "status": 5},
            {"plex_rating_key": "99", "available_at": "2026-07-01T00:00:00.000Z", "status": 5},   # >30 days: label comes off
            {"plex_rating_key": "7", "available_at": None, "status": 3}]                            # pending: nothing
    assert home.plan_requested(items, reqs, today) == [(items[0], True), (items[1], False), (items[2], False)]
```

- [ ] **Step 2: Run → fail.** `ModuleNotFoundError`.

- [ ] **Step 3: Implement `ww/overseerr.py`** — `requests(since_days)`: GET `/api/v1/request` with `take=100`, `skip` stepping by 100 until `pageInfo.pages` exhausted, `sort=added`, `filter=all`; keep rows with `createdAt >= today - since_days`; map as in the test (`available_at` = `media.mediaAddedAt`). `users()`: GET `/api/v1/user?take=200`, map `{id, plexId, plexUsername}`. `timeout=30`, `raise_for_status()`.

- [ ] **Step 4: Implement `home.py`** — argparse with subparsers; `requested` command: for each section, `plex.items(section)`; build `by_key = {r["plex_rating_key"]: r for r in client.requests(since_days=400)}` (window on `available_at`, not request date); `plan_requested` returns `(item, want)` where `want = r and r["status"] in (4, 5) and r["available_at"] and (today - available_date).days <= window_days`; apply with `plex.set_labels(item, {"Requested"} if want else set(), ("Requested",))` unless `--dry-run`; print one line per change `section | title | +Requested/-Requested`. Reuse the `.env` loading pattern of `airdates.py`; add `OVERSEERR_URL=http://192.168.0.6:5055` and `OVERSEERR_API_KEY=` to the server `.env` (append; the key from `overseerr/settings.json`) and to `deploy.sh`'s heredoc.

- [ ] **Step 5: Kometa overlays** — in `movies.yml` and `shows.yml` add:
```yaml
  ww_requested:
    ignore_blank_results: true
    plex_search:
      validate: false
      all:
        label: Requested
        label.not: [DaysLeft_1, …, DaysLeft_30, NewEp_Mon, NewEp_Tue, NewEp_Wed, NewEp_Thu, NewEp_Fri, NewEp_Sat, NewEp_Sun,
                    ReturnsIn_8, …, ReturnsIn_30, Returns_Jan, …, Returns_Dec, Returns_TBA, Returns_2026, …, Returns_2032]
    overlay:
      name: text(REQUESTED)
      font: config/winswatch/fonts/Avenir_95_Black.ttf
      font_size: 58
      font_color: "#120a2a"
      back_color: "#a78bfa"
      back_radius: 15
      back_padding: 18
      horizontal_align: left
      horizontal_offset: 40
      vertical_align: top
      vertical_offset: 40
      group: ww_tl
      weight: 20
```
and give the existing movie `ww_new` the same `label.not` list, `group: ww_tl`, `weight: 10`. Generate the label lists in YAML by hand (they are static; `ReturnsIn_8..30`, years `2026..2032` — mirror `ww/buckets.tab_years()` and note the year list must be bumped yearly, same as the tabs). Shows: `ww_requested` only (no `ww_new`). Extend `test_hand_written_yaml_matches_locked_look` to assert both files' `ww_requested` overlay has `group == "ww_tl"`, `weight == 20`, `back_color == "#a78bfa"`, and that `NewEp_Wed` and `DaysLeft_3` are in its `label.not`; movies' `ww_new` weight 10 same group.

- [ ] **Step 6: Lab proof** — `deploy.sh`; `home.py requested --sections 4,5 --dry-run` then without; force one lab movie to carry both `Requested` and `DaysLeft_3` (Holdovers already has DaysLeft_3 — add `Requested` to it by hand with `PlexLib.set_labels`) and one with only `Requested` (Dune) and a show with `Requested` + `NewEp_Wed` (Slow Horses); `hostexec.py run kometa-lab`; `review_sheet.py --sections 4,5 --out <scratchpad>/lab_review_home1.png`; confirm Holdovers shows LEAVING only, Dune shows REQUESTED (no NEW), Slow Horses shows the NEW EP tab only. Remove the hand-added `Requested` labels afterwards.

- [ ] **Step 7: Commit** — `feat(winswatch): REQUESTED label from Overseerr + poster badge (tabs beat badges)`.

---

### Task 3: Per-user "New · Your Requests" rows

**Files:**
- Create: `scripts/winswatch/ww/shares.py`, `scripts/winswatch/tests/test_shares.py`, `scripts/winswatch/tests/test_home_rows.py`
- Modify: `scripts/winswatch/home.py` (`rows` command), `scripts/winswatch/ww/plexlib.py` (collection helpers)

**Interfaces:**
- Consumes: `ww.overseerr.Client` (Task 2), `home.py` skeleton (Task 2).
- Produces: `ww.shares.merge_exclusions(current: str|None, add: set[str]) -> str` (pure; plex.tv filter string grammar: `key=v1%2Cv2&key!=v3|v4` — read one existing shared user's `filterMovies` through plexapi first and match its exact form; Shortlist's `shortlist_*` entries are the reference); `ww.shares.apply(account: MyPlexAccount, server_name, user, filter_movies: str, filter_tv: str, dry_run) -> None` (`account.updateFriend(user, server, filterMovies=..., filterTelevision=...)`); `PlexLib.upsert_collection(section, title, items, label, sort='custom') -> Collection` (create if missing else replace items keeping insertion order, set `collectionSort` custom, add label); `home.build_new_row(recent: list, requests: list, n_recent=40) -> list` (pure weave: every 4th slot from index 1, leftovers appended, de-duplicated by ratingKey); `home.user_slug(username) -> str` and `home.row_title(base, slug) -> str` (base + zero-width suffix: encode the slug's index in the sorted user list as a run of U+200B/U+200C, exactly the way Shortlist names differ per user — read two Shortlist collection titles from Plex to copy the alphabet).

- [ ] **Step 1: Failing tests** — `test_shares.py`: `merge_exclusions("label!=shortlist_a|shortlist_b", {"winswatch_c"}) == "label!=shortlist_a|shortlist_b|winswatch_c"`, idempotent, keeps `contentRating!=` clauses, empty current → `"label!=winswatch_c"`. `test_home_rows.py`: weave order for 6 recent + 2 requests is `[r0, q0, r1, r2, r3, q1, r4, r5]`; a request already in recent is not duplicated; `row_title("📥 New Movies · Your Requests", "lily_arnold")` starts with the base, differs from the same call for `"da6490"`, and `.strip()`-equal titles are distinct strings.

- [ ] **Step 2: Run → fail.**

- [ ] **Step 3: Implement** `rows`: for each enabled Overseerr/Plex user (Plex users from `MyPlexAccount.users()` + home users; skip the owner), per section: `recent` = `section.search(sort="addedAt:desc", maxresults=40)` (top-level type), `reqs` = that user's requests (`requested_by_plex_id == user.id`, 90 days, status 4/5, `plex_rating_key` resolvable in this section); weave; `upsert_collection(section, row_title(base, slug), items, label=f"winswatch_{slug}")`; then for **every other** user merge `label!=winswatch_{slug}` into their filters (movies filter for section 1, television for section 2) — build the full desired exclusion set per user first and call `updateFriend` once per user; finally promote the collection's hub to shared Home (`section.manageHub`/`ManagedHub.promoteShared()`), never `promoteHome` (owner Home stays clean). `--dry-run` prints titles, item lists and the filter strings it would write. Managed profiles: call `apply` the same way; if plex.tv rejects (`updateFriend` fails for a restricted home user), log `!! share filter not applied for <user>` and continue — report it.

- [ ] **Step 4: Lab proof** — `home.py rows --sections 4,5` (lab libraries; the per-user collections land there, filters get `winswatch_*` exclusions). Verify from a *shared* user's viewpoint: use the Plex API with that user's server token? Not available — instead read back `account.user(name).filterMovies` and print it, confirm every other user has the exclusion and Shortlist's entries are intact, and open Plex as Chase (owner) to see the collections exist with the right items. Record the filter strings before/after in the report. Remove the lab collections afterwards (`collection.delete()`) and strip the `winswatch_*` values from the filters again (`merge_exclusions` inverse: implement `remove_exclusions(current, drop)` too, with a test).

- [ ] **Step 5: Commit** — `feat(winswatch): per-user New·Your Requests rows with Shortlist-style label exclusions`.

---

### Task 4: Collection cards

**Files:**
- Create: `scripts/winswatch/gen_cards.py`, `scripts/winswatch/tests/test_gen_cards.py`, `kometa/overlays/winswatch/fonts/BricolageGrotesque[opsz,wdth,wght].ttf` + `OFL-BricolageGrotesque.txt` (from `https://github.com/google/fonts/tree/main/ofl/bricolagegrotesque`), `kometa/overlays/winswatch/cards/*.png`
- Modify: `scripts/winswatch/home.py` (`cards` command), `scripts/winswatch/deploy.sh` (nothing — `kometa/overlays/winswatch/` is already rsynced whole)

**Interfaces:**
- Consumes: `gen_home.THEMES`, `gen_home.EXTRAS` (Task 1) for theme names/emoji/slugs.
- Produces: `gen_cards.CARDS: dict[slug, (kind, emoji, title)]` — every Home row incl. `for-you-movies`, `for-you-shows`, `trending-movies`, `trending-shows`, `new-movies`, `new-shows`, `popular-movies`, `popular-shows`, `leaving-movies`, `leaving-shows`, `byw` (generic "Because you watched"), every theme slug, `date-night`, `sunday-slow-burn`, `halloween`, `christmas`, `valentines`, `awards-season`; `gen_cards.render(slug) -> PIL.Image` 1000×1500; `TINT[kind] = (top_hex, bottom_hex, ink_hex, ring: bool)` with kinds `personal` (`#0e3b57→#1b5e8a`, white, ring `#5ac8fa` 14 px inset), `trending` (`#3b1f5e→#6d3fb8`, white), `new` (`#0e3b57→#5ac8fa`, `#06131c`), `popular` (`#4a2e00→#e8b84a`, `#1a1200`), `leaving` (`#5a1010→#e52d27`, white), `theme` (`#1a1d26→#3a4052`, white), `seasonal` (per season: halloween `#1a0a2e→#ff7a1a`, christmas `#0b2e1a→#c62828`, valentines `#3a0a1e→#ff4f8b`, awards `#2a2000→#f5c518`).
- Card layout (1000×1500): gradient plate; eyebrow (kind word, e.g. `JUST FOR YOU`, `RIGHT NOW`, `NEW ON WINS WATCH`, `EVERYONE'S WATCHING`, `LAST CALL`, `TODAY'S SHELF`, `THIS SEASON`) Manrope-style caps 34 px tracking 0.14 em at (80, 1130); title (emoji + name) Bricolage 800 at 120 px, wrapping at 840 px, bottom-aligned at y=1400, line pitch 1.05; paw (`src/paw_512.png`) 110 px at top-right (810, 80) in the ink colour at 90 % opacity. Emoji: Pillow cannot render colour emoji from Bricolage — draw the emoji with `NotoColorEmoji` if present on the workstation (`fc-list | grep -i emoji`), else omit the emoji from the card and keep it in the row title only; state which in the report.

- [ ] **Step 1: Failing test** — `test_gen_cards.py`: `render("adrenaline-rush").size == (1000, 1500)`; every slug in `CARDS` renders; `render("for-you-movies")` has ring pixels (`#5ac8fa`) at (14, 750); `render("popular-movies")` bottom-centre pixel is within ±12 of `#e8b84a`; `gen_cards.generate(tmp_path)` writes `len(CARDS)` PNGs.

- [ ] **Step 2: Run → fail.** Steps 3–4: implement, pass, `generate()` into `kometa/overlays/winswatch/cards/`, look at three cards with the Read tool.

- [ ] **Step 5: `home.py cards`** — for collections Kometa does not own (Shortlist's `✨/🎯/👥` rows, Maintainerr's `⏳`, ours `📥`): find them by title prefix in each section, `collection.uploadPoster(filepath=...)` with the matching card; idempotent (skip if the collection's current poster hash — `collection.thumb` — already came from us: keep a `cache/cards.json` of `{ratingKey: slug}` and re-upload only when missing or the card file's mtime is newer). `--dry-run` lists what it would upload.

- [ ] **Step 6: Commit** — `feat(winswatch): generated collection cards for every Home row`.

---

### Task 5: Hub order + demotion

**Files:**
- Create: `scripts/winswatch/ww/plexhome.py`, `scripts/winswatch/tests/test_plexhome.py`
- Modify: `scripts/winswatch/home.py` (`order` command)

**Interfaces:**
- Consumes: `gen_home.load_calendar` + `THEMES` (Task 1) to know today's two themes; `home.row_title` prefix logic (Task 3).
- Produces: `ww.plexhome.desired_order(lib: "movies"|"shows", today: date, calendar) -> list[str]` returning title **prefixes** in §1 order: `["✨ ", "🔥 Trending ", "📥 New ", "👥 Popular ", "⏳ ", "<🎃 seasonal if in window else shelf1 emoji+name>", "<🍷/☕ weekend if Fri-Sun (movies) else shelf2>", "🎯 Because you watched"]`; `plexhome.plan(hubs: list[ManagedHub], desired: list[str]) -> tuple[list[ManagedHub] ordered, list[ManagedHub] to_demote]` (pure: a hub matches the first prefix its title starts with; a prefix may match several hubs — all per-user `✨`/`📥`/`🎯` hubs keep their relative order; unmatched promoted hubs go to `to_demote`; hubs whose title is a theme name **not** in today's pair are demoted too — that is the week A/B rule from Task 1); `plexhome.apply(section, ordered, to_demote, dry_run)` using `ManagedHub.move(after=prev)` walking the list and `hub.demoteShared(); hub.demoteHome()` for the rest.
- Week: week A when `((today - date(2026, 9, 21)).days // 7) % 2 == 0`.

- [ ] **Step 1: Failing test** — `test_plexhome.py` with fake hubs (`title`, `promotedToSharedHome`): given today = Mon 2026-09-21 (week A) movies desired = `[…, "💥 Adrenaline Rush", "💎 Hidden Gems", …]`; hubs list in scrambled order incl. `IMDb Popular`, `🕵️ Crime Files` (Tuesday theme, promoted) → `plan` orders the eight, demotes `IMDb Popular` and `🕵️ Crime Files`; Friday movies → shelf 2 is `🍷 Date Night`; Oct 1 → shelf 1 is `🎃 Halloween`; TV never gets weekend rows.

- [ ] **Step 2: Run → fail.** Step 3: implement (`section.hubs()`? — plexapi: `LibrarySection.manageHubs()`? Check: `plexapi.library.LibrarySection` has `hubs()` and the managed list via `ManagedHub` fetched from `/hubs/sections/{key}/manage`; use `section.fetchItems('/hubs/sections/%s/manage' % section.key, ManagedHub)` if no helper exists — say which in the report). Step 4: pass.

- [ ] **Step 5: Lab proof of the Kometa question** — in the lab config (`build_lab_config.py` output) add two tiny smart collections with `visible_shared: weekly(<today>)` / `weekly(<tomorrow>)`, run `kometa-lab`, then run `home.py order --sections 4,5`, then run `kometa-lab` again and list the hubs: does Kometa's promote/demote pass change the order `home.py order` set? Record the answer; it decides whether `order` must run after Kometa (spec §8 assumes yes — if Kometa preserves order, `order` can join `nightly.sh` at 04:30 and Task 7 skips the second user script).

- [ ] **Step 6: Commit** — `feat(winswatch): Home hub ordering + demotion`.

---

### Task 6: Shortlist settings (UI) and Maintainerr rename (UI)

**Files:** none in the repo; record every changed field in the report. Uses Chrome (logged in) at `http://192.168.0.15:5959` and Maintainerr `http://192.168.0.30:6246`.

- [ ] **Step 1: Shortlist → Rows → Edit**, for each row:
  - `✨ {library_name} Recommended For You` → name template `✨ Movies for you` / `✨ Shows for you` (Shortlist's `{library_name}` gives "Movies"/"TV Shows" — if the template cannot say "Shows" for the TV library, use `✨ {library_name} for you` and note it); sources = **TMDB discover by taste + TMDB recommendations** (untick similar); size 40; rebuild every 8 days; pick order `best`.
  - `🎯 Because you watched {top_seed}` → sources = **TMDB similar only**; **seed window 3**; rebuild every 1 day; size 30.
  - `👥 Popular {library_name} on this server` → `👥 Popular {library_name} on Wins Watch`; size 40.
  - Poster: if a row's poster settings accept a file or URL, point each at the matching card from Task 4 (`cards/for-you-movies.png` etc. — served how? Shortlist likely wants a URL: use the raw GitHub URL of the file on the branch, or skip and let `home.py cards` upload nightly). Note which.
  - Users: **Chase_Test first** (Shortlist → Users → per-user override if the UI has one; otherwise all users — Chase accepted "everyone after the first comparison", so if per-user isn't possible, apply globally and say so).
- [ ] **Step 2: Trigger a Shortlist run** for Chase_Test only (`POST /api/runs {user_ids:[<id>]}` from the browser session, or the UI's Run button) and confirm the two rows now differ (compare titles in Plex).
- [ ] **Step 3: Maintainerr → Collections** → rename `Movies Leaving Soon` → `⏳ Movies Leaving Wins Watch`, `Shows Leaving Soon` → `⏳ Shows Leaving Wins Watch` (title + manual collection name); keep `visibleOnHome`. Confirm the Plex collection title changed after its next handler run (or trigger it).
- [ ] **Step 4:** Report: every field before → after.

---

### Task 7: Integration — config, nightly, Agregarr off, production

**Files:**
- Modify: `scripts/winswatch/promote_config.py` (add `--phase home`), `scripts/winswatch/host/jobs/nightly.sh`, create `scripts/winswatch/host/jobs/order.sh`, `scripts/winswatch/deploy.sh` (copy `kometa/collections/winswatch/` to `/mnt/nastower/appdata/Kometa/config/winswatch/collections/`), `docs/superpowers/specs/2026-09-21-wins-watch-home-design.md` (§8 if Task 5 changed the ordering answer)

- [ ] **Step 1: `promote_config.py --phase home`** — in both libraries: replace every `collection_files:` entry with `- file: config/winswatch/collections/home_movies.yml` (Movies) / `home_shows.yml` (TV) **plus** the existing `trending_movies.yml` / `shows_trending.yml` / `movies_leaving_soon.yml` / `shows_leaving_soon.yml` URLs (keep those four lines as they are); for every remaining `- default: <chart>` line add `template_variables: {visible_home: false, visible_shared: false}` (or drop the default entirely if it exists only for Home — keep `genre`, `franchise`, `universe`, `streaming`, `network`, `collectionless`, `separator_chart` with the visibility off; drop `imdb`, `tmdb`, `basic`). Print the diff; test it parses; write with `--write`.
- [ ] **Step 2: `nightly.sh`** — after `airdates.py`: `python home.py requested --sections $SECTIONS`, `python home.py rows --sections $SECTIONS`, `python home.py cards --sections $SECTIONS` (same rc-collect pattern). `order.sh`: `python home.py order --sections $SECTIONS`. Add `OVERSEERR_*` to the server `.env` if Task 2 didn't.
- [ ] **Step 3: Agregarr off** — `POST http://192.168.0.15:8043/api/v1/docker/agregarr/stop` (bearer `~/.config/nastower/api_token`), then in Plex demote/delete its collections: `My Requests` (both libs) and every `*'s  Movie requests` / `*'s  TV Show requests` (they are Agregarr's; deleting them is fine — row 3 replaces them). Record the list.
- [ ] **Step 4: Unraid user script `winswatch-order`** (only if Task 5 found ordering must follow Kometa) — Settings → User Scripts → Add new script → name `winswatch-order`, contents `#!/bin/bash\nbash /mnt/user/appdata/scripts/winswatch/host/jobs/order.sh`, schedule Custom `45 5 * * *`. Do it in Chrome like the `winswatch` schedule was; verify the schedule persisted after reload.
- [ ] **Step 5: Production run, in order** — `deploy.sh` → `promote_config.py --phase home --write` → `hostexec.py run nightly` (scores, airdates, requested, rows, cards) → `hostexec.py run kometa-prod-collections` (new job: `--run --collections-only`; add it) → `hostexec.py run kometa-prod-overlays` → `hostexec.py run order` (new job) → dump the promoted hubs per section (`/hubs/sections/{1,2}/manage`) into the report and compare to §1 → `review_sheet.py --sections 1,2` for a poster spot-check of REQUESTED.
- [ ] **Step 6:** Report timings of each step, the hub lists, and anything demoted. Commit: `feat(winswatch): Home live — config, nightly, Agregarr retired`.

---

## Self-review

- Spec coverage: §1 rows → T5 order/demote + T6 names + T7 config; §2 rotation → T1 (+T5 week A/B demotion); §3 New rows → T3; §4 badge → T2; §5 cards → T4 (+T6 Shortlist poster note); §6 order → T5; §7 Shortlist → T6; §8 nightly → T7; §9 nothing to do. Gap: spec §5 says Shortlist "rows get theirs through Shortlist's poster setting… otherwise home.py uploads" — covered by T4 step 5 + T6 step 1.
- Placeholders: T1 `THEMES` shows `{...}` for filters that are copied verbatim from named existing files — the implementer has the source; T4 kinds/tints are fully listed; T5's plexapi fetch fallback is spelled out.
- Type consistency: `home.row_title(base, slug)` used in T3 and T5; `gen_home.THEMES[name]["card"]` used by T4; `ww.overseerr.Client.requests()` field names identical in T2 tests and T3 usage.
