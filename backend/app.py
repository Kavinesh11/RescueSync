"""FastAPI backend exposing the RescueSync planner to the web UI.

Run with: uvicorn backend.app:app --reload --port 8000
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rescuesync.metrics import compute_metrics  # noqa: E402
from rescuesync.planner import Mode, plan_all  # noqa: E402

SCENARIOS_DIR = ROOT / "scenarios"

app = FastAPI(title="RescueSync API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODE_MAP = {
    "independent": Mode.INDEPENDENT,
    "cooperative": Mode.COOPERATIVE,
    "rescuesync": Mode.RESCUESYNC,
}


class PlanRequest(BaseModel):
    scenario_name: Optional[str] = None
    scenario: Optional[dict] = None
    mode: str = "rescuesync"


def _list_scenarios() -> list:
    return sorted(p.stem for p in SCENARIOS_DIR.glob("*.json"))


def _load_scenario(name: str) -> dict:
    path = SCENARIOS_DIR / f"{name}.json"
    if not path.exists():
        raise HTTPException(404, f"scenario {name!r} not found")
    return json.loads(path.read_text())


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/scenarios")
def list_scenarios() -> dict:
    scenarios = []
    for name in _list_scenarios():
        data = _load_scenario(name)
        scenarios.append({
            "name": name,
            "description": data.get("description", ""),
            "width": len(data["grid"][0]),
            "height": len(data["grid"]),
            "num_agents": len(data["agents"]),
        })
    return {"scenarios": scenarios}


@app.get("/api/scenarios/{name}")
def get_scenario(name: str) -> dict:
    return _load_scenario(name)


@app.post("/api/plan")
def plan(req: PlanRequest) -> dict:
    if req.mode not in MODE_MAP:
        raise HTTPException(400, f"unknown mode {req.mode!r}, expected one of {sorted(MODE_MAP)}")

    if req.scenario is not None:
        scenario = req.scenario
    elif req.scenario_name is not None:
        scenario = _load_scenario(req.scenario_name)
    else:
        raise HTTPException(400, "must provide scenario_name or scenario")

    try:
        result = plan_all(scenario, MODE_MAP[req.mode])
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    metrics = compute_metrics(result)

    agents_out = {}
    for aid, agent in result.agents.items():
        entry = {
            "id": agent.id,
            "role": agent.role,
            "schedule": [list(c) for c in agent.schedule],
            "failed": agent.failed,
            "finish_time": agent.finish_time,
        }
        if agent.role == "engineer":
            entry.update({
                "rubble": list(agent.rubble),
                "stand": list(agent.stand),
                "park": list(agent.park),
                "clear_start_time": agent.clear_start_time,
            })
        else:
            entry.update({
                "victim": list(agent.victim),
                "rescue_start_time": agent.rescue_start_time,
            })
        agents_out[aid] = entry

    open_time_out = {
        f"{r},{c}": (None if v == float("inf") else v)
        for (r, c), v in result.open_time.items()
    }

    return {
        "mode": req.mode,
        "grid": scenario["grid"],
        "max_time": result.max_time,
        "agents": agents_out,
        "open_time": open_time_out,
        "metrics": metrics,
    }
