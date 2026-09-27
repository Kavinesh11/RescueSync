"""Plain A* and Space-Time A* (Silver, 2005) with a reservation table.

Both use the Manhattan distance heuristic, which is admissible and consistent
on a 4-connected unit-cost grid: every move changes exactly one coordinate by
1, and walls/rubble/WAIT can only make the realized path longer, never
shorter, so h(n) never overestimates the true remaining cost.
"""
from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Tuple

from .environment import Grid
from .reservation import ReservationTable

Cell = Tuple[int, int]


def manhattan(a: Cell, b: Cell) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def plain_astar(grid: Grid, start: Cell, goal: Cell, stats: Optional[dict] = None) -> Optional[List[Cell]]:
    """Classic A* over (row, col) states. Rubble is treated as a permanent wall."""
    if start == goal:
        return [start]

    open_heap: List[Tuple[int, int, Cell]] = [(manhattan(start, goal), 0, start)]
    came_from: Dict[Cell, Cell] = {}
    g_score: Dict[Cell, int] = {start: 0}
    closed: set = set()

    while open_heap:
        _f, g, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        closed.add(current)
        if stats is not None:
            stats["nodes_expanded"] = stats.get("nodes_expanded", 0) + 1

        if current == goal:
            return _reconstruct(came_from, current)

        for nxt in grid.neighbors(current):
            if grid.is_wall(nxt) or grid.is_rubble(nxt):
                continue
            ng = g + 1
            if ng < g_score.get(nxt, float("inf")):
                g_score[nxt] = ng
                came_from[nxt] = current
                heapq.heappush(open_heap, (ng + manhattan(nxt, goal), ng, nxt))

    return None


def space_time_astar(
    grid: Grid,
    start: Cell,
    goal: Cell,
    table: ReservationTable,
    open_time: Dict[Cell, float],
    start_time: int = 0,
    hold_steps: int = 0,
    final: bool = False,
    agent_id: Optional[str] = None,
    stats: Optional[dict] = None,
) -> Optional[List[Tuple[Cell, int]]]:
    """Search over (cell, t) states with 4 moves + WAIT.

    Goal test:
      - if `final`, the goal is a permanent stop: it must be free from arrival
        until the horizon (`table.max_time`), otherwise a later-planned robot
        could drive through our parked one.
      - otherwise, the goal only needs to stay free for `hold_steps` timesteps
        after arrival (e.g. an Engineer's CLEAR, or a Medic's RESCUE, before it
        moves on / or before a later segment re-checks the "final" condition).

    If the window isn't free at arrival, this is simply not treated as a goal
    yet; the agent can still WAIT at the goal cell (it is a normal state) until
    the window opens up, or the search fails at the horizon.
    """
    max_time = table.max_time
    if start_time > max_time:
        return None

    open_heap: List[Tuple[int, int, Cell, int]] = [
        (manhattan(start, goal), start_time, start, start_time)
    ]
    came_from: Dict[Tuple[Cell, int], Tuple[Cell, int]] = {}
    g_score: Dict[Tuple[Cell, int], int] = {(start, start_time): 0}
    closed: set = set()

    def goal_ok(cell: Cell, t: int) -> bool:
        # The CLEAR/RESCUE that follows arrival must also finish inside the
        # horizon; window_free() clamps to max_time, so check it here.
        if t + hold_steps > max_time:
            return False
        if final:
            return table.window_free(cell, t, max_time, ignore_agent=agent_id)
        return table.window_free(cell, t, t + hold_steps, ignore_agent=agent_id)

    while open_heap:
        _f, g, cell, t = heapq.heappop(open_heap)
        if (cell, t) in closed:
            continue
        closed.add((cell, t))
        if stats is not None:
            stats["nodes_expanded"] = stats.get("nodes_expanded", 0) + 1

        if cell == goal and goal_ok(cell, t):
            return _reconstruct_st(came_from, (cell, t))

        if t >= max_time:
            continue

        nt = t + 1
        for nxt in (cell, *grid.neighbors(cell)):
            if not grid.is_passable(nxt, nt, open_time):
                continue
            if not table.is_vertex_free(nxt, nt, ignore_agent=agent_id):
                continue
            if nxt != cell and not table.is_edge_free(cell, nxt, t, ignore_agent=agent_id):
                continue

            ng = g + 1
            key = (nxt, nt)
            if ng < g_score.get(key, float("inf")):
                g_score[key] = ng
                came_from[key] = (cell, t)
                heapq.heappush(open_heap, (ng + manhattan(nxt, goal), ng, nxt, nt))

    return None


def _reconstruct(came_from: Dict[Cell, Cell], current: Cell) -> List[Cell]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def _reconstruct_st(
    came_from: Dict[Tuple[Cell, int], Tuple[Cell, int]],
    current: Tuple[Cell, int],
) -> List[Tuple[Cell, int]]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path
