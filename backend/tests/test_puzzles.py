"""Tests for game.puzzle. Run from backend/:

    python -m unittest tests.test_puzzles

Stubs out the Quokka HTTP call so tests are offline and deterministic.
"""

import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Make `src/` importable so `from game.puzzle import ...` works.
SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from game import puzzle as puzzle_module  # noqa: E402
from game.puzzle import (  # noqa: E402
    GATE_MAP,
    INIT_PREP,
    N_QUBITS,
    PUZZLES_EASY,
    PUZZLES_HARD,
    Puzzle,
    build_circuit,
    evaluate,
    gate_to_qasm,
    puzzle_payload,
    roll_puzzle,
)


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
        p = Puzzle("|0>", "|1>", ["X"], ["X"], 1, 3, [], "1")
        qasm = build_circuit(p, ["X"])
        self.assertIn("qreg q[1];", qasm)
        self.assertIn("creg c[1];", qasm)
        self.assertIn("x q[0];", qasm)
        self.assertIn("measure q[0] -> c[0];", qasm)

    def test_pre_measurement_basis_change(self):
        # |+> goal -> circuit must apply H before measuring.
        p = Puzzle("|0>", "|+>", ["H"], ["H"], 1, 3, ["H"], "0")
        qasm = build_circuit(p, ["H"])
        # Two H q[0] lines total: one from the player, one from gates_before_measurement.
        self.assertEqual(qasm.count("h q[0];"), 2)

    def test_two_qubit_init_prep(self):
        p = Puzzle("|01>", "|01>", ["I"], [], 0, 1, [], "01")
        qasm = build_circuit(p, [])
        self.assertIn("qreg q[2];", qasm)
        self.assertIn("x q[1];", qasm)  # prep for |01>
        self.assertIn("measure q[0] -> c[0];", qasm)
        self.assertIn("measure q[1] -> c[1];", qasm)

    def test_ordering_prep_player_basis_measure(self):
        p = Puzzle("|0>", "|+>", ["H"], ["H"], 1, 3, ["H"], "0")
        qasm = build_circuit(p, ["H"])
        first = qasm.index("h q[0];")
        last = qasm.rindex("h q[0];")
        self.assertLess(first, last)
        self.assertLess(last, qasm.index("measure"))


class TestEvaluate(unittest.TestCase):
    def _patch(self, counts):
        return patch.object(puzzle_module, "send_to_quokka", return_value=counts)

    def test_pass_when_expected_outcome_dominates(self):
        p = Puzzle("|0>", "|1>", ["X"], ["X"], 1, 3, [], "1", shots=1000)
        with self._patch({"1": 980, "0": 20}):
            r = evaluate(p, ["X"], shots=1000)
        self.assertTrue(r["passed"])
        self.assertAlmostEqual(r["score"], 0.98)
        self.assertIn("x q[0];", r["qasm"])

    def test_fail_when_score_below_threshold(self):
        p = Puzzle("|0>", "|1>", ["X", "I"], ["X"], 1, 3, [], "1", shots=1000)
        with self._patch({"1": 500, "0": 500}):
            r = evaluate(p, ["I"], shots=1000)
        self.assertFalse(r["passed"])
        self.assertEqual(r["score"], 0.5)

    def test_rejects_gate_outside_palette(self):
        p = Puzzle("|0>", "|1>", ["X"], ["X"], 1, 3, [], "1")
        r = evaluate(p, ["H"], shots=1000)
        self.assertFalse(r["passed"])
        self.assertIn("palette", r["error"])

    def test_rejects_too_many_gates(self):
        p = Puzzle("|0>", "|1>", ["X"], ["X"], 1, 2, [], "1")
        r = evaluate(p, ["X", "X", "X"], shots=1000)
        self.assertFalse(r["passed"])
        self.assertIn("budget", r["error"].lower())

    def test_rejects_too_few_gates(self):
        p = Puzzle("|0>", "|1>", ["X"], ["X"], 2, 5, [], "1")
        r = evaluate(p, ["X"], shots=1000)
        self.assertFalse(r["passed"])

    def test_two_qubit_bell_state(self):
        p = next(pz for pz in PUZZLES_HARD
                 if pz.goal_state.startswith("(|00> + |11>)") and pz.initial_state == "|00>")
        # After the basis change (CNOT, H), a perfect |Φ+> collapses to "00".
        with self._patch({"00": 985, "11": 15}):
            r = evaluate(p, p.solution, shots=1000)
        self.assertTrue(r["passed"])


class TestPools(unittest.TestCase):
    """Pool integrity: every puzzle's solution must build, every palette gate
    must parse, and the declared expected_measurement must match qubit count."""

    def test_every_puzzle_compiles_with_its_solution(self):
        for name, pool in [("EASY", PUZZLES_EASY), ("HARD", PUZZLES_HARD)]:
            for i, pz in enumerate(pool):
                with self.subTest(pool=name, idx=i, goal=pz.goal_state):
                    qasm = build_circuit(pz, pz.solution)
                    self.assertIn("OPENQASM 2.0;", qasm)
                    self.assertIn("measure", qasm)

    def test_every_palette_gate_parses(self):
        for name, pool in [("EASY", PUZZLES_EASY), ("HARD", PUZZLES_HARD)]:
            for i, pz in enumerate(pool):
                for g in pz.available_gates:
                    with self.subTest(pool=name, idx=i, gate=g):
                        gate_to_qasm(g)

    def test_initial_state_supported(self):
        for pool in (PUZZLES_EASY, PUZZLES_HARD):
            for pz in pool:
                self.assertIn(pz.initial_state, INIT_PREP)
                self.assertIn(pz.initial_state, N_QUBITS)

    def test_min_le_max_gates(self):
        for pool in (PUZZLES_EASY, PUZZLES_HARD):
            for pz in pool:
                self.assertLessEqual(pz.min_gates, pz.max_gates)
                self.assertLessEqual(len(pz.solution), pz.max_gates)
                self.assertGreaterEqual(len(pz.solution), pz.min_gates)

    def test_expected_measurement_length_matches_qubits(self):
        for pool in (PUZZLES_EASY, PUZZLES_HARD):
            for pz in pool:
                self.assertEqual(len(pz.expected_measurement), N_QUBITS[pz.initial_state])


class TestRolling(unittest.TestCase):
    def test_roll_puzzle_stamps_metadata(self):
        p = roll_puzzle()
        self.assertTrue(p.puzzle_id)
        self.assertEqual(p.shots, puzzle_module.DEFAULT_SHOTS)

    def test_roll_puzzle_draws_from_combined_pool(self):
        all_goals = {pz.goal_state for pz in PUZZLES_EASY + PUZZLES_HARD}
        for _ in range(20):
            self.assertIn(roll_puzzle().goal_state, all_goals)

    def test_roll_puzzle_does_not_mutate_pool(self):
        before = PUZZLES_EASY[0].puzzle_id
        roll_puzzle()
        self.assertEqual(PUZZLES_EASY[0].puzzle_id, before)


class TestPayload(unittest.TestCase):
    def test_payload_has_public_fields_only(self):
        p = roll_puzzle()
        payload = puzzle_payload(p)
        for k in ("puzzle_id", "n_qubits", "initial_state", "goal_state",
                  "available_gates", "min_gates", "max_gates", "note"):
            self.assertIn(k, payload)
        # Solution and answer must NOT leak to the client.
        self.assertNotIn("solution", payload)
        self.assertNotIn("gates_before_measurement", payload)
        self.assertNotIn("expected_measurement", payload)


if __name__ == "__main__":
    unittest.main()
