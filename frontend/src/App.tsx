import { useEffect, useRef, useState } from 'react'
import { socket } from './socket'
import Menu from './components/Menu'
import Waiting from './components/Waiting'
import Placement from './components/Placement'
import Game from './components/Game'
import './App.css'
import Board from './components/Board'

type Screen = 'menu' | 'waiting' | 'placement' | 'battle_ready' | 'game' | 'debug'

function App() {
  const [screen, setScreen] = useState<Screen>('menu')
  const screenRef = useRef(screen)
  useEffect(() => { screenRef.current = screen }, [screen])
  const [myId, setMyId] = useState('')
  const [firstTurn, setFirstTurn] = useState('')
  const [error, setError] = useState('')
  const [disconnected, setDisconnected] = useState(false)
  const [myTargetColors, setMyTargetColors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (socket.connected) setMyId(socket.id ?? '')
    socket.on('connect', () => setMyId(socket.id ?? ''))

    socket.on('waiting_for_opponent', () => setScreen('waiting'))
    socket.on('placement_start', () => setScreen('placement'))
    socket.on('game_start', (data: { current_turn: string }) => {
      setFirstTurn(data.current_turn)
      setScreen('game')
    })
    socket.on('opponent_disconnected', () => {
      if (screenRef.current !== 'game') {
        setScreen('menu')
        setDisconnected(true)
      }
    })
    socket.on('error', (data: { message: string }) => setError(data.message))

    return () => {
      socket.off('connect')
      socket.off('waiting_for_opponent')
      socket.off('placement_start')
      socket.off('battle_start')
      socket.off('opponent_disconnected')
      socket.off('error')
    }
  }, [])

  return (
    <>
      {error && (
        <div style={{ position: 'fixed', top: 16, left: '50%', transform: 'translateX(-50%)', background: '#c00', padding: '8px 16px', borderRadius: 4, zIndex: 999 }}>
          {error} <button onClick={() => setError('')} style={{ marginLeft: 8 }}>×</button>
        </div>
      )}
      {disconnected && (
        <div style={{
          position: 'fixed', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(0, 0, 0, 0.75)',
          zIndex: 10,
        }}>
          <div style={{
            background: '#15182a',
            border: '1px solid #2a2e42',
            borderRadius: 12,
            padding: '48px 64px',
            textAlign: 'center',
          }}>
            <h1 style={{ fontSize: '2rem', margin: '0 0 12px', color: '#f55' }}>
              Opponent Disconnected
            </h1>
            <p style={{ color: '#888', margin: '0 0 24px' }}>
              They left before the game could start.
            </p>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
              <button
                onClick={() => { setDisconnected(false); socket.emit('find_match') }}
                style={{
                  padding: '12px 32px', fontSize: '1rem', fontWeight: 600,
                  background: '#3b7cff', border: 'none', borderRadius: 8,
                  color: '#fff', cursor: 'pointer',
                }}
              >
                Find Match
              </button>
              <button
                onClick={() => setDisconnected(false)}
                style={{
                  padding: '12px 24px', fontSize: '1rem',
                  background: 'transparent', border: '1px solid #3a3a4a',
                  borderRadius: 8, color: '#bbb', cursor: 'pointer',
                }}
              >
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}

      {screen === 'menu' && <Menu onPlay={() => socket.emit('find_match')} />}
      {screen === 'waiting' && <Waiting />}
      {screen === 'placement' && <Placement onConfirm={colors => setMyTargetColors(colors)} />}

      {screen === 'game' && (
        <Game
          myId={myId}
          firstTurn={firstTurn}
          myTargetColors={myTargetColors}
          onPlayAgain={() => {
            setMyTargetColors({})
            socket.emit('find_match')
          }}
          onReturnToMenu={() => setScreen('menu')}
        />
      )}
      {screen === 'debug' && (                                                                                                                       
    <Board                                                                                                                                       
      cellColors={{ 'A1': '#3a7af8ff', 'A2': '#0055ffff', 'A7': '#34ff0bff' }}
      hitCells={new Set(['B4'])}                                                                                                                 
      destroyedCells={new Set(['B2'])}
      missCells={new Set(['C3'])}                                                                                                                
      pingCells={new Set(['D4'])}
      selectedCell="E5"                                                                                                                          
      radarArea={new Set(['F1', 'F2', 'G1', 'G2'])}                                                                                              
      probabilityMap={{ 'F1': 0.8, 'F2': 0.3, 'G1': 0.6, 'G2': 0.1 }}                                                                            
      onCellClick={(r, c) => console.log(r, c)}                                                                                                  
    />                                                                                                                                           
  )}    
    </>
  )
}

export default App
