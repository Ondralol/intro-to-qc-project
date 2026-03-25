"""Flask backend for 2-player Quantum Battleship."""

import math
from flask import Flask, render_template, jsonify, request
from quantum_battleship import Game

app = Flask(__name__)
game = Game()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/setup", methods=["POST"])
def setup():
    data = request.get_json()
    result = game.setup(
        p1_classical=data["p1_classical"],
        p1_qa=data["p1_qa"],
        p1_qb=data["p1_qb"],
        p2_classical=data["p2_classical"],
        p2_qa=data["p2_qa"],
        p2_qb=data["p2_qb"],
        p1_theta=data.get("p1_theta", math.pi / 2),
        p2_theta=data.get("p2_theta", math.pi / 2),
    )
    return jsonify(result)


@app.route("/fire", methods=["POST"])
def fire():
    data = request.get_json()
    try:
        result = game.fire(int(data["row"]), int(data["col"]))
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@app.route("/state")
def state():
    return jsonify(game.state())


@app.route("/reset", methods=["POST"])
def reset():
    game.reset()
    return jsonify({"ok": True})


if __name__ == "__main__":
    print("\n  Quantum Battleship (2-player) — web UI")
    print("  Open http://127.0.0.1:5000 in your browser\n")
    app.run(debug=True)
