from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List


@dataclass
class Puzzle:
    """Puzzle structure, contains initial and goal states as well as a list
       of all available gates, restrictions about the minimal and maximal number of gates
       the player can use and finally, the gates applied before the measurement"""

    initial_state: str
    goal_state: str

    available_gates: List[str]
    solution: List[str] # List one possible solution

    # Minimal and maximal number of gates the player can use
    min_gates: int
    max_gates: int

    # List of gates we need to apply before measurement
    gates_before_measurement: List[str]
    # The expected measurement bitstring, such as "0", "1", "00", "11"
    expected_measurement: str

    # Special note shown to the player
    note: str

# Contains all the puzzle options for the easier puzzle version (2x2 Radar)
PUZZLES_EASY = [
    # Actually super easy
    Puzzle(initial_state = "|0>", goal_state="|1>", available_gates=["X", "H", "Z", "I"],
            solution = ["X"], min_gates = 1, max_gates = 10, gates_before_measurement=[],
            expected_measurement="1", note="Not all gates are useful."),
    Puzzle(initial_state = "|0>", goal_state="|+>", available_gates=["X", "H", "Z", "I"],
            solution = ["H"], min_gates = 1, max_gates = 10, gates_before_measurement=["H"],
            expected_measurement="0", note="Not all gates are useful."),
    Puzzle(initial_state = "|+>", goal_state="|->", available_gates=["X", "H", "Z", "I"],
            solution = ["Z"], min_gates = 1, max_gates = 10, gates_before_measurement=["H"],
            expected_measurement="1", note="Not all gates are useful."),
    Puzzle(initial_state = "|->", goal_state="|1>", available_gates=["X", "H", "Z", "I"],
            solution = ["H"], min_gates = 1, max_gates = 10, gates_before_measurement=[],
            expected_measurement="1", note="Not all gates are useful."),

    # Still easy, but bit more difficult
    Puzzle(initial_state = "|0>", goal_state="|->", available_gates=["X", "H", "Z", "I"],
            solution = ["X", "H"], min_gates = 1, max_gates = 10, gates_before_measurement=["H"],
            expected_measurement="1", note="Not all gates are useful."),
    Puzzle(initial_state = "|1>", goal_state="|+>", available_gates=["X", "H", "I"],
            solution = ["X", "H"], min_gates = 1, max_gates = 10, gates_before_measurement=["H"],
            expected_measurement="0", note="Not all gates are useful."),
    Puzzle(initial_state = "|+>", goal_state="|1>", available_gates=["X", "H", "Z", "I"],
            solution = ["H", "X"], min_gates = 1, max_gates = 10, gates_before_measurement=[],
            expected_measurement="1", note="Not all gates are useful."),

    # More difficult
    Puzzle(initial_state = "|0>", goal_state="|1>", available_gates=["H", "Z", "I"],
            solution = ["H", "Z", "H"], min_gates = 1, max_gates = 10, gates_before_measurement=[],
            expected_measurement="1", note="Not all gates are useful."),
    
]


# Contains all the puzzle options for the harder puzzle version (3x3 Radar)
PUZZLES_HARD = [
    # Hard 1-qubit
    Puzzle(initial_state="|0>", goal_state="|+>",
            available_gates=["X", "Z", "Ry(pi/4)", "S", "I"],
            solution=["Ry(pi/4)", "Ry(pi/4)"], min_gates=1, max_gates=10,
            gates_before_measurement=["H"], expected_measurement="0",
            note="Think carefully."),

    Puzzle(initial_state="|->", goal_state="|+>",
            available_gates=["X", "H", "Ry(pi/2)", "S", "T", "I"],
            solution=["Ry(pi/2)", "H"], min_gates=1, max_gates=10,
            gates_before_measurement=["H"], expected_measurement="0",
            note="There are multiple solutions."),

    Puzzle(initial_state="|+>", goal_state="|0>",
            available_gates=["X", "Z", "Ry(pi/2)", "S", "I"],
            solution=["Z", "Ry(pi/2)"], min_gates=1, max_gates=10,
            gates_before_measurement=[], expected_measurement="0",
            note="Not all gates are useful."),


    # 2-qubit puzzles
    Puzzle(initial_state="|00>", goal_state="(|00> + |11>) / sqrt(2)",
            available_gates=["H_0", "H_1", "X_0", "X_1", "Z_0", "CNOT_0_1", "CNOT_1_0"],
            solution=["H_0", "CNOT_0_1"], min_gates=1, max_gates=10,
            gates_before_measurement=["CNOT_0_1", "H_0"], expected_measurement="00",
            note="You'll need to entangle the qubits."),


    Puzzle(initial_state="|00>", goal_state="(|01> + |10>) / sqrt(2)",
            available_gates=["H_0", "H_1", "X_0", "X_1", "Z_0", "CNOT_0_1", "CNOT_1_0"],
            solution=["X_1", "H_0", "CNOT_0_1"], min_gates=1, max_gates=10,
            gates_before_measurement=["CNOT_0_1", "H_0"], expected_measurement="01",
            note="You'll need to entangle the qubits."),

    Puzzle(initial_state="|11>", goal_state="(|00> + |11>) / sqrt(2)",
            available_gates=["H_0", "H_1", "X_0", "X_1", "Z_0", "Z_1", "CNOT_0_1", "CNOT_1_0"],
            solution=["X_0", "X_1", "H_0", "CNOT_0_1"], min_gates=3, max_gates=10,
            gates_before_measurement=["CNOT_0_1", "H_0"], expected_measurement="00",
            note="Think about what state you need before entangling."),
]


# Number of qubits implied by each supported initial state.
N_QUBITS = {
    "|0>": 1, "|1>": 1, "|+>": 1, "|->": 1,
    "|00>": 2, "|01>": 2, "|10>": 2, "|11>": 2,
}

# QASM lines that prepare each initial state from the all-zeros register.
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

def _eval_angle(expr: str) -> float:
    expr = expr.strip()
    if expr == "pi":
        return math.pi
    if expr.startswith("pi/"):
        return math.pi / float(expr[3:])
    if expr.startswith("pi*"):
        return math.pi * float(expr[3:])
    return float(expr)


def _parse_cnot(gate: str) -> str | None:
    if not gate.startswith("CNOT_"):
        return None
    parts = gate.split("_")
    if len(parts) != 3:
        return None
    _, c, t = parts
    return f"cx q[{c}], q[{t}];"


def _parse_ry(gate: str) -> str | None:
    if not gate.startswith("Ry(") or ")" not in gate:
        return None
    close = gate.index(")")
    angle = _eval_angle(gate[3:close])
    rest = gate[close + 1:]
    q = rest[1:] if rest.startswith("_") else "0"
    return f"ry({angle}) q[{q}];"


def gate_to_qasm(gate: str) -> str:
    """Translate a single gate string into one line of QASM."""
    if qasm := _parse_cnot(gate):
        return qasm
    if qasm := _parse_ry(gate):
        return qasm
    if "_" in gate:
        name, q = gate.rsplit("_", 1)
        if name not in GATE_MAP:
            raise ValueError(f"Unknown gate {gate}")
        return f"{GATE_MAP[name]} q[{q}];"
    if gate in GATE_MAP:
        return f"{GATE_MAP[gate]} q[0];"
    raise ValueError(f"Unknown gate {gate}")


def build_circuit(puzzle: Puzzle, player_gates: List[str]) -> str:
    """Builds the complete circuit based on players gates."""

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


def roll_puzzle(difficulty: str) -> Puzzle:
    pool = PUZZLES_EASY if difficulty == "easy" else PUZZLES_HARD
    return random.choice(pool)


def puzzle_payload(puzzle: Puzzle) -> dict:
    return {
        "n_qubits": N_QUBITS[puzzle.initial_state],
        "initial_state": puzzle.initial_state,
        "goal_state": puzzle.goal_state,
        "available_gates": puzzle.available_gates,
        "min_gates": puzzle.min_gates,
        "max_gates": puzzle.max_gates,
        "note": puzzle.note,
    }
