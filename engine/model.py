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
