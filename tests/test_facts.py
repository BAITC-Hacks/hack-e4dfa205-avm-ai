# tests/test_facts.py
from engine.model import load_city
from engine.scoring import evaluate
from engine.advisor import find_improvements
from engine.facts import build_facts, fallback_explanation

CITY = load_city()
EXAMPLE = [dict(d) for d in CITY.example_scenario]


def _prep(decisions=EXAMPLE):
    r = evaluate(CITY, decisions)
    c = find_improvements(CITY, decisions)
    return r, c, build_facts(CITY, r, c)


def test_facts_unique_ids_and_kinds():
    r, c, facts = _prep()
    ids = [f["id"] for f in facts]
    assert ids == [f"f{i}" for i in range(1, len(ids) + 1)]
    kinds = [f["kind"] for f in facts]
    assert kinds.count("measure") == 5
    assert "score" in kinds and "decomposition" in kinds and "worst_district" in kinds
    assert kinds.count("synergy") == 1
    assert kinds.count("candidate") == len(c)
    assert all(f["text"] and isinstance(f["data"], dict) for f in facts)


def test_measure_fact_has_lagged_effects():
    r, c, facts = _prep()
    m7 = next(f for f in facts if f["kind"] == "measure" and f["data"]["measure_id"] == "M7")
    assert "S1" in m7["text"] and "+10,0" in m7["text"] and "62%" in m7["text"]


def test_fallback_has_strengths_and_risks_on_example():
    r, c, facts = _prep()
    fb = fallback_explanation(facts, c)
    assert fb["summary"]
    assert len(fb["strengths"]) >= 1 and len(fb["risks"]) >= 1
    known = {f["id"] for f in facts}
    for key in ("strengths", "risks", "suggestions"):
        for item in fb[key]:
            assert item["fact_ids"] and set(item["fact_ids"]) <= known
    assert len(fb["suggestions"]) == len(c)
    assert {s["candidate_id"] for s in fb["suggestions"]} == {x["id"] for x in c}
    # у примера все меры с лагом 3 дают риск неполной реализации
    risk_kinds = {next(f["kind"] for f in facts if f["id"] == it["fact_ids"][0]) for it in fb["risks"]}
    assert risk_kinds & {"measure", "critical", "district_unchanged", "worst_district"}


def test_fallback_marks_negative_effect_as_risk():
    s = [{"measure_id": "M11", "district_id": "nura"}, {"measure_id": "M7", "district_id": "nura"},
         {"measure_id": "M12"}, {"measure_id": "M4", "district_id": "esil"}, {"measure_id": "M10", "district_id": "esil"}]
    r, c, facts = _prep(s)
    fb = fallback_explanation(facts, c)
    texts = " ".join(it["text"] for it in fb["risks"])
    assert "M11" in texts and "T1" in texts
