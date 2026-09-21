from datetime import date, datetime
from types import SimpleNamespace as NS
import pytest
import home

def _it(key, labels):
    return NS(ratingKey=int(key), title=f"item {key}", labels=[NS(tag=l) for l in labels])

def test_plan_requested_window():
    today = date(2026, 9, 21)
    items = [_it("1252", labels=[]), _it("99", labels=["Requested"]), _it("7", labels=[])]
    reqs = [{"plex_rating_key": "1252", "available_at": "2026-09-05T00:00:00.000Z", "status": 5},
            {"plex_rating_key": "99", "available_at": "2026-07-01T00:00:00.000Z", "status": 5},   # >30 days: label comes off
            {"plex_rating_key": "7", "available_at": None, "status": 3}]                            # pending: nothing
    assert home.plan_requested(items, reqs, today) == [(items[0], True), (items[1], False), (items[2], False)]

def test_plan_requested_unrequested_and_partial():
    today = date(2026, 9, 21)
    items = [_it("5", labels=["Requested"]), _it("8", labels=[]), _it("9", labels=[])]
    reqs = [{"plex_rating_key": "8", "available_at": "2026-09-20T00:00:00.000Z", "status": 4},     # partially available counts
            {"plex_rating_key": "9", "available_at": "2026-08-22T00:00:00.000Z", "status": 5}]     # exactly 30 days: still in
    assert home.plan_requested(items, reqs, today) == [(items[0], False), (items[1], True), (items[2], True)]   # item 5: no request -> label comes off
    assert home.plan_requested(items, reqs, today, window_days=7) == [(items[0], False), (items[1], True), (items[2], False)]

def test_plan_requested_falls_back_to_tmdb_and_plex_added_at():
    """Overseerr's Plex scan has not filled ratingKey/mediaAddedAt since 2025-11-05: match on (type, tmdbId), window on Plex addedAt."""
    today = date(2026, 9, 21)
    def guid(tid): return [NS(id=f"tmdb://{tid}"), NS(id="imdb://tt1")]
    dune = NS(ratingKey=501, title="Dune", type="movie", guids=guid(438631), addedAt=datetime(2026, 9, 10, 8, 0), labels=[])
    old = NS(ratingKey=502, title="Old", type="movie", guids=guid(155), addedAt=datetime(2026, 1, 1), labels=[NS(tag="Requested")])
    show = NS(ratingKey=503, title="Show 155", type="show", guids=guid(155), addedAt=datetime(2026, 9, 15), labels=[])   # tmdb 155 the *show*, not the movie
    noguid = NS(ratingKey=504, title="No guid", type="movie", guids=[], addedAt=datetime(2026, 9, 15), labels=[])
    reqs = [{"type": "movie", "tmdb_id": 438631, "plex_rating_key": None, "available_at": None, "status": 5},
            {"type": "movie", "tmdb_id": 155, "plex_rating_key": None, "available_at": None, "status": 5},
            {"type": "tv", "tmdb_id": 95396, "plex_rating_key": None, "available_at": None, "status": 4},
            {"type": "movie", "tmdb_id": 999, "plex_rating_key": "504", "available_at": "2026-09-20T00:00:00.000Z", "status": 5}]   # rating key still wins
    assert home.plan_requested([dune, old, show, noguid], reqs, today) == [(dune, True), (old, False), (show, False), (noguid, True)]

def test_sections_and_stubs():
    assert home.sections("4, 5") == [4, 5]
    for cmd in ("rows", "cards", "order"):
        with pytest.raises(SystemExit, match="not implemented"):
            home.main([cmd, "--sections", "4"])
