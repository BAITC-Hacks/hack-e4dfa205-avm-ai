# engine/explain.py
from __future__ import annotations
import hashlib
import json
import os
import re
from collections import OrderedDict
from .model import City
from .facts import fallback_explanation
from .templates import template_explanation

PROMPT_VERSION = "akim-explain-v3"
MAX_CACHE = 100
_cache: "OrderedDict[str, dict]" = OrderedDict()

NUM_RE = re.compile(r"(?<![A-Za-zА-Яа-я\d_])-?\d+(?:[.,]\d+)?")


# Правила живой речи для модели: сжатая версия скилла humanizer (Wikipedia, «Signs of AI writing»)
HUMAN_STYLE = (
    "Пиши как живой советник, а не как отчёт или нейросеть. Правила стиля, проверь ответ по ним перед отправкой:\n"
    "1. Короткие предложения разной длины, простые связки «это», «есть», «даёт». Без канцелярита и без выражений "
    "«играет ключевую роль», «важно отметить», «подчёркивает значимость», «способствует развитию», «в рамках».\n"
    "2. Никаких пустых усилителей и рекламы: «значительно», «существенно», «положительно сказывается на качестве жизни», "
    "«комплексный подход», «устойчивое развитие». Вместо них конкретика: какая мера, где, что изменилось и на сколько.\n"
    "3. Никаких деепричастных хвостов вроде «улучшая», «обеспечивая», «способствуя», «подчёркивая» в конце предложения. "
    "Разбей на два предложения.\n"
    "4. Без списков из трёх ради красоты, без формул «не только…, но и…», без «с одной стороны… с другой стороны».\n"
    "5. Без размытых ссылок на авторитеты: «эксперты считают», «как известно», «исследования показывают».\n"
    "6. Без пустых выводов в конце: «в целом план хорош», «дальнейшая работа покажет», «это шаг в правильном направлении». "
    "Заканчивай последним конкретным фактом или советом.\n"
    "7. Без обращений к пользователю в стиле помощника: «отличный вопрос», «надеюсь, это поможет», «давайте разберём». "
    "Просто отвечай по делу.\n"
    "8. Без тире «—» и «–», без жирного шрифта, без эмодзи, без заголовков. Обычные предложения, кавычки «ёлочки».\n"
    "9. Меры называй по-человечески и коротко: «камеры и освещение», «ЛРТ в Нуре», «поликлиника в Нуре», код меры в скобках не обязателен. "
    "Районы называй по имени. Показатели тоже словами: школы, воздух, безопасность улиц, дороги; коды вроде S1, E2, B1 не пиши вообще. К числам оценки добавляй слово «балла» или «баллов»: «+3,99 балла», «56,5 балла», «2 балла».\n"
    "10. Можно иметь мнение и сомнение: «я бы поменял…», «здесь спорно», «мне не нравится, что…». Нельзя льстить и нельзя выдумывать числа.\n"
)

SYSTEM_PROMPT = (
    "Ты советник акима Астаны в учебном симуляторе городского бюджета. "
    "Тебе дан список фактов с идентификаторами f1..fN, каждый факт уже посчитан программой. "
    "Объясни результат так, как объяснил бы опытный заместитель акима коллеге за столом: короткое резюме, 2–3 сильные стороны, 2–3 риска или компромисса, "
    "и по одному комментарию к каждой альтернативе c1..c3, если они переданы. "
    "Называй меры по названию, а не только по коду, и привязывай каждый риск к конкретному району или показателю. "
    "Правила: не придумывай числа, меры и районы; используй только числа из фактов и только в том виде, как они там записаны; "
    "каждое утверждение опирается на факты и перечисляет их идентификаторы в fact_ids; "
    "в suggestions используй только переданные candidate_id; пиши по-русски, коротко, без общих фраз. "
    "Ответ строго JSON без других ключей: {\"summary\": str, \"strengths\": [{\"text\": str, \"fact_ids\": [str]}], "
    "\"risks\": [{\"text\": str, \"fact_ids\": [str]}], \"suggestions\": [{\"candidate_id\": str, \"text\": str, \"fact_ids\": [str]}]}\n\n"
    + HUMAN_STYLE
)

CHAT_PROMPT = (
    "Ты советник акима Астаны в учебном симуляторе городского бюджета. Отвечай на вопросы пользователя о его плане. "
    "Ниже факты о текущем плане, они посчитаны программой, и список лучших планов из полного перебора. "
    "Правила: опирайся только на эти факты; не придумывай числа, меры и районы; если ответа в фактах нет, скажи об этом; "
    "советы давай конкретные: какую меру на какую заменить и что это даст, ссылаясь на альтернативы или лучшие планы. "
    "Отвечай по-русски, коротко, до 120 слов, обычным текстом без JSON.\n\n"
    + HUMAN_STYLE
)


class NotConfigured(Exception):
    pass


def clear_cache() -> None:
    _cache.clear()


def server_key() -> str:
    return os.environ.get("OPENAI_API_KEY", "").strip()


def resolve_key(user_key: str | None) -> str:
    """Ключ из запроса имеет приоритет над серверным."""
    return (user_key or "").strip() or server_key()


def api_key() -> str:
    """Совместимость со старым app.py: серверный ключ."""
    return server_key()


def model_name() -> str:
    return os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"


def _client(key: str):
    from openai import OpenAI
    timeout = float(os.environ.get("LLM_TIMEOUT_S", "15") or 15)
    return OpenAI(api_key=key, timeout=timeout, max_retries=0)


def call_openai(facts: list, candidates: list, key: str) -> tuple:
    """Реальный вызов OpenAI для структурированного объяснения. Возвращает (текст ответа, имя модели)."""
    payload = {"facts": [{"id": f["id"], "kind": f["kind"], "text": f["text"]} for f in facts],
               "candidate_ids": [c["id"] for c in candidates]}
    resp = _client(key).chat.completions.create(
        model=model_name(), temperature=0.3, response_format={"type": "json_object"},
        messages=[{"role": "system", "content": SYSTEM_PROMPT},
                  {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    )
    return resp.choices[0].message.content, model_name()


def call_openai_chat(system: str, messages: list, key: str) -> tuple:
    resp = _client(key).chat.completions.create(
        model=model_name(), temperature=0.4,
        messages=[{"role": "system", "content": system}] + messages,
    )
    return resp.choices[0].message.content, model_name()


def check_key(key: str) -> dict:
    """Минимальный запрос, чтобы проверить ключ. Ключ не сохраняется и не логируется."""
    if not key:
        return {"ok": False, "error": "Ключ не передан"}
    try:
        _client(key).models.retrieve(model_name())
        return {"ok": True, "model": model_name()}
    except Exception as e:
        return {"ok": False, "error": type(e).__name__}


def _allowed_numbers(facts: list, extra: list | None = None) -> set:
    vals = set(extra or [])

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


# Числа, которые можно называть без факта: количество мер и решений, горизонт, порог, бюджет
FREE_NUMBERS = {1.0, 2.0, 3.0, 4.0, 5.0, 8.0, 40.0, 100.0}


def _numbers_ok(text: str, allowed: set) -> bool:
    """Каждое число в тексте должно быть среди чисел разрешённых фактов (с допуском на округление)
    или в коротком списке общих констант. Проверка лексическая: смысл утверждения она не подтверждает."""
    for s in NUM_RE.findall(text):
        v = float(s.replace(",", "."))
        if v in FREE_NUMBERS:
            continue
        if any(abs(v - a) <= 0.051 for a in allowed):
            continue
        return False
    return True


def _numbers_of(facts: list, ids) -> set:
    """Числа только тех фактов, на которые ссылается утверждение."""
    return _allowed_numbers([f for f in facts if f["id"] in set(ids)])


def _statement(item, fact_ids: set, facts: list) -> dict:
    if not isinstance(item, dict) or set(item) - {"text", "fact_ids", "candidate_id"}:
        raise ValueError("bad statement shape")
    text = item.get("text")
    ids = item.get("fact_ids")
    if not isinstance(text, str) or not text.strip() or len(text) > 600:
        raise ValueError("bad text")
    if not isinstance(ids, list) or not ids or not all(isinstance(i, str) for i in ids) or not set(ids) <= fact_ids:
        raise ValueError("unknown fact id")
    if not _numbers_ok(text, _numbers_of(facts, ids)):
        raise ValueError("invented number")
    return {"text": text.strip(), "fact_ids": ids}


def validate_answer(text: str, facts: list, candidates: list) -> dict:
    data = json.loads(text)
    if not isinstance(data, dict) or set(data) != {"summary", "strengths", "risks", "suggestions"}:
        raise ValueError("bad top-level shape")
    fact_ids = {f["id"] for f in facts}
    cand_ids = {c["id"] for c in candidates}
    # Резюме опирается на итоговые факты: оценка, разложение, районы, критические значения. Стоимости и альтернативы в резюме числами не называются
    summary_allowed = _allowed_numbers([f for f in facts if f["kind"] in ("score", "decomposition", "worst_district", "district", "critical", "no_critical", "synergy")])
    summary = data["summary"]
    if not isinstance(summary, str) or not summary.strip() or len(summary) > 800 or not _numbers_ok(summary, summary_allowed):
        raise ValueError("bad summary")
    out = {"summary": summary.strip(), "strengths": [], "risks": [], "suggestions": []}
    for key in ("strengths", "risks"):
        items = data[key]
        if not isinstance(items, list) or not items or len(items) > 5:
            raise ValueError(f"bad {key}")
        for it in items:
            st = _statement(it, fact_ids, facts)
            if "candidate_id" in it:
                raise ValueError("candidate_id outside suggestions")
            out[key].append(st)
    sugg = data["suggestions"]
    if not isinstance(sugg, list) or len(sugg) > 3:
        raise ValueError("bad suggestions")
    used = set()
    for it in sugg:
        st = _statement(it, fact_ids, facts)
        cid = it.get("candidate_id")
        if cid not in cand_ids or cid in used:
            raise ValueError("unknown or repeated candidate id")
        used.add(cid)
        out["suggestions"].append({"candidate_id": cid, **st})
    return out


def _key_tag(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:8] if key else "server"


def explain(city: City, result: dict, candidates: list, facts: list, call_model=None,
            user_key: str | None = None, index: dict | None = None, rank: dict | None = None) -> dict:
    """Живое объяснение с ключом (из запроса или сервера), иначе банк ответов из шаблонов.
    call_model(facts, candidates, key) -> (text, model) подменяется в тестах."""
    call = call_model or call_openai
    key = resolve_key(user_key)
    tag = _key_tag((user_key or "").strip())
    cache_key = f"{city.version}|{PROMPT_VERSION}|{model_name()}|{tag}|{result['scenario_key']}"
    template = template_explanation(city, result, candidates, facts, index, rank)
    base = {"scenario_key": result["scenario_key"], "facts": facts, "rank": rank, "comparison": template["comparison"],
            "key_source": "user" if (user_key or "").strip() else ("server" if server_key() else None)}
    try:
        if not key:
            raise NotConfigured()
        cached = _cache.get(cache_key)
        if cached and cached[0] is call:  # кэш действует только для того же провайдера
            return cached[1]
        text, model = call(facts, candidates, key)
        out = {**base, "mode": "live", "model": model, "reason": None, "explanation": validate_answer(text, facts, candidates)}
        _cache[cache_key] = (call, out)
        while len(_cache) > MAX_CACHE:
            _cache.popitem(last=False)
        return out
    except NotConfigured:
        reason = "not_configured"
    except Exception as e:  # таймаут, сеть, сломанный JSON, неверная схема, выдуманные числа
        reason = type(e).__name__
    return {**base, "mode": "template", "model": None, "reason": reason,
            "explanation": {k: template[k] for k in ("summary", "strengths", "risks", "suggestions")}}


def chat(city: City, result: dict, candidates: list, facts: list, index: dict | None, rank: dict | None,
         messages: list, user_key: str | None = None, call_model=None) -> dict:
    """Диалог с советником. Без ключа возвращает mode=unavailable. Числа в ответе проверяются по фактам."""
    key = resolve_key(user_key)
    if not key:
        return {"mode": "unavailable", "reply": "Диалог с советником доступен только с ключом OpenAI: серверным или введённым в интерфейсе.", "numbers_checked": False, "model": None}
    template = template_explanation(city, result, candidates, facts, index, rank)
    top_lines = []
    if index:
        for t in index["top"][:5]:
            top_lines.append(f"{t['rank']}. Score {t['score']:.2f}, стоимость {t['cost']}: " +
                             "; ".join(f"«{city.measures[d['measure_id']].name}» ({d['measure_id']}, " + (city.district(d['district_id']).name if d.get('district_id') else "весь город") + ")" for d in t["decisions"]))
    system = (CHAT_PROMPT + "\n\nФакты о текущем плане:\n" + "\n".join(f"{f['id']}: {f['text']}" for f in facts) +
              "\n\nСравнение с лучшим планом: " + (template["comparison"] or "нет данных") +
              "\n\nЛучшие планы из полного перебора:\n" + ("\n".join(top_lines) or "нет данных"))
    trimmed = [{"role": m["role"], "content": str(m["content"])[:2000]} for m in messages[-10:] if m.get("role") in ("user", "assistant")]
    if not trimmed or trimmed[-1]["role"] != "user":
        return {"mode": "error", "reply": "Последнее сообщение должно быть от пользователя.", "numbers_checked": False, "model": None}
    call = call_model or call_openai_chat
    try:
        text, model = call(system, trimmed, key)
        if not isinstance(text, str) or not text.strip():
            return {"mode": "error", "reply": "Модель вернула пустой ответ. Расчёт и автоматический разбор работают.", "numbers_checked": False, "model": None}
    except Exception as e:
        return {"mode": "error", "reply": f"Модель недоступна: {type(e).__name__}. Расчёт и шаблонное объяснение работают.", "numbers_checked": False, "model": None}
    extra = []
    if index:
        for t in index["top"][:5]:
            extra += [t["score"], t["cost"], t["rank"]]
        extra += [index["total"], index["score_max"]]
    # Лексическая проверка: каждое число ответа есть среди чисел расчёта. Смысл утверждений она не подтверждает.
    numbers_checked = _numbers_ok(text, _allowed_numbers(facts, extra))
    return {"mode": "live", "reply": text.strip(), "numbers_checked": numbers_checked, "model": model}
