"""Quantum puzzle pool, QASM builder and evaluator.

Each puzzle is a dict consumed by the frontend (see TIER_POOL). Solutions are
judged by *measured outcome*, not by gate-sequence equality, so multiple
solutions are valid.
"""

import math
import random
import uuid

from quokka.quokka import send_to_quokka


# Initial-state preparation prepended before player gates.
INIT_PREP = {
    "|0>":  "",
    "|1>":  "x q[0];\n",
    "|+>":  "h q[0];\n",
    "|->":  "x q[0];\nh q[0];\n",
    "|00>": "",
    "|01>": "x q[1];\n",
    "|+0>": "h q[0];\n",
}


def _gate_qasm(gate: dict) -> str:
    name = gate["name"]
    if name in ("H", "X", "Z", "S"):
        return f"{name.lower()} q[{gate['qubit']}];\n"
    if name == "Ry":
        # theta in degrees from a small fixed menu
        theta_rad = math.radians(float(gate["theta"]))
        return f"ry({theta_rad}) q[{gate['qubit']}];\n"
    if name == "CX":
        return f"cx q[{gate['control']}], q[{gate['target']}];\n"
    if name == "CZ":
        return f"cz q[{gate['control']}], q[{gate['target']}];\n"
    if name == "SWAP":
        return f"swap q[{gate['a']}], q[{gate['b']}];\n"
    raise ValueError(f"Unknown gate {name}")


def build_circuit(initial_state: str, n_qubits: int, gates: list[dict]) -> str:
    qasm = (
        'OPENQASM 2.0;\n'
        'include "qelib1.inc";\n'
        f'qreg q[{n_qubits}];\n'
        f'creg c[{n_qubits}];\n'
    )
    qasm += INIT_PREP.get(initial_state, "")
    for g in gates:
        qasm += _gate_qasm(g)
    for i in range(n_qubits):
        qasm += f"measure q[{i}] -> c[{i}];\n"
    return qasm


def evaluate(puzzle: dict, gates: list[dict], shots: int = 1000) -> dict:
    """Run the player's circuit on Quokka and score it via total-variation distance."""
    if len(gates) > puzzle["max_gates"]:
        return {"passed": False, "score": 0.0, "counts": {}, "qasm": "", "error": "Gate budget exceeded"}

    qasm = build_circuit(puzzle["initial_state"], puzzle["n_qubits"], gates)
    counts = send_to_quokka(qasm, shots)
    empirical = {k: v / shots for k, v in counts.items()}

    target = puzzle["target_distribution"]
    keys = set(target) | set(empirical)
    tvd = 0.5 * sum(abs(empirical.get(k, 0) - target.get(k, 0)) for k in keys)
    score = 1 - tvd
    return {
        "passed": score >= puzzle["threshold"],
        "score": score,
        "counts": counts,
        "qasm": qasm,
    }


# --- puzzle pools ---------------------------------------------------------

TIER_POOL: dict[int, list[dict]] = {
    1: [
        {
            "n_qubits": 1,
            "initial_state": "|0>",
            "target_description": "Measure |1> with high probability",
            "target_distribution": {"1": 1.0},
            "gate_palette": ["H", "X", "Z"],
            "max_gates": 3,
        },
        {
            "n_qubits": 1,
            "initial_state": "|1>",
            "target_description": "Measure |0> with high probability",
            "target_distribution": {"0": 1.0},
            "gate_palette": ["H", "X", "Z"],
            "max_gates": 3,
        },
    ],
    2: [
        {
            "n_qubits": 1,
            "initial_state": "|0>",
            "target_description": "Create a 50/50 superposition",
            "target_distribution": {"0": 0.5, "1": 0.5},
            "gate_palette": ["H", "X", "Z", "S"],
            "max_gates": 3,
        },
        {
            "n_qubits": 1,
            "initial_state": "|+>",
            "target_description": "Collapse |+> back to |0>",
            "target_distribution": {"0": 1.0},
            "gate_palette": ["H", "X", "Z", "S"],
            "max_gates": 3,
        },
        {
            "n_qubits": 1,
            "initial_state": "|0>",
            "target_description": "Tilt to ~75% probability of |1>",
            "target_distribution": {"0": 0.25, "1": 0.75},
            "gate_palette": ["H", "X", "Z", "S", "Ry"],
            "ry_thetas": [30, 45, 60, 90, 120],
            "max_gates": 3,
        },
    ],
    3: [
        {
            "n_qubits": 2,
            "initial_state": "|00>",
            "target_description": "Build the Bell state |Φ+> — outcomes 00 and 11, 50/50",
            "target_distribution": {"00": 0.5, "11": 0.5},
            "gate_palette": ["H", "X", "Z", "CX"],
            "max_gates": 4,
        },
        {
            "n_qubits": 2,
            "initial_state": "|00>",
            "target_description": "Anti-correlated pair — outcomes 01 and 10, 50/50",
            "target_distribution": {"01": 0.5, "10": 0.5},
            "gate_palette": ["H", "X", "Z", "CX"],
            "max_gates": 4,
        },
    ],
}

# Tolerance baked into threshold. score = 1 - TVD; threshold 0.85 ≈ ±15% slack.
DEFAULT_THRESHOLD = 0.85
DEFAULT_SHOTS = 1000


def roll_puzzle(tier: int) -> dict:
    """Pick a random puzzle from the given tier and stamp it with an id + threshold."""
    tier = max(1, min(3, tier))
    template = random.choice(TIER_POOL[tier])
    puzzle = dict(template)
    puzzle["puzzle_id"] = uuid.uuid4().hex[:8]
    puzzle["tier"] = tier
    puzzle["threshold"] = DEFAULT_THRESHOLD
    puzzle["shots"] = DEFAULT_SHOTS
    return puzzle


def tier_for_use(use_index: int) -> int:
    """Tier 1 on first use, 2 on second, 3 from third onward."""
    if use_index <= 0:
        return 1
    if use_index == 1:
        return 2
    return 3
