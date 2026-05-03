import { useEffect, useState } from 'react'
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
  const [myId, setMyId] = useState('')
  const [firstTurn, setFirstTurn] = useState('')
  const [error, setError] = useState('')
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
      {screen === 'placement' && <Placement onConfirm={colors => setMyTargetColors(colors)} />}

      {screen === 'game' && <Game myId={myId} firstTurn={firstTurn} myTargetColors={myTargetColors} />}
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
