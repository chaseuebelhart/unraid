"""Rewrite the production Kometa config.yml for the Wins Watch overlays (Task 10).

    python promote_config.py <config.yml> --phase reset|steady [--write]

reset  : remove_overlays: true, mass_user_rating_update: remove   (run ONCE: strips the old overlays and the old RT user ratings)
steady : remove_overlays: false, mass_user_rating_update commented out (the nightly state: scores.py writes the MDBList score
         into the user-rating slot through the metadata-edit path; Kometa's own mdb writer goes through /:/rate, which plex.tv
         echoes back rounded to whole numbers — every poster then lands on a multiple of 10)

Both phases replace every `overlay_files:` entry of the Movies / TV Shows libraries with the Wins Watch files and set
mass_critic_rating_update: mdb_metacritic, mass_audience_rating_update: mdb_letterboxd (Movies) / mdb_trakt (TV Shows).
The file is edited textually so comments and everything else survive. Prints a unified diff; writes only with --write."""
import argparse, difflib, re, sys
from pathlib import Path

FILES = {
    "Movies": ["movies.yml", "generated/chips_movies.yml", "generated/gauge.yml", "generated/topedge.yml"],
    "TV Shows": ["shows.yml", "seasons.yml", "episodes.yml", "generated/chips_episodes.yml", "generated/gauge.yml",
                 "generated/topedge.yml", "generated/status.yml"],
}
AUDIENCE = {"Movies": "mdb_letterboxd", "TV Shows": "mdb_trakt"}

def _lib_ranges(lines):
    """(name, start, end) for every library under `libraries:` (2-space keys until the next column-0 key)."""
    out, i = [], 0
    while i < len(lines) and not lines[i].startswith("libraries:"): i += 1
    i += 1; cur = None
    for j in range(i, len(lines) + 1):
        line = lines[j] if j < len(lines) else "\x00"
        top = line == "\x00" or (line and not line[0].isspace() and not line.startswith("#"))
        m = re.match(r"^  ([A-Za-z][^:#]*):", line)
        if top or m:
            if cur: out.append((cur[0], cur[1], j)); cur = None
            if top: break
            cur = (m.group(1).strip(), j)
    return out

def rewrite(text: str, phase: str) -> str:
    lines = text.split("\n")
    for name, start, end in reversed(_lib_ranges(lines)):
        if name not in FILES: continue
        seg = lines[start:end]
        # 1. overlay_files block -> ours
        k = next(i for i, l in enumerate(seg) if re.match(r"^    overlay_files:", l))
        e = k + 1
        while e < len(seg) and not re.match(r"^    [a-z_]+:", seg[e]) and not (seg[e] and seg[e][0] == "#"): e += 1
        block = ["    overlay_files:                                  # Wins Watch (scripts/winswatch, kometa/overlays/winswatch)"] + \
                [f"    - file: config/winswatch/{f}" for f in FILES[name]]
        seg[k:e] = block
        # 2. operations
        def setop(key, val):
            for i, l in enumerate(seg):
                if re.match(rf"^      (# )?{key}:", l):
                    seg[i] = f"      {key}: {val}" if val else f"      # {key}: (winswatch scores.py owns this slot)"; return
            raise SystemExit(f"{name}: operations key {key} not found")
        setop("mass_user_rating_update", "remove" if phase == "reset" else None)
        setop("mass_critic_rating_update", "mdb_metacritic")
        setop("mass_audience_rating_update", AUDIENCE[name])
        for i, l in enumerate(seg):
            if re.match(r"^    remove_overlays:", l):
                seg[i] = f"    remove_overlays: {'true' if phase == 'reset' else 'false'}"
        lines[start:end] = seg
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("config"); ap.add_argument("--phase", choices=["reset", "steady"], required=True)
    ap.add_argument("--write", action="store_true"); a = ap.parse_args()
    p = Path(a.config); old = p.read_text(); new = rewrite(old, a.phase)
    sys.stdout.writelines(difflib.unified_diff(old.splitlines(True), new.splitlines(True), "config.yml", f"config.yml ({a.phase})"))
    if a.write:
        p.write_text(new); print(f"\nwrote {p}")

if __name__ == "__main__":
    main()
