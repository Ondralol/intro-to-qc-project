import { useEffect, useState } from 'react'
import { socket } from '../socket'
import Board, { cellKey } from './Board'

interface Props {
  myId: string
  firstTurn: string
  myTargetColors: Record<string, string>
}

interface ShotData {
  cell: [number, number]
  result: 'miss' | 'hit' | 'destroyed'
  destroyed_cells: [number, number][]
  pings: [number, number][]
  next_turn: string
}

export default function Game({ myId, firstTurn, myTargetColors }: Props) {
  const [currentTurn, setCurrentTurn] = useState(firstTurn)
  const [selectedCell, setSelectedCell] = useState<string | null>(null)
  const [gameOver, setGameOver] = useState<'win' | 'loss' | null>(null)

  const [myHits, setMyHits] = useState<Set<string>>(new Set())
  const [myDestroyed, setMyDestroyed] = useState<Set<string>>(new Set())
  const [myMisses, setMyMisses] = useState<Set<string>>(new Set())
  const [myPings, setMyPings] = useState<Set<string>>(new Set())

  const [enemyHits, setEnemyHits] = useState<Set<string>>(new Set())
  const [enemyDestroyed, setEnemyDestroyed] = useState<Set<string>>(new Set())
  const [enemyMisses, setEnemyMisses] = useState<Set<string>>(new Set())
  const [enemyPings, setEnemyPings] = useState<Set<string>>(new Set())

  const isMyTurn = currentTurn === myId

  useEffect(() => {
    socket.on('shot_result', (data: ShotData) => {
      const key = cellKey(data.cell[0], data.cell[1])
      if (data.result === 'miss') {
        setEnemyMisses(prev => new Set(prev).add(key))
      } else if (data.result === 'hit') {
        setEnemyHits(prev => new Set(prev).add(key))
      } else if (data.result === 'destroyed') {
        setEnemyDestroyed(prev => {
          const next = new Set(prev)
          for (const [r, c] of data.destroyed_cells) next.add(cellKey(r, c))
          return next
        })
      }
      for (const [r, c] of data.pings) setEnemyPings(prev => new Set(prev).add(cellKey(r, c)))
      setCurrentTurn(data.next_turn)
      setSelectedCell(null)
    })

    socket.on('shot_received', (data: ShotData) => {
      const key = cellKey(data.cell[0], data.cell[1])
      if (data.result === 'miss') {
        setMyMisses(prev => new Set(prev).add(key))
      } else if (data.result === 'hit') {
        setMyHits(prev => new Set(prev).add(key))
      } else if (data.result === 'destroyed') {
        setMyDestroyed(prev => {
          const next = new Set(prev)
          for (const [r, c] of data.destroyed_cells) next.add(cellKey(r, c))
          return next
        })
      }
      for (const [r, c] of data.pings) setMyPings(prev => new Set(prev).add(cellKey(r, c)))
      setCurrentTurn(data.next_turn)
    })

    socket.on('game_over', (data: { winner: string }) => {
      setGameOver(data.winner === myId ? 'win' : 'loss')
    })

    return () => {
      socket.off('shot_result')
      socket.off('shot_received')
      socket.off('game_over')
    }
  }, [myId])

  const handleEnemyCellClick = (row: number, col: number) => {
    if (!isMyTurn || gameOver) return
    const key = cellKey(row, col)
    if (enemyHits.has(key) || enemyMisses.has(key) || enemyDestroyed.has(key)) return
    setSelectedCell(prev => prev === key ? null : key)
  }

  const handleFire = () => {
    if (!selectedCell || !isMyTurn || gameOver) return
    const row = selectedCell.charCodeAt(0) - 65
    const col = parseInt(selectedCell.slice(1)) - 1
    socket.emit('play_turn', { turn_type: 'fire', cell: [row, col] })
  }

  return (
    <div className="screen" style={{ gap: 32, paddingTop: 32 }}>
      <div style={{
        fontSize: 26,
        fontWeight: 700,
        color: isMyTurn ? '#4af' : '#888',
        letterSpacing: '-0.5px',
      }}>
        {isMyTurn ? 'Your turn' : "Opponent's turn"}
      </div>

      <div style={{ display: 'flex', gap: 64, flexWrap: 'wrap', justifyContent: 'center', alignItems: 'flex-start' }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 20, fontWeight: 600, color: '#ccc' }}>Your Board</span>
          <Board
            cellColors={myTargetColors}
            hitCells={myHits}
            destroyedCells={myDestroyed}
            missCells={myMisses}
            pingCells={myPings}
            disabled
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 20, fontWeight: 600, color: '#ccc' }}>Enemy Board</span>
          <Board
            hitCells={enemyHits}
            destroyedCells={enemyDestroyed}
            missCells={enemyMisses}
            pingCells={enemyPings}
            selectedCell={selectedCell}
            onCellClick={handleEnemyCellClick}
            disabled={!isMyTurn || !!gameOver}
          />
          <button
            onClick={handleFire}
            disabled={!selectedCell || !isMyTurn || !!gameOver}
            style={{ marginTop: 4, padding: '12px 36px', fontSize: 16 }}
          >
            {selectedCell ? `Fire at ${selectedCell}` : 'Select a cell to fire'}
          </button>
        </div>
      </div>

      {gameOver && (
        <div style={{
          position: 'fixed', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(0, 0, 0, 0.75)',
          zIndex: 10,
        }}>
          <div style={{
            background: '#15182a',
            border: '1px solid #2a2e42',
            borderRadius: 12,
            padding: '48px 64px',
            textAlign: 'center',
          }}>
            <h1 style={{
              fontSize: '3rem', margin: '0 0 12px',
              color: gameOver === 'win' ? '#4af' : '#f55',
            }}>
              {gameOver === 'win' ? 'You Win!' : 'You Lose'}
            </h1>
            <p style={{ color: '#888', margin: 0 }}>
              {gameOver === 'win' ? 'All enemy targets destroyed.' : 'All your targets were destroyed.'}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}