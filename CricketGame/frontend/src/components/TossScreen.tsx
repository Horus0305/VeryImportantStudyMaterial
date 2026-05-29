import HeadToHead from '@/components/HeadToHead'
import { useState } from 'react'

const DF = { fontFamily: "'Anton', 'Bebas Neue', sans-serif" }

interface Props {
    screen: string
    tossData: Record<string, unknown>
    username: string
    sendMsg: (msg: Record<string, unknown>) => void
    isHost: boolean
    lobbyPlayers?: string[]
}

export default function TossScreen({ screen, tossData, username, sendMsg, isHost, lobbyPlayers }: Props) {
    const caller      = tossData.caller as string | undefined
    const winner      = tossData.winner as string | undefined
    const coin        = tossData.coin as string | undefined
    const choice      = tossData.choice as string | undefined
    const battingFirst  = tossData.batting_first as string[] | undefined
    const bowlingFirst  = tossData.bowling_first as string[] | undefined
    const sideA       = tossData.side_a as string[] | undefined
    const sideB       = tossData.side_b as string[] | undefined

    const [coinFlipping, setCoinFlipping] = useState(false)

    const handleTossCall = (call: string) => {
        setCoinFlipping(true)
        sendMsg({ action: 'TOSS_CALL', call })
    }

    const lobby1      = lobbyPlayers?.[0]
    const lobby2      = lobbyPlayers?.find(p => p !== lobby1) || lobbyPlayers?.[1]
    const matchLabel1 = sideA?.join(', ') || lobby1 || caller || username
    const matchLabel2 = sideB?.join(', ') || lobby2 || (caller && caller !== username ? caller : '')

    return (
        <div className="w-full h-full flex flex-col relative overflow-hidden">
            {/* Decorative blurs */}
            <div className="absolute top-[-20%] right-[-15%] w-96 h-96 bg-emerald-500/6 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute bottom-[-15%] left-[-10%] w-80 h-80 bg-amber-500/6 rounded-full blur-3xl pointer-events-none" />

            {/* Cancel (host only) */}
            {isHost && (
                <div className="absolute top-3 right-3 sm:top-4 sm:right-4 z-20">
                    <button
                        onClick={() => { if (confirm('Cancel this match? It will be a Tie.')) sendMsg({ action: 'CANCEL_MATCH' }) }}
                        className="h-7 text-[11px] px-3 bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20 rounded-lg font-bold uppercase tracking-wider transition-all"
                    >
                        Cancel
                    </button>
                </div>
            )}

            {/* VS Banner */}
            <div className="relative z-10 pt-6 pb-4 text-center">
                <div className="inline-flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-3 py-1 mb-3 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    Match
                </div>
                <div className="flex items-center justify-center gap-2 sm:gap-4 px-6">
                    <span className="text-2xl sm:text-4xl text-white uppercase leading-none truncate max-w-[38%]" style={DF}>
                        {matchLabel1}
                    </span>
                    <span className="text-sm font-bold text-white px-3 py-1 bg-emerald-600 rounded-lg shrink-0 shadow-lg shadow-emerald-500/20" style={DF}>
                        VS
                    </span>
                    <span className="text-2xl sm:text-4xl text-white uppercase leading-none truncate max-w-[38%]" style={DF}>
                        {matchLabel2}
                    </span>
                </div>
            </div>

            {/* Main card */}
            <div className="relative z-10 flex-1 flex items-center justify-center px-4 pb-6">
                <div className="w-full max-w-md bg-slate-900 border border-white/10 rounded-2xl p-6 sm:p-8 shadow-2xl">

                    {/* ── TOSS CALL ── */}
                    {screen === 'toss' && (
                        <div className="space-y-6 text-center">
                            <div className={`w-20 h-20 sm:w-24 sm:h-24 mx-auto rounded-full bg-linear-to-br from-amber-400 via-yellow-500 to-orange-500 shadow-xl shadow-amber-500/25 flex items-center justify-center ${coinFlipping ? 'animate-spin' : 'animate-bounce'}`}>
                                <span className="text-3xl sm:text-4xl">🪙</span>
                            </div>

                            <div>
                                <h2 className="text-4xl sm:text-5xl text-white uppercase tracking-wide" style={DF}>
                                    Toss Time
                                </h2>
                            </div>

                            {caller === username ? (
                                <>
                                    <p className="text-slate-400 text-xs sm:text-sm font-medium uppercase tracking-wider">
                                        <span className="text-emerald-400 font-bold">{username}</span>, you call it!
                                    </p>
                                    <div className="flex gap-3 justify-center pt-1">
                                        <button
                                            onClick={() => handleTossCall('heads')}
                                            className="group flex-1 py-5 bg-linear-to-br from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-white rounded-xl shadow-lg shadow-amber-500/20 hover:shadow-amber-400/30 transition-all duration-300 hover:scale-105 active:scale-95"
                                        >
                                            <span className="text-2xl block mb-1.5">👑</span>
                                            <span className="text-sm font-bold uppercase tracking-widest" style={DF}>Heads</span>
                                        </button>
                                        <button
                                            onClick={() => handleTossCall('tails')}
                                            className="group flex-1 py-5 bg-linear-to-br from-blue-500 to-cyan-600 hover:from-blue-400 hover:to-cyan-500 text-white rounded-xl shadow-lg shadow-blue-500/20 hover:shadow-blue-400/30 transition-all duration-300 hover:scale-105 active:scale-95"
                                        >
                                            <span className="text-2xl block mb-1.5">🦅</span>
                                            <span className="text-sm font-bold uppercase tracking-widest" style={DF}>Tails</span>
                                        </button>
                                    </div>
                                </>
                            ) : (
                                <div className="space-y-3 py-2">
                                    <p className="text-slate-400 text-sm font-medium">
                                        Waiting for <span className="text-amber-400 font-bold">{caller}</span> to call…
                                    </p>
                                    <div className="flex justify-center gap-1.5">
                                        {[0, 150, 300].map(d => (
                                            <span key={d} className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: `${d}ms` }} />
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* ── TOSS RESULT ── */}
                    {screen === 'toss_result' && (
                        <div className="space-y-6 text-center">
                            <div className="w-20 h-20 sm:w-24 sm:h-24 mx-auto rounded-full bg-linear-to-br from-amber-400 via-yellow-500 to-orange-500 shadow-xl shadow-amber-500/25 flex items-center justify-center animate-flash">
                                <span className="text-4xl">{coin === 'heads' ? '👑' : '🦅'}</span>
                            </div>
                            <div>
                                <div className="text-xs font-bold uppercase tracking-[0.25em] text-slate-500 mb-2">
                                    It's {coin?.toUpperCase()}!
                                </div>
                                <h2 className="text-4xl sm:text-5xl text-amber-400 uppercase leading-none" style={DF}>
                                    {winner}
                                </h2>
                                <p className="text-xl text-emerald-400 font-bold uppercase tracking-wider mt-2" style={DF}>
                                    Won the Toss!
                                </p>
                            </div>
                        </div>
                    )}

                    {/* ── TOSS CHOOSE ── */}
                    {screen === 'toss_choose' && (
                        <div className="space-y-6 text-center">
                            <div className="w-20 h-20 sm:w-24 sm:h-24 mx-auto rounded-full bg-linear-to-br from-amber-400 to-amber-600 shadow-xl shadow-amber-500/25 flex items-center justify-center">
                                <span className="text-4xl">🏆</span>
                            </div>
                            <div>
                                <h2 className="text-4xl sm:text-5xl text-amber-400 uppercase leading-none" style={DF}>
                                    You Won!
                                </h2>
                                <p className="text-slate-400 text-xs sm:text-sm font-medium uppercase tracking-wider mt-2">
                                    Choose wisely, captain
                                </p>
                            </div>
                            <div className="flex gap-3">
                                <button
                                    onClick={() => sendMsg({ action: 'TOSS_CHOICE', choice: 'bat' })}
                                    className="flex-1 py-6 bg-linear-to-br from-emerald-500 to-emerald-700 hover:from-emerald-400 hover:to-emerald-600 text-white rounded-xl shadow-lg shadow-emerald-500/20 hover:shadow-emerald-400/30 transition-all duration-300 hover:scale-105 active:scale-95"
                                >
                                    <span className="text-2xl block mb-1.5">🏏</span>
                                    <span className="text-sm font-bold uppercase tracking-widest" style={DF}>Bat First</span>
                                </button>
                                <button
                                    onClick={() => sendMsg({ action: 'TOSS_CHOICE', choice: 'bowl' })}
                                    className="flex-1 py-6 bg-linear-to-br from-violet-500 to-violet-700 hover:from-violet-400 hover:to-violet-600 text-white rounded-xl shadow-lg shadow-violet-500/20 hover:shadow-violet-400/30 transition-all duration-300 hover:scale-105 active:scale-95"
                                >
                                    <span className="text-2xl block mb-1.5">🎯</span>
                                    <span className="text-sm font-bold uppercase tracking-widest" style={DF}>Bowl First</span>
                                </button>
                            </div>
                        </div>
                    )}

                    {/* ── TOSS DECISION ── */}
                    {screen === 'toss_decision' && (
                        <div className="space-y-5 text-center">
                            <div>
                                <div className="text-xs font-bold uppercase tracking-[0.25em] text-slate-500 mb-2">Toss Result</div>
                                <h2 className="text-4xl sm:text-5xl text-amber-400 uppercase leading-none" style={DF}>
                                    {winner}
                                </h2>
                                <p className="text-slate-300 text-base mt-2">
                                    chose to{' '}
                                    <span className="font-bold text-emerald-400 uppercase" style={DF}>{choice}</span>
                                    {' '}first
                                </p>
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                                <div className="bg-emerald-500/10 border border-emerald-500/25 rounded-xl p-4">
                                    <div className="text-[10px] font-bold uppercase tracking-widest text-emerald-400 mb-2">
                                        🏏 Batting
                                    </div>
                                    <div className="text-white font-bold text-sm" style={DF}>
                                        {battingFirst?.join(', ')}
                                    </div>
                                </div>
                                <div className="bg-violet-500/10 border border-violet-500/25 rounded-xl p-4">
                                    <div className="text-[10px] font-bold uppercase tracking-widest text-violet-400 mb-2">
                                        🎯 Bowling
                                    </div>
                                    <div className="text-white font-bold text-sm" style={DF}>
                                        {bowlingFirst?.join(', ')}
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-center justify-center gap-2 pt-1">
                                <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                                <span className="text-xs font-bold uppercase tracking-widest text-emerald-400">
                                    Match Starting…
                                </span>
                            </div>

                            {(() => {
                                const p1 = battingFirst?.find(p => !p.startsWith('CPU'))
                                const p2 = bowlingFirst?.find(p => !p.startsWith('CPU'))
                                return p1 && p2 ? (
                                    <div className="mt-2">
                                        <HeadToHead player1={p1} player2={p2} defaultOpen={true} />
                                    </div>
                                ) : null
                            })()}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
