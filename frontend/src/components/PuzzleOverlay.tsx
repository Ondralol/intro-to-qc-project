import { useEffect, useState } from 'react'
import { socket } from '../socket'
import './PuzzleOverlay.css'

interface PuzzleData {
  initial_state: string
  goal_state: string
  note: string
  available_gates?: string[]
  min_gates?: number
  max_gates?: number
}

interface PuzzleResult {
  passed: boolean
  score: number
}

export interface Props {
  onClose: () => void
  onRadarUnlocked: (size: RadarSize) => void
}

export type RadarSize = '2x2' | '3x3'

type Step = 'size' | 'loading' | 'puzzle' | 'result'

const GATE_COLOR: Record<string, string> = {
  H: '#44aaff',
  X: '#ff4444',
  Z: '#44cc66',
  Y: '#ff8800',
  S: '#aa44ff',
  T: '#ff44aa',
}

function gateColor(g: string) {
  const base = g.replace(/_\d+$/, '').replace(/\(.*\).*$/, '')
  return GATE_COLOR[base] ?? '#888' // fallback to gray color
}

function RadarGrid({ size }: { size: RadarSize }) {
  const n = size === '2x2' ? 2 : 3
  return (
    <div className="radar-grid" style={{ gridTemplateColumns: `repeat(${n}, 22px)` }}>
      {Array.from({ length: n * n }).map((_, i) => (
        <div key={i} className="radar-cell" />
      ))}
    </div>
  )
}

export default function PuzzleOverlay({ onClose, onRadarUnlocked }: Props) {
  const [step, setStep] = useState<Step>('size')
  const [radarSize, setRadarSize] = useState<RadarSize | null>(null)
  const [puzzleData, setPuzzleData] = useState<PuzzleData | null>(null)
  const [gates, setGates] = useState<string[]>([])
  const [puzzleResult, setPuzzleResult] = useState<PuzzleResult | null>(null)

  useEffect(() => {
    const onPuzzleData = (data: PuzzleData) => {
      setPuzzleData(data)
      setGates([])
      setStep('puzzle')
    }
    const onPuzzleResult = (data: PuzzleResult) => {
      setPuzzleResult(data)
      setStep('result')
    }
    socket.on('puzzle', onPuzzleData)
    socket.on('puzzle_result', onPuzzleResult)
    return () => {
      socket.off('puzzle', onPuzzleData)
      socket.off('puzzle_result', onPuzzleResult)
    }
  }, [])

  const confirmSize = () => {
    if (!radarSize) return
    setStep('loading')
    socket.emit('play_turn', { turn_type: 'puzzle', difficulty: radarSize === '2x2' ? 'easy' : 'hard' })
  }

  const submitPuzzle = () => {
    if (!gates.length) return
    setStep('loading')
    socket.emit('play_turn', { turn_type: 'submit_puzzle', gates, radar_size: radarSize })
  }

  const addGate = (gate: string) => setGates(prev => [...prev, gate])
  const removeGate = (idx: number) => setGates(prev => prev.filter((_, i) => i !== idx))
  const clearGates = () => setGates([])

  const availableGates = puzzleData?.available_gates?.length
    ? puzzleData.available_gates
    : ['H', 'X', 'Z']

  const mustUseRadar = step === 'result' && puzzleResult?.passed === true
  const handleBackdrop = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget && !mustUseRadar) onClose()
  }

  return (
    <div className="po-backdrop" onMouseDown={handleBackdrop}>
      <div className="po-modal">
        <div className="po-header">
          <span className="po-title">Radar Puzzle</span>
          {radarSize && step !== 'size' && (
            <span className="po-size-badge">{radarSize}</span>
          )}
          {!mustUseRadar && (
            <button className="po-close" onClick={onClose} aria-label="Close">×</button>
          )}
        </div>

        {/* Size selection */}
        {step === 'size' && (
          <div className="po-body">
            <p className="po-subtitle">Choose radar scan size.</p>
            <div className="po-size-row">
              {(['2x2', '3x3'] as RadarSize[]).map(sz => (
                <button
                  key={sz}
                  className={`po-size-card ${radarSize === sz ? 'selected' : ''}`}
                  onClick={() => setRadarSize(sz)}
                >
                  <RadarGrid size={sz} />
                  <span className="po-size-label">{sz}</span>
                  <span className="po-size-diff">{sz === '2x2' ? 'Easy' : 'Hard'}</span>
                </button>
              ))}
            </div>
            <div className="po-actions">
              <button className="po-btn-secondary" onClick={onClose}>Cancel</button>
              <button className="po-btn-primary" onClick={confirmSize} disabled={!radarSize}>
                Confirm
              </button>
            </div>
          </div>
        )}

        {/* Loading */}
        {step === 'loading' && (
          <div className="po-body po-loading">
            <div className="po-spinner" />
            <span>Loading…</span>
          </div>
        )}

        {/* Puzzle */}
        {step === 'puzzle' && puzzleData && (
          <div className="po-body">
            <p className="po-description">{puzzleData.note}</p>

            <div className="po-states">
              <div className="po-state-box po-initial">
                <span className="po-state-lbl">Initial</span>
                <span className="po-state-val">{puzzleData.initial_state}</span>
              </div>
              <span className="po-state-arrow">→</span>
              <div className="po-state-box po-target">
                <span className="po-state-lbl">Target</span>
                <span className="po-state-val">{puzzleData.goal_state}</span>
              </div>
            </div>

            <div className="po-circuit-section">
              <span className="po-section-lbl">Circuit - click a gate to remove it</span>
              <div className="po-circuit">
                <span className="po-circuit-edge">{puzzleData.initial_state}</span>
                {gates.length === 0 && (
                  <span className="po-circuit-empty">add gates from below</span>
                )}
                {gates.map((g, i) => (
                  <button
                    key={i}
                    className="po-circuit-gate"
                    onClick={() => removeGate(i)}
                    title="Click to remove"
                    style={{ borderColor: gateColor(g), color: gateColor(g), background: `${gateColor(g)}18` }}
                  >
                    {g}
                  </button>
                ))}
                <span className="po-circuit-edge">measure</span>
              </div>
            </div>

            <div className="po-palette-section">
              <span className="po-section-lbl">Available Gates - click to add</span>
              <div className="po-palette">
                {availableGates.map(g => (
                  <button
                    key={g}
                    className="po-palette-gate"
                    onClick={() => addGate(g)}
                    style={{ borderColor: gateColor(g), color: gateColor(g) }}
                  >
                    {g}
                  </button>
                ))}
              </div>
            </div>

            <div className="po-actions">
              <button className="po-btn-secondary" onClick={clearGates} disabled={!gates.length}>
                Clear
              </button>
              <button className="po-btn-primary" onClick={submitPuzzle} disabled={!gates.length}>
                Submit
              </button>
            </div>
          </div>
        )}

        {/* Result */}
        {step === 'result' && puzzleResult && (
          <div className="po-body">
            <div className={`po-result ${puzzleResult.passed ? 'pass' : 'fail'}`}>
              <span className="po-result-icon">{puzzleResult.passed ? '✓' : '✗'}</span>
              <div className="po-result-text">
                <strong>{puzzleResult.passed ? 'Solved' : 'Incorrect'}</strong>
                <span>
                  {Math.round(puzzleResult.score * 100)}% target state probability
                  {puzzleResult.passed ? '' : ' (need ≥ 80%)'}
                </span>
              </div>
            </div>
            <div className={`po-result-msg ${puzzleResult.passed ? 'pass' : 'fail'}`}>
              {puzzleResult.passed
                ? `${radarSize} radar ready. Use it now.`
                : 'Incorrect sequence — turn passes to opponent.'}
            </div>
            <div className="po-actions">
              <button
                className="po-btn-primary"
                onClick={() => radarSize && puzzleResult.passed ? onRadarUnlocked(radarSize) : onClose()}
              >
                {puzzleResult.passed ? 'Use Radar' : 'Close'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}