# tests/test_bank.py
import json
import pytest
from fastapi.testclient import TestClient
from engine.model import load_city
from engine.scoring import evaluate
from engine.advisor import find_improvements
from engine.facts import build_facts
from engine.ranking import load_index, rank_info, enumerate_valid, INDEX_PATH
from engine.templates import template_explanation, plural
from engine import explain as ex
from app import create_app

CITY = load_city()
EX = [dict(d) for d in CITY.example_scenario]
INDEX = load_index()
BODY = {"decisions": EX}


def _prep():
    r = evaluate(CITY, EX)
    c = find_improvements(CITY, EX)
    return r, c, build_facts(CITY, r, c)


def test_plural():
    assert plural(1, "балл", "балла", "баллов") == "балл"
    assert plural(3, "балл", "балла", "баллов") == "балла"
    assert plural(11, "балл", "балла", "баллов") == "баллов"
    assert plural(22, "балл", "балла", "баллов") == "балла"


def test_index_exists_and_consistent():
    assert INDEX_PATH.exists(), "запустите python scripts/rank_all.py"
    assert INDEX["dataset_version"] == CITY.version
    assert INDEX["total"] > 100000 and len(INDEX["top"]) == 100
    top1 = INDEX["top"][0]
    assert evaluate(CITY, top1["decisions"])["score"] == pytest.approx(top1["score"], abs=1e-9)
    assert INDEX["top"][0]["score"] >= INDEX["top"][-1]["score"]
    # первые 200 наборов перебора валидны по общему валидатору
    from engine.validator import validate
    for i, dec in zip(range(200), enumerate_valid(CITY)):
        assert validate(CITY, dec) == []


def test_rank_info_example():
    r = evaluate(CITY, EX)
    info = rank_info(INDEX, r["scenario_key"], r["score"])
    assert 0 < info["percentile"] <= 100 and info["total"] == INDEX["total"]
    assert info["gap_to_best"] == pytest.approx(INDEX["score_max"] - r["score"], abs=1e-9)
    best = INDEX["top"][0]
    assert rank_info(INDEX, best["scenario_key"], best["score"])["top_position"] == 1
    assert rank_info(None, "x", 1.0) is None


def test_template_explanation_example():
    r, c, f = _prep()
    rank = rank_info(INDEX, r["scenario_key"], r["score"])
    t = template_explanation(CITY, r, c, f, INDEX, rank)
    assert "56,5" in t["summary"] and "вариантов" in t["summary"]
    assert t["strengths"] and t["risks"] and len(t["suggestions"]) == len(c)
    assert t["comparison"] and "57,2" in t["comparison"] and "вместо" in t["comparison"]
    ids = {x["id"] for x in f}
    for key in ("strengths", "risks", "suggestions"):
        for it in t[key]:
            assert it["fact_ids"] and set(it["fact_ids"]) <= ids
    # риск про упущенную синергию: M10 выбран без... нет, здесь M10+M12 оба; проверим негативный набор
    s = [{"measure_id": "M10", "district_id": "nura"}, {"measure_id": "M7", "district_id": "nura"},
         {"measure_id": "M14"}, {"measure_id": "M4", "district_id": "esil"}, {"measure_id": "M11", "district_id": "esil"}]
    r2 = evaluate(CITY, s); c2 = find_improvements(CITY, s); f2 = build_facts(CITY, r2, c2)
    t2 = template_explanation(CITY, r2, c2, f2, INDEX, None)
    texts = " ".join(x["text"] for x in t2["risks"])
    assert "бонус связки" in texts and "платформы обращений" in texts and "Безопасные переходы" in texts


def test_explain_without_key_uses_template(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    ex.clear_cache()
    r, c, f = _prep()
    out = ex.explain(CITY, r, c, f, index=INDEX, rank=rank_info(INDEX, r["scenario_key"], r["score"]))
    assert out["mode"] == "template" and out["reason"] == "not_configured" and out["key_source"] is None
    assert out["comparison"] and out["rank"]["total"] == INDEX["total"]


def test_user_key_has_priority_and_separate_cache(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "server-key")
    seen = []
    r, c, f = _prep()
    good = json.dumps({"summary": "ок", "strengths": [{"text": "s", "fact_ids": ["f1"]}],
                       "risks": [{"text": "r", "fact_ids": ["f2"]}], "suggestions": []})

    def fake(facts, cands, key):
        seen.append(key)
        return good, "m"
    ex.clear_cache()
    a = ex.explain(CITY, r, c, f, call_model=fake)
    b = ex.explain(CITY, r, c, f, call_model=fake, user_key="user-key")
    assert seen == ["server-key", "user-key"] and a["key_source"] == "server" and b["key_source"] == "user"


def test_chat_modes(monkeypatch):
    r, c, f = _prep()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    out = ex.chat(CITY, r, c, f, INDEX, None, [{"role": "user", "content": "что улучшить?"}])
    assert out["mode"] == "unavailable"
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    ok = ex.chat(CITY, r, c, f, INDEX, None, [{"role": "user", "content": "что улучшить?"}],
                 call_model=lambda system, msgs, key: ("Замените M5 на M3 в Нуре, Score 57,21.", "m"))
    assert ok["mode"] == "live" and ok["numbers_checked"] is True
    top_ok = ex.chat(CITY, r, c, f, INDEX, None, [{"role": "user", "content": "?"}],
                     call_model=lambda system, msgs, key: ("Лучший план стоит 98 и даёт Score 57,24", "m"))
    assert top_ok["numbers_checked"] is True
    bad = ex.chat(CITY, r, c, f, INDEX, None, [{"role": "user", "content": "?"}],
                  call_model=lambda system, msgs, key: ("Score станет 99,9", "m"))
    assert bad["mode"] == "live" and bad["numbers_checked"] is False
    err = ex.chat(CITY, r, c, f, INDEX, None, [{"role": "user", "content": "?"}],
                  call_model=lambda *a: (_ for _ in ()).throw(TimeoutError()))
    assert err["mode"] == "error"


def test_api_top_rank_chat_and_key_header(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    ex.clear_cache()
    calls = []

    def fake_chat(system, msgs, key):
        calls.append(key)
        return "Ответ советника без чисел.", "m"
    client = TestClient(create_app(chat_model=fake_chat))
    h = client.get("/api/health").json()
    assert h["ranking_available"] is True and h["total_plans"] == INDEX["total"]
    t = client.get("/api/top?limit=3").json()
    assert len(t["top"]) == 3 and t["top"][0]["rank"] == 1
    e = client.post("/api/evaluate", json=BODY).json()
    assert e["rank"]["total"] == INDEX["total"] and 0 < e["rank"]["percentile"] <= 100
    x = client.post("/api/explain", json=BODY).json()
    assert x["mode"] == "template" and x["comparison"] and x["rank"]
    ch = client.post("/api/chat", json={**BODY, "messages": [{"role": "user", "content": "привет"}]}).json()
    assert ch["mode"] == "unavailable"
    ch = client.post("/api/chat", json={**BODY, "messages": [{"role": "user", "content": "привет"}]},
                     headers={"X-OpenAI-Key": "user-key"}).json()
    assert ch["mode"] == "live" and ch["numbers_checked"] is True and calls == ["user-key"]
    assert client.post("/api/chat", json={**BODY, "messages": [{"role": "user", "content": "x", "extra": 1}]}).status_code == 422
    assert client.post("/api/chat", json={**BODY, "messages": []}).status_code == 422
    assert client.post("/api/chat", json={**BODY, "messages": [{"role": "system", "content": "x"}]}).status_code == 422
    assert client.post("/api/chat", json={**BODY, "messages": [{"role": "assistant", "content": "x"}]}).status_code == 422


def test_cache_respects_missing_key(monkeypatch):
    r, c, f = _prep()
    good = json.dumps({"summary": "ок", "strengths": [{"text": "s", "fact_ids": ["f1"]}],
                       "risks": [{"text": "r", "fact_ids": ["f2"]}], "suggestions": []})
    ex.clear_cache()
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    assert ex.explain(CITY, r, c, f, call_model=lambda *a: (good, "A"))["mode"] == "live"
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert ex.explain(CITY, r, c, f, call_model=lambda *a: (good, "A"))["mode"] == "template"
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    assert ex.explain(CITY, r, c, f, call_model=lambda *a: (good, "B"))["model"] == "B"


def test_pareto_frontier_cost_vs_score():
    # Парето: для каждого уровня стоимости лучший достижимый Score; стоимость и Score строго растут
    pareto = INDEX["pareto"]
    assert pareto and pareto[-1]["score"] == pytest.approx(INDEX["score_max"], abs=1e-9)
    for a, b in zip(pareto, pareto[1:]):
        assert a["cost"] < b["cost"] and a["score"] < b["score"]
    for p in pareto[:5] + pareto[-3:]:
        checked = evaluate(CITY, p["decisions"])
        assert checked["valid"] and checked["cost"] == p["cost"] and checked["score"] == pytest.approx(p["score"], abs=1e-9)
    client = TestClient(create_app())
    t = client.get("/api/top?limit=1").json()
    assert t["pareto"][0]["cost"] == pareto[0]["cost"] and len(t["pareto"]) == len(pareto)
