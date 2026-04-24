import { useState } from 'react'
import { socket } from '../socket'

const GRID = 7
const SIZES = ['1x1', '1x2', '1x3', '2x2'] as const
type Size = typeof SIZES[number]

// How many tiles each anchor of a target occupies
const TILE_COUNT: Record<Size, number> = { '1x1': 1, '1x2': 2, '1x3': 3, '2x2': 4 }

type Coord = [number, number]
type TargetPlacement = { anchor_a: Coord[]; anchor_b: Coord[]; theta: number }
type Placements = Record<Size, TargetPlacement>

const initPlacements = (): Placements =>
  Object.fromEntries(SIZES.map(s => [s, { anchor_a: [], anchor_b: [], theta: Math.PI / 4 }])) as Placements

// Colour per target for visual distinction
const TARGET_COLOURS: Record<Size, { a: string; b: string }> = {
  '1x1': { a: '#1565C0', b: '#0D47A1' },
  '1x2': { a: '#2E7D32', b: '#1B5E20' },
  '1x3': { a: '#E65100', b: '#BF360C' },
  '2x2': { a: '#6A1B9A', b: '#4A148C' },
}

export default function Placement() {
  const [placements, setPlacements] = useState<Placements>(initPlacements)
  const [activeSize, setActiveSize] = useState<Size>('1x2')
  const [activeAnchor, setActiveAnchor] = useState<'A' | 'B'>('A')
  const [submitted, setSubmitted] = useState(false)

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
      // Deselect
      setPlacements(prev => ({
        ...prev,
        [activeSize]: { ...prev[activeSize], [anchorKey]: current.filter(([r, c]) => !(r === row && c === col)) },
      }))
      return
    }

    // Don't allow placing if tile is taken by anything else
    if (getCell(row, col) !== null) return
    if (current.length >= TILE_COUNT[activeSize]) return

    setPlacements(prev => ({
      ...prev,
      [activeSize]: { ...prev[activeSize], [anchorKey]: [...current, [row, col]] },
    }))
  }

  const allPlaced = SIZES.every(s =>
    placements[s].anchor_a.length === TILE_COUNT[s] && placements[s].anchor_b.length === TILE_COUNT[s]
  )

  const handleSubmit = () => {
    const targets = SIZES.map(s => ({
      size: s,
      anchor_a: placements[s].anchor_a,
      anchor_b: placements[s].anchor_b,
      theta: placements[s].theta,
    }))
    socket.emit('place_targets', { targets })
    setSubmitted(true)
  }

  return (
    <div className="screen" style={{ gap: 16 }}>
      <h2>Place your targets</h2>

      {/* Target selector */}
      <div style={{ display: 'flex', gap: 8 }}>
        {SIZES.map(s => (
          <button
            key={s}
            className={activeSize === s ? 'active' : ''}
            onClick={() => setActiveSize(s)}
          >
            {s}
            <span style={{ fontSize: 11, display: 'block', color: '#888' }}>
              A: {placements[s].anchor_a.length}/{TILE_COUNT[s]} B: {placements[s].anchor_b.length}/{TILE_COUNT[s]}
            </span>
          </button>
        ))}
      </div>

      {/* Anchor toggle */}
      <div style={{ display: 'flex', gap: 8 }}>
        <button className={activeAnchor === 'A' ? 'active' : ''} onClick={() => setActiveAnchor('A')}>
          Anchor A
        </button>
        <button className={activeAnchor === 'B' ? 'active' : ''} onClick={() => setActiveAnchor('B')}>
          Anchor B
        </button>
      </div>

      {/* Theta slider */}
      <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
        θ = {placements[activeSize].theta.toFixed(2)} rad
        <input
          type="range" min={0} max={Math.PI} step={0.01}
          value={placements[activeSize].theta}
          onChange={e => setPlacements(prev => ({
            ...prev,
            [activeSize]: { ...prev[activeSize], theta: parseFloat(e.target.value) },
          }))}
        />
      </label>

      {/* Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${GRID}, 40px)`, gap: 2 }}>
        {Array.from({ length: GRID }, (_, row) =>
          Array.from({ length: GRID }, (_, col) => {
            const cell = getCell(row, col)
            let bg = '#1e1e1e'
            if (cell) {
              bg = cell.anchor === 'A' ? TARGET_COLOURS[cell.size].a : TARGET_COLOURS[cell.size].b
            }
            const label = `${String.fromCharCode(65 + row)}${col + 1}`
            return (
              <div
                key={label}
                onClick={() => handleCellClick(row, col)}
                style={{
                  width: 40, height: 40, background: bg,
                  border: '1px solid #333', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 10, color: '#aaa', userSelect: 'none',
                }}
              >
                {label}
              </div>
            )
          })
        )}
      </div>

      <button onClick={handleSubmit} disabled={!allPlaced || submitted}>
        {submitted ? 'Waiting for opponent...' : 'Confirm Placement'}
      </button>
    </div>
  )
}
