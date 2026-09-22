from types import SimpleNamespace as NS
import pytest
from ww import shares

# Grammar as plex.tv returns it in MyPlexUser.filterMovies (read 2026-09-21): conditions `key=v1,v2` joined by '|' or '&',
# stored verbatim. Every account here has one `label!=Shortlist_a,Shortlist_b,...` condition.

def test_merge_appends_to_existing_label_clause():
    assert shares.merge_exclusions("label!=shortlist_a,shortlist_b", {"winswatch_c"}) == "label!=shortlist_a,shortlist_b,winswatch_c"

def test_merge_is_idempotent_case_insensitive_and_sorted_for_new_values():
    cur = "label!=shortlist_a,shortlist_b,Winswatch_c"
    assert shares.merge_exclusions(cur, {"Winswatch_c"}) == cur
    assert shares.merge_exclusions(cur, {"winswatch_c"}) == cur                       # Plex tags compare case-insensitively
    assert shares.merge_exclusions(cur, {"Winswatch_z", "Winswatch_d"}) == cur + ",Winswatch_d,Winswatch_z"

def test_merge_keeps_content_rating_clauses_and_their_separators():
    cur = "contentRating!=NC-17,R|label!=shortlist_a"
    assert shares.merge_exclusions(cur, {"winswatch_c"}) == "contentRating!=NC-17,R|label!=shortlist_a,winswatch_c"
    assert shares.merge_exclusions("contentRating!=R", {"winswatch_c"}) == "contentRating!=R&label!=winswatch_c"   # new condition: AND
    assert shares.merge_exclusions("contentRating!=R&label!=a", {"b"}) == "contentRating!=R&label!=a,b"
    assert shares.merge_exclusions("label!=Age%200%2CAge%201", {"b"}) == "label!=Age%200%2CAge%201%2Cb"           # Plex Web encoding kept

def test_merge_empty_current():
    assert shares.merge_exclusions("", {"winswatch_c"}) == "label!=winswatch_c"
    assert shares.merge_exclusions(None, {"winswatch_c"}) == "label!=winswatch_c"
    assert shares.merge_exclusions("", set()) == ""

def test_remove_is_the_inverse():
    cur = "contentRating!=R&label!=shortlist_a,winswatch_c,shortlist_b,winswatch_d"
    assert shares.remove_exclusions(cur, {"winswatch_c", "Winswatch_d"}) == "contentRating!=R&label!=shortlist_a,shortlist_b"
    assert shares.remove_exclusions("label!=winswatch_c", {"winswatch_c"}) == ""                        # last value: condition goes away
    assert shares.remove_exclusions("label!=winswatch_c&contentRating!=R", {"winswatch_c"}) == "contentRating!=R"
    assert shares.remove_exclusions("label!=shortlist_a", {"winswatch_c"}) == "label!=shortlist_a"      # absent: unchanged
    merged = shares.merge_exclusions("label!=shortlist_a", {"winswatch_c"})
    assert shares.remove_exclusions(merged, {"winswatch_c"}) == "label!=shortlist_a"
    assert shares.remove_exclusions("contentRating!=R", {"winswatch_c"}) == "contentRating!=R"

def test_parse_unparse_round_trips_every_dialect():
    for s in ("label!=a,b", "contentRating!=NC-17,R|label!=a", "contentRating!=R&label!=Age%200%2CAge%201", "", "label=Kids|label!=x"):
        assert shares.unparse(shares.parse(s)) == s
    assert shares.has_exclusions("label!=Shortlist_a,Winswatch_b", {"winswatch_b"})
    assert not shares.has_exclusions("label!=Shortlist_a", {"winswatch_b"})

class _Resp:
    def __init__(self, code, text=""): self.status_code, self.text = code, text

class _Account:
    _token = "tok"
    def __init__(self, codes=(200,)):
        self.calls, self._codes = [], list(codes)
        self._session = self
    def put(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, dict(params), headers["X-Plex-Token"])); return _Resp(self._codes.pop(0))

def _user():
    return NS(title="lily", id=629089349, filterMovies="label!=a", filterTelevision="",
              servers=[NS(name="Other", machineIdentifier="x"), NS(name="NASTower", machineIdentifier="mid")])

def test_apply_puts_api_users_once_with_changed_fields_only():
    acc = _Account()
    written = shares.apply(acc, "NASTower", _user(), "label!=a,Winswatch_b", "label!=Winswatch_b", dry_run=False)
    assert written == {"filterMovies": "label!=a,Winswatch_b", "filterTelevision": "label!=Winswatch_b"}
    assert acc.calls == [("https://plex.tv/api/users/629089349", written, "tok")]
    acc = _Account()
    assert shares.apply(acc, "NASTower", _user(), "label!=a", "", dry_run=False) == {} and acc.calls == []        # nothing changes
    assert shares.apply(acc, "NASTower", _user(), "label!=a,b", "", dry_run=True) == {"filterMovies": "label!=a,b"} and acc.calls == []
    assert shares.apply(acc, "NASTower", _user(), None, "label!=b", dry_run=False) == {"filterTelevision": "label!=b"}   # None = leave alone
    assert acc.calls[-1][1] == {"filterTelevision": "label!=b"}

def test_apply_retries_429_and_raises_on_refusal(monkeypatch):
    monkeypatch.setattr(shares.time, "sleep", lambda s: None)
    acc = _Account(codes=(429, 200))
    assert shares.apply(acc, "NASTower", _user(), "label!=a,b", None, dry_run=False) == {"filterMovies": "label!=a,b"} and len(acc.calls) == 2
    with pytest.raises(RuntimeError, match="422"):
        shares.apply(_Account(codes=(422,)), "NASTower", _user(), "label!=a,b", None, dry_run=False)
    with pytest.raises(LookupError):
        shares.apply(_Account(), "Elsewhere", _user(), "label!=a,b", None, dry_run=False)

def test_nudge_reputs_the_fresh_filter_not_the_stale_object():
    acc = _Account()
    stale = _user(); stale.filterTelevision = "label!=old"
    fresh = _user(); fresh.filterTelevision = "label!=new"
    acc.users = lambda: [NS(id=1, filterTelevision="x"), fresh]
    shares.nudge(acc, stale)
    assert acc.calls == [("https://plex.tv/api/users/629089349", {"filterTelevision": "label!=new"}, "tok")]

def test_nudge_raises_on_non_2xx():
    acc = _Account(codes=(404,))
    acc.users = lambda: [_user()]
    with pytest.raises(RuntimeError, match="404"):
        shares.nudge(acc, _user())

def test_unparse_drops_valueless_conditions_which_is_why_cmd_rows_guards():
    assert shares.unparse(shares.parse("label!=")) == ""
    assert shares.unparse(shares.parse("label!=a,,b")) == "label!=a,b"
    assert shares.unparse(shares.parse("contentRating!=R|label!=a")) == "contentRating!=R|label!=a"
