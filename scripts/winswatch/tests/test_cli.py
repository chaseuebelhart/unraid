from datetime import date
from types import SimpleNamespace as NS
import scores, airdates

def test_scores_plan():
    items = [NS(title="Dune"), NS(title="Nimrods"), NS(title="Unmatched")]
    ids = {"Dune": "1", "Nimrods": "2", "Unmatched": None}
    data = {"1": {"score": 86, "votes": 3645831}, "2": {"score": 71, "votes": 19613}}
    plan = scores.plan(items, lambda kind, tid: data[tid], lambda it: ids[it.title], "movie")
    assert plan[0] == (items[0], 8.6, "Votes_3.5M")
    assert plan[1] == (items[1], 7.1, "Votes_20K")
    assert plan[2] == (items[2], None, None)

def test_airdates_plan():
    items = [NS(title="Reacher"), NS(title="Bear"), NS(title="NoTvdb")]
    tv = {"Reacher": "366924", "Bear": "396112", "NoTvdb": None}
    idx = {"366924": {"status": "continuing", "next_air": date(2026, 9, 23)}, "396112": {"status": "ended", "next_air": None}}
    plan = airdates.plan(items, idx, lambda it: tv[it.title], date(2026, 9, 18))
    assert plan == [(items[0], "NewEp_Wed"), (items[1], None), (items[2], None)]
