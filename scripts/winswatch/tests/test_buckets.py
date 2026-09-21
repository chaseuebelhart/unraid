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
    assert CODEC["ddpatmos"] == ("DD+ ATMOS", "#7dd3fc")   # full labels again (2026-09-21)
    assert SERVICE["Netflix"] == "#e50914"
    assert SERVICE["Apple TV+"] == "#f5f5f7"
