import random
from dataclasses import dataclass
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


class Game:
    ENTANGLED_PAIRS = [(0, 1), (2, 3)]
    QUBIT_BY_SIZE = {"1x1": 0, "1x2": 1, "1x3": 2, "2x2": 3}
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


    def play_puzzle(self, gate_sequence, initial_state, target_outcome):
        # TODO
        from demo import evaluate_puzzle

        return evaluate_puzzle(gate_sequence = gate_sequence, 
                               initial_state = initial_state, 
                               target_outcome = target_outcome)
    
    def _measure_qubit(self, qubit_index: int) -> str:
        from collections import Counter
        import requests, json

        qasm = f"""
        OPENQASM 2.0;
        include "qelib1.inc";
        qreg q[4];
        creg c[4];

        // Put qubit into superposition
        h q[{qubit_index}];

        measure q[{qubit_index}] -> c[{qubit_index}];
        """

        request_http = "https://quokka5.quokkacomputing.com/qsim/qasm"
        data = {"script": qasm, "count": 1}

        result = requests.post(request_http, json=data)
        json_obj = json.loads(result.content)

        raw_data = json_obj["result"]["c"]
        outcome = "".join(map(str, raw_data[0]))

        return outcome[qubit_index]

    def fire(self, player_id, coord):
        # TODO Handle all cases based on design doc
        if self.phase != GamePhase.FIRING:
            raise ValueError("Game is not in firing phase")

        if self.current_turn != player_id:
            raise ValueError("Not your turn")

        opponent_id = (
            self.player_b_id if player_id == self.player_a_id else self.player_a_id
        )

        opponent_targets = self.targets[opponent_id]

        hit_target = None
        hit_anchor = None

        # ---------------------------
        # 🔍 Find target hit
        # ---------------------------
        for target in opponent_targets:
            if coord in target.anchor_a:
                hit_target = target
                hit_anchor = "A"
                break
            elif coord in target.anchor_b:
                hit_target = target
                hit_anchor = "B"
                break

        # ---------------------------
        # CASE A: MISS
        # ---------------------------
        if not hit_target:
            return {"type": "miss", "coord": coord}

        # ---------------------------
        # CASE B: FIRST INTERACTION
        # ---------------------------
        if not hit_target.collapsed:

            measured_value = self._measure_qubit(hit_target.qubit_index)

            # Collapse this target
            hit_target.collapsed = True
            hit_target.value = measured_value

            # Collapse entangled pair
            entangled_targets = []

            for a, b in self.ENTANGLED_PAIRS:
                if hit_target.qubit_index == a:
                    pair_index = b
                elif hit_target.qubit_index == b:
                    pair_index = a
                else:
                    continue

                for t in opponent_targets:
                    if t.qubit_index == pair_index:
                        t.collapsed = True
                        t.value = measured_value
                        entangled_targets.append(t)

            correct_anchor = "A" if measured_value == "0" else "B"

            # 🎯 Compute anchor centers (for UI ping)
            def center(anchor):
                r = round(sum(x for x, _ in anchor) / len(anchor))
                c = round(sum(y for _, y in anchor) / len(anchor))
                return (r, c)

            result = {
                "coord": coord,
                "collapsed_to": correct_anchor,
                "entangled": [],
            }

            # Direct vs Indirect
            if hit_anchor == correct_anchor:
                result["type"] = "direct_hit"
            else:
                result["type"] = "indirect_hit"
                result["correct_anchor_center"] = center(
                    hit_target.anchor_a if correct_anchor == "A" else hit_target.anchor_b
                )

            # Entangled reveal
            for t in entangled_targets:
                result["entangled"].append({
                    "qubit": t.qubit_index,
                    "anchor_center": center(
                        t.anchor_a if t.value == "0" else t.anchor_b
                    )
                })

            return result

        # ---------------------------
        # CASE C: CLASSICAL
        # ---------------------------
        actual_anchor = "A" if hit_target.value == "0" else "B"

        if hit_anchor == actual_anchor:
            return {
                "type": "hit",
                "coord": coord
            }
        else:
            return {
                "type": "miss",
                "coord": coord
            }

    # Helper to convert Game → demo format
    def _build_game_state(self):
        state = {}
        for player_targets in self.targets.values():
            for t in player_targets:
                key = f"q{t.qubit_index}"
                state[key] = {
                    "collapsed": t.collapsed,
                    "value": t.value,
                    "theta": t.theta
                }
        return state

    def run_radar(self, scan_qubits):
        # run the radar scan based on the demo.py logic and return the results
        from demo import run_radar
        return run_radar(self._build_game_state(), scan_qubits)

    # def switch_turn(self):
    #     if self.current_turn == self.player_a_id:
    #         self.current_turn = self.player_b_id
    #     else:
    #         self.current_turn = self.player_a_id

    def disconnected(self):
        self.phase = GamePhase.DISCONNECTED

        