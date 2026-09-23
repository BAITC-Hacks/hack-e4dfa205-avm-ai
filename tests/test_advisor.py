# tests/test_advisor.py
import pytest
from engine.model import load_city
from engine.scoring import evaluate, scenario_key
from engine.advisor import find_improvements
from engine.validator import validate

CITY = load_city()
EXAMPLE = [dict(d) for d in CITY.example_scenario]


def test_candidates_valid_better_and_decomposed_from_user_set():
    base = evaluate(CITY, EXAMPLE)
    cands = find_improvements(CITY, EXAMPLE)
    assert 0 < len(cands) <= 3
    keys = set()
    for n, c in enumerate(cands, 1):
        assert c["id"] == f"c{n}"
        assert validate(CITY, c["decisions"]) == []
        checked = evaluate(CITY, c["decisions"])
        assert c["score"] == checked["score"]
        assert c["score"] > base["score"] + 1e-8
        assert c["delta"] == pytest.approx(checked["score"] - base["score"], abs=1e-9)
        d = c["decomposition"]
        assert d["avg"] + d["min"] + d["crit"] == pytest.approx(c["delta"], abs=1e-9)
        assert c["scenario_key"] == scenario_key(c["decisions"])
        keys.add(c["scenario_key"])
    assert len(keys) == len(cands)
    assert [c["score"] for c in cands] == sorted((c["score"] for c in cands), reverse=True)


def test_candidate_is_single_replacement():
    c = find_improvements(CITY, EXAMPLE)[0]
    orig = set(scenario_key(EXAMPLE).split("|"))
    new = set(c["scenario_key"].split("|"))
    assert len(orig - new) == 1 and len(new - orig) == 1
    assert c["replace"]["measure_id"] in {d["measure_id"] for d in EXAMPLE}


def test_deterministic_on_permutation():
    a = find_improvements(CITY, EXAMPLE)
    b = find_improvements(CITY, list(reversed(EXAMPLE)))
    assert [c["scenario_key"] for c in a] == [c["scenario_key"] for c in b]


def test_invalid_input_returns_empty():
    assert find_improvements(CITY, EXAMPLE[:4]) == []
