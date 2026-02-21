/**
 * TossScreen — Handles toss call, result, choice, and decision display.
 * Full-width, centered within the viewport.
 */
import { Button } from '@/components/ui/button'
import HeadToHead from '@/components/HeadToHead'

interface Props {
    screen: string
    tossData: Record<string, unknown>
    username: string
    sendMsg: (msg: Record<string, unknown>) => void
    isHost: boolean
}

export default function TossScreen({ screen, tossData, username, sendMsg, isHost }: Props) {
    const caller = tossData.caller as string | undefined
    const winner = tossData.winner as string | undefined
    const coin = tossData.coin as string | undefined
    const choice = tossData.choice as string | undefined
    const battingFirst = tossData.batting_first as string[] | undefined
    const bowlingFirst = tossData.bowling_first as string[] | undefined

    return (
        <div className="w-full h-full flex items-center justify-center">
            <div className="w-full max-w-lg bg-white/80 backdrop-blur-sm rounded-2xl border border-slate-200 p-8 shadow-xl text-center">
                <div className="space-y-6">
                    {isHost && (
                        <div className="flex justify-end">
                            <Button
                                variant="destructive"
                                size="sm"
                                className="h-7 text-[11px] px-3"
                                onClick={() => {
                                    if (confirm('Cancel this match? It will be a Tie.')) sendMsg({ action: 'CANCEL_MATCH' })
                                }}
                            >
                                Cancel
                            </Button>
                        </div>
                    )}
                    <div className="text-6xl"></div>

                    {screen === 'toss' && (
                        <>
                            <h2 className="text-3xl font-bold text-slate-900">Toss Time!</h2>
                            {caller === username ? (
                                <>
                                    <p className="text-slate-600 text-lg">You call the toss!</p>
                                    <div className="flex gap-4 justify-center pt-2">
                                        <Button
                                            size="lg"
                                            className="px-10 py-6 text-lg bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 text-white shadow-lg"
                                            onClick={() => sendMsg({ action: 'TOSS_CALL', call: 'heads' })}
                                        >
                                            Heads
                                        </Button>
                                        <Button
                                            size="lg"
                                            className="px-10 py-6 text-lg bg-gradient-to-r from-blue-500 to-cyan-600 hover:from-blue-600 hover:to-cyan-700 text-white shadow-lg"
                                            onClick={() => sendMsg({ action: 'TOSS_CALL', call: 'tails' })}
                                        >
                                            Tails
                                        </Button>
                                    </div>
                                </>
                            ) : (
                                <p className="text-slate-600 text-lg">
                                    Waiting for <span className="font-bold text-orange-600">{caller}</span> to call...
                                </p>
                            )}
                        </>
                    )}

                    {screen === 'toss_result' && (
                        <>
                            <h2 className="text-3xl font-bold text-slate-900">
                                Coin: {coin?.toUpperCase()}
                            </h2>
                            <p className="text-xl text-slate-700">
                                <span className="font-bold text-yellow-600">{winner}</span> won the toss!
                            </p>
                        </>
                    )}

                    {screen === 'toss_choose' && (
                        <>
                            <h2 className="text-3xl font-bold text-yellow-600">
                                You won the toss!
                            </h2>
                            <p className="text-slate-600 text-lg">Choose wisely:</p>
                            <div className="flex gap-4 justify-center pt-2">
                                <Button
                                    size="lg"
                                    className="px-10 py-6 text-lg bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white shadow-lg"
                                    onClick={() => sendMsg({ action: 'TOSS_CHOICE', choice: 'bat' })}
                                >
                                    Bat First
                                </Button>
                                <Button
                                    size="lg"
                                    className="px-10 py-6 text-lg bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700 text-white shadow-lg"
                                    onClick={() => sendMsg({ action: 'TOSS_CHOICE', choice: 'bowl' })}
                                >
                                    Bowl First
                                </Button>
                            </div>
                        </>
                    )}

                    {screen === 'toss_decision' && (
                        <>
                            <h2 className="text-3xl font-bold text-slate-900">{winner} won the toss</h2>
                            <p className="text-xl text-slate-700">
                                and chose to <span className="font-bold text-yellow-600">{choice?.toUpperCase()}</span> first
                            </p>
                            <div className="text-sm text-slate-600 space-y-2 pt-4 bg-slate-50 rounded-lg p-4 border border-slate-200">
                                <p className="flex items-center justify-center gap-2">
                                    <span className="text-green-600 font-semibold"> Batting:</span>
                                    <span className="font-bold text-slate-900">{battingFirst?.join(', ')}</span>
                                </p>
                                <p className="flex items-center justify-center gap-2">
                                    <span className="text-purple-600 font-semibold"> Bowling:</span>
                                    <span className="font-bold text-slate-900">{bowlingFirst?.join(', ')}</span>
                                </p>
                            </div>
                            <p className="text-sm text-blue-600 animate-pulse font-medium">
                                Match starting...
                            </p>
                            {/* Pre-match H2H — first non-CPU player from each side */}
                            {(() => {
                                const p1 = battingFirst?.find(p => !p.startsWith('CPU'))
                                const p2 = bowlingFirst?.find(p => !p.startsWith('CPU'))
                                return p1 && p2 ? (
                                    <div className="mt-4">
                                        <HeadToHead player1={p1} player2={p2} defaultOpen={true} />
                                    </div>
                                ) : null
                            })()}
                        </>
                    )}
                </div>
            </div>
        </div>
    )
}
