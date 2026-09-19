# Wins Watch Poster Overlays Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Kometa overlay set, assets, and nightly label scripts for the decided Wins Watch poster look, and prove it live on two isolated Plex "lab" libraries — without touching production libraries.

**Architecture:** Kometa renders everything (image + text overlays, queues for the chip row, groups for top-edge precedence). Three data facts Kometa can't compute — MDBList score/votes, Sonarr next-air, Maintainerr days-left — arrive as Plex labels / the user-rating slot from small Python scripts run in a `python:3.12-slim` container on the Unraid host. Host commands are triggered through the Unraid User Scripts plugin via the management agent (`POST /api/v1/user-scripts/winswatch/execute`), which runs `host/run.sh` → the current `host/job.sh` that we write over NFS.

**Tech Stack:** Python 3.12, Pillow, PyYAML, python-plexapi, requests, pytest; Kometa (`kometateam/kometa` image); Plex API; MDBList API; Sonarr v3 API; Unraid management agent.

**Spec:** `docs/superpowers/specs/2026-09-18-wins-watch-posters-design.md`

## Global Constraints

- **Never modify production Plex libraries (Movies = section 1, TV Shows = section 2) or the production Kometa `config.yml`** until Chase says so. Lab libraries only.
- Canvas 1000×1500 for posters, 1000×562 for episode stills. `u = 10px`.
- Brand: light blue `#5ac8fa` (ink `#06131c`), deep blue `#1b5e8a`, gold `#f5c518` (score) / `#e8b84a` (leaving), red `#c62828` = canceled only, gray `#5f6b7a` = ended.
- Score bands: gray `#8a94a6` < 65 · white `#ffffff` 65–72 · light blue `#5ac8fa` 73–84 · gold `#f5c518` ≥ 85.
- A title with a `DaysLeft_N` label never shows NEW and never shows a status tab.
- Secrets live only in `/mnt/user/appdata/scripts/winswatch/.env` on the server (copied from Kometa's `.env`); never in the repo.
- Paths: repo `~/repos/unraid`; NFS mounts `/mnt/nastower/appdata` = `/mnt/user/appdata`, `/mnt/nastower/data` is **not** mounted (host jobs handle media paths). Plex sees `/mnt/user/data/media` as `/data/media`.
- Agent token: `$(cat ~/.config/nastower/api_token)`; base `http://192.168.0.15:8043/api/v1`.
- Plex `http://192.168.0.20:32400`, token in `/mnt/nastower/appdata/Kometa/config/.env` (`KOMETA_PlexToken`); MDBList key `KOMETA_MDBListApiKey`; Sonarr `http://192.168.0.30:8989` key `KOMETA_SonarrApiKey`; TMDB `KOMETA_TMDBApiKey`.
- Commit after every task with a `feat(winswatch): …` message.

## File structure

```
scripts/winswatch/
  requirements.txt            # pillow, pyyaml, plexapi, requests, python-dotenv, pytest
  ww/__init__.py
  ww/colors.py                # every hex from the spec, codec/service maps, band()
  ww/buckets.py               # votes_bucket(), airdate_label()
  ww/mdblist.py               # fetch_scores(api_key, kind, tmdb_id) with on-disk cache
  ww/sonarr.py                # next_air_dates(base_url, api_key) -> {tvdb_id: date|None, status}
  ww/plexlib.py               # PlexLib: items(section) with tmdb/tvdb ids, set_labels(), set_user_rating()
  ww/chips.py                 # codec chip combinations, detection conditions, and ranking weight
  gen_assets.py               # -> kometa/overlays/winswatch/assets/*.png
  gen_overlays.py             # -> kometa/overlays/winswatch/generated/{gauge,topedge,status,chips_movies,chips_episodes}.yml
  scores.py                   # CLI: MDBList -> user rating + Votes_* labels
  airdates.py                 # CLI: Sonarr -> NewEp_/ReturnsIn_/Returns_* labels
  build_lab_config.py         # production config.yml -> lab.yml (lab libraries only)
  lab_media.py                # Plex prod file paths -> host/jobs/lab-media.sh (symlinks)
  create_lab_libraries.py     # Plex API: create the two lab sections, hide from Home, check shares
  review_sheet.py             # CLI: tile lab posters/stills into one review PNG
  deploy.sh                   # rsync scripts + overlay files + assets to the server over NFS
  conftest.py                 # test path setup
  host/run.sh                 # what the Unraid user script calls; runs host/job.sh, logs to host/last.log
  host/jobs/labels.sh         # docker run python:3.12-slim … scores.py + airdates.py
  host/jobs/kometa-lab.sh     # docker run kometateam/kometa --config /config/lab.yml --run --overlays-only
  host/jobs/kometa-lab-remove.sh
  tests/test_buckets.py tests/test_gen_overlays.py tests/test_gen_assets.py tests/test_sonarr.py tests/test_mdblist.py
kometa/overlays/winswatch/
  fonts/Avenir_95_Black.ttf   # copy of kometa/overlays/fonts/Avenir_95_Black.ttf
  assets/                     # generated PNGs (committed)
  movies.yml shows.yml seasons.yml episodes.yml    # hand-written
  generated/gauge.yml generated/topedge.yml generated/status.yml generated/chips_movies.yml generated/chips_episodes.yml   # generated (committed)
kometa/lab.yml.template       # libraries + overlay_files; plex/tmdb/mdblist blocks filled by build_lab_config.py
```

Kometa container path for all of it: `/config/winswatch/…` (deploy copies `kometa/overlays/winswatch` → `/mnt/user/appdata/Kometa/config/winswatch`).

## Coordinate sheet (used by Tasks 2, 3, 4)

Posters 1000×1500, origin top-left. Kometa positions use `horizontal_align`/`horizontal_offset`, `vertical_align`/`vertical_offset`.

| Element | Asset / text | Position |
|---|---|---|
| bottom bar | `bar_bottom.png` 1000×240 | h center 0, v bottom 0 |
| chip slot 1/2/3 | text 46px | h left 40 / 165 / 330, v bottom 30 |
| service (shows) | text 46px | h left 40, v bottom 30 |
| arc | `arc_NN.png` 220×130 | h right 40, v bottom 55 |
| number | text `<<user_rating%>>` 62px, back 220×90 transparent | h right 40, v bottom 62 |
| votes | text 31px, back 220×40 transparent | h right 40, v bottom 22 |
| NEW (movies) | text 58px, back brand radius 15, pad 18/32 | h left 40, v top 40 |
| NEW (shows) | same | h left 40, v top 100 |
| reel | `reel.png` 95×95 | h right 40, v top 40 |
| top edge bg | `edge_{gray,red}.png` 1000×16; `tab_{lightblue,deepblue}_{wide,narrow}.png` 1000×80 (line + plate at x 40, plate w 330/230, h 64) | h center 0, v top 0 |
| tab text | 42px, back transparent w 330/230 h 64 | h left 40, v top 16 |
| bookmark bg | `bookmark.png` 1000×112 (gold line + notched gold plate x 40 w 300 h 96) | h center 0, v top 0 |
| bookmark text | 42px ink `#1a1200`, back transparent w 300 h 70 | h left 40, v top 16 |
| NEW SEASON (seasons) | text 58px, back brand | h left 40, v bottom 40 |

Episodes 1000×562: `bar_top.png` 1000×140 (h center, v top 0); chip slots h left 40/165/330, v top 34; runtime text `<<runtime>>m` 46px h right 40, v top 34.

---

### Task 0 (Chase, one-time): create the host hook

In Unraid → Settings → User Scripts → **Add new script**, name `winswatch`, contents:

```bash
#!/bin/bash
bash /mnt/user/appdata/scripts/winswatch/host/run.sh
```

Save. No schedule. Everything else in this plan is automated.

---

### Task 1: Scaffold + color/bucket helpers

**Files:**
- Create: `scripts/winswatch/requirements.txt`, `scripts/winswatch/ww/__init__.py`, `scripts/winswatch/ww/colors.py`, `scripts/winswatch/ww/buckets.py`
- Test: `scripts/winswatch/tests/test_buckets.py`

**Interfaces:**
- Produces: `colors.band(score:int)->str` (hex), `colors.CODEC` dict `{key: (label, hex)}` keys `k4,p1080,p720,sd,dv,dvhdr,hdrp,hdr,atmos,ddpatmos,truehd,dtsx,dtshd,dts,ddp,dd,aac,flac,pcm,opus`, `colors.SERVICE` dict `{display_name: hex}`, `colors.BRAND`, `colors.INK`, `colors.DEEP`, `colors.GOLD`, `colors.LEAVE_GOLD`, `colors.RED`, `colors.GRAY`; `buckets.votes_bucket(n:int)->str|None` returning e.g. `"1.6M"`, `buckets.VOTE_BUCKETS` (ordered list of bucket strings), `buckets.airdate_label(next_air:date|None, status:str, today:date)->str|None`.

- [ ] **Step 1: Write the failing tests**

`scripts/winswatch/tests/test_buckets.py`:
```python
from datetime import date
from ww.buckets import votes_bucket, VOTE_BUCKETS, airdate_label
from ww.colors import band, CODEC, SERVICE

def test_band_edges():
    assert band(64) == "#8a94a6"
    assert band(65) == "#ffffff"
    assert band(72) == "#ffffff"
    assert band(73) == "#5ac8fa"
    assert band(84) == "#5ac8fa"
    assert band(85) == "#f5c518"

def test_votes_bucket():
    assert votes_bucket(0) is None
    assert votes_bucket(853) is None          # under 10K: no count shown
    assert votes_bucket(19_613) == "20K"
    assert votes_bucket(120_000) == "100K"
    assert votes_bucket(793_314) == "800K"
    assert votes_bucket(1_632_540) == "1.5M"
    assert votes_bucket(4_849_612) == "5.0M"
    assert votes_bucket(9_000_000) == "7.0M"  # capped
    assert all(votes_bucket(int(float(b[:-1]) * (1e6 if b.endswith("M") else 1e3))) == b for b in VOTE_BUCKETS)

def test_airdate_label():
    t = date(2026, 9, 18)
    assert airdate_label(date(2026, 9, 23), "continuing", t) == "NewEp_Wed"
    assert airdate_label(date(2026, 9, 25), "continuing", t) == "NewEp_Fri"
    assert airdate_label(date(2026, 10, 1), "continuing", t) == "ReturnsIn_13"
    assert airdate_label(date(2026, 11, 14), "continuing", t) == "Returns_Nov"
    assert airdate_label(date(2027, 2, 5), "continuing", t) == "Returns_2027"
    assert airdate_label(None, "continuing", t) == "Returns_TBA"
    assert airdate_label(None, "ended", t) is None
    assert airdate_label(date(2026, 9, 18), "continuing", t) == "NewEp_Fri"  # today counts as ≤7

def test_codec_and_service_tables():
    assert CODEC["dv"] == ("DV", "#a78bfa")
    assert CODEC["dtshd"] == ("DTS-HD MA", "#fb923c")
    assert SERVICE["Netflix"] == "#e50914"
    assert SERVICE["Apple TV+"] == "#f5f5f7"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd ~/repos/unraid/scripts/winswatch && python -m venv .venv && . .venv/bin/activate && pip install -q pillow pyyaml plexapi requests python-dotenv pytest && pytest -q`
Expected: FAIL — `ModuleNotFoundError: ww`

- [ ] **Step 3: Implement**

`scripts/winswatch/requirements.txt`:
```
pillow
pyyaml
plexapi
requests
python-dotenv
pytest
```

`scripts/winswatch/ww/__init__.py`: empty.

`scripts/winswatch/ww/colors.py`:
```python
BRAND = "#5ac8fa"; INK = "#06131c"; DEEP = "#1b5e8a"
GOLD = "#f5c518"; LEAVE_GOLD = "#e8b84a"; LEAVE_INK = "#1a1200"
RED = "#c62828"; GRAY = "#5f6b7a"; WHITE = "#ffffff"; LOW = "#8a94a6"

def band(score: int) -> str:
    if score >= 85: return GOLD
    if score >= 73: return BRAND
    if score >= 65: return WHITE
    return LOW

# key -> (label, hex)
CODEC = {
    "k4": ("4K", WHITE), "p1080": ("1080p", WHITE), "p720": ("720p", WHITE), "sd": ("SD", WHITE),
    "dv": ("DV", "#a78bfa"), "dvhdr": ("DV·HDR", "#c084fc"), "hdrp": ("HDR10+", "#fbbf24"), "hdr": ("HDR", "#e8b84a"),
    "atmos": ("ATMOS", "#60a5fa"), "ddpatmos": ("DD+ ATMOS", "#7dd3fc"), "truehd": ("TRUEHD", "#2dd4bf"),
    "dtsx": ("DTS:X", "#f87171"), "dtshd": ("DTS-HD MA", "#fb923c"), "dts": ("DTS", "#ef4444"),
    "ddp": ("DD+", "#4ade80"), "dd": ("DD", "#a3a3a3"), "aac": ("AAC", "#9ca3af"),
    "flac": ("FLAC", "#9ca3af"), "pcm": ("PCM", "#9ca3af"), "opus": ("OPUS", "#9ca3af"),
}

# display name -> hex ; Plex `network` values that map to each name are in SERVICE_NETWORKS
SERVICE = {
    "Netflix": "#e50914", "Prime Video": "#00a8e1", "Apple TV+": "#f5f5f7", "HBO": "#ffffff", "Max": "#b535f6",
    "Hulu": "#1ce783", "Disney+": "#5b9bff", "Paramount+": "#0064ff", "Peacock": "#ffcf00", "FX": "#ffffff",
    "Showtime": "#ff2a2a", "AMC": "#ffcc00", "CBS": "#3b82f6", "NBC": "#f37021", "ABC": "#ffffff", "FOX": "#3b82f6",
    "BBC": "#ffffff", "Comedy Central": "#ffc800", "Crunchyroll": "#f47521", "Bravo": "#8b5cf6", "Syfy": "#a855f7",
    "The CW": "#22c55e", "MGM+": "#f5c518", "Lionsgate+": "#ff8a00", "Adult Swim": "#ffffff", "Starz": "#ffffff",
    "USA Network": "#3b82f6",
}
SERVICE_NETWORKS = {
    "Netflix": ["Netflix"], "Prime Video": ["Prime Video", "Amazon", "Amazon Prime Video", "Freevee"],
    "Apple TV+": ["Apple TV+", "Apple TV"], "HBO": ["HBO"], "Max": ["Max", "HBO Max"], "Hulu": ["Hulu"],
    "Disney+": ["Disney+"], "Paramount+": ["Paramount+", "Paramount Network"], "Peacock": ["Peacock"],
    "FX": ["FX", "FXX"], "Showtime": ["Showtime"], "AMC": ["AMC", "AMC+"], "CBS": ["CBS"], "NBC": ["NBC"],
    "ABC": ["ABC"], "FOX": ["FOX"], "BBC": ["BBC One", "BBC Two", "BBC", "BBC Three"], "Comedy Central": ["Comedy Central"],
    "Crunchyroll": ["Crunchyroll"], "Bravo": ["Bravo"], "Syfy": ["Syfy"], "The CW": ["The CW"], "MGM+": ["MGM+"],
    "Lionsgate+": ["Lionsgate+", "Starz"], "Adult Swim": ["Adult Swim"], "Starz": ["Starz"], "USA Network": ["USA Network"],
}
```

`scripts/winswatch/ww/buckets.py`:
```python
from datetime import date

VOTE_BUCKETS = ["10K", "20K", "50K"] + [f"{n}00K" for n in range(1, 10)] + [f"{x/2:.1f}M" for x in range(2, 15)]
# -> 10K 20K 50K 100K..900K 1.0M 1.5M ... 7.0M   (25 buckets)

def _value(b: str) -> int:
    return int(float(b[:-1]) * (1_000_000 if b.endswith("M") else 1_000))

def votes_bucket(n: int) -> str | None:
    """Nearest bucket at or below n; None under 10K; capped at 7.0M."""
    if n < 10_000:
        return None
    best = VOTE_BUCKETS[0]
    for b in VOTE_BUCKETS:
        if _value(b) <= n:
            best = b
    return best

DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def airdate_label(next_air: date | None, status: str, today: date) -> str | None:
    """Sonarr status: continuing|ended|upcoming|deleted. Ended/canceled shows get no label (Kometa uses tmdb_status)."""
    if status not in ("continuing", "upcoming"):
        return None
    if next_air is None:
        return "Returns_TBA"
    days = (next_air - today).days
    if days < 0:
        return "Returns_TBA"
    if days <= 7:
        return f"NewEp_{DOW[next_air.weekday()]}"
    if days <= 30:
        return f"ReturnsIn_{days}"
    if days <= 120:
        return f"Returns_{MON[next_air.month - 1]}"
    return f"Returns_{next_air.year}"
```

- [ ] **Step 4: Run tests**

Run: `pytest -q`  Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
cd ~/repos/unraid && git add scripts/winswatch && git commit -m "feat(winswatch): scaffold, color tables, vote/airdate buckets"
```

---

### Task 2: Asset generator

**Files:**
- Create: `scripts/winswatch/gen_assets.py`, `kometa/overlays/winswatch/fonts/Avenir_95_Black.ttf` (copy)
- Test: `scripts/winswatch/tests/test_gen_assets.py`
- Output: `kometa/overlays/winswatch/assets/*.png`

**Interfaces:**
- Produces: `gen_assets.generate(out_dir: Path) -> list[Path]`; files named exactly: `bar_bottom.png`, `bar_top.png`, `arc_00.png`…`arc_100.png`, `edge_gray.png`, `edge_red.png`, `tab_lightblue_narrow.png`, `tab_lightblue_wide.png`, `tab_deepblue_narrow.png`, `tab_deepblue_wide.png`, `bookmark.png`, `reel.png`.

- [ ] **Step 1: Write the failing test**

`scripts/winswatch/tests/test_gen_assets.py`:
```python
from pathlib import Path
from PIL import Image
import gen_assets

def test_generate_all(tmp_path: Path):
    files = gen_assets.generate(tmp_path)
    names = {f.name for f in files}
    assert {"bar_bottom.png", "bar_top.png", "bookmark.png", "reel.png", "edge_gray.png", "edge_red.png",
            "tab_lightblue_narrow.png", "tab_deepblue_wide.png"} <= names
    assert sum(n.startswith("arc_") for n in names) == 101
    assert Image.open(tmp_path / "bar_bottom.png").size == (1000, 240)
    assert Image.open(tmp_path / "bar_top.png").size == (1000, 140)
    assert Image.open(tmp_path / "arc_86.png").size == (220, 130)
    assert Image.open(tmp_path / "reel.png").size == (95, 95)
    assert Image.open(tmp_path / "bookmark.png").size == (1000, 112)
    assert Image.open(tmp_path / "tab_deepblue_wide.png").size == (1000, 80)

def test_arc_fill_and_band_color(tmp_path: Path):
    gen_assets.generate(tmp_path)
    # the arc's left end (score 0 side) is painted for any score > 0; right end only for ~100
    a86 = Image.open(tmp_path / "arc_86.png").convert("RGBA")
    a20 = Image.open(tmp_path / "arc_20.png").convert("RGBA")
    # sample a point on the left end of the arc ring
    lx, ly = 18, 118
    assert a86.getpixel((lx, ly))[:3] == (0xf5, 0xc5, 0x18)   # gold at 86
    assert a20.getpixel((lx, ly))[:3] == (0x8a, 0x94, 0xa6)   # gray at 20
    # right end: 86 filled? 86% of the arc ends before the right foot, so the right foot is track only (dim)
    rx, ry = 202, 118
    assert a86.getpixel((rx, ry))[3] < 255 or a86.getpixel((rx, ry))[:3] != (0xf5, 0xc5, 0x18)

def test_bar_gradient_direction(tmp_path: Path):
    gen_assets.generate(tmp_path)
    b = Image.open(tmp_path / "bar_bottom.png").convert("RGBA")
    assert b.getpixel((500, 2))[3] < 20          # transparent at top
    assert b.getpixel((500, 238))[3] > 230       # near-opaque at bottom
    t = Image.open(tmp_path / "bar_top.png").convert("RGBA")
    assert t.getpixel((500, 2))[3] > 230
    assert t.getpixel((500, 138))[3] < 20
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest -q tests/test_gen_assets.py`  Expected: FAIL `No module named gen_assets`

- [ ] **Step 3: Implement**

`cp ~/repos/unraid/kometa/overlays/fonts/Avenir_95_Black.ttf ~/repos/unraid/kometa/overlays/winswatch/fonts/`

`scripts/winswatch/gen_assets.py`:
```python
"""Generate every PNG the Wins Watch overlays use. Deterministic; re-run any time."""
import math, sys
from pathlib import Path
from PIL import Image, ImageDraw
from ww.colors import band, BRAND, DEEP, GOLD, LEAVE_GOLD, RED, GRAY

W, H = 1000, 1500

def _hex(h: str, a: int = 255):
    h = h.lstrip("#"); return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)

def _gradient(width, height, stops, out):
    """stops: list of (y_fraction, alpha 0..255) piecewise-linear. Black."""
    im = Image.new("RGBA", (width, height), (0, 0, 0, 0)); px = im.load()
    for y in range(height):
        f = y / (height - 1)
        for (y0, a0), (y1, a1) in zip(stops, stops[1:]):
            if y0 <= f <= y1:
                a = a0 + (a1 - a0) * ((f - y0) / (y1 - y0) if y1 > y0 else 0); break
        for x in range(width):
            px[x, y] = (0, 0, 0, int(a))
    im.save(out)

def _arc(score: int, out: Path):
    """220x130 half-circle gauge. Track (remainder) + fill in band color, halo baked in."""
    S = 4  # supersample
    w, h = 220 * S, 130 * S
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, cy, r = w // 2, h - 12 * S, 92 * S
    bbox = [cx - r, cy - r, cx + r, cy + r]
    col = band(score)
    track = _hex(GOLD, 97) if score >= 85 else (255, 255, 255, 36)
    halo = (0, 0, 0, 217)
    d.arc(bbox, 180, 360, fill=halo, width=int(15.6 * S))                     # halo (5.4u wider than stroke)
    d.arc(bbox, 180, 360, fill=(8, 10, 14, 235), width=int(9 * S))              # dark base so track reads on white art
    d.arc(bbox, 180, 360, fill=track, width=int(9 * S))
    if score > 0:
        d.arc(bbox, 180, 180 + 180 * score / 100, fill=_hex(col), width=int(9 * S))
    im = im.resize((220, 130), Image.LANCZOS); im.save(out)

def _line_and_tab(color, plate_w, out, notch=False, plate_h=64, total_h=80):
    im = Image.new("RGBA", (W, total_h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 16], fill=_hex(color))
    x0, y0, x1, y1 = 40, 0, 40 + plate_w, 16 + plate_h
    if notch:
        d.polygon([(x0, y0), (x1, y0), (x1, y1), ((x0 + x1) // 2, y1 - 26), (x0, y1)], fill=_hex(color))
    else:
        d.rounded_rectangle([x0, y0, x1, y1], radius=15, fill=_hex(color))
        d.rectangle([x0, y0, x1, y0 + 20], fill=_hex(color))  # square the top corners
    im.save(out)

def _edge(color, out):
    im = Image.new("RGBA", (W, 16), _hex(color)); im.save(out)

def _reel(out):
    S = 4; n = 95 * S
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, n - 1, n - 1], fill=(0, 0, 0, 184), outline=_hex(GOLD), width=6 * S)
    inset = 16 * S
    for k in range(12):  # dotted inner ring
        a = 2 * math.pi * k / 12
        cx, cy = n / 2 + (n / 2 - inset) * math.cos(a), n / 2 + (n / 2 - inset) * math.sin(a)
        rr = 3.2 * S; d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=_hex(GOLD))
    im.resize((95, 95), Image.LANCZOS).save(out)

def generate(out_dir: Path) -> list[Path]:
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    _gradient(W, 240, [(0.0, 0), (0.30, 89), (0.72, 235), (1.0, 235)], out_dir / "bar_bottom.png")
    _gradient(W, 140, [(0.0, 230), (0.30, 230), (0.72, 89), (1.0, 0)], out_dir / "bar_top.png")
    for s in range(101):
        _arc(s, out_dir / f"arc_{s:02d}.png")
    _edge(GRAY, out_dir / "edge_gray.png"); _edge(RED, out_dir / "edge_red.png")
    _line_and_tab(BRAND, 230, out_dir / "tab_lightblue_narrow.png"); _line_and_tab(BRAND, 330, out_dir / "tab_lightblue_wide.png")
    _line_and_tab(DEEP, 230, out_dir / "tab_deepblue_narrow.png"); _line_and_tab(DEEP, 330, out_dir / "tab_deepblue_wide.png")
    _line_and_tab(LEAVE_GOLD, 300, out_dir / "bookmark.png", notch=True, plate_h=96, total_h=112)
    _reel(out_dir / "reel.png")
    return sorted(out_dir.glob("*.png"))

if __name__ == "__main__":
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "kometa/overlays/winswatch/assets"
    print(f"wrote {len(generate(dest))} files to {dest}")
```

- [ ] **Step 4: Run tests; generate the real assets**

Run: `pytest -q tests/test_gen_assets.py` → 3 passed. Then `python gen_assets.py` → `wrote 112 files to …/kometa/overlays/winswatch/assets`. Open `arc_86.png`, `arc_42.png`, `bookmark.png` with the Read tool and confirm they look like the artifact (gold arc, gray arc, notched gold tab).

- [ ] **Step 5: Commit**

```bash
git add scripts/winswatch kometa/overlays/winswatch && git commit -m "feat(winswatch): asset generator + generated PNGs"
```

---

### Task 3: Overlay generator (gauge + top edge)

**Files:**
- Create: `scripts/winswatch/gen_overlays.py`
- Test: `scripts/winswatch/tests/test_gen_overlays.py`
- Output: `kometa/overlays/winswatch/generated/gauge.yml`, `kometa/overlays/winswatch/generated/topedge.yml`

**Interfaces:**
- Produces: `gen_overlays.gauge_yaml() -> dict`, `gen_overlays.topedge_yaml() -> dict`, `gen_overlays.write(out_dir)`.
- Group names used by later hand-written files: `topedge_bg`, `topedge_txt`. Font path `config/winswatch/fonts/Avenir_95_Black.ttf`.

- [ ] **Step 1: Write the failing test**

`scripts/winswatch/tests/test_gen_overlays.py`:
```python
import yaml
import gen_overlays
from ww.buckets import VOTE_BUCKETS

FONT = "config/winswatch/fonts/Avenir_95_Black.ttf"

def test_gauge_arcs_cover_every_tenth():
    g = gen_overlays.gauge_yaml()["overlays"]
    arcs = {k: v for k, v in g.items() if k.startswith("ww_arc_")}
    assert len(arcs) == 101
    lo = [v["value_filter"]["user_rating.gte"] for v in arcs.values()]
    assert sorted(lo) == [round(i / 10, 1) for i in range(101)]
    a86 = arcs["ww_arc_86"]
    assert a86["overlay"]["file"] == "config/winswatch/assets/arc_86.png"
    assert a86["value_filter"] == {"user_rating.gte": 8.6, "user_rating.lt": 8.7}
    assert a86["overlay"]["horizontal_align"] == "right" and a86["overlay"]["vertical_offset"] == 55

def test_gauge_number_and_votes():
    g = gen_overlays.gauge_yaml()["overlays"]
    assert g["ww_num_white"]["overlay"]["name"] == "text(<<user_rating%>>)"
    assert g["ww_num_white"]["value_filter"] == {"user_rating.gte": 0.1, "user_rating.lt": 8.5}
    assert g["ww_num_gold"]["value_filter"] == {"user_rating.gte": 8.5}
    assert g["ww_num_gold"]["overlay"]["font_color"] == "#f5c518"
    votes = [k for k in g if k.startswith("ww_votes_")]
    assert len(votes) == 2 * len(VOTE_BUCKETS)
    v = g["ww_votes_1.6M_white"]
    assert v["plex_search"] == {"all": {"label": "Votes_1.6M"}}
    assert v["overlay"]["name"] == "text(1.6M RATINGS)"
    assert v["value_filter"] == {"user_rating.lt": 8.5}

def test_topedge_precedence():
    t = gen_overlays.topedge_yaml()["overlays"]
    bm = t["ww_bookmark_bg"]
    assert bm["overlay"]["group"] == "topedge_bg" and bm["overlay"]["weight"] == 300
    assert bm["plex_search"] == {"any": {"label": [f"DaysLeft_{i}" for i in range(1, 31)]}}
    assert t["ww_bookmark_txt_12"]["overlay"]["name"] == "text(LEAVING 12 DAYS)"
    assert t["ww_bookmark_txt_1"]["overlay"]["name"] == "text(LEAVING 1 DAY)"
    assert t["ww_bookmark_txt_12"]["overlay"]["group"] == "topedge_txt"
    assert t["ww_tab_newep_Wed"]["overlay"]["name"] == "text(NEW EP WED)"
    assert t["ww_tab_newep_Wed"]["overlay"]["weight"] == 200
    assert t["ww_tab_bg_newep"]["overlay"]["file"] == "config/winswatch/assets/tab_lightblue_narrow.png"
    assert t["ww_tab_returnsin_13"]["overlay"]["name"] == "text(RETURNS IN 13 DAYS)"
    assert t["ww_tab_returns_Nov"]["overlay"]["name"] == "text(RETURNS NOV)"
    assert t["ww_tab_returns_2027"]["overlay"]["name"] == "text(RETURNS 2027)"
    assert t["ww_tab_returns_TBA"]["overlay"]["name"] == "text(RETURNS TBA)"
    assert t["ww_edge_ended"]["filters"] == {"tmdb_status": "ended"} and t["ww_edge_ended"]["overlay"]["weight"] == 100
    assert t["ww_edge_canceled"]["filters"] == {"tmdb_status": "canceled"} and t["ww_edge_canceled"]["overlay"]["weight"] == 110
    # every text overlay in topedge_txt is paired with a bg of equal weight class
    for k, v in t.items():
        if v["overlay"].get("group") == "topedge_txt":
            assert v["overlay"]["font"] == FONT

def test_write_roundtrip(tmp_path):
    gen_overlays.write(tmp_path)
    for f in ("gauge.yml", "topedge.yml"):
        data = yaml.safe_load((tmp_path / f).read_text())
        assert "overlays" in data and len(data["overlays"]) > 50
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest -q tests/test_gen_overlays.py`  Expected: FAIL `No module named gen_overlays`

- [ ] **Step 3: Implement**

`scripts/winswatch/gen_overlays.py`:
```python
"""Emit the two generated Kometa overlay files: gauge.yml (arcs, number, votes) and topedge.yml (status tabs, bookmark, edge lines)."""
import sys
from pathlib import Path
import yaml
from ww.buckets import VOTE_BUCKETS, DOW, MON
from ww.colors import GOLD, WHITE, INK, LEAVE_INK

FONT = "config/winswatch/fonts/Avenir_95_Black.ttf"
ASSETS = "config/winswatch/assets"

def _txt(name, size, color, **pos):
    o = {"name": f"text({name})", "font": FONT, "font_size": size, "font_color": color, "back_color": "#00000000"}
    o.update(pos); return o

def gauge_yaml() -> dict:
    ov = {}
    for s in range(101):
        lo = round(s / 10, 1)
        vf = {"user_rating.gte": lo} if s == 100 else {"user_rating.gte": lo, "user_rating.lt": round((s + 1) / 10, 1)}
        ov[f"ww_arc_{s:02d}"] = {
            "overlay": {"name": f"ww_arc_{s:02d}", "file": f"{ASSETS}/arc_{s:02d}.png",
                        "horizontal_align": "right", "horizontal_offset": 40, "vertical_align": "bottom", "vertical_offset": 55},
            "plex_all": True, "value_filter": vf}
    num = dict(horizontal_align="right", horizontal_offset=40, vertical_align="bottom", vertical_offset=62, back_width=220, back_height=90)
    ov["ww_num_white"] = {"overlay": _txt("<<user_rating%>>", 62, WHITE, **num), "plex_all": True, "value_filter": {"user_rating.gte": 0.1, "user_rating.lt": 8.5}}
    ov["ww_num_gold"] = {"overlay": _txt("<<user_rating%>>", 62, GOLD, **num), "plex_all": True, "value_filter": {"user_rating.gte": 8.5}}
    vpos = dict(horizontal_align="right", horizontal_offset=40, vertical_align="bottom", vertical_offset=22, back_width=220, back_height=40)
    for b in VOTE_BUCKETS:
        for tone, color, vf in (("white", WHITE, {"user_rating.lt": 8.5}), ("gold", GOLD, {"user_rating.gte": 8.5})):
            ov[f"ww_votes_{b}_{tone}"] = {"overlay": _txt(f"{b} RATINGS", 31, color, **vpos),
                                          "plex_search": {"all": {"label": f"Votes_{b}"}}, "value_filter": vf}
    return {"overlays": ov}

def topedge_yaml() -> dict:
    ov = {}
    bg = dict(horizontal_align="center", horizontal_offset=0, vertical_align="top", vertical_offset=0)
    def bg_over(name, file, weight, search=None, filters=None):
        o = {"overlay": {"name": name, "file": f"{ASSETS}/{file}", "group": "topedge_bg", "weight": weight, **bg}}
        if search: o["plex_search"] = search
        else: o["plex_all"] = True
        if filters: o["filters"] = filters
        return o
    def txt_over(name, text, weight, search, color=WHITE, width=330, ink_offset=16):
        return {"overlay": {**_txt(text, 42, color, horizontal_align="left", horizontal_offset=40, vertical_align="top",
                                   vertical_offset=ink_offset, back_width=width, back_height=64),
                            "group": "topedge_txt", "weight": weight},
                "plex_search": search}
    days = [f"DaysLeft_{i}" for i in range(1, 31)]
    ov["ww_bookmark_bg"] = bg_over("ww_bookmark_bg", "bookmark.png", 300, {"any": {"label": days}})
    for i in range(1, 31):
        ov[f"ww_bookmark_txt_{i}"] = txt_over(f"ww_bookmark_txt_{i}", f"LEAVING {i} DAY" + ("" if i == 1 else "S"), 300 + i,
                                              {"all": {"label": f"DaysLeft_{i}"}}, color=LEAVE_INK, width=300, ink_offset=22)
    newep = [f"NewEp_{d}" for d in DOW]
    ov["ww_tab_bg_newep"] = bg_over("ww_tab_bg_newep", "tab_lightblue_narrow.png", 210, {"any": {"label": newep}})
    for d in DOW:
        ov[f"ww_tab_newep_{d}"] = txt_over(f"ww_tab_newep_{d}", f"NEW EP {d.upper()}", 200, {"all": {"label": f"NewEp_{d}"}}, color=INK, width=230)
    retin = [f"ReturnsIn_{i}" for i in range(8, 31)]
    ov["ww_tab_bg_returnsin"] = bg_over("ww_tab_bg_returnsin", "tab_deepblue_wide.png", 205, {"any": {"label": retin}})
    for i in range(8, 31):
        ov[f"ww_tab_returnsin_{i}"] = txt_over(f"ww_tab_returnsin_{i}", f"RETURNS IN {i} DAYS", 200, {"all": {"label": f"ReturnsIn_{i}"}})
    months = [f"Returns_{m}" for m in MON]; years = [f"Returns_{y}" for y in range(2026, 2031)]
    ov["ww_tab_bg_returns"] = bg_over("ww_tab_bg_returns", "tab_deepblue_wide.png", 204, {"any": {"label": months + years + ["Returns_TBA"]}})
    for m in MON:
        ov[f"ww_tab_returns_{m}"] = txt_over(f"ww_tab_returns_{m}", f"RETURNS {m.upper()}", 200, {"all": {"label": f"Returns_{m}"}})
    for y in range(2026, 2031):
        ov[f"ww_tab_returns_{y}"] = txt_over(f"ww_tab_returns_{y}", f"RETURNS {y}", 200, {"all": {"label": f"Returns_{y}"}})
    ov["ww_tab_returns_TBA"] = txt_over("ww_tab_returns_TBA", "RETURNS TBA", 200, {"all": {"label": "Returns_TBA"}})
    ov["ww_edge_canceled"] = bg_over("ww_edge_canceled", "edge_red.png", 110, filters={"tmdb_status": "canceled"})
    ov["ww_edge_ended"] = bg_over("ww_edge_ended", "edge_gray.png", 100, filters={"tmdb_status": "ended"})
    return {"overlays": ov}

def write(out_dir: Path):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in (("gauge.yml", gauge_yaml()), ("topedge.yml", topedge_yaml())):
        (out_dir / name).write_text("# GENERATED by scripts/winswatch/gen_overlays.py — do not edit\n" + yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

if __name__ == "__main__":
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "kometa/overlays/winswatch/generated"
    write(dest); print(f"wrote gauge.yml + topedge.yml to {dest}")
```

- [ ] **Step 4: Run tests; generate**

Run: `pytest -q tests/test_gen_overlays.py` → 4 passed. `python gen_overlays.py`.

- [ ] **Step 5: Commit**

```bash
git add scripts/winswatch kometa/overlays/winswatch/generated && git commit -m "feat(winswatch): generated gauge + top-edge overlay files"
```

---

### Task 4: Hand-written overlay files + lab config template

**Files:**
- Create: `kometa/overlays/winswatch/movies.yml`, `shows.yml`, `seasons.yml`, `episodes.yml`, `kometa/lab.yml.template`, `scripts/winswatch/build_lab_config.py`
- Test: `scripts/winswatch/tests/test_lab_config.py`

**Interfaces:**
- Produces: `build_lab_config.build(prod_config_path: Path, template_path: Path, movie_section_name: str, show_section_name: str) -> str` (YAML text).

- [ ] **Step 1: Write the four overlay files**

`kometa/overlays/winswatch/movies.yml`:
```yaml
# Wins Watch — movie posters. Bottom bar, codec chips (queue), NEW, reel. Gauge/top edge come from generated/.
queues:
  ww_chips:
    - horizontal_align: left
      horizontal_offset: 40
      vertical_align: bottom
      vertical_offset: 30
    - horizontal_align: left
      horizontal_offset: 165
      vertical_align: bottom
      vertical_offset: 30
    - horizontal_align: left
      horizontal_offset: 330
      vertical_align: bottom
      vertical_offset: 30

templates:
  ww_chip:
    optional: [res, hdr, dv, regex, audio_regex]
    ignore_blank_results: true
    plex_all: true
    plex_search:
      all:
        any:
          resolution.regex: <<res>>
        hdr: <<hdr>>
    filters:
      has_dolby_vision: <<dv>>
      filepath.regex: <<regex>>
    overlay:
      name: text(<<label>>)
      font: config/winswatch/fonts/Avenir_95_Black.ttf
      font_size: 46
      font_color: <<color>>
      back_color: "#00000000"
      queue: ww_chips
      weight: <<weight>>
  ww_audio:
    ignore_blank_results: true
    plex_all: true
    filters:
      - audio_track_title.regex: <<regex>>
      - filepath.regex: <<regex>>
    overlay:
      name: text(<<label>>)
      font: config/winswatch/fonts/Avenir_95_Black.ttf
      font_size: 46
      font_color: <<color>>
      back_color: "#00000000"
      queue: ww_chips
      weight: <<weight>>

overlays:
  ww_bar:
    plex_all: true
    overlay:
      name: ww_bar
      file: config/winswatch/assets/bar_bottom.png
      horizontal_align: center
      horizontal_offset: 0
      vertical_align: bottom
      vertical_offset: 0

  # --- video (group: one wins) ---
  ww_v_4k:    {template: {name: ww_chip, label: 4K,    color: "#ffffff", weight: 300, res: "(?i)2160|4k"},   overlay: {group: ww_video, weight: 40}}
  ww_v_1080p: {template: {name: ww_chip, label: 1080p, color: "#ffffff", weight: 300, res: "(?i)1080|2k"},   overlay: {group: ww_video, weight: 30}}
  ww_v_720p:  {template: {name: ww_chip, label: 720p,  color: "#ffffff", weight: 300, res: "(?i)720|hd"},    overlay: {group: ww_video, weight: 20}}
  ww_v_sd:    {template: {name: ww_chip, label: SD,    color: "#ffffff", weight: 300, res: "(?i)576|480|sd"},overlay: {group: ww_video, weight: 10}}

  # --- HDR flavor (group: one wins) ---
  ww_h_dvhdr: {template: {name: ww_chip, label: "DV·HDR", color: "#c084fc", weight: 200, dv: true,  regex: '(?i)\bdv(.hdr10?\b)'}, overlay: {group: ww_hdr, weight: 40}}
  ww_h_dv:    {template: {name: ww_chip, label: DV,       color: "#a78bfa", weight: 200, dv: true},                                   overlay: {group: ww_hdr, weight: 30}}
  ww_h_hdrp:  {template: {name: ww_chip, label: HDR10+,   color: "#fbbf24", weight: 200, hdr: true, regex: '(?i)\bhdr10(\+|p(lus)?\b)'}, overlay: {group: ww_hdr, weight: 20}}
  ww_h_hdr:   {template: {name: ww_chip, label: HDR,      color: "#e8b84a", weight: 200, hdr: true},                                  overlay: {group: ww_hdr, weight: 10}}

  # --- audio (group: one wins) — regexes copied from Kometa's audio_codec default ---
  ww_a_truehd_atmos: {template: {name: ww_audio, label: ATMOS,     color: "#60a5fa", weight: 100, regex: '(?i)^(?=.*\btrue[ ._-]?hd(\b|\d))(?=.*\batmos(\b|\d))'}, overlay: {group: ww_audio, weight: 160}}
  ww_a_dtsx:         {template: {name: ww_audio, label: "DTS:X",   color: "#f87171", weight: 100, regex: '(?i)\b(dts[-_. ]?x7?)\b(?![-_. ]?(26[456]))'},          overlay: {group: ww_audio, weight: 150}}
  ww_a_plus_atmos:   {template: {name: ww_audio, label: DD+ ATMOS, color: "#7dd3fc", weight: 100, regex: '(?i)^(?=.*\b((dd[p+])|(dolby[ ._-]digital[ ._-]plus)|(e[ ._-]?ac3)\b))(?=.*\batmos(\b|\d))'}, overlay: {group: ww_audio, weight: 140}}
  ww_a_atmos:        {template: {name: ww_audio, label: ATMOS,     color: "#60a5fa", weight: 100, regex: '(?i)\batmos(\b|\d)'},                                    overlay: {group: ww_audio, weight: 130}}
  ww_a_truehd:       {template: {name: ww_audio, label: TRUEHD,    color: "#2dd4bf", weight: 100, regex: '(?i)\btrue[ ._-]?hd(\b|\d)'},                            overlay: {group: ww_audio, weight: 120}}
  ww_a_dtshd:        {template: {name: ww_audio, label: DTS-HD MA, color: "#fb923c", weight: 100, regex: '(?i)\bdts[ ._-]?(hd[ ._-])?(ma|xll|hd)(\b|\d)(?![ ._-]hra)'}, overlay: {group: ww_audio, weight: 110}}
  ww_a_flac:         {template: {name: ww_audio, label: FLAC,      color: "#9ca3af", weight: 100, regex: '(?i)\bflac(\b|\d)'},                                    overlay: {group: ww_audio, weight: 100}}
  ww_a_pcm:          {template: {name: ww_audio, label: PCM,       color: "#9ca3af", weight: 100, regex: '(?i)\bl?pcm(\b|\d)'},                                   overlay: {group: ww_audio, weight: 90}}
  ww_a_ddp:          {template: {name: ww_audio, label: DD+,       color: "#4ade80", weight: 100, regex: '(?i)\b(dd[p+])|(dolby[ ._-]digital[ ._-]plus)|(e[ ._-]?ac3)\b'}, overlay: {group: ww_audio, weight: 70}}
  ww_a_dts:          {template: {name: ww_audio, label: DTS,       color: "#ef4444", weight: 100, regex: '(?i)\bdts(\b|\d)'},                                     overlay: {group: ww_audio, weight: 50}}
  ww_a_dd:           {template: {name: ww_audio, label: DD,        color: "#a3a3a3", weight: 100, regex: '(?i)\b(dd)|(ac3)|(dolby)(\b|\d)'},                      overlay: {group: ww_audio, weight: 40}}
  ww_a_aac:          {template: {name: ww_audio, label: AAC,       color: "#9ca3af", weight: 100, regex: '(?i)\b(aac|stereo|2\.0)\b'},                            overlay: {group: ww_audio, weight: 30}}
  ww_a_opus:         {template: {name: ww_audio, label: OPUS,      color: "#9ca3af", weight: 100, regex: '(?i)\b(?<!-)OPUS(\b|\d)'},                              overlay: {group: ww_audio, weight: 10}}

  ww_new:
    plex_search:
      all:
        added: 14
        label.not: [DaysLeft_1, DaysLeft_2, DaysLeft_3, DaysLeft_4, DaysLeft_5, DaysLeft_6, DaysLeft_7, DaysLeft_8, DaysLeft_9, DaysLeft_10,
                    DaysLeft_11, DaysLeft_12, DaysLeft_13, DaysLeft_14, DaysLeft_15, DaysLeft_16, DaysLeft_17, DaysLeft_18, DaysLeft_19, DaysLeft_20,
                    DaysLeft_21, DaysLeft_22, DaysLeft_23, DaysLeft_24, DaysLeft_25, DaysLeft_26, DaysLeft_27, DaysLeft_28, DaysLeft_29, DaysLeft_30]
    overlay:
      name: text(NEW)
      font: config/winswatch/fonts/Avenir_95_Black.ttf
      font_size: 58
      font_color: "#06131c"
      back_color: "#5ac8fa"
      back_radius: 15
      back_padding: 18
      horizontal_align: left
      horizontal_offset: 40
      vertical_align: top
      vertical_offset: 40

  ww_reel:
    plex_all: true
    filters:
      tmdb_keyword: aftercreditsstinger, duringcreditsstinger
    overlay:
      name: ww_reel
      file: config/winswatch/assets/reel.png
      horizontal_align: right
      horizontal_offset: 40
      vertical_align: top
      vertical_offset: 40
```

Disproven in Task 9: Kometa raises `'group' and 'queue' cannot be used together`; chips became PNG rows.

`kometa/overlays/winswatch/shows.yml`:
```yaml
# Wins Watch — show posters. Bottom bar, streaming service (no codecs), NEW (lower, under the tab zone), reel.
templates:
  ww_service:
    plex_search:
      any:
        network: <<networks>>
    overlay:
      name: text(<<label>>)
      font: config/winswatch/fonts/Avenir_95_Black.ttf
      font_size: 46
      font_color: <<color>>
      back_color: "#00000000"
      horizontal_align: left
      horizontal_offset: 40
      vertical_align: bottom
      vertical_offset: 30
      group: ww_service
      weight: <<weight>>

overlays:
  ww_bar:
    plex_all: true
    overlay:
      name: ww_bar
      file: config/winswatch/assets/bar_bottom.png
      horizontal_align: center
      horizontal_offset: 0
      vertical_align: bottom
      vertical_offset: 0

  ww_s_netflix:    {template: {name: ww_service, label: NETFLIX,        color: "#e50914", weight: 100, networks: [Netflix]}}
  ww_s_prime:      {template: {name: ww_service, label: PRIME VIDEO,    color: "#00a8e1", weight: 99,  networks: [Prime Video, Amazon, Amazon Prime Video, Freevee]}}
  ww_s_apple:      {template: {name: ww_service, label: APPLE TV+,      color: "#f5f5f7", weight: 98,  networks: [Apple TV+, Apple TV]}}
  ww_s_hbo:        {template: {name: ww_service, label: HBO,            color: "#ffffff", weight: 97,  networks: [HBO]}}
  ww_s_max:        {template: {name: ww_service, label: MAX,            color: "#b535f6", weight: 96,  networks: [Max, HBO Max]}}
  ww_s_hulu:       {template: {name: ww_service, label: HULU,           color: "#1ce783", weight: 95,  networks: [Hulu]}}
  ww_s_disney:     {template: {name: ww_service, label: DISNEY+,        color: "#5b9bff", weight: 94,  networks: [Disney+]}}
  ww_s_paramount:  {template: {name: ww_service, label: PARAMOUNT+,     color: "#0064ff", weight: 93,  networks: [Paramount+, Paramount Network]}}
  ww_s_peacock:    {template: {name: ww_service, label: PEACOCK,        color: "#ffcf00", weight: 92,  networks: [Peacock]}}
  ww_s_fx:         {template: {name: ww_service, label: FX,             color: "#ffffff", weight: 91,  networks: [FX, FXX]}}
  ww_s_showtime:   {template: {name: ww_service, label: SHOWTIME,       color: "#ff2a2a", weight: 90,  networks: [Showtime]}}
  ww_s_amc:        {template: {name: ww_service, label: AMC,            color: "#ffcc00", weight: 89,  networks: [AMC, AMC+]}}
  ww_s_cbs:        {template: {name: ww_service, label: CBS,            color: "#3b82f6", weight: 88,  networks: [CBS]}}
  ww_s_nbc:        {template: {name: ww_service, label: NBC,            color: "#f37021", weight: 87,  networks: [NBC]}}
  ww_s_abc:        {template: {name: ww_service, label: ABC,            color: "#ffffff", weight: 86,  networks: [ABC]}}
  ww_s_fox:        {template: {name: ww_service, label: FOX,            color: "#3b82f6", weight: 85,  networks: [FOX]}}
  ww_s_bbc:        {template: {name: ww_service, label: BBC,            color: "#ffffff", weight: 84,  networks: [BBC One, BBC Two, BBC Three, BBC]}}
  ww_s_comedy:     {template: {name: ww_service, label: COMEDY CENTRAL, color: "#ffc800", weight: 83,  networks: [Comedy Central]}}
  ww_s_crunchy:    {template: {name: ww_service, label: CRUNCHYROLL,    color: "#f47521", weight: 82,  networks: [Crunchyroll]}}
  ww_s_bravo:      {template: {name: ww_service, label: BRAVO,          color: "#8b5cf6", weight: 81,  networks: [Bravo]}}
  ww_s_syfy:       {template: {name: ww_service, label: SYFY,           color: "#a855f7", weight: 80,  networks: [Syfy]}}
  ww_s_cw:         {template: {name: ww_service, label: THE CW,         color: "#22c55e", weight: 79,  networks: [The CW]}}
  ww_s_mgm:        {template: {name: ww_service, label: MGM+,           color: "#f5c518", weight: 78,  networks: [MGM+]}}
  ww_s_starz:      {template: {name: ww_service, label: STARZ,          color: "#ffffff", weight: 77,  networks: [Starz]}}
  ww_s_adultswim:  {template: {name: ww_service, label: ADULT SWIM,     color: "#ffffff", weight: 76,  networks: [Adult Swim]}}
  ww_s_usa:        {template: {name: ww_service, label: USA NETWORK,    color: "#3b82f6", weight: 75,  networks: [USA Network]}}

  ww_new:
    plex_search:
      all:
        episode_added: 14
        label.not: [DaysLeft_1, DaysLeft_2, DaysLeft_3, DaysLeft_4, DaysLeft_5, DaysLeft_6, DaysLeft_7, DaysLeft_8, DaysLeft_9, DaysLeft_10,
                    DaysLeft_11, DaysLeft_12, DaysLeft_13, DaysLeft_14, DaysLeft_15, DaysLeft_16, DaysLeft_17, DaysLeft_18, DaysLeft_19, DaysLeft_20,
                    DaysLeft_21, DaysLeft_22, DaysLeft_23, DaysLeft_24, DaysLeft_25, DaysLeft_26, DaysLeft_27, DaysLeft_28, DaysLeft_29, DaysLeft_30]
    overlay:
      name: text(NEW)
      font: config/winswatch/fonts/Avenir_95_Black.ttf
      font_size: 58
      font_color: "#06131c"
      back_color: "#5ac8fa"
      back_radius: 15
      back_padding: 18
      horizontal_align: left
      horizontal_offset: 40
      vertical_align: top
      vertical_offset: 100

  ww_reel:
    plex_all: true
    filters:
      tmdb_keyword: aftercreditsstinger, duringcreditsstinger
    overlay:
      name: ww_reel
      file: config/winswatch/assets/reel.png
      horizontal_align: right
      horizontal_offset: 40
      vertical_align: top
      vertical_offset: 40
```

`kometa/overlays/winswatch/seasons.yml`:
```yaml
# Wins Watch — season posters: NEW SEASON tag only.
overlays:
  ww_new_season:
    builder_level: season
    plex_search:
      all:
        episode_added: 14
    overlay:
      name: text(NEW SEASON)
      font: config/winswatch/fonts/Avenir_95_Black.ttf
      font_size: 58
      font_color: "#06131c"
      back_color: "#5ac8fa"
      back_radius: 15
      back_padding: 18
      horizontal_align: left
      horizontal_offset: 40
      vertical_align: bottom
      vertical_offset: 40
```

`kometa/overlays/winswatch/episodes.yml`: same as `movies.yml`'s queue/templates/video/HDR/audio blocks with these changes — every overlay gets `builder_level: episode`; the queue positions are `vertical_align: top, vertical_offset: 34` (x 40/165/330); `ww_bar` uses `file: config/winswatch/assets/bar_top.png`, `vertical_align: top, vertical_offset: 0`; drop `ww_new` and `ww_reel`; add:
```yaml
  ww_runtime:
    builder_level: episode
    plex_all: true
    overlay:
      name: text(<<runtime>>m)
      font: config/winswatch/fonts/Avenir_95_Black.ttf
      font_size: 46
      font_color: "#ffffff"
      back_color: "#00000000"
      horizontal_align: right
      horizontal_offset: 40
      vertical_align: top
      vertical_offset: 34
```
(Write the file out in full — copy the blocks, do not reference movies.yml from YAML.)

- [ ] **Step 2: Write the lab config template + builder test**

`kometa/lab.yml.template`:
```yaml
# GENERATED from config.yml by scripts/winswatch/build_lab_config.py — lab libraries only. Never point this at Movies / TV Shows.
plex: __PLEX__
tmdb: __TMDB__
mdblist: __MDBLIST__
settings:
  cache: true
  cache_expiration: 60
  run_order: [overlays, operations]
  overlay_artwork_filetype: webp_lossy
  overlay_artwork_quality: 90
  show_missing: false
  show_unmanaged: false
libraries:
  __MOVIE_LIB__:
    remove_overlays: false
    reapply_overlays: false
    overlay_files:
      - file: config/winswatch/movies.yml
      - file: config/winswatch/generated/gauge.yml
      - file: config/winswatch/generated/topedge.yml
    operations:
      mass_critic_rating_update: mdb_metacritic
      mass_audience_rating_update: mdb_letterboxd
  __SHOW_LIB__:
    remove_overlays: false
    reapply_overlays: false
    overlay_files:
      - file: config/winswatch/shows.yml
      - file: config/winswatch/seasons.yml
      - file: config/winswatch/episodes.yml
      - file: config/winswatch/generated/gauge.yml
      - file: config/winswatch/generated/topedge.yml
    operations:
      mass_critic_rating_update: mdb_metacritic
      mass_audience_rating_update: mdb_trakt
```

`scripts/winswatch/tests/test_lab_config.py`:
```python
import yaml, textwrap
from pathlib import Path
import build_lab_config

def test_build_fills_blocks_and_libraries(tmp_path: Path):
    prod = tmp_path / "config.yml"
    prod.write_text(textwrap.dedent("""
      plex: {url: http://192.168.0.20:32400, token: abc, timeout: 60}
      tmdb: {apikey: tkey, language: en}
      mdblist: {apikey: mkey}
      libraries:
        Movies: {collection_files: []}
    """))
    tpl = Path(__file__).resolve().parents[3] / "kometa/lab.yml.template"
    out = yaml.safe_load(build_lab_config.build(prod, tpl, "Wins Watch Lab", "Wins Watch Lab TV"))
    assert out["plex"]["token"] == "abc" and out["tmdb"]["apikey"] == "tkey" and out["mdblist"]["apikey"] == "mkey"
    assert set(out["libraries"]) == {"Wins Watch Lab", "Wins Watch Lab TV"}
    assert "Movies" not in out["libraries"] and "TV Shows" not in out["libraries"]
    files = [f["file"] for f in out["libraries"]["Wins Watch Lab"]["overlay_files"]]
    assert files == ["config/winswatch/movies.yml", "config/winswatch/generated/gauge.yml", "config/winswatch/generated/topedge.yml"]
```

- [ ] **Step 3: Run to verify it fails** → `No module named build_lab_config`

- [ ] **Step 4: Implement**

`scripts/winswatch/build_lab_config.py`:
```python
"""Build lab.yml from the production config.yml: copy plex/tmdb/mdblist, substitute lab library names. Refuses production library names."""
import sys
from pathlib import Path
import yaml

PROD_LIBS = {"Movies", "TV Shows"}

def build(prod_config: Path, template: Path, movie_lib: str, show_lib: str) -> str:
    if movie_lib in PROD_LIBS or show_lib in PROD_LIBS:
        raise SystemExit("refusing to build a lab config for a production library")
    prod = yaml.safe_load(Path(prod_config).read_text())
    text = Path(template).read_text()
    for key in ("plex", "tmdb", "mdblist"):
        text = text.replace(f"__{key.upper()}__", yaml.safe_dump(prod[key], default_flow_style=True).strip())
    return text.replace("__MOVIE_LIB__", movie_lib).replace("__SHOW_LIB__", show_lib)

if __name__ == "__main__":
    prod, out = Path(sys.argv[1]), Path(sys.argv[2])
    tpl = Path(__file__).resolve().parents[2] / "kometa/lab.yml.template"
    out.write_text(build(prod, tpl, "Wins Watch Lab", "Wins Watch Lab TV")); print(f"wrote {out}")
```

- [ ] **Step 5: Run tests** → `pytest -q` all pass. Also `python -c "import yaml,glob;[yaml.safe_load(open(f)) for f in glob.glob('../../kometa/overlays/winswatch/*.yml')]"` parses all four files.

- [ ] **Step 6: Commit**

```bash
git add kometa scripts/winswatch && git commit -m "feat(winswatch): hand-written overlay files and lab config builder"
```

---

### Task 5: Plex helper + MDBList + Sonarr clients

**Files:**
- Create: `scripts/winswatch/ww/plexlib.py`, `scripts/winswatch/ww/mdblist.py`, `scripts/winswatch/ww/sonarr.py`
- Test: `scripts/winswatch/tests/test_mdblist.py`, `scripts/winswatch/tests/test_sonarr.py`

**Interfaces:**
- `plexlib.PlexLib(url, token)`: `.section(id)->plexapi LibrarySection`; `.items(section_id)->list[plexapi item]`; `.tmdb_id(item)->str|None`; `.tvdb_id(item)->str|None`; `.set_labels(item, add:set[str], remove_prefixes:tuple[str,...])->bool` (returns True if changed; removes any existing label starting with a prefix that is not in `add`); `.set_user_rating(item, value_0_to_10:float)->bool`.
- `mdblist.fetch(api_key, kind:'movie'|'show', tmdb_id:str, cache:dict)->dict {score:int|None, votes:int}`; `mdblist.load_cache(path)`, `mdblist.save_cache(path, cache)`. Cache entries older than 7 days are refetched.
- `sonarr.series_index(base_url, api_key)->dict[tvdb_id:str, {status:str, next_air:date|None}]`.

- [ ] **Step 1: Write failing tests**

`tests/test_mdblist.py`:
```python
import json, time
from ww import mdblist

class FakeResp:
    def __init__(self, data, status=200): self._d, self.status_code = data, status
    def json(self): return self._d
    def raise_for_status(self):
        if self.status_code >= 400: raise RuntimeError(self.status_code)

def test_fetch_parses_and_caches(monkeypatch):
    calls = []
    def fake_get(url, headers=None, timeout=None):
        calls.append(url)
        return FakeResp({"score": 86, "ratings": [{"source": "imdb", "votes": 793314}, {"source": "letterboxd", "votes": 3645831}, {"source": "trakt", "votes": 50380}]})
    monkeypatch.setattr(mdblist.requests, "get", fake_get)
    cache = {}
    r = mdblist.fetch("k", "movie", "693134", cache)
    assert r == {"score": 86, "votes": 3645831}
    assert "https://api.mdblist.com/tmdb/movie/693134?apikey=k" in calls[0]
    r2 = mdblist.fetch("k", "movie", "693134", cache)
    assert r2 == r and len(calls) == 1          # cached

def test_fetch_missing_score(monkeypatch):
    monkeypatch.setattr(mdblist.requests, "get", lambda *a, **k: FakeResp({"score": None, "ratings": []}))
    assert mdblist.fetch("k", "show", "1", {}) == {"score": None, "votes": 0}

def test_cache_expiry(monkeypatch):
    n = {"c": 0}
    monkeypatch.setattr(mdblist.requests, "get", lambda *a, **k: (n.__setitem__("c", n["c"] + 1), FakeResp({"score": 70, "ratings": []}))[1])
    cache = {"movie:9": {"score": 70, "votes": 0, "fetched": time.time() - 8 * 86400}}
    mdblist.fetch("k", "movie", "9", cache)
    assert n["c"] == 1
```

`tests/test_sonarr.py`:
```python
from datetime import date
from ww import sonarr

class FakeResp:
    def __init__(self, data): self._d = data
    def json(self): return self._d
    def raise_for_status(self): pass

def test_series_index(monkeypatch):
    def fake_get(url, headers=None, params=None, timeout=None):
        if url.endswith("/api/v3/series"):
            return FakeResp([{"id": 1, "tvdbId": 366924, "status": "continuing", "nextAiring": "2026-09-23T02:00:00Z"},
                             {"id": 2, "tvdbId": 371572, "status": "continuing"},
                             {"id": 3, "tvdbId": 396112, "status": "ended", "nextAiring": None}])
        raise AssertionError(url)
    monkeypatch.setattr(sonarr.requests, "get", fake_get)
    idx = sonarr.series_index("http://s:8989", "key")
    assert idx["366924"] == {"status": "continuing", "next_air": date(2026, 9, 23)}
    assert idx["371572"] == {"status": "continuing", "next_air": None}
    assert idx["396112"] == {"status": "ended", "next_air": None}
```

- [ ] **Step 2: Run to verify failure** → import errors.

- [ ] **Step 3: Implement**

`ww/mdblist.py`:
```python
import json, time
from pathlib import Path
import requests

TTL = 7 * 86400

def load_cache(path: Path) -> dict:
    p = Path(path); return json.loads(p.read_text()) if p.exists() else {}

def save_cache(path: Path, cache: dict) -> None:
    Path(path).write_text(json.dumps(cache))

def fetch(api_key: str, kind: str, tmdb_id: str, cache: dict) -> dict:
    key = f"{kind}:{tmdb_id}"; hit = cache.get(key)
    if hit and time.time() - hit.get("fetched", 0) < TTL:
        return {"score": hit["score"], "votes": hit["votes"]}
    r = requests.get(f"https://api.mdblist.com/tmdb/{kind}/{tmdb_id}?apikey={api_key}", headers={"User-Agent": "winswatch/1.0"}, timeout=30)
    r.raise_for_status(); d = r.json()
    votes = max([int(x.get("votes") or 0) for x in d.get("ratings", []) if x.get("source") in ("imdb", "letterboxd", "trakt")] + [0])
    out = {"score": d.get("score"), "votes": votes}
    cache[key] = {**out, "fetched": time.time()}
    return out
```

`ww/sonarr.py`:
```python
from datetime import date, datetime
import requests

def series_index(base_url: str, api_key: str) -> dict:
    r = requests.get(f"{base_url.rstrip('/')}/api/v3/series", headers={"X-Api-Key": api_key}, timeout=60)
    r.raise_for_status()
    out = {}
    for s in r.json():
        nxt = s.get("nextAiring")
        out[str(s["tvdbId"])] = {"status": s.get("status", "continuing"),
                                 "next_air": datetime.fromisoformat(nxt.replace("Z", "+00:00")).date() if nxt else None}
    return out
```

`ww/plexlib.py`:
```python
from plexapi.server import PlexServer

class PlexLib:
    def __init__(self, url: str, token: str):
        self.server = PlexServer(url, token)

    def section(self, section_id: int):
        return self.server.library.sectionByID(int(section_id))

    def items(self, section_id: int):
        return self.section(section_id).all()

    @staticmethod
    def _guid(item, prefix):
        for g in getattr(item, "guids", []) or []:
            if g.id.startswith(prefix):
                return g.id[len(prefix):]
        return None

    def tmdb_id(self, item): return self._guid(item, "tmdb://")
    def tvdb_id(self, item): return self._guid(item, "tvdb://")

    def set_labels(self, item, add: set, remove_prefixes: tuple) -> bool:
        current = {l.tag for l in item.labels}
        stale = {l for l in current if l.startswith(remove_prefixes) and l not in add}
        missing = add - current
        if stale: item.removeLabel(list(stale))
        if missing: item.addLabel(list(missing))
        return bool(stale or missing)

    def set_user_rating(self, item, value: float) -> bool:
        if item.userRating is not None and abs(item.userRating - value) < 0.05:
            return False
        item.rate(value)
        return True
```

- [ ] **Step 4: Run tests** → pass.
- [ ] **Step 5: Commit** `git commit -m "feat(winswatch): plex/mdblist/sonarr clients"`

---

### Task 6: `scores.py` and `airdates.py` CLIs

**Files:**
- Create: `scripts/winswatch/scores.py`, `scripts/winswatch/airdates.py`
- Test: `scripts/winswatch/tests/test_cli.py`

**Interfaces:**
- Both accept `--sections 10,11 [--dry-run] [--env PATH]`. Env keys: `PLEX_URL`, `PLEX_TOKEN`, `MDBLIST_API_KEY`, `SONARR_URL`, `SONARR_API_KEY`, `CACHE_DIR` (default `./cache`).
- `scores.plan(items, fetch, tmdb_id, kind) -> list[(item, rating_or_None, label_or_None)]` (pure; tested).
- `airdates.plan(items, index, tvdb_id, today) -> list[(item, label_or_None)]` (pure; tested).

- [ ] **Step 1: Failing tests**

`tests/test_cli.py`:
```python
from datetime import date
from types import SimpleNamespace as NS
import scores, airdates

def test_scores_plan():
    items = [NS(title="Dune"), NS(title="Nimrods"), NS(title="Unmatched")]
    ids = {"Dune": "1", "Nimrods": "2", "Unmatched": None}
    data = {"1": {"score": 86, "votes": 3645831}, "2": {"score": 71, "votes": 19613}}
    plan = scores.plan(items, lambda kind, tid: data[tid], lambda it: ids[it.title], "movie")
    assert plan[0] == (items[0], 8.6, "Votes_3.5M")
    assert plan[1] == (items[1], 7.1, "Votes_10K")
    assert plan[2] == (items[2], None, None)

def test_airdates_plan():
    items = [NS(title="Reacher"), NS(title="Bear"), NS(title="NoTvdb")]
    tv = {"Reacher": "366924", "Bear": "396112", "NoTvdb": None}
    idx = {"366924": {"status": "continuing", "next_air": date(2026, 9, 23)}, "396112": {"status": "ended", "next_air": None}}
    plan = airdates.plan(items, idx, lambda it: tv[it.title], date(2026, 9, 18))
    assert plan == [(items[0], "NewEp_Wed"), (items[1], None), (items[2], None)]
```

- [ ] **Step 2: Verify failure** → import errors.

- [ ] **Step 3: Implement**

`scores.py`:
```python
"""MDBList score -> Plex user rating (0-10) + Votes_<bucket> label. Idempotent. Never touches sections you don't pass."""
import argparse, os
from pathlib import Path
from dotenv import load_dotenv
from ww.plexlib import PlexLib
from ww import mdblist
from ww.buckets import votes_bucket

def plan(items, fetch, tmdb_id, kind):
    out = []
    for it in items:
        tid = tmdb_id(it)
        if not tid:
            out.append((it, None, None)); continue
        d = fetch(kind, tid)
        rating = round(d["score"] / 10, 1) if d.get("score") is not None else None
        b = votes_bucket(d.get("votes") or 0)
        out.append((it, rating, f"Votes_{b}" if b else None))
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sections", required=True); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--env", default=".env")
    a = ap.parse_args(); load_dotenv(a.env)
    plex = PlexLib(os.environ["PLEX_URL"], os.environ["PLEX_TOKEN"]); key = os.environ["MDBLIST_API_KEY"]
    cache_path = Path(os.environ.get("CACHE_DIR", "cache")) / "mdblist.json"; cache_path.parent.mkdir(exist_ok=True)
    cache = mdblist.load_cache(cache_path)
    for sec in a.sections.split(","):
        section = plex.section(int(sec)); kind = "movie" if section.type == "movie" else "show"
        for it, rating, label in plan(section.all(), lambda k, t: mdblist.fetch(key, k, t, cache), plex.tmdb_id, kind):
            changed = []
            if not a.dry_run:
                if rating is not None and plex.set_user_rating(it, rating): changed.append(f"rating={rating}")
                if plex.set_labels(it, {label} if label else set(), ("Votes_",)): changed.append(f"label={label}")
            print(f"{'DRY ' if a.dry_run else ''}{section.title:>18} | {it.title[:44]:<44} | {rating} | {label} | {' '.join(changed) or 'ok'}")
    mdblist.save_cache(cache_path, cache)

if __name__ == "__main__":
    main()
```

`airdates.py`:
```python
"""Sonarr next-air -> one status label per show (NewEp_/ReturnsIn_/Returns_*). Ended/canceled get no label (Kometa uses tmdb_status)."""
import argparse, os
from datetime import date
from dotenv import load_dotenv
from ww.plexlib import PlexLib
from ww import sonarr
from ww.buckets import airdate_label

PREFIXES = ("NewEp_", "ReturnsIn_", "Returns_")

def plan(items, index, tvdb_id, today):
    out = []
    for it in items:
        s = index.get(tvdb_id(it) or "")
        out.append((it, airdate_label(s["next_air"], s["status"], today) if s else None))
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sections", required=True); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--env", default=".env")
    a = ap.parse_args(); load_dotenv(a.env)
    plex = PlexLib(os.environ["PLEX_URL"], os.environ["PLEX_TOKEN"])
    index = sonarr.series_index(os.environ["SONARR_URL"], os.environ["SONARR_API_KEY"])
    for sec in a.sections.split(","):
        section = plex.section(int(sec))
        if section.type != "show": continue
        for it, label in plan(section.all(), index, plex.tvdb_id, date.today()):
            changed = (not a.dry_run) and plex.set_labels(it, {label} if label else set(), PREFIXES)
            print(f"{'DRY ' if a.dry_run else ''}{section.title:>18} | {it.title[:44]:<44} | {label} | {'changed' if changed else 'ok'}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests** → pass. Smoke against production **read-only**: `python scores.py --sections 1 --dry-run --env /mnt/nastower/appdata/scripts/winswatch/.env | head` (the `.env` is created in Task 7; if it doesn't exist yet, skip this smoke and do it in Task 7).
- [ ] **Step 5: Commit** `git commit -m "feat(winswatch): scores + airdates label CLIs"`

---

### Task 7: Host runner, jobs, deploy

**Files:**
- Create: `scripts/winswatch/host/run.sh`, `scripts/winswatch/host/jobs/labels.sh`, `scripts/winswatch/host/jobs/kometa-lab.sh`, `scripts/winswatch/host/jobs/kometa-lab-remove.sh`, `scripts/winswatch/deploy.sh`, `scripts/winswatch/hostexec.py`

**Interfaces:**
- Server layout: `/mnt/user/appdata/scripts/winswatch/{ww,scores.py,airdates.py,requirements.txt,.env,cache/,host/{run.sh,job.sh,jobs/,last.log}}`; Kometa: `/mnt/user/appdata/Kometa/config/winswatch/{fonts,assets,generated,movies.yml,shows.yml,seasons.yml,episodes.yml}` and `/mnt/user/appdata/Kometa/config/lab.yml`.
- `hostexec.py run <job-name> [--wait]` copies `host/jobs/<job-name>.sh` to `host/job.sh` over NFS, POSTs `/api/v1/user-scripts/winswatch/execute` with `{"wait": true}`, prints the returned `output`, then prints `host/last.log`.

- [ ] **Step 1: Write the scripts**

`host/run.sh`:
```bash
#!/bin/bash
# Called by the Unraid user script "winswatch". Runs whatever host/job.sh currently is.
set -uo pipefail
ROOT=/mnt/user/appdata/scripts/winswatch
LOG=$ROOT/host/last.log
{
  echo "=== $(date -Is) job.sh ==="
  cat "$ROOT/host/job.sh"
  echo "=== output ==="
  bash "$ROOT/host/job.sh"
  echo "=== exit $? ==="
} > "$LOG" 2>&1
cat "$LOG"
```

`host/jobs/labels.sh`:
```bash
#!/bin/bash
# Run scores.py + airdates.py against the lab sections in a throwaway python container.
set -euo pipefail
ROOT=/mnt/user/appdata/scripts/winswatch
SECTIONS=$(cat "$ROOT/host/lab_sections")        # e.g. "10,11" written by create_lab_libraries.py
docker run --rm -v "$ROOT":/app -w /app python:3.12-slim bash -c \
  "pip install -q -r requirements.txt >/dev/null && python scores.py --sections $SECTIONS && python airdates.py --sections $SECTIONS"
```

`host/jobs/kometa-lab.sh`:
```bash
#!/bin/bash
set -euo pipefail
docker run --rm -v /mnt/user/appdata/Kometa/config:/config kometateam/kometa --config /config/lab.yml --run --overlays-only --read-only-config
```

`host/jobs/kometa-lab-remove.sh`:
```bash
#!/bin/bash
# Strip lab overlays (restores Kometa's backed-up originals for the lab libraries only).
set -euo pipefail
sed 's/remove_overlays: false/remove_overlays: true/' /mnt/user/appdata/Kometa/config/lab.yml > /mnt/user/appdata/Kometa/config/lab-remove.yml
docker run --rm -v /mnt/user/appdata/Kometa/config:/config kometateam/kometa --config /config/lab-remove.yml --run --overlays-only --read-only-config
```

`deploy.sh` (run from the repo, on the workstation):
```bash
#!/bin/bash
# Copy scripts + overlay files to the server over NFS. Creates .env on the server from Kometa's .env if missing.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/../.." && pwd)
APP=/mnt/nastower/appdata/scripts/winswatch
KCFG=/mnt/nastower/appdata/Kometa/config
mkdir -p "$APP/host/jobs" "$APP/cache" "$KCFG/winswatch"
rsync -a --delete --exclude .venv --exclude tests --exclude __pycache__ --exclude cache --exclude .env --exclude host/last.log --exclude host/job.sh --exclude host/lab_sections \
  "$REPO/scripts/winswatch/" "$APP/"
rsync -a --delete "$REPO/kometa/overlays/winswatch/" "$KCFG/winswatch/"
chmod +x "$APP"/host/*.sh "$APP"/host/jobs/*.sh
if [ ! -f "$APP/.env" ]; then
  KE="$KCFG/.env"
  v() { grep -m1 "^$1=" "$KE" | cut -d= -f2-; }
  cat > "$APP/.env" <<EOF
PLEX_URL=http://192.168.0.20:32400
PLEX_TOKEN=$(v KOMETA_PlexToken)
MDBLIST_API_KEY=$(v KOMETA_MDBListApiKey)
SONARR_URL=http://192.168.0.30:8989
SONARR_API_KEY=$(v KOMETA_SonarrApiKey)
CACHE_DIR=/app/cache
EOF
  chmod 600 "$APP/.env"; echo "created $APP/.env"
fi
python3 "$REPO/scripts/winswatch/build_lab_config.py" "$KCFG/config.yml" "$KCFG/lab.yml"
echo "deployed to $APP and $KCFG/winswatch; lab.yml written"
```

`hostexec.py`:
```python
"""Run a host job through the Unraid user script 'winswatch'. Usage: python hostexec.py run labels"""
import shutil, subprocess, sys, json
from pathlib import Path
import requests

APP = Path("/mnt/nastower/appdata/scripts/winswatch")
TOKEN = Path.home().joinpath(".config/nastower/api_token").read_text().strip()

def run(job: str):
    src = Path(__file__).parent / "host/jobs" / f"{job}.sh"
    shutil.copy(src, APP / "host/job.sh")
    r = requests.post("http://192.168.0.15:8043/api/v1/user-scripts/winswatch/execute", headers={"Authorization": f"Bearer {TOKEN}"},
                      json={"wait": True}, timeout=1800)
    d = r.json(); print(d.get("output") or d.get("message") or d)
    log = APP / "host/last.log"
    if log.exists(): print(log.read_text()[-6000:])
    return d.get("success", False)

if __name__ == "__main__":
    sys.exit(0 if run(sys.argv[2]) else 1)
```

- [ ] **Step 2: Deploy and prove the hook** — `bash scripts/winswatch/deploy.sh`, then write a trivial job: `printf '#!/bin/bash\necho hello from $(hostname); docker --version\n' > /mnt/nastower/appdata/scripts/winswatch/host/jobs/hello.sh` and `python scripts/winswatch/hostexec.py run hello`. Expected: output contains `hello from NASTower` and a Docker version. If the agent returns "script not found", Task 0 hasn't been done — stop and ask Chase.

- [ ] **Step 3: Read-only smoke of the label scripts on production** (no writes): temporarily write `host/lab_sections` as `1,2` is **not allowed** — instead run `python scripts/winswatch/scores.py --sections 1 --dry-run --env /mnt/nastower/appdata/scripts/winswatch/.env | head -20` from the workstation venv. Expected: 20 lines of `DRY Movies | title | 8.6 | Votes_3.5M | ok`. Confirms Plex + MDBList auth. Same for `airdates.py --sections 2 --dry-run`.

- [ ] **Step 4: Commit** `git commit -m "feat(winswatch): host runner, jobs, deploy"` (hello.sh not committed).

---

### Task 8: Lab media + lab libraries

**Files:**
- Create: `scripts/winswatch/lab_media.py`, `scripts/winswatch/create_lab_libraries.py`, `scripts/winswatch/host/jobs/lab-media.sh` (generated)
- Test: `scripts/winswatch/tests/test_lab_media.py`

**Interfaces:**
- `lab_media.LAB_MOVIES = ["Dune: Part Two", "Scary Movie", "The Holdovers", "Sinners", "Deadpool & Wolverine", "The Dark Knight", "Superbad", "Nimrods", "Home Alone", "Parasite"]`, `lab_media.LAB_SHOWS = ["Reacher", "Severance", "The Bear", "Slow Horses", "The Afterparty"]`.
- `lab_media.symlink_script(paths: dict[str, str]) -> str` where paths maps title → container folder path (`/data/media/movies/X (2024)`), returns bash text that creates `/mnt/user/data/media/_winswatch-lab/{movies,tv}/<basename>` symlinks whose targets are the `/data/media/...` container paths.
- `create_lab_libraries.create(plex_url, token) -> (movie_section_id, show_section_id)`; writes `host/lab_sections` on the NFS share; refuses to run if a library named `Wins Watch Lab` already exists (prints its id instead).

- [ ] **Step 1: Failing test**

`tests/test_lab_media.py`:
```python
import lab_media

def test_symlink_script():
    s = lab_media.symlink_script({"Dune: Part Two": "/data/media/movies/Dune Part Two (2024)", "Reacher": "/data/media/tv/Reacher (2022)"})
    assert "mkdir -p '/mnt/user/data/media/_winswatch-lab/movies' '/mnt/user/data/media/_winswatch-lab/tv'" in s
    assert "ln -sfn '/data/media/movies/Dune Part Two (2024)' '/mnt/user/data/media/_winswatch-lab/movies/Dune Part Two (2024)'" in s
    assert "ln -sfn '/data/media/tv/Reacher (2022)' '/mnt/user/data/media/_winswatch-lab/tv/Reacher (2022)'" in s
    assert "rm -rf" not in s
```

- [ ] **Step 2: Verify failure.**

- [ ] **Step 3: Implement**

`lab_media.py`:
```python
"""Resolve the lab titles' folders from production Plex (read-only) and emit host/jobs/lab-media.sh (symlinks)."""
import os, shlex, sys
from pathlib import Path
from dotenv import load_dotenv
from ww.plexlib import PlexLib

LAB_MOVIES = ["Dune: Part Two", "Scary Movie", "The Holdovers", "Sinners", "Deadpool & Wolverine", "The Dark Knight", "Superbad", "Nimrods", "Home Alone", "Parasite"]
LAB_SHOWS = ["Reacher", "Severance", "The Bear", "Slow Horses", "The Afterparty"]
LAB_ROOT = "/mnt/user/data/media/_winswatch-lab"

def symlink_script(paths: dict) -> str:
    lines = ["#!/bin/bash", "set -euo pipefail", f"mkdir -p {shlex.quote(LAB_ROOT + '/movies')} {shlex.quote(LAB_ROOT + '/tv')}"]
    for title, folder in paths.items():
        sub = "tv" if folder.startswith("/data/media/tv") else "movies"
        lines.append(f"ln -sfn {shlex.quote(folder)} {shlex.quote(f'{LAB_ROOT}/{sub}/{os.path.basename(folder)}')}")
    lines.append(f"ls -la {shlex.quote(LAB_ROOT + '/movies')} {shlex.quote(LAB_ROOT + '/tv')}")
    return "\n".join(lines) + "\n"

def resolve(plex: PlexLib) -> dict:
    out = {}
    for title in LAB_MOVIES:
        m = plex.section(1).search(title=title)
        m = [x for x in m if x.title == title] or m
        if not m: print(f"!! movie not found: {title}"); continue
        out[title] = os.path.dirname(m[0].media[0].parts[0].file)
    for title in LAB_SHOWS:
        s = plex.section(2).search(title=title)
        s = [x for x in s if x.title == title] or s
        if not s: print(f"!! show not found: {title}"); continue
        ep = s[0].episodes()[0]
        f = ep.media[0].parts[0].file          # /data/media/tv/Show (Year)/Season 01/file.mkv
        out[title] = f.split("/Season")[0] if "/Season" in f else os.path.dirname(os.path.dirname(f))
    return out

if __name__ == "__main__":
    load_dotenv(sys.argv[1] if len(sys.argv) > 1 else "/mnt/nastower/appdata/scripts/winswatch/.env")
    plex = PlexLib(os.environ["PLEX_URL"], os.environ["PLEX_TOKEN"])
    paths = resolve(plex)
    dest = Path(__file__).parent / "host/jobs/lab-media.sh"; dest.write_text(symlink_script(paths))
    print(dest.read_text())
```

`create_lab_libraries.py`:
```python
"""Create the two lab libraries via the Plex API, hide them from Home, verify no friend shares include them."""
import os, sys, requests
from pathlib import Path
from dotenv import load_dotenv

MOVIE_LIB, SHOW_LIB = "Wins Watch Lab", "Wins Watch Lab TV"

def _sections(url, token):
    r = requests.get(f"{url}/library/sections", headers={"X-Plex-Token": token, "Accept": "application/json"}, timeout=30); r.raise_for_status()
    return {d["title"]: d["key"] for d in r.json()["MediaContainer"].get("Directory", [])}

def create(url, token):
    have = _sections(url, token)
    if MOVIE_LIB in have or SHOW_LIB in have:
        print(f"already exist: {MOVIE_LIB}={have.get(MOVIE_LIB)} {SHOW_LIB}={have.get(SHOW_LIB)}"); return have.get(MOVIE_LIB), have.get(SHOW_LIB)
    specs = [(MOVIE_LIB, "movie", "tv.plex.agents.movie", "Plex Movie", "/data/media/_winswatch-lab/movies"),
             (SHOW_LIB, "show", "tv.plex.agents.series", "Plex TV Series", "/data/media/_winswatch-lab/tv")]
    for name, typ, agent, scanner, loc in specs:
        r = requests.post(f"{url}/library/sections", headers={"X-Plex-Token": token}, timeout=60,
                          params={"name": name, "type": typ, "agent": agent, "scanner": scanner, "language": "en-US", "location": loc})
        r.raise_for_status(); print(f"created {name}")
    have = _sections(url, token)
    for name in (MOVIE_LIB, SHOW_LIB):   # hide from Home / dashboard
        requests.put(f"{url}/library/sections/{have[name]}/prefs", headers={"X-Plex-Token": token}, params={"includeInGlobal": 0}, timeout=30)
    return have[MOVIE_LIB], have[SHOW_LIB]

def check_shares(token, machine_id, ids):
    r = requests.get(f"https://plex.tv/api/servers/{machine_id}/shared_servers", headers={"X-Plex-Token": token}, timeout=30)
    leaked = [s for s in ids if f'id="{s}"' in r.text and "shared=\"1\"" in r.text]
    print("share check:", "OK — lab libraries not shared" if not leaked else f"!! shared with friends: {leaked} — fix in Plex > Settings > Manage Library Access")

if __name__ == "__main__":
    load_dotenv(sys.argv[1] if len(sys.argv) > 1 else "/mnt/nastower/appdata/scripts/winswatch/.env")
    url, token = os.environ["PLEX_URL"], os.environ["PLEX_TOKEN"]
    m, s = create(url, token)
    Path("/mnt/nastower/appdata/scripts/winswatch/host/lab_sections").write_text(f"{m},{s}\n")
    mid = requests.get(f"{url}/identity", headers={"X-Plex-Token": token, "Accept": "application/json"}, timeout=30).json()["MediaContainer"]["machineIdentifier"]
    check_shares(token, mid, [m, s]); print(f"lab sections: {m},{s}")
```

- [ ] **Step 4: Run** — `pytest -q` passes. Then:
  1. `python lab_media.py` → prints the symlink script (15 `ln -sfn` lines, all targets under `/data/media/`). Review it.
  2. `bash deploy.sh` (copies the new job), then `python hostexec.py run lab-media` → `ls -la` shows 15 symlinks under `_winswatch-lab`.
  3. `python create_lab_libraries.py` → `created Wins Watch Lab`, `created Wins Watch Lab TV`, `share check: OK`, `lab sections: N,M`. Then wait ~2 minutes and confirm with `curl -s "http://192.168.0.20:32400/library/sections/N/all?X-Plex-Token=…" -H 'Accept: application/json' | python3 -c "import json,sys;print(json.load(sys.stdin)['MediaContainer']['size'])"` → 10 movies; TV section → 5 shows. If a title didn't match, fix the match in Plex web (Fix Match) — that's allowed on the lab libraries.
  4. If `share check` reports a leak, stop and tell Chase before continuing.

- [ ] **Step 5: Commit** `git add scripts/winswatch && git commit -m "feat(winswatch): lab media symlinks + lab library creation"`

---

### Task 9: First lab render + review sheet

**Files:**
- Create: `scripts/winswatch/review_sheet.py`
- Modify (only if the run shows a layout bug): `kometa/overlays/winswatch/*.yml`, `scripts/winswatch/gen_assets.py`

**Interfaces:**
- `review_sheet.py --sections N,M --out review.png` downloads every lab poster (plus season posters and first-episode stills) from Plex and tiles them into one PNG with titles.

- [ ] **Step 1: Labels then Kometa**

`python hostexec.py run labels` → expect one line per lab item with `rating=… label=Votes_…` and `NewEp_/Returns_` labels for the shows. Then `python hostexec.py run kometa-lab` → Kometa log ends with `Finished … Run` and no `[ERROR]` lines; look specifically for `Overlay Error`, `font`, and `queue` messages. Typical run: 1–3 minutes.

- [ ] **Step 2: Review sheet**

`review_sheet.py`:
```python
import argparse, os, io, urllib.parse, requests
from PIL import Image, ImageDraw
from dotenv import load_dotenv

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sections", required=True); ap.add_argument("--out", default="review.png"); ap.add_argument("--env", default="/mnt/nastower/appdata/scripts/winswatch/.env")
    a = ap.parse_args(); load_dotenv(a.env); url, tok = os.environ["PLEX_URL"], os.environ["PLEX_TOKEN"]
    H = {"X-Plex-Token": tok, "Accept": "application/json"}
    tiles = []
    for sec in a.sections.split(","):
        for it in requests.get(f"{url}/library/sections/{sec}/all", headers=H, timeout=60).json()["MediaContainer"].get("Metadata", []):
            tiles.append((it["title"], it["thumb"], False))
            if it["type"] == "show":
                for s in requests.get(f"{url}{it['key']}", headers=H, timeout=60).json()["MediaContainer"].get("Metadata", [])[:1]:
                    tiles.append((f"{it['title']} · {s['title']}", s["thumb"], False))
                    eps = requests.get(f"{url}{s['key']}", headers=H, timeout=60).json()["MediaContainer"].get("Metadata", [])
                    if eps: tiles.append((f"{it['title']} · {eps[0]['title'][:24]}", eps[0]["thumb"], True))
    W, Hh = 300, 450; cols = 6; rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * W, rows * (Hh + 26)), "#101014"); d = ImageDraw.Draw(sheet)
    for i, (title, thumb, wide) in enumerate(tiles):
        img = Image.open(io.BytesIO(requests.get(f"{url}/photo/:/transcode?url={urllib.parse.quote(thumb)}&width=600&height={338 if wide else 900}&minSize=1&upscale=1&X-Plex-Token={tok}", timeout=60).content)).convert("RGB")
        img.thumbnail((W, Hh)); x, y = (i % cols) * W, (i // cols) * (Hh + 26)
        sheet.paste(img, (x + (W - img.width) // 2, y)); d.text((x + 4, y + Hh + 6), title[:40], fill="white")
    sheet.save(a.out); print(f"wrote {a.out} with {len(tiles)} tiles")

if __name__ == "__main__":
    main()
```

Run `python review_sheet.py --sections N,M --out /tmp/claude-1000/-home-chase-projects/c0e38624-0c03-4d09-8fb2-8c18939e1b5b/scratchpad/lab_review.png` and open it with the Read tool.

- [ ] **Step 3: Compare against the artifact's Winner row and fix what's off**

Check, in order: (a) chip row order and no duplicate video chips (if broken: split template `queue` and definition `group` as noted in Task 4); (b) gauge sits at the bar's right with the number centered and the votes line under it (adjust `vertical_offset` in `gen_overlays.py`, regenerate, redeploy, rerun); (c) tab text sits inside its plate (adjust `vertical_offset` 16 / `back_width`); (d) NEW absent on the leaving title; (e) shows: service name present, no codecs; (f) episodes: top bar + runtime. Each fix = edit → `bash deploy.sh` → `python hostexec.py run kometa-lab` → new review sheet. Kometa re-renders only items whose overlay set changed; to force a full redraw once, set `reapply_overlays: true` in `lab.yml.template`, rebuild, run, set it back.

- [ ] **Step 4: Force the remaining states for Chase's live review**

Using Plex web on the lab libraries only (Edit → Tags → Labels): add `DaysLeft_3` to The Holdovers; add `DaysLeft_4` to The Afterparty (canceled + leaving); replace Reacher's `NewEp_*` with `ReturnsIn_13`; set Severance to `Returns_2027`; add `Votes_4.6M` to Parasite. Re-run `kometa-lab` and regenerate the review sheet. Then tell Chase the lab libraries are ready to open on TV/phone, with the list of forced states.

- [ ] **Step 5: Commit** `git add scripts/winswatch kometa && git commit -m "feat(winswatch): lab render + review sheet; layout fixes from first run"`

---

### Task 10 (later, on Chase's go): promote to production — NOT part of this plan's execution

Documented so nobody improvises it: in production `config.yml`, delete every existing `overlay_files` entry for Movies and TV Shows, add the same five/three files as `lab.yml.template`, run **once** with `mass_user_rating_update: remove` before switching the slot to `mdb`, set `mass_critic_rating_update: mdb_metacritic`, `mass_audience_rating_update: mdb_letterboxd` (Movies) / `mdb_trakt` (TV), run **once** with `remove_overlays: true`, then set it back and let the 05:00 schedule take over. Point `host/lab_sections` → a new `host/prod_sections` = `1,2` and schedule the `winswatch` user script for 04:00 daily running `labels.sh`. Then delete the lab libraries in Plex and `rm -rf /mnt/user/data/media/_winswatch-lab`.

Also: confirm `TZ` is set in `.env`; pin the label container's requirements (drop pytest/pillow from runtime); point the scheduled user script at a fixed `labels.sh`, not the swappable `job.sh`; gate promotion on a full-library `--overlays-only` timing run; add a `RETURNS TBA` fallback overlay (`tmdb_status: returning`, weight 203) if Chase wants it.
