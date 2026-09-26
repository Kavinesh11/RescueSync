"""Grid world: walls, rubble, victims.

Cell convention: a cell is (row, col) — row is the vertical index into the
list of grid strings, col is the horizontal index into each string. This
matches the scenario JSON files, e.g. "start": [1, 2] means row 1, col 2.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

Cell = Tuple[int, int]

INF = float("inf")

VALID_SYMBOLS = {"#", ".", "R", "V"}


class Grid:
    def __init__(self, rows: List[str]):
        if not rows:
            raise ValueError("grid must have at least one row")
        width = len(rows[0])
        if width == 0 or any(len(r) != width for r in rows):
            raise ValueError("all grid rows must be non-empty and the same length")

        self.rows_text: List[str] = list(rows)
        self.height = len(rows)
        self.width = width

        self.walls: set = set()
        self.rubble: set = set()
        self.victims: set = set()

        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch not in VALID_SYMBOLS:
                    raise ValueError(f"unknown grid symbol {ch!r} at ({r}, {c})")
                cell = (r, c)
                if ch == "#":
                    self.walls.add(cell)
                elif ch == "R":
                    self.rubble.add(cell)
                elif ch == "V":
                    self.victims.add(cell)

    @classmethod
    def from_scenario(cls, scenario: dict) -> "Grid":
        return cls(scenario["grid"])

    def in_bounds(self, cell: Cell) -> bool:
        r, c = cell
        return 0 <= r < self.height and 0 <= c < self.width

    def is_wall(self, cell: Cell) -> bool:
        return cell in self.walls

    def is_rubble(self, cell: Cell) -> bool:
        return cell in self.rubble

    def is_passable(self, cell: Cell, t: int, open_time: Dict[Cell, float]) -> bool:
        """Whether `cell` can be occupied at time `t`, given rubble open times."""
        if not self.in_bounds(cell):
            return False
        if cell in self.walls:
            return False
        if cell in self.rubble:
            return t >= open_time.get(cell, INF)
        return True

    def neighbors(self, cell: Cell) -> List[Cell]:
        r, c = cell
        candidates = [(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)]
        return [n for n in candidates if self.in_bounds(n)]

    def validate_cell(self, cell: Cell, name: str) -> None:
        if not self.in_bounds(cell):
            raise ValueError(f"{name} {cell} is out of bounds")
        if cell in self.walls:
            raise ValueError(f"{name} {cell} is a wall")
