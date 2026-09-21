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
