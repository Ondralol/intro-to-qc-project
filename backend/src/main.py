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

# Single shared GameManager instance which holds all active games and player sessions
manager = GameManager()

# Ping every 5 minutes to prevent cold start
@app.route('/health')
def health():
    return 'ok'


# Fired automatically by Socket.IO when a client closes the tab or loses connection
# request.sid is the disconnecting player's socket ID, the unique identifier
@socketio.on("disconnect")
def handle_disconnect():
    try:
        game = manager.get_game_for_player(request.sid)
        game_id = game.game_id
        # Clean up both players from the manager and mark the game as disconnected
        manager.remove_player(request.sid)
        # Tell the other player their opponent left
        emit("opponent_disconnected", room=game_id)
    except ValueError:
        # Player disconnected before joining any game
        pass


# Fired when a player clicks Play
# Either puts them in a waiting lobby or pairs them with whoever is already waiting
@socketio.on("find_match")
def handle_find_match():
    try:
        game, is_waiting = manager.find_match(request.sid)
        # Join the Socket.IO room for this game so we can broadcast to both players later
        join_room(game.game_id)
        # There is no opponent yet
        if is_waiting:
            emit("waiting_for_opponent", {"game_id": game.game_id})
        # The second player join, the game can starts
        else:
            emit("placement_start", to=game.game_id)
    except Exception as e:
        emit("error", {"message": str(e)})


# Fired when a player submits their target placement
@socketio.on("place_targets")
def handle_place_targets(data):
    try:
        game = manager.get_game_for_player(request.sid)
        # Place target for the specific player
        game.place_targets(request.sid, data["targets"])
        # Send ack
        emit("placement_confirmed", to=request.sid)
        # Once both players have placed, start the game
        if game.phase == GamePhase.FIRING:
            emit("game_start", {"current_turn": game.current_turn}, to=game.game_id)
    except Exception as e:
        emit("error", {"message": str(e)})


# Fired when a player submits their turn
@socketio.on("play_turn")
def handle_play_turn(data):
    try:
        game = manager.get_game_for_player(request.sid)
        if game.current_turn != request.sid:
            emit("error", {"message": "Not your turn!"})  
            return

        # Get turn type (fire or puzzle)
        turn_type = data.get("turn_type")

        # If fire
        if turn_type == "fire":
            enemy_id = game.player_a_id if game.player_a_id != request.sid else game.player_b_id
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
        
        # If puzzle
        elif turn_type == "puzzle":
            #game.radar(request.sid, data)
            pass
        elif turn_type == "radar":
            enemy_id = game.player_a_id if game.player_a_id != request.sid else game.player_b_id
            tiles = data.get("tiles") or data.get("payload", {}).get("tiles", [])
            result = game.radar(request.sid, tiles)
            game.current_turn = result["next_turn"]
            emit("radar_result", result, to=request.sid)
            emit("turn_changed", {"current_turn": result["next_turn"]}, to=enemy_id)
        else:
            emit("error", {"message": f"Unknown turn type: {turn_type}"})

    except Exception as e:
        emit("error", {"message": str(e)})


def main():
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)


if __name__ == "__main__":
    main()
