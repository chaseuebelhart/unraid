"""MDBList score -> Plex user rating (0-10) + Votes_<bucket> label. Idempotent. Never touches sections you don't pass."""
import argparse, os
from pathlib import Path
from dotenv import load_dotenv
from ww.plexlib import PlexLib
from ww import mdblist
from ww.buckets import votes_bucket

def plan(items, fetch, tmdb_id, kind):
    out = []
    for it in items:
        tid = tmdb_id(it)
        if not tid:
            out.append((it, None, None)); continue
        d = fetch(kind, tid)
        rating = round(d["score"] / 10, 1) if d.get("score") is not None else None
        b = votes_bucket(d.get("votes") or 0)
        out.append((it, rating, f"Votes_{b}" if b else None))
    return out

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--sections", required=True); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--env", default=".env")
    a = ap.parse_args(); load_dotenv(a.env)
    plex = PlexLib(os.environ["PLEX_URL"], os.environ["PLEX_TOKEN"]); key = os.environ["MDBLIST_API_KEY"]
    cache_path = Path(os.environ.get("CACHE_DIR", "cache")) / "mdblist.json"; cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache = mdblist.load_cache(cache_path)
    try:
        for sec in a.sections.split(","):
            section = plex.section(int(sec)); kind = "movie" if section.type == "movie" else "show"
            for it, rating, label in plan(section.all(), lambda k, t: mdblist.fetch(key, k, t, cache), plex.tmdb_id, kind):
                changed = []
                if not a.dry_run:
                    if rating is not None and plex.set_user_rating(it, rating): changed.append(f"rating={rating}")
                    if plex.set_labels(it, {label} if label else set(), ("Votes_",)): changed.append(f"label={label}")
                print(f"{'DRY ' if a.dry_run else ''}{section.title:>18} | {it.title[:44]:<44} | {rating} | {label} | {' '.join(changed) or 'ok'}")
    finally:
        mdblist.save_cache(cache_path, cache)

if __name__ == "__main__":
    main()
