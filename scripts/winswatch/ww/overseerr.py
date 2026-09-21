"""Small Overseerr client: users and (recent) requests, flattened to the few fields the Home scripts need."""
from datetime import date, datetime, timedelta
import requests

def today() -> date:   # module-level so tests can patch it
    return date.today()

def _iso_date(s: str) -> date:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).date()

class Client:
    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip("/")
        self.headers = {"X-Api-Key": api_key}

    def _get(self, path: str, params: dict) -> dict:
        r = requests.get(f"{self.url}{path}", headers=self.headers, params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def users(self) -> list[dict]:
        """[{id, plexId, plexUsername}] — Overseerr user id vs Plex account id (requestedBy.plexId)."""
        return [{"id": u["id"], "plexId": u.get("plexId"), "plexUsername": u.get("plexUsername")}
                for u in self._get("/api/v1/user", {"take": 200})["results"]]

    def requests(self, since_days: int) -> list[dict]:
        """Requests created within since_days, newest first. status = Overseerr media status
        (1 unknown, 2 pending, 3 processing, 4 partially available, 5 available); available_at = media.mediaAddedAt."""
        cutoff = today() - timedelta(days=since_days)
        out, skip, pages = [], 0, 1
        while skip < pages * 100:
            page = self._get("/api/v1/request", {"take": 100, "skip": skip, "sort": "added", "filter": "all"})
            pages = page.get("pageInfo", {}).get("pages", 1)
            for r in page.get("results", []):
                if _iso_date(r["createdAt"]) < cutoff:
                    continue
                m = r.get("media") or {}
                out.append({"type": r["type"], "tmdb_id": m.get("tmdbId"), "requested_by_plex_id": (r.get("requestedBy") or {}).get("plexId"),
                            "created_at": r["createdAt"], "status": m.get("status"), "available_at": m.get("mediaAddedAt"),
                            "plex_rating_key": str(m["ratingKey"]) if m.get("ratingKey") is not None else None})
            skip += 100
        return out
