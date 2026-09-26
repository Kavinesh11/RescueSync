"""Independent execution + collision checker.

This is deliberately decoupled from the planner: it only reads each agent's
final `schedule` (position per timestep) and checks it against every other
agent's schedule. It does not know or care whether a reservation table was
used, so it verifies the planner rather than trusting it.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

Cell = Tuple[int, int]


def _pos_at(agent, t: int) -> Cell:
    if t < len(agent.schedule):
        return agent.schedule[t]
    return agent.schedule[-1]


def simulate(plan_result) -> Dict:
    agents = {aid: a for aid, a in plan_result.agents.items() if a.schedule}
    if not agents:
        return {"collisions": [], "makespan": 0}

    ids = list(agents.keys())
    makespan = max(len(agents[i].schedule) - 1 for i in ids)
    collisions: List[dict] = []

    for t in range(makespan + 1):
        occupied: Dict[Cell, str] = {}
        for aid in ids:
            cell = _pos_at(agents[aid], t)
            if cell in occupied:
                collisions.append({
                    "kind": "vertex", "t": t, "cell": list(cell),
                    "agents": [occupied[cell], aid],
                })
            else:
                occupied[cell] = aid

    for t in range(makespan):
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = agents[ids[i]], agents[ids[j]]
                a1, a2 = _pos_at(a, t), _pos_at(a, t + 1)
                b1, b2 = _pos_at(b, t), _pos_at(b, t + 1)
                if a1 != a2 and a1 == b2 and b1 == a2:
                    collisions.append({
                        "kind": "swap", "t": t, "cell": None,
                        "agents": [ids[i], ids[j]],
                    })

    return {"collisions": collisions, "makespan": makespan}
