# engine/scoring.py
from __future__ import annotations
from .model import City
from .validator import validate


def normalize(decisions: list) -> list:
    """Нормализованный набор: без district_id у городских мер, отсортирован по номеру меры."""
    out = []
    for d in decisions:
        if not isinstance(d, dict):
            d = {}
        mid = str(d.get("measure_id") or "")
        did = d.get("district_id") or None
        out.append({"measure_id": mid, "district_id": str(did)} if did else {"measure_id": mid})
    return sorted(out, key=lambda x: (_measure_number(x["measure_id"]), x.get("district_id") or ""))


def _measure_number(mid: str) -> int:
    try:
        return int(mid[1:])
    except (ValueError, TypeError):
        return 999


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
