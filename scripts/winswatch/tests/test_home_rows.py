from types import SimpleNamespace as NS
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

def test_row_title_zero_width_suffix():
    a, b = home.row_title(BASE, "lily_arnold"), home.row_title(BASE, "da6490")
    assert a.startswith(BASE) and b.startswith(BASE)
    assert a != b
    assert home.strip_zw(a) == home.strip_zw(b) == BASE
    assert set(a[len(BASE):]) <= {"​", "‌"} and len(a) - len(BASE) == 64
    assert home.row_title(BASE, "lily_arnold") == a                     # deterministic

def test_row_title_with_plex_id_is_shortlist_identical():
    """Shortlist's suffix = 64 bits of the Plex account id, LSB first, U+200B = 0 / U+200C = 1 (read from
    '✨ Movies Recommended For You' 13527 / labels Shortlist_mike_nordby, id 838573123, on 2026-09-21)."""
    t = home.row_title(BASE, 838573123)
    bits = "".join("0" if ch == "​" else "1" for ch in t[len(BASE):])
    assert bits == "1100001000111001110111111000110000000000000000000000000000000000"
    assert home.row_title(BASE, 0) == BASE + "​" * 64

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
