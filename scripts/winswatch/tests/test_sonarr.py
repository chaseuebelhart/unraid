from datetime import date
from ww import sonarr

class FakeResp:
    def __init__(self, data): self._d = data
    def json(self): return self._d
    def raise_for_status(self): pass

def test_series_index(monkeypatch):
    monkeypatch.setenv("TZ", "America/Chicago")
    def fake_get(url, headers=None, params=None, timeout=None):
        if url.endswith("/api/v3/series"):
            return FakeResp([{"id": 1, "tvdbId": 366924, "status": "continuing", "nextAiring": "2026-09-25T01:00:00Z", "monitored": True},
                             {"id": 2, "tvdbId": 371572, "status": "continuing", "monitored": False},
                             {"id": 3, "tvdbId": 396112, "status": "ended", "nextAiring": None}])
        raise AssertionError(url)
    monkeypatch.setattr(sonarr.requests, "get", fake_get)
    idx = sonarr.series_index("http://s:8989", "key")
    assert idx["366924"] == {"status": "continuing", "next_air": date(2026, 9, 24), "monitored": True}
    assert idx["371572"] == {"status": "continuing", "next_air": None, "monitored": False}
    assert idx["396112"] == {"status": "ended", "next_air": None, "monitored": True}   # absent `monitored` -> True
