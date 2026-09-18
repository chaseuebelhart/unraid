import yaml
import gen_overlays
from ww.buckets import VOTE_BUCKETS
from ww.chips import chip_combos

FONT = "config/winswatch/fonts/Avenir_95_Black.ttf"

def test_gauge_arcs_cover_every_tenth():
    g = gen_overlays.gauge_yaml()["overlays"]
    arcs = {k: v for k, v in g.items() if k.startswith("ww_arc_")}
    assert len(arcs) == 101
    lo = [v["filters"]["user_rating.gte"] for v in arcs.values()]
    assert sorted(lo) == [round(i / 10, 1) for i in range(101)]
    a86 = arcs["ww_arc_86"]
    assert a86["overlay"]["file"] == "config/winswatch/assets/arc_86.png"
    assert a86["filters"] == {"user_rating.gte": 8.6, "user_rating.lt": 8.7} and a86["plex_all"] is True
    assert a86["overlay"]["horizontal_align"] == "right" and a86["overlay"]["vertical_offset"] == 55
    assert "value_filter" not in a86   # Kometa 2.4.8 rejects user_rating there

def test_gauge_number_and_votes():
    g = gen_overlays.gauge_yaml()["overlays"]
    assert g["ww_num_white"]["overlay"]["name"] == "text(<<user_rating%>>)"
    assert g["ww_num_white"]["filters"] == {"user_rating.gte": 0.1, "user_rating.lt": 8.5}
    assert g["ww_num_gold"]["filters"] == {"user_rating.gte": 8.5}
    assert g["ww_num_gold"]["overlay"]["font_color"] == "#f5c518"
    votes = [k for k in g if k.startswith("ww_votes_")]
    assert len(votes) == 2 * len(VOTE_BUCKETS)
    v = g["ww_votes_1.5M_white"]
    assert v["plex_search"] == {"validate": False, "all": {"label": "Votes_1.5M"}}
    assert v["ignore_blank_results"] is True     # a missing label skips the overlay instead of erroring
    assert v["overlay"]["name"] == "text(1.5M RATINGS)"
    assert v["filters"] == {"user_rating.lt": 8.5}

def test_topedge_and_status_precedence():
    t = gen_overlays.topedge_yaml()["overlays"]
    assert set(t) == {f"ww_bookmark_{i}" for i in range(1, 31)}
    bm = t["ww_bookmark_12"]
    assert bm["overlay"] == {"name": "ww_bookmark_12", "file": "config/winswatch/assets/bookmark_12.png", "group": "topedge", "weight": 312,
                             "horizontal_align": "center", "horizontal_offset": 0, "vertical_align": "top", "vertical_offset": 0}
    assert bm["plex_search"] == {"validate": False, "all": {"label": "DaysLeft_12"}}
    s = gen_overlays.status_yaml()["overlays"]
    assert s["ww_tab_newep_Wed"]["overlay"]["file"].endswith("/tab_NewEp_Wed.png") and s["ww_tab_newep_Wed"]["overlay"]["weight"] == 210
    assert s["ww_tab_newep_Wed"]["plex_search"] == {"validate": False, "all": {"label": "NewEp_Wed"}}
    assert s["ww_tab_returnsin_13"]["overlay"]["file"].endswith("/tab_ReturnsIn_13.png") and s["ww_tab_returnsin_13"]["overlay"]["weight"] == 205
    assert s["ww_tab_returns_Nov"]["overlay"]["file"].endswith("/tab_Returns_Nov.png")
    assert s["ww_tab_returns_2027"]["overlay"]["file"].endswith("/tab_Returns_2027.png")
    assert s["ww_tab_returns_TBA"]["overlay"]["file"].endswith("/tab_Returns_TBA.png") and s["ww_tab_returns_TBA"]["overlay"]["weight"] == 204
    assert s["ww_edge_ended"]["filters"] == {"tmdb_status": "ended"} and s["ww_edge_ended"]["overlay"]["weight"] == 100
    assert s["ww_edge_canceled"]["filters"] == {"tmdb_status": "canceled"} and s["ww_edge_canceled"]["overlay"]["weight"] == 110
    # one group: bookmark (300+) outranks every tab (200s) which outranks the bare edge lines (100s)
    assert {v["overlay"]["group"] for v in list(t.values()) + list(s.values())} == {"topedge"}
    assert max(v["overlay"]["weight"] for v in s.values()) < 300 <= min(v["overlay"]["weight"] for v in t.values())
    assert all(v["ignore_blank_results"] is True for v in list(t.values()) + list(s.values()))

def test_chips_one_group_best_wins():
    m = gen_overlays.chips_yaml()["overlays"]
    e = gen_overlays.chips_yaml("episode")["overlays"]
    assert len(m) == len(e) == len(list(chip_combos())) == 168
    top = m["ww_c_k4_dvhdr_dtsx"]
    assert top["overlay"]["group"] == "ww_chips" and "queue" not in top["overlay"]   # Kometa: group xor queue
    assert top["overlay"]["file"] == "config/winswatch/assets/chip_k4_dvhdr_dtsx.png"
    assert top["overlay"]["weight"] > m["ww_c_k4_dv_dtsx"]["overlay"]["weight"] > m["ww_c_k4_x_dtsx"]["overlay"]["weight"]
    assert m["ww_c_k4_x_x"]["overlay"]["weight"] > m["ww_c_p1080_dvhdr_dtsx"]["overlay"]["weight"]   # video always leads
    assert m["ww_c_k4_dvhdr_atmos"]["overlay"]["weight"] > m["ww_c_k4_dvhdr_truehd"]["overlay"]["weight"]
    assert m["ww_c_k4_x_x"]["overlay"]["vertical_align"] == "bottom" and m["ww_c_k4_x_x"]["overlay"]["vertical_offset"] == 30
    assert e["ww_c_k4_x_x"]["overlay"]["vertical_align"] == "top" and e["ww_c_k4_x_x"]["builder_level"] == "episode"
    assert e["ww_c_k4_x_x"]["overlay"]["file"].endswith("/chipl_k4_x_x.png") and e["ww_c_k4_x_x"]["overlay"]["horizontal_offset"] == 77
    assert m["ww_c_k4_dvhdr_truehdatmos"]["overlay"]["weight"] > m["ww_c_k4_dvhdr_dtsx"]["overlay"]["weight"]
    assert "builder_level" not in m["ww_c_k4_x_x"]
    sdr = m["ww_c_p1080_x_ddp"]
    assert sdr["plex_search"] == {"all": {"hdr": False}}
    assert all(f["has_dolby_vision"] is False and f["resolution.regex"] == "(?i)1080|2k" for f in sdr["filters"])
    assert "audio_track_title.regex" in sdr["filters"][0] and "filepath.regex" in sdr["filters"][1]
    assert m["ww_c_k4_dv_x"]["plex_all"] is True and m["ww_c_k4_dv_x"]["filters"]["has_dolby_vision"] is True
    assert m["ww_c_k4_hdr_x"]["plex_search"] == {"all": {"hdr": True}}
    assert not any(k.startswith("ww_c_p720_dv") or k.startswith("ww_c_sd_hdr") for k in m)   # no HDR rows below 1080p

def test_write_roundtrip(tmp_path):
    gen_overlays.write(tmp_path)
    for f, n in (("gauge.yml", 150), ("topedge.yml", 29), ("status.yml", 49), ("chips_movies.yml", 150), ("chips_episodes.yml", 150)):
        data = yaml.safe_load((tmp_path / f).read_text())
        assert "overlays" in data and len(data["overlays"]) > n
