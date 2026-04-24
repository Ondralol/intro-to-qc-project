import { useEffect, useState } from 'react'
import { socket } from './socket'
import Menu from './components/Menu'
import Waiting from './components/Waiting'
import Placement from './components/Placement'
import GameReady from './components/GameReady'
import './App.css'

type Screen = 'menu' | 'waiting' | 'placement' | 'battle_ready'

function App() {
  const [screen, setScreen] = useState<Screen>('menu')
  const [myId, setMyId] = useState('')
  const [firstTurn, setFirstTurn] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    socket.on('connect', () => setMyId(socket.id ?? ''))

    socket.on('waiting_for_opponent', () => setScreen('waiting'))
    socket.on('placement_start', () => setScreen('placement'))
    socket.on('game_start', (data: { current_turn: string }) => {
      setFirstTurn(data.current_turn)
      setScreen('battle_ready')
    })
    socket.on('opponent_disconnected', () => setScreen('menu'))
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
      {screen === 'menu' && <Menu onPlay={() => socket.emit('find_match')} />}
      {screen === 'waiting' && <Waiting />}
      {screen === 'placement' && <Placement />}
      {screen === 'battle_ready' && <GameReady firstTurn={firstTurn} myId={myId} />}
    </>
  )
}

export default App
