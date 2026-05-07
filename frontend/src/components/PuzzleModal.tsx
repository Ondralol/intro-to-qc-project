import { useEffect, useState } from 'react'
import { socket } from '../socket'

export interface Puzzle {
  puzzle_id: string
  tier: number
  n_qubits: number
  initial_state: string
  target_description: string
  gate_palette: string[]
  ry_thetas: number[]
  max_gates: number
}

interface PuzzleResult {
  passed: boolean
  score: number
  counts: Record<string, number>
}

type Gate =
  | { name: 'H' | 'X' | 'Z' | 'S'; qubit: number }
  | { name: 'Ry'; qubit: number; theta: number }
  | { name: 'CX' | 'CZ'; control: number; target: number }
  | { name: 'SWAP'; a: number; b: number }

interface Props {
  puzzle: Puzzle
  onClose: () => void
}

const TWO_QUBIT = new Set(['CX', 'CZ', 'SWAP'])

function gateLabel(g: Gate): string {
  if (g.name === 'Ry') return `Ry(${g.theta}°) q${g.qubit}`
  if (g.name === 'CX' || g.name === 'CZ') return `${g.name} q${g.control}→q${g.target}`
  if (g.name === 'SWAP') return `SWAP q${g.a}↔q${g.b}`
  return `${g.name} q${g.qubit}`
}

export default function PuzzleModal({ puzzle, onClose }: Props) {
  const [gates, setGates] = useState<Gate[]>([])
  const [qubit, setQubit] = useState(0)
  const [theta, setTheta] = useState(puzzle.ry_thetas[0] ?? 45)
  const [result, setResult] = useState<PuzzleResult | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    const onResult = (data: PuzzleResult) => {
      setResult(data)
      setSubmitting(false)
    }
    socket.on('puzzle_result', onResult)
    return () => { socket.off('puzzle_result', onResult) }
  }, [])

  const addSingle = (name: 'H' | 'X' | 'Z' | 'S') => {
    if (gates.length >= puzzle.max_gates) return
    setGates([...gates, { name, qubit }])
  }

  const addRy = () => {
    if (gates.length >= puzzle.max_gates) return
    setGates([...gates, { name: 'Ry', qubit, theta }])
  }

  const addTwo = (name: 'CX' | 'CZ' | 'SWAP') => {
    if (gates.length >= puzzle.max_gates) return
    if (puzzle.n_qubits < 2) return
    if (name === 'SWAP') setGates([...gates, { name, a: 0, b: 1 }])
    else setGates([...gates, { name, control: 0, target: 1 }])
  }

  const undo = () => setGates(gates.slice(0, -1))
  const reset = () => { setGates([]); setResult(null) }

  const submit = () => {
    setSubmitting(true)
    socket.emit('submit_puzzle', { puzzle_id: puzzle.puzzle_id, gates })
  }

  const budgetLeft = puzzle.max_gates - gates.length

  return (
    <div style={{
      position: 'fixed', inset: 0,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'rgba(0, 0, 0, 0.75)', zIndex: 20,
    }}>
      <div style={{
        background: '#15182a',
        border: '1px solid #2a2e42',
        borderRadius: 12,
        padding: '32px 40px',
        width: 520,
        maxWidth: '92vw',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 16 }}>
          <h2 style={{ fontSize: 22, color: '#4af', margin: 0 }}>Radar Puzzle — Tier {puzzle.tier}</h2>
          <span style={{ fontSize: 13, color: '#888' }}>{puzzle.n_qubits} qubit{puzzle.n_qubits > 1 ? 's' : ''}</span>
        </div>

        <div style={{ color: '#ccc', fontSize: 14, marginBottom: 6 }}>
          Start: <span style={{ color: '#eee' }}>{puzzle.initial_state}</span>
        </div>
        <div style={{ color: '#ccc', fontSize: 14, marginBottom: 20 }}>
          Goal: <span style={{ color: '#eee' }}>{puzzle.target_description}</span>
        </div>

        {/* Qubit selector (only when more than one qubit) */}
        {puzzle.n_qubits > 1 && (
          <div style={{ marginBottom: 12, fontSize: 13, color: '#aaa' }}>
            Apply single-qubit gates to:&nbsp;
            {Array.from({ length: puzzle.n_qubits }).map((_, i) => (
              <button
                key={i}
                onClick={() => setQubit(i)}
                className={qubit === i ? 'active' : ''}
                style={{ marginRight: 6, padding: '4px 10px', fontSize: 13 }}
              >q{i}</button>
            ))}
          </div>
        )}

        {/* Ry theta selector */}
        {puzzle.gate_palette.includes('Ry') && (
          <div style={{ marginBottom: 12, fontSize: 13, color: '#aaa' }}>
            Ry angle:&nbsp;
            {puzzle.ry_thetas.map(t => (
              <button
                key={t}
                onClick={() => setTheta(t)}
                className={theta === t ? 'active' : ''}
                style={{ marginRight: 6, padding: '4px 10px', fontSize: 13 }}
              >{t}°</button>
            ))}
          </div>
        )}

        {/* Gate palette */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16 }}>
          {puzzle.gate_palette.map(g => {
            const disabled = gates.length >= puzzle.max_gates
            const onClick = () => {
              if (g === 'Ry') addRy()
              else if (TWO_QUBIT.has(g)) addTwo(g as 'CX' | 'CZ' | 'SWAP')
              else addSingle(g as 'H' | 'X' | 'Z' | 'S')
            }
            return (
              <button key={g} onClick={onClick} disabled={disabled} style={{ minWidth: 56 }}>
                {g}
              </button>
            )
          })}
        </div>

        {/* Sequence preview */}
        <div style={{
          background: '#0d0f1a',
          border: '1px solid #2a2e42',
          borderRadius: 6,
          padding: 12,
          minHeight: 44,
          marginBottom: 8,
          fontFamily: 'monospace',
          fontSize: 13,
          color: '#eee',
        }}>
          {gates.length === 0
            ? <span style={{ color: '#555' }}>(no gates yet)</span>
            : gates.map((g, i) => (
                <span key={i} style={{ marginRight: 10 }}>{i + 1}. {gateLabel(g)}</span>
              ))}
        </div>
        <div style={{ fontSize: 12, color: '#888', marginBottom: 16 }}>
          Gates used: {gates.length} / {puzzle.max_gates}
          {budgetLeft === 0 && <span style={{ marginLeft: 8, color: '#fa4' }}>budget reached</span>}
        </div>

        {/* Result */}
        {result && (
          <div style={{
            border: `1px solid ${result.passed ? '#4af' : '#f55'}`,
            borderRadius: 6, padding: 12, marginBottom: 16, fontSize: 14,
            color: result.passed ? '#4af' : '#f55',
          }}>
            {result.passed ? 'Passed!' : 'Failed.'} score = {(result.score * 100).toFixed(1)}%
            <div style={{ color: '#888', fontFamily: 'monospace', fontSize: 12, marginTop: 4 }}>
              counts: {JSON.stringify(result.counts)}
            </div>
          </div>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button onClick={onClose} style={{ marginRight: 'auto' }}>
            {result?.passed ? 'Close' : 'Cancel'}
          </button>
          <button onClick={undo} disabled={gates.length === 0 || !!result}>Undo</button>
          <button onClick={reset} disabled={gates.length === 0}>Reset</button>
          <button
            onClick={submit}
            disabled={gates.length === 0 || submitting || !!result}
            className="active"
          >
            {submitting ? 'Running…' : 'Submit'}
          </button>
        </div>
      </div>
    </div>
  )
}
