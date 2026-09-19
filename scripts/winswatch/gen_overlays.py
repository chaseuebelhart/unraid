"""Emit the generated Kometa overlay files:
  gauge.yml          arcs + number + votes line (movies and shows)
  topedge.yml        LEAVING bookmark (movies and shows)
  status.yml         NEW EP / RETURNS tabs + ended/canceled edge lines (shows only: uses tmdb_status)
  chips_movies.yml   codec chip rows on movie posters (one pre-rendered PNG per video/HDR/audio combination)
  chips_episodes.yml the same rows on episode stills (builder_level: episode, top bar)

Kometa facts these files are shaped around (verified against Kometa 2.4.8):
  * `group` and `queue` cannot be used on the same overlay, and a definition's `overlay:` dict replaces the
    template's rather than merging -> chips are whole-row PNGs in a single group instead of queued text.
  * `value_filter` does not accept user_rating -> ratings are plain `filters: user_rating.gte/.lt`.
  * plex_search validates label/network values against the library and fails the whole overlay if any is
    missing -> label searches carry `validate: false` and `ignore_blank_results: true`, so missing labels are
    dropped silently (FilterFailed is swallowed by overlays.py) instead of killing the overlay."""
import sys
from pathlib import Path
import yaml
from ww.buckets import VOTE_BUCKETS, DOW, MON, tab_years
from ww.colors import GOLD, WHITE
from ww.chips import chip_combos, conditions, weight
from gen_assets import chip_metrics

FONT = "config/winswatch/fonts/Avenir_95_Black.ttf"
ASSETS = "config/winswatch/assets"

def _txt(name, size, color, **pos):
    o = {"name": f"text({name})", "font": FONT, "font_size": size, "font_color": color, "back_color": "#00000000"}
    o.update(pos); return o

def _label_search(mode: str, labels) -> dict:
    """plex_search on labels that tolerates labels which don't exist (yet) in the library."""
    return {"validate": False, mode: {"label": labels}}

def gauge_yaml() -> dict:
    ov = {}
    for s in range(101):
        lo = round(s / 10, 1)
        vf = {"user_rating.gte": lo} if s == 100 else {"user_rating.gte": lo, "user_rating.lt": round((s + 1) / 10, 1)}
        ov[f"ww_arc_{s:02d}"] = {
            "overlay": {"name": f"ww_arc_{s:02d}", "file": f"{ASSETS}/arc_{s:02d}.png",
                        "horizontal_align": "right", "horizontal_offset": 40, "vertical_align": "bottom", "vertical_offset": 55},
            "plex_all": True, "ignore_blank_results": True, "filters": vf}
    num = dict(horizontal_align="right", horizontal_offset=40, vertical_align="bottom", vertical_offset=62, back_width=220, back_height=90)
    ov["ww_num_white"] = {"overlay": _txt("<<user_rating%>>", 62, WHITE, **num), "plex_all": True, "ignore_blank_results": True,
                          "filters": {"user_rating.gte": 0.1, "user_rating.lt": 8.5}}
    ov["ww_num_gold"] = {"overlay": _txt("<<user_rating%>>", 62, GOLD, **num), "plex_all": True, "ignore_blank_results": True,
                         "filters": {"user_rating.gte": 8.5}}
    vpos = dict(horizontal_align="right", horizontal_offset=40, vertical_align="bottom", vertical_offset=22, back_width=220, back_height=40)
    for b in VOTE_BUCKETS:
        for tone, color, vf in (("white", WHITE, {"user_rating.lt": 8.5}), ("gold", GOLD, {"user_rating.gte": 8.5})):
            ov[f"ww_votes_{b}_{tone}"] = {"overlay": _txt(f"{b} RATINGS", 31, color, **vpos),
                                          "plex_search": _label_search("all", f"Votes_{b}"), "ignore_blank_results": True, "filters": vf}
    return {"overlays": ov}

_BG = dict(horizontal_align="center", horizontal_offset=0, vertical_align="top", vertical_offset=0)

def _top(name, file, weight, label=None, filters=None):
    """A full-width top-edge PNG (line + tab/bookmark with its text baked in). All share group `topedge`, so
    exactly one wins per item: bookmark (300+) > NEW EP (210) > RETURNS IN (205) > RETURNS (204) > edge line."""
    o = {"overlay": {"name": name, "file": f"{ASSETS}/{file}", "group": "topedge", "weight": weight, **_BG}, "ignore_blank_results": True}
    if label: o["plex_search"] = _label_search("all", label)
    else: o["plex_all"] = True
    if filters: o["filters"] = filters
    return o

def topedge_yaml() -> dict:
    """LEAVING bookmark: outranks every status tab while a DaysLeft_N label exists (movies and shows)."""
    return {"overlays": {f"ww_bookmark_{i}": _top(f"ww_bookmark_{i}", f"bookmark_{i}.png", 300 + i, label=f"DaysLeft_{i}") for i in range(1, 31)}}

def status_yaml() -> dict:
    """Show-only: status tab (light blue = new episode this week, deep blue = returning) and the bare edge line
    for ended (gray) / canceled (red)."""
    ov = {}
    for d in DOW:
        ov[f"ww_tab_newep_{d}"] = _top(f"ww_tab_newep_{d}", f"tab_NewEp_{d}.png", 210, label=f"NewEp_{d}")
    for i in range(8, 31):
        ov[f"ww_tab_returnsin_{i}"] = _top(f"ww_tab_returnsin_{i}", f"tab_ReturnsIn_{i}.png", 205, label=f"ReturnsIn_{i}")
    for m in MON:
        ov[f"ww_tab_returns_{m}"] = _top(f"ww_tab_returns_{m}", f"tab_Returns_{m}.png", 204, label=f"Returns_{m}")
    for y in tab_years():
        ov[f"ww_tab_returns_{y}"] = _top(f"ww_tab_returns_{y}", f"tab_Returns_{y}.png", 204, label=f"Returns_{y}")
    ov["ww_tab_returns_TBA"] = _top("ww_tab_returns_TBA", "tab_Returns_TBA.png", 204, label="Returns_TBA")
    ov["ww_edge_canceled"] = _top("ww_edge_canceled", "edge_red.png", 110, filters={"tmdb_status": "canceled"})
    ov["ww_edge_ended"] = _top("ww_edge_ended", "edge_gray.png", 100, filters={"tmdb_status": "ended"})
    return {"overlays": ov}

def chips_yaml(level: str | None = None) -> dict:
    """One overlay per codec-row PNG, all in group ww_chips; the heaviest matching row is drawn.
    level=None -> movie posters, bottom bar; level='episode' -> episode stills, top bar."""
    # Episode stills are composed on a 1920x1080 canvas (Kometa's landscape_dim), so they use the 1.92x chip renders
    # and 1.92x offsets; posters are 1000x1500.
    # The row PNG carries the font's descent below the baseline. Episodes are top-aligned (top edge = cap top at 65,
    # baseline unaffected); movies are bottom-aligned, so the spec's 30px bottom gap is measured from the baseline
    # (which used to sit 5px above the PNG's bottom edge) and the descent + 2 is taken off the offset.
    _, descent, _ = chip_metrics()
    pos = (dict(horizontal_offset=77, vertical_align="top", vertical_offset=65) if level == "episode"
           else dict(horizontal_offset=40, vertical_align="bottom", vertical_offset=30 + 5 - (descent + 2)))
    prefix = "chipl" if level == "episode" else "chip"
    ov = {}
    for v, h, a in chip_combos():
        key = "_".join(k or "x" for k in (v, h, a))
        o = {"overlay": {"name": f"ww_c_{key}", "file": f"{ASSETS}/{prefix}_{key}.png", "group": "ww_chips", "weight": weight(v, h, a),
                         "horizontal_align": "left", **pos},
             "ignore_blank_results": True, **conditions(v, h, a)}
        if level:
            o["builder_level"] = level
        ov[f"ww_c_{key}"] = o
    return {"overlays": ov}

FILES = {"gauge.yml": gauge_yaml, "topedge.yml": topedge_yaml, "status.yml": status_yaml,
         "chips_movies.yml": lambda: chips_yaml(), "chips_episodes.yml": lambda: chips_yaml("episode")}

def write(out_dir: Path):
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    for name, fn in FILES.items():
        (out_dir / name).write_text("# GENERATED by scripts/winswatch/gen_overlays.py — do not edit\n" + yaml.safe_dump(fn(), sort_keys=False, allow_unicode=True, width=4096))

if __name__ == "__main__":
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "kometa/overlays/winswatch/generated"
    write(dest); print(f"wrote {', '.join(FILES)} to {dest}")
