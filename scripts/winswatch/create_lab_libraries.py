"""Create the two lab libraries via the Plex API, hide them from Home, verify no friend shares include them."""
import os, sys, requests
from pathlib import Path
from dotenv import load_dotenv

MOVIE_LIB, SHOW_LIB = "Wins Watch Lab", "Wins Watch Lab TV"

def _sections(url, token):
    r = requests.get(f"{url}/library/sections", headers={"X-Plex-Token": token, "Accept": "application/json"}, timeout=30); r.raise_for_status()
    return {d["title"]: d["key"] for d in r.json()["MediaContainer"].get("Directory", [])}

def create(url, token):
    have = _sections(url, token)
    if MOVIE_LIB in have or SHOW_LIB in have:
        print(f"already exist: {MOVIE_LIB}={have.get(MOVIE_LIB)} {SHOW_LIB}={have.get(SHOW_LIB)}"); return have.get(MOVIE_LIB), have.get(SHOW_LIB)
    specs = [(MOVIE_LIB, "movie", "tv.plex.agents.movie", "Plex Movie", "/data/media/_winswatch-lab/movies"),
             (SHOW_LIB, "show", "tv.plex.agents.series", "Plex TV Series", "/data/media/_winswatch-lab/tv")]
    for name, typ, agent, scanner, loc in specs:
        r = requests.post(f"{url}/library/sections", headers={"X-Plex-Token": token}, timeout=60,
                          params={"name": name, "type": typ, "agent": agent, "scanner": scanner, "language": "en-US", "location": loc})
        r.raise_for_status(); print(f"created {name}")
    have = _sections(url, token)
    for name in (MOVIE_LIB, SHOW_LIB):   # hide from Home / dashboard
        requests.put(f"{url}/library/sections/{have[name]}/prefs", headers={"X-Plex-Token": token}, params={"includeInGlobal": 0}, timeout=30)
    return have[MOVIE_LIB], have[SHOW_LIB]

def check_shares(token, machine_id, ids):
    r = requests.get(f"https://plex.tv/api/servers/{machine_id}/shared_servers", headers={"X-Plex-Token": token}, timeout=30)
    leaked = [s for s in ids if f'id="{s}"' in r.text and "shared=\"1\"" in r.text]
    print("share check:", "OK — lab libraries not shared" if not leaked else f"!! shared with friends: {leaked} — fix in Plex > Settings > Manage Library Access")

if __name__ == "__main__":
    load_dotenv(sys.argv[1] if len(sys.argv) > 1 else "/mnt/nastower/appdata/scripts/winswatch/.env")
    url, token = os.environ["PLEX_URL"], os.environ["PLEX_TOKEN"]
    m, s = create(url, token)
    Path("/mnt/nastower/appdata/scripts/winswatch/host/lab_sections").write_text(f"{m},{s}\n")
    mid = requests.get(f"{url}/identity", headers={"X-Plex-Token": token, "Accept": "application/json"}, timeout=30).json()["MediaContainer"]["machineIdentifier"]
    check_shares(token, mid, [m, s]); print(f"lab sections: {m},{s}")
