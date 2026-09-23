# app.py
from __future__ import annotations
from pathlib import Path
from typing import Literal, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.base import BaseHTTPMiddleware

from engine.model import load_city
from engine.scoring import evaluate, baseline
from engine.advisor import find_improvements
from engine.facts import build_facts
from engine.explain import explain, chat, check_key, server_key, resolve_key
from engine.ranking import load_index, rank_info

load_dotenv(Path(__file__).resolve().parent / ".env")
MAX_BODY = 16 * 1024
STATIC = Path(__file__).resolve().parent / "static"


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    measure_id: str = Field(max_length=8)
    district_id: Optional[str] = Field(default=None, max_length=32)


class ScenarioIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    decisions: list[Decision] = Field(max_length=10)


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    decisions: list[Decision] = Field(max_length=10)
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)


class BodyLimitMiddleware(BaseHTTPMiddleware):
    """Читает тело POST целиком и отвечает 413, если фактически получено больше MAX_BODY байт."""

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST":
            body = await request.body()
            if len(body) > MAX_BODY:
                return JSONResponse({"detail": "body too large"}, status_code=413)
        return await call_next(request)


def create_app(call_model=None, chat_model=None, index_path=None) -> FastAPI:
    city = load_city()
    index = load_index(index_path) if index_path else load_index()
    if index and index.get("dataset_version") != city.version:
        index = None
    app = FastAPI(title="Аким на 5 часов", version="1.1")
    app.add_middleware(BodyLimitMiddleware)

    def to_decisions(s) -> list:
        return [{"measure_id": d.measure_id, **({"district_id": d.district_id} if d.district_id else {})} for d in s.decisions]

    def with_rank(r: dict) -> dict:
        r["rank"] = rank_info(index, r["scenario_key"], r["score"]) if r["valid"] else None
        return r

    def valid_or_422(s):
        d = to_decisions(s)
        r = with_rank(evaluate(city, d))
        if not r["valid"]:
            raise HTTPException(status_code=422, detail={"errors": r["errors"]})
        return d, r

    @app.get("/api/health")
    def health():
        return {"status": "ok", "dataset_version": city.version, "ai_configured": bool(server_key()),
                "ranking_available": index is not None, "total_plans": index["total"] if index else None}

    @app.get("/api/city")
    def city_data():
        return {**city.raw, "baseline": baseline(city)}

    @app.get("/api/top")
    def top(limit: int = 5):
        if not index:
            return {"total": None, "top": []}
        return {"total": index["total"], "score_max": index["score_max"], "top": index["top"][:max(1, min(limit, 100))]}

    @app.post("/api/evaluate")
    def api_evaluate(s: ScenarioIn):
        return with_rank(evaluate(city, to_decisions(s)))

    @app.post("/api/improvements")
    def api_improvements(s: ScenarioIn):
        d, r = valid_or_422(s)
        return {"scenario_key": r["scenario_key"], "candidates": find_improvements(city, d)}

    @app.post("/api/explain")
    def api_explain(s: ScenarioIn, x_openai_key: Optional[str] = Header(default=None, alias="X-OpenAI-Key")):
        d, r = valid_or_422(s)
        cands = find_improvements(city, d)
        facts = build_facts(city, r, cands)
        out = explain(city, r, cands, facts, call_model=call_model, user_key=x_openai_key, index=index, rank=r["rank"])
        return {**out, "candidates": cands}

    @app.post("/api/chat")
    def api_chat(s: ChatIn, x_openai_key: Optional[str] = Header(default=None, alias="X-OpenAI-Key")):
        d, r = valid_or_422(s)
        cands = find_improvements(city, d)
        facts = build_facts(city, r, cands)
        if s.messages[-1].role != "user":
            raise HTTPException(status_code=422, detail={"errors": [{"code": "last_message_not_user", "message": "Последнее сообщение должно быть от пользователя"}]})
        msgs = [{"role": m.role, "content": m.content} for m in s.messages]
        return chat(city, r, cands, facts, index, r["rank"], msgs, user_key=x_openai_key, call_model=chat_model)

    @app.post("/api/ai/check")
    def api_ai_check(x_openai_key: Optional[str] = Header(default=None, alias="X-OpenAI-Key")):
        key = resolve_key(x_openai_key)
        out = check_key(key)
        out["key_source"] = "user" if (x_openai_key or "").strip() else ("server" if server_key() else None)
        return out

    if (STATIC / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="static")
    return app


app = create_app()
