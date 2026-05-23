"""Tests for game.puzzle and quokka.evaluate_puzzle. Run from backend/:

    uv run python -m unittest tests.test_puzzles
"""

import math
import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from game.puzzle import (  # noqa: E402
    INIT_PREP,
    N_QUBITS,
    PUZZLES_EASY,
    PUZZLES_HARD,
    Puzzle,
    build_circuit,
    gate_to_qasm,
)
from quokka.quokka import evaluate_puzzle  # noqa: E402


class TestGateParser(unittest.TestCase):
    def test_fixed_single_qubit_gates(self):
        self.assertEqual(gate_to_qasm("H"), "h q[0];")
        self.assertEqual(gate_to_qasm("X"), "x q[0];")
        self.assertEqual(gate_to_qasm("Z"), "z q[0];")
        self.assertEqual(gate_to_qasm("S"), "s q[0];")
        self.assertEqual(gate_to_qasm("T"), "t q[0];")
        self.assertEqual(gate_to_qasm("I"), "id q[0];")

    def test_indexed_single_qubit_gates(self):
        self.assertEqual(gate_to_qasm("H_0"), "h q[0];")
        self.assertEqual(gate_to_qasm("X_1"), "x q[1];")
        self.assertEqual(gate_to_qasm("Z_2"), "z q[2];")

    def test_cnot(self):
        self.assertEqual(gate_to_qasm("CNOT_0_1"), "cx q[0], q[1];")
        self.assertEqual(gate_to_qasm("CNOT_1_0"), "cx q[1], q[0];")

    def test_ry_angles(self):
        self.assertEqual(gate_to_qasm("Ry(pi)"), f"ry({math.pi}) q[0];")
        self.assertEqual(gate_to_qasm("Ry(pi/2)"), f"ry({math.pi / 2}) q[0];")
        self.assertEqual(gate_to_qasm("Ry(pi/4)"), f"ry({math.pi / 4}) q[0];")
        self.assertEqual(gate_to_qasm("Ry(0.5)"), "ry(0.5) q[0];")

    def test_ry_with_explicit_qubit(self):
        self.assertEqual(gate_to_qasm("Ry(pi/2)_1"), f"ry({math.pi / 2}) q[1];")

    def test_unknown_gate_raises(self):
        with self.assertRaises(ValueError):
            gate_to_qasm("nope")
        with self.assertRaises(ValueError):
            gate_to_qasm("Q_0")


class TestBuildCircuit(unittest.TestCase):
    def test_single_qubit_init_and_measure(self):
        p = Puzzle("|0>", "|1>", ["X"], ["X"], 1, 3, [], "1", "")
        qasm = build_circuit(p, ["X"])
        self.assertIn("qreg q[1];", qasm)
        self.assertIn("creg c[1];", qasm)
        self.assertIn("x q[0];", qasm)
        self.assertIn("measure q[0] -> c[0];", qasm)

    def test_pre_measurement_basis_change(self):
        p = Puzzle("|0>", "|+>", ["H"], ["H"], 1, 3, ["H"], "0", "")
        qasm = build_circuit(p, ["H"])
        self.assertEqual(qasm.count("h q[0];"), 2)

    def test_two_qubit_init_prep(self):
        p = Puzzle("|01>", "|01>", ["I"], [], 0, 1, [], "01", "")
        qasm = build_circuit(p, [])
        self.assertIn("qreg q[2];", qasm)
        self.assertIn("x q[1];", qasm)
        self.assertIn("measure q[0] -> c[0];", qasm)
        self.assertIn("measure q[1] -> c[1];", qasm)

    def test_ordering_prep_player_basis_measure(self):
        p = Puzzle("|0>", "|+>", ["H"], ["H"], 1, 3, ["H"], "0", "")
        qasm = build_circuit(p, ["H"])
        first = qasm.index("h q[0];")
        last = qasm.rindex("h q[0];")
        self.assertLess(first, last)
        self.assertLess(last, qasm.index("measure"))


class TestEvaluate(unittest.TestCase):
    """Integration tests that use Quokka"""

    def test_rejects_gate_outside_palette(self):
        p = Puzzle("|0>", "|1>", ["X"], ["X"], 1, 3, [], "1", "")
        r = evaluate_puzzle(p, ["H"])
        self.assertFalse(r["passed"])
        self.assertIn("availab", r["error"].lower())

    def test_rejects_too_many_gates(self):
        p = Puzzle("|0>", "|1>", ["X"], ["X"], 1, 2, [], "1", "")
        r = evaluate_puzzle(p, ["X", "X", "X"])
        self.assertFalse(r["passed"])
        self.assertIn("budget", r["error"].lower())

    def test_rejects_too_few_gates(self):
        p = Puzzle("|0>", "|1>", ["X"], ["X"], 2, 5, [], "1", "")
        r = evaluate_puzzle(p, ["X"])
        self.assertFalse(r["passed"])

    def test_easy_solutions_pass(self):
        for i, pz in enumerate(PUZZLES_EASY):
            with self.subTest(idx=i, goal=pz.goal_state):
                r = evaluate_puzzle(pz, pz.solution)
                self.assertTrue(r["passed"], f"EASY[{i}] score={r['score']:.2f}")

    def test_hard_solutions_pass(self):
        for i, pz in enumerate(PUZZLES_HARD):
            with self.subTest(idx=i, goal=pz.goal_state):
                r = evaluate_puzzle(pz, pz.solution)
                self.assertTrue(r["passed"], f"HARD[{i}] score={r['score']:.2f}")


if __name__ == "__main__":
    unittest.main()