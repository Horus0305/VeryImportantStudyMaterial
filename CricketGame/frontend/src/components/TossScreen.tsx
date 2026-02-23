/**
 * TossScreen — Premium coin toss experience.
 *
 * Redesigned to match the editorial sports design language:
 * - Dark hero header showing match participants (side_a vs side_b)
 * - Animated coin with heads/tails
 * - Glassmorphism decision cards
 * - Bebas Neue display font for headings
 */
import { Button } from '@/components/ui/button'
import HeadToHead from '@/components/HeadToHead'
import { useState } from 'react'

const DISPLAY_FONT = { fontFamily: "'Anton', 'Bebas Neue', sans-serif" }

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
    const sideA = tossData.side_a as string[] | undefined
    const sideB = tossData.side_b as string[] | undefined

    const [coinFlipping, setCoinFlipping] = useState(false)

    const handleTossCall = (call: string) => {
        setCoinFlipping(true)
        sendMsg({ action: 'TOSS_CALL', call })
    }

    const matchLabel1 = sideA?.join(', ') || 'Team A'
    const matchLabel2 = sideB?.join(', ') || 'Team B'

    return (
        <div className="w-full h-full flex flex-col items-center justify-center relative overflow-hidden">
            {/* Background gradient */}
            <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-emerald-900" />
            <div className="absolute top-0 right-0 w-1/2 h-1/2 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute bottom-0 left-0 w-1/3 h-1/3 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

            {/* Cancel button (host only) */}
            {isHost && (
                <div className="absolute top-4 right-4 z-20">
                    <Button
                        variant="destructive"
                        size="sm"
                        className="h-7 text-[11px] px-3 bg-red-600/80 hover:bg-red-600"
                        onClick={() => {
                            if (confirm('Cancel this match? It will be a Tie.')) sendMsg({ action: 'CANCEL_MATCH' })
                        }}
                    >
                        Cancel
                    </Button>
                </div>
            )}

            {/* Match Header */}
            <div className="relative z-10 text-center mb-6 sm:mb-8">
                <div className="text-[10px] sm:text-xs font-bold uppercase tracking-[0.3em] text-emerald-400 mb-2">
                    ⚡ Match
                </div>
                <div className="flex items-center justify-center gap-3 sm:gap-4">
                    <span className="text-2xl sm:text-4xl lg:text-5xl text-white uppercase leading-none" style={DISPLAY_FONT}>
                        {matchLabel1}
                    </span>
                    <span className="text-lg sm:text-2xl text-emerald-500 font-bold px-2 sm:px-3 py-1 bg-emerald-500/10 rounded" style={DISPLAY_FONT}>
                        VS
                    </span>
                    <span className="text-2xl sm:text-4xl lg:text-5xl text-white uppercase leading-none" style={DISPLAY_FONT}>
                        {matchLabel2}
                    </span>
                </div>
            </div>

            {/* Main Toss Card */}
            <div className="relative z-10 w-full max-w-md mx-4">
                <div className="bg-white/10 backdrop-blur-xl rounded-2xl border border-white/20 p-6 sm:p-8 shadow-2xl">

                    {/* ─── Toss Call Screen ─── */}
                    {screen === 'toss' && (
                        <div className="space-y-6 text-center">
                            {/* Coin */}
                            <div className={`w-24 h-24 mx-auto rounded-full bg-gradient-to-br from-amber-400 via-yellow-500 to-orange-500 shadow-xl shadow-amber-500/30 flex items-center justify-center ${coinFlipping ? 'animate-spin' : 'animate-bounce'}`}>
                                <span className="text-4xl">🪙</span>
                            </div>

                            <h2 className="text-3xl sm:text-4xl text-white uppercase tracking-wide" style={DISPLAY_FONT}>
                                Toss Time
                            </h2>

                            {caller === username ? (
                                <>
                                    <p className="text-slate-300 text-sm font-medium uppercase tracking-wider">
                                        <span className="text-emerald-400 font-bold">{username}</span>, you call it!
                                    </p>
                                    <div className="flex gap-3 justify-center pt-2">
                                        <button
                                            className="group relative px-8 sm:px-10 py-4 sm:py-5 bg-gradient-to-br from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-white rounded-xl shadow-lg shadow-amber-500/30 hover:shadow-amber-400/40 transition-all duration-300 hover:scale-105 active:scale-95"
                                            onClick={() => handleTossCall('heads')}
                                        >
                                            <span className="text-2xl block mb-1">👑</span>
                                            <span className="text-sm font-bold uppercase tracking-widest" style={DISPLAY_FONT}>Heads</span>
                                        </button>
                                        <button
                                            className="group relative px-8 sm:px-10 py-4 sm:py-5 bg-gradient-to-br from-blue-500 to-cyan-600 hover:from-blue-400 hover:to-cyan-500 text-white rounded-xl shadow-lg shadow-blue-500/30 hover:shadow-blue-400/40 transition-all duration-300 hover:scale-105 active:scale-95"
                                            onClick={() => handleTossCall('tails')}
                                        >
                                            <span className="text-2xl block mb-1">🦅</span>
                                            <span className="text-sm font-bold uppercase tracking-widest" style={DISPLAY_FONT}>Tails</span>
                                        </button>
                                    </div>
                                </>
                            ) : (
                                <div className="space-y-3">
                                    <p className="text-slate-300 text-sm font-medium">
                                        Waiting for <span className="text-amber-400 font-bold">{caller}</span> to call...
                                    </p>
                                    <div className="flex justify-center gap-1">
                                        <span className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                                        <span className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                                        <span className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* ─── Toss Result ─── */}
                    {screen === 'toss_result' && (
                        <div className="space-y-6 text-center">
                            <div className="w-24 h-24 mx-auto rounded-full bg-gradient-to-br from-amber-400 via-yellow-500 to-orange-500 shadow-xl shadow-amber-500/30 flex items-center justify-center">
                                <span className="text-3xl font-bold text-white" style={DISPLAY_FONT}>
                                    {coin === 'heads' ? '👑' : '🦅'}
                                </span>
                            </div>

                            <div>
                                <div className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400 mb-2">
                                    It's {coin?.toUpperCase()}!
                                </div>
                                <h2 className="text-3xl sm:text-4xl text-white uppercase" style={DISPLAY_FONT}>
                                    <span className="text-amber-400">{winner}</span>
                                </h2>
                                <p className="text-lg text-emerald-400 font-bold uppercase tracking-wider mt-1" style={DISPLAY_FONT}>
                                    Won the Toss!
                                </p>
                            </div>
                        </div>
                    )}

                    {/* ─── Toss Choose ─── */}
                    {screen === 'toss_choose' && (
                        <div className="space-y-6 text-center">
                            <div className="w-20 h-20 mx-auto rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 shadow-xl shadow-emerald-500/30 flex items-center justify-center">
                                <span className="text-3xl">🏆</span>
                            </div>

                            <div>
                                <h2 className="text-3xl sm:text-4xl text-amber-400 uppercase" style={DISPLAY_FONT}>
                                    You Won!
                                </h2>
                                <p className="text-slate-300 text-sm font-medium uppercase tracking-wider mt-2">
                                    Choose wisely, captain
                                </p>
                            </div>

                            <div className="flex gap-3 justify-center">
                                <button
                                    className="relative group flex-1 py-5 sm:py-6 bg-gradient-to-br from-emerald-500 to-green-600 hover:from-emerald-400 hover:to-green-500 text-white rounded-xl shadow-lg shadow-emerald-500/30 hover:shadow-emerald-400/40 transition-all duration-300 hover:scale-105 active:scale-95 overflow-hidden"
                                    onClick={() => sendMsg({ action: 'TOSS_CHOICE', choice: 'bat' })}
                                >
                                    <div className="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity" />
                                    <span className="text-2xl block mb-1">🏏</span>
                                    <span className="text-sm font-bold uppercase tracking-widest" style={DISPLAY_FONT}>Bat First</span>
                                </button>
                                <button
                                    className="relative group flex-1 py-5 sm:py-6 bg-gradient-to-br from-purple-500 to-violet-600 hover:from-purple-400 hover:to-violet-500 text-white rounded-xl shadow-lg shadow-purple-500/30 hover:shadow-purple-400/40 transition-all duration-300 hover:scale-105 active:scale-95 overflow-hidden"
                                    onClick={() => sendMsg({ action: 'TOSS_CHOICE', choice: 'bowl' })}
                                >
                                    <div className="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity" />
                                    <span className="text-2xl block mb-1">🎯</span>
                                    <span className="text-sm font-bold uppercase tracking-widest" style={DISPLAY_FONT}>Bowl First</span>
                                </button>
                            </div>
                        </div>
                    )}

                    {/* ─── Toss Decision ─── */}
                    {screen === 'toss_decision' && (
                        <div className="space-y-5 text-center">
                            <div>
                                <div className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400 mb-2">
                                    Toss Result
                                </div>
                                <h2 className="text-3xl sm:text-4xl text-white uppercase" style={DISPLAY_FONT}>
                                    <span className="text-amber-400">{winner}</span> won
                                </h2>
                                <p className="text-lg text-slate-300 mt-1">
                                    chose to <span className="font-bold text-emerald-400 uppercase" style={DISPLAY_FONT}>{choice?.toUpperCase()}</span> first
                                </p>
                            </div>

                            {/* Teams assignment */}
                            <div className="grid grid-cols-2 gap-3 text-sm">
                                <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4">
                                    <div className="text-[10px] font-bold uppercase tracking-widest text-emerald-500 mb-2">
                                        🏏 Batting
                                    </div>
                                    <div className="text-white font-bold text-base" style={DISPLAY_FONT}>
                                        {battingFirst?.join(', ')}
                                    </div>
                                </div>
                                <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-4">
                                    <div className="text-[10px] font-bold uppercase tracking-widest text-purple-400 mb-2">
                                        🎯 Bowling
                                    </div>
                                    <div className="text-white font-bold text-base" style={DISPLAY_FONT}>
                                        {bowlingFirst?.join(', ')}
                                    </div>
                                </div>
                            </div>

                            {/* Match starting indicator */}
                            <div className="flex items-center justify-center gap-2 pt-2">
                                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                                <span className="text-xs font-bold uppercase tracking-widest text-emerald-400">
                                    Match Starting...
                                </span>
                            </div>

                            {/* Pre-match H2H */}
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
