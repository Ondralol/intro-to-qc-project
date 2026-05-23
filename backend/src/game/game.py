import random

from game.game_helper import GamePhase
from game.game_helper import Target

import quokka.quokka

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
        # Puzzle the player most recently requested but hasn't yet resolved.
        self.active_puzzle: dict = {}  # player_id -> Puzzle        
        self.radar_ready: set = set()  # players who passed their puzzle and can fire radar this turn

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


    def issue_puzzle(self, player_id: str, difficulty: str):
        """Roll a fresh puzzle of the given difficulty for the player."""
        from game.puzzle import roll_puzzle

        if self.phase != GamePhase.FIRING:
            raise ValueError("Puzzles only available during firing phase")
        if player_id not in (self.player_a_id, self.player_b_id):
            raise ValueError("Unknown player")

        p = roll_puzzle(difficulty)
        self.active_puzzle[player_id] = p
        return p

    def submit_puzzle(self, player_id: str, gates: list[str]) -> dict:
        """Evaluate the player's gate sequence. Unlocks radar this turn if passed."""
        from quokka.quokka import evaluate_puzzle

        p = self.active_puzzle.pop(player_id, None)
        if not p:
            raise ValueError("No active puzzle for this player")

        result = evaluate_puzzle(p, gates)
        if result["passed"]:
            self.radar_ready.add(player_id)
        return result

    def radar_scan(self, player_id: str, cells: list[tuple[int, int]]) -> list[dict]:
        """Reconstruct quantum state via Quokka and return per-cell probabilities."""
        from quokka.quokka import radar_scan as quokka_radar_scan

        enemy_id = self.player_a_id if self.player_a_id != player_id else self.player_b_id
        enemy_targets = self.targets[enemy_id]

        # Map cells to which enemy target qubits they overlap with.
        cell_set = set(cells)
        cell_info: dict[tuple, tuple] = {}  # cell -> (target, anchor)
        scan_qubits: set[int] = set()
        for t in enemy_targets:
            for cell in t.anchor_a:
                if cell in cell_set:
                    cell_info[cell] = (t, "a")
                    scan_qubits.add(t.qubit_index)
            for cell in t.anchor_b:
                if cell in cell_set:
                    cell_info[cell] = (t, "b")
                    scan_qubits.add(t.qubit_index)

        if not scan_qubits:
            return [{"cell": list(c), "probability": 0.0} for c in cells]

        # Probability of anchor B for all targets
        qubit_p1 = quokka_radar_scan(enemy_targets, self.ENTANGLED_PAIRS, list(scan_qubits))

        # Map the qubit probabilities back to the cells
        result = []
        for cell in cells:
            if cell not in cell_info:
                result.append({"cell": list(cell), "probability": 0.0})
            else:
                t, anchor = cell_info[cell]
                p1 = qubit_p1[t.qubit_index]
                prob = (1.0 - p1) if anchor == "a" else p1
                result.append({"cell": list(cell), "probability": prob})
        return result

    def fire(self, player_id, coord: tuple[int, int]):
        enemy_id = self.player_a_id if self.player_a_id != player_id else self.player_b_id
        enemy_targets = self.targets[enemy_id]

        found_target = None
        found_anchor = None
        # Find the target
        for target in enemy_targets:
            # Try every cell in anchor A
            for cell in target.anchor_a:
                if coord == cell:
                    found_target = target
                    found_anchor = "A"
                    break

            # Try every cell in anchor B
            for cell in target.anchor_b:
                if coord == cell:
                    found_target = target
                    found_anchor = "B"
                    break
            
            if found_target:
                break
        
        # If we hit, we continue to play, otherwise the enemy plays
        miss_turn = enemy_id
        hit_turn = player_id

        # Case A - complete miss
        if not found_target:
            return {"result": "miss", "cell": list(coord), "destroyed_cells": [], "pings": [], "next_turn": miss_turn, "game_over": False, "winner": None}

        # Case B - first interaction, qubit has not collapsed
        if not found_target.collapsed:
            pair = next(p for p in self.ENTANGLED_PAIRS if found_target.qubit_index in p)
            partner_qubit = pair[0] if found_target.qubit_index == pair[1] else pair[1]
            partner_target = next(t for t in enemy_targets if t.qubit_index == partner_qubit)

            # pair[0] is the control qubit (Ry applied to it)
            if found_target.qubit_index == pair[0]:
                t1, t2 = found_target, partner_target
            else:
                t1, t2 = partner_target, found_target

            outcome = quokka.quokka.fire_shot(t1, t2)  # "00" or "11"
            t1.value = outcome[0]
            t2.value = outcome[1]
            t1.collapsed = True
            t2.collapsed = True

            # Losing anchor cells of both targets become pings (revealed as ghost positions)
            # Basically we show the positions where the target is NOT
            pings = []
            for t in [t1, t2]:
                losing_anchor = t.anchor_b if t.value == "0" else t.anchor_a
                for cell in losing_anchor:
                    pings.append(list(cell))

            real_anchor = found_target.anchor_a if found_target.value == "0" else found_target.anchor_b
            # If we hit the correct anchor
            if coord in real_anchor:
                found_target.hit_cells.add(coord)
                # If we completely destroyed the target
                if found_target.hit_cells >= set(real_anchor):
                    destroyed_cells = [list(c) for c in real_anchor]
                    game_over, winner = self._check_game_over(enemy_id)
                    return {"result": "destroyed", "cell": list(coord), "destroyed_cells": destroyed_cells, "pings": pings, "next_turn": hit_turn, "game_over": game_over, "winner": winner}
                return {"result": "hit", "cell": list(coord), "destroyed_cells": [], "pings": pings, "next_turn": hit_turn, "game_over": False, "winner": None}
            return {"result": "miss", "cell": list(coord), "destroyed_cells": [], "pings": pings, "next_turn": miss_turn, "game_over": False, "winner": None}

        # Case C - subsequent hits on an already collapsed target
        real_anchor = found_target.anchor_a if found_target.value == "0" else found_target.anchor_b
        # If we hit the correct anchor
        if coord in real_anchor:
            found_target.hit_cells.add(coord)
            # If we completely destroyed the target
            if found_target.hit_cells >= set(real_anchor):
                destroyed_cells = [list(c) for c in real_anchor]
                game_over, winner = self._check_game_over(enemy_id)
                return {"result": "destroyed", "cell": list(coord), "destroyed_cells": destroyed_cells, "pings": [], "next_turn": hit_turn, "game_over": game_over, "winner": winner}
            return {"result": "hit", "cell": list(coord), "destroyed_cells": [], "pings": [], "next_turn": hit_turn, "game_over": False, "winner": None}
        return {"result": "miss", "cell": list(coord), "destroyed_cells": [], "pings": [], "next_turn": miss_turn, "game_over": False, "winner": None}

    def _check_game_over(self, loser_id: str):
        # Check all targets
        for target in self.targets[loser_id]:
            if not target.collapsed:
                return False, None
            real_anchor = target.anchor_a if target.value == "0" else target.anchor_b
            if target.hit_cells < set(real_anchor):
                return False, None
        winner_id = self.player_b_id if loser_id == self.player_a_id else self.player_a_id
        self.phase = GamePhase.FINISHED
        self.winner = winner_id
        return True, winner_id

    def disconnected(self):
        self.phase = GamePhase.DISCONNECTED

        