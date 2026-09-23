# tests/test_codex_regressions.py — регрессии по ревью Codex (docs/codex-proposals.md, R4 и R5)
from fastapi.testclient import TestClient
from app import create_app
from engine.model import load_city
from engine.scoring import evaluate

CITY = load_city()
EX = [dict(d) for d in CITY.example_scenario]
BODY = {"decisions": EX, "messages": [{"role": "user", "content": "что улучшить?"}]}


def test_empty_model_reply_gives_error_mode_not_500(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    for reply in (None, "", "   ", 42):
        client = TestClient(create_app(chat_model=lambda *a, r=reply: (r, "fake")))
        resp = client.post("/api/chat", json=BODY)
        assert resp.status_code == 200
        j = resp.json()
        assert j["mode"] == "error" and j["numbers_checked"] is False and j["model"] is None
    client = TestClient(create_app(chat_model=lambda *a: ("Ответ без чисел.", "fake")))
    assert client.post("/api/chat", json=BODY).json()["mode"] == "live"


def test_core_survives_non_string_measure_id():
    for bad in ([], {}, 7, None):
        r = evaluate(CITY, [{"measure_id": bad}] + EX[1:])
        assert r["valid"] is False and any(e["code"] == "unknown_measure" for e in r["errors"])
