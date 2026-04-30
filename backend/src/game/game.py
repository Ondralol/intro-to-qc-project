import random
import json
import requests
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Optional



class GamePhase(Enum):
    WAITING = "waiting"
    PLACEMENT = "placement"
    FIRING = "firing"
    FINISHED = "finished"
    DISCONNECTED = "disconnected"


@dataclass
class Target:
    size: str  # "1x1", "1x2", "1x3", "2x2"
    anchor_a: list[tuple[int, int]] # array of coordinates
    anchor_b: list[tuple[int, int]] # array of coordinates
    theta: float  # Ry angle in radians, set by player during placement
    qubit_index: int  # 0-3
    collapsed: bool = False
    value: Optional[str] = None  # "0" = anchor A, "1" = anchor B

def send_to_quokka(program, count=1, my_quokka='quokka5'):
   request_http = 'https://{}.quokkacomputing.com/qsim/qasm'.format(my_quokka)
   data = {'script': program, 'count': count}
   result = requests.post(request_http, json=data, verify=True)
   json_obj = json.loads(result.content)
   raw_data = json_obj['result']['c']
   counts = Counter(["".join(map(str, shot)) for shot in raw_data])
   print(dict(counts))
   return dict(counts)

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
def get_anchor(anchor:list[tuple[int,int]]) -> tuple[int,int]:
    row = [tile[0] for tile in anchor]
    col = [tile[1] for tile in anchor]
    return (round(sum(row)/len(row)),round(sum(col)/len(col)))
def build_measurement_circuit(targets:list[Target], measured_qubit:int)-> str:
    qasm = (
       'OPENQASM 2.0;\n'
       'include "qelib1.inc";\n'
       'qreg q[4];\n'
       'creg c[4];\n'
   )
    for target in targets:
        q=target.qubit_index
        if target.collapsed:
            if target.value == "1":
                qasm+=f"x q[{q}];\n"
        else:
            if q in [0,2]:
                qasm+=f"ry({target.theta}) q[{q}];\n"
    for control, paired in Game.ENTANGLED_PAIRS:
        control_target = next(t for t in targets if t.qubit_index == control)
        paired_target = next(t for t in targets if t.qubit_index == paired)
        if not control_target.collapsed and not paired_target.collapsed:
            qasm+=f"cx q[{control}], q[{paired}];\n"
    qasm+=f"measure q[{measured_qubit}]->c[{measured_qubit}];\n"
    return qasm
def get_measure_value(count, qubit_index):
    common = max(count, key=count.get)
    return common[qubit_index]

class Game:
    ENTANGLED_PAIRS = [(0, 1), (2, 3)]
    QUBIT_BY_SIZE = {"1x1": 0, "1x2": 1, "1x3": 2, "2x2": 3}
    GRID_SIZE = 7

    def __init__(self, game_id, player_a_id):
        self.game_id = game_id
        self.player_a_id = player_a_id
        self.player_b_id = None
        self.phase = GamePhase.WAITING
        self.current_turn = None
        self.winner = None
        self.targets: dict[str, list[Target]] = {}  # player_id -> their 4 targets
        self.ready = set() # players who have placed their targets

    def add_player(self, player_id: str):
        self.player_b_id = player_id
        self.phase = GamePhase.PLACEMENT

    def place_targets(self, player_id: str, raw_targets: list[dict]):
        """ Adds target for player_id.

        The structure of raw_targets (this is send from the frontend)
        raw_targets: list of 4 target objects, one per size.

        [
          {
            "size":     "1x2" | "2x2" | "2x3" | "1x4",
            "anchor_a": [[row, col], ...],
            "anchor_b": [[row, col], ...],
            "theta":    float   // Ry angle in radians
          },
          ...
        ]

        Rows and cols are 0-indexed (0–6). Anchor A and B must not share any tiles.
        No two targets may share any tile across either anchor.
        """

        if self.phase != GamePhase.PLACEMENT:
            raise ValueError("Not in placement phase")
        if player_id in self.ready:
            raise ValueError("Already placed")
        if len(raw_targets) != 4:
            raise ValueError("Must place exactly 4 targets")

        # Check if the targets match the defined structure    
        sizes = [t["size"] for t in raw_targets]
        if sorted(sizes) != sorted(self.QUBIT_BY_SIZE.keys()):
            raise ValueError("Must place one of each target size")

        targets = []

        # This will contain all positions that have a target placed onto them
        all_tiles: set[tuple[int, int]] = set()

        # Iterate over each target and add it to the game
        for raw in raw_targets:
            anchor_a = [tuple(c) for c in raw["anchor_a"]]
            anchor_b = [tuple(c) for c in raw["anchor_b"]]

            # Check if no tile is out of bounds
            for tile in anchor_a + anchor_b:
                if not (0 <= tile[0] < self.GRID_SIZE and 0 <= tile[1] < self.GRID_SIZE):
                    raise ValueError(f"Tile {tile} is out of bounds")

            # Check if the tiles do not share any tile
            if set(anchor_a) & set(anchor_b):
                raise ValueError(f"Anchor A and B overlap for {raw['size']}")
            
            # Check if the tiles do not overal with another target
            for tile in anchor_a + anchor_b:
                if tile in all_tiles:
                    raise ValueError(f"Tile {tile} overlaps with another target")
                all_tiles.add(tile)
            
            # Append the targets
            targets.append(Target(
                size=raw["size"],
                anchor_a=anchor_a,
                anchor_b=anchor_b,
                theta=raw["theta"],
                qubit_index=self.QUBIT_BY_SIZE[raw["size"]],
            ))

        # Add targets to player and make the player ready
        self.targets[player_id] = targets
        self.ready.add(player_id)


        # If both players are ready, set, set the game state to FIRING 
        # TODO Potential race condition
        if len(self.ready) == 2 and self.phase != GamePhase.FIRING:
            self.phase = GamePhase.FIRING
            # Select who plays first
            if self.current_turn is None:
                self.current_turn = random.choice([self.player_a_id, self.player_b_id])


    def play_puzzle(self, gate_sequence: list[str]):
        return evaluate_puzzle(
            gate_sequence=gate_sequence, initial_state = "|0>", target_outcome= "1", threshold= 0.8, shots=1000
        )

    def fire(self, player_id, coord):
        if self.phase != GamePhase.FIRING:
            raise ValueError("Not in firing phase")
        if player_id != self.current_turn:
            raise ValueError("Not your turn")
        shot = tuple(coord)
        if player_id == self.player_a_id:
            opponent_id = self.player_b_id
        else:
            opponent_id = self.player_a_id
        opponent_targets = self.targets[opponent_id]
        click_target = None
        click_anchor = None
        for target in opponent_targets:
            if shot in target.anchor_a:
                click_target=target
                click_anchor="0"
                break
            elif shot in target.anchor_b:
                click_target=target
                click_anchor="1"
                break
        if click_target is None:
            self.current_turn=opponent_id
            return{
                "result":"miss", "message": "Miss", "next_turn": self.current_turn,
            }
        if click_target.collapsed:
            self.current_turn = opponent_id
            return {"result": "already_collapsed", "collapsed_value": click_target.value, "message": "Target already collapsed.", "next_turn": self.current_turn,
            }
        qasm = build_measurement_circuit(opponent_targets,click_target.qubit_index)
        count = send_to_quokka(qasm, count=1000)
        measured_value = get_measure_value(count, click_target.qubit_index)
        click_target.collapsed=True
        click_target.value=measured_value
        entangled_reveal=None
        for q1, q2 in self.ENTANGLED_PAIRS:
            if click_target.qubit_index == q1:
                entangled_qubit=q2
            elif click_target.qubit_index == q2:
                entangled_qubit=q1
            else:
                continue
            for target in opponent_targets:
                if target.qubit_index == entangled_qubit:
                    target.collapsed=True
                    target.value=measured_value
                    if target.value == "0":
                        ping_an = target.anchor_a
                    else:
                        ping_an=target.anchor_b
                    entangled_reveal={"target_size": target.size, "collapsed_value": target.value, "ping": get_anchor(ping_an),}
        if click_anchor == measured_value:
            result="direct_hit"
            ping = None
        else:
            result="indirect_hit"
            if measured_value == "0":
                correct_an = click_target.anchor_a
            else:
                correct_an=click_target.anchor_b
            ping = get_anchor(correct_an)
        self.current_turn=opponent_id
        return{
            "result": result,
            "clicked_anchor": click_anchor,
            "collapsed_value": measured_value,
            "ping": ping,
            "entangled_reveal": entangled_reveal,
            "counts": count,
            "qasm": qasm,
            "next_turn": self.current_turn,
        }


    def disconnected(self):
        self.phase = GamePhase.DISCONNECTED

        