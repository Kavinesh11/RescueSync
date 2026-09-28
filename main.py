"""RescueSync CLI entry point.

Examples:
    python main.py --scenario scenarios/blocked_victim.json --mode rescuesync
    python main.py --scenario scenarios/blocked_victim.json --mode cooperative --gui
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rescuesync.metrics import compute_metrics
from rescuesync.planner import Mode, plan_all

MODE_MAP = {
    "1": Mode.INDEPENDENT, "independent": Mode.INDEPENDENT,
    "2": Mode.COOPERATIVE, "cooperative": Mode.COOPERATIVE,
    "3": Mode.RESCUESYNC, "rescuesync": Mode.RESCUESYNC,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="RescueSync planner CLI")
    parser.add_argument("--scenario", required=True, help="path to a scenario JSON file")
    parser.add_argument("--mode", default="rescuesync", choices=sorted(MODE_MAP))
    parser.add_argument("--gui", action="store_true", help="launch the Pygame visualizer")
    args = parser.parse_args()

    scenario = json.loads(Path(args.scenario).read_text(encoding="utf-8"))
    mode = MODE_MAP[args.mode]
    result = plan_all(scenario, mode)
    metrics = compute_metrics(result)

    print(json.dumps(metrics, indent=2))

    if args.gui:
        from rescuesync.visualizer import run_visualizer
        run_visualizer(scenario, mode)


if __name__ == "__main__":
    main()
