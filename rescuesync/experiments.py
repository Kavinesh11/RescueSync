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
    num_rubble: int = 4,
    max_time: int = 200,
) -> dict:
    rng = random.Random(seed)
    grid: List[List[str]] = [["." for _ in range(size)] for _ in range(size)]
    for c in range(size):
        grid[0][c] = "#"
        grid[size - 1][c] = "#"
    for r in range(size):
        grid[r][0] = "#"
        grid[r][size - 1] = "#"

    free_cells = [(r, c) for r in range(1, size - 1) for c in range(1, size - 1)]
    rng.shuffle(free_cells)

    def pop_cell() -> Cell:
        return free_cells.pop()

    def adjacent_free(cell: Cell):
        r, c = cell
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = r + dr, c + dc
            if 0 < nr < size - 1 and 0 < nc < size - 1 and grid[nr][nc] == ".":
                return (nr, nc)
        return None

    rubble_cells: List[Cell] = []
    for _ in range(num_rubble):
        rc = pop_cell()
        grid[rc[0]][rc[1]] = "R"
        rubble_cells.append(rc)

    agents = []
    for i in range(num_engineers):
        start = pop_cell()
        rubble = rubble_cells[i % len(rubble_cells)]
        stand = adjacent_free(rubble) or pop_cell()
        park = pop_cell()
        agents.append({
            "id": f"E{i + 1}", "role": "engineer",
            "start": list(start), "rubble": list(rubble),
            "stand": list(stand), "park": list(park),
        })

    for i in range(num_medics):
        start = pop_cell()
        victim = pop_cell()
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
                seed=seed, size=15, num_engineers=num_engineers,
                num_medics=num_medics, num_rubble=max(2, num_engineers),
            )
            for mode in (Mode.INDEPENDENT, Mode.COOPERATIVE, Mode.RESCUESYNC):
                result = plan_all(scenario, mode)
                metrics = compute_metrics(result)
                rows.append({"robots": n, "mode": mode.value, **metrics})

    (out / "raw_results.json").write_text(json.dumps(rows, indent=2))
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
