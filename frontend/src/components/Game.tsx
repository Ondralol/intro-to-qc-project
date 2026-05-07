import { useEffect, useState } from 'react'
import { socket } from '../socket'
import Board, { cellKey } from './Board'
import './Game.css'

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

interface PuzzleData {
  initial: string
  target: string
  description: string
  hint: string
}

interface PuzzleResult {
  passed: boolean
  probability: number
  radar_unlocked: boolean
}

interface RadarResult {
  cell_probs: Record<string, number>
  next_turn: string
}

// Generate the 3×3 (or smaller near edges) area around a center cell
function get3x3(centerKey: string): Set<string> {
  const row = centerKey.charCodeAt(0) - 65
  const col = parseInt(centerKey.slice(1)) - 1
  const area = new Set<string>()
  for (let r = Math.max(0, row - 1); r <= Math.min(6, row + 1); r++) {
    for (let c = Math.max(0, col - 1); c <= Math.min(6, col + 1); c++) {
      area.add(cellKey(r, c))
    }
  }
  return area
}

// Decode cell key "B4" → [row=1, col=3]
function decodeKey(key: string): [number, number] {
  return [key.charCodeAt(0) - 65, parseInt(key.slice(1)) - 1]
}

const AVAILABLE_GATES = ['H', 'X', 'Z'] as const

export default function Game({ myId, firstTurn, myTargetColors }: Props) {
  const [currentTurn, setCurrentTurn] = useState(firstTurn)
  const [gameOver, setGameOver] = useState<'win' | 'loss' | null>(null)

  // My board state (what the enemy did to me)
  const [myHits, setMyHits] = useState<Set<string>>(new Set())
  const [myDestroyed, setMyDestroyed] = useState<Set<string>>(new Set())
  const [myMisses, setMyMisses] = useState<Set<string>>(new Set())
  const [myPings, setMyPings] = useState<Set<string>>(new Set())

  // Enemy board state (what I've done to them)
  const [enemyHits, setEnemyHits] = useState<Set<string>>(new Set())
  const [enemyDestroyed, setEnemyDestroyed] = useState<Set<string>>(new Set())
  const [enemyMisses, setEnemyMisses] = useState<Set<string>>(new Set())
  const [enemyPings, setEnemyPings] = useState<Set<string>>(new Set())
  const [enemyRadarProbs, setEnemyRadarProbs] = useState<Record<string, number>>({})

  // Fire mode
  const [selectedCell, setSelectedCell] = useState<string | null>(null)

  // Puzzle state
  const [showPuzzle, setShowPuzzle] = useState(false)
  const [puzzleData, setPuzzleData] = useState<PuzzleData | null>(null)
  const [gates, setGates] = useState<string[]>([])
  const [puzzleLoading, setPuzzleLoading] = useState(false)
  const [puzzleResult, setPuzzleResult] = useState<PuzzleResult | null>(null)
  const [radarUnlocked, setRadarUnlocked] = useState(false)

  // Radar mode
  const [inRadarMode, setInRadarMode] = useState(false)
  const [radarHoverArea, setRadarHoverArea] = useState<Set<string>>(new Set())
  const [radarSelectedArea, setRadarSelectedArea] = useState<Set<string>>(new Set())
  const [radarCenter, setRadarCenter] = useState<string | null>(null)
  const [radarLoading, setRadarLoading] = useState(false)

  const isMyTurn = currentTurn === myId

  // ── Socket listeners ──────────────────────────────────────────────────────

  useEffect(() => {
    const onShotResult = (data: ShotData) => {
      const key = cellKey(data.cell[0], data.cell[1])
      if (data.result === 'miss') setEnemyMisses(p => new Set(p).add(key))
      else if (data.result === 'hit') setEnemyHits(p => new Set(p).add(key))
      else if (data.result === 'destroyed') {
        setEnemyDestroyed(p => {
          const n = new Set(p)
          for (const [r, c] of data.destroyed_cells) n.add(cellKey(r, c))
          return n
        })
      }
      for (const [r, c] of data.pings) setEnemyPings(p => new Set(p).add(cellKey(r, c)))
      setCurrentTurn(data.next_turn)
      setSelectedCell(null)
    }

    const onShotReceived = (data: ShotData) => {
      const key = cellKey(data.cell[0], data.cell[1])
      if (data.result === 'miss') setMyMisses(p => new Set(p).add(key))
      else if (data.result === 'hit') setMyHits(p => new Set(p).add(key))
      else if (data.result === 'destroyed') {
        setMyDestroyed(p => {
          const n = new Set(p)
          for (const [r, c] of data.destroyed_cells) n.add(cellKey(r, c))
          return n
        })
      }
      for (const [r, c] of data.pings) setMyPings(p => new Set(p).add(cellKey(r, c)))
      setCurrentTurn(data.next_turn)
    }

    const onGameOver = (data: { winner: string }) => {
      setGameOver(data.winner === myId ? 'win' : 'loss')
    }

    const onPuzzleData = (data: PuzzleData) => {
      setPuzzleData(data)
      setGates([])
      setPuzzleResult(null)
    }

    const onPuzzleResult = (data: PuzzleResult) => {
      setPuzzleLoading(false)
      setPuzzleResult(data)
      if (data.radar_unlocked) setRadarUnlocked(true)
    }

    const onRadarResult = (data: RadarResult) => {
      setRadarLoading(false)
      setEnemyRadarProbs(data.cell_probs)
      setCurrentTurn(data.next_turn)
      setInRadarMode(false)
      setRadarCenter(null)
      setRadarSelectedArea(new Set())
      setRadarHoverArea(new Set())
    }

    const onTurnChanged = (data: { next_turn: string }) => {
      setCurrentTurn(data.next_turn)
    }

    socket.on('shot_result', onShotResult)
    socket.on('shot_received', onShotReceived)
    socket.on('game_over', onGameOver)
    socket.on('puzzle_data', onPuzzleData)
    socket.on('puzzle_result', onPuzzleResult)
    socket.on('radar_result', onRadarResult)
    socket.on('turn_changed', onTurnChanged)

    return () => {
      socket.off('shot_result', onShotResult)
      socket.off('shot_received', onShotReceived)
      socket.off('game_over', onGameOver)
      socket.off('puzzle_data', onPuzzleData)
      socket.off('puzzle_result', onPuzzleResult)
      socket.off('radar_result', onRadarResult)
      socket.off('turn_changed', onTurnChanged)
    }
  }, [myId])

  // ── Fire ──────────────────────────────────────────────────────────────────

  const handleEnemyCellClick = (row: number, col: number) => {
    if (!isMyTurn || gameOver) return
    if (inRadarMode) {
      const key = cellKey(row, col)
      setRadarCenter(key)
      setRadarSelectedArea(get3x3(key))
      setRadarHoverArea(new Set())
      return
    }
    const key = cellKey(row, col)
    if (enemyHits.has(key) || enemyMisses.has(key) || enemyDestroyed.has(key)) return
    setSelectedCell(prev => (prev === key ? null : key))
  }

  const handleEnemyCellHover = (row: number, col: number) => {
    if (!inRadarMode || !isMyTurn) return
    if (radarCenter) return // already selected
    setRadarHoverArea(get3x3(cellKey(row, col)))
  }

  const handleFire = () => {
    if (!selectedCell || !isMyTurn || gameOver) return
    const [row, col] = decodeKey(selectedCell)
    socket.emit('play_turn', { turn_type: 'fire', cell: [row, col] })
    setSelectedCell(null)
  }

  // ── Puzzle ────────────────────────────────────────────────────────────────

  const openPuzzle = () => {
    setShowPuzzle(true)
    setPuzzleResult(null)
    setGates([])
    socket.emit('play_turn', { turn_type: 'get_puzzle' })
  }

  const addGate = (gate: string) => {
    if (puzzleLoading) return
    setGates(prev => [...prev, gate])
    setPuzzleResult(null)
  }

  const removeGate = (idx: number) => {
    if (puzzleLoading) return
    setGates(prev => prev.filter((_, i) => i !== idx))
    setPuzzleResult(null)
  }

  const submitPuzzle = () => {
    if (!gates.length || puzzleLoading) return
    setPuzzleLoading(true)
    socket.emit('play_turn', { turn_type: 'puzzle', gates })
  }

  const closePuzzle = () => {
    setShowPuzzle(false)
    setPuzzleData(null)
    setGates([])
    setPuzzleResult(null)
    setPuzzleLoading(false)
  }

  // ── Radar ─────────────────────────────────────────────────────────────────

  const enterRadarMode = () => {
    setInRadarMode(true)
    setRadarCenter(null)
    setRadarSelectedArea(new Set())
    setRadarHoverArea(new Set())
    setSelectedCell(null)
  }

  const cancelRadar = () => {
    setInRadarMode(false)
    setRadarCenter(null)
    setRadarSelectedArea(new Set())
    setRadarHoverArea(new Set())
  }

  const submitRadar = () => {
    if (!radarCenter || radarLoading) return
    const tiles = [...radarSelectedArea].map(k => decodeKey(k))
    setRadarLoading(true)
    socket.emit('play_turn', { turn_type: 'radar', tiles })
  }

  // ── Derived board props ───────────────────────────────────────────────────

  const activeRadarArea = radarCenter ? radarSelectedArea : radarHoverArea

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="game-root">
      {/* Turn banner */}
      <div className={`turn-banner ${isMyTurn ? 'my-turn' : 'their-turn'}`}>
        {gameOver ? (gameOver === 'win' ? 'You won!' : 'You lost') : (isMyTurn ? 'Your turn' : "Opponent's turn")}
      </div>

      {/* Boards */}
      <div className="boards-row">
        {/* My board */}
        <div className="board-panel">
          <span className="board-label">Your Board</span>
          <Board
            cellColors={myTargetColors}
            hitCells={myHits}
            destroyedCells={myDestroyed}
            missCells={myMisses}
            pingCells={myPings}
            disabled
          />
        </div>

        {/* Enemy board */}
        <div className="board-panel">
          <span className="board-label">Enemy Board</span>
          <Board
            hitCells={enemyHits}
            destroyedCells={enemyDestroyed}
            missCells={enemyMisses}
            pingCells={enemyPings}
            selectedCell={inRadarMode ? undefined : (selectedCell ?? undefined)}
            radarArea={activeRadarArea}
            probabilityMap={enemyRadarProbs}
            onCellClick={handleEnemyCellClick}
            onCellHover={handleEnemyCellHover}
            disabled={!isMyTurn || !!gameOver}
          />

          {/* Action area */}
          {isMyTurn && !gameOver && (
            <div className="action-area">
              {!inRadarMode && (
                <div className="fire-row">
                  <button
                    className="btn-fire"
                    onClick={handleFire}
                    disabled={!selectedCell}
                  >
                    {selectedCell ? `Fire at ${selectedCell}` : 'Select a cell'}
                  </button>
                  <button className="btn-puzzle" onClick={openPuzzle}>
                    🔬 Radar Puzzle
                  </button>
                  {radarUnlocked && (
                    <button className="btn-radar" onClick={enterRadarMode}>
                      ⚡ Use Radar
                    </button>
                  )}
                </div>
              )}

              {radarUnlocked && !inRadarMode && (
                <span className="radar-unlocked-badge">Radar charged</span>
              )}

              {inRadarMode && (
                <>
                  <p className="radar-hint">
                    {radarCenter
                      ? `Scan area selected around ${radarCenter}`
                      : 'Hover over the enemy board to preview scan area, then click to select'}
                  </p>
                  <div className="fire-row">
                    <button
                      className="btn-fire"
                      onClick={submitRadar}
                      disabled={!radarCenter || radarLoading}
                    >
                      {radarLoading ? 'Scanning…' : 'Scan Area'}
                    </button>
                    <button className="btn-secondary" onClick={cancelRadar}>
                      Cancel
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Puzzle overlay */}
      {showPuzzle && (
        <div className="puzzle-overlay" onClick={e => e.target === e.currentTarget && closePuzzle()}>
          <div className="puzzle-card">
            <h3>🔬 Quantum Puzzle</h3>

            {puzzleData ? (
              <>
                <p className="puzzle-description">{puzzleData.description}</p>
                {puzzleData.hint && <p className="puzzle-hint">Hint: {puzzleData.hint}</p>}

                {/* Circuit display */}
                <div className="circuit-display">
                  <span className="circuit-label">{puzzleData.initial} →</span>
                  {gates.length === 0 && <span className="circuit-label"> (add gates) </span>}
                  {gates.map((g, i) => (
                    <span
                      key={i}
                      className="gate-chip"
                      onClick={() => removeGate(i)}
                      title="Click to remove"
                    >
                      {g}
                    </span>
                  ))}
                  <span className="circuit-label">→ measure</span>
                </div>

                {/* Gate buttons */}
                <div className="gate-buttons">
                  {AVAILABLE_GATES.map(g => (
                    <button key={g} className="btn-gate" onClick={() => addGate(g)} disabled={puzzleLoading}>
                      {g}
                    </button>
                  ))}
                  <button
                    className="btn-secondary"
                    onClick={() => { setGates([]); setPuzzleResult(null) }}
                    disabled={puzzleLoading}
                  >
                    Clear
                  </button>
                </div>

                {/* Result */}
                {puzzleResult && (
                  <div className={`puzzle-result ${puzzleResult.passed ? 'pass' : 'fail'}`}>
                    {puzzleResult.passed
                      ? `✓ Passed (${Math.round(puzzleResult.probability * 100)}%) — Radar unlocked!`
                      : `✗ Failed (${Math.round(puzzleResult.probability * 100)}%) — Try a different sequence`}
                  </div>
                )}

                {/* Actions */}
                <div className="puzzle-actions">
                  <button className="btn-secondary" onClick={closePuzzle} disabled={puzzleLoading}>
                    {puzzleResult?.passed ? 'Close' : 'Cancel'}
                  </button>
                  <button
                    className="btn-submit"
                    onClick={submitPuzzle}
                    disabled={puzzleLoading || gates.length === 0}
                  >
                    {puzzleLoading ? 'Evaluating…' : 'Submit →'}
                  </button>
                </div>
              </>
            ) : (
              <p className="puzzle-description">Loading puzzle…</p>
            )}
          </div>
        </div>
      )}

      {/* Game-over overlay */}
      {gameOver && (
        <div className="gameover-overlay">
          <div className="gameover-card">
            <h1 className={`gameover-title ${gameOver}`}>
              {gameOver === 'win' ? 'You Win!' : 'You Lose'}
            </h1>
            <p className="gameover-sub">
              {gameOver === 'win'
                ? 'All enemy targets destroyed.'
                : 'All your targets were destroyed.'}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
