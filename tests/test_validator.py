# tests/test_validator.py
from engine.model import load_city
from engine.validator import validate

CITY = load_city()
EXAMPLE = [dict(d) for d in CITY.example_scenario]


def codes(decisions):
    return [e["code"] for e in validate(CITY, decisions)]


def by_code(decisions, code):
    return next(e for e in validate(CITY, decisions) if e["code"] == code)


def test_example_is_valid():
    assert validate(CITY, EXAMPLE) == []


def test_cheapest_set_is_valid():
    s = [{"measure_id": "M9", "district_id": "nura"}, {"measure_id": "M11", "district_id": "esil"},
         {"measure_id": "M10", "district_id": "nura"}, {"measure_id": "M12"}, {"measure_id": "M4", "district_id": "saryarka"}]
    assert validate(CITY, s) == []


def test_zero_four_and_six_decisions():
    assert "decision_count" in codes([])
    assert "decision_count" in codes(EXAMPLE[:4])
    assert "decision_count" in codes(EXAMPLE + [{"measure_id": "M9", "district_id": "esil"}])


def test_budget_exceeded_with_indexes():
    s = [{"measure_id": "M3", "district_id": "esil"}, {"measure_id": "M13", "district_id": "almaty"},
         {"measure_id": "M5", "district_id": "saryarka"}, {"measure_id": "M7", "district_id": "nura"}, {"measure_id": "M12"}]  # 121
    e = by_code(s, "budget_exceeded")
    assert "21" in e["message"] and e["decision_indexes"] == [0, 1, 2, 3, 4]


def test_budget_exactly_100_is_valid():
    s = [{"measure_id": "M3", "district_id": "esil"}, {"measure_id": "M13", "district_id": "almaty"},
         {"measure_id": "M4", "district_id": "saryarka"}, {"measure_id": "M10", "district_id": "nura"}, {"measure_id": "M14"}]  # 30+28+15+12+16=101
    assert "budget_exceeded" in codes(s)
    s[3] = {"measure_id": "M11", "district_id": "nura"}  # 30+28+15+10+16=99
    assert "budget_exceeded" not in codes(s)


def test_duplicate_measure_even_in_other_district():
    s = EXAMPLE[:4] + [{"measure_id": "M7", "district_id": "esil"}]
    e = by_code(s, "duplicate_measure")
    assert e["measure_ids"] == ["M7"] and e["decision_indexes"] == [0, 4]


def test_direction_limit():
    s = [{"measure_id": "M7", "district_id": "nura"}, {"measure_id": "M8", "district_id": "nura"},
         {"measure_id": "M9", "district_id": "esil"}, {"measure_id": "M12"}, {"measure_id": "M10", "district_id": "nura"}]
    e = by_code(s, "direction_limit")
    assert set(e["measure_ids"]) == {"M7", "M8", "M9"} and e["decision_indexes"] == [0, 1, 2]


def test_district_required_and_forbidden():
    assert by_code(EXAMPLE[:4] + [{"measure_id": "M9"}], "district_required")["decision_indexes"] == [4]
    s = EXAMPLE[:3] + [{"measure_id": "M12", "district_id": "nura"}, EXAMPLE[4]]
    assert by_code(s, "district_forbidden")["decision_indexes"] == [3]


def test_null_district_for_city_measure_is_ok():
    s = EXAMPLE[:3] + [{"measure_id": "M12", "district_id": None}, EXAMPLE[4]]
    assert validate(CITY, s) == []


def test_unknown_ids():
    assert "unknown_measure" in codes(EXAMPLE[:4] + [{"measure_id": "M99", "district_id": "nura"}])
    assert "unknown_district" in codes(EXAMPLE[:4] + [{"measure_id": "M9", "district_id": "moon"}])


def test_conflict_global_m1_m3_any_districts():
    s = [{"measure_id": "M1", "district_id": "esil"}, {"measure_id": "M3", "district_id": "nura"},
         {"measure_id": "M12"}, {"measure_id": "M10", "district_id": "nura"}, {"measure_id": "M4", "district_id": "saryarka"}]
    e = by_code(s, "incompatible_measures")
    assert e["scope"] == "global" and set(e["measure_ids"]) == {"M1", "M3"}


def test_conflict_same_district_only():
    same = [{"measure_id": "M4", "district_id": "nura"}, {"measure_id": "M7", "district_id": "nura"},
            {"measure_id": "M12"}, {"measure_id": "M10", "district_id": "esil"}, {"measure_id": "M9", "district_id": "esil"}]
    diff = [{"measure_id": "M4", "district_id": "esil"}, {"measure_id": "M7", "district_id": "nura"},
            {"measure_id": "M12"}, {"measure_id": "M10", "district_id": "esil"}, {"measure_id": "M9", "district_id": "esil"}]
    assert by_code(same, "incompatible_measures")["scope"] == "same_district"
    assert "incompatible_measures" not in codes(diff)
    assert validate(CITY, diff) == []
