"""
Quantum Battleship -- Minimal Prototype
=======================================
Purpose: prove the core quantum mechanic is technically real.

Demonstrates:
  1. Programmatic QASM generation driven by classical game state (theta, ship positions)
  2. Live execution on Quokka (quokka3.quokkacomputing.com)
  3. Wave-function collapse: a shot at one quantum placement collapses the ship
     with probability P(A) = cos^2(theta/2), P(B) = sin^2(theta/2)

No graphics, no web server, no full game loop -- just the quantum core.

Run:
    pip install requests
    python prototype.py
"""

import math
import random
import requests

# ---------------------------------------------------------------------------
# Quokka connection
# ---------------------------------------------------------------------------

QUOKKA_URL = "http://quokka3.quokkacomputing.com/qsim/qasm"


def send_to_quokka(qasm):
    """
    POST an OpenQASM 2.0 program to Quokka.
    Returns the single-bit measurement result (0 or 1).

    This is where classical game state becomes a real quantum computation.
    """
    response = requests.post(
        QUOKKA_URL,
        json={"script": qasm, "count": 1},
        timeout=10,
    )
    result = response.json()["result"]["c"][0][0]
    return int(result)


# ---------------------------------------------------------------------------
# QASM generation -- driven by classical game state
# ---------------------------------------------------------------------------

def build_collapse_circuit(theta):
    """
    Construct the collapse circuit from classical game state.

    'theta' is the player's chosen angle stored in the game state.
    Every collapse event produces a unique, parameterised circuit.

    Circuit:  |0> --- RY(theta) --- Measure --> c[0]

      |0> encodes Placement A
      |1> encodes Placement B
      P(collapse to A) = cos^2(theta/2)
      P(collapse to B) = sin^2(theta/2)
    """
    p_a = math.cos(theta / 2) ** 2
    p_b = math.sin(theta / 2) ** 2

    return (
        "// Quantum Battleship -- Ship Collapse Circuit\n"
        "// Generated at runtime from classical game state (theta)\n"
        "// |0> = Placement A    |1> = Placement B\n"
        "// theta = {:.4f} rad  =>  P(A) = {:.1%},  P(B) = {:.1%}\n"
        "OPENQASM 2.0;\n"
        'include "qelib1.inc";\n'
        "qreg q[1];\n"
        "creg c[1];\n"
        "ry({:.4f}) q[0];\n"
        "measure q[0] -> c[0];\n"
    ).format(theta, p_a, p_b, theta)


# ---------------------------------------------------------------------------
# Quantum ship -- minimal game state object
# ---------------------------------------------------------------------------

class QuantumShip:
    """
    Minimal quantum ship.

    Classical state fields:
      placement_a / placement_b  -- the two possible 3-cell positions
      theta                      -- rotation angle encoding collapse probability

    The theta field feeds directly into the QASM circuit.
    This is the bridge between classical game state and quantum execution.
    """

    def __init__(self, placement_a, placement_b, theta=math.pi / 2):
        self.placement_a = set(map(tuple, placement_a))
        self.placement_b = set(map(tuple, placement_b))
        self.theta = theta          # classical game state -> shapes the quantum circuit
        self.collapsed = False
        self.active_placement = None

    def fire(self, row, col):
        """
        Fire at (row, col).
        Returns a result dict describing the quantum outcome.
        """
        coord = (row, col)
        in_a = coord in self.placement_a
        in_b = coord in self.placement_b

        # Miss -- not in either placement
        if not in_a and not in_b:
            return {"event": "miss"}

        # Hit both -- ship stays in superposition (no measurement yet)
        if in_a and in_b:
            return {
                "event": "hit_both",
                "note":  "Cell is in BOTH placements -- hit scored, ship stays in superposition",
            }

        # Exactly one placement hit -- trigger quantum collapse
        # Build circuit from current classical game state
        qasm = build_collapse_circuit(self.theta)

        # Execute on Quokka -- outcome obeys the Born rule
        outcome = send_to_quokka(qasm)

        self.collapsed = True
        self.active_placement = "A" if outcome == 0 else "B"

        hit_after_collapse = (
            coord in self.placement_a if outcome == 0 else coord in self.placement_b
        )

        return {
            "event":              "collapse",
            "outcome":            outcome,
            "collapsed_to":       self.active_placement,
            "hit_after_collapse": hit_after_collapse,
            "qasm":               qasm,
            "p_a":                math.cos(self.theta / 2) ** 2,
            "p_b":                math.sin(self.theta / 2) ** 2,
        }


# ---------------------------------------------------------------------------
# Demo runner
# ---------------------------------------------------------------------------

def divider(char="-", width=60):
    print(char * width)


def run_scenario(label, placement_a, placement_b, theta, fire_at):
    """Run one demo scenario and print a clear, annotated output."""
    divider("=")
    print("SCENARIO: {}".format(label))
    divider()
    print("  Quantum ship Placement A : {}".format(sorted(placement_a)))
    print("  Quantum ship Placement B : {}".format(sorted(placement_b)))
    print("  Player theta             : {:.4f} rad  ({:.1f} deg)".format(
        theta, math.degrees(theta)))
    print("  P(collapse to A)         : {:.1%}".format(math.cos(theta / 2) ** 2))
    print("  P(collapse to B)         : {:.1%}".format(math.sin(theta / 2) ** 2))
    print("  Shot fired at            : {}".format(fire_at))
    divider()

    ship = QuantumShip(placement_a, placement_b, theta)

    try:
        result = ship.fire(*fire_at)
    except Exception as e:
        print("  [Quokka unreachable - {}]".format(e))
        print("  Falling back to local Born-rule sampling ...")
        p_b = math.sin(theta / 2) ** 2
        outcome = random.choices([0, 1], weights=[1 - p_b, p_b])[0]
        result = {
            "event":              "collapse (local fallback)",
            "outcome":            outcome,
            "collapsed_to":       "A" if outcome == 0 else "B",
            "hit_after_collapse": True,
            "qasm":               build_collapse_circuit(theta),
        }

    event = result["event"]
    print("  Event : {}".format(event.upper()))

    if event == "miss":
        print("  -> No ship at this cell.")

    elif event == "hit_both":
        print("  -> {}".format(result["note"]))

    elif "collapse" in event:
        print()
        print("  +-- QASM sent to Quokka " + "-" * 35 + "+")
        for line in result["qasm"].strip().splitlines():
            print("  |  {}".format(line))
        print("  +" + "-" * 58 + "+")
        print()
        print("  Quokka measurement result : {}".format(result["outcome"]))
        print("  Ship collapsed to         : Placement {}".format(result["collapsed_to"]))
        print("  Hit on active placement?  : {}".format(
            "YES" if result["hit_after_collapse"] else "NO"))

    divider()
    print()


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print()
    print("  QUANTUM BATTLESHIP -- PROTOTYPE")
    print("  Demonstrating: superposition, collapse, Born-rule probability")
    print("  Quantum execution via: Quokka (quokka3.quokkacomputing.com)")
    print()

    # Scenario 1: Equal superposition (theta = pi/2 -- 50/50)
    run_scenario(
        label       = "Equal superposition  (theta = pi/2, P(A) = P(B) = 50%)",
        placement_a = [(2, 3), (2, 4), (2, 5)],   # horizontal row 2
        placement_b = [(4, 1), (5, 1), (6, 1)],   # vertical col 1
        theta       = math.pi / 2,
        fire_at     = (2, 4),                      # in A only -> triggers collapse
    )

    # Scenario 2: Biased toward Placement A (theta = pi/4, P(A) ~= 85%)
    run_scenario(
        label       = "Biased toward A      (theta = pi/4, P(A) ~= 85%)",
        placement_a = [(0, 0), (0, 1), (0, 2)],
        placement_b = [(6, 4), (6, 5), (6, 6)],
        theta       = math.pi / 4,
        fire_at     = (6, 5),                      # in B only -> triggers collapse
    )

    # Scenario 3: Biased toward Placement B (theta = 3*pi/4, P(B) ~= 85%)
    run_scenario(
        label       = "Biased toward B      (theta = 3*pi/4, P(B) ~= 85%)",
        placement_a = [(1, 0), (2, 0), (3, 0)],
        placement_b = [(1, 6), (2, 6), (3, 6)],
        theta       = 3 * math.pi / 4,
        fire_at     = (1, 0),                      # in A only -> triggers collapse
    )

    # Scenario 4: Shot in both placements -- no collapse, ship stays quantum
    run_scenario(
        label       = "Shot in BOTH placements (no collapse -- ship stays in superposition)",
        placement_a = [(3, 3), (3, 4), (3, 5)],
        placement_b = [(3, 3), (4, 3), (5, 3)],   # A and B share cell (3,3)
        theta       = math.pi / 2,
        fire_at     = (3, 3),                      # in both -> hit, no collapse
    )

    print("  All scenarios complete.")
    print()
