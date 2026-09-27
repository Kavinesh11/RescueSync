"""plan_all(): priority-ordered planning across the three modes.

Mode              Reservations   Rubble clearing   Expected result
Independent A*    off            off               collisions; blocked victims unreachable
Cooperative A*    on             off                0 collisions; blocked victims still fail
RescueSync        on             on                 0 collisions; Engineers open the routes so every victim is rescued

Engineers are always planned before Medics: a Medic's search needs to know
each rubble's open_time, and that time only exists once the responsible
Engineer has been planned. Within each role, agents are planned in scenario
list order - that order is each agent's priority.
"""
from __future__ import annotations

import time
from enum import Enum
from typing import Dict

from .agents import BaseAgent, EngineerAgent, MedicAgent, Cell, agent_from_dict
from .astar import plain_astar, space_time_astar
from .environment import INF, Grid
from .reservation import ReservationTable


class Mode(str, Enum):
    INDEPENDENT = "independent"
    COOPERATIVE = "cooperative"
    RESCUESYNC = "rescuesync"


class PlanResult:
    def __init__(self) -> None:
        self.agents: Dict[str, BaseAgent] = {}
        self.open_time: Dict[Cell, float] = {}
        self.stats: dict = {"nodes_expanded": 0}
        self.planning_time_ms: float = 0.0
        self.mode: str = ""
        self.max_time: int = 0


def plan_all(scenario: dict, mode: Mode) -> PlanResult:
    t0 = time.perf_counter()

    grid = Grid.from_scenario(scenario)
    clear_time = scenario.get("clear_time", 2)
    rescue_time = scenario.get("rescue_time", 2)
    max_time = scenario.get("max_time", 100)

    agents = [agent_from_dict(a) for a in scenario["agents"]]
    for a in agents:
        grid.validate_cell(a.start, f"{a.id}.start")
        if isinstance(a, EngineerAgent):
            grid.validate_cell(a.stand, f"{a.id}.stand")
            grid.validate_cell(a.park, f"{a.id}.park")
        if isinstance(a, MedicAgent):
            grid.validate_cell(a.victim, f"{a.id}.victim")

    engineers = [a for a in agents if isinstance(a, EngineerAgent)]
    medics = [a for a in agents if isinstance(a, MedicAgent)]

    result = PlanResult()
    result.mode = mode.value
    result.max_time = max_time

    table = ReservationTable(max_time=max_time)
    for a in agents:
        # Every agent physically occupies its start cell until it is actually
        # planned and moves. Placeholder-reserve the whole horizon so that an
        # earlier-priority agent can't plan a final resting place on top of a
        # not-yet-planned agent that hasn't had the chance to step aside yet.
        # `_plan_engineer`/`_plan_medic` release exactly what each agent uses
        # once its real path is known (or re-freeze it forever on failure).
        table.reserve_window(a.start, 0, max_time, a.id)
        a.schedule = [a.start]

    open_time: Dict[Cell, float] = {r: INF for r in grid.rubble}
    stats = result.stats

    use_reservations = mode in (Mode.COOPERATIVE, Mode.RESCUESYNC)
    use_clearing = mode == Mode.RESCUESYNC

    for eng in engineers:
        _plan_engineer(eng, grid, table, open_time, clear_time, max_time, use_reservations, use_clearing, stats)

    for med in medics:
        _plan_medic(med, grid, table, open_time, rescue_time, max_time, use_reservations, stats)

    result.agents = {a.id: a for a in agents}
    result.open_time = open_time
    result.planning_time_ms = (time.perf_counter() - t0) * 1000
    return result


def _apply_path(agent: BaseAgent, path_with_time) -> None:
    """Append a (cell, t) path to the agent's schedule.

    A step where the cell repeats is a WAIT action taken by the search
    itself (e.g. to dodge another robot, or to wait for rubble to open) --
    distinct from the CLEAR/RESCUE hold padding added by `_pad_schedule`,
    which is a deliberate action, not a wait.
    """
    for cell, _t in path_with_time[1:]:
        if cell == agent.schedule[-1]:
            agent.wait_count += 1
        agent.schedule.append(cell)


def _pad_schedule(agent: BaseAgent, upto_t: int) -> None:
    last = agent.schedule[-1]
    while len(agent.schedule) - 1 < upto_t:
        agent.schedule.append(last)


def _freeze_in_place(table: ReservationTable, agent: BaseAgent, max_time: int) -> None:
    """An agent that fails mid-mission never moves again from here on out."""
    last_cell = agent.schedule[-1]
    last_t = len(agent.schedule) - 1
    table.reserve_window(last_cell, last_t, max_time, agent.id)


def _plan_engineer(
    eng: EngineerAgent,
    grid: Grid,
    table: ReservationTable,
    open_time: Dict[Cell, float],
    clear_time: int,
    max_time: int,
    use_reservations: bool,
    use_clearing: bool,
    stats: dict,
) -> None:
    if not use_reservations:
        path = plain_astar(grid, eng.start, eng.stand, stats)
        if path is None:
            eng.failed = True
            return
        eng.schedule = list(path)
        arrival = len(path) - 1
        eng.clear_start_time = arrival
        if use_clearing:
            open_time[eng.rubble] = arrival + clear_time
        for _ in range(clear_time):
            eng.schedule.append(eng.stand)

        path2 = plain_astar(grid, eng.stand, eng.park, stats)
        if path2 is None:
            eng.failed = True
            return
        eng.schedule.extend(path2[1:])
        eng.finish_time = len(eng.schedule) - 1
        return

    table.clear_agent_window(eng.start, 0, max_time, eng.id)

    path1 = space_time_astar(
        grid, eng.start, eng.stand, table, open_time,
        start_time=0, hold_steps=clear_time, final=False,
        agent_id=eng.id, stats=stats,
    )
    if path1 is None:
        eng.failed = True
        _freeze_in_place(table, eng, max_time)
        return
    table.reserve_path(path1, eng.id)
    arrival = path1[-1][1]
    hold_end = arrival + clear_time
    table.reserve_window(eng.stand, arrival, hold_end, eng.id)
    eng.clear_start_time = arrival
    if use_clearing:
        open_time[eng.rubble] = hold_end

    _apply_path(eng, path1)
    _pad_schedule(eng, hold_end)

    path2 = space_time_astar(
        grid, eng.stand, eng.park, table, open_time,
        start_time=hold_end, hold_steps=0, final=True,
        agent_id=eng.id, stats=stats,
    )
    if path2 is None:
        eng.failed = True
        if table.window_free(eng.stand, hold_end, max_time, ignore_agent=eng.id):
            # Stuck at the stand, but nobody planned earlier needs this cell
            # later on, so the rubble is still cleared and the robot stays put.
            _freeze_in_place(table, eng, max_time)
            return
        # Staying at the stand forever would collide with an earlier-planned
        # agent's path. Roll the whole mission back: the robot never leaves its
        # start cell (still free, it was placeholder-reserved until now) and
        # its rubble is never cleared.
        table.release_agent(eng.id)
        open_time[eng.rubble] = INF
        eng.schedule = [eng.start]
        eng.wait_count = 0
        eng.clear_start_time = None
        _freeze_in_place(table, eng, max_time)
        return
    table.reserve_path(path2, eng.id)
    arrival2 = path2[-1][1]
    table.reserve_window(eng.park, arrival2, max_time, eng.id)
    _apply_path(eng, path2)
    eng.finish_time = arrival2


def _plan_medic(
    med: MedicAgent,
    grid: Grid,
    table: ReservationTable,
    open_time: Dict[Cell, float],
    rescue_time: int,
    max_time: int,
    use_reservations: bool,
    stats: dict,
) -> None:
    if not use_reservations:
        path = plain_astar(grid, med.start, med.victim, stats)
        if path is None:
            med.failed = True
            return
        med.schedule = list(path)
        arrival = len(path) - 1
        med.rescue_start_time = arrival
        for _ in range(rescue_time):
            med.schedule.append(med.victim)
        med.finish_time = len(med.schedule) - 1
        return

    table.clear_agent_window(med.start, 0, max_time, med.id)

    path = space_time_astar(
        grid, med.start, med.victim, table, open_time,
        start_time=0, hold_steps=rescue_time, final=True,
        agent_id=med.id, stats=stats,
    )
    if path is None:
        med.failed = True
        _freeze_in_place(table, med, max_time)
        return
    table.reserve_path(path, med.id)
    arrival = path[-1][1]
    med.rescue_start_time = arrival
    hold_end = arrival + rescue_time
    table.reserve_window(med.victim, arrival, max_time, med.id)

    _apply_path(med, path)
    _pad_schedule(med, hold_end)
    med.finish_time = hold_end
