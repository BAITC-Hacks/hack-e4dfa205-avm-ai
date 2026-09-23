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
