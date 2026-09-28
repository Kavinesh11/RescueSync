import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SCENARIOS_DIR = ROOT / "scenarios"


@pytest.fixture
def load_scenario():
    def _load(name: str) -> dict:
        return json.loads((SCENARIOS_DIR / f"{name}.json").read_text(encoding="utf-8"))

    return _load
