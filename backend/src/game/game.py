import random
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class GamePhase(Enum):
    WAITING = "waiting"
    PLACEMENT = "placement"
    FIRING = "firing"
    FINISHED = "finished"


@dataclass
class Target:
    size: str  # "1x2", "2x2", "2x3", "1x4"
    anchor_a: list[tuple[int, int]] # array of coordinates
    anchor_b: list[tuple[int, int]] # array of coordinates
    theta: float  # Ry angle in radians, set by player during placement
    qubit_index: int  # 0-3
    collapsed: bool = False
    value: Optional[str] = None  # "0" = anchor A, "1" = anchor B


class Game:
    ENTANGLED_PAIRS = [(0, 1), (2, 3)]
    QUBIT_BY_SIZE = {"1x2": 0, "2x2": 1, "2x3": 2, "1x4": 3}
    GRID_SIZE = 7

    def __init__(self, game_id, player_a_id):
        self.game_id = game_id
        self.player_a_id = player_a_id
        self.player_b_id = None
        self.phase = GamePhase.WAITING
        self.current_turn = None
        self.winner = None
        self.targets: dict[str, list[Target]] = {}  # player_id -> their 4 targets
        self.ready = set() # players who have placed their targets

    def add_player(self, player_id: str):
        self.player_b_id = player_id
        self.phase = GamePhase.PLACEMENT

    def place_targets(self, player_id: str, raw_targets: list[dict]):
        """ Adds target for player_id.

        The structure of raw_targets (this is send from the frontend)
        raw_targets: list of 4 target objects, one per size.

        [
          {
            "size":     "1x2" | "2x2" | "2x3" | "1x4",
            "anchor_a": [[row, col], ...],
            "anchor_b": [[row, col], ...],
            "theta":    float   // Ry angle in radians
          },
          ...
        ]

        Rows and cols are 0-indexed (0–6). Anchor A and B must not share any tiles.
        No two targets may share any tile across either anchor.
        """

        if self.phase != GamePhase.PLACEMENT:
            raise ValueError("Not in placement phase")
        if player_id in self.ready:
            raise ValueError("Already placed")
        if len(raw_targets) != 4:
            raise ValueError("Must place exactly 4 targets")

        # Check if the targets match the defined structure    
        sizes = [t["size"] for t in raw_targets]
        if sorted(sizes) != sorted(self.QUBIT_BY_SIZE.keys()):
            raise ValueError("Must place one of each target size")

        targets = []

        # This will contain all positions that have a target placed onto them
        all_tiles: set[tuple[int, int]] = set()

        # Iterate over each target and add it to the game
        for raw in raw_targets:
            anchor_a = [tuple(c) for c in raw["anchor_a"]]
            anchor_b = [tuple(c) for c in raw["anchor_b"]]

            # Check if no tile is out of bounds
            for tile in anchor_a + anchor_b:
                if not (0 <= tile[0] < self.GRID_SIZE and 0 <= tile[1] < self.GRID_SIZE):
                    raise ValueError(f"Tile {tile} is out of bounds")

            # Check if the tiles do not share any tile
            if set(anchor_a) & set(anchor_b):
                raise ValueError(f"Anchor A and B overlap for {raw['size']}")
            
            # Check if the tiles do not overal with another target
            for tile in anchor_a + anchor_b:
                if tile in all_tiles:
                    raise ValueError(f"Tile {tile} overlaps with another target")
                all_tiles.add(tile)
            
            # Append the targets
            targets.append(Target(
                size=raw["size"],
                anchor_a=anchor_a,
                anchor_b=anchor_b,
                theta=raw["theta"],
                qubit_index=self.QUBIT_BY_SIZE[raw["size"]],
            ))

        # Add targets to player and make the player ready
        self.targets[player_id] = targets
        self.ready.add(player_id)


        # If both players are ready, set, set the game state to FIRING 
        # TODO Potential race condition
        if len(self.ready) == 2:
            self.phase = GamePhase.FIRING
            # Select who plays first
            self.current_turn = random.choice([self.player_a_id, self.player_b_id])