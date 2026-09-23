# tests/test_explain.py
import json
from engine.model import load_city
from engine.scoring import evaluate
from engine.advisor import find_improvements
from engine.facts import build_facts
from engine import explain as ex

CITY = load_city()
EX = [dict(d) for d in CITY.example_scenario]


def _prep():
    r = evaluate(CITY, EX)
    c = find_improvements(CITY, EX)
    return r, c, build_facts(CITY, r, c)


def _good(c):
    return json.dumps({"summary": "План усиливает Нуру.", "strengths": [{"text": "Нура растёт", "fact_ids": ["f2"]}],
                       "risks": [{"text": "Эффект школ реализован частично", "fact_ids": ["f5"]}],
                       "suggestions": [{"candidate_id": c[0]["id"], "text": "Замена усиливает результат", "fact_ids": ["f1"]}] if c else []},
                      ensure_ascii=False)


def test_no_key_is_fallback_and_never_calls_model(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    calls = []
    ex.clear_cache()
    r, c, f = _prep()
    out = ex.explain(CITY, r, c, f, call_model=lambda *a: calls.append(1) or (_good(c), "m"))
    assert out["mode"] == "template" and out["reason"] == "not_configured" and calls == []
    assert out["explanation"]["summary"] and out["explanation"]["risks"]


def test_broken_json_is_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    ex.clear_cache()
    r, c, f = _prep()
    out = ex.explain(CITY, r, c, f, call_model=lambda *a: ("{not json", "m"))
    assert out["mode"] == "template" and out["reason"] == "JSONDecodeError"


def test_unknown_fact_or_candidate_is_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    r, c, f = _prep()
    bad_fact = json.dumps({"summary": "x", "strengths": [{"text": "y", "fact_ids": ["f999"]}],
                           "risks": [{"text": "z", "fact_ids": ["f1"]}], "suggestions": []})
    ex.clear_cache()
    assert ex.explain(CITY, r, c, f, call_model=lambda *a: (bad_fact, "m"))["mode"] == "template"
    bad_cand = json.dumps({"summary": "x", "strengths": [{"text": "y", "fact_ids": ["f1"]}],
                           "risks": [{"text": "z", "fact_ids": ["f1"]}], "suggestions": [{"candidate_id": "c9", "text": "t", "fact_ids": ["f1"]}]})
    ex.clear_cache()
    assert ex.explain(CITY, r, c, f, call_model=lambda *a: (bad_cand, "m"))["mode"] == "template"


def test_invented_number_or_missing_section_is_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    r, c, f = _prep()
    invented = json.dumps({"summary": "Score 999 при бюджете 10000", "strengths": [{"text": "y", "fact_ids": ["f1"]}],
                           "risks": [{"text": "z", "fact_ids": ["f1"]}], "suggestions": []})
    ex.clear_cache()
    assert ex.explain(CITY, r, c, f, call_model=lambda *a: (invented, "m"))["mode"] == "template"
    no_risks = json.dumps({"summary": "x", "strengths": [{"text": "y", "fact_ids": ["f1"]}], "risks": [], "suggestions": []})
    ex.clear_cache()
    assert ex.explain(CITY, r, c, f, call_model=lambda *a: (no_risks, "m"))["mode"] == "template"
    only_summary = json.dumps({"summary": "x"})
    ex.clear_cache()
    assert ex.explain(CITY, r, c, f, call_model=lambda *a: (only_summary, "m"))["mode"] == "template"


def test_rounded_fact_number_is_accepted(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    r, c, f = _prep()
    ok = json.dumps({"summary": "Score вырос до 56,5, прирост около 4 балла", "strengths": [{"text": "y", "fact_ids": ["f2"]}],
                     "risks": [{"text": "z", "fact_ids": ["f1"]}], "suggestions": []}, ensure_ascii=False)
    ex.clear_cache()
    assert ex.explain(CITY, r, c, f, call_model=lambda *a: (ok, "m"))["mode"] == "live"


def test_valid_answer_is_live_and_cached(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    calls = []
    r, c, f = _prep()

    def fake(*a):
        calls.append(1)
        return _good(c), "fake-model"
    ex.clear_cache()
    a = ex.explain(CITY, r, c, f, call_model=fake)
    b = ex.explain(CITY, r, c, f, call_model=fake)
    assert a["mode"] == "live" and a["model"] == "fake-model" and len(calls) == 1 and b == a


def test_transient_failure_not_cached(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    r, c, f = _prep()
    state = {"n": 0}

    def flaky(*a):
        state["n"] += 1
        if state["n"] == 1:
            raise TimeoutError("timeout")
        return _good(c), "m"
    ex.clear_cache()
    assert ex.explain(CITY, r, c, f, call_model=flaky)["mode"] == "template"
    assert ex.explain(CITY, r, c, f, call_model=flaky)["mode"] == "live"
