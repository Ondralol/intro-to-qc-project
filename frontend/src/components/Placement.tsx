import { useRef, useState } from 'react'
import { socket } from '../socket'
import Board, { cellKey } from './Board'

const SIZES = ['1x1', '1x2', '1x3', '2x2'] as const
type Size = typeof SIZES[number]

const TILE_COUNT: Record<Size, number> = { '1x1': 1, '1x2': 2, '1x3': 3, '2x2': 4 }

const SHAPE_HINT: Record<Size, string> = {
  '1x1': '',
  '1x2': 'Must be 2 adjacent cells',
  '1x3': 'Must be 3 cells in a straight line',
  '2x2': 'Must be a 2×2 square',
}

// Pair 1: 1x1 + 1x2  |  Pair 2: 1x3 + 2x2
const PAIRS: [Size, Size][] = [['1x1', '1x2'], ['1x3', '2x2']]

type Coord = [number, number]
type TargetPlacement = { anchor_a: Coord[]; anchor_b: Coord[] }
type Placements = Record<Size, TargetPlacement>

const TARGET_COLOURS: Record<Size, { a: string; b: string }> = {
  '1x1': { a: '#1565C0', b: '#0D47A1' },
  '1x2': { a: '#2E7D32', b: '#1B5E20' },
  '1x3': { a: '#E65100', b: '#BF360C' },
  '2x2': { a: '#6A1B9A', b: '#4A148C' },
}

const initPlacements = (): Placements =>
  Object.fromEntries(SIZES.map(s => [s, { anchor_a: [], anchor_b: [] }])) as unknown as Placements

const DEBUG_PLACEMENTS: Placements = {
  '1x1': { anchor_a: [[0, 0]],                          anchor_b: [[0, 2]] },
  '1x2': { anchor_a: [[1, 0], [1, 1]],                  anchor_b: [[1, 3], [1, 4]] },
  '1x3': { anchor_a: [[2, 0], [2, 1], [2, 2]],          anchor_b: [[2, 4], [2, 5], [2, 6]] },
  '2x2': { anchor_a: [[4, 0], [4, 1], [5, 0], [5, 1]], anchor_b: [[4, 3], [4, 4], [5, 3], [5, 4]] },
}

function isValidPartial(coords: Coord[], size: Size): boolean {
  if (coords.length <= 1) return true

  switch (size) {
    case '1x1':
      return false

    case '1x2': {
      const [[r0, c0], [r1, c1]] = coords
      return (r0 === r1 && Math.abs(c0 - c1) === 1) || (c0 === c1 && Math.abs(r0 - r1) === 1)
    }

    case '1x3': {
      const rows = coords.map(([r]) => r)
      const cols = coords.map(([, c]) => c)
      const sameRow = rows.every(r => r === rows[0])
      const sameCol = cols.every(c => c === cols[0])
      if (!sameRow && !sameCol) return false
      if (sameRow) {
        const sorted = [...cols].sort((a, b) => a - b)
        return sorted.every((c, i) => i === 0 || c === sorted[i - 1] + 1)
      } else {
        const sorted = [...rows].sort((a, b) => a - b)
        return sorted.every((r, i) => i === 0 || r === sorted[i - 1] + 1)
      }
    }

    case '2x2': {
      const rows = [...new Set(coords.map(([r]) => r))].sort((a, b) => a - b)
      const cols = [...new Set(coords.map(([, c]) => c))].sort((a, b) => a - b)
      if (rows.length > 2 || cols.length > 2) return false
      if (rows.length === 2 && rows[1] - rows[0] !== 1) return false
      if (cols.length === 2 && cols[1] - cols[0] !== 1) return false
      return true
    }
  }
}

const pctToTheta = (pct: number) => 2 * Math.acos(Math.sqrt(pct / 100))

interface Props {
  onConfirm: (cellColors: Record<string, string>) => void
}

export default function Placement({ onConfirm }: Props) {
  const [placements, setPlacements] = useState<Placements>(initPlacements)
  const [activeSize, setActiveSize] = useState<Size>('1x1')
  const [activeAnchor, setActiveAnchor] = useState<'A' | 'B'>('A')
  const [submitted, setSubmitted] = useState(false)
  const [warning, setWarning] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [pair1Pct, setPair1Pct] = useState(50)
  const [pair2Pct, setPair2Pct] = useState(50)
  const warningTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const showWarning = (msg: string) => {
    if (warningTimer.current) clearTimeout(warningTimer.current)
    setWarning(msg)
    warningTimer.current = setTimeout(() => setWarning(null), 2500)
  }

  const selectSize = (s: Size) => {
    setActiveSize(s)
    setActiveAnchor('A')
    setWarning(null)
  }

  const getCell = (row: number, col: number): { size: Size; anchor: 'A' | 'B' } | null => {
    for (const s of SIZES) {
      if (placements[s].anchor_a.some(([r, c]) => r === row && c === col)) return { size: s, anchor: 'A' }
      if (placements[s].anchor_b.some(([r, c]) => r === row && c === col)) return { size: s, anchor: 'B' }
    }
    return null
  }

  const handleCellClick = (row: number, col: number) => {
    if (submitted) return
    const anchorKey = activeAnchor === 'A' ? 'anchor_a' : 'anchor_b'
    const current = placements[activeSize][anchorKey]
    const alreadyInThisAnchor = current.some(([r, c]) => r === row && c === col)

    if (alreadyInThisAnchor) {
      setWarning(null)
      setPlacements(prev => ({
        ...prev,
        [activeSize]: { ...prev[activeSize], [anchorKey]: current.filter(([r, c]) => !(r === row && c === col)) },
      }))
      return
    }

    if (getCell(row, col) !== null) return
    if (current.length >= TILE_COUNT[activeSize]) return

    const next: Coord[] = [...current, [row, col]]
    if (!isValidPartial(next, activeSize)) {
      showWarning(SHAPE_HINT[activeSize])
      return
    }

    setWarning(null)
    setPlacements(prev => ({
      ...prev,
      [activeSize]: { ...prev[activeSize], [anchorKey]: next },
    }))
  }

  const getMissing = (): string[] => {
    const missing: string[] = []
    for (const s of SIZES) {
      const anchors = []
      if (placements[s].anchor_a.length < TILE_COUNT[s]) anchors.push('Anchor A')
      if (placements[s].anchor_b.length < TILE_COUNT[s]) anchors.push('Anchor B')
      if (anchors.length > 0) missing.push(`${s} (${anchors.join(', ')})`)
    }
    return missing
  }

  const handleSubmit = () => {
    const missing = getMissing()
    if (missing.length > 0) {
      setSubmitError(`Missing: ${missing.join(' · ')}`)
      return
    }
    setSubmitError(null)

    const pairTheta: Record<Size, number> = {
      '1x1': pctToTheta(pair1Pct), '1x2': pctToTheta(pair1Pct),
      '1x3': pctToTheta(pair2Pct), '2x2': pctToTheta(pair2Pct),
    }
    const targets = SIZES.map(s => ({
      size: s,
      anchor_a: placements[s].anchor_a,
      anchor_b: placements[s].anchor_b,
      theta: pairTheta[s],
    }))
    const colors: Record<string, string> = {}
    for (const s of SIZES) {
      for (const [r, c] of placements[s].anchor_a) colors[cellKey(r, c)] = TARGET_COLOURS[s].a
      for (const [r, c] of placements[s].anchor_b) colors[cellKey(r, c)] = TARGET_COLOURS[s].b
    }
    onConfirm(colors)
    socket.emit('place_targets', { targets })
    setSubmitted(true)
  }

  const cellColors: Record<string, string> = {}
  for (const s of SIZES) {
    for (const [r, c] of placements[s].anchor_a) cellColors[cellKey(r, c)] = TARGET_COLOURS[s].a
    for (const [r, c] of placements[s].anchor_b) cellColors[cellKey(r, c)] = TARGET_COLOURS[s].b
  }

  return (
    <div className="screen" style={{ gap: 16 }}>
      <h2>Place your targets</h2>

      <div style={{ display: 'flex', gap: 8 }}>
        {SIZES.map(s => (
          <button
            key={s}
            className={activeSize === s ? 'active' : ''}
            onClick={() => selectSize(s)}
            disabled={submitted}
          >
            {s}
            <span style={{ fontSize: 13, display: 'block', color: '#888' }}>
              A: {placements[s].anchor_a.length}/{TILE_COUNT[s]} B: {placements[s].anchor_b.length}/{TILE_COUNT[s]}
            </span>
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <button className={activeAnchor === 'A' ? 'active' : ''} onClick={() => setActiveAnchor('A')} disabled={submitted}>Anchor A</button>
        <button className={activeAnchor === 'B' ? 'active' : ''} onClick={() => setActiveAnchor('B')} disabled={submitted}>Anchor B</button>
      </div>

      {warning && (
        <div style={{ color: '#f90', fontSize: 15 }}>{warning}</div>
      )}

      <Board
        cellColors={cellColors}
        onCellClick={handleCellClick}
        disabled={submitted}
      />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 400 }}>
        <span style={{ fontSize: 14, color: '#888' }}>
          Set the probability that each entangled pair collapses to Anchor A when first measured.
        </span>

        {PAIRS.map(([a, b], i) => {
          const pct = i === 0 ? pair1Pct : pair2Pct
          const setPct = i === 0 ? setPair1Pct : setPair2Pct
          return (
            <label key={i} style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 15 }}>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                <span style={{ minWidth: 60 }}>A: <strong>{pct}%</strong></span>
                <span style={{ flex: 1, textAlign: 'center', color: '#aaa' }}>{a} and {b}</span>
                <span style={{ minWidth: 60, textAlign: 'right', color: '#888' }}>B: {100 - pct}%</span>
              </div>
              <input
                type="range" min={0} max={100} step={1}
                value={pct}
                disabled={submitted}
                onChange={e => setPct(parseInt(e.target.value))}
              />
            </label>
          )
        })}
      </div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <button onClick={handleSubmit} disabled={submitted}>
          {submitted ? 'Waiting for opponent...' : 'Confirm Placement'}
        </button>
        <button onClick={() => { setPlacements(initPlacements()); setActiveAnchor('A'); setWarning(null); setSubmitError(null) }} disabled={submitted}>
          Reset
        </button>
        {/*<button onClick={() => { setPlacements(DEBUG_PLACEMENTS); setWarning(null); setSubmitError(null) }} disabled={submitted}>
          Fill All (debug)
        </button>*/}
      </div>

      {submitError && (
        <div style={{ color: '#f55', fontSize: 15 }}>{submitError}</div>
      )}
    </div>
  )
}