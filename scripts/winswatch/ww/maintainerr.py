"""Maintainerr's collection list, read-only (http://192.168.0.30:6246, unauthenticated).

Only used by `home.py check`. Collections are matched by `type` ("movie"/"show"), never by title: looking the ⏳ Leaving
rows up by exact title is precisely what broke the DaysLeft labeler when they were renamed (design §10).

The embedded `media` array is a short preview (2 of 7 items on 2026-09-22); `mediaCount` is the real member count, which
is why that is what is normalised out here."""
import requests

DEFAULT_URL = "http://192.168.0.30:6246"


def collections(base_url: str = DEFAULT_URL) -> list[dict]:
    r = requests.get(f"{base_url.rstrip('/')}/api/collections", timeout=60)
    r.raise_for_status()
    return [{"id": c.get("id"), "title": c.get("title"), "type": c.get("type"),
             "library_id": str(c.get("libraryId")), "media_count": c.get("mediaCount") or 0,
             "active": bool(c.get("isActive"))} for c in r.json()]
