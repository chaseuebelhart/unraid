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
