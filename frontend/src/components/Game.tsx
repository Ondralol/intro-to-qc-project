import { useEffect, useState } from 'react'
import { socket } from '../socket'
import Board, { cellKey } from './Board'
import PuzzleModal, { type Puzzle } from './PuzzleModal'

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

  const [puzzle, setPuzzle] = useState<Puzzle | null>(null)
  const [requestingPuzzle, setRequestingPuzzle] = useState(false)

  // Radar scan: after passing the puzzle, the player picks a 3x3 area on the enemy board.
  const [radarMode, setRadarMode] = useState(false)
  const [radarAnchor, setRadarAnchor] = useState<[number, number] | null>(null)
  const [scanning, setScanning] = useState(false)
  const [enemyProbabilities, setEnemyProbabilities] = useState<Record<string, number>>({})
  const [enemyRevealed, setEnemyRevealed] = useState<Set<string>>(new Set())

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

    socket.on('puzzle_issued', (data: Puzzle) => {
      setPuzzle(data)
      setRequestingPuzzle(false)
    })

    // When the puzzle passes, close the modal and let the player pick a scan area.
    socket.on('puzzle_result', (data: { passed: boolean }) => {
      if (data.passed) {
        setPuzzle(null)
        setRadarMode(true)
        setRadarAnchor(null)
        setSelectedCell(null)
      }
    })

    socket.on('radar_result', (data: {
      probability_map: Record<string, number>
      scan_cells: [number, number][]
    }) => {
      const probs: Record<string, number> = {}
      for (const [k, v] of Object.entries(data.probability_map)) {
        const [r, c] = k.split(',').map(Number)
        probs[cellKey(r, c)] = v
      }
      setEnemyProbabilities(prev => ({ ...prev, ...probs }))
      setEnemyRevealed(prev => {
        const next = new Set(prev)
        for (const [r, c] of data.scan_cells) next.add(cellKey(r, c))
        return next
      })
      setRadarMode(false)
      setRadarAnchor(null)
      setScanning(false)
    })

    return () => {
      socket.off('shot_result')
      socket.off('shot_received')
      socket.off('game_over')
      socket.off('puzzle_issued')
      socket.off('puzzle_result')
      socket.off('radar_result')
    }
  }, [myId])

  // 3x3 area cells given the chosen anchor (top-left). Clamped so the box stays in-bounds.
  const radarAreaCells = (() => {
    if (!radarAnchor) return [] as [number, number][]
    const [r0, c0] = radarAnchor
    const r = Math.min(r0, 7 - 3)
    const c = Math.min(c0, 7 - 3)
    const cells: [number, number][] = []
    for (let dr = 0; dr < 3; dr++) for (let dc = 0; dc < 3; dc++) cells.push([r + dr, c + dc])
    return cells
  })()
  const radarAreaSet = new Set(radarAreaCells.map(([r, c]) => cellKey(r, c)))

  const handleEnemyCellClick = (row: number, col: number) => {
    if (gameOver) return
    if (radarMode) {
      setRadarAnchor([row, col])
      return
    }
    if (!isMyTurn) return
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

  const handleRadar = () => {
    if (!isMyTurn || gameOver || puzzle || requestingPuzzle || radarMode) return
    setRequestingPuzzle(true)
    socket.emit('request_puzzle')
  }

  const handleScan = () => {
    if (!radarMode || !radarAnchor || scanning) return
    setScanning(true)
    socket.emit('radar_scan', { cells: radarAreaCells })
  }

  const handleCancelScan = () => {
    setRadarMode(false)
    setRadarAnchor(null)
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
            selectedCell={radarMode ? null : selectedCell}
            radarArea={radarMode ? radarAreaSet : (enemyRevealed.size > 0 ? enemyRevealed : undefined)}
            probabilityMap={enemyProbabilities}
            onCellClick={handleEnemyCellClick}
            disabled={(!isMyTurn && !radarMode) || !!gameOver}
          />
          {radarMode ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, marginTop: 4 }}>
              <span style={{ fontSize: 13, color: '#4af' }}>
                {radarAnchor ? '3×3 area selected — click Scan to measure' : 'Click any cell to anchor the 3×3 scan area'}
              </span>
              <div style={{ display: 'flex', gap: 12 }}>
                <button onClick={handleCancelScan} disabled={scanning} style={{ padding: '12px 24px', fontSize: 16 }}>
                  Cancel
                </button>
                <button
                  onClick={handleScan}
                  disabled={!radarAnchor || scanning}
                  className="active"
                  style={{ padding: '12px 36px', fontSize: 16 }}
                >
                  {scanning ? 'Scanning…' : 'Scan'}
                </button>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', gap: 12, marginTop: 4 }}>
              <button
                onClick={handleFire}
                disabled={!selectedCell || !isMyTurn || !!gameOver}
                style={{ padding: '12px 36px', fontSize: 16 }}
              >
                {selectedCell ? `Fire at ${selectedCell}` : 'Select a cell to fire'}
              </button>
              <button
                onClick={handleRadar}
                disabled={!isMyTurn || !!gameOver || !!puzzle || requestingPuzzle}
                style={{ padding: '12px 24px', fontSize: 16 }}
              >
                {requestingPuzzle ? 'Loading…' : 'Radar'}
              </button>
            </div>
          )}
        </div>
      </div>

      {puzzle && <PuzzleModal puzzle={puzzle} onClose={() => setPuzzle(null)} />}

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