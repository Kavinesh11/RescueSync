"""Shared space-time reservation table used by Cooperative / RescueSync modes."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

Cell = Tuple[int, int]


class ReservationTable:
    def __init__(self, max_time: int):
        self.max_time = max_time
        self.vertex: Dict[Tuple[Cell, int], str] = {}
        self.edge: Dict[Tuple[Cell, Cell, int], str] = {}

    def is_vertex_free(self, cell: Cell, t: int, ignore_agent: Optional[str] = None) -> bool:
        owner = self.vertex.get((cell, t))
        return owner is None or owner == ignore_agent

    def is_edge_free(self, frm: Cell, to: Cell, t: int, ignore_agent: Optional[str] = None) -> bool:
        """No agent may traverse (to -> frm) at the same timestep (a swap conflict)."""
        owner = self.edge.get((to, frm, t))
        return owner is None or owner == ignore_agent

    def window_free(self, cell: Cell, t_start: int, t_end: int, ignore_agent: Optional[str] = None) -> bool:
        t_end = min(t_end, self.max_time)
        for t in range(t_start, t_end + 1):
            if not self.is_vertex_free(cell, t, ignore_agent):
                return False
        return True

    def reserve_vertex(self, cell: Cell, t: int, agent_id: str) -> None:
        self.vertex[(cell, t)] = agent_id

    def reserve_edge(self, frm: Cell, to: Cell, t: int, agent_id: str) -> None:
        self.edge[(frm, to, t)] = agent_id

    def reserve_window(self, cell: Cell, t_start: int, t_end: int, agent_id: str) -> None:
        t_end = min(t_end, self.max_time)
        for t in range(t_start, t_end + 1):
            self.reserve_vertex(cell, t, agent_id)

    def clear_agent_window(self, cell: Cell, t_start: int, t_end: int, agent_id: str) -> None:
        """Remove `agent_id`'s own reservations, e.g. to release a placeholder."""
        t_end = min(t_end, self.max_time)
        for t in range(t_start, t_end + 1):
            key = (cell, t)
            if self.vertex.get(key) == agent_id:
                del self.vertex[key]

    def release_agent(self, agent_id: str) -> None:
        """Remove every vertex and edge reservation held by `agent_id`."""
        self.vertex = {k: v for k, v in self.vertex.items() if v != agent_id}
        self.edge = {k: v for k, v in self.edge.items() if v != agent_id}

    def reserve_path(self, path: List[Tuple[Cell, int]], agent_id: str) -> None:
        """Reserve every vertex and edge of a (cell, t) path, in order."""
        for cell, t in path:
            self.reserve_vertex(cell, t, agent_id)
        for (c1, t1), (c2, _t2) in zip(path, path[1:]):
            self.reserve_edge(c1, c2, t1, agent_id)
