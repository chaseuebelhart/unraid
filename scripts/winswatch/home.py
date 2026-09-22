"""Wins Watch Home: Plex-side state for the home screen. Usage: home.py <requested|rows|cards|order> --sections 1,2 [--dry-run] [--env PATH]

requested — one `Requested` label per item that an Overseerr request made available in the last 30 days (Kometa draws the
            REQUESTED badge from it; a LEAVING bookmark / status tab suppresses the badge via label.not in the overlay YAML).
rows / cards / order — Tasks 3/4/5."""
import argparse, os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from ww.plexlib import PlexLib
from ww import overseerr
import gen_cards

LABEL = "Requested"
AVAILABLE = (4, 5)          # Overseerr media status: partially available / available

def load_env(path: str) -> dict:
    load_dotenv(path)
    return dict(os.environ)

def plex(env: dict) -> PlexLib:
    return PlexLib(env["PLEX_URL"], env["PLEX_TOKEN"])

def sections(arg: str) -> list[int]:
    return [int(s) for s in arg.split(",") if s.strip()]

def today(env: dict):
    return datetime.now(ZoneInfo(env.get("TZ", "America/Chicago"))).date()

_ITEM_TYPE = {"movie": "movie", "tv": "show"}   # Overseerr request type -> Plex item type

def _tmdb_id(item):
    return PlexLib._guid(item, "tmdb://")

def plan_requested(items, requests, today, window_days: int = 30, tmdb_id=_tmdb_id) -> list[tuple]:
    """(item, want) for every item: want = an Overseerr request for it is (partially) available and became so <= window_days ago.
    The window is on the availability date, not the request date.
    Match: Overseerr media.ratingKey first; else (type, tmdbId) against the item's tmdb guid. Availability date: Overseerr
    mediaAddedAt; else the item's Plex addedAt. The fallbacks exist because Overseerr only fills ratingKey/mediaAddedAt from its
    own Plex scan, which has not populated them on this server since 2025-11-05 (lastScan in overseerr/settings.json)."""
    by_key, by_tmdb = {}, {}
    # Several requests can share one media (re-requests, extra seasons): the newest wins. Sorted here rather than trusting
    # the API's sort=added order.
    for r in sorted(requests, key=lambda r: r.get("created_at") or "", reverse=True):
        if r.get("plex_rating_key"): by_key.setdefault(str(r["plex_rating_key"]), r)
        if r.get("tmdb_id") is not None: by_tmdb.setdefault((_ITEM_TYPE.get(r.get("type")), str(r["tmdb_id"])), r)
    out = []
    for it in items:
        r = by_key.get(str(it.ratingKey))
        if r is None:
            tid = tmdb_id(it)
            r = by_tmdb.get((getattr(it, "type", None), str(tid))) if tid else None
        want = False
        if r and r.get("status") in AVAILABLE:
            added = getattr(it, "addedAt", None)
            available = overseerr._iso_date(r["available_at"]) if r.get("available_at") else (added.date() if added else None)
            want = available is not None and (today - available).days <= window_days
        out.append((it, want))
    return out

def cmd_requested(a, env):
    p = plex(env)
    client = overseerr.Client(env["OVERSEERR_URL"], env["OVERSEERR_API_KEY"])
    reqs = client.requests(since_days=400)
    day = today(env)
    for sec in sections(a.sections):
        section = p.section(sec)
        for it, want in plan_requested(section.all(), reqs, day):
            has = LABEL in {l.tag for l in it.labels}
            if has == want:
                continue
            if not a.dry_run:
                p.set_labels(it, {LABEL} if want else set(), (LABEL,))
            print(f"{'DRY ' if a.dry_run else ''}{section.title:>18} | {it.title[:44]:<44} | {'+' if want else '-'}{LABEL}")

def cmd_cards(a, env):
    p = plex(env)
    cards_dir = Path(__file__).resolve().parent.parents[1] / "kometa/overlays/winswatch/cards"
    cache_path = Path(env.get("CACHE_DIR", "cache")) / "cards.json"
    secs = [p.section(s) for s in sections(a.sections)]
    for line in gen_cards.upload_cards(p, secs, cards_dir, cache_path, dry_run=a.dry_run):
        print(line)

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("requested", "rows", "cards", "order"):
        sp = sub.add_parser(name)
        sp.add_argument("--sections", required=True); sp.add_argument("--dry-run", action="store_true"); sp.add_argument("--env", default=".env")
    a = ap.parse_args(argv)
    if a.cmd == "cards":
        return cmd_cards(a, load_env(a.env))
    if a.cmd != "requested":
        raise SystemExit(f"{a.cmd}: not implemented")
    cmd_requested(a, load_env(a.env))

if __name__ == "__main__":
    main()
