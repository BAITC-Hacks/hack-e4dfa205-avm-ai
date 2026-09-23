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
