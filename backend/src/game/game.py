import random

from game.game_helper import GamePhase, Target
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
        self.targets: dict[str, list[Target]] = {}
        self.ready = set()
        # Radar / puzzle state per player
        self.radar_unlocked: dict[str, bool] = {}
        self.active_puzzle: dict[str, dict] = {}  # player_id -> puzzle dict

    def add_player(self, player_id: str):
        self.player_b_id = player_id
        self.phase = GamePhase.PLACEMENT

    def place_targets(self, player_id: str, raw_targets: list[dict]):
        if self.phase != GamePhase.PLACEMENT:
            raise ValueError("Not in placement phase")
        if player_id in self.ready:
            raise ValueError("Already placed")
        if len(raw_targets) != 4:
            raise ValueError("Must place exactly 4 targets")

        sizes = [t["size"] for t in raw_targets]
        if sorted(sizes) != sorted(self.QUBIT_BY_SIZE.keys()):
            raise ValueError("Must place one of each target size")

        targets = []
        all_tiles: set[tuple[int, int]] = set()

        for raw in raw_targets:
            anchor_a = [tuple(c) for c in raw["anchor_a"]]
            anchor_b = [tuple(c) for c in raw["anchor_b"]]

            for tile in anchor_a + anchor_b:
                if not (0 <= tile[0] < self.GRID_SIZE and 0 <= tile[1] < self.GRID_SIZE):
                    raise ValueError(f"Tile {tile} is out of bounds")

            if set(anchor_a) & set(anchor_b):
                raise ValueError(f"Anchor A and B overlap for {raw['size']}")

            for tile in anchor_a + anchor_b:
                if tile in all_tiles:
                    raise ValueError(f"Tile {tile} overlaps with another target")
                all_tiles.add(tile)

            targets.append(Target(
                size=raw["size"],
                anchor_a=anchor_a,
                anchor_b=anchor_b,
                theta=raw["theta"],
                qubit_index=self.QUBIT_BY_SIZE[raw["size"]],
            ))

        self.targets[player_id] = targets
        self.ready.add(player_id)

        if len(self.ready) == 2:
            self.phase = GamePhase.FIRING
            self.current_turn = random.choice([self.player_a_id, self.player_b_id])

    # ------------------------------------------------------------------
    # Fire
    # ------------------------------------------------------------------

    def fire(self, player_id, coord: tuple[int, int]):
        enemy_id = self.player_b_id if player_id == self.player_a_id else self.player_a_id
        enemy_targets = self.targets[enemy_id]

        found_target = None
        found_anchor = None
        for target in enemy_targets:
            for cell in target.anchor_a:
                if coord == cell:
                    found_target = target
                    found_anchor = "A"
                    break
            for cell in target.anchor_b:
                if coord == cell:
                    found_target = target
                    found_anchor = "B"
                    break
            if found_target:
                break

        miss_turn = enemy_id
        hit_turn = player_id

        # Case A — miss
        if not found_target:
            return {
                "result": "miss", "cell": list(coord),
                "destroyed_cells": [], "pings": [],
                "next_turn": miss_turn, "game_over": False, "winner": None,
            }

        # Case B — first interaction, qubit not yet collapsed
        if not found_target.collapsed:
            pair = next(p for p in self.ENTANGLED_PAIRS if found_target.qubit_index in p)
            partner_qubit = pair[0] if found_target.qubit_index == pair[1] else pair[1]
            partner_target = next(t for t in enemy_targets if t.qubit_index == partner_qubit)

            if found_target.qubit_index == pair[0]:
                t1, t2 = found_target, partner_target
            else:
                t1, t2 = partner_target, found_target

            outcome = quokka.quokka.fire_shot(t1, t2)  # "00" or "11"
            t1.value = outcome[0]
            t2.value = outcome[1]
            t1.collapsed = True
            t2.collapsed = True

            # Pings = losing-anchor cells for both entangled targets
            pings = []
            for t in [t1, t2]:
                losing_anchor = t.anchor_b if t.value == "0" else t.anchor_a
                for cell in losing_anchor:
                    pings.append(list(cell))

            real_anchor = found_target.anchor_a if found_target.value == "0" else found_target.anchor_b
            if coord in real_anchor:
                found_target.hit_cells.add(coord)
                if found_target.hit_cells >= set(real_anchor):
                    game_over, winner = self._check_game_over(enemy_id)
                    return {
                        "result": "destroyed", "cell": list(coord),
                        "destroyed_cells": [list(c) for c in real_anchor],
                        "pings": pings, "next_turn": hit_turn,
                        "game_over": game_over, "winner": winner,
                    }
                return {
                    "result": "hit", "cell": list(coord),
                    "destroyed_cells": [], "pings": pings,
                    "next_turn": hit_turn, "game_over": False, "winner": None,
                }
            return {
                "result": "miss", "cell": list(coord),
                "destroyed_cells": [], "pings": pings,
                "next_turn": miss_turn, "game_over": False, "winner": None,
            }

        # Case C — subsequent hit on an already-collapsed target
        real_anchor = found_target.anchor_a if found_target.value == "0" else found_target.anchor_b
        if coord in real_anchor:
            found_target.hit_cells.add(coord)
            if found_target.hit_cells >= set(real_anchor):
                game_over, winner = self._check_game_over(enemy_id)
                return {
                    "result": "destroyed", "cell": list(coord),
                    "destroyed_cells": [list(c) for c in real_anchor],
                    "pings": [], "next_turn": hit_turn,
                    "game_over": game_over, "winner": winner,
                }
            return {
                "result": "hit", "cell": list(coord),
                "destroyed_cells": [], "pings": [],
                "next_turn": hit_turn, "game_over": False, "winner": None,
            }
        return {
            "result": "miss", "cell": list(coord),
            "destroyed_cells": [], "pings": [],
            "next_turn": miss_turn, "game_over": False, "winner": None,
        }

    # ------------------------------------------------------------------
    # Puzzle
    # ------------------------------------------------------------------

    def get_puzzle(self, player_id: str) -> dict:
        """Return (and cache) a random puzzle for this player."""
        if player_id not in self.active_puzzle:
            self.active_puzzle[player_id] = quokka.quokka.get_random_puzzle()
        return self.active_puzzle[player_id]

    def play_puzzle(self, player_id: str, gate_sequence: list) -> dict:
        """Evaluate the player's gate sequence.
        Does NOT advance the turn — puzzle attempts are free.
        If passed, the player's radar is unlocked.
        """
        puzzle = self.active_puzzle.get(player_id)
        if not puzzle:
            raise ValueError("No active puzzle — call get_puzzle first")

        result = quokka.quokka.evaluate_puzzle(
            gate_sequence=gate_sequence,
            initial_state=puzzle["initial"],
            target_outcome=puzzle["target"],
        )

        if result["passed"]:
            self.radar_unlocked[player_id] = True
            # Clear the puzzle so a fresh one is given next time
            del self.active_puzzle[player_id]

        return {
            "passed": result["passed"],
            "probability": result["probability"],
            "radar_unlocked": self.radar_unlocked.get(player_id, False),
        }

    # ------------------------------------------------------------------
    # Radar
    # ------------------------------------------------------------------

    def radar_scan(self, player_id: str, tiles: list) -> dict:
        """Run a radar scan over the given tiles.
        Consumes the radar charge and advances the turn.
        """
        if not self.radar_unlocked.get(player_id):
            raise ValueError("Radar not unlocked — solve the puzzle first")

        enemy_id = self.player_b_id if player_id == self.player_a_id else self.player_a_id
        enemy_targets = self.targets[enemy_id]

        tile_set = {tuple(t) for t in tiles}

        # Find qubits whose anchors overlap with the scan area
        scan_qubits: list[int] = []
        for target in enemy_targets:
            overlap = (set(target.anchor_a) | set(target.anchor_b)) & tile_set
            if overlap and target.qubit_index not in scan_qubits:
                scan_qubits.append(target.qubit_index)

        cell_probs: dict[str, float] = {}

        if scan_qubits:
            radar_result = quokka.quokka.run_radar(enemy_targets, scan_qubits)
            qubit_results = radar_result["qubit_results"]

            # Map qubit measurement results back to individual cells
            for target in enemy_targets:
                if target.qubit_index not in qubit_results:
                    continue
                prob_one = qubit_results[target.qubit_index]["prob_one"]

                for cell in target.anchor_a:
                    if tuple(cell) in tile_set:
                        key = f"{chr(65 + cell[0])}{cell[1] + 1}"
                        cell_probs[key] = round(1.0 - prob_one, 3)

                for cell in target.anchor_b:
                    if tuple(cell) in tile_set:
                        key = f"{chr(65 + cell[0])}{cell[1] + 1}"
                        cell_probs[key] = round(prob_one, 3)

        # Consume radar charge and advance turn
        self.radar_unlocked[player_id] = False
        self.current_turn = enemy_id

        return {"cell_probs": cell_probs, "next_turn": self.current_turn}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _check_game_over(self, loser_id: str):
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
