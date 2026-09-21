"""Render the Home rotation (home_calendar.yml) into Kometa collection files. Deterministic; re-run after editing the calendar."""
import sys
from pathlib import Path
import yaml

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / "kometa/collections/winswatch"
DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
CARD = "config/winswatch/cards/{slug}.png"


def _theme(lib, emoji, slug, sort, filter=None, tmdb_movie=None, summary=None, collection_mode=None):
    return {
        "lib": lib, "emoji": emoji, "card": slug, "sort": sort,
        "filter": filter, "tmdb_movie": tmdb_movie, "summary": summary, "collection_mode": collection_mode,
    }


# smart_filter blocks copied from kometa/collections/*.yml with two changes: `rating.gte` -> `user_rating.gte`
# (our MDBList score /10 — `rating` silently meant critic rating, which is now Metacritic and often empty) and
# no `Kids` genre (Plex has no such genre in this library). `limit` and `sort_by` are dropped here and set
# uniformly by `_coll` (limit 40, sort_by random — the reshuffle mechanism; smart collections never carry
# `collection_order`, which is what silently broke Halloween / Date Night / Sunday Slow Burn before).
#
# Edge of Your Seat is retuned per the design spec: its old filter matched ~0 shows because the file used a
# genre name that's too narrow for this library. Retuned thresholds and genre lists were validated against
# Plex in Step 6 (see task-1-report.md for counts). Not Just Cartoons was retuned the same way but still
# couldn't clear the bar and was dropped from the rotation entirely — see the note above THEMES_BY_LIB.
THEMES = {
    "Adrenaline Rush": _theme("movies", "💥", "adrenaline-rush", "!08_Adrenaline_Rush", filter={
        "all": {
            "user_rating.gte": 6.0,
            "release": 3652,  # last 10 years
            "genre.not": ["Animation", "Horror", "Family"],
            "any": {"genre": ["Action", "Thriller"]},
        }}),
    "Crime Files": _theme("movies", "🕵️", "crime-files", "!08_Crime_Files", filter={
        "all": {
            "user_rating.gte": 6.0,
            "genre.not": ["Animation", "Horror", "Family"],
            "genre": ["Crime"],
        }}),
    "Sci-Fi Odyssey": _theme("movies", "🚀", "sci-fi-odyssey", "!10_Sci_Fi_Odyssey", filter={
        "all": {
            "user_rating.gte": 6.0,
            "genre.not": ["Animation", "Family", "Horror"],
            "genre": ["Science Fiction"],
        }}),
    "Hidden Gems": _theme("movies", "💎", "hidden-gems", "!11_Hidden_Gems", filter={
        "all": {
            "user_rating.gte": 7.5,
            "genre.not": ["Animation", "Family", "Documentary", "Horror"],
        }}),
    "Love & Laughs": _theme("movies", "💘", "love-and-laughs", "!09_Love_and_Laughs", filter={
        "all": {
            "title.not": ["porn", "Joe Dirt"],
            "genre.not": ["Animation", "Horror"],
            "any": {
                "all": {"genre": ["Romance", "Comedy"]},
                "title.is": ["Silver Linings Playbook", "The Notebook"],
            },
        }}),
    "Mind Benders": _theme("movies", "🌀", "mind-benders", "!10_Mind_Benders", filter={
        "all": {
            "user_rating.gte": 7.0,
            "genre.not": ["Animation", "Family", "Horror", "Action"],
            "any": {"genre": ["Mystery", "Thriller"]},
        }}),
    "Based on a True Story": _theme("movies", "📰", "based-on-a-true-story", "!11_Based_on_a_True_Story", filter={
        "all": {
            "user_rating.gte": 6.5,
            "genre.not": ["Animation", "Horror", "Family"],
            "any": {"genre": ["History", "War"]},
        }}),
    "Director's Spotlight": _theme("movies", "🎬", "directors-spotlight", "!07_Directors_Spotlight", filter={
        "all": {
            "user_rating.gte": 7.0,
            "genre.not": ["Animation", "Horror", "Family"],
            "all": [
                {"any": {"genre": ["Drama", "History"]}},
                {"any": {
                    "director": [
                        "Ron Howard", "Steven Spielberg", "Richard Linklater", "Alexander Payne",
                        "Greta Gerwig", "Marc Forster", "Clint Bentley", "Denis Villeneuve",
                        "Alfonso Cuarón", "Martin Scorsese", "Paul Thomas Anderson", "Joel Coen",
                        "Ethan Coen", "Damien Chazelle", "Ridley Scott", "Christopher Nolan",
                        "Quentin Tarantino",
                    ],
                    "actor": [
                        "Matt Damon", "Emily Blunt", "Cate Blanchett", "Ryan Gosling", "Bradley Cooper",
                        "Christian Bale", "Leonardo DiCaprio", "Matthew McConaughey", "Joaquin Phoenix",
                        "Adam Driver", "Robert De Niro", "Tom Hanks", "Al Pacino", "Jack Nicholson",
                        "Brad Pitt", "Denzel Washington",
                    ],
                }},
            ],
        }}),
    "Fresh Picks": _theme("movies", "🍿", "fresh-picks", "!06_Fresh_Picks", filter={
        "all": {
            "user_rating.gte": 6.0,
            "genre.not": ["Animation", "Horror", "Family"],
            "release": 1460,  # last 4 years
            "all": [{"any": {"genre": ["Drama", "History"]}}],
        }}),
    # Raunchy Comedy has no smart_filter in the old file (raunchy_comedy.yml is a hard-coded tmdb_movie list —
    # "raunchy comedy" isn't a Plex genre); kept as a curated list here rather than forced into a genre filter.
    "Raunchy Comedy": _theme(
        "movies", "🍺", "raunchy-comedy", "!05_Raunchy_Comedy",
        summary="Over-the-top, dumb, raunchy comedies from the Ferrell/Rogen/Sandler/McBride universe.",
        collection_mode="hide",
        tmdb_movie=[
            12133, 8699, 9718, 11635, 9955, 8363, 10189, 109414, 6957, 4964,
            10358, 20829, 195589, 10074, 38319, 13484, 18785, 9614, 11017, 9032,
            10663, 9678, 2022, 9291, 87428, 9900, 10956, 9398, 37931, 9988,
            9472, 138832, 7446, 39939, 2294, 15373, 136795, 41733, 51540, 49520,
            57214, 9352, 76493, 290250, 496, 9522, 9870,
        ],
    ),
    "Worlds Beyond": _theme("shows", "🪐", "worlds-beyond", "!06_Worlds_Beyond", filter={
        "all": {
            "user_rating.gte": 6.5,
            "genre.not": ["Animation", "Family"],
            "any": {"genre": ["Action & Adventure", "Sci-Fi & Fantasy"]},
        }}),
    "Peak TV": _theme("shows", "🏔️", "peak-tv", "!06_Peak_TV", filter={
        "all": {
            "user_rating.gte": 7,
            "genre.not": ["Animation", "Family", "Comedy"],
            "genre": ["Drama"],
        }}),
    "Crime Beat": _theme("shows", "🚔", "crime-beat", "!07_Crime_Beat", filter={
        "all": {
            "user_rating.gte": 6.0,
            "genre.not": ["Animation", "Family"],
            "any": {"genre": ["Crime"]},
        }}),
    "Comfort Binge": _theme("shows", "🛋️", "comfort-binge", "!07_Comfort_Binge", filter={
        "all": {
            "user_rating.gte": 6.0,
            "genre": ["Comedy"],
        }}),
    "Just Dropped": _theme("shows", "📺", "just-dropped", "!05_Just_Dropped", filter={
        "all": {
            "user_rating.gte": 6.0,
            "release": 730,  # last 2 years
            "any": {"network": [
                "Netflix", "Disney+", "Hulu", "Prime Video", "Apple TV", "HBO", "HBO Max",
                "Paramount+", "Peacock",
            ]},
        }}),
    "Edge of Your Seat": _theme("shows", "🎢", "edge-of-your-seat", "!08_Edge_of_Your_Seat", filter={
        "all": {
            "user_rating.gte": 6.5,
            "genre.not": ["Animation", "Family"],
            "genre": ["Mystery", "Crime"],
        }}),
    # Not Just Cartoons was dropped from the rotation (coordinator ruling, Fix round 1): the TV library only
    # has 6 titles total tagged Plex genre Animation, so no rating threshold gets it to the >=15-match bar.
}
THEMES_BY_LIB = {lib: [n for n, t in THEMES.items() if t["lib"] == lib] for lib in ("movies", "shows")}

# Not in the rotation: fixed schedules (weekend extras + seasonal). sort_title kept exactly as the old files had
# it. Christmas Movies has no smart_filter in the old file either (a curated tmdb_movie list); kept as-is.
EXTRAS = {
    "Date Night": _theme("movies", "🍷", "date-night", "!12_Date_Night", filter={
        "all": {
            "user_rating.gte": 6.0,
            "genre.not": ["Horror", "Animation", "Documentary"],
            "any": {"genre": ["Romance", "Drama", "Comedy"]},
        }}),
    "Sunday Slow Burn": _theme("movies", "☕", "sunday-slow-burn", "!12_Sunday_Slow_Burn", filter={
        "all": {
            "user_rating.gte": 7.0,
            "duration.gte": 90,
            "genre.not": ["Action", "Horror", "Animation", "Family"],
            "genre": ["Drama"],
        }}),
    "Halloween": _theme("movies", "🎃", "halloween", "!02_Halloween", filter={
        "all": {
            "user_rating.gte": 6.0,
            "any": {"genre": ["Horror", "Thriller"]},
        }}),
    "Christmas Movies": _theme(
        "movies", "🎄", "christmas", "!02_Christmas_Movies",
        summary="A curated collection of Christmas classics and holiday favorites. Visible each year from November through December.",
        tmdb_movie=[
            771, 772, 10719, 5825, 11395, 8871, 5255, 850, 1585, 9479,
            527435, 508, 51052, 360920, 508965, 9279, 1581, 10147, 10437, 562,
            520172, 9043, 9647, 13376, 9021, 5375, 615666, 454467, 654028, 12193,
        ],
    ),
    "Valentine's Picks": _theme("movies", "💘", "valentines", "!02_Valentines_Picks", filter={
        "all": {
            "user_rating.gte": 6.0,
            "genre.not": ["Horror", "Animation"],
            "genre": ["Romance"],
        }}),
    "Awards Season": _theme("movies", "🏆", "awards-season", "!02_Awards_Season", filter={
        "all": {
            "user_rating.gte": 7.5,
            "genre.not": ["Animation", "Family", "Horror"],
            "any": {"genre": ["Drama", "History", "War"]},
        }}),
}
EXTRA_SCHEDULE = {
    "Date Night": "weekly(friday|saturday)",
    "Sunday Slow Burn": "weekly(sunday)",
    "Halloween": "range(09/15-10/31)",
    "Christmas Movies": "range(11/01-12/31)",
    "Valentine's Picks": "range(02/01-02/14)",
    "Awards Season": "range(01/01-03/15)",
}


def load_calendar(path):
    cal = yaml.safe_load(Path(path).read_text())
    return {lib: [list(d) for d in cal[lib]] for lib in ("movies", "shows")}


def weekly_schedule(days, theme):
    on = sorted({i % 7 for i, d in enumerate(days) if theme in d})
    return "weekly(" + "|".join(DAYS[i] for i in on) + ")"


def _coll(sort, slug, sched, t):
    doc = {
        "sort_title": sort,
        "file_poster": CARD.format(slug=slug),
        "visible_home": sched,
        "visible_shared": sched,
        "visible_library": True,
    }
    if t.get("summary"):
        doc["summary"] = t["summary"]
    if t.get("collection_mode"):
        doc["collection_mode"] = t["collection_mode"]
    if t.get("filter") is not None:
        flt = dict(t["filter"])
        flt["limit"] = 40
        flt["sort_by"] = "random"
        doc["smart_filter"] = flt
    else:
        doc["tmdb_movie"] = list(t["tmdb_movie"])
        doc["collection_order"] = "random"
    return doc


def render(cal, themes):
    out = {"home_movies.yml": {"collections": {}}, "home_shows.yml": {"collections": {}}}
    for name, t in themes.items():
        f = "home_movies.yml" if t["lib"] == "movies" else "home_shows.yml"
        sched = weekly_schedule(cal[t["lib"]], name)
        out[f]["collections"][f"{t['emoji']} {name}"] = _coll(t["sort"], t["card"], sched, t)
    for name, t in EXTRAS.items():
        out["home_movies.yml"]["collections"][f"{t['emoji']} {name}"] = _coll(t["sort"], t["card"], EXTRA_SCHEDULE[name], t)
    return out


def write(out_dir=OUT):
    out_dir.mkdir(parents=True, exist_ok=True)
    for fname, doc in render(load_calendar(HERE / "home_calendar.yml"), THEMES).items():
        (out_dir / fname).write_text(
            "# GENERATED by scripts/winswatch/gen_home.py from home_calendar.yml — do not edit\n"
            + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=4096)
        )


if __name__ == "__main__":
    write(Path(sys.argv[1]) if len(sys.argv) > 1 else OUT)
    print("wrote home_movies.yml, home_shows.yml")
