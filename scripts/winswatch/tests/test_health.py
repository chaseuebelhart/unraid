"""Thresholds of the nightly's post-condition health check (ww/health.py) + the CLI's exit code.

All fakes, no network: every check function takes the numbers `home.collect` read, so the bands can be pinned exactly."""
from datetime import date
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
import airdates, gen_home, home
from ww import health, plexhome

CAL = gen_home.load_calendar(Path(__file__).resolve().parents[1] / "home_calendar.yml")
DAY = date(2027, 3, 22)                      # week A Monday, no seasonal window open
DESIRED = plexhome.desired_order("movies", DAY, CAL)   # ✨ 🔥 📥 👥 ⏳ + 💥 Adrenaline Rush + 💎 Hidden Gems + 🎯


def mcol(title, type_, n):
    return {"id": 1, "title": title, "type": type_, "library_id": "1", "media_count": n, "active": True}


# --- the label prefixes must not drift from the producers ------------------------------------------------------------

def test_prefixes_match_the_producers():
    assert health.AIRDATE_PREFIXES == airdates.PREFIXES
    assert health._FIXED == plexhome.FIXED_TOP
    assert health.REQUESTED_LABEL == home.LABEL


# --- 1. DaysLeft labels vs Maintainerr --------------------------------------------------------------------------------

def test_days_left_fails_when_the_collection_has_members_and_nothing_is_labelled():
    r = health.check_days_left("Movies", 0, [mcol("⏳ Movies Leaving Wins Watch", "movie", 7)], "movie")
    assert r.status == health.FAIL and (r.got, r.expected) == (0, 7)

def test_days_left_fails_when_no_collection_of_that_type_exists():
    r = health.check_days_left("Shows", 4, [], "show")
    assert r.status == health.FAIL and "show" in r.detail

def test_days_left_warns_past_the_churn_tolerance_but_passes_inside_it():
    col = [mcol("⏳ Movies Leaving Wins Watch", "movie", 10)]
    assert health.check_days_left("Movies", 10, col, "movie").status == health.PASS
    assert health.check_days_left("Movies", 8, col, "movie").status == health.PASS    # off by 2 == tolerance
    assert health.check_days_left("Movies", 12, col, "movie").status == health.PASS
    assert health.check_days_left("Movies", 7, col, "movie").status == health.WARN    # off by 3
    assert health.check_days_left("Movies", 14, col, "movie").status == health.WARN

def test_days_left_passes_on_an_empty_collection_with_no_labels():
    assert health.check_days_left("Shows", 0, [mcol("⏳ Shows Leaving Wins Watch", "show", 0)], "show").status == health.PASS

def test_days_left_sums_several_collections_of_the_same_type():
    cols = [mcol("⏳ Movies Leaving Wins Watch", "movie", 7), mcol("⏳ 4K Leaving", "movie", 3)]
    assert health.check_days_left("Movies", 10, cols, "movie").expected == 10


# --- 2. air-date labels vs Sonarr ------------------------------------------------------------------------------------

def test_airdates_fails_at_zero_only_above_the_floor():
    assert health.check_airdates("Shows", 0, 11).status == health.FAIL
    assert health.check_airdates("Shows", 0, 10).status == health.WARN     # at the floor it is only a warning
    assert health.check_airdates("Shows", 0, 0).status == health.PASS      # nothing continuing, nothing to label

def test_airdates_warns_below_half_and_passes_above():
    assert health.check_airdates("Shows", 19, 40).status == health.WARN
    assert health.check_airdates("Shows", 20, 40).status == health.PASS    # exactly half is fine
    assert health.check_airdates("Shows", 44, 40).status == health.PASS    # unmonitored continuing shows get labels too


# --- 3. score coverage -----------------------------------------------------------------------------------------------

def test_score_coverage_bands():
    assert health.check_scores("Movies", 49, 100).status == health.FAIL
    assert health.check_scores("Movies", 50, 100).status == health.WARN
    assert health.check_scores("Movies", 89, 100).status == health.WARN
    assert health.check_scores("Movies", 90, 100).status == health.PASS
    assert health.check_scores("Movies", 0, 0).status == health.PASS       # empty library: no division by zero
    assert "90.0% rated" in health.check_scores("Movies", 90, 100).detail


# --- 4. REQUESTED labels ---------------------------------------------------------------------------------------------

def test_requested_warns_at_zero_and_never_fails():
    assert health.check_requested("Movies", 0).status == health.WARN
    assert health.check_requested("Movies", 1).status == health.PASS


# --- 5. Home rows ----------------------------------------------------------------------------------------------------

def full_rows():
    return ["✨ Movies for you", "🔥 Trending Movies", "📥 New Movies · Your Requests", "👥 Popular Movies on Wins Watch",
            "⏳ Movies Leaving Wins Watch", "💥 Adrenaline Rush", "💎 Hidden Gems", "🎯 Because you watched Heat"]

def test_home_rows_pass_in_order():
    r = health.check_home_rows("Movies", full_rows(), DESIRED)
    assert r.status == health.PASS and (r.got, r.expected) == (8, 8)

def test_home_rows_fail_on_a_missing_fixed_row():
    rows = [t for t in full_rows() if not t.startswith("⏳ ")]
    r = health.check_home_rows("Movies", rows, DESIRED)
    assert r.status == health.FAIL and "⏳ " in r.detail

def test_home_rows_fail_on_fewer_than_two_shelves():
    rows = [t for t in full_rows() if t != "💎 Hidden Gems"]
    r = health.check_home_rows("Movies", rows, DESIRED)
    assert r.status == health.FAIL and "1 of 2 theme/seasonal shelves" in r.detail

def test_home_rows_warn_on_order_mismatch_only():
    rows = full_rows()
    rows[1], rows[3] = rows[3], rows[1]
    assert health.check_home_rows("Movies", rows, DESIRED).status == health.WARN

def test_home_rows_tolerate_duplicate_per_user_rows_and_unmatched_hubs():
    rows = full_rows()[:5] + ["📥 New Movies · Your Requests​", "💥 Adrenaline Rush", "💎 Hidden Gems"]
    # the second 📥 row sits after ⏳ -> out of order; without it the set is complete and in order
    assert health.check_home_rows("Movies", rows, DESIRED).status == health.WARN
    assert health.check_home_rows("Movies", full_rows() + ["IMDb Popular"], DESIRED).status == health.PASS

def test_home_rows_missing_bottom_row_is_not_a_failure():
    rows = [t for t in full_rows() if not t.startswith("🎯")]
    assert health.check_home_rows("Movies", rows, DESIRED).status == health.PASS


# --- 6. per-user rows ------------------------------------------------------------------------------------------------

def test_user_rows_fail_when_one_is_missing():
    assert health.check_user_rows("Movies", 6, 7).status == health.FAIL
    assert health.check_user_rows("Movies", 7, 7).status == health.PASS
    assert health.check_user_rows("Movies", 8, 7).status == health.WARN


# --- 7. cards --------------------------------------------------------------------------------------------------------

def test_cards_warn_on_a_missing_or_stale_upload():
    matched = [("101", "⏳ Movies Leaving Wins Watch", "leaving-movies"), ("102", "👥 Popular Movies on Wins Watch", "popular-movies")]
    assert health.check_cards("Movies", matched, {"101": "leaving-movies", "102": "popular-movies"}).status == health.PASS
    stale = health.check_cards("Movies", matched, {"101": "leaving-movies", "102": "new-movies"})
    assert stale.status == health.WARN and (stale.got, stale.expected) == (1, 2)
    assert health.check_cards("Movies", matched, {}).status == health.WARN
    assert health.check_cards("Movies", [], {}).status == health.PASS


# --- render / exit code ----------------------------------------------------------------------------------------------

def test_render_is_delimited_and_counts_every_status():
    results = [health.check_scores("Movies", 100, 100), health.check_requested("Movies", 0),
               health.check_airdates("Shows", 0, 40)]
    out = health.render(results)
    assert out[0] == health.HEADER and out[-1] == health.FOOTER
    assert out[-2] == "---- 3 checks: 1 PASS, 1 WARN, 1 FAIL"
    assert health.worst(results) == health.FAIL
    assert health.worst([health.check_requested("Movies", 5)]) == health.PASS


def _run_check(monkeypatch, tmp_path, results):
    env_file = tmp_path / ".env"
    env_file.write_text("PLEX_URL=http://example\nPLEX_TOKEN=tok\n")
    monkeypatch.setattr(home, "collect", lambda env, secs, day, **kw: results)
    home.main(["check", "--sections", "1,2", "--env", str(env_file)])

def test_cli_exits_non_zero_when_a_check_fails(monkeypatch, tmp_path, capsys):
    results = [health.check_scores("Movies", 10, 100), health.check_requested("Movies", 0)]
    with pytest.raises(SystemExit) as e:
        _run_check(monkeypatch, tmp_path, results)
    assert e.value.code != 0 and "score coverage/Movies" in str(e.value.code)
    assert health.HEADER in capsys.readouterr().out

def test_cli_exits_zero_when_everything_passes_or_warns(monkeypatch, tmp_path, capsys):
    results = [health.check_scores("Movies", 95, 100), health.check_requested("Movies", 0)]   # one PASS, one WARN
    _run_check(monkeypatch, tmp_path, results)                                                # no SystemExit
    out = capsys.readouterr().out
    assert "1 PASS, 1 WARN, 0 FAIL" in out


# --- collect() wiring (fake Plex / Maintainerr / Sonarr) --------------------------------------------------------------

class FakeSection:
    TYPE = "show"
    type = "show"
    title = "TV Shows"
    def __init__(self, items, cols, hubs): self._i, self._c, self._h = items, cols, hubs
    def all(self): return self._i
    def collections(self): return self._c
    def managedHubs(self): return self._h

def test_collect_wires_every_check_for_a_show_section(monkeypatch, tmp_path):
    item = NS(ratingKey=1, title="Reacher", userRating=8.1,
              labels=[NS(tag="DaysLeft_12"), NS(tag="NewEp_Wed"), NS(tag="Requested")])
    col = NS(ratingKey=77, title="⏳ Shows Leaving Wins Watch", labels=[])
    hubs = [NS(title=t, identifier=t, promotedToSharedHome=True, promotedToOwnHome=False) for t in
            ["✨ Shows for you", "🔥 Trending Shows", "📥 New Shows · Your Requests", "👥 Popular Shows on Wins Watch",
             "⏳ Shows Leaving Wins Watch", "🪐 Worlds Beyond", "🛋️ Comfort Binge"]]
    section = FakeSection([item], [col], hubs)
    p = NS(section=lambda sid: section, tvdb_id=lambda it: "366924")
    monkeypatch.setattr(home.maintainerr, "collections", lambda url: [mcol("⏳ Shows Leaving Wins Watch", "show", 1)])
    monkeypatch.setattr(home.sonarr, "series_index",
                        lambda url, key: {"366924": {"status": "continuing", "next_air": None, "monitored": True}})
    env = {"SONARR_URL": "http://s", "SONARR_API_KEY": "k", "CACHE_DIR": str(tmp_path)}
    results = home.collect(env, [2], DAY, p=p, account=NS(users=lambda: []))
    assert [r.check for r in results] == ["days-left labels", "air-date labels", "score coverage", "requested labels",
                                          "home rows", "per-user rows", "cards"]
    by = {r.check: r for r in results}
    assert by["days-left labels"].status == health.PASS and (by["days-left labels"].got, by["days-left labels"].expected) == (1, 1)
    assert by["air-date labels"].status == health.PASS
    assert by["score coverage"].status == health.PASS
    assert by["requested labels"].status == health.PASS
    assert by["home rows"].status == health.PASS
    assert by["per-user rows"].status == health.PASS       # no users, no 📥 collections
    assert by["cards"].status == health.WARN               # the ⏳ collection has no uploaded card in the cache
