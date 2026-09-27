"""Unit tests: heuristic, plain A*, reservation table, is_passable, collision checker, scenario validation."""
import pytest

from rescuesync.astar import manhattan, plain_astar, space_time_astar
from rescuesync.environment import Grid
from rescuesync.planner import Mode, plan_all
from rescuesync.reservation import ReservationTable
from rescuesync.simulator import simulate


def test_manhattan_heuristic():
    assert manhattan((0, 0), (0, 0)) == 0
    assert manhattan((0, 0), (3, 4)) == 7
    assert manhattan((2, 2), (0, 0)) == 4


def test_plain_astar_open_grid_is_optimal():
    grid = Grid(["#####", "#...#", "#...#", "#...#", "#####"])
    path = plain_astar(grid, (1, 1), (3, 3))
    assert path is not None
    assert len(path) - 1 == manhattan((1, 1), (3, 3))
    assert path[0] == (1, 1) and path[-1] == (3, 3)


def test_plain_astar_trivial_start_equals_goal():
    grid = Grid(["###", "#.#", "###"])
    assert plain_astar(grid, (1, 1), (1, 1)) == [(1, 1)]


def test_plain_astar_no_path_through_wall():
    grid = Grid(["#####", "#.#.#", "#.#.#", "#####"])
    assert plain_astar(grid, (1, 1), (1, 3)) is None


def test_plain_astar_treats_rubble_as_wall():
    grid = Grid(["#####", "#.R.#", "#####"])
    assert plain_astar(grid, (1, 1), (1, 3)) is None


def test_grid_rejects_unknown_symbol():
    import pytest

    with pytest.raises(ValueError):
        Grid(["#####", "#.X.#", "#####"])


def test_grid_rejects_ragged_rows():
    import pytest

    with pytest.raises(ValueError):
        Grid(["#####", "#.#", "#####"])


def test_is_passable_before_and_after_open_time():
    grid = Grid(["#####", "#.R.#", "#####"])
    rubble = (1, 2)
    open_time = {rubble: 5}
    assert grid.is_passable(rubble, 4, open_time) is False
    assert grid.is_passable(rubble, 5, open_time) is True
    assert grid.is_passable(rubble, 100, open_time) is True


def test_is_passable_wall_never_passable():
    grid = Grid(["#####", "#.#.#", "#####"])
    assert grid.is_passable((1, 2), 0, {}) is False
    assert grid.is_passable((1, 2), 10_000, {}) is False


def test_reservation_table_blocks_vertex_conflict():
    table = ReservationTable(max_time=10)
    table.reserve_vertex((1, 1), 3, "A")
    assert table.is_vertex_free((1, 1), 3) is False
    assert table.is_vertex_free((1, 1), 3, ignore_agent="A") is True
    assert table.is_vertex_free((1, 1), 4) is True


def test_reservation_table_blocks_swap_conflict():
    table = ReservationTable(max_time=10)
    table.reserve_edge((1, 2), (1, 1), 3, "A")
    # B tries to move (1,1) -> (1,2) at the same timestep: a swap.
    assert table.is_edge_free((1, 1), (1, 2), 3) is False
    assert table.is_edge_free((1, 1), (1, 2), 3, ignore_agent="A") is True


def test_space_time_astar_waits_for_vertex_conflict():
    grid = Grid(["#####", "#...#", "#####"])
    table = ReservationTable(max_time=10)
    open_time = {}
    table.reserve_vertex((1, 2), 1, "blocker")
    path = space_time_astar(grid, (1, 1), (1, 3), table, open_time, final=True, agent_id="A")
    assert path is not None
    cells = [c for c, _t in path]
    assert (1, 1) in cells  # waited at least once before proceeding


def test_collision_checker_detects_vertex_collision():
    class Fake:
        def __init__(self, schedule):
            self.schedule = schedule
            self.finish_time = len(schedule) - 1

    class FakeResult:
        pass

    result = FakeResult()
    result.agents = {
        "A": Fake([(0, 0), (0, 1), (0, 2)]),
        "B": Fake([(0, 2), (0, 1), (0, 0)]),
    }
    sim = simulate(result)
    kinds = {c["kind"] for c in sim["collisions"]}
    assert "vertex" in kinds


def test_collision_checker_detects_swap_collision():
    class Fake:
        def __init__(self, schedule):
            self.schedule = schedule

    class FakeResult:
        pass

    result = FakeResult()
    result.agents = {
        "A": Fake([(0, 1), (0, 2)]),
        "B": Fake([(0, 2), (0, 1)]),
    }
    sim = simulate(result)
    kinds = {c["kind"] for c in sim["collisions"]}
    assert "swap" in kinds


def test_collision_checker_clean_paths_have_no_collisions():
    class Fake:
        def __init__(self, schedule):
            self.schedule = schedule

    class FakeResult:
        pass

    result = FakeResult()
    result.agents = {
        "A": Fake([(0, 0), (0, 1), (0, 2)]),
        "B": Fake([(2, 0), (2, 1), (2, 2)]),
    }
    sim = simulate(result)
    assert sim["collisions"] == []


def _scenario_with(**changes):
    """blocked_victim, with fields of E1 / M1 overridden (or extra agents added)."""
    agents = [
        {"id": "E1", "role": "engineer", "start": [1, 2], "rubble": [2, 3], "stand": [1, 3], "park": [1, 5]},
        {"id": "M1", "role": "medic", "start": [1, 1], "victim": [3, 5]},
    ]
    agents[0].update(changes.pop("E1", {}))
    agents[1].update(changes.pop("M1", {}))
    agents += changes.pop("extra", [])
    return {
        "grid": ["#######", "#.....#", "###R###", "#....V#", "#######"],
        "clear_time": 2, "rescue_time": 2, "max_time": 30, "agents": agents,
    }


@pytest.mark.parametrize("changes, message", [
    ({"extra": [{"id": "M1", "role": "medic", "start": [1, 4], "victim": [3, 4]}]}, "duplicate agent id"),
    ({"extra": [{"id": "M2", "role": "medic", "start": [1, 1], "victim": [3, 4]}]}, "both start at"),
    ({"E1": {"rubble": [1, 4]}}, "is not a rubble"),
    ({"E1": {"stand": [1, 4]}}, "is not next to its rubble"),
    ({"extra": [{"id": "E2", "role": "engineer", "start": [1, 4], "rubble": [2, 3], "stand": [3, 3], "park": [3, 1]}]},
     "both assigned rubble"),
    ({"M1": {"victim": [0, 0]}}, "is a wall"),
])
def test_plan_all_rejects_invalid_scenarios(changes, message):
    with pytest.raises(ValueError, match=message):
        plan_all(_scenario_with(**changes), Mode.RESCUESYNC)


def test_plan_all_accepts_valid_scenario():
    plan_all(_scenario_with(), Mode.RESCUESYNC)
