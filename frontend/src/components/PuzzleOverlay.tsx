import { useEffect, useState } from 'react'
import { socket } from '../socket'
import './PuzzleOverlay.css'

// ── Types ─────────────────────────────────────────────────────────────────────

interface PuzzleData {
  initial: string
  target: string
  description: string
  hint: string
  available_gates?: string[]
}

interface PuzzleResult {
  passed: boolean
  probability: number
  radar_unlocked: boolean
}

export interface Props {
  onClose: () => void
  onRadarUnlocked: (size: RadarSize) => void
}

export type RadarSize = '2x2' | '3x3'

type Step = 'size' | 'loading' | 'puzzle' | 'result'

// ── Gate colours ──────────────────────────────────────────────────────────────

const GATE_COLOR: Record<string, string> = {
  H: '#44aaff',
  X: '#ff4444',
  Z: '#44cc66',
  Y: '#ff8800',
  S: '#aa44ff',
  CNOT: '#ff44aa',
}

function gateColor(g: string) {
  return GATE_COLOR[g] ?? '#888'
}

// ── Sub-components ────────────────────────────────────────────────────────────

/** Visual grid showing the radar area preview */
function RadarGrid({ size }: { size: RadarSize }) {
  const n = size === '2x2' ? 2 : 3
  return (
    <div
      className="radar-grid"
      style={{ gridTemplateColumns: `repeat(${n}, 22px)` }}
    >
      {Array.from({ length: n * n }).map((_, i) => (
        <div key={i} className="radar-cell" />
      ))}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function PuzzleOverlay({ onClose, onRadarUnlocked }: Props) {
  const [step, setStep] = useState<Step>('size')
  const [radarSize, setRadarSize] = useState<RadarSize | null>(null)
  const [puzzleData, setPuzzleData] = useState<PuzzleData | null>(null)
  const [gates, setGates] = useState<string[]>([])
  const [puzzleResult, setPuzzleResult] = useState<PuzzleResult | null>(null)
  const [failCount, setFailCount] = useState(0)

  // ── Drag state ─────────────────────────────────────────────────────────────

  // What is currently being dragged
  type DragSource =
    | { from: 'palette'; gate: string }
    | { from: 'circuit'; gate: string; index: number }

  const [dragging, setDragging] = useState<DragSource | null>(null)
  // Which drop-zone index is highlighted (0 = before gate 0, 1 = after gate 0 …)
  const [dropIndex, setDropIndex] = useState<number | null>(null)
  // Whether pointer is over the palette area (to show "remove" hint)
  const [overPalette, setOverPalette] = useState(false)

  // ── Socket listeners ───────────────────────────────────────────────────────

  useEffect(() => {
    const onPuzzleData = (data: PuzzleData) => {
      setPuzzleData(data)
      setGates([])
      setPuzzleResult(null)
      setStep('puzzle')
    }

    const onPuzzleResult = (data: PuzzleResult) => {
      setPuzzleResult(data)
      if (!data.passed) {
        setFailCount(c => c + 1)
      } else if (radarSize) {
        onRadarUnlocked(radarSize)
      }
      setStep('result')
    }

    socket.on('puzzle_data', onPuzzleData)
    socket.on('puzzle_result', onPuzzleResult)
    return () => {
      socket.off('puzzle_data', onPuzzleData)
      socket.off('puzzle_result', onPuzzleResult)
    }
  }, [radarSize, onRadarUnlocked])

  // ── Actions ────────────────────────────────────────────────────────────────

  const confirmSize = () => {
    if (!radarSize) return
    setStep('loading')
    socket.emit('play_turn', { turn_type: 'get_puzzle', radar_size: radarSize })
  }

  const submitPuzzle = () => {
    if (!gates.length) return
    setStep('loading')
    socket.emit('play_turn', { turn_type: 'puzzle', gates, radar_size: radarSize })
  }

  const tryAgain = () => {
    setGates([])
    setPuzzleResult(null)
    setStep('puzzle')
  }

  const clearGates = () => setGates([])

  // ── Drag handlers ──────────────────────────────────────────────────────────

  const startPaletteDrag = (gate: string) => setDragging({ from: 'palette', gate })

  const startCircuitDrag = (index: number, gate: string) =>
    setDragging({ from: 'circuit', gate, index })

  const endDrag = () => {
    setDragging(null)
    setDropIndex(null)
    setOverPalette(false)
  }

  const onDropZoneOver = (e: React.DragEvent, idx: number) => {
    e.preventDefault()
    setDropIndex(idx)
    setOverPalette(false)
  }

  const onDropZoneDrop = (idx: number) => {
    if (!dragging) return

    setGates(prev => {
      const next = [...prev]
      if (dragging.from === 'palette') {
        next.splice(idx, 0, dragging.gate)
      } else {
        // reorder within circuit
        const from = dragging.index
        next.splice(from, 1)
        const insertAt = idx > from ? idx - 1 : idx
        next.splice(insertAt, 0, dragging.gate)
      }
      return next
    })

    endDrag()
  }

  const onPaletteOver = (e: React.DragEvent) => {
    e.preventDefault()
    setOverPalette(true)
    setDropIndex(null)
  }

  const onPaletteDrop = () => {
    // Dropping onto palette removes a circuit gate
    if (dragging?.from === 'circuit') {
      const idx = dragging.index
      setGates(prev => prev.filter((_, i) => i !== idx))
    }
    endDrag()
  }

  // Click-to-add (alternative to drag)
  const addGateClick = (gate: string) => setGates(prev => [...prev, gate])

  // Click-to-remove
  const removeGate = (idx: number) => setGates(prev => prev.filter((_, i) => i !== idx))

  // ── Derived ────────────────────────────────────────────────────────────────

  const availableGates = puzzleData?.available_gates?.length
    ? puzzleData.available_gates
    : ['H', 'X', 'Z']

  const showHint = failCount >= 2 && puzzleData?.hint

  const isDragging = dragging !== null

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div
      className="po-backdrop"
      onMouseDown={e => e.target === e.currentTarget && onClose()}
    >
      <div className="po-modal">
        {/* Header */}
        <div className="po-header">
          <span className="po-title">🔬 Radar Puzzle</span>
          {radarSize && step !== 'size' && (
            <span className="po-size-badge">{radarSize} radar</span>
          )}
          <button className="po-close" onClick={onClose} aria-label="Close">×</button>
        </div>

        {/* ── Step 1: Size selection ── */}
        {step === 'size' && (
          <div className="po-body">
            <p className="po-subtitle">
              Choose the radar scan size you want to unlock:
            </p>

            <div className="po-size-row">
              {(['2x2', '3x3'] as RadarSize[]).map(sz => (
                <button
                  key={sz}
                  className={`po-size-card ${radarSize === sz ? 'selected' : ''}`}
                  onClick={() => setRadarSize(sz)}
                >
                  <RadarGrid size={sz} />
                  <span className="po-size-label">{sz}</span>
                  <span className="po-size-diff">
                    {sz === '2x2' ? 'Easy puzzle' : 'Hard puzzle'}
                  </span>
                </button>
              ))}
            </div>

            <div className="po-actions">
              <button className="po-btn-secondary" onClick={onClose}>Cancel</button>
              <button
                className="po-btn-primary"
                onClick={confirmSize}
                disabled={!radarSize}
              >
                Confirm →
              </button>
            </div>
          </div>
        )}

        {/* ── Loading ── */}
        {step === 'loading' && (
          <div className="po-body po-loading">
            <div className="po-spinner" />
            <span>Loading…</span>
          </div>
        )}

        {/* ── Step 2: Puzzle ── */}
        {step === 'puzzle' && puzzleData && (
          <div className="po-body">
            {/* Description */}
            <p className="po-description">{puzzleData.description}</p>

            {/* Initial → Target states */}
            <div className="po-states">
              <div className="po-state-box po-initial">
                <span className="po-state-lbl">Initial</span>
                <span className="po-state-val">{puzzleData.initial}</span>
              </div>
              <span className="po-state-arrow">→</span>
              <div className="po-state-box po-target">
                <span className="po-state-lbl">Target</span>
                <span className="po-state-val">{puzzleData.target}</span>
              </div>
            </div>

            {/* Hint (shown after 2 failures) */}
            {showHint && (
              <p className="po-hint">💡 Hint: {puzzleData.hint}</p>
            )}

            {/* Circuit drop area */}
            <div className="po-circuit-section">
              <span className="po-section-lbl">Your Circuit</span>
              <p className="po-circuit-help">
                Drag gates from the palette into the circuit. Click a placed gate to remove it.
              </p>

              <div className={`po-circuit ${isDragging ? 'dragging' : ''}`}>
                {/* Initial state label */}
                <span className="po-circuit-edge">{puzzleData.initial} →</span>

                {/* Drop zone before gate 0 */}
                <DropZone
                  index={0}
                  active={isDragging && dropIndex === 0}
                  onOver={e => onDropZoneOver(e, 0)}
                  onDrop={() => onDropZoneDrop(0)}
                  onLeave={() => setDropIndex(null)}
                />

                {gates.length === 0 && !isDragging && (
                  <span className="po-circuit-empty">drop gates here</span>
                )}

                {gates.map((g, i) => (
                  <div key={i} className="po-circuit-gate-wrap">
                    <div
                      className="po-circuit-gate"
                      draggable
                      onDragStart={() => startCircuitDrag(i, g)}
                      onDragEnd={endDrag}
                      onClick={() => removeGate(i)}
                      title="Drag to reorder · click to remove"
                      style={{
                        borderColor: gateColor(g),
                        color: gateColor(g),
                        background: `${gateColor(g)}18`,
                      }}
                    >
                      {g}
                    </div>
                    <DropZone
                      index={i + 1}
                      active={isDragging && dropIndex === i + 1}
                      onOver={e => onDropZoneOver(e, i + 1)}
                      onDrop={() => onDropZoneDrop(i + 1)}
                      onLeave={() => setDropIndex(null)}
                    />
                  </div>
                ))}

                {/* Measure label */}
                <span className="po-circuit-edge">→ measure</span>
              </div>
            </div>

            {/* Gate palette */}
            <div className="po-palette-section">
              <span className="po-section-lbl">Available Gates</span>
              <p className="po-palette-help">
                Drag into circuit or click to append. Drop a circuit gate here to remove it.
              </p>

              <div
                className={`po-palette ${overPalette && dragging?.from === 'circuit' ? 'drop-target' : ''}`}
                onDragOver={onPaletteOver}
                onDragLeave={() => setOverPalette(false)}
                onDrop={onPaletteDrop}
              >
                {availableGates.map(g => (
                  <div
                    key={g}
                    className="po-palette-gate"
                    draggable
                    onDragStart={() => startPaletteDrag(g)}
                    onDragEnd={endDrag}
                    onClick={() => addGateClick(g)}
                    title={`Drag to add ${g} gate · click to append`}
                    style={{
                      borderColor: gateColor(g),
                      color: gateColor(g),
                    }}
                  >
                    {g}
                  </div>
                ))}

                {overPalette && dragging?.from === 'circuit' && (
                  <span className="po-palette-remove-hint">← drop to remove</span>
                )}
              </div>
            </div>

            <div className="po-actions">
              <button className="po-btn-secondary" onClick={onClose}>Cancel</button>
              <button className="po-btn-secondary" onClick={clearGates} disabled={!gates.length}>
                Clear
              </button>
              <button
                className="po-btn-primary"
                onClick={submitPuzzle}
                disabled={!gates.length}
              >
                Submit →
              </button>
            </div>
          </div>
        )}

        {/* ── Step 3: Result ── */}
        {step === 'result' && puzzleResult && (
          <div className="po-body">
            <div className={`po-result ${puzzleResult.passed ? 'pass' : 'fail'}`}>
              <span className="po-result-icon">{puzzleResult.passed ? '✓' : '✗'}</span>
              <div className="po-result-text">
                <strong>{puzzleResult.passed ? 'Puzzle Solved!' : 'Incorrect Sequence'}</strong>
                <span>
                  Measured target state with{' '}
                  {Math.round(puzzleResult.probability * 100)}% probability
                  {puzzleResult.passed ? '' : ' (need ≥ 80%)'}
                </span>
              </div>
            </div>

            <div className={`po-result-msg ${puzzleResult.passed ? 'pass' : 'fail'}`}>
              {puzzleResult.passed
                ? `🎉 ${radarSize} radar scan is now available! Close this panel and use it on the board.`
                : 'The gate sequence did not produce the target state. Try a different combination.'}
            </div>

            <div className="po-actions">
              {!puzzleResult.passed && (
                <button className="po-btn-secondary" onClick={tryAgain}>
                  Try Again
                </button>
              )}
              <button className="po-btn-primary" onClick={onClose}>
                {puzzleResult.passed ? 'Use Radar' : 'Close'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Drop zone helper component ────────────────────────────────────────────────

interface DropZoneProps {
  index: number
  active: boolean
  onOver: (e: React.DragEvent) => void
  onDrop: () => void
  onLeave: () => void
}

function DropZone({ active, onOver, onDrop, onLeave }: DropZoneProps) {
  return (
    <div
      className={`po-drop-zone ${active ? 'active' : ''}`}
      onDragOver={onOver}
      onDrop={onDrop}
      onDragLeave={onLeave}
    />
  )
}
