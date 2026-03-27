# Assessment 2 — Project Blueprint
## Quantum Battleship
**Introduction to Quantum Computing 2026**
**Group [GROUP NUMBER]**
**Submitted:** [DATE]

---

## 1. Game Concept & Learning Goal

### Game Description

Quantum Battleship is a 2-player turn-based strategy game played on a 7×7 grid. Each player commands two ships:

- **A classical ship** — 3 cells long, placed at a fixed hidden position as in traditional Battleship.
- **A quantum ship** — 3 cells long, but placed in *superposition* across two possible positions (Placement A and Placement B). The ship genuinely occupies both locations simultaneously until it is observed.

Players alternate firing at coordinates on the opponent's grid. A shot landing on one of the opponent's ships deals damage; a shot that touches exactly one of the quantum ship's two possible placements triggers a **quantum measurement** — a real circuit executed on Quokka — that collapses the ship permanently to one of its two positions. Any cells that were hit while the ship was still in superposition are carried over if they match the revealed position.

A player wins by sinking both of the opponent's ships (landing hits on all 3 cells of each).

**Strategic depth from quantum mechanics:** Before the game starts, each player secretly sets a bias angle θ for their quantum ship. A small θ makes Placement A more likely to survive a collapse; a large θ favours Placement B. This means players can lay traps — biasing toward a placement the opponent has already missed — while the opponent has no way of knowing the bias chosen.

### Quantum Concepts Demonstrated

| Concept | Where it appears in gameplay |
|---|---|
| **Superposition** | The quantum ship exists in two locations at once until measured |
| **Wave-function collapse** | A shot landing in exactly one placement forces a real measurement |
| **Biased superposition via RY rotation** | The player-set angle θ controls P(A) = cos²(θ/2) and P(B) = sin²(θ/2) |
| **Born rule** | The collapse outcome is probabilistic according to quantum amplitudes |
| **OpenQASM 2.0** | The full circuit source is shown to players after every collapse event |

### Why Quantum Mechanics Is Essential

The game **cannot be replicated with classical probability alone** in a way that preserves its strategic character. The key distinction is that:

1. The quantum ship is not "secretly in one place but the players don't know which" (hidden variable). It genuinely occupies both placements until a measurement forces a choice. This is why a shot covering both placements scores a hit *without collapsing the ship* — the ship is hit in both realities simultaneously.
2. The collapse probability is not a fixed 50/50 coin flip. It is a continuous quantum amplitude set by the player via θ, directly mapping to the Born rule. Players who understand the physics can exploit this.
3. The QASM circuit — executed live on Quokka — is the mechanism that produces the outcome. Players see the circuit, the rotation angle, and the resulting probabilities. The game is transparent about its quantum machinery.

Replacing Quokka with a classical random number generator would make the game work superficially, but would remove the connection to actual quantum computation and eliminate the educational value.

---

## 2. Quantum Design Sketch

### Quantum System

- **Qubits:** 1 qubit per collapse event
- **Classical registers:** 1 classical bit (measurement output)
- **Gate:** RY(θ) — Y-axis rotation, parameterised by the player's chosen angle
- **Measurement:** standard Z-basis measurement

### Collapse Circuit

```
         ┌─────────┐ ┌─┐
 |0⟩ ────┤  RY(θ)  ├─┤M├──── c[0]
         └─────────┘ └─┘
```

- `|0⟩` is the ground state, encoding "Placement A"
- `RY(θ)` rotates the Bloch vector by angle θ around the Y-axis, creating the superposition:

  |ψ⟩ = cos(θ/2)|0⟩ + sin(θ/2)|1⟩

- Measurement collapses to:
  - **0 → Placement A** with probability P(A) = cos²(θ/2)
  - **1 → Placement B** with probability P(B) = sin²(θ/2)

### OpenQASM 2.0 Source (example at θ = π/2)

```qasm
OPENQASM 2.0;
include "qelib1.inc";

qreg q[1];
creg c[1];

// ry(1.5708) biases the superposition:
//   P(Placement A) = 50.0%
//   P(Placement B) = 50.0%
ry(1.5708) q[0];

// Measure: 0 → Placement A,  1 → Placement B
measure q[0] -> c[0];
```

This QASM string is **generated programmatically** at runtime from the player's θ value and POSTed to Quokka — it is never hard-coded.

### How Quantum Effects Influence Gameplay Outcomes

```
Player sets θ during setup
        │
        ▼
Opponent fires at a cell in exactly ONE placement
        │
        ▼
generate_collapse_qasm(θ)  →  QASM string with ry(θ)
        │
        ▼
POST to Quokka → measurement result: 0 or 1
        │
    ┌───┴───┐
    0       1
    ▼       ▼
  Collapse  Collapse
 to A      to B
    │       │
    └───┬───┘
        ▼
  Game state updated: quantum ship now classical
  Hits from superposition phase carried over if on active placement
  Player notified of outcome + sees full QASM circuit
```

The θ angle directly controls the quantum amplitude — it is not a post-hoc weighting but the rotation angle in the actual circuit sent to Quokka.

---

## 3. Technical Plan

### Tools & Frameworks

| Layer | Technology |
|---|---|
| Quantum execution | **Quokka** (`quokka3.quokkacomputing.com/qsim/qasm`) |
| Circuit language | **OpenQASM 2.0** |
| HTTP client | `requests` — POST circuits to Quokka REST API |
| Game engine | Python 3 (`quantum_battleship.py`) |
| Web backend | **Flask** — REST API serving `/setup`, `/fire`, `/state`, `/reset` |
| Frontend | HTML + vanilla JavaScript |

### Dynamic QASM Generation & Execution

Quantum programs are generated on every collapse event — not pre-written. The flow is:

1. **Player input influences circuit construction.** The player's θ (set via a UI slider during setup) is stored in the game state. When a collapse is triggered, `generate_collapse_qasm(theta)` is called, substituting the live θ value into the QASM template:

   ```python
   f"ry({theta:.4f}) q[0];\n"
   ```

   Every collapse produces a unique circuit parameterised by that player's chosen angle.

2. **Circuit is POSTed to Quokka at runtime:**

   ```python
   requests.post(QUOKKA_URL, json={"script": qasm, "count": 1}, timeout=10)
   ```

3. **Measurement result drives game state:**

   ```python
   outcome = response.json()["result"]["c"][0][0]  # 0 or 1
   ```

   The integer outcome determines which placement survives. This result is genuinely quantum — it obeys the Born rule as simulated by Quokka, not a local pseudo-random number.

4. **Transparency:** The full QASM source, the rotation angle, and the resulting probabilities are all displayed in the browser after each collapse so players can inspect the circuit that determined their fate.

### Classical vs. Quantum Division

| Responsibility | Layer |
|---|---|
| Ship placement validation, overlap detection | Classical (Python) |
| Turn management, win/loss detection | Classical (Python) |
| Tracking superposition state, overlap hits, carried-over hits | Classical (Python — `QuantumShip`) |
| **Determining collapse outcome** | **Quantum (Quokka)** |
| QASM string construction | Classical (Python — string formatting) |
| Game state serialisation / REST API | Classical (Flask) |
| Grid rendering, result display, QASM highlighting | Classical (JavaScript) |

The quantum layer is deliberately minimal and isolated: a single function `simulate_collapse(theta)` is the sole entry point. Everything above and below it is ordinary code.

### Expected Challenges & Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Quokka latency** (1–3 s per HTTP round-trip) | High | Visible pause at collapse moment | Show animated "Collapsing…" indicator; the pause is also a teaching moment |
| **Quokka unavailability** (server down or rate-limited) | Medium | Collapse cannot execute | Fallback to local `random.choices` weighted by Born rule probabilities; game never blocks |
| **Single-shot measurement** produces exact Born-rule distribution in expectation, but one sample can feel surprising | Low | Player confusion | Display P(A)% and P(B)% alongside the result and QASM so the probabilities are explicit |
| **θ edge cases** (θ = 0 or θ = π) make collapse deterministic | Low | Trivialises quantum mechanic if exploited | Intentional — fully biasing to one placement is a valid strategic choice and still runs the circuit on Quokka |
| **Flask singleton game state** — concurrent browser tabs cause race conditions | Low | Bug in rare edge cases | Acceptable for pass-and-play prototype; session-scoped state needed for multiplayer |

---

## 4. Initial Quantum Prototype

### What the Prototype Demonstrates

The submitted codebase is a **fully working quantum prototype** that satisfies all prototype requirements:

| Requirement | Status |
|---|---|
| Programmatically generated QASM (not hard-coded) | ✅ `generate_collapse_qasm(theta)` constructs QASM from live θ at runtime |
| Executes on Quokka | ✅ `simulate_collapse()` POSTs to `quokka3.quokkacomputing.com/qsim/qasm` |
| Demonstrates core quantum mechanic | ✅ Superposition + wave-function collapse drives every game outcome |
| Classical game state influences circuit | ✅ Player's θ (set during setup, stored in game state) is the rotation angle in the circuit |

### Key Code: QASM Generation (game state → circuit)

```python
# quantum_battleship.py — generate_collapse_qasm()
def generate_collapse_qasm(theta: float) -> str:
    p_a = round(math.cos(theta / 2) ** 2, 4)
    p_b = round(math.sin(theta / 2) ** 2, 4)
    return (
        "OPENQASM 2.0;\n"
        'include "qelib1.inc";\n'
        "qreg q[1];\n"
        "creg c[1];\n"
        f"// ry({theta:.4f}) — P(A)={p_a:.1%}, P(B)={p_b:.1%}\n"
        f"ry({theta:.4f}) q[0];\n"
        "measure q[0] -> c[0];\n"
    )
```

The rotation angle `theta` comes directly from the player's setup choice — it is never a fixed constant.

### Key Code: Quokka Execution

```python
# quantum_battleship.py — simulate_collapse()
def simulate_collapse(theta: float) -> int:
    qasm = generate_collapse_qasm(theta)
    try:
        response = requests.post(
            "http://quokka3.quokkacomputing.com/qsim/qasm",
            json={"script": qasm, "count": 1},
            timeout=10
        )
        return int(response.json()["result"]["c"][0][0])
    except Exception:
        # Fallback: local Born-rule sampling
        p_b = math.sin(theta / 2) ** 2
        return random.choices([0, 1], weights=[1 - p_b, p_b])[0]
```

### Running the Prototype

```bash
pip install flask requests
python app.py
# Open http://127.0.0.1:5000
```

Setup → place ships → set θ → hand off device → fire. The first shot hitting exactly one quantum placement executes the circuit on Quokka and collapses the ship.

---

## 5. Team Roles & Responsibilities

| Name | Student Number | Role | Justification |
|---|---|---|---|
| [NAME 1] | [SID] | **Quantum Lead** — circuit design, Quokka integration, QASM generation logic | [Justification — e.g. strongest background in linear algebra and quantum gates from lectures] |
| [NAME 2] | [SID] | **Game Design & Logic** — rules, ship placement, hit/miss engine, win conditions | [Justification — e.g. prior experience with Python OOP; designed the game ruleset] |
| [NAME 3] | [SID] | **Frontend & Integration** — HTML/JS UI, Flask API, connecting frontend to quantum backend | [Justification — e.g. web development background; built the grid and result panels] |
| [NAME 4] | [SID] | **Documentation & Testing** — blueprint report, testing edge cases, milestone tracking | [Justification — e.g. detail-oriented; responsible for ensuring all deliverables are complete] |

> **Note:** Fill in real names, student IDs, and justifications specific to your group.

---

## 6. Milestone Timeline

| Week | Dates | Milestone | Owner(s) |
|---|---|---|---|
| Week 1 | 17–21 Mar | Finalise game concept; agree on quantum mechanic; begin QASM prototype | Quantum Lead, Game Design |
| Week 2 | 24–28 Mar | Complete working Quokka prototype; write blueprint sections 1–4; internal review | All |
| **Phase 1 due** | **1 Apr, 2:00 pm** | **Submit Assessment 2 (this document)** | All |
| Week 3 | 7–11 Apr | Extend prototype: full 7×7 grid, both ship types, θ slider, Flask server | Game Design, Integration |
| Week 4 | 14–18 Apr | Complete game UI; all shot outcomes working; handoff flow between players | Frontend & Integration |
| Week 5 | 21–25 Apr | End-to-end playtesting; fix bugs; polish UI; ensure Quokka integration is robust | All |
| Week 6 | 28 Apr – 2 May | Final testing; prepare presentation slides and live demo script | All |
| **Phase 2 due** | **[FINAL DATE]** | **Submit final project + present** | All |

### Integration Points
- **End of Week 2:** Quantum Lead hands off working `simulate_collapse()` to Integration for wiring into Flask.
- **End of Week 3:** Game Design hands off complete `Game` / `Player` engine to Frontend for UI binding.
- **Week 5:** Full dry-run of presentation using the real game on a local machine.

### Presentation Preparation
- One live game demo (pre-place ships to guarantee a collapse event early)
- Slides: game concept → quantum mechanic → circuit diagram → live QASM output → what we learned
- Each member presents the section they owned

---

*Document prepared for Introduction to Quantum Computing 2026 — Assessment 2.*
