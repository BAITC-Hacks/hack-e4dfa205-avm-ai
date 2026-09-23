# app.py
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.base import BaseHTTPMiddleware

from engine.model import load_city
from engine.scoring import evaluate, baseline
from engine.advisor import find_improvements
from engine.facts import build_facts
from engine.explain import explain, api_key

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


class BodyLimitMiddleware(BaseHTTPMiddleware):
    """Читает тело POST целиком и отвечает 413, если фактически получено больше MAX_BODY байт.
    Проверяется реальный размер, а не только заголовок Content-Length."""

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST":
            body = await request.body()
            if len(body) > MAX_BODY:
                return JSONResponse({"detail": "body too large"}, status_code=413)
        return await call_next(request)


def create_app(call_model=None) -> FastAPI:
    city = load_city()
    app = FastAPI(title="Аким на 5 часов", version="1.0")
    app.add_middleware(BodyLimitMiddleware)

    def to_decisions(s: ScenarioIn) -> list:
        return [{"measure_id": d.measure_id, **({"district_id": d.district_id} if d.district_id else {})} for d in s.decisions]

    def valid_or_422(s: ScenarioIn):
        d = to_decisions(s)
        r = evaluate(city, d)
        if not r["valid"]:
            raise HTTPException(status_code=422, detail={"errors": r["errors"]})
        return d, r

    @app.get("/api/health")
    def health():
        return {"status": "ok", "dataset_version": city.version, "ai_configured": bool(api_key())}

    @app.get("/api/city")
    def city_data():
        return {**city.raw, "baseline": baseline(city)}

    @app.post("/api/evaluate")
    def api_evaluate(s: ScenarioIn):
        return evaluate(city, to_decisions(s))

    @app.post("/api/improvements")
    def api_improvements(s: ScenarioIn):
        d, r = valid_or_422(s)
        return {"scenario_key": r["scenario_key"], "candidates": find_improvements(city, d)}

    @app.post("/api/explain")
    def api_explain(s: ScenarioIn):
        d, r = valid_or_422(s)
        cands = find_improvements(city, d)
        facts = build_facts(city, r, cands)
        out = explain(city, r, cands, facts, call_model=call_model)
        return {**out, "candidates": cands}

    if (STATIC / "index.html").exists():
        app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="static")
    return app


app = create_app()
