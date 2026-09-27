"""Computes all metrics from an executed plan (see CLAUDE.md section 11)."""
from __future__ import annotations

from typing import Dict

from .agents import MedicAgent
from .simulator import simulate


def compute_metrics(plan_result) -> Dict:
    sim = simulate(plan_result)
    agents = plan_result.agents

    # A Medic that crashed into another robot on the way didn't really
    # rescue anyone, even if its (independently planned) path reached the
    # victim. Only Independent A* can produce such plans.
    collided = {aid for c in sim["collisions"] for aid in c["agents"]}

    total_victims = sum(1 for a in agents.values() if isinstance(a, MedicAgent))
    rescued = sum(
        1 for a in agents.values()
        if isinstance(a, MedicAgent) and not a.failed and a.id not in collided
    )

    finish_times = [a.finish_time for a in agents.values() if a.finish_time is not None]
    makespan = max(finish_times) if finish_times else 0
    sum_of_costs = sum(finish_times) if finish_times else 0

    wait_actions = sum(a.wait_count for a in agents.values())
    medic_dependency_wait = sum(a.wait_count for a in agents.values() if isinstance(a, MedicAgent))

    return {
        "mode": plan_result.mode,
        "victims_rescued": rescued,
        "victims_total": total_victims,
        "success_rate": (rescued / total_victims) if total_victims else 1.0,
        "collisions": len(sim["collisions"]),
        "collision_details": sim["collisions"],
        "makespan": makespan,
        "sum_of_costs": sum_of_costs,
        "wait_actions": wait_actions,
        "medic_dependency_wait": medic_dependency_wait,
        "planning_time_ms": round(plan_result.planning_time_ms, 3),
        "nodes_expanded": plan_result.stats.get("nodes_expanded", 0),
        "agents_failed": sorted(a.id for a in agents.values() if a.failed),
    }
