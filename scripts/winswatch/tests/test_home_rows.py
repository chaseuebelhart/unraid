from types import SimpleNamespace as NS
import pytest
import home
from ww.plexlib import PlexLib

def _it(key, **kw):
    return NS(ratingKey=key, title=f"item {key}", type="movie", **kw)

BASE = "📥 New Movies · Your Requests"

def test_weave_every_4th_slot_from_index_1():
    r = [_it(i) for i in range(6)]
    q = [_it(100), _it(101)]
    assert [x.ratingKey for x in home.build_new_row(r, q)] == [0, 100, 1, 2, 3, 101, 4, 5]

def test_weave_leftovers_and_caps():
    r = [_it(i) for i in range(3)]
    q = [_it(100), _it(101), _it(102)]
    assert [x.ratingKey for x in home.build_new_row(r, q)] == [0, 100, 1, 2, 101, 102]   # slot 1, then slot 5 is past the end: appended
    assert [x.ratingKey for x in home.build_new_row(r, [])] == [0, 1, 2]
    assert [x.ratingKey for x in home.build_new_row([], q)] == [100, 101, 102]
    assert [x.ratingKey for x in home.build_new_row([_it(i) for i in range(50)], q, n_recent=4)] == [0, 100, 1, 2, 3, 101, 102]

def test_weave_dedupes_a_request_already_in_recent():
    r = [_it(i) for i in range(6)]
    q = [_it(3), _it(3)]                      # requested item is also the 4th newest; listed twice
    keys = [x.ratingKey for x in home.build_new_row(r, q)]
    assert keys == [0, 3, 1, 2, 4, 5]         # takes the request slot, gone from the recent run, no duplicate
    assert len(keys) == len(set(keys))

def test_user_slug_matches_shortlist():
    assert home.user_slug("Lily.Arnold") == "lily_arnold"
    assert home.user_slug("jordy.allen") == "jordy_allen"
    assert home.user_slug("Chase_Test") == "chase_test"
    assert home.user_slug("mike_nordby") == "mike_nordby"
    assert home.user_slug("da6490") == "da6490"
    assert home.user_slug("Mike Nordby!") == "mike_nordby"

@pytest.mark.parametrize("base", sorted(home.NEW_BASE.values()))
def test_row_title_zero_width_suffix(base):
    a, b = home.row_title(base, "lily_arnold"), home.row_title(base, "da6490")
    assert a.startswith(base) and b.startswith(base)
    assert a != b
    assert home.strip_zw(a) == home.strip_zw(b) == base
    assert set(a[len(base):]) <= {"​", "‌"} and len(a) - len(base) == home.MARKER_BITS
    assert home.row_title(base, "lily_arnold") == a                     # deterministic
    assert not all(c in "​‌" for c in a[-64:])                # never a Shortlist marker

def test_row_title_raises_when_the_title_would_read_as_a_shortlist_marker():
    """Enforced, not incidental: a base too short (or itself zero-width) to break up the last 64 characters would make
    Shortlist's sweep_broken_rows delete the collection. Both real bases are long enough; a naked suffix is not."""
    for bad in ("", "​" * 30):
        with pytest.raises(ValueError, match="Shortlist marker"):
            home.row_title(bad, 838573123)
    for good in home.NEW_BASE.values():
        home.row_title(good, 838573123)                                 # does not raise

def test_row_title_with_plex_id_uses_shortlist_alphabet_but_not_its_marker():
    """Same bit encoding as Shortlist (LSB first, U+200B = 0 / U+200C = 1; id 838573123 = Shortlist_mike_nordby on
    2026-09-21) but 40 chars, never 64: Shortlist's sweep_broken_rows deletes any label-less collection whose last 64
    chars are all zero-width (it deleted all 16 of our rows on 2026-09-21 when the suffix was byte-identical to its own)."""
    t = home.row_title(BASE, 838573123)
    bits = "".join("0" if ch == "​" else "1" for ch in t[len(BASE):])
    assert bits == "1100001000111001110111111000110000000000"
    assert home.row_title(BASE, 0) == BASE + "​" * 40
    assert home.MARKER_BITS != 64
    for title in (t, home.row_title(BASE, 0), home.row_title(BASE, "da6490")):
        suffix = title[-64:]
        assert not (len(suffix) == 64 and all(c in "​‌" for c in suffix)), "would read as a Shortlist marker"

def test_exclusion_plan_every_other_user():
    users = [NS(id=1, slug="a"), NS(id=2, slug="b"), NS(id=3, slug="c")]
    assert home.exclusions_for(users) == {1: {"Winswatch_b", "Winswatch_c"}, 2: {"Winswatch_a", "Winswatch_c"}, 3: {"Winswatch_a", "Winswatch_b"}}

# --- PlexLib.upsert_collection against a fake section ---------------------------------------------------------------

class FakeCollection:
    def __init__(self, section, title, items):
        self.section, self.title, self._items, self.labels, self.collectionSort, self.smart = section, title, list(items), [], 0, False
        self.ratingKey = 900 + len(section._collections); self.log = []
    def items(self): return list(self._items)
    def addItems(self, items): self._items += list(items); self.log.append(("add", [i.ratingKey for i in items]))
    def removeItems(self, items):
        keys = {i.ratingKey for i in items}; self._items = [i for i in self._items if i.ratingKey not in keys]; self.log.append(("remove", sorted(keys)))
    def moveItem(self, item, after=None):
        self._items.remove(item); idx = self._items.index(after) + 1 if after else 0; self._items.insert(idx, item)
        self.log.append(("move", item.ratingKey, after.ratingKey if after else None))
    def sortUpdate(self, sort): self.collectionSort = {"release": 0, "alpha": 1, "custom": 2}[sort]; self.log.append(("sort", sort))
    def addLabel(self, label): self.labels.append(NS(tag=label)); self.log.append(("label", label))
    def delete(self): self.section._collections.remove(self); self.log.append(("delete",))
    def reload(self): return self

class FakeSection:
    key = 4
    def __init__(self): self._collections = []
    def collections(self): return list(self._collections)

def _lib(create_log):
    lib = PlexLib.__new__(PlexLib)
    def create(title, section, items):
        c = FakeCollection(section, title, items); section._collections.append(c); create_log.append(title); return c
    lib._create_collection = create
    return lib

def test_upsert_creates_then_replaces_in_order():
    created, sec = [], FakeSection()
    a, b, c, d = (_it(k) for k in (1, 2, 3, 4))
    lib = _lib(created)
    col = lib.upsert_collection(sec, "T​", [a, b, c], "winswatch_x")
    assert created == ["T​"] and [i.ratingKey for i in col.items()] == [1, 2, 3]
    assert col.collectionSort == 2 and [l.tag for l in col.labels] == ["winswatch_x"]
    # second run: same items, same order -> no item churn
    col.log.clear()
    assert lib.upsert_collection(sec, "T​", [a, b, c], "winswatch_x") is col and col.log == []
    # new order + one new + one gone
    lib.upsert_collection(sec, "T​", [d, c, a], "winswatch_x")
    assert [i.ratingKey for i in col.items()] == [4, 3, 1] and created == ["T​"]
    assert ("remove", [2]) in col.log and ("add", [4]) in col.log

def test_upsert_matches_by_label_when_suffix_changed_and_deletes_when_empty():
    created, sec = [], FakeSection()
    lib = _lib(created)
    col = lib.upsert_collection(sec, "T​​", [_it(1)], "winswatch_x")
    col2 = lib.upsert_collection(sec, "T‌​", [_it(1), _it(2)], "winswatch_x")   # same base, new suffix: reuse
    assert col2 is col and created == ["T​​"]
    assert lib.upsert_collection(sec, "T‌​", [], "winswatch_x") is None and sec.collections() == []
    assert lib.upsert_collection(sec, "T‌​", [], "winswatch_x") is None      # nothing to delete either

def test_plan_filters_skips_a_filter_that_does_not_round_trip():
    users = [NS(id=1, slug="a", title="A", filterMovies="label!=Shortlist_b", filterTelevision=""),
             NS(id=2, slug="b", title="B", filterMovies="label!=", filterTelevision="contentRating!=R|label!=x"),   # 'label!=' has no values: unparse would drop it
             NS(id=3, slug="c", title="C", filterMovies=None, filterTelevision="label!=a,,b")]                         # empty value: not reproducible either
    wanted, problems = home.plan_filters(users, ["movie", "show"])
    assert wanted["movie"] == {1: "label!=Shortlist_b,Winswatch_b,Winswatch_c", 3: "label!=Winswatch_a,Winswatch_b"}
    assert wanted["show"] == {1: "label!=Winswatch_b,Winswatch_c", 2: "contentRating!=R|label!=x,Winswatch_a,Winswatch_c"}
    assert [p.split(" does not")[0] for p in problems] == ["!! filter for B (filterMovies)", "!! filter for C (filterTelevision)"]
    assert "skipping: 'label!='" in problems[0]
    assert home.plan_filters(users, ["movie"])[0]["show"] == {}          # a kind not processed leaves that filter alone

# --- _users: only accounts that share NASTower, and unique slugs -----------------------------------------------------

def _u(uid, username, servers=("NASTower",)):
    return NS(id=uid, username=username, title=username, servers=[NS(name=n) for n in servers],
              filterMovies="", filterTelevision="")

def test_users_drops_accounts_that_do_not_share_the_server(capsys):
    """ww.shares.apply raises LookupError for an account that does not share NASTower, which would make the nightly
    exit non-zero for good the first time Chase accepts a plex.tv friend who shares nothing."""
    from ww import shares
    stranger = _u(2, "some_friend", servers=("SomeoneElsesPlex",))
    account = NS(users=lambda: [_u(1, "lily.arnold"), stranger, _u(3, "no_share", servers=())])
    users = home._users(account)
    assert [u.id for u in users] == [1] and users[0].slug == "lily_arnold"
    out = capsys.readouterr().out
    assert "skipping some_friend (2): no share of server 'NASTower'" in out and "no_share (3)" in out
    with pytest.raises(LookupError):                       # why they are dropped
        shares.apply(NS(), home.SERVER_NAME, stranger, "label!=Winswatch_x", None, dry_run=False)

def test_users_suffixes_colliding_slugs_so_rows_do_not_cross_wire(capsys):
    """`Mike Nordby!` and `mike_nordby` both slugify to mike_nordby: one label for two accounts would hide each of
    their rows from the other (and from themselves)."""
    account = NS(users=lambda: [_u(11, "Mike Nordby!"), _u(22, "mike_nordby"), _u(33, "lily.arnold")])
    users = home._users(account)
    assert [u.slug for u in users] == ["mike_nordby_11", "mike_nordby_22", "lily_arnold"]
    assert len({u.slug for u in users}) == 3
    excl = home.exclusions_for(users)
    assert excl[11] == {"Winswatch_mike_nordby_22", "Winswatch_lily_arnold"}
    assert excl[22] == {"Winswatch_mike_nordby_11", "Winswatch_lily_arnold"}
    assert excl[11] != excl[22] and "Winswatch_mike_nordby_11" not in excl[11]     # nobody excludes their own row
    assert "slug collision on 'mike_nordby'" in capsys.readouterr().out

# --- cmd_rows: an empty search must not delete the rows --------------------------------------------------------------

def test_cmd_rows_leaves_a_section_alone_when_the_recent_search_comes_back_empty(monkeypatch, capsys):
    """upsert_collection deletes a collection it is handed no items for, so one empty search would wipe all 16 per-user
    rows (Plex hiccup, section re-scanning). The section is reported with a !! line and skipped instead."""
    import plexapi.myplex
    empty = NS(TYPE="movie", title="Movies", key=1, search=lambda **kw: [], all=lambda: [], collections=lambda: [])
    item = _it(7, guids=[])
    full = NS(TYPE="show", title="TV Shows", key=2, search=lambda **kw: [item], all=lambda: [item], collections=lambda: [])
    upserts = []
    class FakePlexLib:
        def __init__(self, url, token): pass
        def section(self, sec_id): return {1: empty, 2: full}[sec_id]
        def tmdb_id(self, it): return None
        def upsert_collection(self, section, title, items, label):
            upserts.append((section.title, home.strip_zw(title), label, [i.ratingKey for i in items])); return None
    users = [_u(1, "lily.arnold")]
    monkeypatch.setattr(home, "PlexLib", FakePlexLib)
    monkeypatch.setattr(plexapi.myplex, "MyPlexAccount", lambda token=None: NS(users=lambda: users))
    monkeypatch.setattr(home.overseerr, "Client", lambda url, key: NS(requests=lambda since_days: []))
    for k, v in {"PLEX_URL": "http://fake", "PLEX_TOKEN": "tok", "OVERSEERR_URL": "http://fake", "OVERSEERR_API_KEY": "k"}.items():
        monkeypatch.setenv(k, v)
    with pytest.raises(SystemExit) as e:
        home.main(["rows", "--sections", "1,2", "--env", "/nonexistent.env"])
    assert "1 problem(s)" in str(e.value)
    out = capsys.readouterr().out
    assert "!! Movies: recent search returned nothing, leaving this section's rows untouched" in out
    assert upserts == [("TV Shows", home.NEW_BASE["show"], "Winswatch_lily_arnold", [7])]   # only the healthy section
