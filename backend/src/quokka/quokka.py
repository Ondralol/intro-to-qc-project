import json
import requests
from collections import Counter

from game.game_helper import Target
from game.puzzle import Puzzle, build_circuit
from typing import List


def send_to_quokka(program, count=1, my_quokka='quokka1'):
    request_http = 'https://{}.quokkacomputing.com/qsim/qasm'.format(my_quokka)
    data = {'script': program, 'count': count}
    result = requests.post(request_http, json=data, verify=True)
    try:
        json_obj = json.loads(result.content)
    except json.JSONDecodeError:
        raise RuntimeError("Quokka quantum computer is currently unavailable (HTTP {})".format(result.status_code))
    raw_data = json_obj['result']['c']
    counts = Counter(["".join(map(str, shot)) for shot in raw_data])
    print(dict(counts))
    return dict(counts)


def fire_shot(target1: Target, target2: Target) -> str:
    """Run one entangled measurement. Returns a 2bit string -  bit 0 = target1, bit 1 = target2.
    With CNOT entanglement only "00" and "11" are possible outcomes."""
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
    # Either returns "00" or "11" in our case
    return max(counts, key=counts.get)


def radar_scan(
    targets: List[Target],
    entangled_pairs: List[tuple],
    scan_qubits: List[int],
    shots: int = 100,
) -> dict[int, float]:
    """Reconstruct quantum state and return P(qubit=1) for each scanned qubit.

    For uncollapsed pairs: Ry(θ) + CX to recreate superposition.
    For collapsed pairs: X gate to hardcode the known value.
    Uses creg c[4] so outcome[i] maps directly to qubit i.
    """
    qubit_to_target = {t.qubit_index: t for t in targets}

    lines = [
        "OPENQASM 2.0;",
        'include "qelib1.inc";',
        "qreg q[4];",
        "creg c[4];",
    ]

    for pair in entangled_pairs:
        t0 = qubit_to_target.get(pair[0])
        t1 = qubit_to_target.get(pair[1])
        if t0 is None or t1 is None:
            continue
        if t0.collapsed:
            if t0.value == "1":
                lines.append(f"x q[{pair[0]}];")
            if t1.value == "1":
                lines.append(f"x q[{pair[1]}];")
        else:
            lines.append(f"ry({t0.theta}) q[{pair[0]}];")
            lines.append(f"cx q[{pair[0]}], q[{pair[1]}];")

    for q in scan_qubits:
        lines.append(f"measure q[{q}] -> c[{q}];")

    counts = send_to_quokka("\n".join(lines) + "\n", shots)

    total = sum(counts.values())
    qubit_p1 = {}
    for q in scan_qubits:
        ones = sum(count for outcome, count in counts.items() if outcome[q] == "1")
        qubit_p1[q] = round(ones / total, 4)

    return qubit_p1


def evaluate_puzzle(puzzle: Puzzle, gates: List[str], shots: int = 100, threshold = 0.8) -> dict:
    """Run the player's circuit on Quokka and evaluate it."""

    # Player used too few gates
    if len(gates) > puzzle.max_gates:
        return {"passed": False, "score": 0.0, "counts": {}, "qasm": "", "error": "Gate budget exceeded"}
    
    # Player used too many gates
    if len(gates) < puzzle.min_gates:
        return {"passed": False, "score": 0.0, "counts": {}, "qasm": "", "error": f"Use at least {puzzle.min_gates} gate(s)"}
    
    # Player used unavailable gates
    for g in gates:
        if g not in puzzle.available_gates:
            return {"passed": False, "score": 0.0, "counts": {}, "qasm": "", "error": f"Gate {g} not availabe"}

    # Evaluate results compared to the expected state
    qasm = build_circuit(puzzle, gates)
    counts = send_to_quokka(qasm, shots)
    score = counts.get(str(puzzle.expected_measurement), 0) / shots
    return {
        "passed": score >= threshold,
        "score": score,
        "qasm": qasm,
    }