import os
import requests
import re
from utils.env_loader import load_project_env, get_repo_root

# Load .env from repo root
load_project_env()

API_KEY = os.getenv("TMDB_API_KEY")
if not API_KEY:
    raise RuntimeError("TMDB_API_KEY is not set in .env")


def parse_title_year(line):
    m = re.match(r"(.+?)\s*\((\d{4})\)$", line.strip())
    if m:
        return m.group(1), int(m.group(2))
    return line.strip(), None

def search_movie(title, year=None):
    params = {
        "api_key": API_KEY,
        "query": title,
    }
    if year:
        params["year"] = year

    r = requests.get("https://api.themoviedb.org/3/search/movie", params=params)
    r.raise_for_status()
    data = r.json()
    results = data.get("results", [])
    if not results:
        return None

    # If year was specified, prefer exact year matches
    if year:
        for res in results:
            if res.get("release_date", "").startswith(str(year)):
                return res

    # Fallback to the first result
    return results[0]


tmdb_ids = []
repo_root = get_repo_root(__file__)
tmdb_path = os.path.join(repo_root, "kometa", "scripts", "tmdb_id.txt")
with open(tmdb_path, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        title, year = parse_title_year(line)
        res = search_movie(title, year)
        if not res:
            print(f"# NOT FOUND: {line}")
            continue
        movie_id = res["id"]
        name = res["title"]
        date = res.get("release_date", "")
        print(f"      - {movie_id:<7}  # {name} ({date[:4]})")
        tmdb_ids.append(movie_id)
