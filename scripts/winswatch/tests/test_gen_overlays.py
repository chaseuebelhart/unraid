from datetime import date, timedelta
from pathlib import Path
import yaml
import gen_assets, gen_overlays
from ww.buckets import airdate_label, tab_years
from ww.chips import chip_combos

def test_gauge_score_plates_cover_every_tenth():
    g = gen_overlays.gauge_yaml()["overlays"]
    assert set(g) == {f"ww_score_{s:02d}" for s in range(101)}     # no separate number / vote overlays in the locked look
    lo = [v["filters"]["user_rating.gte"] for v in g.values()]
    assert sorted(lo) == [round(i / 10, 1) for i in range(101)]
    p86 = g["ww_score_86"]
    assert p86["overlay"] == {"name": "ww_score_86", "file": "config/winswatch/assets/score_86.png",
                              "horizontal_align": "right", "horizontal_offset": 0, "vertical_align": "bottom", "vertical_offset": 242}
    assert p86["filters"] == {"user_rating.gte": 8.6, "user_rating.lt": 8.7} and p86["plex_all"] is True and p86["ignore_blank_results"] is True
    assert g["ww_score_100"]["filters"] == {"user_rating.gte": 10.0}
    assert "value_filter" not in p86   # Kometa 2.4.8 rejects user_rating there

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
    assert s[f"ww_tab_returns_{date.today().year + 1}"]["overlay"]["file"].endswith(f"/tab_Returns_{date.today().year + 1}.png")
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
    _, descent, _ = gen_assets.chip_metrics()
    assert gen_assets.CHIP_PX == 60 and gen_assets.CHIP_GAP == 39 and descent == 14
    mo = m["ww_c_k4_x_x"]["overlay"]
    assert mo["vertical_align"] == "bottom" and mo["vertical_offset"] == 30 + 5 - (descent + 2) == 19 and mo["horizontal_offset"] == 39   # baseline stays 35px up
    eo = e["ww_c_k4_x_x"]["overlay"]
    assert eo["vertical_align"] == "bottom" and eo["vertical_offset"] == round(19 * 1.92) == 36 and e["ww_c_k4_x_x"]["builder_level"] == "episode"
    assert eo["file"].endswith("/chipl_k4_x_x.png") and eo["horizontal_offset"] == 77
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
    for f, n in (("gauge.yml", 100), ("topedge.yml", 29), ("status.yml", 49), ("chips_movies.yml", 150), ("chips_episodes.yml", 150)):
        data = yaml.safe_load((tmp_path / f).read_text())
        assert "overlays" in data and len(data["overlays"]) > n

def test_every_airdate_label_has_an_overlay():
    """airdate_label -> status.yml: every label the pipeline can write for a next-air date up to 6 years out is drawn."""
    labels = {v["plex_search"]["all"]["label"] for v in gen_overlays.status_yaml()["overlays"].values() if "plex_search" in v}
    today = date.today()
    produced = {airdate_label(today + timedelta(days=d), "continuing", today) for d in range(0, 366 * 6)} | {airdate_label(None, "continuing", today)}
    assert produced - {None} <= labels, sorted(produced - labels)
    assert f"Returns_{today.year + 6}" in labels and f"Returns_{today.year + 7}" not in labels
    assert tab_years(date(2030, 6, 1)) == list(range(2030, 2037))

def test_every_referenced_asset_exists(tmp_path):
    """Guard against asset/YAML drift: each file: in the generated AND hand-written YAML is produced by gen_assets.generate()."""
    names = {p.name for p in gen_assets.generate(tmp_path)}
    docs = [fn() for fn in gen_overlays.FILES.values()]
    ww = Path(__file__).resolve().parents[3] / "kometa/overlays/winswatch"
    docs += [yaml.safe_load((ww / f).read_text()) for f in ("movies.yml", "shows.yml", "seasons.yml", "episodes.yml")]
    referenced = set()
    for doc in docs:
        for v in doc["overlays"].values():
            f = (v.get("overlay") or {}).get("file")
            if f:
                assert f.startswith("config/winswatch/assets/"), f
                referenced.add(f.rsplit("/", 1)[1])
    missing = referenced - names
    assert not missing, sorted(missing)
    assert {"score_86.png", "bar_bottom.png", "bar_bottom_ep.png", "bookmark_1.png", "tab_Returns_TBA.png", "chip_k4_x_x.png", "chipl_k4_x_x.png"} <= referenced

def test_hand_written_yaml_matches_locked_look():
    ww = Path(__file__).resolve().parents[3] / "kometa/overlays/winswatch"
    ep = yaml.safe_load((ww / "episodes.yml").read_text())["overlays"]
    assert ep["ww_bar"]["overlay"]["file"].endswith("/bar_bottom_ep.png") and ep["ww_bar"]["overlay"]["vertical_align"] == "bottom"
    rt = ep["ww_runtime"]["overlay"]
    assert rt["font_size"] == 115 and rt["vertical_align"] == "bottom" and rt["vertical_offset"] == gen_overlays.chip_bottom_offset("episode") and rt["horizontal_offset"] == 77
    new = ep["ww_new"]
    assert new["builder_level"] == "episode" and new["plex_search"] == {"all": {"episode_air_date": 7}}
    assert new["overlay"]["font_size"] == 111 and new["overlay"]["horizontal_offset"] == 77 and new["overlay"]["vertical_offset"] == 77
    assert new["overlay"]["back_radius"] == 29 and new["overlay"]["back_padding"] == 35 and new["overlay"]["vertical_align"] == "top"
    se = yaml.safe_load((ww / "seasons.yml").read_text())["overlays"]["ww_new_season"]["overlay"]
    assert se["vertical_align"] == "top" and se["vertical_offset"] == 40 and se["horizontal_offset"] == 40
    sh = yaml.safe_load((ww / "shows.yml").read_text())
    svc = sh["templates"]["ww_service"]["overlay"]
    assert svc["font_size"] == 60 and svc["horizontal_offset"] == 39 and svc["vertical_align"] == "bottom"
    new = sh["overlays"]["ww_new"]["overlay"]
    assert new["font_size"] == 58 and new["vertical_offset"] == 116   # clears the 104px-tall tab by the same 12px as before
