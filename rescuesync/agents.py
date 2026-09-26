"""BaseAgent, EngineerAgent, MedicAgent — role data and the executed schedule."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

Cell = Tuple[int, int]


@dataclass
class BaseAgent:
    id: str
    start: Cell
    role: str
    schedule: List[Cell] = field(default_factory=list)
    failed: bool = False
    finish_time: Optional[int] = None
    wait_count: int = 0


@dataclass
class EngineerAgent(BaseAgent):
    rubble: Cell = (0, 0)
    stand: Cell = (0, 0)
    park: Cell = (0, 0)
    clear_start_time: Optional[int] = None


@dataclass
class MedicAgent(BaseAgent):
    victim: Cell = (0, 0)
    rescue_start_time: Optional[int] = None


def agent_from_dict(d: dict) -> BaseAgent:
    role = d["role"]
    if role == "engineer":
        return EngineerAgent(
            id=d["id"],
            start=tuple(d["start"]),
            role=role,
            rubble=tuple(d["rubble"]),
            stand=tuple(d["stand"]),
            park=tuple(d["park"]),
        )
    if role == "medic":
        return MedicAgent(
            id=d["id"],
            start=tuple(d["start"]),
            role=role,
            victim=tuple(d["victim"]),
        )
    raise ValueError(f"unknown agent role {role!r}")
