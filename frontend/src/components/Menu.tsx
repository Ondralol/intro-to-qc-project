import { useState } from 'react'

interface Props {
  onPlay: () => void
}

export default function Menu({ onPlay }: Props) {
  const [showHelp, setShowHelp] = useState(false)

  return (
    <div className="screen">
      <h1>Entangled Targets</h1>
      <div style={{ display: 'flex', gap: 8 }}>
        <button onClick={onPlay}>Play</button>
        <button onClick={() => setShowHelp(h => !h)}>Help</button>
      </div>
      {showHelp && (
        <div style={{ maxWidth: 420, textAlign: 'center', lineHeight: 1.6, color: '#aaa' }}>
          <p>
            TODO - how to paly the game
          </p>
        </div>
      )}
    </div>
  )
}
