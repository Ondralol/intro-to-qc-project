import './Board.css'

const ROW_LABELS = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
const COL_LABELS = ['1', '2', '3', '4', '5', '6', '7']
const GRID = 7

export function cellKey(row: number, col: number): string {
  return `${ROW_LABELS[row]}${col + 1}`
}

export interface BoardProps {
  cellColors?: Record<string, string>
  hitCells?: Set<string>
  destroyedCells?: Set<string>
  missCells?: Set<string>
  pingCells?: Set<string>
  selectedCell?: string | null
  radarArea?: Set<string>
  probabilityMap?: Record<string, number>
  onCellClick?: (row: number, col: number) => void
  onCellHover?: (row: number, col: number) => void
  disabled?: boolean
  cellSize?: number
}

export default function Board({
  cellColors = {},
  hitCells = new Set(),
  destroyedCells = new Set(),
  missCells = new Set(),
  pingCells = new Set(),
  selectedCell = null,
  radarArea = new Set(),
  probabilityMap = {},
  onCellClick,
  onCellHover,
  disabled = false,
  cellSize = 54,
}: BoardProps) {
  return (
    <div className="board-wrapper">
    <div style={{ display: 'inline-block', userSelect: 'none' }}>
      <div style={{ display: 'flex', marginLeft: cellSize + 6 }}>
        {COL_LABELS.map(col => (
          <div
            key={col}
            style={{
              width: cellSize,
              textAlign: 'center',
              fontSize: 14,
              color: '#888',
              marginRight: 4,
              lineHeight: `${cellSize}px`,
            }}
          >
            {col}
          </div>
        ))}
      </div>

      {Array.from({ length: GRID }, (_, row) => (
        <div key={ROW_LABELS[row]} style={{ display: 'flex', alignItems: 'center', marginBottom: 4 }}>
          <div
            style={{
              width: cellSize,
              textAlign: 'center',
              fontSize: 14,
              color: '#888',
              marginRight: 6,
              lineHeight: `${cellSize}px`,
            }}
          >
            {ROW_LABELS[row]}
          </div>

          {Array.from({ length: GRID }, (_, col) => {
            const key = cellKey(row, col)
            const isDestroyed = destroyedCells.has(key)
            const isHit = hitCells.has(key)
            const isMiss = missCells.has(key)
            const isSelected = selectedCell === key
            const isInRadar = radarArea.has(key)
            const hasPing = pingCells.has(key)
            const probability = probabilityMap[key]

            return (
              <div
                key={key}
                className={`board-cell${disabled ? ' disabled' : ''}`}
                onClick={() => !disabled && onCellClick?.(row, col)}
                onMouseEnter={() => !disabled && onCellHover?.(row, col)}
                style={{
                  width: cellSize,
                  height: cellSize,
                  background: cellColors[key] ?? '#1e1e1e',
                  border: isSelected
                    ? '2px solid #fff'
                    : isInRadar
                    ? '1px solid #4af'
                    : '1px solid #333',
                  marginRight: 4,
                }}
              >
                {isDestroyed && (
                  <div style={{
                    position: 'absolute', inset: 0,
                    background: 'rgba(160, 30, 30, 0.5)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 22, color: '#ff6666', fontWeight: 'bold',
                  }}>×</div>
                )}

                {!isDestroyed && isHit && (
                  <div style={{
                    position: 'absolute', inset: 0,
                    background: 'rgba(0, 0, 0, 0.35)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 22, color: '#fff', fontWeight: 'bold',
                  }}>×</div>
                )}

                {isMiss && (
                  <div style={{
                    position: 'absolute', inset: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 22, color: '#555', fontWeight: 'bold',
                  }}>×</div>
                )}

                {isInRadar && (
                  <div style={{
                    position: 'absolute', inset: 0,
                    background: 'rgba(68, 170, 255, 0.08)',
                    pointerEvents: 'none',
                  }} />
                )}

                {probability !== undefined && (
                  <div style={{
                    position: 'absolute', inset: 0,
                    background: `rgba(68, 170, 255, ${probability * 0.5})`,
                    pointerEvents: 'none',
                  }} />
                )}

                {hasPing && (
                  <div style={{
                    position: 'absolute', inset: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    pointerEvents: 'none',
                  }}>
                    <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#ffcc00' }} />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      ))}
    </div>
    </div>
  )
}