# scripts/demo.py
"""Демонстрация основного сценария в терминале, без сервера и без сети.
Запуск из корня репозитория: python scripts/demo.py
С ключом OpenAI в .env объяснение будет живым (mode=live), без ключа — банк ответов (mode=template)."""
from __future__ import annotations
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
from engine.model import load_city  # noqa: E402
from engine.scoring import evaluate, baseline  # noqa: E402
from engine.advisor import find_improvements  # noqa: E402
from engine.facts import build_facts  # noqa: E402
from engine.ranking import load_index, rank_info  # noqa: E402
from engine.explain import explain  # noqa: E402


def f2(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


def sg(x: float) -> str:
    return ("+" if x >= 0 else "−") + f2(abs(x))


def dec_str(city, d: dict) -> str:
    m = city.measures[d["measure_id"]]
    where = city.district(d["district_id"]).name if d.get("district_id") else "город"
    return f"{m.id} «{m.name}» — {where}"


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def main(argv: list | None = None) -> int:
    load_dotenv(ROOT / ".env")
    city = load_city()
    print("«Аким на 5 часов»: демонстрация основного сценария (данные ТЗ, версия", city.version + ")")

    section("1. Старт одинаков для всех")
    b = baseline(city)
    print(f"Бюджет {city.budget}, решений ровно {city.decisions_required}, мер в каталоге {len(city.measures)}, районов {len(city.districts)}.")
    print(f"Score без действий: {f2(b['score'])}. Критических показателей (<{int(city.critical_threshold)}): {b['critical_count']} — "
          + ", ".join(f"{city.district(p['district_id']).name} {p['indicator']}={p['value']:g}" for p in b["critical_pairs"]))

    section("2. Пример из ТЗ")
    example = [dict(d) for d in city.example_scenario]
    r = evaluate(city, example)
    for d in r["decisions"]:
        print("  •", dec_str(city, d))
    print(f"Стоимость {r['cost']} из {city.budget}, остаток {r['remaining_budget']}.")
    print(f"Score {f2(r['score'])} ({sg(r['delta'])} к базе {f2(r['baseline_score'])}); критических: {r['critical_count']}; синергии: {', '.join(r['active_synergies']) or 'нет'}.")
    dc = r["decomposition"]
    print(f"Разложение прироста: средний результат города {sg(dc['avg'])}, слабейший район {sg(dc['min'])}, снятый штраф {sg(dc['crit'])}.")
    for d in r["district_results"]:
        changed = [i for i in d["indicators"] if abs(i["after"] - i["before"]) > 1e-9]
        tail = ", ".join(f"{i['code']} {i['before']:g}→{i['after']:g}" for i in changed) or "без изменений"
        print(f"  {d['name']:9s} {f2(d['score_before'])} → {f2(d['score_after'])}   {tail}")

    section("3. Правила не обойти")
    over = [{"measure_id": "M3", "district_id": "esil"}, {"measure_id": "M13", "district_id": "almaty"},
            {"measure_id": "M5", "district_id": "saryarka"}, {"measure_id": "M7", "district_id": "nura"}, {"measure_id": "M12"}]
    o = evaluate(city, over)
    print(f"Набор на 121 единицу: valid={o['valid']}, score={o['score']} → " + "; ".join(f"{e['code']}: {e['message']}" for e in o["errors"]))
    conflict = [{"measure_id": "M1", "district_id": "esil"}, {"measure_id": "M3", "district_id": "nura"},
                {"measure_id": "M12"}, {"measure_id": "M10", "district_id": "nura"}, {"measure_id": "M4", "district_id": "saryarka"}]
    c = evaluate(city, conflict)
    print("M1 и M3 вместе: " + "; ".join(f"{e['code']}: {e['message']}" for e in c["errors"]))

    section("4. Советник: улучшение заменой одной меры")
    cands = find_improvements(city, example)
    for k in cands:
        print(f"  {k['id']}: {dec_str(city, k['replace'])} → {dec_str(city, k['with'])}: Score {f2(k['score'])} ({sg(k['delta'])}), стоимость {k['cost']}")
    if not cands:
        print("  улучшений заменой одной меры не найдено")

    section("5. Ранг среди всех допустимых планов")
    index = load_index()
    rank = rank_info(index, r["scenario_key"], r["score"]) if index else None
    if index and rank:
        total = f"{index['total']:,}".replace(",", " ")
        best = index["top"][0]
        print(f"Полный перебор: {total} допустимых планов (data/top_sets.json). Пример из ТЗ лучше {rank['percentile']:.1f}% планов, "
              f"до лучшего не хватает {f2(rank['gap_to_best'])}.")
        print(f"Лучший план по модели: Score {f2(best['score'])} за {best['cost']}: " + "; ".join(dec_str(city, d) for d in best["decisions"]))
    else:
        print("Индекс перебора не найден: python scripts/rank_all.py")

    section("6. Объяснение советника")
    facts = build_facts(city, r, cands)
    out = explain(city, r, cands, facts, index=index, rank=rank)
    src = "ключ OpenAI" if out["mode"] == "live" else "без ключа, банк ответов из фактов и перебора"
    print(f"mode={out['mode']} ({src}); модель: {out['model'] or '—'}; причина: {out['reason'] or '—'}; фактов: {len(facts)}")
    ex = out["explanation"]
    print("Резюме:", ex["summary"])
    print("Сильные стороны:"); [print("  +", it["text"], it["fact_ids"]) for it in ex["strengths"]]
    print("Риски:"); [print("  −", it["text"], it["fact_ids"]) for it in ex["risks"]]
    print("Предложения:"); [print("  →", it["text"], it["fact_ids"]) for it in ex["suggestions"]]
    if out.get("comparison"):
        print("Сравнение с лучшим планом:", out["comparison"])

    section("Дальше")
    print("Сервер и интерфейс: python -m uvicorn app:app --port 8000 → http://localhost:8000 (Swagger: /docs). Тесты: pytest -q.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
