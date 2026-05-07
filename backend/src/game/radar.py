"""Radar scan: reconstruct quantum state and measure qubits whose targets overlap the scan area.

This mirrors `demo/demo.py` but adapted to the actual Game: targets are the enemy's,
each carrying anchor_a/anchor_b cells and a qubit_index. Pairs (0,1) and (2,3) are
entangled via CNOT during placement.
"""

from quokka.quokka import send_to_quokka
from game.game_helper import Target


# Same as Game.ENTANGLED_PAIRS — control qubit listed first.
PAIRS = [(0, 1), (2, 3)]


def build_radar_circuit(targets: list[Target], scan_qubits: list[int]) -> str:
    """QASM that recreates current state of all 4 qubits, then measures only scan_qubits."""
    by_q = {t.qubit_index: t for t in targets}
    n = 4

    qasm = (
        'OPENQASM 2.0;\n'
        'include "qelib1.inc";\n'
        f'qreg q[{n}];\n'
        f'creg c[{n}];\n'
    )

    # State preparation
    for i in range(n):
        t = by_q[i]
        if t.collapsed:
            if t.value == "1":
                qasm += f"x q[{i}];\n"
        else:
            # Only the control qubit of the pair carries the Ry; CNOT propagates it.
            if i in (0, 2):
                qasm += f"ry({t.theta}) q[{i}];\n"

    for ctrl, tgt in PAIRS:
        if not by_q[ctrl].collapsed and not by_q[tgt].collapsed:
            qasm += f"cx q[{ctrl}], q[{tgt}];\n"

    for i in scan_qubits:
        qasm += f"measure q[{i}] -> c[{i}];\n"

    return qasm


def _qubits_overlapping_area(targets: list[Target], area: set[tuple[int, int]]) -> list[int]:
    """Return qubit indices whose targets have any anchor cell inside the scan area."""
    result = []
    for t in targets:
        cells = set(t.anchor_a) | set(t.anchor_b)
        if cells & area:
            result.append(t.qubit_index)
    return sorted(result)


def run_radar_scan(targets: list[Target], area_cells: list[tuple[int, int]], shots: int = 1000) -> dict:
    """Build + run the radar circuit. Returns per-cell probabilities for cells inside the area
    that belong to a measured target's anchor."""
    area = set(area_cells)
    scan_qubits = _qubits_overlapping_area(targets, area)

    if not scan_qubits:
        # Nothing in the area — empty scan, no Quokka call needed.
        return {
            "qasm": "",
            "counts": {},
            "probability_map": {},
            "qubit_results": [],
            "scan_qubits": [],
        }

    qasm = build_radar_circuit(targets, scan_qubits)
    counts = send_to_quokka(qasm, shots)

    # Per-qubit probability of measuring 1
    prob_one_by_qubit: dict[int, float] = {}
    for q_idx in scan_qubits:
        ones = 0
        for outcome, c in counts.items():
            # outcome is a bit string of length 4; index q_idx is that qubit's bit
            if q_idx < len(outcome) and outcome[q_idx] == "1":
                ones += c
        prob_one_by_qubit[q_idx] = ones / shots

    # Build per-cell probability map for cells in the scan area belonging to relevant anchors.
    by_q = {t.qubit_index: t for t in targets}
    probability_map: dict[str, float] = {}
    qubit_results = []

    for q_idx in scan_qubits:
        t = by_q[q_idx]
        p1 = prob_one_by_qubit[q_idx]

        # Anchor A cells inside the area get prob(target lands here) = 1 - p1.
        for r, c in t.anchor_a:
            if (r, c) in area:
                probability_map[f"{r},{c}"] = round(1.0 - p1, 4)
        # Anchor B cells inside the area get prob = p1.
        for r, c in t.anchor_b:
            if (r, c) in area:
                probability_map[f"{r},{c}"] = round(p1, 4)

        if 0.35 <= p1 <= 0.65:
            status = "superposition"
        elif p1 > 0.65:
            status = "anchor_b"
        else:
            status = "anchor_a"
        qubit_results.append({"qubit": q_idx, "prob_one": round(p1, 4), "status": status})

    return {
        "qasm": qasm,
        "counts": counts,
        "probability_map": probability_map,
        "qubit_results": qubit_results,
        "scan_qubits": scan_qubits,
    }
