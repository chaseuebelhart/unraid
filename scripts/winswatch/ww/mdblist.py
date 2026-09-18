import json, time
from pathlib import Path
import requests

TTL = 7 * 86400

def load_cache(path: Path) -> dict:
    p = Path(path); return json.loads(p.read_text()) if p.exists() else {}

def save_cache(path: Path, cache: dict) -> None:
    Path(path).write_text(json.dumps(cache))

def fetch(api_key: str, kind: str, tmdb_id: str, cache: dict) -> dict:
    key = f"{kind}:{tmdb_id}"; hit = cache.get(key)
    if hit and time.time() - hit.get("fetched", 0) < TTL:
        return {"score": hit["score"], "votes": hit["votes"]}
    r = requests.get(f"https://api.mdblist.com/tmdb/{kind}/{tmdb_id}?apikey={api_key}", headers={"User-Agent": "winswatch/1.0"}, timeout=30)
    r.raise_for_status(); d = r.json()
    votes = max([int(x.get("votes") or 0) for x in d.get("ratings", []) if x.get("source") in ("imdb", "letterboxd", "trakt")] + [0])
    out = {"score": d.get("score"), "votes": votes}
    cache[key] = {**out, "fetched": time.time()}
    return out
