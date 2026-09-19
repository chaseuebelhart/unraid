"""Sonarr next-air -> one status label per show (NewEp_/ReturnsIn_/Returns_*). Ended/canceled get no label (Kometa uses tmdb_status)."""
import argparse, os
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from ww.plexlib import PlexLib
from ww import sonarr
from ww.buckets import airdate_label

PREFIXES = ("NewEp_", "ReturnsIn_", "Returns_")

def plan(items, index, tvdb_id, today):
    out = []
    for it in items:
        s = index.get(tvdb_id(it) or "")
        out.append((it, airdate_label(s["next_air"], s["status"], today) if s else None))
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sections", required=True); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--env", default=".env")
    a = ap.parse_args(); load_dotenv(a.env)
    plex = PlexLib(os.environ["PLEX_URL"], os.environ["PLEX_TOKEN"])
    index = sonarr.series_index(os.environ["SONARR_URL"], os.environ["SONARR_API_KEY"])
    today = datetime.now(ZoneInfo(os.environ.get("TZ", "America/Chicago"))).date()
    for sec in a.sections.split(","):
        section = plex.section(int(sec))
        if section.type != "show": continue
        for it, label in plan(section.all(), index, plex.tvdb_id, today):
            changed = (not a.dry_run) and plex.set_labels(it, {label} if label else set(), PREFIXES)
            print(f"{'DRY ' if a.dry_run else ''}{section.title:>18} | {it.title[:44]:<44} | {label} | {'changed' if changed else 'ok'}")

if __name__ == "__main__":
    main()
