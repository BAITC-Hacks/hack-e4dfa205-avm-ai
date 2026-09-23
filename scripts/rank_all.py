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
          f"топ-1: {index['top'][0]['scenario_key']}, Парето: {len(index['pareto'])} точек, {time.time() - t:.1f} с, файл {INDEX_PATH}")
