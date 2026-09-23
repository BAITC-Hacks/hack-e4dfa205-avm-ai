# План реализации бэкенда «Аким на 5 часов»

## Как запустить агента по этому плану

Человек открывает Claude Code (или другой агент) в корне репозитория и вставляет одно сообщение:

```
Прочитай docs/akim-backend-plan.md целиком и выполняй его задачи 1–9 строго по порядку, шаг за шагом.
Правила: код бери из плана как есть; тесты сначала запускай и смотри, что они падают, потом пиши код, потом запускай снова.
После каждой задачи покажи вывод pytest и спроси «коммитить?». Коммить только после моего «да» с сообщением из плана
и строкой Co-Authored-By из AGENTS.md, потом git push origin main. Папку static/ не трогай. Контракт API не меняй.
Если шаг не проходит, не иди дальше: покажи ошибку и предложи исправление в рамках плана.
```

Правила для агента, читающего этот план:

1. **Порядок.** Задачи 1–9 по порядку, внутри задачи шаги по порядку. Не начинать следующую задачу, пока тесты текущей не проходят.
2. **Код из плана.** Каждый файл в плане приведён целиком. Создавать файл ровно с этим содержимым. Отклоняться только если тест не проходит из-за ошибки в плане, тогда исправить минимально и сказать об этом человеку.
3. **Тесты сначала.** В каждой задаче: написать тест, запустить, убедиться, что падает по ожидаемой причине, написать код, запустить, убедиться, что проходит.
4. **Коммиты.** После каждой задачи спросить «коммитить?». Без «да» не коммитить. Сообщение коммита взять из шага «Коммит по разрешению». В конец сообщения добавить строку `Co-Authored-By` из `AGENTS.md`. После коммита `git push origin main`. Если push отклонён, сделать `git fetch origin` и `git merge origin/main`, никаких `rebase`, `--amend`, `push --force`.
5. **Границы.** Папка `static/` принадлежит фронтенду, не трогать. Контракт API из раздела «Контракт для фронтенда» не менять: если в коде нужно поле, которого нет в контракте, сначала добавить его в контракт в этом файле и в `docs/akim-spec.md`, сказать человеку.
6. **Секреты.** Файл `.env` не читать, не выводить, не коммитить. Ключ берётся только через `os.environ`.
7. **Отчёт после каждой задачи:** какие файлы созданы, вывод `pytest -q`, что осталось.
8. **Если застрял** на шаге дольше 15 минут: остановиться, описать проблему и два варианта решения, спросить человека.

Итоговая структура после выполнения всех задач:

```
app.py
requirements.txt
.env.example                  уже есть, не менять
data/city.json
engine/__init__.py
engine/model.py
engine/validator.py
engine/scoring.py
engine/advisor.py
engine/facts.py
engine/explain.py
tests/test_validator.py
tests/test_scoring.py
tests/test_advisor.py
tests/test_facts.py
tests/test_explain.py
tests/test_api.py
tests/test_bank.py            задача 12
engine/ranking.py             задача 11
engine/templates.py           задача 11
scripts/rank_all.py           задача 11
data/top_sets.json            задача 11, генерируется скриптом
README.md                     дополняется в задачах 9 и 12
```

Команда полной проверки в любой момент: `pytest -q`. Команда запуска сервера: `python -m uvicorn app:app --port 8000`.

> **Для агента-исполнителя.** Выполняй задачи строго по порядку, шаг за шагом, отмечая чекбоксы. Не пропускай шаги с тестами. Не меняй контракт API из раздела «Контракт» без записи в `docs/akim-spec.md`. Не трогай папку `static/`, её пишет другой человек. Коммит после каждой задачи только после явного разрешения пользователя: спроси «коммитить?» и жди ответа. Никаких `push --force`, `rebase`, `--amend`.

**Цель.** Сервер FastAPI, который по пяти решениям пользователя считает Astana Quality of Life Score по формуле ТЗ, проверяет правила, ищет улучшение заменой одной меры и даёт AI-объяснение через OpenAI с честным резервом без ключа.

**Архитектура.** Чистое расчётное ядро в `engine/` без веба. Данные в `data/city.json`. Тонкий `app.py` с пятью маршрутами. LLM получает только посчитанные факты и отвечает JSON со ссылками на них; сервер проверяет схему, ссылки и числа, при любой ошибке отдаёт шаблонное объяснение с пометкой `fallback`.

**Стек.** Python 3.11+, FastAPI, uvicorn, pydantic v2, openai, python-dotenv, pytest, httpx.

**Источники.** Условия задачи: `docs/tracks/12-akim-tz.md`. Спецификация: `docs/akim-spec.md`. Ревью, учтённое в этом плане: `docs/akim-backend-review-codex.md`.

**Соглашения.** Решение это `dict` вида `{"measure_id": "M7", "district_id": "nura"}`; у городской меры ключа `district_id` нет или он `None`. Набор это `list[dict]`. Все числа считаются во float без промежуточного округления, округляет только интерфейс. Порог критического значения строго меньше 40. Команды ниже даны для PowerShell или Git Bash из корня репозитория.

---

## Карта файлов

| Файл | Ответственность |
|---|---|
| `requirements.txt` | зависимости с версиями |
| `data/city.json` | данные задачи из ТЗ |
| `engine/__init__.py` | пустой файл пакета |
| `engine/model.py` | загрузка и проверка `city.json`, неизменяемые структуры |
| `engine/validator.py` | правила набора, коды ошибок |
| `engine/scoring.py` | формула Score, вклад мер, синергии, разложение прироста, ключ сценария |
| `engine/advisor.py` | улучшение заменой одной меры |
| `engine/facts.py` | факты для объяснения, резервное объяснение |
| `engine/explain.py` | OpenAI, строгая проверка ответа, кэш |
| `app.py` | FastAPI, маршруты, лимит тела, раздача `static/` |
| `tests/test_validator.py`, `tests/test_scoring.py`, `tests/test_advisor.py`, `tests/test_facts.py`, `tests/test_explain.py`, `tests/test_api.py` | тесты |

---

## Контракт для фронтенда

Фронтенд отправляет только идентификаторы. Все POST принимают одно тело:

```json
{"decisions": [{"measure_id": "M7", "district_id": "nura"}, {"measure_id": "M12"}]}
```

| Маршрут | Ответ |
|---|---|
| `GET /api/health` | `{"status": "ok", "dataset_version": "hackalem-12-v1", "ai_configured": true}` |
| `GET /api/city` | содержимое `data/city.json` целиком плюс поле `baseline` (см. ниже) |
| `POST /api/evaluate` | результат сценария, всегда HTTP 200 при корректной структуре тела; невалидный набор даёт `valid: false` |
| `POST /api/improvements` | `{"scenario_key": "...", "candidates": [...]}`; 422 для невалидного набора |
| `POST /api/explain` | `{"scenario_key", "mode": "live" или "fallback", "model", "reason", "explanation", "facts", "candidates"}`; 422 для невалидного набора |

Структурно неверное тело (лишнее поле, неверный тип, больше 10 решений, тело больше 16 КБ) даёт 422 или 413.

После задач 10–12 (часть 2 ниже) к контракту добавляются заголовок `X-OpenAI-Key`, маршруты `/api/top`, `/api/chat`, `/api/ai/check`, поле `rank` в `/api/evaluate` и поля `comparison`, `rank`, `key_source` в `/api/explain`; режим `fallback` переименован в `template`. Фронтенд ориентируется на итоговый контракт из части 2.

`baseline` в `/api/city`:

```json
{"score": 52.55768, "average": 56.8624, "minimum": 49.18, "critical_count": 2,
 "critical_pairs": [{"district_id": "nura", "indicator": "S1", "value": 38}, {"district_id": "nura", "indicator": "S2", "value": 35}],
 "district_scores": {"esil": 62.99, "almaty": 57.06, "saryarka": 54.65, "baikonur": 56.63, "nura": 49.18}}
```

Ответ `/api/evaluate` для допустимого набора (пример из ТЗ, числа сокращены):

```json
{"valid": true, "errors": [], "scenario_key": "M5:saryarka|M7:nura|M8:nura|M10:nura|M12",
 "decisions": [{"measure_id": "M5", "district_id": "saryarka"}, {"measure_id": "M7", "district_id": "nura"}, {"measure_id": "M8", "district_id": "nura"}, {"measure_id": "M10", "district_id": "nura"}, {"measure_id": "M12"}],
 "cost": 95, "remaining_budget": 5,
 "score": 56.54307, "baseline_score": 52.55768, "delta": 3.98539,
 "decomposition": {"avg": 0.85064, "min": 1.13475, "crit": 2.0},
 "average": 58.0776, "minimum": 52.9625, "critical_count": 0, "critical_pairs": [],
 "active_synergies": ["M10+M12"],
 "synergy_effects": [{"pair": "M10+M12", "district_id": "nura", "indicator": "B1", "bonus": 2}],
 "measure_contributions": [{"measure_id": "M7", "district_id": "nura", "realized_fraction": 0.625,
                            "effects": [{"district_id": "nura", "code": "S1", "delta": 10.0}]}],
 "district_results": [{"id": "nura", "name": "Нура", "population": 0.16, "score_before": 49.18, "score_after": 52.9625,
                       "indicators": [{"code": "S1", "name": "Школы и детсады", "before": 38, "after": 48.0, "critical": false}]}]}
```

Для невалидного набора: `valid: false`, `errors` заполнен, `scenario_key` и `decisions` заполнены, все остальные поля `null`. Ошибка:

```json
{"code": "budget_exceeded", "message": "Превышен бюджет на 21: стоимость 121 при лимите 100",
 "measure_ids": ["M3", "M13", "M5", "M7", "M12"], "decision_indexes": [0, 1, 2, 3, 4]}
```

Коды ошибок: `decision_count`, `unknown_measure`, `unknown_district`, `district_required`, `district_forbidden`, `duplicate_measure`, `direction_limit`, `incompatible_measures` (с дополнительным полем `scope`: `global` или `same_district`), `budget_exceeded`. `decision_indexes` это позиции в исходном массиве `decisions`, с нуля.

Кандидат в `/api/improvements`:

```json
{"id": "c1", "replace": {"measure_id": "M5", "district_id": "saryarka"}, "with": {"measure_id": "M13", "district_id": "almaty"},
 "decisions": [...полный новый набор из 5...], "cost": 98, "score": 57.2, "delta": 0.66,
 "decomposition": {"avg": 0.4, "min": 0.26, "crit": 0.0}, "minimum": 53.8, "critical_count": 0, "scenario_key": "..."}
```

`delta` и `decomposition` кандидата считаются относительно набора пользователя, не базы; сумма трёх слагаемых равна `delta`. Пустой список означает «улучшений заменой одной меры не найдено».

Объяснение в `/api/explain`:

```json
{"summary": "...", "strengths": [{"text": "...", "fact_ids": ["f2"]}], "risks": [{"text": "...", "fact_ids": ["f9"]}],
 "suggestions": [{"candidate_id": "c1", "text": "...", "fact_ids": ["f14"]}]}
```

`facts` это список `{"id": "f1", "kind": "score", "text": "...", "data": {...}}`. Фронт показывает ответ только если `scenario_key` совпадает с текущим набором.

---

### Задача 1. Зависимости и данные

**Файлы:** создать `requirements.txt`, `data/city.json`, `engine/__init__.py`; удалить `data/.gitkeep`, `engine/.gitkeep`.

- [ ] **Шаг 1. `requirements.txt`**

```
fastapi==0.115.0
uvicorn==0.30.6
pydantic==2.9.2
openai==1.51.0
python-dotenv==1.0.1
httpx==0.27.2
pytest==8.3.3
```

- [ ] **Шаг 2. Установить и проверить**

Команды по одной (в PowerShell 5.1 оператор `&&` не работает):
```
pip install -r requirements.txt
python -c "import fastapi, openai, pytest; print('ok')"
```
Ожидание: `ok`. Если pip не находит версию, взять ближайшую доступную и записать её в файл.

- [ ] **Шаг 3. `engine/__init__.py`**: пустой файл.

- [ ] **Шаг 4. `data/city.json`**

```json
{
  "version": "hackalem-12-v1",
  "budget": 100,
  "horizon_quarters": 8,
  "decisions_required": 5,
  "max_per_direction": 2,
  "critical_threshold": 40,
  "score_weights": {"avg": 0.7, "min": 0.3, "crit_penalty": 1.0},
  "indicator_order": ["T1","T2","E1","E2","S1","S2","B1","B2","C1","C2"],
  "indicator_weights": {"T1":0.10,"T2":0.10,"E1":0.09,"E2":0.11,"S1":0.11,"S2":0.11,"B1":0.09,"B2":0.09,"C1":0.10,"C2":0.10},
  "indicator_names": {
    "T1":"Разгрузка дорог","T2":"Доступность общественного транспорта",
    "E1":"Озеленение","E2":"Качество воздуха",
    "S1":"Школы и детсады","S2":"Поликлиники и первичная медпомощь",
    "B1":"Безопасность улиц","B2":"Безопасность дорожного движения",
    "C1":"Надёжность ЖКХ","C2":"Скорость решения обращений жителей"
  },
  "indicator_directions": {"T1":"transport","T2":"transport","E1":"ecology","E2":"ecology","S1":"social","S2":"social","B1":"safety","B2":"safety","C1":"services","C2":"services"},
  "direction_names": {"transport":"Транспорт","ecology":"Экология","social":"Соцсфера","safety":"Безопасность","services":"Сервисы"},
  "districts": [
    {"id":"esil","name":"Есиль","population":0.27,"profile":"богатый, но с пробками на мостах и переполненными школами",
     "indicators":{"T1":45,"T2":62,"E1":68,"E2":72,"S1":48,"S2":55,"B1":78,"B2":60,"C1":75,"C2":70}},
    {"id":"almaty","name":"Алматы","population":0.24,"profile":"старый ЖКХ и пробки",
     "indicators":{"T1":40,"T2":75,"E1":50,"E2":55,"S1":60,"S2":65,"B1":62,"B2":52,"C1":50,"C2":60}},
    {"id":"saryarka","name":"Сарыарка","population":0.20,"profile":"смог от частного сектора, слабое озеленение",
     "indicators":{"T1":50,"T2":70,"E1":42,"E2":40,"S1":62,"S2":68,"B1":58,"B2":55,"C1":45,"C2":55}},
    {"id":"baikonur","name":"Байконур","population":0.13,"profile":"середняк без ярких перекосов",
     "indicators":{"T1":52,"T2":68,"E1":55,"E2":50,"S1":58,"S2":60,"B1":52,"B2":58,"C1":55,"C2":58}},
    {"id":"nura","name":"Нура","population":0.16,"profile":"главный аутсайдер по соцсфере и транспорту",
     "indicators":{"T1":55,"T2":40,"E1":45,"E2":65,"S1":38,"S2":35,"B1":55,"B2":50,"C1":60,"C2":50}}
  ],
  "measures": [
    {"id":"M1","direction":"transport","name":"Выделенные полосы для автобусов","scope":"district","cost":18,"lag":2,"effects":{"T1":6,"T2":9}},
    {"id":"M2","direction":"transport","name":"Умные светофоры (адаптивное управление)","scope":"city","cost":22,"lag":2,"effects":{"T1":4,"B2":3}},
    {"id":"M3","direction":"transport","name":"Линия ЛРТ / расширение","scope":"district","cost":30,"lag":4,"effects":{"T1":16,"T2":20,"E2":4}},
    {"id":"M4","direction":"ecology","name":"Парк / сквер","scope":"district","cost":15,"lag":2,"effects":{"E1":12,"E2":3,"B1":2}},
    {"id":"M5","direction":"ecology","name":"Перевод частного сектора на чистое топливо","scope":"district","cost":25,"lag":3,"effects":{"E2":14,"C1":4}},
    {"id":"M6","direction":"ecology","name":"Городская программа озеленения и ветрозащитных полос","scope":"city","cost":20,"lag":4,"effects":{"E1":5,"E2":3}},
    {"id":"M7","direction":"social","name":"Школа + детсад (модульное строительство)","scope":"district","cost":24,"lag":3,"effects":{"S1":16}},
    {"id":"M8","direction":"social","name":"Центр семейного здоровья / поликлиника","scope":"district","cost":20,"lag":3,"effects":{"S2":14}},
    {"id":"M9","direction":"social","name":"Дворовые спорт-хабы","scope":"district","cost":10,"lag":1,"effects":{"S1":3,"S2":3,"B1":3}},
    {"id":"M10","direction":"safety","name":"Освещение и камеры (расширение Safe City)","scope":"district","cost":12,"lag":1,"effects":{"B1":12,"B2":2}},
    {"id":"M11","direction":"safety","name":"Безопасные переходы и школьные зоны","scope":"district","cost":10,"lag":1,"effects":{"B2":12,"T1":-2}},
    {"id":"M12","direction":"services","name":"Единая цифровая платформа обращений","scope":"city","cost":14,"lag":1,"effects":{"C2":5}},
    {"id":"M13","direction":"services","name":"Модернизация тепло- и водосетей","scope":"district","cost":28,"lag":4,"effects":{"C1":18,"E2":2}},
    {"id":"M14","direction":"services","name":"Аварийные бригады ЖКХ + раннее оповещение","scope":"city","cost":16,"lag":1,"effects":{"C1":5,"C2":2}}
  ],
  "synergies": [
    {"pair":["M1","M2"],"indicator":"T1","bonus":2,"district_of":"M1"},
    {"pair":["M10","M12"],"indicator":"B1","bonus":2,"district_of":"M10"},
    {"pair":["M5","M6"],"indicator":"E2","bonus":2,"district_of":"M5"}
  ],
  "conflicts": [
    {"pair":["M1","M3"],"scope":"global","reason":"либо BRT, либо ЛРТ, в любом районе"},
    {"pair":["M4","M7"],"scope":"same_district","reason":"конфликт за участок"},
    {"pair":["M5","M13"],"scope":"same_district","reason":"дублирование программы"}
  ],
  "example_scenario": [
    {"measure_id":"M7","district_id":"nura"},
    {"measure_id":"M8","district_id":"nura"},
    {"measure_id":"M10","district_id":"nura"},
    {"measure_id":"M12"},
    {"measure_id":"M5","district_id":"saryarka"}
  ]
}
```

- [ ] **Шаг 5. Проверить JSON**

Команда: `python -c "import json; d=json.load(open('data/city.json', encoding='utf-8')); print(len(d['districts']), len(d['measures']), round(sum(x['population'] for x in d['districts']),6), round(sum(d['indicator_weights'].values()),6))"`
Ожидание: `5 14 1.0 1.0`

- [ ] **Шаг 6. Коммит по разрешению.** Сообщение: `feat: данные задачи и зависимости`. Файлы: `requirements.txt data/city.json engine/__init__.py`, плюс `git rm data/.gitkeep engine/.gitkeep`.

---

### Задача 2. Модель данных с проверкой датасета

**Файлы:** создать `engine/model.py`.

- [ ] **Шаг 1. Код**

```python
# engine/model.py
from __future__ import annotations
import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "city.json"


@dataclass(frozen=True)
class Measure:
    id: str
    direction: str
    name: str
    scope: str          # "district" | "city"
    cost: int
    lag: int
    effects: MappingProxyType   # indicator -> delta


@dataclass(frozen=True)
class District:
    id: str
    name: str
    population: float
    profile: str
    indicators: MappingProxyType   # indicator -> value


@dataclass(frozen=True)
class City:
    version: str
    budget: int
    horizon: int
    decisions_required: int
    max_per_direction: int
    critical_threshold: float
    w_avg: float
    w_min: float
    crit_penalty: float
    indicator_order: tuple
    indicator_weights: MappingProxyType
    indicator_names: MappingProxyType
    direction_names: MappingProxyType
    districts: tuple          # tuple[District]
    measures: MappingProxyType  # id -> Measure
    synergies: tuple          # tuple[dict]
    conflicts: tuple          # tuple[dict]
    example_scenario: tuple
    raw: dict                 # исходный JSON только для отдачи через /api/city, не изменять

    def district(self, did: str) -> District:
        for d in self.districts:
            if d.id == did:
                return d
        raise KeyError(did)

    @property
    def district_ids(self) -> list:
        return [d.id for d in self.districts]


def _check(cond: bool, message: str) -> None:
    if not cond:
        raise ValueError(f"city.json: {message}")


def _validate_raw(raw: dict) -> None:
    order = raw["indicator_order"]
    _check(len(order) == 10 and len(set(order)) == 10, "нужно 10 уникальных показателей")
    _check(set(raw["indicator_weights"]) == set(order), "веса заданы не для всех показателей")
    _check(abs(sum(raw["indicator_weights"].values()) - 1.0) < 1e-9, "сумма весов показателей должна быть 1")
    districts = raw["districts"]
    _check(len(districts) == 5, "нужно ровно 5 районов")
    _check(len({d["id"] for d in districts}) == 5, "id районов должны быть уникальны")
    _check(abs(sum(d["population"] for d in districts) - 1.0) < 1e-9, "сумма долей населения должна быть 1")
    for d in districts:
        _check(set(d["indicators"]) == set(order), f"район {d['id']}: не все показатели заданы")
        for code, v in d["indicators"].items():
            _check(isinstance(v, (int, float)) and math.isfinite(v) and 0 <= v <= 100, f"район {d['id']}: {code} вне 0–100")
    measures = raw["measures"]
    _check(len(measures) == 14, "нужно ровно 14 мер")
    ids = [m["id"] for m in measures]
    _check(len(set(ids)) == 14, "id мер должны быть уникальны")
    directions = set(raw["direction_names"])
    for m in measures:
        _check(m["direction"] in directions, f"мера {m['id']}: неизвестное направление")
        _check(m["scope"] in ("district", "city"), f"мера {m['id']}: scope должен быть district или city")
        _check(isinstance(m["cost"], int) and m["cost"] > 0, f"мера {m['id']}: стоимость должна быть положительным целым")
        _check(isinstance(m["lag"], int) and 0 <= m["lag"] <= raw["horizon_quarters"], f"мера {m['id']}: лаг вне 0–горизонт")
        for code, v in m["effects"].items():
            _check(code in order, f"мера {m['id']}: неизвестный показатель {code}")
            _check(isinstance(v, (int, float)) and math.isfinite(v), f"мера {m['id']}: эффект {code} не число")
    for s in raw["synergies"]:
        _check(all(p in ids for p in s["pair"]) and s["district_of"] in s["pair"], "синергия ссылается на неизвестную меру")
        _check(s["indicator"] in order, "синергия ссылается на неизвестный показатель")
    for c in raw["conflicts"]:
        _check(all(p in ids for p in c["pair"]), "конфликт ссылается на неизвестную меру")
        _check(c["scope"] in ("global", "same_district"), "конфликт: scope должен быть global или same_district")


@lru_cache(maxsize=4)
def load_city(path: Path = DATA_PATH) -> City:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    _validate_raw(raw)
    districts = tuple(
        District(d["id"], d["name"], float(d["population"]), d.get("profile", ""), MappingProxyType(dict(d["indicators"])))
        for d in raw["districts"]
    )
    measures = MappingProxyType({
        m["id"]: Measure(m["id"], m["direction"], m["name"], m["scope"], int(m["cost"]), int(m["lag"]), MappingProxyType(dict(m["effects"])))
        for m in raw["measures"]
    })
    sw = raw["score_weights"]
    return City(
        version=raw["version"], budget=int(raw["budget"]), horizon=int(raw["horizon_quarters"]),
        decisions_required=int(raw["decisions_required"]), max_per_direction=int(raw["max_per_direction"]),
        critical_threshold=float(raw["critical_threshold"]),
        w_avg=float(sw["avg"]), w_min=float(sw["min"]), crit_penalty=float(sw["crit_penalty"]),
        indicator_order=tuple(raw["indicator_order"]),
        indicator_weights=MappingProxyType(dict(raw["indicator_weights"])),
        indicator_names=MappingProxyType(dict(raw["indicator_names"])),
        direction_names=MappingProxyType(dict(raw["direction_names"])),
        districts=districts, measures=measures,
        synergies=tuple(raw["synergies"]), conflicts=tuple(raw["conflicts"]),
        example_scenario=tuple(raw["example_scenario"]), raw=raw,
    )
```

- [ ] **Шаг 2. Проверить**

Команда: `python -c "from engine.model import load_city; c=load_city(); print(c.version, c.measures['M7'].cost, c.district('nura').indicators['S1'], len(c.district_ids))"`
Ожидание: `hackalem-12-v1 24 38 5`

- [ ] **Шаг 3. Проверить, что повреждённый датасет отклоняется**

Команда: `python -c "import json,tempfile,pathlib; from engine.model import load_city; d=json.load(open('data/city.json',encoding='utf-8')); d['districts'][0]['population']=0.5; p=pathlib.Path(tempfile.mkdtemp())/'bad.json'; p.write_text(json.dumps(d),encoding='utf-8'); load_city(p)"`
Ожидание: `ValueError: city.json: сумма долей населения должна быть 1`

---

### Задача 3. Валидатор

**Файлы:** создать `engine/validator.py`, `tests/test_validator.py`; удалить `tests/.gitkeep`.

Каждая ошибка: `{"code", "message", "measure_ids", "decision_indexes"}`; у `incompatible_measures` дополнительно `"scope"`.

- [ ] **Шаг 1. Тесты**

```python
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
```

- [ ] **Шаг 2. Запустить, убедиться, что падает**

Команда: `pytest tests/test_validator.py -q`
Ожидание: ошибка импорта `engine.validator`.

- [ ] **Шаг 3. Код**

```python
# engine/validator.py
from __future__ import annotations
from collections import defaultdict
from .model import City


def _err(code: str, message: str, measure_ids: list, indexes: list, **extra) -> dict:
    e = {"code": code, "message": message, "measure_ids": measure_ids, "decision_indexes": sorted(indexes)}
    e.update(extra)
    return e


def validate(city: City, decisions: list) -> list:
    """Возвращает список ошибок. Пустой список означает допустимый набор."""
    errors = []
    n = len(decisions)
    if n != city.decisions_required:
        errors.append(_err("decision_count", f"Нужно ровно {city.decisions_required} решений, передано {n}", [], list(range(n))))

    known = []  # (index, Measure, district_id or None)
    for i, d in enumerate(decisions):
        mid = d.get("measure_id")
        did = d.get("district_id") or None
        m = city.measures.get(mid)
        if m is None:
            errors.append(_err("unknown_measure", f"Неизвестная мера {mid}", [mid] if mid else [], [i]))
            continue
        if m.scope == "district":
            if not did:
                errors.append(_err("district_required", f"Для меры {mid} «{m.name}» нужно указать район", [mid], [i]))
                continue
            if did not in city.district_ids:
                errors.append(_err("unknown_district", f"Неизвестный район {did}", [mid], [i]))
                continue
        elif did:
            errors.append(_err("district_forbidden", f"Мера {mid} «{m.name}» действует на весь город, район не указывается", [mid], [i]))
            continue
        known.append((i, m, did if m.scope == "district" else None))

    positions = defaultdict(list)
    for i, m, _ in known:
        positions[m.id].append(i)
    for mid, idx in positions.items():
        if len(idx) > 1:
            errors.append(_err("duplicate_measure", f"Мера {mid} выбрана {len(idx)} раза, допускается один раз", [mid], idx))

    by_dir = defaultdict(list)
    for i, m, _ in known:
        by_dir[m.direction].append((i, m.id))
    for direction, items in by_dir.items():
        if len(items) > city.max_per_direction:
            errors.append(_err("direction_limit",
                               f"Из направления «{city.direction_names[direction]}» выбрано {len(items)} мер, допускается не более {city.max_per_direction}",
                               [mid for _, mid in items], [i for i, _ in items]))

    placement = {m.id: (i, did) for i, m, did in known}
    for c in city.conflicts:
        a, b = c["pair"]
        if a in placement and b in placement:
            ia, da = placement[a]
            ib, db = placement[b]
            if c["scope"] == "global":
                errors.append(_err("incompatible_measures", f"Меры {a} и {b} несовместимы: {c['reason']}", [a, b], [ia, ib], scope="global"))
            elif da == db:
                errors.append(_err("incompatible_measures", f"Меры {a} и {b} нельзя выбрать в одном районе: {c['reason']}", [a, b], [ia, ib], scope="same_district"))

    cost = sum(m.cost for _, m, _ in known)
    if cost > city.budget:
        errors.append(_err("budget_exceeded", f"Превышен бюджет на {cost - city.budget}: стоимость {cost} при лимите {city.budget}",
                           [m.id for _, m, _ in known], [i for i, _, _ in known]))
    return errors


def scenario_cost(city: City, decisions: list) -> int:
    return sum(city.measures[d["measure_id"]].cost for d in decisions if d.get("measure_id") in city.measures)
```

- [ ] **Шаг 4. Запустить**

Команда: `pytest tests/test_validator.py -q`
Ожидание: все 12 тестов проходят.

- [ ] **Шаг 5. Коммит по разрешению.** `feat: валидатор набора решений с кодами ошибок и индексами`

---

### Задача 4. Расчёт Score, вклад мер, разложение прироста

**Файлы:** создать `engine/scoring.py`, `tests/test_scoring.py`.

- [ ] **Шаг 1. Тесты**

```python
# tests/test_scoring.py
import copy
import pytest
from engine.model import load_city
from engine.scoring import evaluate, baseline, scenario_key, apply_effects, count_critical, aggregate

CITY = load_city()
EXAMPLE = [dict(d) for d in CITY.example_scenario]
TOL = 1e-6


def test_baseline_numbers():
    b = baseline(CITY)
    assert b["average"] == pytest.approx(56.8624, abs=TOL)
    assert b["minimum"] == pytest.approx(49.18, abs=TOL)
    assert b["critical_count"] == 2
    assert b["score"] == pytest.approx(52.55768, abs=TOL)
    per = {d["id"]: d["score_after"] for d in b["district_results"]}
    assert per["esil"] == pytest.approx(62.99, abs=TOL)
    assert per["almaty"] == pytest.approx(57.06, abs=TOL)
    assert per["saryarka"] == pytest.approx(54.65, abs=TOL)
    assert per["baikonur"] == pytest.approx(56.63, abs=TOL)
    assert per["nura"] == pytest.approx(49.18, abs=TOL)
    assert b["critical_pairs"] == [{"district_id": "nura", "indicator": "S1", "value": 38},
                                   {"district_id": "nura", "indicator": "S2", "value": 35}]


def test_example_numbers():
    r = evaluate(CITY, EXAMPLE)
    assert r["valid"] is True
    assert r["cost"] == 95 and r["remaining_budget"] == 5
    assert r["average"] == pytest.approx(58.0776, abs=TOL)
    assert r["minimum"] == pytest.approx(52.9625, abs=TOL)
    assert r["critical_count"] == 0 and r["critical_pairs"] == []
    assert r["score"] == pytest.approx(56.54307, abs=TOL)
    assert r["baseline_score"] == pytest.approx(52.55768, abs=TOL)
    assert r["delta"] == pytest.approx(3.98539, abs=TOL)
    d = r["decomposition"]
    assert d["avg"] == pytest.approx(0.85064, abs=TOL)
    assert d["min"] == pytest.approx(1.13475, abs=TOL)
    assert d["crit"] == pytest.approx(2.0, abs=TOL)
    assert d["avg"] + d["min"] + d["crit"] == pytest.approx(r["delta"], abs=TOL)
    assert r["active_synergies"] == ["M10+M12"]
    assert r["synergy_effects"] == [{"pair": "M10+M12", "district_id": "nura", "indicator": "B1", "bonus": 2}]


def test_permutation_same_result_and_key():
    a = evaluate(CITY, EXAMPLE)
    b = evaluate(CITY, list(reversed(EXAMPLE)))
    assert a["score"] == b["score"] and a["scenario_key"] == b["scenario_key"]
    assert a["decisions"] == b["decisions"]
    assert scenario_key(EXAMPLE) == "M5:saryarka|M7:nura|M8:nura|M10:nura|M12"


def test_no_mutation_and_repeatable():
    before = copy.deepcopy(CITY.raw)
    r1 = evaluate(CITY, EXAMPLE)
    r2 = evaluate(CITY, EXAMPLE)
    assert CITY.raw == before
    assert CITY.district("nura").indicators["S1"] == 38
    assert r1 == r2


def test_lag_applied_and_synergy_without_lag():
    r = evaluate(CITY, EXAMPLE)
    nura = next(d for d in r["district_results"] if d["id"] == "nura")
    ind = {i["code"]: i for i in nura["indicators"]}
    assert ind["S1"]["after"] == pytest.approx(48.0)        # 38 + 16*5/8
    assert ind["S2"]["after"] == pytest.approx(43.75)       # 35 + 14*5/8
    assert ind["B1"]["after"] == pytest.approx(67.5)        # 55 + 12*7/8 + 2 синергия без лага
    assert ind["C2"]["after"] == pytest.approx(54.375)      # 50 + 5*7/8, городская мера
    esil = next(d for d in r["district_results"] if d["id"] == "esil")
    assert {i["code"]: i for i in esil["indicators"]}["C2"]["after"] == pytest.approx(74.375)


def test_measure_contributions():
    r = evaluate(CITY, EXAMPLE)
    mc = {m["measure_id"]: m for m in r["measure_contributions"]}
    assert set(mc) == {"M7", "M8", "M10", "M12", "M5"}
    assert mc["M7"]["realized_fraction"] == pytest.approx(5 / 8)
    assert mc["M7"]["effects"] == [{"district_id": "nura", "code": "S1", "delta": pytest.approx(10.0)}]
    assert len(mc["M12"]["effects"]) == 5
    assert all(e["code"] == "C2" and e["delta"] == pytest.approx(4.375) for e in mc["M12"]["effects"])


def test_invalid_returns_nulls():
    r = evaluate(CITY, EXAMPLE[:4])
    assert r["valid"] is False and r["score"] is None and r["errors"]
    assert r["district_results"] is None and r["measure_contributions"] is None
    assert r["decisions"] is not None and r["scenario_key"]


def test_clip_after_sum_both_bounds():
    # два эффекта в одной ячейке: 99 + 4*6/8 − 2*7/8 = 100.25 → 100. Clip после каждого шага дал бы 98.25
    ind = apply_effects(CITY, [{"measure_id": "M2"}, {"measure_id": "M11", "district_id": "esil"}], base={"esil": {"T1": 99.0}})
    assert ind["esil"]["T1"] == 100
    # нижняя граница: 1 − 1.75 → 0
    ind = apply_effects(CITY, [{"measure_id": "M11", "district_id": "esil"}], base={"esil": {"T1": 1.0}})
    assert ind["esil"]["T1"] == 0


def test_critical_threshold_is_strict():
    assert count_critical(CITY, {"x": {"T1": 39.999}}) == 1
    assert count_critical(CITY, {"x": {"T1": 40.0}}) == 0


def test_minimum_follows_weakest_district_not_nura():
    base = {d.id: dict(d.indicators) for d in CITY.districts}
    base["esil"] = {c: 41.0 for c in CITY.indicator_order}
    agg = aggregate(CITY, apply_effects(CITY, [], base=base))
    assert agg["minimum"] == pytest.approx(41.0)
    assert min(agg["per"], key=agg["per"].get) == "esil"
```

- [ ] **Шаг 2. Запустить, убедиться, что падает**

Команда: `pytest tests/test_scoring.py -q`
Ожидание: ошибка импорта `engine.scoring`.

- [ ] **Шаг 3. Код**

```python
# engine/scoring.py
from __future__ import annotations
from .model import City
from .validator import validate


def normalize(decisions: list) -> list:
    """Нормализованный набор: без district_id у городских мер, отсортирован по номеру меры."""
    out = []
    for d in decisions:
        mid = d.get("measure_id", "")
        did = d.get("district_id") or None
        out.append({"measure_id": mid, "district_id": did} if did else {"measure_id": mid})
    return sorted(out, key=lambda x: (_measure_number(x["measure_id"]), x.get("district_id") or ""))


def _measure_number(mid: str) -> int:
    return int(mid[1:]) if mid[1:].isdigit() else 999


def scenario_key(decisions: list) -> str:
    parts = []
    for d in normalize(decisions):
        parts.append(f"{d['measure_id']}:{d['district_id']}" if d.get("district_id") else d["measure_id"])
    return "|".join(parts)


def _lag_factor(city: City, lag: int) -> float:
    return (city.horizon - lag) / city.horizon


def apply_effects(city: City, decisions: list, base: dict | None = None) -> dict:
    """{district_id: {indicator: value}} после эффектов с лагом, синергий и обрезки 0–100.
    Обрезка выполняется один раз после суммирования, поэтому порядок мер не влияет."""
    if base is None:
        ind = {d.id: {c: float(v) for c, v in d.indicators.items()} for d in city.districts}
    else:
        ind = {k: {c: float(v) for c, v in v_.items()} for k, v_ in base.items()}
    placement = {}
    for d in decisions:
        m = city.measures[d["measure_id"]]
        did = d.get("district_id") or None
        placement[m.id] = did
        targets = [did] if m.scope == "district" else list(ind.keys())
        f = _lag_factor(city, m.lag)
        for t in targets:
            for code, delta in m.effects.items():
                if code in ind[t]:
                    ind[t][code] += delta * f
    for s in city.synergies:
        a, b = s["pair"]
        if a in placement and b in placement:
            t = placement[s["district_of"]]
            if t is not None and t in ind and s["indicator"] in ind[t]:
                ind[t][s["indicator"]] += s["bonus"]
    for t in ind:
        for code in ind[t]:
            ind[t][code] = max(0.0, min(100.0, ind[t][code]))
    return ind


def district_score(city: City, values: dict) -> float:
    return sum(city.indicator_weights[c] * values[c] for c in city.indicator_order if c in values)


def count_critical(city: City, ind: dict) -> int:
    return sum(1 for t in ind for c in ind[t] if ind[t][c] < city.critical_threshold)


def aggregate(city: City, ind: dict) -> dict:
    per = {t: district_score(city, ind[t]) for t in ind}
    pops = {d.id: d.population for d in city.districts}
    avg = sum(pops.get(t, 0.0) * per[t] for t in per)
    mn = min(per.values())
    crit = count_critical(city, ind)
    score = city.w_avg * avg + city.w_min * mn - city.crit_penalty * crit
    return {"per": per, "average": avg, "minimum": mn, "critical_count": crit, "score": score, "ind": ind}


def critical_pairs(city: City, ind: dict) -> list:
    return [{"district_id": t, "indicator": c, "value": ind[t][c]}
            for t in ind for c in city.indicator_order if c in ind[t] and ind[t][c] < city.critical_threshold]


def active_synergies(city: City, decisions: list) -> list:
    ids = {d["measure_id"] for d in decisions}
    return [f"{a}+{b}" for a, b in (s["pair"] for s in city.synergies) if a in ids and b in ids]


def synergy_effects(city: City, decisions: list) -> list:
    placement = {d["measure_id"]: d.get("district_id") or None for d in decisions}
    out = []
    for s in city.synergies:
        a, b = s["pair"]
        if a in placement and b in placement:
            out.append({"pair": f"{a}+{b}", "district_id": placement[s["district_of"]],
                        "indicator": s["indicator"], "bonus": s["bonus"]})
    return out


def measure_contributions(city: City, decisions: list) -> list:
    """Вклад каждой меры в показатели с учётом лага, до обрезки 0–100."""
    out = []
    for d in decisions:
        m = city.measures[d["measure_id"]]
        did = d.get("district_id") or None
        f = _lag_factor(city, m.lag)
        targets = [did] if m.scope == "district" else city.district_ids
        effects = [{"district_id": t, "code": c, "delta": delta * f} for t in targets for c, delta in m.effects.items()]
        out.append({"measure_id": m.id, "district_id": did, "realized_fraction": f, "effects": effects})
    return out


def _district_results(city: City, base_ind: dict, base_per: dict, agg: dict) -> list:
    out = []
    for d in city.districts:
        rows = []
        for c in city.indicator_order:
            after = agg["ind"][d.id][c]
            rows.append({"code": c, "name": city.indicator_names[c], "before": base_ind[d.id][c],
                         "after": after, "critical": after < city.critical_threshold})
        out.append({"id": d.id, "name": d.name, "population": d.population,
                    "score_before": base_per[d.id], "score_after": agg["per"][d.id], "indicators": rows})
    return out


def baseline(city: City) -> dict:
    ind = apply_effects(city, [])
    agg = aggregate(city, ind)
    return {"score": agg["score"], "average": agg["average"], "minimum": agg["minimum"],
            "critical_count": agg["critical_count"], "critical_pairs": critical_pairs(city, ind),
            "district_scores": dict(agg["per"]),
            "district_results": _district_results(city, ind, agg["per"], agg)}


NULL_FIELDS = ("cost", "remaining_budget", "score", "baseline_score", "delta", "decomposition",
               "average", "minimum", "critical_count", "critical_pairs", "active_synergies",
               "synergy_effects", "measure_contributions", "district_results")


def evaluate(city: City, decisions: list) -> dict:
    errors = validate(city, decisions)
    key = scenario_key(decisions)
    norm = normalize(decisions)
    if errors:
        return {"valid": False, "errors": errors, "scenario_key": key, "decisions": norm, **{k: None for k in NULL_FIELDS}}
    base_ind = apply_effects(city, [])
    base_agg = aggregate(city, base_ind)
    ind = apply_effects(city, norm)
    agg = aggregate(city, ind)
    cost = sum(city.measures[d["measure_id"]].cost for d in norm)
    decomposition = {
        "avg": city.w_avg * (agg["average"] - base_agg["average"]),
        "min": city.w_min * (agg["minimum"] - base_agg["minimum"]),
        "crit": city.crit_penalty * (base_agg["critical_count"] - agg["critical_count"]),
    }
    return {
        "valid": True, "errors": [], "scenario_key": key, "decisions": norm,
        "cost": cost, "remaining_budget": city.budget - cost,
        "score": agg["score"], "baseline_score": base_agg["score"], "delta": agg["score"] - base_agg["score"],
        "decomposition": decomposition, "average": agg["average"], "minimum": agg["minimum"],
        "critical_count": agg["critical_count"], "critical_pairs": critical_pairs(city, ind),
        "active_synergies": active_synergies(city, norm),
        "synergy_effects": synergy_effects(city, norm),
        "measure_contributions": measure_contributions(city, norm),
        "district_results": _district_results(city, base_ind, base_agg["per"], agg),
    }
```

- [ ] **Шаг 4. Запустить**

Команда: `pytest tests/test_scoring.py tests/test_validator.py -q`
Ожидание: все тесты проходят. Если `test_example_numbers` даёт другое число, сверить по шагам: Нура S1 48, S2 43.75, B1 67.5, B2 51.75, C2 54.375; Сарыарка E2 48.75, C1 47.5; D_nura 52.9625; D_avg 58.0776.

- [ ] **Шаг 5. Коммит по разрешению.** `feat: формула Score, вклад мер, разложение прироста, контрольные тесты`

---

### Задача 5. Советник: улучшение заменой одной меры

**Файлы:** создать `engine/advisor.py`, `tests/test_advisor.py`.

- [ ] **Шаг 1. Тесты**

```python
# tests/test_advisor.py
import pytest
from engine.model import load_city
from engine.scoring import evaluate, scenario_key
from engine.advisor import find_improvements
from engine.validator import validate

CITY = load_city()
EXAMPLE = [dict(d) for d in CITY.example_scenario]


def test_candidates_valid_better_and_decomposed_from_user_set():
    base = evaluate(CITY, EXAMPLE)
    cands = find_improvements(CITY, EXAMPLE)
    assert 0 < len(cands) <= 3
    keys = set()
    for n, c in enumerate(cands, 1):
        assert c["id"] == f"c{n}"
        assert validate(CITY, c["decisions"]) == []
        checked = evaluate(CITY, c["decisions"])
        assert c["score"] == checked["score"]
        assert c["score"] > base["score"] + 1e-8
        assert c["delta"] == pytest.approx(checked["score"] - base["score"], abs=1e-9)
        d = c["decomposition"]
        assert d["avg"] + d["min"] + d["crit"] == pytest.approx(c["delta"], abs=1e-9)
        assert c["scenario_key"] == scenario_key(c["decisions"])
        keys.add(c["scenario_key"])
    assert len(keys) == len(cands)
    assert [c["score"] for c in cands] == sorted((c["score"] for c in cands), reverse=True)


def test_candidate_is_single_replacement():
    c = find_improvements(CITY, EXAMPLE)[0]
    orig = set(scenario_key(EXAMPLE).split("|"))
    new = set(c["scenario_key"].split("|"))
    assert len(orig - new) == 1 and len(new - orig) == 1
    assert c["replace"]["measure_id"] in {d["measure_id"] for d in EXAMPLE}


def test_deterministic_on_permutation():
    a = find_improvements(CITY, EXAMPLE)
    b = find_improvements(CITY, list(reversed(EXAMPLE)))
    assert [c["scenario_key"] for c in a] == [c["scenario_key"] for c in b]


def test_invalid_input_returns_empty():
    assert find_improvements(CITY, EXAMPLE[:4]) == []
```

- [ ] **Шаг 2. Запустить, убедиться, что падает**

Команда: `pytest tests/test_advisor.py -q`

- [ ] **Шаг 3. Код**

```python
# engine/advisor.py
from __future__ import annotations
from .model import City
from .scoring import evaluate, scenario_key, normalize
from .validator import validate

EPS = 1e-8


def _placements(city: City, m) -> list:
    if m.scope == "city":
        return [{"measure_id": m.id}]
    return [{"measure_id": m.id, "district_id": did} for did in city.district_ids]


def find_improvements(city: City, decisions: list, limit: int = 3) -> list:
    """Замена одной меры на любую меру с любым допустимым районом, включая перенос той же меры.
    Возвращает до limit строгих улучшений. delta и decomposition относительно набора пользователя."""
    if validate(city, decisions):
        return []
    decisions = normalize(decisions)
    orig = evaluate(city, decisions)
    seen = {orig["scenario_key"]}
    found = []
    for i, old in enumerate(decisions):
        for m in city.measures.values():
            for new in _placements(city, m):
                cand = decisions[:i] + [new] + decisions[i + 1:]
                key = scenario_key(cand)
                if key in seen:
                    continue
                seen.add(key)
                if validate(city, cand):
                    continue
                r = evaluate(city, cand)
                if r["score"] > orig["score"] + EPS:
                    found.append({
                        "replace": dict(old), "with": dict(new), "decisions": r["decisions"],
                        "cost": r["cost"], "score": r["score"], "delta": r["score"] - orig["score"],
                        "decomposition": {k: r["decomposition"][k] - orig["decomposition"][k] for k in ("avg", "min", "crit")},
                        "minimum": r["minimum"], "critical_count": r["critical_count"], "scenario_key": key,
                    })
    found.sort(key=lambda c: (-c["score"], c["cost"], c["scenario_key"]))
    out = found[:limit]
    for n, c in enumerate(out, 1):
        c["id"] = f"c{n}"
    return out
```

- [ ] **Шаг 4. Запустить**

Команда: `pytest tests/test_advisor.py -q`
Ожидание: 4 теста проходят, время меньше 3 секунд.

- [ ] **Шаг 5. Коммит по разрешению.** `feat: советник, улучшение заменой одной меры`

---

### Задача 6. Факты и резервное объяснение

**Файлы:** создать `engine/facts.py`, `tests/test_facts.py`.

Факт: `{"id": "f1", "kind": "...", "text": "...", "data": {...}}`. Виды: `plan`, `score`, `decomposition`, `worst_district`, `measure`, `synergy`, `district`, `district_unchanged`, `critical`, `no_critical`, `candidate`, `no_candidates`. Резервное объяснение строится правилами из фактов, ничего не выдумывает.

Правила резерва:
- `summary`: текст факта `score` плюс текст факта `worst_district`.
- `strengths`: факт `decomposition`; до двух фактов `district` с наибольшим ростом оценки; факт `no_critical`, если есть; факт `synergy`, если есть.
- `risks` в порядке приоритета: `critical` (остались критические показатели); `measure` с отрицательным эффектом; `district_unchanged` (районы, которых решения не коснулись); `measure` с `realized_fraction` не выше 0.625 (лаг 3 и больше, реализована только часть эффекта); если ничего из этого нет, факт `worst_district` с пояснением, что район остаётся слабейшим. Не более четырёх пунктов.
- `suggestions`: по одному на факт `candidate`.

- [ ] **Шаг 1. Тесты**

```python
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
```

- [ ] **Шаг 2. Запустить, убедиться, что падает**

Команда: `pytest tests/test_facts.py -q`

- [ ] **Шаг 3. Код**

```python
# engine/facts.py
from __future__ import annotations
from .model import City


def _r(x: float, n: int = 2) -> str:
    return f"{x:.{n}f}".replace(".", ",")


def _sgn(x: float, n: int = 1) -> str:
    return ("+" if x >= 0 else "") + _r(x, n)


def _where(city: City, did) -> str:
    return city.district(did).name if did else "весь город"


def build_facts(city: City, result: dict, candidates: list) -> list:
    facts = []

    def add(kind: str, text: str, data: dict | None = None) -> None:
        facts.append({"id": f"f{len(facts) + 1}", "kind": kind, "text": text, "data": data or {}})

    decisions = result["decisions"]
    names = [f"{city.measures[d['measure_id']].id} «{city.measures[d['measure_id']].name}» ({_where(city, d.get('district_id'))}, "
             f"{city.measures[d['measure_id']].cost} ед.)" for d in decisions]
    add("plan", "Выбранные меры: " + "; ".join(names) + f". Стоимость {result['cost']} из {city.budget}, остаток {result['remaining_budget']}.",
        {"cost": result["cost"], "remaining_budget": result["remaining_budget"], "budget": city.budget})
    add("score", f"Score {_r(result['score'])} против базы {_r(result['baseline_score'])}, прирост {_sgn(result['delta'], 2)}.",
        {"score": result["score"], "baseline_score": result["baseline_score"], "delta": result["delta"]})
    dc = result["decomposition"]
    add("decomposition",
        f"Разложение прироста: средний результат города {_sgn(dc['avg'], 2)}, слабейший район {_sgn(dc['min'], 2)}, "
        f"снятый штраф за критические значения {_sgn(dc['crit'], 2)}.", dict(dc))
    worst = min(result["district_results"], key=lambda d: d["score_after"])
    add("worst_district",
        f"Слабейший район после решений: {worst['name']}, оценка {_r(worst['score_after'])} (было {_r(worst['score_before'])}).",
        {"district_id": worst["id"], "score_after": worst["score_after"], "score_before": worst["score_before"]})

    for mc in result["measure_contributions"]:
        m = city.measures[mc["measure_id"]]
        if m.scope == "district":
            eff = ", ".join(f"{e['code']} {_sgn(e['delta'])}" for e in mc["effects"])
        else:
            first = mc["effects"][0]["district_id"]
            eff = "в каждом районе " + ", ".join(f"{e['code']} {_sgn(e['delta'])}" for e in mc["effects"] if e["district_id"] == first)
        pct = int(round(mc["realized_fraction"] * 100))
        add("measure",
            f"{m.id} «{m.name}» ({_where(city, mc['district_id'])}): лаг {m.lag} кв., реализовано {pct}% полного эффекта за горизонт; {eff}.",
            {"measure_id": m.id, "district_id": mc["district_id"], "lag": m.lag, "realized_fraction": mc["realized_fraction"],
             "effects": mc["effects"], "has_negative": any(e["delta"] < 0 for e in mc["effects"])})

    for s in result["synergy_effects"]:
        add("synergy", f"Синергия {s['pair']}: {s['indicator']} +{s['bonus']} в районе {_where(city, s['district_id'])}, без лага.", dict(s))

    for d in result["district_results"]:
        changed = [i for i in d["indicators"] if abs(i["after"] - i["before"]) > 1e-9]
        if changed:
            txt = ", ".join(f"{i['code']} {_r(i['before'], 1)}→{_r(i['after'], 1)}" for i in changed)
            add("district", f"{d['name']}: оценка {_r(d['score_before'])}→{_r(d['score_after'])}; изменились {txt}.",
                {"district_id": d["id"], "score_before": d["score_before"], "score_after": d["score_after"],
                 "gain": d["score_after"] - d["score_before"]})
        else:
            low = [i for i in d["indicators"] if i["after"] < 50]
            lows = (", самые низкие: " + ", ".join(f"{i['code']} {_r(i['after'], 0)}" for i in low)) if low else ""
            add("district_unchanged", f"{d['name']}: решения района не коснулись, оценка {_r(d['score_after'])}{lows}.",
                {"district_id": d["id"], "score_after": d["score_after"], "gain": 0.0})

    if result["critical_pairs"]:
        pairs = ", ".join(f"{_where(city, p['district_id'])} {p['indicator']} {_r(p['value'], 1)}" for p in result["critical_pairs"])
        add("critical", f"Критические показатели ниже {int(city.critical_threshold)} остались: {pairs}. Штраф 1 балл за каждый.",
            {"pairs": result["critical_pairs"], "count": len(result["critical_pairs"])})
    else:
        add("no_critical", f"Критических показателей ниже {int(city.critical_threshold)} не осталось.", {"count": 0})

    if candidates:
        for c in candidates:
            a, b = c["replace"], c["with"]
            add("candidate",
                f"Альтернатива {c['id']}: заменить {a['measure_id']} ({_where(city, a.get('district_id'))}) на {b['measure_id']} "
                f"({_where(city, b.get('district_id'))}); стоимость {c['cost']}, Score {_r(c['score'])}, прирост {_sgn(c['delta'], 2)} к текущему набору.",
                {"candidate_id": c["id"], "cost": c["cost"], "score": c["score"], "delta": c["delta"]})
    else:
        add("no_candidates", "Улучшений заменой одной меры не найдено.", {})
    return facts


def fallback_explanation(facts: list, candidates: list) -> dict:
    def of(kind):
        return [f for f in facts if f["kind"] == kind]

    def item(f):
        return {"text": f["text"], "fact_ids": [f["id"]]}

    score = of("score")[0]
    worst = of("worst_district")[0]
    strengths = [item(of("decomposition")[0])]
    grown = sorted(of("district"), key=lambda f: -f["data"]["gain"])[:2]
    strengths += [item(f) for f in grown]
    strengths += [item(f) for f in of("no_critical")]
    strengths += [item(f) for f in of("synergy")]

    risks = [item(f) for f in of("critical")]
    risks += [item(f) for f in of("measure") if f["data"]["has_negative"]]
    risks += [item(f) for f in of("district_unchanged")]
    risks += [item(f) for f in of("measure") if f["data"]["realized_fraction"] <= 0.625 and not f["data"]["has_negative"]]
    if not risks:
        risks = [{"text": worst["text"] + " Район остаётся слабейшим, его показатели ограничивают итог.", "fact_ids": [worst["id"]]}]
    risks = risks[:4]

    suggestions = []
    for f in of("candidate"):
        suggestions.append({"candidate_id": f["data"]["candidate_id"], "text": f["text"], "fact_ids": [f["id"]]})
    return {"summary": score["text"] + " " + worst["text"], "strengths": strengths[:5], "risks": risks, "suggestions": suggestions}
```

- [ ] **Шаг 4. Запустить**

Команда: `pytest tests/test_facts.py -q`
Ожидание: 4 теста проходят.

- [ ] **Шаг 5. Коммит по разрешению.** `feat: факты для объяснения и резервное объяснение по правилам`

---

### Задача 7. AI-объяснение через OpenAI со строгой проверкой

**Файлы:** создать `engine/explain.py`, `tests/test_explain.py`.

Правила проверки ответа модели: JSON-объект с ровно четырьмя ключами `summary`, `strengths`, `risks`, `suggestions`; `strengths` и `risks` непустые списки; у каждого утверждения непустой `text` и непустой `fact_ids` из существующих фактов; у предложения `candidate_id` из переданных, без повторов; любое число в тексте либо целое от 0 до 14, либо совпадает с числом из фактов с допуском 0.051. Любое нарушение даёт `fallback`. Функция вызова модели передаётся параметром, чтобы тесты не ходили в сеть.

- [ ] **Шаг 1. Тесты**

```python
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
    assert out["mode"] == "fallback" and out["reason"] == "not_configured" and calls == []
    assert out["explanation"]["summary"] and out["explanation"]["risks"]


def test_broken_json_is_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    ex.clear_cache()
    r, c, f = _prep()
    out = ex.explain(CITY, r, c, f, call_model=lambda *a: ("{not json", "m"))
    assert out["mode"] == "fallback" and out["reason"] == "JSONDecodeError"


def test_unknown_fact_or_candidate_is_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    r, c, f = _prep()
    bad_fact = json.dumps({"summary": "x", "strengths": [{"text": "y", "fact_ids": ["f999"]}],
                           "risks": [{"text": "z", "fact_ids": ["f1"]}], "suggestions": []})
    ex.clear_cache()
    assert ex.explain(CITY, r, c, f, call_model=lambda *a: (bad_fact, "m"))["mode"] == "fallback"
    bad_cand = json.dumps({"summary": "x", "strengths": [{"text": "y", "fact_ids": ["f1"]}],
                           "risks": [{"text": "z", "fact_ids": ["f1"]}], "suggestions": [{"candidate_id": "c9", "text": "t", "fact_ids": ["f1"]}]})
    ex.clear_cache()
    assert ex.explain(CITY, r, c, f, call_model=lambda *a: (bad_cand, "m"))["mode"] == "fallback"


def test_invented_number_or_missing_section_is_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    r, c, f = _prep()
    invented = json.dumps({"summary": "Score 999 при бюджете 10000", "strengths": [{"text": "y", "fact_ids": ["f1"]}],
                           "risks": [{"text": "z", "fact_ids": ["f1"]}], "suggestions": []})
    ex.clear_cache()
    assert ex.explain(CITY, r, c, f, call_model=lambda *a: (invented, "m"))["mode"] == "fallback"
    no_risks = json.dumps({"summary": "x", "strengths": [{"text": "y", "fact_ids": ["f1"]}], "risks": [], "suggestions": []})
    ex.clear_cache()
    assert ex.explain(CITY, r, c, f, call_model=lambda *a: (no_risks, "m"))["mode"] == "fallback"
    only_summary = json.dumps({"summary": "x"})
    ex.clear_cache()
    assert ex.explain(CITY, r, c, f, call_model=lambda *a: (only_summary, "m"))["mode"] == "fallback"


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
    assert ex.explain(CITY, r, c, f, call_model=flaky)["mode"] == "fallback"
    assert ex.explain(CITY, r, c, f, call_model=flaky)["mode"] == "live"
```

- [ ] **Шаг 2. Запустить, убедиться, что падает**

Команда: `pytest tests/test_explain.py -q`

- [ ] **Шаг 3. Код**

```python
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
```

- [ ] **Шаг 4. Запустить**

Команда: `pytest tests/test_explain.py -q`
Ожидание: 7 тестов проходят.

- [ ] **Шаг 5. Живой запрос с ключом из `.env`**

Команда: `python -c "from dotenv import load_dotenv; load_dotenv(); from engine.model import load_city; from engine.scoring import evaluate; from engine.advisor import find_improvements; from engine.facts import build_facts; from engine.explain import explain; c=load_city(); s=list(c.example_scenario); r=evaluate(c,s); k=find_improvements(c,s); o=explain(c,r,k,build_facts(c,r,k)); print(o['mode'], o['model'], o['reason']); print(o['explanation']['summary']); print(len(o['explanation']['strengths']), len(o['explanation']['risks']), len(o['explanation']['suggestions']))"`
Ожидание: `live gpt-4o-mini None`, осмысленное резюме, счётчики не нулевые. Если `fallback` с `reason` `invented number` повторяется три раза подряд, ослабить проверку чисел: допуск 0.51 вместо 0.051, и записать это в README. Если `reason` `AuthenticationError`, проверить ключ в `.env`.

- [ ] **Шаг 6. Коммит по разрешению.** `feat: AI-объяснение с проверкой схемы, ссылок и чисел, резерв`

---

### Задача 8. Сервер FastAPI

**Файлы:** создать `app.py`, `tests/test_api.py`.

- [ ] **Шаг 1. Тесты**

```python
# tests/test_api.py
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
    assert j["mode"] == "fallback" and j["reason"] == "not_configured"
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
```

- [ ] **Шаг 2. Запустить, убедиться, что падает**

Команда: `pytest tests/test_api.py -q`

- [ ] **Шаг 3. Код**

```python
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
```

Примечание для исполнителя: `BaseHTTPMiddleware` в Starlette кэширует прочитанное тело, поэтому маршрут после `await request.body()` получает то же тело. Если `test_body_limit` возвращает 422 вместо 413, значит middleware не подключился: проверить, что `add_middleware` вызван до объявления маршрутов.

- [ ] **Шаг 4. Запустить тесты и сервер**

Команда: `pytest -q`
Ожидание: все тесты проходят.
Команда: `python -m uvicorn app:app --port 8000`, в другом терминале `curl -s localhost:8000/api/health`
Ожидание: `{"status":"ok","dataset_version":"hackalem-12-v1","ai_configured":true}` при заполненном `.env`.
Команда: `curl -s -X POST localhost:8000/api/explain -H "Content-Type: application/json" -d "{\"decisions\":[{\"measure_id\":\"M7\",\"district_id\":\"nura\"},{\"measure_id\":\"M8\",\"district_id\":\"nura\"},{\"measure_id\":\"M10\",\"district_id\":\"nura\"},{\"measure_id\":\"M12\"},{\"measure_id\":\"M5\",\"district_id\":\"saryarka\"}]}"`
Ожидание: JSON с `"mode":"live"`.

- [ ] **Шаг 5. Коммит по разрешению.** `feat: FastAPI сервер, маршруты city, evaluate, improvements, explain, лимит тела`

---

### Задача 9. README, соответствие ТЗ, чистый запуск

**Файлы:** изменить `README.md` (разделы «Запуск», «Проверка основного сценария», «Соответствие требованиям ТЗ», «Сторонние материалы»), `.gitignore` (добавить `.venv/` и `.clean-check/`).

- [ ] **Шаг 1. Проверить, что в `.gitignore` есть строки ниже, иначе добавить**

```
# Виртуальные окружения и проверка чистого запуска
.venv/
.clean-check/
```

- [ ] **Шаг 2. Заполнить таблицу соответствия в README**

| Требование ТЗ | Где реализовано | Как проверить |
|---|---|---|
| Единый виртуальный бюджет | `data/city.json`, поле `budget = 100`; `GET /api/city` | `curl localhost:8000/api/city` показывает `"budget": 100`, значение одинаково для всех |
| Решения по 5 направлениям | каталог мер в `data/city.json`, вкладки в `static/` | В интерфейсе пять вкладок, мера любого направления выбирается |
| Контроль превышения бюджета | `engine/validator.py`, код `budget_exceeded` | `POST /api/evaluate` с набором на 121 ед. возвращает `valid: false` и причину; интерфейс не даёт добавить |
| AI-анализ принятых решений | `engine/explain.py`, `POST /api/explain` | С ключом ответ `mode: live`; без ключа `mode: fallback` с пометкой в интерфейсе |
| Расчёт Astana Quality of Life Score | `engine/scoring.py`, `tests/test_scoring.py` | `pytest tests/test_scoring.py`: база 52,55768, пример 56,54307 |
| Объяснение сильных сторон, рисков, последствий | `engine/facts.py`, `engine/explain.py` | Панель советника: резюме, сильные стороны, риски, альтернативы |
| Критерий 1: одинаковый старт | `data/city.json` версии `hackalem-12-v1`, проверка при загрузке | `GET /api/health` показывает версию |
| Критерий 3: решения влияют на показатели | `district_results`, `measure_contributions` в `/api/evaluate` | В ответе `before` и `after` по каждому показателю |
| Критерий 5: смена набора меняет Score | пересчёт на каждый запрос, `scenario_key` | Заменить одну меру, Score и ключ меняются |

- [ ] **Шаг 3. Раздел «Сторонние материалы»**

FastAPI (MIT), uvicorn (BSD-3), pydantic (MIT), openai-python (Apache 2.0), python-dotenv (BSD-3), httpx (BSD-3), pytest (MIT). Данные районов, мер и формула предоставлены организатором в условиях трека 12. Собственный код создан в ходе соревновательной части с использованием AI-инструментов.

- [ ] **Шаг 4. Чистый запуск внутри репозитория**

Проверяется текущая версия файлов, предназначенных к сдаче, в новом окружении, без личного `.env`. Команды PowerShell из корня репозитория:

```
Remove-Item -Recurse -Force .clean-check -ErrorAction SilentlyContinue
New-Item -ItemType Directory .clean-check | Out-Null
git ls-files -co --exclude-standard | Out-File -Encoding utf8 .clean-check\files.txt
tar -cf .clean-check\src.tar -T .clean-check\files.txt
tar -xf .clean-check\src.tar -C .clean-check
Set-Location .clean-check
python -m venv .venv
.\.venv\Scripts\Activate.ps1
$env:OPENAI_API_KEY = ""
pip install -r requirements.txt
pytest -q
python -m uvicorn app:app --port 8001
```

Ожидание: тесты проходят; `http://localhost:8001` открывает страницу; `http://localhost:8001/api/health` отвечает `ai_configured: false`; `POST /api/evaluate` примера даёт 56,54; `POST /api/explain` даёт `mode: fallback`. Записать в README строку «Чистый запуск проверен: Windows 11, Python 3.12, 23.09.2026, режим без ключа». Остановить сервер, `Set-Location ..`, `Remove-Item -Recurse -Force .clean-check`.

- [ ] **Шаг 5. Проверить перед коммитом**

Команды: `git status --short`, `git diff --check`, `git grep -n "sk-" -- . ":!*.md"` (ожидание: ничего не найдено).

- [ ] **Шаг 6. Коммит по разрешению.** `docs: README, соответствие ТЗ, лицензии, проверка чистого запуска`

---







---

## Часть 2. Советник: ранжирование, банк ответов, ключ из интерфейса, диалог

Задачи 10–12 выполняются строго после задачи 8, параллельно с README из задачи 9 нельзя: обе меняют README. Весь код ниже проверен в отдельном окружении: 57 тестов проходят, живой режим и диалог проверены с реальным ключом. Файлы `engine/explain.py` и `app.py` в этих задачах **заменяются целиком** новыми версиями, а не правятся по кусочкам.

### Что добавляется к контракту для фронтенда

- Заголовок `X-OpenAI-Key` у `POST /api/explain`, `POST /api/chat`, `POST /api/ai/check`: ключ пользователя из интерфейса. Приоритет над серверным ключом. Сервер его не хранит и не логирует. Фронт держит ключ в `sessionStorage`.
- `GET /api/health` дополнительно: `ranking_available`, `total_plans`.
- `GET /api/top?limit=5`: `{"total": 694395, "score_max": 57.23673, "top": [{"rank": 1, "score": 57.23673, "cost": 98, "scenario_key": "...", "decisions": [...], "minimum": ..., "critical_count": ...}]}`.
- `POST /api/evaluate` дополнительно: `rank`: `{"percentile": 99.9, "total": 694395, "top_position": null, "best_score": 57.23673, "gap_to_best": 0.69}` или `null` для невалидного набора.
- `POST /api/explain`: `mode` теперь `live` или `template` (вместо `fallback`); дополнительно `comparison` (строка сравнения с лучшим планом или `null`), `rank`, `key_source` (`user`, `server` или `null`).
- `POST /api/chat`, тело `{"decisions": [...], "messages": [{"role": "user", "content": "..."}]}` (роли `user` и `assistant`, до 20 сообщений, последнее от пользователя): ответ `{"mode": "live" | "unavailable" | "error", "reply": "...", "numbers_checked": true, "model": "gpt-4o-mini"}`. `numbers_checked` это лексическая проверка: каждое число ответа встречается среди чисел расчёта и топа планов. Смысл утверждений она не подтверждает; при `false` фронт показывает пометку «числа не сверены с расчётом».
- `POST /api/ai/check` без тела: `{"ok": true, "model": "gpt-4o-mini", "key_source": "user"}` или `{"ok": false, "error": "AuthenticationError", "key_source": ...}`.

### Задача 10. Укрепление ядра по ревью

**Файлы:** изменить `engine/scoring.py`, `engine/validator.py`, `tests/test_scoring.py`, `tests/test_validator.py`.

- [ ] **Шаг 1. Тесты.** Дописать в конец `tests/test_scoring.py`:

```python
def test_null_measure_id_is_error_not_crash():
    r = evaluate(CITY, [{"measure_id": None}] + EXAMPLE[1:])
    assert r["valid"] is False and any(e["code"] == "unknown_measure" for e in r["errors"])
    r = evaluate(CITY, ["M7"] + EXAMPLE[1:])
    assert r["valid"] is False and any(e["code"] == "unknown_measure" for e in r["errors"])
```

и в конец `tests/test_validator.py`:

```python
def test_duplicates_counted_even_when_rows_invalid():
    s = [{"measure_id": "M1"}] * 5
    assert "duplicate_measure" in codes(s) and "district_required" in codes(s)
```

- [ ] **Шаг 2. Запустить**: `pytest tests/test_scoring.py tests/test_validator.py -q`, ожидание: два новых теста падают.

- [ ] **Шаг 3. Правка `engine/scoring.py`**, функция `normalize`, цикл заменить на:

```python
    for d in decisions:
        if not isinstance(d, dict):
            d = {}
        mid = str(d.get("measure_id") or "")
        did = d.get("district_id") or None
        out.append({"measure_id": mid, "district_id": str(did)} if did else {"measure_id": mid})
```

- [ ] **Шаг 4. Правка `engine/validator.py`.** В начале цикла `for i, d in enumerate(decisions):` первыми строками добавить:

```python
        if not isinstance(d, dict):
            errors.append(_err("unknown_measure", "Решение должно быть объектом с measure_id", [], [i]))
            continue
```

и заменить заполнение `positions` на:

```python
    positions = defaultdict(list)
    for i, d in enumerate(decisions):
        if isinstance(d, dict) and d.get("measure_id") in city.measures:
            positions[d["measure_id"]].append(i)
```

- [ ] **Шаг 5. Запустить**: `pytest -q`, ожидание: все тесты проходят.
- [ ] **Шаг 6. Коммит по разрешению.** `fix: ядро устойчиво к null и не-объектам, повторы считаются до фильтрации`

### Задача 11. Полный перебор, глобальный топ и банк ответов

**Файлы:** создать `engine/ranking.py`, `scripts/rank_all.py`, `engine/templates.py`; заменить целиком `engine/explain.py`; изменить `tests/test_explain.py` и `tests/test_api.py` (строка `"fallback"` → `"template"` везде); создать `data/top_sets.json` скриптом.

- [ ] **Шаг 1. `engine/ranking.py`**

```python
# engine/ranking.py
"""Полный перебор всех допустимых наборов: глобальный топ и процентиль пользователя.
Индекс считается один раз скриптом scripts/rank_all.py и хранится в data/top_sets.json."""
from __future__ import annotations
import bisect
import itertools
import json
from collections import Counter
from pathlib import Path
from .model import City
from .scoring import apply_effects, aggregate, scenario_key, normalize

INDEX_PATH = Path(__file__).resolve().parent.parent / "data" / "top_sets.json"
TOP_N = 100
QUANTILES = 1000


def enumerate_valid(city: City):
    """Генератор всех допустимых наборов (по правилам ТЗ) без вызова validate: быстрее в 20 раз."""
    ms = list(city.measures.values())
    conf_global = [tuple(x["pair"]) for x in city.conflicts if x["scope"] == "global"]
    conf_same = [tuple(x["pair"]) for x in city.conflicts if x["scope"] == "same_district"]
    for combo in itertools.combinations(ms, city.decisions_required):
        if sum(m.cost for m in combo) > city.budget:
            continue
        if any(v > city.max_per_direction for v in Counter(m.direction for m in combo).values()):
            continue
        ids = {m.id for m in combo}
        if any(a in ids and b in ids for a, b in conf_global):
            continue
        dist = [m for m in combo if m.scope == "district"]
        cityw = [m for m in combo if m.scope == "city"]
        for assign in itertools.product(city.district_ids, repeat=len(dist)):
            place = dict(zip((m.id for m in dist), assign))
            if any(a in place and b in place and place[a] == place[b] for a, b in conf_same):
                continue
            yield [{"measure_id": m.id, "district_id": place[m.id]} for m in dist] + [{"measure_id": m.id} for m in cityw]


def build_index(city: City) -> dict:
    scores = []
    top = []
    for dec in enumerate_valid(city):
        agg = aggregate(city, apply_effects(city, dec))
        cost = sum(city.measures[d["measure_id"]].cost for d in dec)
        scores.append(agg["score"])
        top.append((agg["score"], cost, scenario_key(dec), normalize(dec), agg["minimum"], agg["critical_count"]))
        if len(top) > TOP_N * 20:
            top.sort(key=lambda x: (-x[0], x[1], x[2]))
            del top[TOP_N:]
    top.sort(key=lambda x: (-x[0], x[1], x[2]))
    top = top[:TOP_N]
    scores.sort()
    step = max(1, len(scores) // QUANTILES)
    quantiles = scores[::step]
    return {
        "dataset_version": city.version, "total": len(scores),
        "score_min": scores[0], "score_max": scores[-1],
        "quantiles": quantiles,
        "top": [{"rank": i + 1, "score": s, "cost": c, "scenario_key": k, "decisions": d, "minimum": mn, "critical_count": cc}
                for i, (s, c, k, d, mn, cc) in enumerate(top)],
    }


def save_index(index: dict, path: Path = INDEX_PATH) -> None:
    Path(path).write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")


def load_index(path: Path = INDEX_PATH) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def rank_info(index: dict | None, scenario_key_: str, score: float) -> dict | None:
    """Процентиль (доля планов не лучше данного) и позиция в топ-100, если есть."""
    if not index:
        return None
    q = index["quantiles"]
    pos = bisect.bisect_right(q, score)
    percentile = 100.0 * pos / len(q)
    position = next((t["rank"] for t in index["top"] if t["scenario_key"] == scenario_key_), None)
    return {"percentile": percentile, "total": index["total"], "top_position": position,
            "best_score": index["score_max"], "gap_to_best": index["score_max"] - score}
```

- [ ] **Шаг 2. `scripts/rank_all.py`**

```python
# scripts/rank_all.py
"""Считает индекс всех допустимых наборов и сохраняет data/top_sets.json. Запуск: python scripts/rank_all.py (около 30 секунд)."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine.model import load_city  # noqa: E402
from engine.ranking import build_index, save_index, INDEX_PATH  # noqa: E402

if __name__ == "__main__":
    t = time.time()
    city = load_city()
    index = build_index(city)
    save_index(index, INDEX_PATH)
    print(f"наборов: {index['total']}, лучший: {index['score_max']:.5f}, худший: {index['score_min']:.5f}, "
          f"топ-1: {index['top'][0]['scenario_key']}, {time.time() - t:.1f} с, файл {INDEX_PATH}")
```

- [ ] **Шаг 3. Построить индекс**

Команда: `python scripts/rank_all.py`
Ожидание: `наборов: 694395, лучший: 57.23673, худший: 52.04092, топ-1: M2|M3:nura|M8:nura|M9:nura|M14`, около 25 секунд, файл `data/top_sets.json` около 50 КБ. Файл коммитится в репозиторий, чтобы эксперту не нужно было ждать перебор.

- [ ] **Шаг 4. `engine/templates.py`**

```python
# engine/templates.py
"""Банк ответов советника без модели: короткие понятные фразы из фактов, глобального топа и правил.
Возвращает ту же структуру, что и живое объяснение, плюс поле comparison."""
from __future__ import annotations
from .model import City

# Короткие названия мер: (именительный, родительный, винительный, множественное число)
SHORT = {
    "M1": ("автобусные полосы", "автобусных полос", "автобусные полосы", True),
    "M2": ("умные светофоры", "умных светофоров", "умные светофоры", True),
    "M3": ("ЛРТ", "ЛРТ", "ЛРТ", False),
    "M4": ("парк", "парка", "парк", False),
    "M5": ("чистое топливо", "чистого топлива", "чистое топливо", False),
    "M6": ("озеленение города", "озеленения города", "озеленение города", False),
    "M7": ("школа с детсадом", "школы с детсадом", "школу с детсадом", False),
    "M8": ("поликлиника", "поликлиники", "поликлинику", False),
    "M9": ("спорт-площадки", "спорт-площадок", "спорт-площадки", True),
    "M10": ("камеры и освещение", "камер и освещения", "камеры и освещение", True),
    "M11": ("безопасные переходы", "безопасных переходов", "безопасные переходы", True),
    "M12": ("платформа обращений", "платформы обращений", "платформу обращений", False),
    "M13": ("новые теплосети", "новых теплосетей", "новые теплосети", True),
    "M14": ("аварийные бригады", "аварийных бригад", "аварийные бригады", True),
}
IND = {
    "T1": "дороги", "T2": "транспорт", "E1": "озеленение", "E2": "воздух", "S1": "школы", "S2": "поликлиники",
    "B1": "безопасность улиц", "B2": "безопасность на дорогах", "C1": "ЖКХ", "C2": "обращения жителей",
}
LOC = {"esil": "в Есиле", "almaty": "в Алматы", "saryarka": "в Сарыарке", "baikonur": "в Байконуре", "nura": "в Нуре"}
NAME = {"esil": "Есиль", "almaty": "Алматы", "saryarka": "Сарыарка", "baikonur": "Байконур", "nura": "Нура"}
GEN = {"esil": "Есиля", "almaty": "Алматы", "saryarka": "Сарыарки", "baikonur": "Байконура", "nura": "Нуры"}
CASES = {"nom": 0, "gen": 1, "acc": 2}


def plural(n: float, one: str, few: str, many: str) -> str:
    n = abs(int(round(n)))
    if 11 <= n % 100 <= 19:
        return many
    r = n % 10
    return one if r == 1 else few if 2 <= r <= 4 else many


def fmt(x: float, n: int = 1) -> str:
    return f"{x:.{n}f}".replace(".", ",")


def sgn(x: float, n: int = 1) -> str:
    return ("+" if x >= 0 else "−") + fmt(abs(x), n)


def cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def mname(city: City, mid: str, case: str = "nom") -> str:
    if mid in SHORT:
        return SHORT[mid][CASES[case]]
    return city.measures[mid].name.lower()


def is_plural(mid: str) -> bool:
    return SHORT.get(mid, (None, None, None, False))[3]


def verb(mid: str, singular: str, plural_: str) -> str:
    return plural_ if is_plural(mid) else singular


def iname(city: City, code: str) -> str:
    return IND.get(code, city.indicator_names.get(code, code).lower())


def where(did: str | None) -> str:
    return LOC.get(did or "", "по всему городу")


def measure_phrase(city: City, d: dict, case: str = "nom") -> str:
    return f"{mname(city, d['measure_id'], case)} {where(d.get('district_id'))}"


def _facts_by(facts: list, kind: str) -> list:
    return [f for f in facts if f["kind"] == kind]


def _ids(*facts) -> list:
    return [f["id"] for f in facts if f]


def template_explanation(city: City, result: dict, candidates: list, facts: list, index: dict | None, rank: dict | None) -> dict:
    dec_f = _facts_by(facts, "decomposition")[0]
    worst_f = _facts_by(facts, "worst_district")[0]
    plan_f = _facts_by(facts, "plan")[0]
    delta = result["delta"]
    dc = result["decomposition"]
    worst = min(result["district_results"], key=lambda d: d["score_after"])

    # Резюме: три коротких предложения
    if delta < 0:
        opener = "Этот план делает городу хуже."
    elif delta < 1:
        opener = "План почти ничего не меняет."
    elif delta < 3:
        opener = "Неплохой план."
    else:
        opener = "Сильный план."
    parts = [opener, f"Оценка города {fmt(result['score'])} вместо {fmt(result['baseline_score'])} на старте."]
    if rank:
        if rank["top_position"] == 1:
            parts.append(f"Это лучший из всех {rank['total']} вариантов.")
        elif rank["top_position"]:
            parts.append(f"Это {rank['top_position']}-е место среди {rank['total']} вариантов.")
        elif rank["percentile"] >= 99.95:
            parts.append("Лучше 99,9% всех вариантов.")
        else:
            parts.append(f"Лучше {fmt(rank['percentile'])}% всех вариантов.")
    parts.append(f"Самый слабый район всё ещё {worst['name']}: {fmt(worst['score_after'])}.")
    summary = " ".join(parts)

    # Сильные стороны
    strengths = []
    if dc["avg"] > 1e-9:
        strengths.append({"text": f"Город в целом стал лучше ({sgn(dc['avg'], 2)}).", "fact_ids": _ids(dec_f)})
    if dc["min"] > 1e-9:
        strengths.append({"text": f"Самый слабый район подтянулся ({sgn(dc['min'], 2)}).", "fact_ids": _ids(dec_f)})
    if dc["crit"] > 1e-9:
        n = int(round(dc["crit"]))
        tail = "штраф снят полностью." if not result["critical_pairs"] else f"штраф меньше на {n} {plural(n, 'балл', 'балла', 'баллов')}."
        strengths.append({"text": f"{plural(n, 'Убран', 'Убраны', 'Убраны')} {n} {plural(n, 'провал', 'провала', 'провалов')} ниже 40, {tail}",
                          "fact_ids": _ids(dec_f, *_facts_by(facts, "no_critical"))})
    for f in _facts_by(facts, "synergy"):
        s = f["data"]
        a, b = s["pair"].split("+")
        strengths.append({"text": f"{cap(mname(city, a))} плюс {mname(city, b)} дают бонус: {iname(city, s['indicator'])} {where(s['district_id'])} +{s['bonus']}.", "fact_ids": _ids(f)})
    grown = sorted(_facts_by(facts, "district"), key=lambda f: -f["data"]["gain"])[:2]
    for f in grown:
        d = f["data"]
        if d["gain"] > 1e-9:
            strengths.append({"text": f"{NAME[d['district_id']]}: {fmt(d['score_before'])} → {fmt(d['score_after'])}.", "fact_ids": _ids(f)})
    if not strengths:
        strengths.append({"text": "Хвалить нечего: ни одна часть оценки не выросла.", "fact_ids": _ids(dec_f)})

    # Риски
    risks = []
    for f in _facts_by(facts, "critical"):
        for p in f["data"]["pairs"]:
            risks.append({"text": f"{cap(iname(city, p['indicator']))} {where(p['district_id'])} всё ещё провалены: {fmt(p['value'], 0)} из 100. Это минус балл.", "fact_ids": _ids(f)})
    for f in _facts_by(facts, "measure"):
        d = f["data"]
        for e in d["effects"]:
            if e["delta"] < 0:
                mid = d["measure_id"]
                risks.append({"text": f"{cap(mname(city, mid))} {where(d['district_id'])} немного {verb(mid, 'ухудшает', 'ухудшают')} показатель «{iname(city, e['code'])}» ({sgn(e['delta'])}).", "fact_ids": _ids(f)})
    for f in _facts_by(facts, "district_unchanged"):
        risks.append({"text": f"{NAME[f['data']['district_id']]} остался без внимания.", "fact_ids": _ids(f)})
    chosen = {d["measure_id"] for d in result["decisions"]}
    for s in city.synergies:
        a, b = s["pair"]
        if (a in chosen) != (b in chosen):
            have, miss = (a, b) if a in chosen else (b, a)
            risks.append({"text": f"Без {mname(city, miss, 'gen')} не срабатывает бонус связки с {mname(city, have, 'gen')}: вместе они дали бы ещё +{s['bonus']} к показателю «{iname(city, s['indicator'])}».", "fact_ids": _ids(plan_f)})
    for f in _facts_by(facts, "measure"):
        d = f["data"]
        if d["realized_fraction"] <= 0.5:
            m = city.measures[d["measure_id"]]
            risks.append({"text": f"{cap(mname(city, m.id))} {where(d['district_id'])} {verb(m.id, 'заработает', 'заработают')} только через {m.lag} {plural(m.lag, 'квартал', 'квартала', 'кварталов')}. Полного эффекта за два года не будет.", "fact_ids": _ids(f)})
    rb = result["remaining_budget"]
    if rb >= 10:
        risks.append({"text": f"{rb} {plural(rb, 'единица', 'единицы', 'единиц')} бюджета не потрачены. Остаток ничего не даёт.", "fact_ids": _ids(plan_f)})
    if not risks:
        risks.append({"text": f"{worst['name']} остаётся самым слабым районом. Пока так, итог выше не поднять.", "fact_ids": _ids(worst_f)})
    risks = risks[:5]

    # Что можно сделать
    suggestions = []
    for f in _facts_by(facts, "candidate"):
        c = next(x for x in candidates if x["id"] == f["data"]["candidate_id"])
        suggestions.append({"candidate_id": c["id"],
                            "text": f"Замените {measure_phrase(city, c['replace'], 'acc')} на {measure_phrase(city, c['with'], 'acc')}. Оценка станет {fmt(c['score'])} ({sgn(c['delta'], 2)}), бюджет {c['cost']}.",
                            "fact_ids": _ids(f)})

    comparison = None
    if index and index.get("top"):
        best = index["top"][0]
        if best["scenario_key"] == result["scenario_key"]:
            comparison = f"Это лучший план из всех. Выше {fmt(best['score'])} в этой модели не подняться."
        else:
            mine = {(d["measure_id"], d.get("district_id")) for d in result["decisions"]}
            theirs = {(d["measure_id"], d.get("district_id")) for d in best["decisions"]}
            remove = [d for d in result["decisions"] if (d["measure_id"], d.get("district_id")) not in theirs]
            add = [d for d in best["decisions"] if (d["measure_id"], d.get("district_id")) not in mine]
            comparison = (f"Лучший план даёт {fmt(best['score'])}, вам не хватает {fmt(best['score'] - result['score'])}. "
                          f"В нём вместо {', '.join(measure_phrase(city, d, 'gen') for d in remove)} "
                          f"стоят {', '.join(measure_phrase(city, d) for d in add)}.")
    return {"summary": summary, "strengths": strengths[:5], "risks": risks, "suggestions": suggestions, "comparison": comparison}
```

- [ ] **Шаг 5. `engine/explain.py` заменить целиком**

```python
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

PROMPT_VERSION = "akim-explain-v2"
MAX_CACHE = 100
_cache: "OrderedDict[str, dict]" = OrderedDict()

NUM_RE = re.compile(r"(?<![A-Za-zА-Яа-я\d_])-?\d+(?:[.,]\d+)?")

SYSTEM_PROMPT = (
    "Ты советник акима Астаны в учебном симуляторе городского бюджета. "
    "Тебе дан список фактов с идентификаторами f1..fN, каждый факт уже посчитан программой. "
    "Объясни результат человеческим языком: короткое резюме, 2–3 сильные стороны, 2–3 риска или компромисса, "
    "и по одному комментарию к каждой альтернативе c1..c3, если они переданы. "
    "Называй меры по названию, а не только по коду, и привязывай каждый риск к конкретному району или показателю. "
    "Правила: не придумывай числа, меры и районы; используй только числа из фактов и только в том виде, как они там записаны; "
    "каждое утверждение опирается на факты и перечисляет их идентификаторы в fact_ids; "
    "в suggestions используй только переданные candidate_id; пиши по-русски, коротко, без общих фраз. "
    "Ответ строго JSON без других ключей: {\"summary\": str, \"strengths\": [{\"text\": str, \"fact_ids\": [str]}], "
    "\"risks\": [{\"text\": str, \"fact_ids\": [str]}], \"suggestions\": [{\"candidate_id\": str, \"text\": str, \"fact_ids\": [str]}]}"
)

CHAT_PROMPT = (
    "Ты советник акима Астаны в учебном симуляторе городского бюджета. Отвечай на вопросы пользователя о его плане. "
    "Ниже факты о текущем плане, они посчитаны программой, и список лучших планов из полного перебора. "
    "Правила: опирайся только на эти факты; не придумывай числа, меры и районы; если ответа в фактах нет, скажи об этом; "
    "советы давай конкретные: какую меру на какую заменить и что это даст, ссылаясь на альтернативы или лучшие планы. "
    "Отвечай по-русски, коротко, до 120 слов, обычным текстом без JSON."
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
```

- [ ] **Шаг 6. В `tests/test_explain.py` и `tests/test_api.py` заменить все `"fallback"` на `"template"`.**

Команда (Git Bash): `sed -i 's/"fallback"/"template"/g' tests/test_explain.py tests/test_api.py`

- [ ] **Шаг 7. Запустить**: `pytest -q`, ожидание: все тесты проходят. старый `app.py` продолжает импортировать `api_key`, эта функция сохранена в новом `explain.py` для совместимости, поэтому сервер работает до задачи 12.
- [ ] **Шаг 8. Коммит по разрешению.** `feat: полный перебор планов, глобальный топ, банк ответов советника`. Файлы: `engine/ranking.py scripts/rank_all.py engine/templates.py engine/explain.py data/top_sets.json tests/test_explain.py tests/test_api.py`

### Задача 12. Ключ из интерфейса, топ, ранг и диалог в API

**Файлы:** заменить целиком `app.py`; создать `tests/test_bank.py`.

- [ ] **Шаг 1. `tests/test_bank.py`**

```python
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
    assert "не срабатывает бонус" in texts and "платформы обращений" in texts and "Безопасные переходы" in texts


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
```

- [ ] **Шаг 2. Запустить**: `pytest tests/test_bank.py -q`, ожидание: падения на отсутствующих маршрутах.

- [ ] **Шаг 3. `app.py` заменить целиком**

```python
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
```

- [ ] **Шаг 4. Запустить**: `pytest -q`, ожидание: все тесты проходят, 57 и больше.

- [ ] **Шаг 5. Живая проверка с ключом из `.env`**

Команда: `python -m uvicorn app:app --port 8000`, затем в другом терминале (Git Bash):

```
curl -s localhost:8000/api/health
curl -s "localhost:8000/api/top?limit=3"
curl -s -X POST localhost:8000/api/ai/check
curl -s -X POST localhost:8000/api/chat -H "Content-Type: application/json" -d '{"decisions":[{"measure_id":"M7","district_id":"nura"},{"measure_id":"M8","district_id":"nura"},{"measure_id":"M10","district_id":"nura"},{"measure_id":"M12"},{"measure_id":"M5","district_id":"saryarka"}],"messages":[{"role":"user","content":"Что поменять, чтобы обогнать лучший план?"}]}'
```

В PowerShell тело передаётся так: `-d "{\"decisions\":[{\"measure_id\":\"M7\",\"district_id\":\"nura\"},{\"measure_id\":\"M8\",\"district_id\":\"nura\"},{\"measure_id\":\"M10\",\"district_id\":\"nura\"},{\"measure_id\":\"M12\"},{\"measure_id\":\"M5\",\"district_id\":\"saryarka\"}],\"messages\":[{\"role\":\"user\",\"content\":\"Что поменять, чтобы обогнать лучший план?\"}]}"`.

Ожидание: `ranking_available: true`, три плана в топе, `ok: true`, ответ советника с `mode: live` и `numbers_checked: true`.

- [ ] **Шаг 6. README.** В таблицу соответствия добавить строки: «AI-рекомендации по улучшению» → `engine/advisor.py`, `engine/ranking.py`, `/api/improvements`, `/api/top`; «Сравнение результатов» → `rank` в `/api/evaluate`, `/api/top`. В раздел про переменные окружения добавить абзац: ключ можно ввести в интерфейсе, он передаётся заголовком `X-OpenAI-Key`, на сервере не сохраняется. В раздел про режимы: `live`, `template` (банк ответов из фактов и полного перебора), диалог доступен только с ключом, поле `numbers_checked` и его ограничение.

- [ ] **Шаг 7. Коммит по разрешению.** `feat: ключ OpenAI из интерфейса, топ планов, ранг сценария, диалог с советником`

## Порядок отсечения при нехватке времени

Не режутся: задачи 1–4 (данные, валидатор, расчёт), задача 8 (сервер), задача 9 (README и чистый запуск), резервное объяснение из задачи 6. Если к 17:00 не закрыта задача 7, сервер отдаёт `fallback` с честной пометкой, а README описывает, что живой режим не проверен. Если не закрыта задача 5, маршрут `/api/improvements` возвращает пустой список, а факты и резерв работают без альтернатив.

## Самопроверка плана

- Спецификация `docs/akim-spec.md`: раздел 3 данные → задача 1; раздел 4 правила → задача 3; раздел 5 расчёт и контрольные числа → задача 4; раздел 6 советник → задача 5; раздел 7 объяснение, режимы, кэш → задачи 6 и 7; раздел 8 API и лимит тела → задача 8; раздел 10 тесты → задачи 3–8; раздел 11 README → задача 9.
- Ревью Codex: разложение кандидата от набора пользователя → задача 5; строгая схема и проверка чисел в ответе модели → задача 7; риски резерва по правилам с тестами → задача 6; вклад мер в фактах → задачи 4 и 6; лимит фактически полученных байтов → задача 8; чистый запуск внутри репозитория → задача 9; тест без ключа требует ровно `fallback` → задачи 7 и 8; clip с двумя эффектами и смена слабейшего района → задача 4.
- Имена согласованы: `load_city` (`model.py`); `validate`, `scenario_cost` (`validator.py`); `normalize`, `scenario_key`, `apply_effects`, `aggregate`, `count_critical`, `critical_pairs`, `baseline`, `evaluate`, `measure_contributions`, `synergy_effects` (`scoring.py`); `find_improvements` (`advisor.py`); `build_facts`, `fallback_explanation` (`facts.py`); `explain`, `validate_answer`, `clear_cache`, `api_key`, `model_name`, `call_openai`, `NotConfigured` (`explain.py`); `create_app`, `app` (`app.py`).
