# Quantum Puzzle System — Design Proposal
**Entangled Targets (Quantum Battleships)**

---

## Overview

The puzzle system gives players a way to earn special abilities during the game. Instead of firing, a player can open a quantum puzzle and attempt to solve it. **Puzzle attempts are free (no turn cost)** — only using the unlocked ability costs a turn.

---

## A. Gameplay Flow

```
Player's Turn Starts
        │
        ▼
   Choose Action
   ┌────┴──────────────┬─────────────────┐
   ▼                   ▼                 ▼
🔥 Fire           🔬 Open Puzzle    ⚡ Use Ability
   │                   │                 │
Miss → enemy      Passed?           Ability used
Hit  → your       ├─ No  → Try Again    → enemy's turn
turn              │  (Free, no cost)
                  └─ Yes → Ability Unlocked!
                            Turn continues
```

---

## B. Puzzle Types & Difficulty Levels

### Level 1 — Single Qubit (existing gates: H, X, Z)

| Puzzle | Initial | Target | Solution | Hint |
|--------|---------|--------|----------|------|
| Bit flip | \|0⟩ | \|1⟩ | X | Flip the qubit |
| Reset | \|1⟩ | \|0⟩ | X | Flip the qubit |
| Superposition | \|0⟩ | \|+⟩ | H | Create equal superposition |
| Collapse | \|+⟩ | \|0⟩ | H | H is its own inverse |
| Phase flip | \|+⟩ | \|−⟩ | Z | Flip the phase |

---

### Level 2 — Single Qubit Multi-step (add Y, S gates)

| Puzzle | Initial | Target | Solution | Hint |
|--------|---------|--------|----------|------|
| Minus state | \|0⟩ | \|−⟩ | X → H | Flip then superpose |
| Plus from 1 | \|1⟩ | \|−⟩ | H | Apply Hadamard |
| Phase rotation | \|0⟩ | \|i⟩ | H → S | Superpose then phase shift |
| Double flip | \|0⟩ | \|0⟩ | X → X | Two flips cancel out |
| Combined | \|0⟩ | −\|1⟩ | X → Z | Flip then phase |

**New Gates for Level 2:**
- **Y gate**: Combined bit + phase flip. `Y|0⟩ = i|1⟩`
- **S gate**: 90° phase rotation. `S|1⟩ = i|1⟩`. Used to reach Y eigenstates.

---

### Level 3 — Two Qubits (add CNOT gate)

| Puzzle | Initial | Target | Solution | Hint |
|--------|---------|--------|----------|------|
| Bell State Φ+ | \|00⟩ | (\\|00⟩+\|11⟩)/√2 | H(q0) → CNOT | Hadamard then entangle |
| Bell State Ψ+ | \|00⟩ | (\|01⟩+\|10⟩)/√2 | X(q1) → H(q0) → CNOT | Flip target first |
| SWAP | \|01⟩ | \|10⟩ | CNOT → CNOT(rev) → CNOT | SWAP = 3 CNOTs |
| Entangle from \|11⟩ | \|11⟩ | (\|00⟩−\|11⟩)/√2 | H(q0) → CNOT | Phase depends on initial |

**Circuit Diagram Example (Bell State):**
```
q[0] |0⟩ ──[H]──●────── measure
                 │
q[1] |0⟩ ────── ⊕────── measure

Result: (|00⟩ + |11⟩) / √2
```

---

## C. Reward System

| Puzzle Level | Ability Unlocked | Effect | Turn Cost |
|---|---|---|---|
| Level 1 (1 qubit) | ⚡ **Radar** | Scan a 3×3 area — shows qubit probability for each cell | Yes (1 turn) |
| Level 2 (multi-step) | 🚀 **Quantum Torpedo** | Fires at BOTH anchor positions simultaneously. Forces immediate collapse. | Yes (1 turn) |
| Level 3 (2 qubit) | 💥 **Entanglement Disruptor** | Collapses one of the enemy's uncollapsed entangled pairs immediately, revealing their real positions via pings | Yes (1 turn) |

**Key Rule:** Each puzzle gives one charge of its ability. To get another charge, solve another puzzle.

---

## D. Puzzle UI Design

```
┌─────────────────────────────────────────────────┐
│ 🔬 Quantum Puzzle              [Level 1 · 1Q]   │
│─────────────────────────────────────────────────│
│ Transform the qubit from the initial state to   │
│ the target state by applying the correct gates. │
│                                                 │
│  Initial: |0⟩          →         Target: |1⟩   │
│                                                 │
│ Circuit:                                        │
│ ┌───────────────────────────────────────────┐   │
│ │ |0⟩ → [X] → measure                      │   │
│ └───────────────────────────────────────────┘   │
│ (click a gate chip to remove it)                │
│                                                 │
│ Add Gates:  [H] [X] [Z] [Y] [S] [CNOT]  [Clear]│
│                                                 │
│ 💡 Hint: (shown after 2 fails) Flip the qubit  │
│                                                 │
│ ✓ Passed (100%) — Radar Unlocked!              │
│                                                 │
│          [Cancel]  [Clear]        [Submit →]    │
└─────────────────────────────────────────────────┘
```

**Two-qubit puzzle UI shows two wires:**
```
Circuit:
┌───────────────────────────────────────────┐
│ q[0] |0⟩ → [H] → ●  → measure            │
│                   │                       │
│ q[1] |0⟩ ──────→ ⊕  → measure            │
└───────────────────────────────────────────┘
```

---

## E. Gate Reference Card

| Gate | Symbol | Effect on \|0⟩ | Effect on \|1⟩ | QASM |
|------|--------|----------------|----------------|------|
| NOT | X | → \|1⟩ | → \|0⟩ | `x q[0];` |
| Hadamard | H | → \|+⟩ | → \|−⟩ | `h q[0];` |
| Phase flip | Z | → \|0⟩ | → −\|1⟩ | `z q[0];` |
| Pauli-Y | Y | → i\|1⟩ | → −i\|0⟩ | `y q[0];` |
| S gate | S | → \|0⟩ | → i\|1⟩ | `s q[0];` |
| CNOT | CX | (2-qubit) flips target if control=\|1⟩ | — | `cx q[0],q[1];` |

---

## F. Progressive Hint System

| Attempts | Hint Shown |
|----------|-----------|
| 1–2 | No hint |
| 3–4 | Conceptual hint (e.g. "Flip the qubit") |
| 5+ | Gate name revealed (e.g. "Try the X gate") |

---

## G. Evaluation Logic (Backend)

All puzzles are evaluated via the **Quokka Quantum Simulator API** with **1000 shots**.

**Pass threshold: ≥ 80% probability of measuring the target state**

```python
# Single qubit example
QASM:
  OPENQASM 2.0;
  include "qelib1.inc";
  qreg q[1];
  creg c[1];
  # initial state preparation
  x q[0];        # set to |1⟩ if initial = "1"
  # player gates
  x q[0];        # player applied X
  measure q[0] -> c[0];

# Two qubit example  
QASM:
  OPENQASM 2.0;
  include "qelib1.inc";
  qreg q[2];
  creg c[2];
  # player gates
  h q[0];
  cx q[0], q[1];
  measure q[0] -> c[0];
  measure q[1] -> c[1];
```

**Result mapping:**
- Single qubit: count shots where result = target ("0" or "1")
- Two qubit: count shots where result = target ("00", "11", "01", "10")
- Probability = matching shots / 1000
- Bell states: treat "00" and "11" as both valid for Φ+ (sum their probabilities)

---

## H. Implementation Notes

- Gates available per level are unlocked progressively (Level 1: H, X, Z → Level 2: adds Y, S → Level 3: adds CNOT)
- Puzzle difficulty displayed in modal header with color coding (blue=L1, green=L2, purple=L3)
- Each solved puzzle clears and generates a new one for next attempt
- Radar, Torpedo, and Disruptor all emit `turn_changed` to the enemy after use
- Only one ability can be active at a time (solving L1 while L2 is charged keeps L2 charged)
