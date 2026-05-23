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
    gates_before_measuremet: List[str]
    # The expected measurement, such as |0>, |1>, |00>, |11>
    expectect_measurement: int

    # Special note shown to the player
    note: str

# Contains all the puzzle options for the easier puzzle version (2x2 Radar)
PUZZLES_EASY = [
    # Actually super easy
    Puzzle(initial_state = "|0>", goal_state="|1>", available_gates=["X", "H", "Z", "I"],
            solution = ["X"], min_gates = 1, max_gates = 10, gates_before_measuremet=[], 
            expectect_measurement=1, note="Not all gates are useful."),
    Puzzle(initial_state = "|0>", goal_state="|+>", available_gates=["X", "H", "Z", "I"],
            solution = ["H"], min_gates = 1, max_gates = 10, gates_before_measuremet=["H"], 
            expectect_measurement=0, note="Not all gates are useful."),
    Puzzle(initial_state = "|+>", goal_state="|->", available_gates=["X", "H", "Z", "I"],
            solution = ["Z"], min_gates = 1, max_gates = 10, gates_before_measuremet=["H"], 
            expectect_measurement=1, note="Not all gates are useful."),
    Puzzle(initial_state = "|->", goal_state="|1>", available_gates=["X", "H", "Z", "I"],
            solution = ["H"], min_gates = 1, max_gates = 10, gates_before_measuremet=[], 
            expectect_measurement=1, note="Not all gates are useful."),

    # Still easy, but bit more difficult
    Puzzle(initial_state = "|0>", goal_state="|->", available_gates=["X", "H", "Z", "I"],
            solution = ["X", "H"], min_gates = 1, max_gates = 10, gates_before_measuremet=["H"], 
            expectect_measurement=1, note="Not all gates are useful."),
    Puzzle(initial_state = "|1>", goal_state="|+>", available_gates=["X", "H", "I"],
            solution = ["X", "H"], min_gates = 1, max_gates = 10, gates_before_measuremet=["H"], 
            expectect_measurement=0, note="Not all gates are useful."),
    Puzzle(initial_state = "|+>", goal_state="|1>", available_gates=["X", "H", "Z", "I"],
            solution = ["H", "X"], min_gates = 1, max_gates = 10, gates_before_measuremet=[], 
            expectect_measurement=1, note="Not all gates are useful."),

    # More difficult
    Puzzle(initial_state = "|0>", goal_state="|1>", available_gates=["H", "Z", "I"],
            solution = ["H", "Z", "H"], min_gates = 1, max_gates = 10, gates_before_measuremet=[], 
            expectect_measurement=1, note="Not all gates are useful."),
    
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