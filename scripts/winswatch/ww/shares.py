"""plex.tv share filters — the mechanism Shortlist uses to make a collection visible to one account only: the collection
carries a label, every *other* account's share gets `label!=<label>` merged into its filterMovies / filterTelevision.
Filters are account-wide (not per library), and Shortlist/Agregarr write the same strings, so they are always merged, never
overwritten: parse -> append our values -> unparse leaves every byte we did not add as it was.

Grammar (read from MyPlexUser.filterMovies 2026-09-21, and Shortlist's privacy.py notes, live-validated by them): conditions
`key=v1,v2,...` (keys contentRating, contentRating!, label, label!) joined by `|` (OR) or `&` (AND); plex.tv stores whatever it
is given byte-for-byte (`,` or `%2C` between values, either separator). Every account here holds a single
`label!=Shortlist_...,Agregarr...` condition, so we append to it. A NEW label! condition is joined with `&`: a PMS reads
`|` as OR and `contentRating!=R|label!=x` would hide nothing (a collection has no rating). Values compare case-insensitively
(Plex tags are), and Plex title-cases a new tag, so the label is written as `Winswatch_<slug>` — the form Plex stores.

Write path: `PUT https://plex.tv/api/users/{plex account id}?filterMovies=...&filterTelevision=...` (what Shortlist uses).
plexapi 4.18.2's updateFriend PUTs `/api/v2/sharings/{id}`, which plex.tv answers with 404 (verified 2026-09-21), so it is
not used."""
import re, time
from urllib.parse import unquote

KEY = "label!"
CLIENT_ID = "winswatch-home"
_COND_SEP = re.compile(r"([|&])")
_VALUE_SEP = re.compile(r"(%2C|%2c|,)")

def parse(current: str | None) -> list[dict]:
    """[{sep, key, values, vsep}] — sep joins the condition to the previous one ('' on the first), vsep is the value separator
    as read (default ',')."""
    out, sep = [], ""
    for part in _COND_SEP.split(current or ""):
        if part in ("|", "&"):
            sep = part; continue
        if not part:
            continue
        key, _, vals = part.partition("=")
        vseps = _VALUE_SEP.findall(vals)
        out.append({"sep": sep, "key": key, "values": [v for v in _VALUE_SEP.split(vals) if v and v not in ("%2C", "%2c", ",")],
                    "vsep": vseps[0] if vseps else ","})
        sep = ""
    return out

def unparse(conds: list[dict]) -> str:
    out = ""
    for i, c in enumerate(c for c in conds if c["values"]):
        out += ((c["sep"] or "&") if i else "") + f"{c['key']}={c['vsep'].join(c['values'])}"
    return out

def _same(a: str, b: str) -> bool:
    return unquote(a).casefold() == unquote(b).casefold()

def merge_exclusions(current: str | None, add: set[str], key: str = KEY) -> str:
    """Append the values of `add` that are not yet there (sorted) to the first `key` condition; create it (ANDed) if absent."""
    conds = parse(current)
    for c in conds:
        if c["key"] == key:
            c["values"] += sorted(v for v in add if not any(_same(v, have) for have in c["values"]))
            break
    else:
        if add:
            conds.append({"sep": "&" if conds else "", "key": key, "values": sorted(add), "vsep": ","})
    return unparse(conds)

def remove_exclusions(current: str | None, drop: set[str], key: str = KEY) -> str:
    """Inverse of merge_exclusions: drop the values; an emptied condition disappears with its separator."""
    conds = parse(current)
    for c in conds:
        if c["key"] == key:
            c["values"] = [v for v in c["values"] if not any(_same(v, d) for d in drop)]
    kept = [c for c in conds if c["values"]]
    if kept: kept[0]["sep"] = ""
    return unparse(kept)

def has_exclusions(current: str | None, values: set[str], key: str = KEY) -> bool:
    have = [v for c in parse(current) if c["key"] == key for v in c["values"]]
    return all(any(_same(v, h) for h in have) for v in values)

def apply(account, server_name: str, user, filter_movies: str | None, filter_tv: str | None, dry_run: bool) -> dict:
    """One plex.tv write per user with the filters that actually change (None = leave that filter alone). Returns the fields
    written ({} when nothing changed). Raises on a refused write (e.g. a managed account with a parental restriction profile
    answers 422) — the caller decides."""
    fields = {}
    if filter_movies is not None and filter_movies != (user.filterMovies or ""):
        fields["filterMovies"] = filter_movies
    if filter_tv is not None and filter_tv != (user.filterTelevision or ""):
        fields["filterTelevision"] = filter_tv
    if not fields or dry_run:
        return fields
    if not any(s.name == server_name for s in user.servers):
        raise LookupError(f"{user.title}: no share of server {server_name!r}")
    headers = {"X-Plex-Token": account._token, "X-Plex-Client-Identifier": CLIENT_ID}
    for attempt in range(4):
        r = account._session.put(f"https://plex.tv/api/users/{user.id}", params=fields, headers=headers, timeout=30)
        if r.status_code in (200, 201):
            return fields
        if r.status_code == 429 or 500 <= r.status_code < 600:
            time.sleep(2 ** attempt); continue
        break
    raise RuntimeError(f"plex.tv {r.status_code} on PUT /api/users/{user.id}: {(r.text or '')[:200]}")

# The PMS learns about a filter change from a plex.tv push (`notifySharingChange`) and answers it by re-reading ALL users'
# share settings (GET servers.plex.tv/api/v2/server/users) — but it handles at most one push per ~6 s and DROPS the ones in
# between (PMS 1.43.4 log, 2026-09-21: pushes every 2.1 s, re-reads at +0, +6.3, +12.6 s; the rest ignored). A batch of
# writes therefore leaves whoever was written after the last handled push with the OLD filter until the next sharing
# change, whenever that is (8 writes in 6 s: only user 1 enforced; a no-op write 5 min later: all 8). Hence one no-op
# write (`nudge`) after a quiet gap longer than the debounce: that push is handled and the re-read sees every write.
NUDGE_DELAY_S = 10.0

def nudge(account, user) -> None:
    """Re-PUT one user's filterTelevision unchanged: plex.tv still pushes notifySharingChange, the PMS re-reads every
    user's filters. Call once after a batch of apply() writes, with a user whose write was accepted. The value is re-read
    from plex.tv first — a stale in-memory MyPlexUser would write an old filter back. Raises on a non-2xx answer."""
    fresh = next(u for u in account.users() if u.id == user.id)
    headers = {"X-Plex-Token": account._token, "X-Plex-Client-Identifier": CLIENT_ID}
    r = account._session.put(f"https://plex.tv/api/users/{fresh.id}", params={"filterTelevision": fresh.filterTelevision or ""},
                             headers=headers, timeout=30)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"plex.tv {r.status_code} on nudge PUT /api/users/{fresh.id}: {(r.text or '')[:200]}")
