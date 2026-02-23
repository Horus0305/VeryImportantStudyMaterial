/**
 * TossScreen — Premium light-mode toss experience.
 *
 * Design: Light bg-slate-50, white cards, emerald accents,
 * Bebas Neue display font, fills full available area, mobile-responsive.
 * Shows actual player/captain names — never "Team A" / "Team B".
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
    lobbyPlayers?: string[]
}

export default function TossScreen({ screen, tossData, username, sendMsg, isHost, lobbyPlayers }: Props) {
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

    // Derive real player names — prioritise backend data, fall back to lobby players
    const labelFromSide = (side?: string[]) => side?.join(', ')
    const lobby1 = lobbyPlayers?.[0]
    const lobby2 = lobbyPlayers?.find(p => p !== lobby1) || lobbyPlayers?.[1]
    const matchLabel1 = labelFromSide(sideA) || lobby1 || caller || username
    const matchLabel2 = labelFromSide(sideB) || lobby2 || (caller && caller !== username ? caller : '')

    return (
        <div className="w-full h-full flex flex-col bg-slate-50 relative overflow-hidden">
            {/* Subtle decorative blurs */}
            <div className="absolute top-[-20%] right-[-15%] w-[400px] h-[400px] bg-emerald-200/25 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute bottom-[-15%] left-[-10%] w-[350px] h-[350px] bg-amber-200/20 rounded-full blur-3xl pointer-events-none" />

            {/* Cancel button (host only) */}
            {isHost && (
                <div className="absolute top-3 right-3 sm:top-4 sm:right-4 z-20">
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

            {/* Match Header — Prominent VS Banner */}
            <div className="relative z-10 pt-4 pb-3 sm:pt-6 sm:pb-4 text-center">
                <div className="text-[10px] sm:text-xs font-bold uppercase tracking-[0.3em] text-emerald-600 mb-1.5 sm:mb-2">
                    ⚡ Match
                </div>
                <div className="flex items-center justify-center gap-2 sm:gap-3 px-4">
                    <span className="text-xl sm:text-3xl lg:text-4xl text-slate-900 uppercase leading-none truncate max-w-[40%]" style={DISPLAY_FONT}>
                        {matchLabel1}
                    </span>
                    <span className="text-sm sm:text-lg text-white font-bold px-2 py-0.5 sm:px-3 sm:py-1 bg-emerald-600 rounded shrink-0" style={DISPLAY_FONT}>
                        VS
                    </span>
                    <span className="text-xl sm:text-3xl lg:text-4xl text-slate-900 uppercase leading-none truncate max-w-[40%]" style={DISPLAY_FONT}>
                        {matchLabel2}
                    </span>
                </div>
            </div>

            {/* Main Toss Card — fills remaining space */}
            <div className="relative z-10 flex-1 flex items-center justify-center px-4 pb-6">
                <div className="w-full max-w-md bg-white rounded-2xl border border-slate-200 p-5 sm:p-8 shadow-lg">

                    {/* ─── Toss Call Screen ─── */}
                    {screen === 'toss' && (
                        <div className="space-y-5 sm:space-y-6 text-center">
                            {/* Coin */}
                            <div className={`w-20 h-20 sm:w-24 sm:h-24 mx-auto rounded-full bg-gradient-to-br from-amber-400 via-yellow-500 to-orange-500 shadow-lg shadow-amber-500/20 flex items-center justify-center ${coinFlipping ? 'animate-spin' : 'animate-bounce'}`}>
                                <span className="text-3xl sm:text-4xl">🪙</span>
                            </div>

                            <h2 className="text-3xl sm:text-4xl text-slate-900 uppercase tracking-wide" style={DISPLAY_FONT}>
                                Toss Time
                            </h2>

                            {caller === username ? (
                                <>
                                    <p className="text-slate-500 text-xs sm:text-sm font-medium uppercase tracking-wider">
                                        <span className="text-emerald-700 font-bold">{username}</span>, you call it!
                                    </p>
                                    <div className="flex gap-3 justify-center pt-1">
                                        <button
                                            className="group px-6 sm:px-10 py-4 sm:py-5 bg-gradient-to-br from-amber-500 to-orange-600 hover:from-amber-400 hover:to-orange-500 text-white rounded-xl shadow-md shadow-amber-500/20 hover:shadow-amber-400/30 transition-all duration-300 hover:scale-105 active:scale-95"
                                            onClick={() => handleTossCall('heads')}
                                        >
                                            <span className="text-2xl block mb-1">👑</span>
                                            <span className="text-xs sm:text-sm font-bold uppercase tracking-widest" style={DISPLAY_FONT}>Heads</span>
                                        </button>
                                        <button
                                            className="group px-6 sm:px-10 py-4 sm:py-5 bg-gradient-to-br from-blue-500 to-cyan-600 hover:from-blue-400 hover:to-cyan-500 text-white rounded-xl shadow-md shadow-blue-500/20 hover:shadow-blue-400/30 transition-all duration-300 hover:scale-105 active:scale-95"
                                            onClick={() => handleTossCall('tails')}
                                        >
                                            <span className="text-2xl block mb-1">🦅</span>
                                            <span className="text-xs sm:text-sm font-bold uppercase tracking-widest" style={DISPLAY_FONT}>Tails</span>
                                        </button>
                                    </div>
                                </>
                            ) : (
                                <div className="space-y-3">
                                    <p className="text-slate-500 text-sm font-medium">
                                        Waiting for <span className="text-amber-600 font-bold">{caller}</span> to call...
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
                        <div className="space-y-5 sm:space-y-6 text-center">
                            <div className="w-20 h-20 sm:w-24 sm:h-24 mx-auto rounded-full bg-gradient-to-br from-amber-400 via-yellow-500 to-orange-500 shadow-lg shadow-amber-500/20 flex items-center justify-center">
                                <span className="text-3xl font-bold" style={DISPLAY_FONT}>
                                    {coin === 'heads' ? '👑' : '🦅'}
                                </span>
                            </div>

                            <div>
                                <div className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400 mb-2">
                                    It's {coin?.toUpperCase()}!
                                </div>
                                <h2 className="text-3xl sm:text-4xl text-slate-900 uppercase" style={DISPLAY_FONT}>
                                    <span className="text-amber-600">{winner}</span>
                                </h2>
                                <p className="text-lg text-emerald-600 font-bold uppercase tracking-wider mt-1" style={DISPLAY_FONT}>
                                    Won the Toss!
                                </p>
                            </div>
                        </div>
                    )}

                    {/* ─── Toss Choose ─── */}
                    {screen === 'toss_choose' && (
                        <div className="space-y-5 sm:space-y-6 text-center">
                            <div className="w-18 h-18 sm:w-20 sm:h-20 mx-auto rounded-full bg-gradient-to-br from-emerald-400 to-emerald-600 shadow-lg shadow-emerald-500/20 flex items-center justify-center">
                                <span className="text-3xl">🏆</span>
                            </div>

                            <div>
                                <h2 className="text-3xl sm:text-4xl text-amber-600 uppercase" style={DISPLAY_FONT}>
                                    You Won!
                                </h2>
                                <p className="text-slate-500 text-xs sm:text-sm font-medium uppercase tracking-wider mt-2">
                                    Choose wisely, captain
                                </p>
                            </div>

                            <div className="flex gap-3 justify-center">
                                <button
                                    className="relative group flex-1 py-5 sm:py-6 bg-gradient-to-br from-emerald-500 to-green-600 hover:from-emerald-400 hover:to-green-500 text-white rounded-xl shadow-md shadow-emerald-500/20 hover:shadow-emerald-400/30 transition-all duration-300 hover:scale-105 active:scale-95 overflow-hidden"
                                    onClick={() => sendMsg({ action: 'TOSS_CHOICE', choice: 'bat' })}
                                >
                                    <span className="text-2xl block mb-1">🏏</span>
                                    <span className="text-xs sm:text-sm font-bold uppercase tracking-widest" style={DISPLAY_FONT}>Bat First</span>
                                </button>
                                <button
                                    className="relative group flex-1 py-5 sm:py-6 bg-gradient-to-br from-purple-500 to-violet-600 hover:from-purple-400 hover:to-violet-500 text-white rounded-xl shadow-md shadow-purple-500/20 hover:shadow-purple-400/30 transition-all duration-300 hover:scale-105 active:scale-95 overflow-hidden"
                                    onClick={() => sendMsg({ action: 'TOSS_CHOICE', choice: 'bowl' })}
                                >
                                    <span className="text-2xl block mb-1">🎯</span>
                                    <span className="text-xs sm:text-sm font-bold uppercase tracking-widest" style={DISPLAY_FONT}>Bowl First</span>
                                </button>
                            </div>
                        </div>
                    )}

                    {/* ─── Toss Decision ─── */}
                    {screen === 'toss_decision' && (
                        <div className="space-y-4 sm:space-y-5 text-center">
                            <div>
                                <div className="text-xs font-bold uppercase tracking-[0.2em] text-slate-400 mb-2">
                                    Toss Result
                                </div>
                                <h2 className="text-3xl sm:text-4xl text-slate-900 uppercase" style={DISPLAY_FONT}>
                                    <span className="text-amber-600">{winner}</span> won
                                </h2>
                                <p className="text-base sm:text-lg text-slate-600 mt-1">
                                    chose to <span className="font-bold text-emerald-600 uppercase" style={DISPLAY_FONT}>{choice?.toUpperCase()}</span> first
                                </p>
                            </div>

                            {/* Teams assignment */}
                            <div className="grid grid-cols-2 gap-3 text-sm">
                                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 sm:p-4">
                                    <div className="text-[10px] font-bold uppercase tracking-widest text-emerald-600 mb-1.5 sm:mb-2">
                                        🏏 Batting
                                    </div>
                                    <div className="text-slate-900 font-bold text-sm sm:text-base" style={DISPLAY_FONT}>
                                        {battingFirst?.join(', ')}
                                    </div>
                                </div>
                                <div className="bg-purple-50 border border-purple-200 rounded-xl p-3 sm:p-4">
                                    <div className="text-[10px] font-bold uppercase tracking-widest text-purple-600 mb-1.5 sm:mb-2">
                                        🎯 Bowling
                                    </div>
                                    <div className="text-slate-900 font-bold text-sm sm:text-base" style={DISPLAY_FONT}>
                                        {bowlingFirst?.join(', ')}
                                    </div>
                                </div>
                            </div>

                            {/* Match starting indicator */}
                            <div className="flex items-center justify-center gap-2 pt-1">
                                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                                <span className="text-xs font-bold uppercase tracking-widest text-emerald-600">
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
