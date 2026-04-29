const ROW_LABELS = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
const COL_LABELS = ['1', '2', '3', '4', '5', '6', '7']
const GRID = 7

export function cellKey(row: number, col: number): string {
  return `${ROW_LABELS[row]}${col + 1}`
}

export interface BoardProps {
  /**
   * Map from cell label (e.g. "A1", "C4") to a CSS background colour.
   * Cells without an entry are rendered as empty.
   */
  cellColors?: Record<string, string>
  /**
   * Set of cell labels that should show a ping indicator dot (e.g. for
   * indirect-hit / entanglement reveals).
   */
  pingCells?: Set<string>
  onCellClick?: (row: number, col: number) => void
  disabled?: boolean
  /** Side length in pixels for each cell. Defaults to 40. */
  cellSize?: number
}

export default function Board({
  cellColors = {},
  pingCells = new Set(),
  onCellClick,
  disabled = false,
  cellSize = 40,
}: BoardProps) {
  return (
    <div style={{ display: 'inline-block', userSelect: 'none' }}>
      {/* Column headers */}
      <div style={{ display: 'flex', marginLeft: cellSize + 6 }}>
        {COL_LABELS.map(col => (
          <div
            key={col}
            style={{
              width: cellSize,
              textAlign: 'center',
              fontSize: 11,
              color: '#888',
              marginRight: 2,
              lineHeight: `${cellSize}px`,
            }}
          >
            {col}
          </div>
        ))}
      </div>

      {/* Rows */}
      {Array.from({ length: GRID }, (_, row) => (
        <div key={ROW_LABELS[row]} style={{ display: 'flex', alignItems: 'center', marginBottom: 2 }}>
          {/* Row label */}
          <div
            style={{
              width: cellSize,
              textAlign: 'center',
              fontSize: 11,
              color: '#888',
              marginRight: 6,
              lineHeight: `${cellSize}px`,
            }}
          >
            {ROW_LABELS[row]}
          </div>

          {/* Cells */}
          {Array.from({ length: GRID }, (_, col) => {
            const key = cellKey(row, col)
            const bg = cellColors[key] ?? '#1e1e1e'
            const hasPing = pingCells.has(key)

            return (
              <div
                key={key}
                onClick={() => !disabled && onCellClick?.(row, col)}
                title={key}
                style={{
                  position: 'relative',
                  width: cellSize,
                  height: cellSize,
                  background: bg,
                  border: '1px solid #333',
                  cursor: disabled ? 'default' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 10,
                  color: '#aaa',
                  marginRight: 2,
                  flexShrink: 0,
                }}
              >
                {key}
                {hasPing && (
                  <div
                    style={{
                      position: 'absolute',
                      top: 3,
                      right: 3,
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      background: '#ffcc00',
                      pointerEvents: 'none',
                    }}
                  />
                )}
              </div>
            )
          })}
        </div>
      ))}
    </div>
  )
}
