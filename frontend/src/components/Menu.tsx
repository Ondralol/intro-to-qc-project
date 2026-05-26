import { useState } from 'react'
import './Menu.css'

interface Props {
  onPlay: () => void
}

export default function Menu({ onPlay }: Props) {
  const [showHelp, setShowHelp] = useState(false)

  return (
    <div className="menu-root">
      <div className="menu-hero">
        <div className="menu-title-block">
          <h1 className="menu-title">Entangled Targets</h1>
          <p className="menu-subtitle">
            A quantum battleship game - place your targets in superposition, entangle them, and outsmart your opponent.
          </p>
        </div>

        <div className="menu-buttons">
          <button className="btn-primary" onClick={onPlay}>Play</button>
          <button
            className={`btn-secondary${showHelp ? ' active' : ''}`}
            onClick={() => setShowHelp(h => !h)}
          >
            {showHelp ? 'Close Help' : 'How to Play'}
          </button>
        </div>
      </div>

      {showHelp && (
        <div className="help-panel">
          <h2 className="help-title">How to Play</h2>

          <div className="help-steps">
            <div className="help-step">
              <span className="step-num">1</span>
              <div>
                <strong>Place your targets</strong>
                <p>You have a 7×7 grid and 4 targets of different sizes. Each target has two possible anchor positions (A and B), place both to define where the target could be. Targets start in quantum superposition between Anchor A and Anchor B. You can shift the probability of the targets collapsing to either of the anchors.</p>
              </div>
            </div>

            <div className="help-step">
              <span className="step-num">2</span>
              <div>
                <strong>Take turns firing shots</strong>
                <p>Click any cell on the opponent's grid to fire. If you hit an anchor belonging to a target in superposition, the quantum state collapses and you find out whether the target was really there. Targets are entangled in pairs, so collapsing one also reveals information about its partner.</p>
              </div>
            </div>

            <div className="help-step">
              <span className="step-num">3</span>
              <div>
                <strong>Interpreting shot results</strong>
                <p>Gray `X` means that you missed. White `X` means that you hit a part of the target. Red `X` means that you destroyed the whole target. Yellow dots reveal positions where the target is 100% NOT (they represent the anchor that the targets didn't collapse into).</p>
              </div>
            </div>

            <div className="help-step">
              <span className="step-num">4</span>
              <div>
                <strong>Unlock the Radar ability</strong>
                <p>Solve a short quantum circuit puzzle to unlock a radar that scans a 2x2 or 3x3 area.</p>
              </div>
            </div>

            <div className="help-step">
              <span className="step-num">5</span>
              <div>
                <strong>Win the game</strong>
                <p>Destroy all of your opponent's targets before they destroy yours.</p>
              </div>
            </div>
          </div>
        </div>
      )}

      <footer className="menu-footer">
        <a
          href="https://github.com/Ondralol/intro-to-qc-project"
          target="_blank"
          rel="noopener noreferrer"
          className="footer-link"
        >
          <svg className="footer-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0 1 12 6.844a9.59 9.59 0 0 1 2.504.337c1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.02 10.02 0 0 0 22 12.017C22 6.484 17.522 2 12 2z"/>
          </svg>
          Source Code
        </a>
      </footer>
    </div>
  )
}
