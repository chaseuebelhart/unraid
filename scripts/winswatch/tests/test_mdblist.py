import json, time
from ww import mdblist

class FakeResp:
    def __init__(self, data, status=200): self._d, self.status_code = data, status
    def json(self): return self._d
    def raise_for_status(self):
        if self.status_code >= 400: raise RuntimeError(self.status_code)

def test_fetch_parses_and_caches(monkeypatch):
    calls = []
    def fake_get(url, headers=None, timeout=None):
        calls.append(url)
        return FakeResp({"score": 86, "ratings": [{"source": "imdb", "votes": 793314}, {"source": "letterboxd", "votes": 3645831}, {"source": "trakt", "votes": 50380}]})
    monkeypatch.setattr(mdblist.requests, "get", fake_get)
    cache = {}
    r = mdblist.fetch("k", "movie", "693134", cache)
    assert r == {"score": 86, "votes": 3645831}
    assert "https://api.mdblist.com/tmdb/movie/693134?apikey=k" in calls[0]
    r2 = mdblist.fetch("k", "movie", "693134", cache)
    assert r2 == r and len(calls) == 1          # cached

def test_fetch_missing_score(monkeypatch):
    monkeypatch.setattr(mdblist.requests, "get", lambda *a, **k: FakeResp({"score": None, "ratings": []}))
    assert mdblist.fetch("k", "show", "1", {}) == {"score": None, "votes": 0}

def test_cache_expiry(monkeypatch):
    n = {"c": 0}
    monkeypatch.setattr(mdblist.requests, "get", lambda *a, **k: (n.__setitem__("c", n["c"] + 1), FakeResp({"score": 70, "ratings": []}))[1])
    cache = {"movie:9": {"score": 70, "votes": 0, "fetched": time.time() - 8 * 86400}}
    mdblist.fetch("k", "movie", "9", cache)
    assert n["c"] == 1
