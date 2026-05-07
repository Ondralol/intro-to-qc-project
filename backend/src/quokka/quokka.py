import json
import math
import random
import requests
from collections import Counter

from game.game_helper import Target


# ---------------------------------------------------------------------------
# Core Quokka sender
# ---------------------------------------------------------------------------

def send_to_quokka(program, count=1, my_quokka='quokka5'):
    request_http = 'https://{}.quokkacomputing.com/qsim/qasm'.format(my_quokka)
    data = {'script': program, 'count': count}
    result = requests.post(request_http, json=data, verify=True)
    json_obj = json.loads(result.content)
    raw_data = json_obj['result']['c']
    counts = Counter(["".join(map(str, shot)) for shot in raw_data])
    print(dict(counts))
    return dict(counts)


# ---------------------------------------------------------------------------
# Fire shot — entangled pair measurement
# ---------------------------------------------------------------------------

def fire_shot(target1: Target, target2: Target) -> str:
    """One entangled measurement. Returns 2-bit string (bit 0 = target1, bit 1 = target2).
    With CNOT entanglement only '00' and '11' are possible outcomes."""
    qasm = (
        'OPENQASM 2.0;\n'
        'include "qelib1.inc";\n'
        'qreg q[2];\n'
        'creg c[2];\n'
        f'ry({target1.theta}) q[0];\n'
        'cx q[0], q[1];\n'
        'measure q[0] -> c[0];\n'
        'measure q[1] -> c[1];\n'
    )
    counts = send_to_quokka(qasm, count=1)
    return max(counts, key=counts.get)


# ---------------------------------------------------------------------------
# Puzzle
# ---------------------------------------------------------------------------

GATE_MAP = {
    "H": "h q[0];\n",
    "X": "x q[0];\n",
    "Z": "z q[0];\n",
}

PUZZLES = [
    {
        "initial": "|0>",
        "target": "1",
        "description": "Transform |0⟩ so that measuring |1⟩ has >80% probability",
        "hint": "Which gate flips the qubit?",
    },
    {
        "initial": "|1>",
        "target": "0",
        "description": "Transform |1⟩ so that measuring |0⟩ has >80% probability",
        "hint": "Which gate flips the qubit?",
    },
    {
        "initial": "|+>",
        "target": "0",
        "description": "Transform |+⟩ so that measuring |0⟩ has >80% probability",
        "hint": "The Hadamard gate converts between computational and Hadamard bases",
    },
]


def get_random_puzzle() -> dict:
    return random.choice(PUZZLES)


def build_puzzle_circuit(initial_state: str, gate_sequence: list) -> str:
    qasm = (
        'OPENQASM 2.0;\n'
        'include "qelib1.inc";\n'
        'qreg q[1];\n'
        'creg c[1];\n'
    )
    if initial_state == "|1>":
        qasm += "x q[0];\n"
    elif initial_state == "|+>":
        qasm += "h q[0];\n"
    elif initial_state == "|->":
        qasm += "x q[0];\n"
        qasm += "h q[0];\n"
    for gate in gate_sequence:
        if gate not in GATE_MAP:
            raise ValueError(f"Unknown gate: {gate}")
        qasm += GATE_MAP[gate]
    qasm += "measure q[0] -> c[0];\n"
    return qasm


def evaluate_puzzle(
    gate_sequence: list,
    initial_state: str = "|0>",
    target_outcome: str = "1",
    threshold: float = 0.8,
    shots: int = 1000,
) -> dict:
    """Evaluate a player's gate sequence against the target outcome."""
    if not gate_sequence:
        return {"passed": False, "probability": 0.0, "counts": {}}
    qasm = build_puzzle_circuit(initial_state, gate_sequence)
    results = send_to_quokka(qasm, shots)
    success_count = results.get(target_outcome, 0)
    probability = success_count / shots
    passed = probability >= threshold
    return {"passed": passed, "probability": round(probability, 3), "counts": results}


# ---------------------------------------------------------------------------
# Radar — non-destructive state reconstruction + scan
# ---------------------------------------------------------------------------

def build_radar_circuit(targets: list, scan_qubits: list) -> str:
    """Reconstruct the full 4-qubit game state and measure only the requested qubits."""
    n = 4
    qasm = (
        'OPENQASM 2.0;\n'
        'include "qelib1.inc";\n'
        f'qreg q[{n}];\n'
        f'creg c[{n}];\n'
    )
    qubit_map = {t.qubit_index: t for t in targets}

    # Initialise each qubit based on its current classical state
    for q_idx in range(n):
        t = qubit_map.get(q_idx)
        if t is None:
            continue
        if t.collapsed:
            # Hard-code the known value
            if t.value == "1":
                qasm += f"x q[{q_idx}];\n"
            # value "0" is already |0⟩ by default — no gate needed
        else:
            # Only the control qubit of each entangled pair gets an Ry rotation
            # Pairs are (0,1) and (2,3); control qubits are 0 and 2
            if q_idx in (0, 2):
                # theta is already the Ry angle in radians
                qasm += f"ry({t.theta}) q[{q_idx}];\n"

    # Re-apply CNOT entanglement for uncollapsed pairs
    for control, target_q in [(0, 1), (2, 3)]:
        ct = qubit_map.get(control)
        tt = qubit_map.get(target_q)
        if ct and tt and not ct.collapsed and not tt.collapsed:
            qasm += f"cx q[{control}], q[{target_q}];\n"

    # Measure only the scan qubits
    for i in scan_qubits:
        if i < n:
            qasm += f"measure q[{i}] -> c[{i}];\n"

    return qasm


def run_radar(targets: list, scan_qubits: list, shots: int = 1000) -> dict:
    """Run the radar scan and return per-qubit probability of measuring |1⟩."""
    qasm = build_radar_circuit(targets, scan_qubits)
    counts = send_to_quokka(qasm, shots)

    qubit_results = {}
    for qubit_idx in scan_qubits:
        ones = sum(
            count for outcome, count in counts.items()
            if qubit_idx < len(outcome) and outcome[qubit_idx] == "1"
        )
        prob_one = ones / shots

        if 0.35 <= prob_one <= 0.65:
            status = "superposition"
        elif prob_one > 0.65:
            status = "anchor_b"
        else:
            status = "anchor_a"

        qubit_results[qubit_idx] = {"status": status, "prob_one": round(prob_one, 3)}

    return {"qubit_results": qubit_results}
