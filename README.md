# RescueSync

Cooperative multi-agent rescue planner. Engineers clear rubble, Medics
rescue victims, and everyone shares a single space-time reservation table so
no two robots ever occupy the same cell at the same time or swap places.

The project ships three planner modes side by side so you can see the
improvement at each step:

| Mode | Reservations | Rubble clearing | Result |
|---|---|---|---|
| **Independent A\*** | off | off | robots collide; blocked victims unreachable |
| **Cooperative A\*** | on | off | 0 collisions; blocked victims still fail |
| **RescueSync** | on | on | 0 collisions; every reachable victim rescued |

See [`CLAUDE.md`](CLAUDE.md) for the full system design, algorithm details,
validation strategy, and known limitations.

## Quickstart

### 1. Core engine (Python)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

# Plan a scenario headlessly, print metrics as JSON
python main.py --scenario scenarios/blocked_victim.json --mode rescuesync

# Same, but with the Pygame demo (Space=play/pause, arrows=step, 1/2/3=mode, R=restart)
python main.py --scenario scenarios/blocked_victim.json --mode cooperative --gui

# Run the test suite (26 tests: unit + the 11 scenario tests)
pytest

# Regenerate the Review-2 experiment graphs -> experiments/output/*.png
python -m rescuesync.experiments
```

### 2. Web UI (backend + frontend)

The web UI is the primary, polished demo. It's a FastAPI backend that runs
the exact same `rescuesync/` planner, plus a React + Tailwind + shadcn/ui
frontend that visualizes it.

```bash
# Terminal 1 — backend (from the repo root)
pip install -r requirements.txt
uvicorn backend.app:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The dev server proxies `/api/*` to the
backend on port 8000. Pick a scenario, switch between Independent /
Cooperative / RescueSync, and scrub the timeline. Collisions flash red on
the grid and are counted live in the metrics panel.

Keyboard shortcuts (mirroring the Pygame demo): `Space` play/pause, `←`/`→`
step, `1`/`2`/`3` switch mode, `R` restart.

## Repository layout

```
rescuesync/     the graded core engine — grid, agents, A*, planner, simulator, metrics
scenarios/      9 JSON scenario files (see CLAUDE.md §10 for what each proves)
tests/          pytest: unit tests + the 11 scenario tests
backend/        FastAPI wrapper exposing rescuesync/ over HTTP
frontend/       React + Vite + TypeScript + Tailwind + shadcn/ui
main.py         CLI entry point (headless or --gui)
```

## Demo script (~5 minutes)

1. **Independent A\*** on `crossing`: robots collide, flashes appear.
   *"Individually optimal paths collide."*
2. **Cooperative A\*** on `crossing`: 0 collisions, one robot waits. Switch
   to `blocked_victim`: the Medic never reaches the victim.
   *"No collisions, but the blocked victim is never reached."*
3. **RescueSync** on `blocked_victim`: the Engineer clears the rubble (it
   changes color), the Medic waits then passes through, victim rescued.
4. `large_map`: 12 robots, several rubble cells, all reachable victims
   rescued with 0 collisions.
5. Show `experiments/output/*.png`, then run `pytest` live.

## Known limitations

Prioritized planning is incomplete (a different agent priority order can
succeed where another fails — see `scenarios/priority_order.json`); the map
is assumed fully known ahead of time; task assignment is fixed in the
scenario file, not decided by the planner. Full list in `CLAUDE.md` §13.
