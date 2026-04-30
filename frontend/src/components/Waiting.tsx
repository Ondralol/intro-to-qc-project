import './Waiting.css'

export default function Waiting() {
  return (
    <div className="waiting-root">
      <div className="waiting-card">
        <div className="waiting-orb" aria-hidden="true">
          <span className="orb-inner" />
        </div>

        <h2 className="waiting-title">Searching for opponent</h2>
        <p className="waiting-sub">
          Share the link with a friend to start the game.
        </p>

        <div className="waiting-dots" aria-label="loading">
          <span /><span /><span />
        </div>

        <div className="waiting-hint">
          While you wait — your targets will be placed in <em>superposition</em> once a match is found.
        </div>
      </div>
    </div>
  )
}
