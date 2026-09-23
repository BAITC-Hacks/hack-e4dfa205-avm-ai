# tests/test_demo.py
import importlib.util
import io
from contextlib import redirect_stdout
from pathlib import Path

DEMO = Path(__file__).resolve().parent.parent / "scripts" / "demo.py"


def _load():
    spec = importlib.util.spec_from_file_location("demo", DEMO)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_demo_runs_offline_and_prints_key_numbers(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mod = _load()
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = mod.main([])
    out = buf.getvalue()
    assert rc == 0
    assert "52,56" in out and "56,54" in out          # база и пример из ТЗ
    assert "budget_exceeded" in out or "Превышен бюджет" in out  # контроль бюджета
    assert "694 395" in out or "694395" in out        # полный перебор
    assert "template" in out                          # без ключа — банк ответов, честно
