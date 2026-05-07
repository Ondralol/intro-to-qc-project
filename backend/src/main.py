from gevent import monkey
monkey.patch_all()

from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS

from game.game_manager import GameManager
from game.game import GamePhase

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

manager = GameManager()


@app.route('/health')
def health():
    return 'ok'


@socketio.on("disconnect")
def handle_disconnect():
    try:
        game = manager.get_game_for_player(request.sid)
        game_id = game.game_id
        manager.remove_player(request.sid)
        emit("opponent_disconnected", room=game_id)
    except ValueError:
        pass


@socketio.on("find_match")
def handle_find_match():
    try:
        game, is_waiting = manager.find_match(request.sid)
        join_room(game.game_id)
        if is_waiting:
            emit("waiting_for_opponent", {"game_id": game.game_id})
        else:
            emit("placement_start", to=game.game_id)
    except Exception as e:
        emit("error", {"message": str(e)})


@socketio.on("place_targets")
def handle_place_targets(data):
    try:
        game = manager.get_game_for_player(request.sid)
        game.place_targets(request.sid, data["targets"])
        emit("placement_confirmed", to=request.sid)
        if game.phase == GamePhase.FIRING:
            emit("game_start", {"current_turn": game.current_turn}, to=game.game_id)
    except Exception as e:
        emit("error", {"message": str(e)})


@socketio.on("play_turn")
def handle_play_turn(data):
    try:
        game = manager.get_game_for_player(request.sid)
        turn_type = data.get("turn_type")

        # Puzzle does not require it to be your turn — attempts are free
        if turn_type != "puzzle" and turn_type != "get_puzzle":
            if game.current_turn != request.sid:
                emit("error", {"message": "Not your turn!"})
                return

        enemy_id = game.player_b_id if game.player_a_id == request.sid else game.player_a_id

        # ------------------------------------------------------------------
        # Fire
        # ------------------------------------------------------------------
        if turn_type == "fire":
            result = game.fire(request.sid, tuple(data["cell"]))
            game.current_turn = result["next_turn"]
            shot_data = {
                "cell": result["cell"],
                "result": result["result"],
                "destroyed_cells": result["destroyed_cells"],
                "pings": result["pings"],
                "next_turn": result["next_turn"],
            }
            emit("shot_result", shot_data, to=request.sid)
            emit("shot_received", shot_data, to=enemy_id)
            if result["game_over"]:
                emit("game_over", {"winner": result["winner"]}, to=game.game_id)

        # ------------------------------------------------------------------
        # Get puzzle (fetch a new puzzle without attempting it)
        # ------------------------------------------------------------------
        elif turn_type == "get_puzzle":
            puzzle = game.get_puzzle(request.sid)
            emit("puzzle_data", {
                "initial": puzzle["initial"],
                "target": puzzle["target"],
                "description": puzzle["description"],
                "hint": puzzle.get("hint", ""),
            }, to=request.sid)

        # ------------------------------------------------------------------
        # Submit puzzle answer
        # ------------------------------------------------------------------
        elif turn_type == "puzzle":
            gates = data.get("gates", [])
            result = game.play_puzzle(request.sid, gates)
            emit("puzzle_result", result, to=request.sid)

        # ------------------------------------------------------------------
        # Radar scan
        # ------------------------------------------------------------------
        elif turn_type == "radar":
            tiles = data.get("tiles", [])
            result = game.radar_scan(request.sid, tiles)
            emit("radar_result", {
                "cell_probs": result["cell_probs"],
                "next_turn": result["next_turn"],
            }, to=request.sid)
            emit("turn_changed", {"next_turn": result["next_turn"]}, to=enemy_id)

        else:
            emit("error", {"message": f"Unknown turn type: {turn_type}"})

    except Exception as e:
        emit("error", {"message": str(e)})


def main():
    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
