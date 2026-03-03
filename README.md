# Quantum Battleships

## Brief explanation
Adaptation of Battleship game where the position of ships is not deterministic, but ships exist in superposition. The game can be played either against another player or against an AI

## Core quantum mechanics
- Ship exists on multiple tiles until meassured by enemy fire (wave function collapses)
- Entaglement between multiple ships. If one part is hit, the entangled ship is hit as well
- Sonar that uses quantum interference to measure whether a ship is at a specific tile with 100% accutacy
- Optionally we can add more quantum mechanics. Cryptography algorithms such as BB84 are really cool and we could create some sort of minigame that would give the player some advantage or something


## Implementation details
- Backed: Python + FlaskAPI-SocketIO deployed on a server
- Fronted: React + socket.io-client
