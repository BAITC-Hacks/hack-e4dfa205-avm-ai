# tests/test_scoring.py
import copy
import pytest
from engine.model import load_city
from engine.scoring import evaluate, baseline, scenario_key, apply_effects, count_critical, aggregate

CITY = load_city()
EXAMPLE = [dict(d) for d in CITY.example_scenario]
TOL = 1e-6


def test_baseline_numbers():
    b = baseline(CITY)
    assert b["average"] == pytest.approx(56.8624, abs=TOL)
    assert b["minimum"] == pytest.approx(49.18, abs=TOL)
    assert b["critical_count"] == 2
    assert b["score"] == pytest.approx(52.55768, abs=TOL)
    per = {d["id"]: d["score_after"] for d in b["district_results"]}
    assert per["esil"] == pytest.approx(62.99, abs=TOL)
    assert per["almaty"] == pytest.approx(57.06, abs=TOL)
    assert per["saryarka"] == pytest.approx(54.65, abs=TOL)
    assert per["baikonur"] == pytest.approx(56.63, abs=TOL)
    assert per["nura"] == pytest.approx(49.18, abs=TOL)
    assert b["critical_pairs"] == [{"district_id": "nura", "indicator": "S1", "value": 38},
                                   {"district_id": "nura", "indicator": "S2", "value": 35}]


def test_example_numbers():
    r = evaluate(CITY, EXAMPLE)
    assert r["valid"] is True
    assert r["cost"] == 95 and r["remaining_budget"] == 5
    assert r["average"] == pytest.approx(58.0776, abs=TOL)
    assert r["minimum"] == pytest.approx(52.9625, abs=TOL)
    assert r["critical_count"] == 0 and r["critical_pairs"] == []
    assert r["score"] == pytest.approx(56.54307, abs=TOL)
    assert r["baseline_score"] == pytest.approx(52.55768, abs=TOL)
    assert r["delta"] == pytest.approx(3.98539, abs=TOL)
    d = r["decomposition"]
    assert d["avg"] == pytest.approx(0.85064, abs=TOL)
    assert d["min"] == pytest.approx(1.13475, abs=TOL)
    assert d["crit"] == pytest.approx(2.0, abs=TOL)
    assert d["avg"] + d["min"] + d["crit"] == pytest.approx(r["delta"], abs=TOL)
    assert r["active_synergies"] == ["M10+M12"]
    assert r["synergy_effects"] == [{"pair": "M10+M12", "district_id": "nura", "indicator": "B1", "bonus": 2}]


def test_permutation_same_result_and_key():
    a = evaluate(CITY, EXAMPLE)
    b = evaluate(CITY, list(reversed(EXAMPLE)))
    assert a["score"] == b["score"] and a["scenario_key"] == b["scenario_key"]
    assert a["decisions"] == b["decisions"]
    assert scenario_key(EXAMPLE) == "M5:saryarka|M7:nura|M8:nura|M10:nura|M12"


def test_no_mutation_and_repeatable():
    before = copy.deepcopy(CITY.raw)
    r1 = evaluate(CITY, EXAMPLE)
    r2 = evaluate(CITY, EXAMPLE)
    assert CITY.raw == before
    assert CITY.district("nura").indicators["S1"] == 38
    assert r1 == r2


def test_lag_applied_and_synergy_without_lag():
    r = evaluate(CITY, EXAMPLE)
    nura = next(d for d in r["district_results"] if d["id"] == "nura")
    ind = {i["code"]: i for i in nura["indicators"]}
    assert ind["S1"]["after"] == pytest.approx(48.0)        # 38 + 16*5/8
    assert ind["S2"]["after"] == pytest.approx(43.75)       # 35 + 14*5/8
    assert ind["B1"]["after"] == pytest.approx(67.5)        # 55 + 12*7/8 + 2 синергия без лага
    assert ind["C2"]["after"] == pytest.approx(54.375)      # 50 + 5*7/8, городская мера
    esil = next(d for d in r["district_results"] if d["id"] == "esil")
    assert {i["code"]: i for i in esil["indicators"]}["C2"]["after"] == pytest.approx(74.375)


def test_measure_contributions():
    r = evaluate(CITY, EXAMPLE)
    mc = {m["measure_id"]: m for m in r["measure_contributions"]}
    assert set(mc) == {"M7", "M8", "M10", "M12", "M5"}
    assert mc["M7"]["realized_fraction"] == pytest.approx(5 / 8)
    assert mc["M7"]["effects"] == [{"district_id": "nura", "code": "S1", "delta": pytest.approx(10.0)}]
    assert len(mc["M12"]["effects"]) == 5
    assert all(e["code"] == "C2" and e["delta"] == pytest.approx(4.375) for e in mc["M12"]["effects"])


def test_invalid_returns_nulls():
    r = evaluate(CITY, EXAMPLE[:4])
    assert r["valid"] is False and r["score"] is None and r["errors"]
    assert r["district_results"] is None and r["measure_contributions"] is None
    assert r["decisions"] is not None and r["scenario_key"]


def test_clip_after_sum_both_bounds():
    # два эффекта в одной ячейке: 99 + 4*6/8 − 2*7/8 = 100.25 → 100. Clip после каждого шага дал бы 98.25
    ind = apply_effects(CITY, [{"measure_id": "M2"}, {"measure_id": "M11", "district_id": "esil"}], base={"esil": {"T1": 99.0}})
    assert ind["esil"]["T1"] == 100
    # нижняя граница: 1 − 1.75 → 0
    ind = apply_effects(CITY, [{"measure_id": "M11", "district_id": "esil"}], base={"esil": {"T1": 1.0}})
    assert ind["esil"]["T1"] == 0


def test_critical_threshold_is_strict():
    assert count_critical(CITY, {"x": {"T1": 39.999}}) == 1
    assert count_critical(CITY, {"x": {"T1": 40.0}}) == 0


def test_minimum_follows_weakest_district_not_nura():
    base = {d.id: dict(d.indicators) for d in CITY.districts}
    base["esil"] = {c: 41.0 for c in CITY.indicator_order}
    agg = aggregate(CITY, apply_effects(CITY, [], base=base))
    assert agg["minimum"] == pytest.approx(41.0)
    assert min(agg["per"], key=agg["per"].get) == "esil"
