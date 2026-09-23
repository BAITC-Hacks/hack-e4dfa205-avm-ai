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
    best_by_cost = {}  # стоимость -> лучший план этой стоимости (для Парето «цена → Score»)
    for dec in enumerate_valid(city):
        agg = aggregate(city, apply_effects(city, dec))
        cost = sum(city.measures[d["measure_id"]].cost for d in dec)
        scores.append(agg["score"])
        row = (agg["score"], cost, scenario_key(dec), normalize(dec), agg["minimum"], agg["critical_count"])
        top.append(row)
        cur = best_by_cost.get(cost)
        if cur is None or (row[0], -row[1], row[2]) > (cur[0], -cur[1], cur[2]):
            best_by_cost[cost] = row
        if len(top) > TOP_N * 20:
            top.sort(key=lambda x: (-x[0], x[1], x[2]))
            del top[TOP_N:]
    top.sort(key=lambda x: (-x[0], x[1], x[2]))
    top = top[:TOP_N]
    scores.sort()
    step = max(1, len(scores) // QUANTILES)
    quantiles = scores[::step]
    pareto = []  # по возрастанию стоимости оставляем только строгие улучшения Score
    best_so_far = float("-inf")
    for cost in sorted(best_by_cost):
        s, c, k, d, mn, cc = best_by_cost[cost]
        if s > best_so_far + 1e-9:
            pareto.append({"cost": c, "score": s, "scenario_key": k, "decisions": d, "minimum": mn, "critical_count": cc})
            best_so_far = s
    return {
        "dataset_version": city.version, "total": len(scores),
        "score_min": scores[0], "score_max": scores[-1],
        "quantiles": quantiles, "pareto": pareto,
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
