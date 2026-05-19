from __future__ import annotations

import math
import random
import re
import uuid
from dataclasses import dataclass, field, replace, asdict
from typing import List

from quokka.quokka import send_to_quokka


@dataclass
class Puzzle:
    initial_state: str
    goal_state: str
    available_gates: List[str]
    solution: List[str]
    min_gates: int
    max_gates: int
    gates_before_measurement: List[str]
    expected_measurement: str
    note: str = ""
    # Stamped when a puzzle is rolled for a player.
    puzzle_id: str = ""
    shots: int = 1000


# Number of qubits implied by each supported initial state.
N_QUBITS = {
    "|0>": 1, "|1>": 1, "|+>": 1, "|->": 1,
    "|00>": 2, "|01>": 2, "|10>": 2, "|11>": 2,
}

# QASM lines to prepare each initial state from the all-zeros register.
INIT_PREP = {
    "|0>":  [],
    "|1>":  ["x q[0];"],
    "|+>":  ["h q[0];"],
    "|->":  ["x q[0];", "h q[0];"],
    "|00>": [],
    "|01>": ["x q[1];"],
    "|10>": ["x q[0];"],
    "|11>": ["x q[0];", "x q[1];"],
}

# Fixed single-qubit gates. Indexed (e.g. "H_1") and parametric ("Ry(pi/4)")
# forms are handled by the regexes in `gate_to_qasm`.
GATE_MAP = {
    "H": "h",
    "X": "x",
    "Z": "z",
    "S": "s",
    "T": "t",
    "I": "id",
}

_CNOT_RE = re.compile(r"^CNOT_(\d+)_(\d+)$")
_RY_RE = re.compile(r"^Ry\(([^)]+)\)(?:_(\d+))?$")
_INDEXED_RE = re.compile(r"^([A-Za-z]+)_(\d+)$")


def _eval_angle(expr: str) -> float:
    """Parse 'pi', 'pi/4', 'pi*2', or a plain float into radians."""
    expr = expr.strip().replace(" ", "")
    if expr == "pi":
        return math.pi
    if expr.startswith("pi/"):
        return math.pi / float(expr[3:])
    if expr.startswith("pi*"):
        return math.pi * float(expr[3:])
    return float(expr)


def gate_to_qasm(gate: str) -> str:
    """Translate a single gate string into one line of QASM."""
    cnot = _CNOT_RE.match(gate)
    if cnot:
        return f"cx q[{cnot.group(1)}], q[{cnot.group(2)}];"

    ry = _RY_RE.match(gate)
    if ry:
        theta = _eval_angle(ry.group(1))
        q = ry.group(2) or "0"
        return f"ry({theta}) q[{q}];"

    indexed = _INDEXED_RE.match(gate)
    if indexed:
        name, q = indexed.group(1), indexed.group(2)
        if name not in GATE_MAP:
            raise ValueError(f"Unknown gate {gate}")
        return f"{GATE_MAP[name]} q[{q}];"

    if gate in GATE_MAP:
        return f"{GATE_MAP[gate]} q[0];"

    raise ValueError(f"Unknown gate {gate}")


def build_circuit(puzzle: Puzzle, player_gates: List[str]) -> str:
    """Init prep → player gates → fixed pre-measurement gates → measure all."""
    n = N_QUBITS[puzzle.initial_state]
    lines = [
        "OPENQASM 2.0;",
        'include "qelib1.inc";',
        f"qreg q[{n}];",
        f"creg c[{n}];",
    ]
    lines.extend(INIT_PREP[puzzle.initial_state])
    for g in player_gates:
        lines.append(gate_to_qasm(g))
    for g in puzzle.gates_before_measurement:
        lines.append(gate_to_qasm(g))
    for i in range(n):
        lines.append(f"measure q[{i}] -> c[{i}];")
    return "\n".join(lines) + "\n"


DEFAULT_THRESHOLD = 0.8


def evaluate(puzzle: Puzzle, gates: List[str], shots: int = 1000) -> dict:
    """Run the player's circuit on Quokka and score by P(expected outcome)."""
    if len(gates) > puzzle.max_gates:
        return {"passed": False, "score": 0.0, "counts": {}, "qasm": "", "error": "Gate budget exceeded"}
    if len(gates) < puzzle.min_gates:
        return {"passed": False, "score": 0.0, "counts": {}, "qasm": "", "error": f"Use at least {puzzle.min_gates} gate(s)"}
    for g in gates:
        if g not in puzzle.available_gates:
            return {"passed": False, "score": 0.0, "counts": {}, "qasm": "", "error": f"Gate {g} not in palette"}

    qasm = build_circuit(puzzle, gates)
    counts = send_to_quokka(qasm, shots)

    expected = str(puzzle.expected_measurement)
    score = counts.get(expected, 0) / shots
    return {
        "passed": score >= DEFAULT_THRESHOLD,
        "score": score,
        "counts": counts,
        "qasm": qasm,
    }


# --- puzzle pools ---------------------------------------------------------
# Mirrors backend/src/game/puzzle.py on main, with the inconsistent field
# names (`gates_before_measuremet`, `expectect_measurement`) corrected.

PUZZLES_EASY: List[Puzzle] = [
    Puzzle("|0>", "|1>",  ["X", "H", "Z", "I"], ["X"],            1, 10, [],     "1", "Not all gates are useful."),
    Puzzle("|0>", "|+>",  ["X", "H", "Z", "I"], ["H"],            1, 10, ["H"],  "0", "Not all gates are useful."),
    Puzzle("|+>", "|->",  ["X", "H", "Z", "I"], ["Z"],            1, 10, ["H"],  "1", "Not all gates are useful."),
    Puzzle("|->", "|1>",  ["X", "H", "Z", "I"], ["H"],            1, 10, [],     "1", "Not all gates are useful."),
    Puzzle("|0>", "|->",  ["X", "H", "Z", "I"], ["X", "H"],       1, 10, ["H"],  "1", "Not all gates are useful."),
    Puzzle("|1>", "|+>",  ["X", "H", "I"],      ["X", "H"],       1, 10, ["H"],  "0", "Not all gates are useful."),
    Puzzle("|+>", "|1>",  ["X", "H", "Z", "I"], ["H", "X"],       1, 10, [],     "1", "Not all gates are useful."),
    Puzzle("|0>", "|1>",  ["H", "Z", "I"],      ["H", "Z", "H"],  1, 10, [],     "1", "Not all gates are useful."),
]

PUZZLES_HARD: List[Puzzle] = [
    Puzzle("|0>", "|+>",
           ["X", "Z", "Ry(pi/4)", "S", "I"],
           ["Ry(pi/4)", "Ry(pi/4)"], 1, 10, ["H"], "0",
           "Think carefully."),

    Puzzle("|->", "|+>",
           ["X", "H", "Ry(pi/2)", "S", "T", "I"],
           ["Ry(pi/2)", "H"], 1, 10, ["H"], "0",
           "There are multiple solutions."),

    Puzzle("|+>", "|0>",
           ["X", "Z", "Ry(pi/2)", "S", "I"],
           ["Z", "Ry(pi/2)"], 1, 10, [], "0",
           "Not all gates are useful."),

    Puzzle("|00>", "(|00> + |11>) / sqrt(2)",
           ["H_0", "H_1", "X_0", "X_1", "Z_0", "CNOT_0_1", "CNOT_1_0"],
           ["H_0", "CNOT_0_1"], 1, 10, ["CNOT_0_1", "H_0"], "00",
           "You'll need to entangle the qubits."),

    Puzzle("|00>", "(|01> + |10>) / sqrt(2)",
           ["H_0", "H_1", "X_0", "X_1", "Z_0", "CNOT_0_1", "CNOT_1_0"],
           ["X_1", "H_0", "CNOT_0_1"], 1, 10, ["CNOT_0_1", "H_0"], "01",
           "You'll need to entangle the qubits."),

    Puzzle("|11>", "(|00> + |11>) / sqrt(2)",
           ["H_0", "H_1", "X_0", "X_1", "Z_0", "Z_1", "CNOT_0_1", "CNOT_1_0"],
           ["X_0", "X_1", "H_0", "CNOT_0_1"], 3, 10, ["CNOT_0_1", "H_0"], "00",
           "Think about what state you need before entangling."),
]


DEFAULT_SHOTS = 1000


def roll_puzzle() -> Puzzle:
    """Pick a random puzzle from the combined pool and stamp it with a fresh id."""
    template = random.choice(PUZZLES_EASY + PUZZLES_HARD)
    return replace(template, puzzle_id=uuid.uuid4().hex[:8], shots=DEFAULT_SHOTS)


def puzzle_payload(puzzle: Puzzle) -> dict:
    """Public fields emitted to the client for the puzzle UI."""
    return {
        "puzzle_id": puzzle.puzzle_id,
        "n_qubits": N_QUBITS[puzzle.initial_state],
        "initial_state": puzzle.initial_state,
        "goal_state": puzzle.goal_state,
        "available_gates": puzzle.available_gates,
        "min_gates": puzzle.min_gates,
        "max_gates": puzzle.max_gates,
        "note": puzzle.note,
    }
