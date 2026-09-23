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
