# CLAUDE.md

This file is the single source of truth for RescueSync's system design,
architecture, algorithms, validation strategy, and known limitations. Read
this before making changes; it explains *why* the code is shaped the way it
is, not just what it does.

## 1. What this project is

RescueSync is a cooperative multi-agent rescue planner built for a course
case-study (PEAS / environment analysis / search-strategy review, then a
tool-selection / demo / testing review). A disaster site is a grid with
walls, rubble, and victims. Two robot roles cooperate:

- **Engineer**: clears rubble (`CLEAR`, 2 timesteps) so cells behind it
  become passable.
- **Medic**: reaches and rescues victims (`RESCUE`, 2 timesteps), sometimes
  only reachable after an Engineer clears the way.

All robots plan with **Cooperative Space-Time A\*** (Silver, 2005): a shared
reservation table over `(cell, time)` prevents any two robots from ever
occupying the same cell at the same time, or swapping cells between two
adjacent timesteps. The system demonstrates three planner modes side by side
so the improvement at each step is visible:

| Mode | Reservations | Rubble clearing | Result |
|---|---|---|---|
| Independent A* | off | off | robots collide; blocked victims unreachable |
| Cooperative A* | on | off | 0 collisions; blocked victims still fail |
| RescueSync | on | on | 0 collisions; every reachable victim is rescued |

**Our actual contribution** (state it exactly like this in the report/viva):
we don't claim a new pathfinding algorithm. We combine Cooperative Space-Time
A* with heterogeneous, role-specific agents and an explicit time-dependent
task dependency — an Engineer's `CLEAR` action changes when a cell becomes
passable, and the Medic's planner uses that time directly, while every agent
stays collision-free. Real-world grounding: RoboCup Rescue Agent Simulation
(police agents clear roads for ambulance agents) and real urban
search-and-rescue robotics.

## 2. Repository layout

```
RescueSync/
├── CLAUDE.md              # this file
├── README.md              # setup + quickstart for humans
├── main.py                # CLI: plan a scenario headlessly, or --gui for Pygame
├── requirements.txt        # pygame, matplotlib, pytest, fastapi, uvicorn
├── pytest.ini
├── rescuesync/             # the graded core engine (pure Python, no UI deps except visualizer.py)
│   ├── environment.py       # Grid: walls/rubble/victims, is_passable()
│   ├── agents.py            # BaseAgent, EngineerAgent, MedicAgent
│   ├── reservation.py       # ReservationTable: vertex + edge (swap) reservations
│   ├── astar.py             # plain_astar() and space_time_astar()
│   ├── planner.py           # plan_all(): the 3 modes, priority order, dependency logic
│   ├── simulator.py         # independent execution + collision checker
│   ├── metrics.py           # all reported metrics
│   ├── experiments.py       # random scenario generator + Review-2 graphs (matplotlib)
│   └── visualizer.py        # Pygame demo (secondary to the web UI, see §8)
├── scenarios/*.json         # 8 hand-designed scenarios + 1 generated stress-test map
├── tests/                   # pytest: unit tests + the 11 scenario tests from §12
├── backend/app.py           # FastAPI: exposes plan_all()/metrics to the web UI
└── frontend/                 # React + Vite + TypeScript + Tailwind + shadcn/ui
```

Scalability: adding robots/rubble/victims means editing a JSON scenario
file, not the code. A new robot role is one new `BaseAgent` subclass. A new
planner mode plugs in behind the same `plan_all()` interface. The simulator's
collision checker is intentionally decoupled from the planner — it only
reads each agent's final `schedule`, so it verifies the planner rather than
trusting it (this is how the collision-leak bug in §7 was actually caught).

## 3. The world model

Grid legend (scenario JSON, `"grid": [...]` — one string per row):

| Symbol | Meaning | Traversable? |
|---|---|---|
| `#` | Wall | Never |
| `.` | Free cell | Always |
| `R` | Rubble | Only from the time it's cleared onwards |
| `V` | Victim | Yes (a Medic stands on it to rescue; cosmetic marker only — the actual victim cell comes from the agent's `victim` field) |

**Cell convention — this is the single most important gotcha in the
codebase: a cell is `(row, col)`, not `(x, y)`.** `"start": [1, 2]` means
row 1, column 2. This was reverse-engineered from the design doc's own
worked example (a grid string `"# M E . . . #"` with `M1 at (1,1), E1 at
(1,2)"` only makes sense as `(row, col)` — M is at row1/col1, E is at
row1/col2). `environment.py`, `astar.py`, `reservation.py` all use this
convention uniformly; the frontend's `GridCanvas` renders `cell[0]` as the
vertical axis and `cell[1]` as the horizontal axis to match.

Modelling assumptions (verbatim, also stated in the Review 1 slides):

1. Rubble and victim locations are known beforehand (e.g. a drone survey).
   Partial observability is future work.
2. Movement is deterministic: a `MOVE` always succeeds.
3. Task assignment is given in the scenario (which Engineer clears which
   rubble, which Medic rescues which victim) — this project is about path
   planning, not task allocation.
4. Time is discrete. One action = one timestep, except `CLEAR` (2 steps) and
   `RESCUE` (2 steps).
5. Every robot's start cell is reserved at `t=0`.

## 4. PEAS and environment properties (Review 1)

| | Engineer | Medic |
|---|---|---|
| Performance | rubble cleared, 0 collisions, early clear time, short path | victim rescued, 0 collisions, short rescue time, few waits |
| Environment | disaster-site grid: walls, rubble, victims, other robots | same |
| Actuators | MOVE (N/S/E/W), WAIT, CLEAR | MOVE (N/S/E/W), WAIT, RESCUE |
| Sensors | grid map, rubble/victim state, reservation table, current time | same, plus rubble clear times |

System-level performance measure: victims rescued / total, zero collisions,
low makespan.

Environment properties: fully **observable** (the planner sees the whole
map and all reservations), **deterministic**, **sequential** (an Engineer's
early clear changes a Medic's later path), **static during planning /
dynamic during execution** (from each robot's view, other robots move and
rubble opens while it executes), **discrete**, **cooperative multi-agent,
heterogeneous**, **known** rules. Each robot is a goal-based agent (searches
for an action sequence to its goal); the system as a whole is utility-based
(it prefers lower-cost joint plans — makespan, waits). A simple reflex agent
fails here: it can't wait for rubble to clear, can't avoid an oncoming robot
in a corridor, and gets stuck.

## 5. The algorithm

### 5.1 Plain A* (`astar.plain_astar`)

State = `(row, col)`. `h(n)` = Manhattan distance to goal. Admissible and
consistent on a 4-connected unit-cost grid: every move changes exactly one
coordinate by 1, so `h` never overestimates and decreases by at most 1 per
step. Complete and optimal for a single robot. Used for: Independent A*
mode, and as the "known correct answer" that `test_01` checks Space-Time A*
against on an open map.

### 5.2 Why plain A* alone fails

Two robots each plan optimally in isolation and can still collide — e.g. one
plans `(1,1)→(1,2)→(1,3)`, another plans `(1,3)→(1,2)→(1,1)`; both are at
`(1,2)` at `t=1`. This one example motivates the whole project.

### 5.3 Space-Time A* (`astar.space_time_astar`)

State = `(cell, t)`. Actions = 4 moves + `WAIT`, every action costs 1 and
advances `t` by 1. Heuristic is still Manhattan (still admissible — `WAIT`
only adds cost, never helps). A successor `(cell2, t+1)` from `(cell1, t)`
is legal only if:

- `cell2` is not a wall, and not un-opened rubble (`t+1 >= open_time[cell2]`)
- `(cell2, t+1)` has no vertex reservation (no vertex conflict)
- `((cell2, cell1), t)` has no edge reservation (no swap conflict — nobody
  is making the reverse move at the same timestep)

**Goal test — the one place this implementation intentionally diverges from
a single monolithic rule**, because Engineers have two distinct kinds of
stop (a temporary stand, then a permanent park) while Medics have one
(rescue-then-park). `space_time_astar` takes two independent parameters:

- `hold_steps`: the goal cell must stay free for `[arrival, arrival +
  hold_steps]` — enough room to run `CLEAR`/`RESCUE` in place.
- `final`: if true, the goal cell must stay free from arrival all the way to
  `table.max_time` — "nobody else may ever drive through our parked robot."

If the window isn't free yet, the state is simply *not* accepted as a goal
(it's just an ordinary passable node) — the agent can `WAIT` there and
re-check later, or the search fails at the horizon. A Medic's final call
passes `final=True` (parks at the victim cell forever after rescuing, which
already covers the `RESCUE` hold). An Engineer's first segment (to its stand
cell) passes `hold_steps=clear_time, final=False` (it's going to leave for
its park cell afterward); its second segment (to its park cell) passes
`final=True`.

### 5.4 The dependency (RescueSync's actual contribution)

- `open_time[rubble] = INF` for every rubble cell at the start. Nobody can
  enter rubble.
- **Engineers are always planned before Medics**, in scenario list order
  (that order is priority): a Medic's search needs to know each rubble's
  open time, and that time only exists once the responsible Engineer has
  been planned.
  1. Space-Time A* to the stand cell (`hold_steps=clear_time`).
  2. Hold there for `clear_time` steps (the stand cell stays reserved).
  3. **Only in RescueSync mode**: `open_time[rubble] = arrival + clear_time`.
  4. Space-Time A* from stand to park (`final=True`), reserved forever after.
- Medics plan after, in list order. A Medic that arrives at rubble before it
  opens simply `WAIT`s — the search discovers this on its own, since `WAIT`
  is a legal action, not special-cased.
- If nobody ever clears a rubble cell the Medic needs, `open_time` stays
  `INF` forever; the search exhausts the reachable `(cell, t)` state space
  bounded by `max_time` and returns `None` — reported as failure, never a
  hang (see `test_06`, `test_07`).

### 5.5 The three modes, implemented as two flags

`plan_all(scenario, mode)` doesn't branch into three code paths — it's one
path gated by two booleans derived from `mode`:

```python
use_reservations = mode in (COOPERATIVE, RESCUESYNC)   # reservation table consulted at all?
use_clearing     = mode == RESCUESYNC                   # open_time actually gets set?
```

When `use_reservations` is false, both roles fall back to `plain_astar` with
rubble treated as a permanent wall, and the reservation table is never
touched — this *is* Independent A*, not a separate implementation.

## 6. The reservation-table subtlety that isn't obvious from the pseudocode

**A not-yet-planned agent still physically exists at its start cell.** The
naive approach — reserve every agent's start only at `t=0` — lets an
earlier-priority agent search find that a not-yet-planned agent's start cell
is "free forever from some future time onward" (because nothing says
otherwise yet) and permanently park there. Then when the later agent is
actually planned, the simulator's independent collision checker (which
assumes a `failed` agent never moves from wherever its schedule last placed
it) reports a genuine, invisible collision between the parked robot and the
one that was still supposedly waiting at its own start. This was caught
empirically during development, not designed in from the start — see the
git history / development notes if you want the exact repro.

**The fix**: at setup, every agent's start cell is reservation-window'd for
`[0, max_time]` under its own id — a placeholder that says "I'm still here
until proven otherwise." The moment an agent's real turn comes up,
`table.clear_agent_window(...)` releases that placeholder before its own
search runs (so it can freely leave its own start), and its real path/park
reservations replace it. If an agent's search fails partway (e.g. it reaches
its stand cell but can never reach its park cell), `_freeze_in_place()`
re-establishes a permanent placeholder at wherever it actually stopped —
because that's the physically true statement: a robot that can't find a
plan doesn't vanish, it just stays put forever.

**The cost of this fix**: it is deliberately conservative in favor of the
zero-collision guarantee. It can make an earlier-planned agent fail where a
less-cautious algorithm might have "gotten lucky" by passing through a
not-yet-active agent's start cell before that agent needed to move (see
`priority_order.json` and `swap_corridor.json` scenario notes below — this
is also *why* agent order matters in some scenarios and had to be chosen
carefully, not arbitrarily).

## 7. Validation strategy

Three layers, each catching a different class of bug:

1. **Unit tests** (`tests/test_units.py`): the Manhattan heuristic, plain
   A* on known grids (including the trivial start==goal case, wall-blocked,
   rubble-as-wall), `Grid` symbol/shape validation, `is_passable` before and
   after `open_time`, the reservation table's vertex/swap rejection, and the
   collision checker against hand-built fake schedules (this is what caught
   the placeholder bug above — the checker doesn't know or trust the
   planner).
2. **Scenario tests** (`tests/test_scenarios.py`): the 11 scenarios from
   §12, each asserting the specific behavior it's designed to demonstrate.
3. **The independent simulator** (`simulator.py`) is re-run over *every*
   scenario in *every* mode as a blanket invariant: Cooperative A* and
   RescueSync must report exactly 0 collisions, always — this is checked
   both in CI (implicitly, via `test_scenarios.py` and `test_units.py`) and
   explicitly across the full scenario set and the 90-run experiment sweep
   (see `experiments.py`, whose `collisions.png` output is a direct
   empirical check of this invariant at scale).

**A note on scenario design** (worth remembering when adding new
scenarios): a scenario where one agent's *goal* coincides with another
agent's *start* cell is not automatically solvable — see §6. When designing
a new scenario, prefer distinct start/goal cells across agents, and if two
agents must fully swap ends of a corridor, verify empirically (not just by
hand) that a pocket exists in the right place — see `swap_corridor.json`,
where the pocket had to be repositioned from the geometric middle to align
with where the two agents' schedules actually cross.

**A note on metrics**: `wait_actions` / `medic_dependency_wait` count actual
`WAIT` actions taken during search (tracked via `agent.wait_count`,
incremented in `_apply_path` when a path step repeats a cell) — deliberately
*not* inferred by scanning the final schedule for repeated cells, because
the `CLEAR`/`RESCUE` hold padding also repeats cells and is a deliberate
action, not a wait. `medic_dependency_wait` is a proxy: it counts *all*
`WAIT`s taken by Medics, which may include waits caused by avoiding another
robot, not only waits caused by rubble. This is a known, documented
simplification — separating "waiting for rubble" from "waiting for another
robot" would require tagging each wait with a cause during search.

## 8. Tools (Review 2)

| Tool | Role | Why |
|---|---|---|
| Python 3.11+ | core engine | course language, fast to prototype |
| `heapq` (stdlib) | A* priority queue | built in; the search itself is hand-written because that's the graded part |
| `json` (stdlib) | scenario files | human-readable, no extra dependency |
| `pytest` | automated tests | simple syntax, one command runs everything |
| `matplotlib` | Review-2 experiment graphs | standard, saves PNGs for the report |
| `Pygame` | secondary desktop demo (`main.py --gui`) | kept for parity with the original tool-selection writeup; the **primary, polished demo is the web UI** below |
| `FastAPI` + `uvicorn` | thin backend | exposes `plan_all()`/`compute_metrics()` as JSON over HTTP so the web UI can drive it; no planning logic lives here, it only serializes `rescuesync/` |
| React + Vite + TypeScript + Tailwind + shadcn/ui | web UI | a stylish, interactive replacement/upgrade for the Pygame demo — same controls (play/pause/step/restart/mode-switch), grid + agents + collision highlighting + live metrics, in a browser |

Considered and rejected: NetworkX (hides the search we're supposed to
implement), Mesa/PettingZoo (agent-sim/RL frameworks, unneeded complexity,
RL is off-syllabus).

## 9. Running everything

```bash
pip install -r requirements.txt

# headless: prints metrics as JSON
python main.py --scenario scenarios/blocked_victim.json --mode rescuesync

# Pygame demo (Space=play/pause, arrows=step, 1/2/3=mode, R=restart)
python main.py --scenario scenarios/blocked_victim.json --mode cooperative --gui

# tests
pytest

# Review-2 experiment graphs -> experiments/output/*.png
python -m rescuesync.experiments

# backend (from repo root)
uvicorn backend.app:app --reload --port 8000

# frontend (separate terminal)
cd frontend && npm install && npm run dev
# open http://localhost:5173 (dev server proxies /api -> http://127.0.0.1:8000)
```

## 10. Scenario catalog (`scenarios/*.json`)

| File | Demonstrates | Ties to test |
|---|---|---|
| `open_single.json` | single robot, open map, matches plain A* | `test_01` |
| `crossing.json` | plus-shaped intersection, simultaneous crossing | `test_02` |
| `swap_corridor.json` | head-on pass in a 1-wide corridor using a side pocket | `test_03` |
| `blocked_victim.json` | the worked example — rubble is the only route | `test_04`, `test_05`, `test_08` |
| `engineer_unreachable.json` | Engineer walled off from its own rubble | `test_06` |
| `victim_walled_in.json` | victim sealed in by walls, no rubble at all | `test_07` |
| `series_rubble.json` | 2 Engineers, 2 rubble cells in series, each with its own pocket to park in | `test_09` |
| `priority_order.json` | prioritized planning's incompleteness — reordering the same 2 agents changes success/failure | `test_10` |
| `large_map.json` | 15x15, 12 robots, generated by `experiments.random_scenario(seed=42, ...)` for determinism | `test_11` |

## 11. Metrics (`metrics.compute_metrics`)

| Metric | Definition |
|---|---|
| `collisions` | vertex + swap conflicts found by the independent simulator |
| `victims_rescued` / `success_rate` | rescued Medics ÷ total Medics |
| `makespan` | finish time of the last agent |
| `sum_of_costs` | sum of every agent's finish time |
| `wait_actions` | total `WAIT` steps across all agents (search-time waits only, see §7) |
| `medic_dependency_wait` | `WAIT` steps taken by Medics specifically |
| `planning_time_ms` | wall-clock time to plan every agent |
| `nodes_expanded` | total A* node expansions across every search call |
| `agents_failed` | ids of agents whose search never reached its goal |

## 12. Testing scenarios (Review 2, mirrors the rubric's testing table)

1. Single robot, open map → optimal path length equals plain A*'s answer.
2. Two robots crossing at one cell → Mode 1 collides; Mode 3 is 0 collisions with a WAIT.
3. Head-on swap in a corridor with a side pocket → Mode 3: no swap, one robot uses the pocket.
4. Blocked victim (the worked example) → Mode 2 fails; Mode 3 rescues.
5. Medic arrives before rubble is cleared → it WAITs; `medic_dependency_wait > 0`.
6. Engineer can't reach its rubble → Engineer and dependent Medic fail cleanly, no hang.
7. Victim totally walled in → failure reported within the time horizon.
8. Engineer parking never blocks the Medic.
9. Two Engineers, two rubble cells in series → Medic waits for the later clear time.
10. Priority-order change → reordering the same agents changes success/failure (known Cooperative A* / prioritized-planning limitation — see §6).
11. Large map, 12 robots → 0 collisions.

Unit tests cover: the Manhattan heuristic, plain A* on known grids, the
reservation table's vertex/swap rejection, `is_passable` before/after
`open_time`, and the collision checker against hand-built schedules.

## 13. Known limitations (state these before anyone asks)

- Prioritized planning is incomplete and not globally optimal — a different
  agent order can succeed where another fails (`test_10`; CBS would fix
  this, out of scope).
- The map, rubble, and victims are assumed fully known ahead of time.
- Task assignment (which Engineer clears which rubble, which Medic rescues
  which victim) is fixed in the scenario file, not decided by the planner.
- `medic_dependency_wait` doesn't distinguish "waiting for rubble" from
  "waiting to avoid another robot" (see §7).
- The reservation-table placeholder scheme (§6) trades some completeness
  for an unconditional zero-collision guarantee; a small number of
  scenarios need agent order or start/goal placement chosen deliberately to
  avoid a self-inflicted deadlock (documented per-scenario where relevant).

## 14. Viva-ready one-liners

- **Heuristic admissible?** Yes — Manhattan distance on a 4-connected
  unit-cost grid never overestimates; obstacles and `WAIT` only add cost.
- **Why add time to the state?** So two robots can use the same cell at
  different times, and so the planner can express "wait here, then go."
- **What's a swap conflict?** Two robots exchanging cells in one step;
  blocked via edge reservations, checked both directions.
- **Why plan Engineers first?** Medics need to know when rubble opens, and
  that time only exists once the Engineer has been planned.
- **What if a Medic arrives early?** It `WAIT`s — discovered by the search
  itself, not special-cased.
- **What if nobody clears the rubble?** `open_time` stays infinite; the
  search hits the horizon and reports failure, never hangs.
- **Is the planner optimal?** Each robot's path is optimal *given* the
  reservations already committed by higher-priority robots. The joint plan
  is not guaranteed optimal — that needs CBS (future work).
- **Is it complete?** No — see `priority_order.json` / `test_10`.
- **Why is the environment dynamic?** Other robots move and rubble opens
  during execution, so from any one robot's view the world changes; it's
  static only during the planning computation itself.
- **How does this scale?** Planning cost grows with the number of robots
  and the time horizon (`experiments.py`'s `planning_time.png`).
