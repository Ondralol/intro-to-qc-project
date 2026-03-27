"""
Quantum Battleship — 2-Player, 7×7 grid
========================================
Each player has:
  - 1 classical ship  (3 cells, horizontal or vertical)
  - 1 quantum ship    (superposition of 2 possible placements)

Quantum ship firing rules:
  Cell in neither placement  → miss
  Cell in both placements    → hit (no collapse yet — ship remains in superposition)
  Cell in exactly one        → trigger quantum measurement → wave-function collapse
  After collapse             → quantum ship behaves classically

Collapse circuit:
  1 qubit:  |0⟩ = Placement A,  |1⟩ = Placement B
  Apply ry(theta): equal superposition (theta = π/2) or biased
  Measure → 0 collapses to A, 1 collapses to B
"""

import math
import random
from typing import List, Tuple, Optional, Set

import requests

QUOKKA_URL = "http://quokka3.quokkacomputing.com/qsim/qasm"

GRID_SIZE = 7
SHIP_LENGTH = 3


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_ship(cells: List[Tuple[int, int]]) -> Tuple[bool, str]:
    """Return (ok, error_message). Ship must be SHIP_LENGTH consecutive cells."""
    if len(cells) != SHIP_LENGTH:
        return False, f"Ship must be exactly {SHIP_LENGTH} cells."
    rows = [r for r, c in cells]
    cols = [c for r, c in cells]
    for r, c in cells:
        if not (0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE):
            return False, f"Cell ({r},{c}) is out of bounds (grid is {GRID_SIZE}×{GRID_SIZE})."
    if len(set(rows)) == 1:   # horizontal
        sc = sorted(cols)
        if sc == list(range(sc[0], sc[0] + SHIP_LENGTH)):
            return True, ""
        return False, "Horizontal cells must be consecutive (no gaps)."
    if len(set(cols)) == 1:   # vertical
        sr = sorted(rows)
        if sr == list(range(sr[0], sr[0] + SHIP_LENGTH)):
            return True, ""
        return False, "Vertical cells must be consecutive (no gaps)."
    return False, "Ship must be horizontal or vertical."


# ---------------------------------------------------------------------------
# QASM generation and simulation
# ---------------------------------------------------------------------------

def generate_collapse_qasm(theta: float) -> str:
    """
    Build an OpenQASM 2.0 circuit that collapses the quantum ship.
    ry(theta)|0⟩ creates a biased superposition:
      theta = π/2 → P(A) = P(B) = 50%
      theta < π/2 → biased toward Placement A
      theta > π/2 → biased toward Placement B
    """
    p_a = round(math.cos(theta / 2) ** 2, 4)
    p_b = round(math.sin(theta / 2) ** 2, 4)
    return (
        "// ================================================\n"
        "// Quantum Battleship — Ship Collapse Circuit\n"
        "// |0⟩ = Placement A,  |1⟩ = Placement B\n"
        "// ================================================\n"
        "OPENQASM 2.0;\n"
        'include "qelib1.inc";\n'
        "\n"
        "qreg q[1];\n"
        "creg c[1];\n"
        "\n"
        "// Initialise to |0⟩ (implicit)\n"
        f"// ry({theta:.4f}) biases the superposition:\n"
        f"//   P(Placement A) = {p_a:.1%}\n"
        f"//   P(Placement B) = {p_b:.1%}\n"
        f"ry({theta:.4f}) q[0];\n"
        "\n"
        "// Measure: 0 → Placement A,  1 → Placement B\n"
        "measure q[0] -> c[0];\n"
    )


def simulate_collapse(theta: float) -> int:
    """Execute the collapse circuit on Quokka. Returns 0 (Placement A) or 1 (Placement B).
    Falls back to local weighted sampling if Quokka is unreachable."""
    qasm = generate_collapse_qasm(theta)
    try:
        response = requests.post(QUOKKA_URL, json={"script": qasm, "count": 1}, timeout=10)
        outcome = response.json()["result"]["c"][0][0]
        return int(outcome)
    except Exception:
        p_b = math.sin(theta / 2) ** 2
        return random.choices([0, 1], weights=[1 - p_b, p_b])[0]


# ---------------------------------------------------------------------------
# Classical ship
# ---------------------------------------------------------------------------

class ClassicalShip:
    def __init__(self, cells: List[Tuple[int, int]]):
        self.cells: Set[Tuple[int, int]] = set(map(tuple, cells))
        self.hits: Set[Tuple[int, int]] = set()

    def fire(self, r: int, c: int) -> bool:
        coord = (r, c)
        if coord in self.cells and coord not in self.hits:
            self.hits.add(coord)
            return True
        return False

    def is_sunk(self) -> bool:
        return self.cells <= self.hits

    def to_dict(self) -> dict:
        return {
            "cells": [list(c) for c in self.cells],
            "hits":  [list(h) for h in self.hits],
            "sunk":  self.is_sunk(),
        }


# ---------------------------------------------------------------------------
# Quantum ship
# ---------------------------------------------------------------------------

class QuantumShip:
    def __init__(
        self,
        placement_a: List[Tuple[int, int]],
        placement_b: List[Tuple[int, int]],
        theta: float = math.pi / 2,
    ):
        self.placement_a: Set[Tuple[int, int]] = set(map(tuple, placement_a))
        self.placement_b: Set[Tuple[int, int]] = set(map(tuple, placement_b))
        self.theta = theta

        # Post-collapse state
        self.collapsed = False
        self.collapsed_to: Optional[str] = None         # "A" or "B"
        self.active_placement: Optional[Set[Tuple[int, int]]] = None
        self.hits: Set[Tuple[int, int]] = set()

        # Cells hit while the ship was still in superposition (in both placements)
        self.overlap_hits: Set[Tuple[int, int]] = set()

    def fire(self, r: int, c: int) -> dict:
        """Fire at (r, c). Returns a dict describing the quantum outcome."""
        coord = (r, c)

        # ── Already collapsed: behave classically ──
        if self.collapsed:
            hit = coord in self.active_placement and coord not in self.hits
            if hit:
                self.hits.add(coord)
            return {
                "type": "hit" if hit else "miss",
                "collapsed": True,
                "qasm": None,
            }

        in_a = coord in self.placement_a
        in_b = coord in self.placement_b

        # ── Neither placement ──
        if not in_a and not in_b:
            return {"type": "miss", "collapsed": False, "qasm": None}

        # ── Both placements: definite hit, no collapse yet ──
        if in_a and in_b:
            self.overlap_hits.add(coord)
            return {"type": "hit_both", "collapsed": False, "qasm": None}

        # ── Exactly one placement: trigger collapse ──
        qasm = generate_collapse_qasm(self.theta)
        p_a  = math.cos(self.theta / 2) ** 2
        p_b  = math.sin(self.theta / 2) ** 2
        outcome = simulate_collapse(self.theta)

        self.collapsed = True
        if outcome == 0:
            self.active_placement = set(self.placement_a)
            self.collapsed_to = "A"
        else:
            self.active_placement = set(self.placement_b)
            self.collapsed_to = "B"

        # Carry over overlap hits that land on the active placement
        for h in self.overlap_hits:
            if h in self.active_placement:
                self.hits.add(h)

        # Register this shot against the now-known placement
        hit_after_collapse = coord in self.active_placement
        if hit_after_collapse:
            self.hits.add(coord)

        return {
            "type":               "collapse",
            "collapsed":          True,
            "collapsed_to":       self.collapsed_to,
            "outcome":            outcome,
            "p_a":                round(p_a, 4),
            "p_b":                round(p_b, 4),
            "hit_after_collapse": hit_after_collapse,
            "qasm":               qasm,
        }

    def is_sunk(self) -> bool:
        if not self.collapsed or self.active_placement is None:
            return False
        return self.active_placement <= self.hits

    def to_dict(self) -> dict:
        return {
            "placement_a":      [list(c) for c in self.placement_a],
            "placement_b":      [list(c) for c in self.placement_b],
            "collapsed":        self.collapsed,
            "collapsed_to":     self.collapsed_to,
            "active_placement": [list(c) for c in self.active_placement] if self.active_placement else None,
            "hits":             [list(h) for h in self.hits],
            "overlap_hits":     [list(h) for h in self.overlap_hits],
            "sunk":             self.is_sunk(),
        }


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

class Player:
    def __init__(
        self,
        name: str,
        classical_cells: List[Tuple[int, int]],
        q_placement_a: List[Tuple[int, int]],
        q_placement_b: List[Tuple[int, int]],
        q_theta: float = math.pi / 2,
    ):
        self.name = name
        self.classical = ClassicalShip(classical_cells)
        self.quantum = QuantumShip(q_placement_a, q_placement_b, q_theta)

    def receive_fire(self, r: int, c: int) -> dict:
        classical_hit = self.classical.fire(r, c)
        quantum_result = self.quantum.fire(r, c)

        # Determine the overall display outcome
        if classical_hit:
            display = "hit"
        elif quantum_result["type"] == "hit_both":
            display = "hit"
        elif quantum_result["type"] == "collapse" and quantum_result["hit_after_collapse"]:
            display = "hit"
        elif quantum_result["type"] == "hit":   # post-collapse classical hit
            display = "hit"
        else:
            display = "miss"

        return {
            "display_result": display,
            "classical":      {"hit": classical_hit, "sunk": self.classical.is_sunk()},
            "quantum":        quantum_result,
            "quantum_sunk":   self.quantum.is_sunk(),
            "all_sunk":       self.all_sunk(),
        }

    def all_sunk(self) -> bool:
        return self.classical.is_sunk() and self.quantum.is_sunk()

    def to_dict(self) -> dict:
        return {
            "name":      self.name,
            "classical": self.classical.to_dict(),
            "quantum":   self.quantum.to_dict(),
            "all_sunk":  self.all_sunk(),
        }


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------

class Game:
    def __init__(self):
        self.players: List[Player] = []
        self.current_turn: int = 0
        self.winner: Optional[int] = None
        self.phase: str = "setup"
        self.shot_history: List[dict] = []

    def setup(
        self,
        p1_classical: List, p1_qa: List, p1_qb: List,
        p2_classical: List, p2_qa: List, p2_qb: List,
        p1_theta: float = math.pi / 2,
        p2_theta: float = math.pi / 2,
    ) -> dict:
        placements = [
            ("P1 Classical", p1_classical),
            ("P1 Quantum A", p1_qa),
            ("P1 Quantum B", p1_qb),
            ("P2 Classical", p2_classical),
            ("P2 Quantum A", p2_qa),
            ("P2 Quantum B", p2_qb),
        ]
        for name, cells in placements:
            ok, msg = validate_ship([tuple(c) for c in cells])
            if not ok:
                return {"ok": False, "error": f"{name}: {msg}"}

        self.players = [
            Player("Player 1",
                   [tuple(c) for c in p1_classical],
                   [tuple(c) for c in p1_qa],
                   [tuple(c) for c in p1_qb],
                   p1_theta),
            Player("Player 2",
                   [tuple(c) for c in p2_classical],
                   [tuple(c) for c in p2_qa],
                   [tuple(c) for c in p2_qb],
                   p2_theta),
        ]
        self.phase = "playing"
        self.current_turn = 0
        self.winner = None
        self.shot_history = []
        return {"ok": True}

    def fire(self, r: int, c: int) -> dict:
        if self.phase != "playing":
            raise ValueError("Game is not in playing phase.")
        if not (0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE):
            raise ValueError(f"({r},{c}) is outside the {GRID_SIZE}×{GRID_SIZE} grid.")

        attacker = self.current_turn
        defender = 1 - attacker
        result = self.players[defender].receive_fire(r, c)

        result["attacker"] = attacker
        result["coord"] = [r, c]
        result["shot_number"] = len(self.shot_history) + 1

        self.shot_history.append({
            "attacker": attacker,
            "coord":    [r, c],
            "result":   result["display_result"],
        })

        if self.players[defender].all_sunk():
            self.winner = attacker
            self.phase = "done"
            result["game_over"] = True
        else:
            result["game_over"] = False
            self.current_turn = 1 - self.current_turn

        return result

    def state(self) -> dict:
        return {
            "phase":        self.phase,
            "current_turn": self.current_turn,
            "winner":       self.winner,
            "grid_size":    GRID_SIZE,
            "players":      [p.to_dict() for p in self.players] if self.players else [],
            "shot_history": self.shot_history,
        }

    def reset(self):
        self.__init__()
