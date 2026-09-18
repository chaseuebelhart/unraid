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
    v = g["ww_votes_1.5M_white"]
    assert v["plex_search"] == {"all": {"label": "Votes_1.5M"}}
    assert v["overlay"]["name"] == "text(1.5M RATINGS)"
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
