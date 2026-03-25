# Quantum Battleships

A 2-player twist on the classic Battleship game where one of each player's ships exists in **quantum superposition** — its position is genuinely uncertain until fired upon.

---

## How the Game Works

### Setup

- The grid is **7×7**.
- Each player places **2 ships**, each 3 cells long (horizontal or vertical):
  - **1 classical ship** — a normal ship at a fixed, hidden position.
  - **1 quantum ship** — placed in superposition across **2 possible positions** (Placement A and Placement B). The ship simultaneously occupies both until observed.
- Players also set a **theta (θ)** angle that biases the superposition: at θ = π/2 (default) the ship is equally likely to be in either position; a smaller θ biases toward A, a larger θ toward B.

### Taking a Shot

Players alternate firing at a coordinate on the opponent's grid. The outcome depends on which ships occupy that cell:

| Situation | Result |
|---|---|
| Cell is empty on both ships | Miss |
| Cell hits the classical ship | Hit — ship loses a cell |
| Cell is in **both** quantum placements | Hit — but the quantum ship **stays in superposition** |
| Cell is in **exactly one** quantum placement | **Collapse!** — wave-function collapses (see below) |
| Quantum ship already collapsed | Behaves like a classical ship |

### Quantum Collapse

When a shot lands in exactly one of the two quantum placements, a **1-qubit circuit** runs to resolve the superposition:

```
|0⟩ --[ RY(θ) ]-- Measure
```

- `|0⟩` = Placement A, `|1⟩` = Placement B
- The rotation angle θ sets the probability: `P(A) = cos²(θ/2)`, `P(B) = sin²(θ/2)`
- The measurement result collapses the ship to one placement permanently
- Any hits scored while the ship was in superposition (overlap hits) are carried over if they land on the revealed placement

The game exposes the **OpenQASM 2.0 source** of the collapse circuit so you can see exactly what quantum operation was performed.

### Winning

A player wins when **both** of the opponent's ships are sunk (all 3 cells of each ship have been hit).

---

## Quantum Mechanics Concepts Demonstrated

- **Superposition** — the quantum ship genuinely exists in two places at once before measurement
- **Wave-function collapse** — a single-cell shot forces the system to pick a definite state
- **Biased superposition** — the RY rotation lets you tune the probability of each outcome, demonstrating that quantum states need not be 50/50
- **OpenQASM** — the collapse circuit is shown as standard quantum assembly, making the quantum operation transparent

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python + Flask |
| Game logic | `quantum_battleship.py` (pure Python, no external QC library needed) |
| Frontend | HTML/JS served via Flask templates |
| Quantum circuit | OpenQASM 2.0 (simulated locally with `random.choices`) |

---

## Running Locally

```bash
pip install flask
python app.py
```

Then open `http://127.0.0.1:5000` in your browser.

### API Endpoints

| Method | Route | Description |
|---|---|---|
| `GET` | `/` | Serve the game UI |
| `POST` | `/setup` | Place all ships and start the game |
| `POST` | `/fire` | Fire at `{"row": r, "col": c}` |
| `GET` | `/state` | Get full game state as JSON |
| `POST` | `/reset` | Reset the game |

---
