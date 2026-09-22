from datetime import date
from pathlib import Path
from types import SimpleNamespace as NS
import gen_home
from ww import plexhome

CAL = gen_home.load_calendar(Path(__file__).resolve().parents[1] / "home_calendar.yml")
TOP = ["✨ ", "🔥 Trending ", "📥 New ", "👥 Popular ", "⏳ "]
BYW = "🎯 Because you watched"

def hub(title, shared=True, home=False):
    return NS(title=title, promotedToSharedHome=shared, promotedToOwnHome=home, identifier=title)

def test_week_parity():
    assert plexhome.week(date(2026, 9, 21)) == "A" and plexhome.week(date(2026, 9, 27)) == "A"
    assert plexhome.week(date(2026, 9, 28)) == "B" and plexhome.week(date(2026, 10, 4)) == "B"
    assert plexhome.week(date(2026, 10, 5)) == "A"

def test_in_schedule():
    assert plexhome.in_schedule("weekly(friday|saturday)", date(2027, 3, 26))       # Fri
    assert not plexhome.in_schedule("weekly(friday|saturday)", date(2027, 3, 25))   # Thu
    assert plexhome.in_schedule("range(09/15-10/31)", date(2026, 9, 15))
    assert plexhome.in_schedule("range(09/15-10/31)", date(2026, 10, 31))
    assert not plexhome.in_schedule("range(09/15-10/31)", date(2026, 11, 1))
    assert plexhome.in_schedule("range(12/20-01/05)", date(2026, 1, 3))            # wraps the year

def test_desired_order_plain_week_a_monday():
    # 2027-03-22: week A Monday with no seasonal window open (Awards Season ends 03/15)
    d = plexhome.desired_order("movies", date(2027, 3, 22), CAL)
    assert d == TOP + ["💥 Adrenaline Rush", "💎 Hidden Gems", BYW]
    assert plexhome.desired_order("shows", date(2027, 3, 22), CAL) == TOP + ["🪐 Worlds Beyond", "🛋️ Comfort Binge", BYW]

def test_desired_order_week_b():
    # 2027-03-29: week B Monday -> Love & Laughs, Mind Benders (emoji read from THEMES, not hard-coded)
    d = plexhome.desired_order("movies", date(2027, 3, 29), CAL)
    ll = gen_home.THEMES["Love & Laughs"]["emoji"]
    assert d[5:7] == [f"{ll} Love & Laughs", "🌀 Mind Benders"]

def test_seasonal_takes_shelf_1():
    # Halloween window is 09/15-10/31: 2026-09-21 (plan epoch, week A Monday) already sits inside it
    assert plexhome.desired_order("movies", date(2026, 9, 21), CAL)[5:7] == ["🎃 Halloween", "💎 Hidden Gems"]
    assert plexhome.desired_order("movies", date(2026, 10, 1), CAL)[5] == "🎃 Halloween"
    assert plexhome.desired_order("movies", date(2026, 12, 25), CAL)[5] == "🎄 Christmas Movies"
    assert plexhome.desired_order("movies", date(2027, 2, 10), CAL)[5] == "💘 Valentine's Picks"   # narrower window beats Awards
    assert plexhome.desired_order("movies", date(2027, 2, 20), CAL)[5] == "🏆 Awards Season"

def test_weekend_takes_shelf_2_movies_only():
    fri, sat, sun = date(2027, 3, 26), date(2027, 3, 27), date(2027, 3, 28)
    assert plexhome.desired_order("movies", fri, CAL)[5:7] == ["🎬 Director's Spotlight", "🍷 Date Night"]
    assert plexhome.desired_order("movies", sat, CAL)[5:7] == ["💥 Adrenaline Rush", "🍷 Date Night"]
    assert plexhome.desired_order("movies", sun, CAL)[5:7] == ["💎 Hidden Gems", "☕ Sunday Slow Burn"]
    for day in (fri, sat, sun):
        d = plexhome.desired_order("shows", day, CAL)
        assert not any(x in d for x in ("🍷 Date Night", "☕ Sunday Slow Burn", "🎃 Halloween"))
    assert plexhome.desired_order("shows", sun, CAL)[5:7] == ["🎢 Edge of Your Seat", "🛋️ Comfort Binge"]

def test_plan_orders_matches_and_demotes_the_rest():
    desired = plexhome.desired_order("movies", date(2027, 3, 22), CAL)
    byw1, byw2 = hub("🎯 Because you watched Heat​‌"), hub("🎯 Because you watched Dune‌​")
    fy1, fy2, fy3 = hub("✨ Movies Recommended For You​"), hub("✨ Movies for you‌"), hub("✨ Movies Recommended For You‌‌")
    imdb, crime = hub("IMDb Popular", home=True), hub("🕵️ Crime Files", home=True)
    recent = hub("Recently Added Movies", shared=True, home=True)
    unwatched = hub("Top Unwatched Movies", shared=False, home=False)
    my_req = hub("My Requests", shared=False, home=True)
    gems, rush = hub("💎 Hidden Gems", home=True), hub("💥 Adrenaline Rush", home=True)
    leaving, popular, trending = hub("⏳ Movies Leaving Wins Watch"), hub("👥 Popular Movies on Wins Watch​"), hub("🔥 Trending Movies")
    new1, new2 = hub("📥 New Movies · Your Requests​"), hub("📥 New Movies · Your Requests‌")
    hubs = [byw1, gems, imdb, fy1, recent, crime, new1, unwatched, popular, rush, fy2, leaving, my_req, trending, byw2, new2, fy3]
    ordered, demote = plexhome.plan(hubs, desired)
    assert ordered == [fy1, fy2, fy3, trending, new1, new2, popular, leaving, rush, gems, byw1, byw2]
    assert demote == [imdb, recent, crime, my_req]     # unwatched is not promoted -> left alone

def test_plan_matches_prefix_only_once_and_tolerates_missing_rows():
    desired = plexhome.desired_order("shows", date(2027, 3, 22), CAL)
    hubs = [hub("Trending Shows"), hub("🪐 Worlds Beyond"), hub("Just Dropped")]
    ordered, demote = plexhome.plan(hubs, desired)
    assert [h.title for h in ordered] == ["🪐 Worlds Beyond"]
    assert [h.title for h in demote] == ["Trending Shows", "Just Dropped"]     # un-emoji'd stock rows go too

class FakeHub:
    def __init__(self, title, shared=True, home=True):
        self.title, self.promotedToSharedHome, self.promotedToOwnHome, self.identifier = title, shared, home, title
        self.moves, self.vis = [], None
    def move(self, after=None): self.moves.append(after.title if after else None)
    def updateVisibility(self, recommended=None, home=None, shared=None): self.vis = (home, shared); return self

def test_apply_walks_moves_and_demotes(capsys):
    a, b, c, x = FakeHub("✨ A"), FakeHub("🔥 Trending B"), FakeHub("🎯 Because you watched C"), FakeHub("IMDb Popular")
    section = NS(title="Movies", key=1)
    plexhome.apply(section, [a, b, c], [x], dry_run=True)
    assert a.moves == [] and x.vis is None and "DRY" in capsys.readouterr().out
    plexhome.apply(section, [a, b, c], [x], dry_run=False)
    assert a.moves == [None] and b.moves == ["✨ A"] and c.moves == ["🔥 Trending B"]
    assert x.vis == (False, False)

def test_lib_for_section():
    assert plexhome.lib_for(NS(type="movie")) == "movies" and plexhome.lib_for(NS(type="show")) == "shows"

def test_home_order_command_dispatches_dry_run(monkeypatch, capsys):
    import home
    hubs = [FakeHub("IMDb Popular"), FakeHub("💎 Hidden Gems"), FakeHub("✨ Movies for you​", home=False)]
    section = NS(title="Wins Watch Lab", key=4, type="movie", managedHubs=lambda: hubs, collections=lambda: [])
    class FakePlexLib:
        def __init__(self, url, token): pass
        def section(self, sec_id): assert sec_id == 4; return section
    monkeypatch.setattr(home, "PlexLib", FakePlexLib)
    monkeypatch.setenv("PLEX_URL", "http://fake"); monkeypatch.setenv("PLEX_TOKEN", "tok")
    home.main(["order", "--sections", "4", "--dry-run", "--env", "/nonexistent.env"])
    out = capsys.readouterr().out
    assert "DRY" in out and "demote IMDb Popular" in out and "move   ✨ Movies for you" in out
    assert all(h.moves == [] and h.vis is None for h in hubs)


def test_resolve_titles_uses_current_collection_title():
    """/hubs/sections/N/manage keeps the title from promotion time: a renamed collection must be matched by its current name."""
    from types import SimpleNamespace as NS
    hubs = [NS(identifier="custom.collection.1.7486", title="Movies Leaving Soon"),
            NS(identifier="custom.collection.1.999", title="Gone"),
            NS(identifier="movie.recentlyadded", title="Recently Added Movies")]
    plexhome.resolve_titles(hubs, {"7486": "⏳ Movies Leaving Wins Watch"})
    assert [h.title for h in hubs] == ["⏳ Movies Leaving Wins Watch", "Gone", "Recently Added Movies"]
