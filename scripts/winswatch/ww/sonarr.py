import os
from datetime import date, datetime
from zoneinfo import ZoneInfo
import requests

def series_index(base_url: str, api_key: str) -> dict:
    r = requests.get(f"{base_url.rstrip('/')}/api/v3/series", headers={"X-Api-Key": api_key}, timeout=60)
    r.raise_for_status()
    tz = ZoneInfo(os.environ.get("TZ", "America/Chicago"))
    out = {}
    for s in r.json():
        nxt = s.get("nextAiring")
        out[str(s["tvdbId"])] = {"status": s.get("status", "continuing"),
                                 "next_air": datetime.fromisoformat(nxt.replace("Z", "+00:00")).astimezone(tz).date() if nxt else None}
    return out
