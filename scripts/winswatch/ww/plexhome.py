"""Plex Home hub order + demotion (design §1 / §6): decide today's eight rows, sort the section's managed hubs to match,
demote everything else that is promoted. Planning is pure; `apply` is the only part that talks to Plex.

Kometa can't order hubs and its weekly() has no fortnight, so on any weekday up to four themes qualify for promotion;
`plan` narrows a day to this week's pair (week A/B parity from EPOCH) and hands the rest to `to_demote`."""
import re
from datetime import date
import gen_home

EPOCH = date(2026, 9, 21)                      # week A Monday
FIXED_TOP = ["✨ ", "🔥 Trending ", "📥 New ", "👥 Popular ", "⏳ "]   # rows 1-5, matched by emoji + first word only
FIXED_BOTTOM = ["🎯 Because you watched"]                              # row 8
LIB_BY_TYPE = {"movie": "movies", "show": "shows"}
_DAYS = {d: i for i, d in enumerate(gen_home.DAYS)}

def week(today: date) -> str:
    return "A" if ((today - EPOCH).days // 7) % 2 == 0 else "B"

def todays_pair(lib: str, today: date, calendar) -> list[str]:
    return list(calendar[lib][(0 if week(today) == "A" else 7) + today.weekday()])

def in_schedule(sched: str, today: date) -> bool:
    """Kometa schedule subset used by EXTRA_SCHEDULE: weekly(day|day) and range(mm/dd-mm/dd) (range may wrap the year)."""
    if m := re.fullmatch(r"weekly\(([a-z|]+)\)", sched):
        return today.weekday() in {_DAYS[d] for d in m.group(1).split("|")}
    if m := re.fullmatch(r"range\((\d\d)/(\d\d)-(\d\d)/(\d\d)\)", sched):
        m1, d1, m2, d2 = map(int, m.groups())
        start, end, now = (m1, d1), (m2, d2), (today.month, today.day)
        return start <= now <= end if start <= end else (now >= start or now <= end)
    raise ValueError(f"unsupported schedule: {sched}")

def _range_len(sched: str) -> int:
    m1, d1, m2, d2 = map(int, re.findall(r"\d\d", sched))
    return ((m2 - m1) % 12) * 31 + (d2 - d1)

def lib_for(section) -> str:
    return LIB_BY_TYPE[section.type]

def desired_order(lib: str, today: date, calendar, themes=None, extras=None, schedule=None) -> list[str]:
    """The eight row-title prefixes for `lib` on `today`, top to bottom. Shelf 1 is the seasonal row while one is in its
    window (the narrowest window wins when two overlap, e.g. Valentine's inside Awards Season), shelf 2 the weekend row
    on Fri-Sun; both are movies-only (EXTRAS carry lib). Displaced pair themes fall out of the list and get demoted."""
    themes, extras, schedule = themes or gen_home.THEMES, extras or gen_home.EXTRAS, schedule or gen_home.EXTRA_SCHEDULE
    label = lambda name, src: f"{src[name]['emoji']} {name}"
    shelf1, shelf2 = (label(n, themes) for n in todays_pair(lib, today, calendar))
    live = [n for n, t in extras.items() if t["lib"] == lib and in_schedule(schedule[n], today)]
    seasonal = sorted((n for n in live if schedule[n].startswith("range")), key=lambda n: _range_len(schedule[n]))
    weekend = [n for n in live if schedule[n].startswith("weekly")]
    if seasonal: shelf1 = label(seasonal[0], extras)
    if weekend: shelf2 = label(weekend[0], extras)
    return FIXED_TOP + [shelf1, shelf2] + FIXED_BOTTOM

def resolve_titles(hubs, titles: dict) -> None:
    """The manage list reports each collection hub's title as it was when the hub was promoted; a collection renamed
    since (our ⏳ rows, Shortlist rows renamed in its settings) keeps the stale title there. `titles` = {ratingKey (str):
    current collection title}; a hub whose identifier is custom.collection.<section>.<ratingKey> gets the current title."""
    for h in hubs:
        m = re.fullmatch(r"custom\.collection\.\d+\.(\d+)", getattr(h, "identifier", "") or "")
        if m and m.group(1) in titles:
            h.title = titles[m.group(1)]

def _promoted(hub) -> bool:
    return bool(getattr(hub, "promotedToSharedHome", False) or getattr(hub, "promotedToOwnHome", False))

def plan(hubs, desired: list[str]):
    """(ordered, to_demote). A hub belongs to the first prefix its title starts with; hubs sharing a prefix (per-user
    ✨/📥/🎯 rows) keep their current relative order. Matched hubs are ordered whether or not they are promoted yet
    (moving an unpromoted hub is harmless and pre-positions it for its owner's promote). Promoted hubs that match
    nothing — stock charts, Plex's own Recently Added, themes outside this week's pair — are demoted."""
    slots = {i: [] for i in range(len(desired))}
    to_demote = []
    for h in hubs:
        i = next((i for i, p in enumerate(desired) if h.title.startswith(p)), None)
        if i is not None: slots[i].append(h)
        elif _promoted(h): to_demote.append(h)
    return [h for i in range(len(desired)) for h in slots[i]], to_demote

def _short(title: str) -> str:
    return title.strip("​‌")[:44]

def apply(section, ordered, to_demote, dry_run: bool = False, current=None) -> None:
    """Promote every matched hub that is not promoted yet, walk `ordered` with ManagedHub.move(after=prev) (first hub goes
    to the top), then drop `to_demote` from both the shared and the owner Home in one visibility update
    (== demoteShared() + demoteHome(), one PUT instead of two).

    Promoting is what makes `order` self-healing: a row matched to one of today's slots but left unpromoted (Kometa's 05:00
    run failed, or the hourly pass crossed midnight in Chicago and demoted today's pair before tomorrow's was promoted)
    goes back on the shared Home by itself instead of waiting for the next Kometa run. Only `shared` is set — the owner's
    Home stays clean (§3), which is also why the flag is never turned on here for `promotedToOwnHome`.

    `current` = the section's managed hubs in their present order; when the matched hubs already sit in `ordered`'s
    relative order and nothing had to be promoted, the move walk is skipped entirely (the hourly pass is then a no-op)."""
    tag, name = ("DRY " if dry_run else ""), section.title
    promote = [h for h in ordered if not _promoted(h)]
    for h in promote:
        print(f"{tag}{name:>18} | promote {_short(h.title):<44} | shared=0 -> 1")
        if not dry_run: h.updateVisibility(shared=True)
    keys = {id(h) for h in ordered}
    if not promote and current is not None and [h for h in current if id(h) in keys] == list(ordered):
        print(f"{tag}{name:>18} | already in order ({len(ordered)} hubs)")
        for i, h in enumerate(ordered, 1):                 # no writes, but the log still shows the row set it left in place
            print(f"{tag}{name:>18} | keep {i:>2} {_short(h.title)}")
    else:
        prev = None
        for h in ordered:
            print(f"{tag}{name:>18} | move   {_short(h.title):<44} | after {_short(prev.title) if prev else '(top)'}")
            if not dry_run: h.move(after=prev)
            prev = h
    for h in to_demote:
        print(f"{tag}{name:>18} | demote {_short(h.title):<44} | shared={int(h.promotedToSharedHome)} home={int(h.promotedToOwnHome)}")
        if not dry_run: h.updateVisibility(home=False, shared=False)
