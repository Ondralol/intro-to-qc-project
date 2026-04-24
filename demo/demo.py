import json
import requests
from collections import Counter
import math


def send_to_quokka(program, count=1, my_quokka='quokka5'):
   request_http = 'https://{}.quokkacomputing.com/qsim/qasm'.format(my_quokka)
   data = {'script': program, 'count': count}
   result = requests.post(request_http, json=data, verify=True)
   json_obj = json.loads(result.content)
   raw_data = json_obj['result']['c']
   counts = Counter(["".join(map(str, shot)) for shot in raw_data])
   print(dict(counts))
   return dict(counts)






# Very simplified version of game state, just represents which qubits have collapsed and their value
# Imagine that q0 and q1 have collapsed already and their value is 1 for this example
# theta represents the initial rotation that player initially made, this is needed for
# the reconstruction in Radar Scan
game_state = {
   "q0": {"collapsed": True,  "value": "1", "theta": 50},
   "q1": {"collapsed": True,  "value": "1", "theta": None},
   "q2": {"collapsed": False, "value": None, "theta": 60},
   "q3": {"collapsed": False, "value": None, "theta": None},
}




# Gate representation for the puzzle, there will be more gates option in the final version
GATE_MAP = {
   "H": "h q[0];\n",
   "X": "x q[0];\n",
   "Z": "z q[0];\n",
}




def build_puzzle_circuit(initial_state: str, gate_sequence: list[str]) -> str:
   """ Dynamically generate QASM.


       Using the initial_state and gate_sequence produce a QASM circuit
   """
   qasm = (
       'OPENQASM 2.0;\n'
       'include "qelib1.inc";\n'
       'qreg q[1];\n'
       'creg c[1];\n'
   )


   # initialise qubit based on starting state
   if initial_state == "|1>":
       qasm += "x q[0];\n"
   elif initial_state == "|+>":
       qasm += "h q[0];\n"
   elif initial_state == "|->":
       qasm += "x q[0];\n"
       qasm += "h q[0];\n"


   # append each gate chosen by the player
   for gate in gate_sequence:
       if gate not in GATE_MAP:
           raise ValueError(f"Unknown gate {gate}")
       qasm += GATE_MAP[gate]


   qasm += "measure q[0] -> c[0];\n"
   return qasm






# Currently only handles simple target_outcomes, for outcomes like |->, we would need to apply
# additional gates to the users input to be able to measure the results
def evaluate_puzzle(
   gate_sequence: list[str],
   initial_state: str = "|0>",
   target_outcome: str = "1",
   threshold: float = 0.8,
   shots: int = 1000
) -> dict:
   """ Evalutes the player's circuit."""


   qasm = build_puzzle_circuit(initial_state, gate_sequence)
   print(qasm)


   results = send_to_quokka(qasm, shots)
   print(f"Quokka result ({shots} shots): {results}")


   success_count = results.get(target_outcome, 0)
   probability = success_count / shots


   passed = probability >= threshold




   print(f"P(|{target_outcome}⟩) = {probability * 100}%,  threshold = {int(threshold*100)}% , Passed: {passed}")
   return {
       "qasm": qasm,
       "counts": results,
       "probability": probability,
       "passed": passed,
   }




def build_radar_circuit(game_state: dict, scan_qubits: list[int]) -> str:
   """Dynamically generate QASM for the radar scan.


   Classical game state controls circuit structure:
     - Collapsed qubit:  Hardcode known value instead
     - Uncollapsed qubit: apply Ry(theta) gate to recreate superposition and CNOT to entangle pairs
   """


   n = len(game_state) # This will most likely be 4
   qasm = (
       'OPENQASM 2.0;\n'
       'include "qelib1.inc";\n'
       f'qreg q[{n}];\n'
       f'creg c[{n}];\n'
   )




   qubits = list(game_state.keys())  # ["q0", "q1", "q2", "q3"]


   # For each qubit, the circuit depends entirely on classical game state.
   for i, qubit in enumerate(qubits):
       state = game_state[qubit]
       if state["collapsed"]:
           # It was already meassured, hard code the value
           if state["value"] == "1":
               qasm += f"x q[{i}];  // {qubit} has collapsed to Anchor B\n"
           else:
               qasm += f"// {qubit} collapsed to Anchor A — |0> by default\n"
       else:
           if i % 2 == 0: # only apply to first control qubit
               probability = state['theta'] / 100.0
               theta_rad = 2 * math.asin(math.sqrt(probability))
               qasm += f"ry({theta_rad}) q[{i}];  // {qubit} in superposition — applying Ry(theta)\n"


   # We need to reentangle uncollapsed pairs
   pair_a = (0, 1)  # q0, q1
   pair_b = (2, 3)  # q2, q3


   for control, target in [pair_a, pair_b]:
       ctrl_key = qubits[control]
       tgt_key  = qubits[target]
       if not game_state[ctrl_key]["collapsed"] and not game_state[tgt_key]["collapsed"]:
           qasm += f"cx q[{control}], q[{target}];  // re-entangle {ctrl_key}+{tgt_key}\n"


   # Measure the qubits
   for i in scan_qubits:
       qasm += f"measure q[{i}] -> c[{i}];\n"


   return qasm




def interpret_radar_results(counts: dict, scan_qubits: list[int], shots: int) -> dict:
   """ Interpret the radar scan results."""


   results = {}
   for qubit_idx in scan_qubits:
       ones = 0
       for outcome, count in counts.items():
           # Count the ones
           if qubit_idx < len(outcome) and outcome[qubit_idx] == "1":
               ones += count


       prob_one = ones / shots
       print(prob_one)


       # This will be later updated so we can properly show the actual probability in the UI
       if 0.35 <= prob_one <= 0.65:
           status = "Superposition"
           detail = f"~50/50 split ({round(prob_one*100)}% Anchor B) — target might be in either anchor"
       elif prob_one > 0.65:
           status = "Collapse to Anchor B"
           detail = f"Near-certain Anchor B ({round(prob_one*100)}%)"
       else:
           status = "Collapse to Anchor A"
           detail = f"Near-certain Anchor A ({round((1-prob_one)*100)}%)"


       results[f"q{qubit_idx}"] = {"status": status, "detail": detail, "prob_one": prob_one}
   return results




def run_radar(
   game_state: dict,
   scan_qubits: list[int],
   shots: int = 1000
) -> dict:
   """
   Build radar circuit from current game state, execute it on Quokka and interpret results"""
   qasm = build_radar_circuit(game_state, scan_qubits)
   print("\nRadar QASM:")
   print(qasm)


   counts = send_to_quokka(qasm, shots)
   print(f"Quokka counts ({shots} shots): {counts}")


   results = interpret_radar_results(counts, scan_qubits, shots)
   print("\nRadar Results:")
   for qubit, result in results.items():
       print(f"{qubit}: {result['status']} — {result['detail']}")


   return results


# Simulate the radar
def main():
   print("-" * 50)
   print("Radar showcase")
   print("-" * 50)


   # Try to unlock the radar by completing the puzzle
   print("\nStep 1: Quantum Puzzle")
   print("> Transform |0⟩ so that measuring |1⟩ has > 80% probability")
   print("> Player submits gate sequence: ['X'] (applies X gate)")


   # Simulate the puzzle result
   puzzle_result = evaluate_puzzle(
       gate_sequence=["X"],
       initial_state="|0>",
       target_outcome="1",
       threshold=0.8,
       shots=1000
   )


   if not puzzle_result["passed"]:
       print("\nPuzzle failed: radar remains locked.")
       return


   print("\nPuzzle passed: radar unlocked")


   # Use the radar to scan the current game state
   print("\nStep 2: Radar Scan")
   print("Classical game state:")
   for qubit, state in game_state.items():
       if state["collapsed"]:
           print(f"  {qubit}: collapsed: Anchor {'B' if state['value'] == '1' else 'A'}")
       else:
           print(f"  {qubit}: in superposition")


   print("\nThe player selects scan area covering q2 and q3")
   
   # Assume we get the scan_qubits from the Grid Tile to Anchor + Qubit mapping
   run_radar(
       game_state=game_state,
       scan_qubits=[2, 3],
       shots=1000
   )


   print("\n" + "-" * 50)


if __name__ == "__main__":
   main()
