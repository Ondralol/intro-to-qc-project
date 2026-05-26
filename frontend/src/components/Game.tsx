import { useEffect, useState } from 'react'
import { socket } from '../socket'
import Board, { cellKey } from './Board'
import PuzzleOverlay from './PuzzleOverlay'
import type { RadarSize } from './PuzzleOverlay'

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

interface RadarResult {
  scan: { cell: [number, number]; probability: number }[]
}

export default function Game({ myId, firstTurn, myTargetColors }: Props) {
  const [currentTurn, setCurrentTurn] = useState(firstTurn)
  const [selectedCell, setSelectedCell] = useState<string | null>(null)
  const [selectedRadarOrigin, setSelectedRadarOrigin] = useState<[number, number] | null>(null)
  const [radarArea, setRadarArea] = useState<Set<string>>(new Set())
  const [radarProbabilities, setRadarProbabilities] = useState<Record<string, number>>({})
  const [gameOver, setGameOver] = useState<'win' | 'loss' | null>(null)

  const [myHits, setMyHits] = useState<Set<string>>(new Set())
  const [myDestroyed, setMyDestroyed] = useState<Set<string>>(new Set())
  const [myMisses, setMyMisses] = useState<Set<string>>(new Set())
  const [myPings, setMyPings] = useState<Set<string>>(new Set())

  const [enemyHits, setEnemyHits] = useState<Set<string>>(new Set())
  const [enemyDestroyed, setEnemyDestroyed] = useState<Set<string>>(new Set())
  const [enemyMisses, setEnemyMisses] = useState<Set<string>>(new Set())
  const [enemyPings, setEnemyPings] = useState<Set<string>>(new Set())

  const [showPuzzle, setShowPuzzle] = useState(false)
  // Set after solving a puzzle — player must use radar this turn
  const [radarUnlocked, setRadarUnlocked] = useState<RadarSize | null>(null)

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
      setRadarProbabilities(prev => { const n = { ...prev }; delete n[key]; return n })
      setRadarArea(prev => { const n = new Set(prev); n.delete(key); return n })
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

    socket.on('turn_changed', (data: { current_turn: string }) => {
      setCurrentTurn(data.current_turn)
    })

    socket.on('radar_result', (data: RadarResult) => {
      const probs: Record<string, number> = {}
      for (const { cell, probability } of data.scan) {
        probs[cellKey(cell[0], cell[1])] = Math.max(0, Math.min(probability, 1))
      }
      setRadarProbabilities(probs)
      setRadarArea(new Set(Object.keys(probs)))
      setSelectedRadarOrigin(null)
    })

    return () => {
      socket.off('shot_result')
      socket.off('shot_received')
      socket.off('game_over')
      socket.off('turn_changed')
      socket.off('radar_result')
    }
  }, [myId])

  const handleEnemyCellClick = (row: number, col: number) => {
    if (!isMyTurn || gameOver) return
    if (radarUnlocked) {
      const size = radarUnlocked === '2x2' ? 2 : 3
      const area = buildRadarArea(row, col, size)
      setSelectedRadarOrigin([row, col])
      setRadarArea(new Set(area.map(([r, c]) => cellKey(r, c))))
      return
    }
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

  const handleRadarUnlocked = (size: RadarSize) => {
    setRadarUnlocked(size)
    setShowPuzzle(false)
    setSelectedCell(null)
  }

  const handleConfirmRadar = () => {
    if (!selectedRadarOrigin || !radarUnlocked || !isMyTurn || gameOver) return
    const size = radarUnlocked === '2x2' ? 2 : 3
    const tiles = buildRadarArea(selectedRadarOrigin[0], selectedRadarOrigin[1], size)
    socket.emit('play_turn', { turn_type: 'submit_radar', cells: tiles })
    setRadarUnlocked(null)
    setSelectedRadarOrigin(null)
  }

  return (
    <div className="screen" style={{ gap: 32, paddingTop: 32 }}>
      <div style={{
        fontSize: 26,
        fontWeight: 700,
        color: isMyTurn ? '#4af' : '#888',
        letterSpacing: '-0.5px',
      }}>
        {gameOver
          ? (gameOver === 'win' ? 'You Win!' : 'You Lose')
          : (isMyTurn ? 'Your turn' : "Opponent's turn")}
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
            radarArea={radarArea}
            probabilityMap={radarProbabilities}
            onCellClick={handleEnemyCellClick}
            disabled={!isMyTurn || !!gameOver}
          />

          {isMyTurn && !gameOver && (
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', justifyContent: 'center' }}>
              {radarUnlocked ? (
                <button
                  onClick={handleConfirmRadar}
                  disabled={!selectedRadarOrigin}
                  style={{ padding: '12px 28px', fontSize: 15 }}
                >
                  {selectedRadarOrigin
                    ? `Scan ${radarUnlocked} area`
                    : `Select ${radarUnlocked} area on board`}
                </button>
              ) : (
                <>
                  <button
                    onClick={handleFire}
                    disabled={!selectedCell}
                    style={{ padding: '12px 28px', fontSize: 15 }}
                  >
                    {selectedCell ? `Fire at ${selectedCell}` : 'Select a cell'}
                  </button>
                  <button
                    onClick={() => setShowPuzzle(true)}
                    style={{ padding: '12px 20px', fontSize: 15 }}
                  >
                    Puzzle
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {showPuzzle && (
        <PuzzleOverlay
          onClose={() => setShowPuzzle(false)}
          onRadarUnlocked={handleRadarUnlocked}
        />
      )}

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

function buildRadarArea(row: number, col: number, size: number): [number, number][] {
  const maxOrigin = 7 - size
  const originRow = Math.min(row, maxOrigin)
  const originCol = Math.min(col, maxOrigin)
  const area: [number, number][] = []
  for (let r = originRow; r < originRow + size; r++) {
    for (let c = originCol; c < originCol + size; c++) {
      area.push([r, c])
    }
  }
  return area
}