# tests/test_api.py
import asyncio
import json
import pytest
from fastapi.testclient import TestClient
from app import create_app
from engine import explain as ex

EX = {"decisions": [{"measure_id": "M7", "district_id": "nura"}, {"measure_id": "M8", "district_id": "nura"},
                    {"measure_id": "M10", "district_id": "nura"}, {"measure_id": "M12"}, {"measure_id": "M5", "district_id": "saryarka"}]}


@pytest.fixture
def client():
    return TestClient(create_app())


def test_health_and_city(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["dataset_version"] == "hackalem-12-v1" and h["ai_configured"] is False
    c = client.get("/api/city").json()
    assert len(c["districts"]) == 5 and len(c["measures"]) == 14 and c["budget"] == 100
    assert "example_scenario" in c and c["baseline"]["score"] == pytest.approx(52.55768, abs=1e-6)
    assert c["baseline"]["district_scores"]["nura"] == pytest.approx(49.18, abs=1e-6)


def test_evaluate_example(client):
    r = client.post("/api/evaluate", json=EX)
    assert r.status_code == 200
    j = r.json()
    assert j["valid"] and j["cost"] == 95 and j["score"] == pytest.approx(56.54307, abs=1e-6)
    assert j["decisions"][0] == {"measure_id": "M5", "district_id": "saryarka"}


def test_evaluate_invalid_is_200_with_errors(client):
    j = client.post("/api/evaluate", json={"decisions": EX["decisions"][:4]}).json()
    assert j["valid"] is False and j["score"] is None and j["errors"][0]["code"] == "decision_count"


def test_null_district_for_city_measure_accepted(client):
    body = json.loads(json.dumps(EX))
    body["decisions"][3]["district_id"] = None
    assert client.post("/api/evaluate", json=body).json()["valid"] is True


def test_improvements_and_explain_422_on_invalid(client):
    bad = {"decisions": EX["decisions"][:4]}
    r = client.post("/api/improvements", json=bad)
    assert r.status_code == 422 and r.json()["detail"]["errors"][0]["code"] == "decision_count"
    assert client.post("/api/explain", json=bad).status_code == 422


def test_improvements_ok(client):
    j = client.post("/api/improvements", json=EX).json()
    assert j["scenario_key"] and all(c["id"].startswith("c") for c in j["candidates"])


def test_explain_without_key_is_fallback(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    ex.clear_cache()
    j = client.post("/api/explain", json=EX).json()
    assert j["mode"] == "template" and j["reason"] == "not_configured"
    assert j["scenario_key"] and j["explanation"]["summary"] and j["facts"] and "candidates" in j


def test_explain_with_injected_model_is_live(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    good = json.dumps({"summary": "ок", "strengths": [{"text": "s", "fact_ids": ["f1"]}],
                       "risks": [{"text": "r", "fact_ids": ["f2"]}], "suggestions": []})
    ex.clear_cache()
    client = TestClient(create_app(call_model=lambda *a: (good, "fake")))
    j = client.post("/api/explain", json=EX).json()
    assert j["mode"] == "live" and j["model"] == "fake"


def test_unknown_field_and_too_many_rejected(client):
    assert client.post("/api/evaluate", json={"decisions": EX["decisions"], "score": 999}).status_code == 422
    bad = {"decisions": [dict(EX["decisions"][0], cost=1)] + EX["decisions"][1:]}
    assert client.post("/api/evaluate", json=bad).status_code == 422
    assert client.post("/api/evaluate", json={"decisions": EX["decisions"] * 3}).status_code == 422


def test_body_limit(client):
    big = {"decisions": [{"measure_id": "M12", "district_id": "x" * 20000}]}
    assert client.post("/api/evaluate", json=big).status_code == 413


def test_body_limit_stops_reading_chunked_stream():
    # TestClient читает тело целиком до вызова приложения, поэтому middleware проверяется через ASGI напрямую:
    # тело без Content-Length тремя чанками по 16 385 байт, ответ 413 после первого чанка, остальные не запрошены
    app = create_app()
    chunks = [b"x" * 16385] * 3
    received, sent = [], []

    async def receive():
        received.append(1)
        return {"type": "http.request", "body": chunks[len(received) - 1], "more_body": len(received) < len(chunks)}

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST", "scheme": "http",
             "path": "/api/evaluate", "raw_path": b"/api/evaluate", "query_string": b"", "root_path": "",
             "headers": [(b"host", b"testserver"), (b"content-type", b"application/json")],
             "client": ("testclient", 50000), "server": ("testserver", 80)}
    asyncio.run(app(scope, receive, send))
    start = next(m for m in sent if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    assert start["status"] == 413 and json.loads(body) == {"detail": "body too large"}
    assert len(received) == 1


def test_body_limit_passes_small_chunked_stream(client):
    # Обычное тело чанками доходит до маршрута целиком
    raw = json.dumps(EX).encode()
    parts = [raw[i:i + 7] for i in range(0, len(raw), 7)]
    r = client.post("/api/evaluate", content=iter(parts), headers={"Content-Type": "application/json"})
    assert r.status_code == 200 and r.json()["valid"] is True
