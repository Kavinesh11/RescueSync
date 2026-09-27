"""The 11 scenario tests from CLAUDE.md section 12 (Testing), plus regressions."""
import pytest

from rescuesync.astar import manhattan
from rescuesync.experiments import random_scenario
from rescuesync.metrics import compute_metrics
from rescuesync.planner import Mode, plan_all


def _run(scenario, mode):
    result = plan_all(scenario, mode)
    return result, compute_metrics(result)


# 1. Single robot, open map -> optimal path length equals plain A*'s answer.
def test_01_single_robot_open_map_is_optimal(load_scenario):
    scenario = load_scenario("open_single")
    agent = scenario["agents"][0]
    expected = manhattan(tuple(agent["start"]), tuple(agent["victim"]))
    for mode in (Mode.INDEPENDENT, Mode.COOPERATIVE, Mode.RESCUESYNC):
        _, m = _run(scenario, mode)
        assert m["victims_rescued"] == 1
        assert m["medic_dependency_wait"] == 0
        assert m["collisions"] == 0
        assert m["makespan"] - scenario["rescue_time"] == expected


# 2. Two robots crossing at one cell -> Mode 1 collides, Mode 3 has 0 collisions with a wait.
def test_02_crossing_robots(load_scenario):
    scenario = load_scenario("crossing")
    _, indep = _run(scenario, Mode.INDEPENDENT)
    assert indep["collisions"] > 0

    _, sync = _run(scenario, Mode.RESCUESYNC)
    assert sync["collisions"] == 0
    assert sync["victims_rescued"] == sync["victims_total"]
    assert sync["wait_actions"] > 0


# 3. Head-on swap in a corridor with a side pocket -> no swap, one robot uses the pocket.
def test_03_head_on_swap_uses_pocket(load_scenario):
    scenario = load_scenario("swap_corridor")
    result, m = _run(scenario, Mode.RESCUESYNC)
    assert m["collisions"] == 0
    assert m["victims_rescued"] == m["victims_total"]
    pocket = (2, 5)
    used_pocket = any(pocket in agent.schedule for agent in result.agents.values())
    assert used_pocket


# 4. Blocked victim (the worked example) -> Mode 2 fails, Mode 3 rescues.
def test_04_blocked_victim(load_scenario):
    scenario = load_scenario("blocked_victim")
    _, coop = _run(scenario, Mode.COOPERATIVE)
    assert coop["victims_rescued"] == 0
    assert "M1" in coop["agents_failed"]

    _, sync = _run(scenario, Mode.RESCUESYNC)
    assert sync["victims_rescued"] == 1
    assert sync["collisions"] == 0


# 5. Medic arrives before rubble is cleared -> it WAITs, dependency wait > 0.
def test_05_medic_waits_for_rubble(load_scenario):
    scenario = load_scenario("blocked_victim")
    _, sync = _run(scenario, Mode.RESCUESYNC)
    assert sync["medic_dependency_wait"] > 0


# 6. Engineer can't reach its rubble -> Engineer and dependent Medic fail cleanly, no hang.
def test_06_engineer_unreachable_fails_cleanly(load_scenario):
    scenario = load_scenario("engineer_unreachable")
    for mode in (Mode.INDEPENDENT, Mode.COOPERATIVE, Mode.RESCUESYNC):
        result, m = _run(scenario, mode)
        assert "E1" in m["agents_failed"]
        assert "M1" in m["agents_failed"]
        assert m["collisions"] == 0


# 7. Victim totally walled in -> failure reported within the time horizon.
def test_07_victim_walled_in_fails_within_horizon(load_scenario):
    scenario = load_scenario("victim_walled_in")
    for mode in (Mode.INDEPENDENT, Mode.COOPERATIVE, Mode.RESCUESYNC):
        _, m = _run(scenario, mode)
        assert m["victims_rescued"] == 0
        assert "M1" in m["agents_failed"]


# 8. Engineer parking never blocks the Medic.
def test_08_engineer_parking_does_not_block_medic(load_scenario):
    scenario = load_scenario("blocked_victim")
    result, m = _run(scenario, Mode.RESCUESYNC)
    engineer = result.agents["E1"]
    medic = result.agents["M1"]
    assert m["collisions"] == 0
    assert medic.finish_time is not None
    assert engineer.park not in medic.schedule


# 9. Two Engineers, two rubble cells in series -> Medic waits for the later clear time.
def test_09_series_rubble_waits_for_later_clear(load_scenario):
    scenario = load_scenario("series_rubble")
    _, coop = _run(scenario, Mode.COOPERATIVE)
    assert coop["victims_rescued"] == 0  # rubble never clears without mode 3

    _, sync = _run(scenario, Mode.RESCUESYNC)
    assert sync["victims_rescued"] == 1
    assert sync["collisions"] == 0
    assert sync["medic_dependency_wait"] > 0


# 10. Priority-order change -> different result / failure (known CA* limitation).
def test_10_priority_order_changes_outcome(load_scenario):
    scenario = load_scenario("priority_order")
    by_id = {a["id"]: a for a in scenario["agents"]}

    forward = dict(scenario)
    forward["agents"] = [by_id["MA"], by_id["MB"]]
    _, forward_metrics = _run(forward, Mode.RESCUESYNC)

    reversed_scn = dict(scenario)
    reversed_scn["agents"] = [by_id["MB"], by_id["MA"]]
    _, reversed_metrics = _run(reversed_scn, Mode.RESCUESYNC)

    assert forward_metrics["agents_failed"] == []
    assert reversed_metrics["agents_failed"] != []
    assert forward_metrics["agents_failed"] != reversed_metrics["agents_failed"]


# 11. Large map, 10+ robots -> 0 collisions.
def test_11_large_map_zero_collisions(load_scenario):
    scenario = load_scenario("large_map")
    assert len(scenario["agents"]) >= 10
    _, m = _run(scenario, Mode.RESCUESYNC)
    assert m["collisions"] == 0


# 12. Regression: an Engineer that clears its rubble but can't reach its park
# cell used to be frozen at its stand on top of an earlier-planned agent's
# path. These generated maps all collided in Cooperative mode before the fix.
@pytest.mark.parametrize("seed, n", [(100, 6), (100, 8), (170, 8), (229, 8), (307, 8), (342, 8), (348, 8)])
def test_12_stuck_engineer_never_collides(seed, n):
    scenario = random_scenario(seed=seed, size=15, num_engineers=n, num_medics=n)
    for mode in (Mode.COOPERATIVE, Mode.RESCUESYNC):
        _, m = _run(scenario, mode)
        assert m["collisions"] == 0
