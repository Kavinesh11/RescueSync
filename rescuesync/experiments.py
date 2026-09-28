"""Random scenario generation + the Review-2 experiment graphs.

Run with: python -m rescuesync.experiments
Produces experiments/output/*.png and raw_results.json.
"""
from __future__ import annotations

import json
import random
import statistics as st
from pathlib import Path
from typing import Dict, List, Tuple

from .metrics import compute_metrics
from .planner import Mode, plan_all

Cell = Tuple[int, int]

# Okabe-Ito colorblind-safe palette.
COLORS = {
    "independent": "#D55E00",
    "cooperative": "#0072B2",
    "rescuesync": "#009E73",
}
LABELS = {
    "independent": "Independent A*",
    "cooperative": "Cooperative A*",
    "rescuesync": "RescueSync",
}
MODE_ORDER = ["independent", "cooperative", "rescuesync"]

ROBOT_COUNTS = [2, 4, 6, 8, 10, 12]
RUNS_PER_SETTING = 5


def random_scenario(
    seed: int,
    size: int = 15,
    num_engineers: int = 3,
    num_medics: int = 5,
    max_time: int = 200,
) -> dict:
    """A left/right split map with one rubble "door" per Engineer.

    The interior is cut in half by a solid wall at the middle column, pierced
    only by `num_engineers` rubble cells (one door per Engineer). Some Medics
    start on one side and are rescued on the other, so they are genuinely
    unreachable in Independent/Cooperative mode -- not just inconvenienced by
    a single obstacle they could otherwise walk around.
    """
    rng = random.Random(seed)
    grid: List[List[str]] = [["." for _ in range(size)] for _ in range(size)]
    for c in range(size):
        grid[0][c] = "#"
        grid[size - 1][c] = "#"
    for r in range(size):
        grid[r][0] = "#"
        grid[r][size - 1] = "#"

    mid = size // 2
    for r in range(1, size - 1):
        grid[r][mid] = "#"

    interior_rows = list(range(1, size - 1))
    door_rows = rng.sample(interior_rows, min(num_engineers, len(interior_rows)))
    doors: List[Cell] = []
    for r in door_rows:
        grid[r][mid] = "R"
        doors.append((r, mid))

    reserved = {(r, mid - 1) for r in door_rows} | {(r, mid + 1) for r in door_rows}
    left_cells = [(r, c) for r in range(1, size - 1) for c in range(1, mid) if (r, c) not in reserved]
    right_cells = [(r, c) for r in range(1, size - 1) for c in range(mid + 1, size - 1) if (r, c) not in reserved]
    rng.shuffle(left_cells)
    rng.shuffle(right_cells)

    agents = []
    for i, door in enumerate(doors):
        r, _c = door
        start = left_cells.pop()
        park = left_cells.pop()
        agents.append({
            "id": f"E{i + 1}", "role": "engineer",
            "start": list(start), "rubble": list(door),
            "stand": [r, mid - 1], "park": list(park),
        })

    for i in range(num_medics):
        crosses = rng.random() < 0.6
        if crosses:
            if rng.random() < 0.5:
                start, victim = left_cells.pop(), right_cells.pop()
            else:
                start, victim = right_cells.pop(), left_cells.pop()
        else:
            side = left_cells if rng.random() < 0.5 else right_cells
            start, victim = side.pop(), side.pop()
        grid[victim[0]][victim[1]] = "V"
        agents.append({
            "id": f"M{i + 1}", "role": "medic",
            "start": list(start), "victim": list(victim),
        })

    return {
        "name": f"random_seed{seed}",
        "grid": ["".join(row) for row in grid],
        "clear_time": 2,
        "rescue_time": 2,
        "max_time": max_time,
        "agents": agents,
    }


def run_experiments(output_dir: str = "experiments/output") -> List[dict]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    rows: List[dict] = []
    for n in ROBOT_COUNTS:
        for run in range(RUNS_PER_SETTING):
            seed = n * 1000 + run
            num_engineers = max(1, n // 3)
            num_medics = n - num_engineers
            scenario = random_scenario(
                seed=seed, size=15, num_engineers=num_engineers, num_medics=num_medics,
            )
            for mode in (Mode.INDEPENDENT, Mode.COOPERATIVE, Mode.RESCUESYNC):
                result = plan_all(scenario, mode)
                metrics = compute_metrics(result)
                rows.append({"robots": n, "mode": mode.value, **metrics})

    (out / "raw_results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    _plot(rows, str(out))
    return rows


def _agg(rows: List[dict], mode: str, field: str) -> Tuple[List[int], List[float]]:
    by_n: Dict[int, List[float]] = {}
    for r in rows:
        if r["mode"] != mode:
            continue
        by_n.setdefault(r["robots"], []).append(r[field])
    xs = sorted(by_n)
    ys = [st.mean(by_n[x]) for x in xs]
    return xs, ys


def _plot(rows: List[dict], output_dir: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def line_chart(field: str, ylabel: str, title: str, filename: str) -> None:
        plt.figure(figsize=(7, 5))
        for mode in MODE_ORDER:
            xs, ys = _agg(rows, mode, field)
            plt.plot(xs, ys, marker="o", label=LABELS[mode], color=COLORS[mode])
        plt.xlabel("Number of robots")
        plt.ylabel(ylabel)
        plt.title(title)
        plt.legend()
        plt.grid(alpha=0.25)
        plt.tight_layout()
        plt.savefig(f"{output_dir}/{filename}", dpi=150)
        plt.close()

    line_chart("success_rate", "Success rate", "Success rate vs. number of robots", "success_rate.png")
    line_chart("planning_time_ms", "Planning time (ms)", "Planning time vs. number of robots", "planning_time.png")
    line_chart("makespan", "Makespan", "Makespan vs. number of robots", "makespan.png")

    plt.figure(figsize=(7, 5))
    totals = [sum(r["collisions"] for r in rows if r["mode"] == m) for m in MODE_ORDER]
    plt.bar([LABELS[m] for m in MODE_ORDER], totals, color=[COLORS[m] for m in MODE_ORDER])
    plt.ylabel("Total collisions across all runs")
    plt.title("Collisions per planner mode")
    plt.tight_layout()
    plt.savefig(f"{output_dir}/collisions.png", dpi=150)
    plt.close()


if __name__ == "__main__":
    run_experiments()
