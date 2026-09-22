"""Post-condition health checks for the Wins Watch Home nightly (design §10).

Every function here is pure: it takes numbers/titles that `home.py check` has already read from Plex, Maintainerr and
Sonarr and returns a `Result`. Nothing in this module talks to the network, so the thresholds are unit-testable.

Why it exists: on 2026-09-21 two collections were renamed ("Movies/Shows Leaving Soon" -> "⏳ … Leaving Wins Watch") and
Chase's separate DaysLeft labeler — which looked its collections up by exact title — silently stopped writing
`DaysLeft_*` labels. Every LEAVING bookmark vanished from every poster and no job noticed. These checks compare what each
producer *should* have written against the source it writes from, so the next silent stop is one line in the log."""
from dataclasses import dataclass

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
RANK = {PASS: 0, WARN: 1, FAIL: 2}

# Label namespaces the nightly writes. AIRDATE_PREFIXES must stay == airdates.PREFIXES (a test asserts it).
DAYS_LEFT_PREFIX = "DaysLeft_"
AIRDATE_PREFIXES = ("NewEp_", "ReturnsIn_", "Returns_")
REQUESTED_LABEL = "Requested"

DAYS_LEFT_TOLERANCE = 2      # the labeler and Maintainerr are hours apart; a couple of items of churn is normal
AIRDATE_FLOOR = 10           # below this many continuing shows, "zero labels" is not conclusive
SCORE_FAIL, SCORE_WARN = 0.50, 0.90
_FIXED = ["✨ ", "🔥 Trending ", "📥 New ", "👥 Popular ", "⏳ "]   # == ww.plexhome.FIXED_TOP (a test asserts it)
MIN_SHELVES = 2              # design §1: two theme/seasonal shelves below the five fixed rows

HEADER = "==================== WINS WATCH HEALTH CHECK ===================="
FOOTER = "==================== END WINS WATCH HEALTH CHECK ================"


@dataclass(frozen=True)
class Result:
    check: str
    scope: str
    got: int
    expected: int
    status: str
    detail: str = ""

    def line(self) -> str:
        return f"{self.status:<4} | {self.check:<17} | {self.scope:<18} | {self.got:>5} vs {self.expected:<5} | {self.detail}"


def worst(results) -> str:
    return max((r.status for r in results), key=lambda s: RANK[s], default=PASS)


def render(results) -> list[str]:
    """The whole block the nightly prints, delimiters included, so it is findable in host/last.log."""
    counts = {s: sum(1 for r in results if r.status == s) for s in (PASS, WARN, FAIL)}
    return ([HEADER] + [r.line() for r in results] +
            [f"---- {len(results)} checks: {counts[PASS]} PASS, {counts[WARN]} WARN, {counts[FAIL]} FAIL", FOOTER])


def _match(title: str, desired: list[str]):
    """Index of the first row prefix `title` starts with, or None. Same matching as ww.plexhome.plan."""
    return next((i for i, p in enumerate(desired) if title.startswith(p)), None)


# --- the checks -----------------------------------------------------------------------------------------------------

def check_days_left(scope: str, labelled: int, collections: list, media_type: str = "") -> Result:
    """`DaysLeft_*` labels in one library vs the member count of that library's Maintainerr collection.

    `collections` = the Maintainerr collections whose `type` is this library's (ww.maintainerr normalises them to
    {"title", "type", "media_count"}). Matched by type on purpose: matching by title is the bug this check exists for."""
    members = sum(c["media_count"] for c in collections)
    titles = ", ".join(c["title"] for c in collections) or f"(none of type {media_type!r})"
    if not collections:
        return Result("days-left labels", scope, labelled, 0, FAIL, f"no Maintainerr collection of type {media_type!r}")
    if members and not labelled:
        return Result("days-left labels", scope, labelled, members, FAIL,
                      f"{titles}: collection has members but nothing is labelled — the labeler is not running")
    if abs(labelled - members) > DAYS_LEFT_TOLERANCE:
        return Result("days-left labels", scope, labelled, members, WARN, f"{titles}: off by {abs(labelled - members)}")
    return Result("days-left labels", scope, labelled, members, PASS, titles)


def check_airdates(scope: str, labelled: int, continuing: int) -> Result:
    """`NewEp_*`/`ReturnsIn_*`/`Returns_*` labels vs the shows Sonarr calls continuing (or upcoming) and monitored."""
    if not labelled and continuing > AIRDATE_FLOOR:
        return Result("air-date labels", scope, labelled, continuing, FAIL,
                      f"Sonarr has {continuing} continuing shows and none is labelled — airdates.py is not landing")
    if labelled * 2 < continuing:
        return Result("air-date labels", scope, labelled, continuing, WARN, "fewer than half the continuing shows carry a label")
    return Result("air-date labels", scope, labelled, continuing, PASS, "")


def check_scores(scope: str, rated: int, total: int) -> Result:
    """Share of top-level items with a non-null userRating (scores.py writes it from the MDBList score)."""
    share = rated / total if total else 1.0
    status = FAIL if share < SCORE_FAIL else WARN if share < SCORE_WARN else PASS
    return Result("score coverage", scope, rated, total, status, f"{share * 100:.1f}% rated")


def check_requested(scope: str, labelled: int) -> Result:
    """`Requested` labels (the REQUESTED poster badge). Never FAILs: a month with no new requests is legitimate."""
    status = WARN if labelled == 0 else PASS
    return Result("requested labels", scope, labelled, 1, status,
                  "no Requested labels (legitimate if nothing was requested lately)" if status == WARN else "")


def check_home_rows(scope: str, promoted_titles: list[str], desired: list[str]) -> Result:
    """Promoted hub titles, in their current order, vs ww.plexhome.desired_order for today.

    FAIL when any of the five fixed rows has no promoted hub, or when fewer than two theme/seasonal shelves are
    promoted. WARN on an order mismatch only — the hourly `order` pass fixes those by itself."""
    fixed, shelves = desired[:len(_FIXED)], range(len(_FIXED), len(desired) - 1)
    hit = [_match(t, desired) for t in promoted_titles]
    covered = {i for i in hit if i is not None}
    missing = [p for i, p in enumerate(fixed) if i not in covered]
    n_shelves = sum(1 for i in shelves if i in covered)
    got, expected = len(covered), len(desired)
    if missing:
        return Result("home rows", scope, got, expected, FAIL, "no promoted hub for: " + ", ".join(repr(p) for p in missing))
    if n_shelves < MIN_SHELVES:
        return Result("home rows", scope, got, expected, FAIL,
                      f"only {n_shelves} of {MIN_SHELVES} theme/seasonal shelves promoted (wanted {', '.join(desired[len(_FIXED):-1])})")
    seq = [i for i in hit if i is not None]
    if seq != sorted(seq):
        return Result("home rows", scope, got, expected, WARN, "promoted hubs are out of order (the hourly `order` pass will fix it)")
    return Result("home rows", scope, got, expected, PASS, " · ".join(desired[i] for i in sorted(covered)))


def check_user_rows(scope: str, rows: int, users: int) -> Result:
    """One `📥 New …` collection per shared/home user (home._users). A missing one means that user has no New row."""
    status = FAIL if rows < users else WARN if rows > users else PASS
    detail = ("missing a per-user row" if status == FAIL else
              "more rows than users — a former user's row was left behind" if status == WARN else "")
    return Result("per-user rows", scope, rows, users, status, detail)


def check_cards(scope: str, matched: list, cache: dict) -> Result:
    """Every collection matched by a row prefix should carry a poster we uploaded.

    `matched` = [(ratingKey (str), title, card slug)] for the rows gen_cards owns; `cache` = cache/cards.json
    ({ratingKey: slug}). WARN only: the uploads are best-effort and a card can be re-uploaded any time."""
    missing = [t for key, t, slug in matched if cache.get(key) != slug]
    got = len(matched) - len(missing)
    status = WARN if missing else PASS
    return Result("cards", scope, got, len(matched), status,
                  "no card uploaded for: " + ", ".join(missing) if missing else "")
