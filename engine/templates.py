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
