"""Wins Watch Home: Plex-side state for the home screen. Usage: home.py <requested|rows|cards|order> --sections 1,2 [--dry-run] [--env PATH]

requested — one `Requested` label per item that an Overseerr request made available in the last 30 days (Kometa draws the
            REQUESTED badge from it; a LEAVING bookmark / status tab suppresses the badge via label.not in the overlay YAML).
order     — sort each library's promoted hubs into the design §1 row order for today and demote the rest (ww/plexhome.py).
rows      — per-user 📥 New · Your Requests collections (ww/shares.py). cards — upload the generated collection cards."""
import argparse, hashlib, os, re, time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from ww.plexlib import PlexLib
from ww import overseerr, plexhome
import gen_cards, gen_home

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

def cmd_order(a, env):
    """Sort each section's managed hubs into design §1 order for today and demote every other promoted hub (§6)."""
    p, day = plex(env), today(env)
    cal = gen_home.load_calendar(Path(__file__).with_name("home_calendar.yml"))
    for sec in sections(a.sections):
        section = p.section(sec)
        hubs = section.managedHubs()
        plexhome.resolve_titles(hubs, {str(c.ratingKey): c.title for c in section.collections()})
        ordered, demote = plexhome.plan(hubs, plexhome.desired_order(plexhome.lib_for(section), day, cal))
        plexhome.apply(section, ordered, demote, a.dry_run)

# --- rows: per-user "📥 New · Your Requests" collections (Task 3) ---------------------------------------------------------
# One collection per shared/home user and library, visible to that user only through the Shortlist mechanism: label
# `Winswatch_<slug>` on the collection (Plex title-cases tags), `label!=Winswatch_<slug>` merged into every OTHER account's share filter (ww.shares).
# Plex needs distinct titles, so each gets an invisible zero-width suffix (row_title). The owner gets no row (no share with self).
NEW_BASE = {"movie": "📥 New Movies · Your Requests", "show": "📥 New Shows · Your Requests"}
N_RECENT, REQUEST_DAYS, SERVER_NAME = 40, 90, "NASTower"
ZW0, ZW1 = "​", "‌"   # Shortlist's (client-proven) zero-width alphabet: bits of the Plex account id, LSB first (0 -> U+200B, 1 -> U+200C)
# MARKER_BITS must stay != 64: Shortlist's sweep_broken_rows treats ANY collection whose last 64 chars are all zero-width as
# its own orphan when it lacks a Shortlist_ label, and DELETES it (it did, to all 16 rows, on 2026-09-21). 40 bits is still
# injective over Plex account ids (32-bit ints) and never looks like a Shortlist marker.
MARKER_BITS = 40

def user_slug(username: str) -> str:
    """Shortlist's slug: lower-case, every run of non-alphanumerics -> '_' (Lily.Arnold -> lily_arnold, Chase_Test -> chase_test)."""
    return re.sub(r"[^a-z0-9]+", "_", username.lower()).strip("_")

def row_title(base: str, ident) -> str:
    """base + MARKER_BITS zero-width chars. ident = the Plex account id (int); a slug (str) -> a stable hash of it (tests /
    users without an id). Same alphabet as Shortlist's marker, different length — see MARKER_BITS."""
    value = ident if isinstance(ident, int) else int.from_bytes(hashlib.blake2b(ident.encode(), digest_size=8).digest(), "little")
    assert 0 <= value < (1 << MARKER_BITS) or not isinstance(ident, int), f"account id {ident} does not fit the {MARKER_BITS}-bit marker"
    return base + "".join(ZW1 if (value >> i) & 1 else ZW0 for i in range(MARKER_BITS))

def strip_zw(title: str) -> str:
    return title.rstrip(ZW0 + ZW1)

def build_new_row(recent: list, requests: list, n_recent: int = N_RECENT) -> list:
    """Weave: the user's requests take every 4th slot from index 1 (1, 5, 9, …) in the newest-added run; leftovers are appended.
    A requested item that is also in `recent` keeps only its request slot. De-duplicated by ratingKey."""
    seen, reqs = set(), []
    for q in requests:
        if q.ratingKey not in seen:
            seen.add(q.ratingKey); reqs.append(q)
    rec = [r for r in recent if r.ratingKey not in seen][:n_recent]
    out, qi = [], 0
    for r in rec:
        if len(out) % 4 == 1 and qi < len(reqs):
            out.append(reqs[qi]); qi += 1
        out.append(r)
    return out + reqs[qi:]

def exclusions_for(users) -> dict:
    """{user.id: {"Winswatch_<slug>" of every OTHER user}} — the full desired set per account, so one plex.tv write each."""
    labels = {u.id: f"Winswatch_{u.slug}" for u in users}
    return {u.id: {l for uid, l in labels.items() if uid != u.id} for u in users}

def _requests_for(section, p: PlexLib, reqs: list) -> dict:
    """{plex account id: [items of this section the user requested, newest request first]} — resolves like plan_requested:
    Overseerr's ratingKey when it has one, else (type, tmdb guid) within the section (Overseerr's Plex scan is dead since 2025-11)."""
    by_key, by_tmdb = {}, {}
    for it in section.all():
        by_key[str(it.ratingKey)] = it
        tid = p.tmdb_id(it)
        if tid: by_tmdb[(it.type, str(tid))] = it
    out = {}
    for r in sorted(reqs, key=lambda r: r.get("created_at") or "", reverse=True):
        if r.get("status") not in AVAILABLE or r.get("requested_by_plex_id") is None:
            continue
        it = by_key.get(str(r["plex_rating_key"])) if r.get("plex_rating_key") else None
        if it is None and r.get("tmdb_id") is not None:
            it = by_tmdb.get((_ITEM_TYPE.get(r.get("type")), str(r["tmdb_id"])))
        if it is not None and it.type == section.TYPE:
            out.setdefault(int(r["requested_by_plex_id"]), []).append(it)
    return out

def _users(account) -> list:
    """Shared + home users (the owner is not in the list), each with `.slug`."""
    users = account.users()
    for u in users:
        u.slug = user_slug(u.username or u.title)
    return users

def plan_filters(users, kinds, merge=None) -> tuple[dict, list]:
    """({kind: {user.id: desired filter string}}, problems) for the section kinds processed. A filter that does not
    round-trip through parse/unparse is never rewritten (unparse would drop what it could not read): that user is
    skipped and reported."""
    from ww import shares
    merge = merge or shares.merge_exclusions
    wanted, problems = {"movie": {}, "show": {}}, []
    excl = exclusions_for(users)
    for u in users:
        for kind in kinds:
            current = (u.filterMovies if kind == "movie" else u.filterTelevision) or ""
            if shares.unparse(shares.parse(current)) != current:
                problems.append(f"!! filter for {u.title} ({'filterMovies' if kind == 'movie' else 'filterTelevision'}) does not round-trip, skipping: {current!r}")
                continue
            wanted[kind][u.id] = merge(current, excl[u.id])
    return wanted, problems

def cmd_rows(a, env):
    from plexapi.myplex import MyPlexAccount
    from ww import shares
    p = plex(env)
    account = MyPlexAccount(token=env["PLEX_TOKEN"])
    users = _users(account)
    reqs = overseerr.Client(env["OVERSEERR_URL"], env["OVERSEERR_API_KEY"]).requests(since_days=REQUEST_DAYS)
    dry = "DRY " if a.dry_run else ""
    problems, kinds = [], []
    for sec in sections(a.sections):
        section = p.section(sec)
        base = NEW_BASE[section.TYPE]
        recent = section.search(sort="addedAt:desc", maxresults=N_RECENT, libtype=section.TYPE)
        per_user = _requests_for(section, p, reqs)
        for u in users:
            items = build_new_row(recent, per_user.get(u.id, []))
            title, label = row_title(base, u.id), f"Winswatch_{u.slug}"
            print(f"{dry}{section.title:>18} | {strip_zw(title)} [{u.slug}] | {len(items)} items, {len(per_user.get(u.id, []))} requested"
                  + (": " + ", ".join(i.title for i in items[:12]) + (" …" if len(items) > 12 else "") if a.dry_run else ""))
            if a.dry_run:
                continue
            col = p.upsert_collection(section, title, items, label)
            if col is not None:
                hub = col.visibility()
                if not (hub.promotedToSharedHome and hub.promotedToRecommended):
                    # friends' Home + the library's Recommended tab (what Shortlist sets); never promoteHome (owner Home stays clean)
                    hub = hub.updateVisibility(shared=True, recommended=True)
                print(f"{'':>18} | collection {col.ratingKey}: sort={col.collectionSort} labels={[l.tag for l in col.labels]} "
                      f"hub shared={hub.promotedToSharedHome} own={hub.promotedToOwnHome}")
        kinds.append(section.TYPE)
    # Filters are merged against values re-read NOW: the collection phase above takes a while and Shortlist/Agregarr write
    # the same strings — merging into a stale copy would drop what they added in between.
    users = _users(account)
    wanted, skipped = plan_filters(users, kinds)
    problems += skipped
    for line in skipped:
        print(line)
    written = {}
    for u in users:                                            # one plex.tv write per user, both filters at once
        fm, ft = wanted["movie"].get(u.id), wanted["show"].get(u.id)
        try:
            fields = shares.apply(account, SERVER_NAME, u, fm, ft, a.dry_run)
        except Exception as e:                                 # managed profiles with a parental preset are refused (422)
            problems.append(f"!! share filter not applied for {u.title}: {type(e).__name__}: {e}"); print(problems[-1])
            continue
        if fields:
            written[u.id] = fields
            for field, value in fields.items():
                print(f"{dry}{'share filter':>18} | {u.title:<16} | {field}: {value}")
    if written and not a.dry_run:
        time.sleep(shares.NUDGE_DELAY_S)                       # the PMS debounces sharing-change pushes (~6 s) and drops the rest:
        try:                                                   # one more push after a quiet gap makes it re-read every filter
            shares.nudge(account, next(u for u in users if u.id in written))   # a user whose write plex.tv accepted
        except Exception as e:
            problems.append(f"!! nudge failed: {type(e).__name__}: {e}"); print(problems[-1])
        after = {u.id: u for u in account.users()}             # read back: plex.tv stored exactly what we sent
        for uid, fields in written.items():
            for field, value in fields.items():
                got = getattr(after[uid], field)
                if got != value:
                    problems.append(f"!! read-back mismatch for {after[uid].title} {field}: {got!r}"); print(problems[-1])
    if problems:
        raise SystemExit(f"rows: {len(problems)} problem(s), see !! lines above")

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("requested", "rows", "cards", "order"):
        sp = sub.add_parser(name)
        sp.add_argument("--sections", required=True); sp.add_argument("--dry-run", action="store_true"); sp.add_argument("--env", default=".env")
    a = ap.parse_args(argv)
    cmds = {"requested": cmd_requested, "rows": cmd_rows, "cards": cmd_cards, "order": cmd_order}
    if a.cmd not in cmds:
        raise SystemExit(f"{a.cmd}: not implemented")
    cmds[a.cmd](a, load_env(a.env))

if __name__ == "__main__":
    main()
