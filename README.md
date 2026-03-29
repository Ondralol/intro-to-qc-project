# Entangled targets
This is a single player game where you play against an computer opponent. You and the computer opponent will both have 7x7 map grid and several targets. When the game starts, you will place these targets on your grid and then in each turn, starting with the player, you will try to hit the enemy's targets. The one who eliminates all targets first wins the game. The game will utilize quantum mechanics, such as superposition and entanglement as well as quantum quizz minigame that gives the player a chance to use a special ability to scan an 3x3 area for the targets.

# The map & targets
- There will be a 7x7 Map field with where you can place 4 targets of various sizes. Targets will have the following sizes (tiles dimensions): 1x2, 2x2, 2x3 and 1x4
- Each target can be placed either vertically or diagonally
The map showcase for future reference
```
      1   2   3   4   5   6   7
   +---+---+---+---+---+---+---+
A  | . | . | . | . | . | . | . |
   +---+---+---+---+---+---+---+
B  | . | . | . | . | . | . | . |
   +---+---+---+---+---+---+---+
C  | . | . | . | . | . | . | . |
   +---+---+---+---+---+---+---+
D  | . | . | . | . | . | . | . |
   +---+---+---+---+---+---+---+
E  | . | . | . | . | . | . | . |
   +---+---+---+---+---+---+---+
F  | . | . | . | . | . | . | . |
   +---+---+---+---+---+---+---+
G  | . | . | . | . | . | . | . |
   +---+---+---+---+---+---+---+
```


## Core quantum mechanics
- Each target (1x2, 2x2, 2x3 or 1x4) is represented by a single qubit. This qubit is mapped to two potential locations: **Anchor A (|0>)** and **Anchor B (|1>)**, which represent the specific grid tiles forming the targe'ts shape. The target begins in a superposition of these two anchors using the Hadamard gate. For example, a 1x2 target exists in superposition between **Anchor A** (`A1` + `A2`) and **Anchor B** (`A7` + `B7`). The map positions for Anchors A and B can never overlap, ensuring the target collapses into one distinct location upon measurement.
Further more, the targets are linked in pairs (`1x2 + 2x2` and `2x3 + 1x4`) using CNOT gates to entangle them together. \

Note: For future references, let's define the center of an Anchor as as the midpoint of all grid tiles occupied by the target’s shape, rounded to the nearest valid grid cell. For example, a 1x4 target placed on A1–A4 would have its center at A3.

The user has a few actions they can make in each game step:
### Normal shot: The result depends on the game state and on what they hit

#### Case A: Empty space (Clasical miss)
If the player clicks on a tile that contains neither Anchor A nor Anchor B for any target, it's a standard miss. No QASM is generated and no measurement is sent to Quokka

#### Case B: The first interaction
If the player clicks a tile that belongs to a target in superposition that has not been measured (nor has its entangled qubit been measured), backend triggers a measurement on the corresponding qubit. This will collapse the qubit corresponding to that target as well as the qubit that is entangled with this qubit.  Several things can then happen:
- Direct hit: If the measurement returns |0> and the player clicked on part of the Anchor A (or the measurement returns |1> and the player clicked on part of the Anchor B). That means that the part of the target was successfuly hit and player now knows the part of the whole target.
- Indirect hit: If the measurement returns |1> and the player clicked on part of the Anchor A (or if the measurement returns |0> and the player clicked on part of the Anchor B). This essentially confirms that the position the user's hit was not the correct Anchor. Since the other anchor is the correct one, we will showcase this in the UI by showing a ping at the center of the correct Anchor.
- Entangled reveal: Because the targets are entangled in pairs, measuring one qubit in an entangled pair will instantly collapse its pair. The UI will show a ping at the corresponding anchor for the entangled target as well. 

#### Case C: Subsequent hits
For any target that has been collapsed, the backend uses classical logic. Since the state is no longer in superposition, the position is deterministic and no furhter Quokka calls are required.

### Radar: A ability that allows the player to scan 3x3 area to gain more information about the targets

#### 1. step: Puzzle
In order to unlock the radar, the player must first solve a simple quantum puzzle. They are given an initial and final quantum states. The goal is to transform the initial state using given gates into the final state. Backend will verify their solution by executing their transformation on Quoka. The transformation will be run multiple times (100 or 1000) to verify its accuracy compared to the actual final state. If the probabilities match close enough, the puzzle will be evaluated as successful.

#### 2. step: Area scan
After successfully completing the puzzle, the player selects a 3x3 area on the grid to scan. The radar provides a non-desctructive method to measure the quantum state of targets in that area through state reconstruction.


Since we cannot directly meassure the corresponding qubits in the area, because that would collapse them, we will reconstruct the whole quantum state from the beginning until this step. We will then meassure the corresponding qubits in this scan area several times (100 or 1000). This statistic sampling allows the radar to determine the probability distribution of the targets. \

The radar can result in two scenarios for each meassured qubits:

- Superposition reveal: If the result of the meassurement returns an approximate 50/50 distribution, the target is confirmed to be in a superposition between Anchor A and B. The UI will reveal the full Anchor shape withing the 3x3 area using Color A. This informs the player that the target might be here.

- Deterministic reveal: If the meassurement returns one-sided result (near 0% 100%), we know that target has already been collapsed, either by previous direct short or an entanglement reaction. The UI will highlight the full Anchor shape within the 3x3 area if the target actually is in this area, otherwise nothing will be shown.


## Implementation details
- Backed: Python + FlaskAPI-SocketIO deployed on a server
- Fronted: React + socket.io-client
