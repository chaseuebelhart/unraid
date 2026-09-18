"""Resolve the lab titles' folders from production Plex (read-only) and emit host/jobs/lab-media.sh (symlinks)."""
import os, sys
from pathlib import Path
from dotenv import load_dotenv
from ww.plexlib import PlexLib

LAB_MOVIES = ["Dune: Part Two", "Scary Movie", "The Holdovers", "Sinners", "Deadpool & Wolverine", "The Dark Knight", "Superbad", "Nimrods", "Home Alone", "Parasite"]
LAB_SHOWS = ["Reacher", "Severance", "The Bear", "Slow Horses", "The Afterparty"]
LAB_ROOT = "/mnt/user/data/media/_winswatch-lab"

def _q(s: str) -> str:
    # Always single-quote (unlike shlex.quote, which skips quoting for already-safe
    # strings) so every path in the generated script is quoted, not just the ones
    # with spaces/parens.
    return "'" + s.replace("'", "'\\''") + "'"

def symlink_script(paths: dict) -> str:
    lines = ["#!/bin/bash", "set -euo pipefail", f"mkdir -p {_q(LAB_ROOT + '/movies')} {_q(LAB_ROOT + '/tv')}"]
    for title, folder in paths.items():
        sub = "tv" if folder.startswith("/data/media/tv") else "movies"
        lines.append(f"ln -sfn {_q(folder)} {_q(f'{LAB_ROOT}/{sub}/{os.path.basename(folder)}')}")
    lines.append(f"ls -la {_q(LAB_ROOT + '/movies')} {_q(LAB_ROOT + '/tv')}")
    return "\n".join(lines) + "\n"

def resolve(plex: PlexLib) -> dict:
    out = {}
    for title in LAB_MOVIES:
        m = plex.section(1).search(title=title)
        m = [x for x in m if x.title == title] or m
        if not m: print(f"!! movie not found: {title}"); continue
        out[title] = os.path.dirname(m[0].media[0].parts[0].file)
    for title in LAB_SHOWS:
        s = plex.section(2).search(title=title)
        s = [x for x in s if x.title == title] or s
        if not s: print(f"!! show not found: {title}"); continue
        ep = s[0].episodes()[0]
        f = ep.media[0].parts[0].file          # /data/media/tv/Show (Year)/Season 01/file.mkv
        out[title] = f.split("/Season")[0] if "/Season" in f else os.path.dirname(os.path.dirname(f))
    return out

if __name__ == "__main__":
    load_dotenv(sys.argv[1] if len(sys.argv) > 1 else "/mnt/nastower/appdata/scripts/winswatch/.env")
    plex = PlexLib(os.environ["PLEX_URL"], os.environ["PLEX_TOKEN"])
    paths = resolve(plex)
    dest = Path(__file__).parent / "host/jobs/lab-media.sh"; dest.write_text(symlink_script(paths))
    print(dest.read_text())
