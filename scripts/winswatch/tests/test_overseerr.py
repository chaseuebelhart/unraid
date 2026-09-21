from datetime import date
from ww import overseerr

class _Resp:
    def __init__(self, data): self._d = data
    def json(self): return self._d
    def raise_for_status(self): pass

def test_requests_paginates_and_maps(monkeypatch):
    pages = {0: {"pageInfo": {"pages": 2}, "results": [{"type": "movie", "createdAt": "2026-09-01T00:00:00.000Z", "requestedBy": {"plexId": 1}, "media": {"tmdbId": 155, "status": 5, "mediaAddedAt": "2026-09-05T00:00:00.000Z", "ratingKey": "1252"}}]},
             100: {"pageInfo": {"pages": 2}, "results": [{"type": "tv", "createdAt": "2026-05-01T00:00:00.000Z", "requestedBy": {"plexId": 6}, "media": {"tmdbId": 95396, "status": 4, "mediaAddedAt": None, "ratingKey": None}}]}}
    seen = []
    def fake_get(url, headers, params, timeout):
        assert url == "http://x/api/v1/request" and headers == {"X-Api-Key": "k"} and timeout == 30
        assert params["take"] == 100 and params["sort"] == "added" and params["filter"] == "all"
        seen.append(params["skip"]); return _Resp(pages[params["skip"]])
    monkeypatch.setattr(overseerr.requests, "get", fake_get)
    monkeypatch.setattr(overseerr, "today", lambda: date(2026, 9, 21))
    got = overseerr.Client("http://x", "k").requests(since_days=90)   # today is patched to 2026-09-21
    assert seen == [0, 100]
    assert [r["tmdb_id"] for r in got] == [155]          # the tv one is older than 90 days
    assert got[0] == {"type": "movie", "tmdb_id": 155, "requested_by_plex_id": 1, "created_at": "2026-09-01T00:00:00.000Z", "status": 5, "available_at": "2026-09-05T00:00:00.000Z", "plex_rating_key": "1252"}

def test_requests_keeps_older_rows_with_a_wider_window(monkeypatch):
    page = {"pageInfo": {"pages": 1}, "results": [{"type": "tv", "createdAt": "2026-05-01T00:00:00.000Z", "requestedBy": {"plexId": 6}, "media": {"tmdbId": 95396, "status": 4, "mediaAddedAt": None, "ratingKey": None}}]}
    monkeypatch.setattr(overseerr.requests, "get", lambda url, headers, params, timeout: _Resp(page))
    monkeypatch.setattr(overseerr, "today", lambda: date(2026, 9, 21))
    got = overseerr.Client("http://x/", "k").requests(since_days=400)
    assert got == [{"type": "tv", "tmdb_id": 95396, "requested_by_plex_id": 6, "created_at": "2026-05-01T00:00:00.000Z", "status": 4, "available_at": None, "plex_rating_key": None}]

def test_users(monkeypatch):
    def fake_get(url, headers, params, timeout):
        assert url == "http://x/api/v1/user" and params == {"take": 200}
        return _Resp({"pageInfo": {"pages": 1}, "results": [{"id": 1, "plexId": 1, "plexUsername": "chase", "email": "x@y"}, {"id": 2, "plexId": 6, "plexUsername": "guest"}]})
    monkeypatch.setattr(overseerr.requests, "get", fake_get)
    assert overseerr.Client("http://x", "k").users() == [{"id": 1, "plexId": 1, "plexUsername": "chase"}, {"id": 2, "plexId": 6, "plexUsername": "guest"}]
