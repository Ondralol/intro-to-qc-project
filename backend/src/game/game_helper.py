from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class GamePhase(Enum):
    WAITING = "waiting"
    PLACEMENT = "placement"
    FIRING = "firing"
    FINISHED = "finished"
    DISCONNECTED = "disconnected"


@dataclass
class Target:
    size: str  # "1x1", "1x2", "1x3", "2x2"
    anchor_a: list[tuple[int, int]] # array of coordinates
    anchor_b: list[tuple[int, int]] # array of coordinates
    theta: float  # Ry angle in radians, set by player during placement
    qubit_index: int  # 0-3
    collapsed: bool = False
    value: Optional[str] = None  # "0" = anchor A, "1" = anchor B
    hit_cells: set = field(default_factory=set)
