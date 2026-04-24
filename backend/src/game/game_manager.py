import uuid
from collections import deque
from game.game import Game


class GameManager:
    def __init__(self):
        # Dictionary where the key is game_id and the value is Game
        self.games: dict[str, Game] = {}
        # Dictionary where the key is player_id and the value is game_id
        self.players: dict[str, str] = {}
        # Queue of player ids who have been waiting the longest
        self._waiting: deque[str] = deque()

    def find_match(self, player_id: str) -> tuple[Game, bool]:
        """Join a waiting game or create a new one.

        Returns (game, is_new) where is_new=True means this player is waiting for an opponent.
        """
        # If there is someone waiting
        if self._waiting:
            # Get the game of the person who has been waiting the longest
            game = self._get_game(self._waiting.popleft())
            game.add_player(player_id)
            self.players[player_id] = game.game_id
            return game, False

        # Create new game if nobody is waiting
        game_id = uuid.uuid4().hex[:8]
        game = Game(game_id, player_id)
        self.games[game_id] = game
        self.players[player_id] = game_id
        self._waiting.append(game_id)
        return game, True

    def get_game_for_player(self, player_id):
        game_id = self.players.get(player_id)
        if not game_id:
            raise ValueError("Player is not in a game")
        return self._get_game(game_id)

    def remove_player(self, player_id) -> str | None:
        """Remove player, clean up their game, and return the game_id."""
        game_id = self.players.pop(player_id, None)
        if not game_id or game_id not in self.games:
            return None

        if game_id in self._waiting:
            # Player was still in the lobby, no opponent to notify
            self._waiting.remove(game_id)
        else:
            # Player was in an active game, mark it so the other player knows
            self.games[game_id].disconnected()

        # Also remove the opponent from our player tracking so they can find a new game
        game = self.games[game_id]
        opponent_id = game.player_b_id if player_id == game.player_a_id else game.player_a_id
        self.players.pop(opponent_id, None)

        del self.games[game_id]
        return game_id

    def _get_game(self, game_id):
        if game_id not in self.games:
            raise ValueError("Game not found")
        return self.games[game_id]