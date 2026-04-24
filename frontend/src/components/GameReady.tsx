interface Props {
  firstTurn: string
  myId: string
}

export default function GameReady({ firstTurn, myId }: Props) {
  const isMyTurn = firstTurn === myId
  return (
    <div className="screen">
      <h2>Both players ready!</h2>
      <p>{isMyTurn ? 'You go first.' : 'Opponent goes first.'}</p>
    </div>
  )
}
