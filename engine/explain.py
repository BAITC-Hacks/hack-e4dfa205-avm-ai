# engine/explain.py
from __future__ import annotations
import json
import os
import re
from collections import OrderedDict
from .model import City
from .facts import fallback_explanation

PROMPT_VERSION = "akim-explain-v1"
MAX_CACHE = 100
_cache: "OrderedDict[str, dict]" = OrderedDict()

NUM_RE = re.compile(r"(?<![A-Za-zА-Яа-я\d_])-?\d+(?:[.,]\d+)?")

SYSTEM_PROMPT = (
    "Ты советник акима Астаны в учебном симуляторе городского бюджета. "
    "Тебе дан список фактов с идентификаторами f1..fN, каждый факт уже посчитан программой. "
    "Объясни результат человеческим языком: короткое резюме, 2–3 сильные стороны, 2–3 риска или компромисса, "
    "и по одному комментарию к каждой альтернативе c1..c3, если они переданы. "
    "Правила: не придумывай числа, меры и районы; используй только числа из фактов и только в том виде, как они там записаны; "
    "каждое утверждение опирается на факты и перечисляет их идентификаторы в fact_ids; "
    "в suggestions используй только переданные candidate_id; пиши по-русски, коротко, без общих фраз. "
    "Ответ строго JSON без других ключей: {\"summary\": str, \"strengths\": [{\"text\": str, \"fact_ids\": [str]}], "
    "\"risks\": [{\"text\": str, \"fact_ids\": [str]}], \"suggestions\": [{\"candidate_id\": str, \"text\": str, \"fact_ids\": [str]}]}"
)


class NotConfigured(Exception):
    pass


def clear_cache() -> None:
    _cache.clear()


def api_key() -> str:
    return os.environ.get("OPENAI_API_KEY", "").strip()


def model_name() -> str:
    return os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"


def call_openai(facts: list, candidates: list) -> tuple:
    """Реальный вызов OpenAI. Возвращает (текст ответа, имя модели)."""
    from openai import OpenAI
    timeout = float(os.environ.get("LLM_TIMEOUT_S", "15") or 15)
    client = OpenAI(api_key=api_key(), timeout=timeout, max_retries=0)
    payload = {"facts": [{"id": f["id"], "kind": f["kind"], "text": f["text"]} for f in facts],
               "candidate_ids": [c["id"] for c in candidates]}
    resp = client.chat.completions.create(
        model=model_name(), temperature=0.3, response_format={"type": "json_object"},
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    )
    return resp.choices[0].message.content, model_name()


def _allowed_numbers(facts: list) -> set:
    vals = set()

    def walk(x):
        if isinstance(x, bool):
            return
        if isinstance(x, (int, float)):
            vals.add(float(x))
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    for f in facts:
        walk(f.get("data", {}))
        for s in NUM_RE.findall(f["text"]):
            vals.add(float(s.replace(",", ".")))
    return vals


def _numbers_ok(text: str, allowed: set) -> bool:
    for s in NUM_RE.findall(text):
        v = float(s.replace(",", "."))
        if v.is_integer() and 0 <= v <= 14:
            continue
        if any(abs(v - a) <= 0.051 for a in allowed):
            continue
        return False
    return True


def _statement(item, fact_ids: set, allowed: set) -> dict:
    if not isinstance(item, dict) or set(item) - {"text", "fact_ids", "candidate_id"}:
        raise ValueError("bad statement shape")
    text = item.get("text")
    ids = item.get("fact_ids")
    if not isinstance(text, str) or not text.strip() or len(text) > 600:
        raise ValueError("bad text")
    if not isinstance(ids, list) or not ids or not all(isinstance(i, str) for i in ids) or not set(ids) <= fact_ids:
        raise ValueError("unknown fact id")
    if not _numbers_ok(text, allowed):
        raise ValueError("invented number")
    return {"text": text.strip(), "fact_ids": ids}


def validate_answer(text: str, facts: list, candidates: list) -> dict:
    data = json.loads(text)
    if not isinstance(data, dict) or set(data) != {"summary", "strengths", "risks", "suggestions"}:
        raise ValueError("bad top-level shape")
    fact_ids = {f["id"] for f in facts}
    cand_ids = {c["id"] for c in candidates}
    allowed = _allowed_numbers(facts)
    summary = data["summary"]
    if not isinstance(summary, str) or not summary.strip() or len(summary) > 800 or not _numbers_ok(summary, allowed):
        raise ValueError("bad summary")
    out = {"summary": summary.strip(), "strengths": [], "risks": [], "suggestions": []}
    for key in ("strengths", "risks"):
        items = data[key]
        if not isinstance(items, list) or not items or len(items) > 5:
            raise ValueError(f"bad {key}")
        for it in items:
            st = _statement(it, fact_ids, allowed)
            if "candidate_id" in it:
                raise ValueError("candidate_id outside suggestions")
            out[key].append(st)
    sugg = data["suggestions"]
    if not isinstance(sugg, list) or len(sugg) > 3:
        raise ValueError("bad suggestions")
    used = set()
    for it in sugg:
        st = _statement(it, fact_ids, allowed)
        cid = it.get("candidate_id")
        if cid not in cand_ids or cid in used:
            raise ValueError("unknown or repeated candidate id")
        used.add(cid)
        out["suggestions"].append({"candidate_id": cid, **st})
    return out


def explain(city: City, result: dict, candidates: list, facts: list, call_model=None) -> dict:
    """call_model(facts, candidates) -> (text, model). По умолчанию реальный OpenAI."""
    call = call_model or call_openai
    key = f"{city.version}|{PROMPT_VERSION}|{model_name()}|{result['scenario_key']}"
    if key in _cache:
        return _cache[key]
    base = {"scenario_key": result["scenario_key"], "facts": facts}
    try:
        if not api_key():
            raise NotConfigured()
        text, model = call(facts, candidates)
        out = {**base, "mode": "live", "model": model, "reason": None, "explanation": validate_answer(text, facts, candidates)}
        _cache[key] = out
        while len(_cache) > MAX_CACHE:
            _cache.popitem(last=False)
        return out
    except NotConfigured:
        reason = "not_configured"
    except Exception as e:  # таймаут, сеть, сломанный JSON, неверная схема, выдуманные числа
        reason = type(e).__name__
    return {**base, "mode": "fallback", "model": None, "reason": reason, "explanation": fallback_explanation(facts, candidates)}
