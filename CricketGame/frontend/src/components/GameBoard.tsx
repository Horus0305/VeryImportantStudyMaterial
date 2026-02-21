import { useCallback, useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import HeadToHead from '@/components/HeadToHead'

interface BatCard {
    name: string; runs: number; balls: number; fours: number; sixes: number; sr: number; dismissal: string; is_out: boolean
}
interface BowlCard {
    name: string; overs: string; runs: number; wickets: number; econ: number
}
interface StandingsEntry {
    player: string; played: number; won: number; lost: number; tied: number; points: number; nrr: number
}
interface TournamentPayload {
    standings: StandingsEntry[]
    phase: string
    upcoming_matches?: Array<{ label: string; teams: string[] }>
}
interface CaptainOption {
    player: string
    disabled: boolean
}

interface MatchState {
    mode: string
    innings: number
    batting_side: string[]
    bowling_side: string[]
    striker: string
    non_striker: string | null
    bowler: string
    total_runs: number
    wickets: number
    overs: string
    total_overs: number
    target: number | null
    batting_card: BatCard[]
    bowling_card: BowlCard[]
    my_role: string
    bat_ready?: boolean
    bowl_ready?: boolean
    tournament?: TournamentPayload
    needs_batter_choice?: boolean
    needs_bowler_choice?: boolean
    available_batters?: CaptainOption[]
    available_bowlers?: CaptainOption[]
    batting_captain?: string | null
    bowling_captain?: string | null
}

interface BallFlash {
    is_out?: boolean
    runs?: number
    milestone?: number | null
    hat_trick?: boolean
}

interface Props {
    state: MatchState
    ballFlash: BallFlash | null
    sendMsg: (msg: Record<string, unknown>) => void
    isHost: boolean
    countdown?: { role: string; seconds: number } | null
}

const DISPLAY_FONT = { fontFamily: "'Bebas Neue', 'Teko', sans-serif" }

const ROLE_LABELS: Record<string, { text: string; icon: string; active: boolean }> = {
    BATTING: { text: 'You are BATTING – pick your number!', icon: '', active: true },
    BOWLING: { text: 'You are BOWLING – pick your number!', icon: '', active: true },
    NON_STRIKER: { text: 'Non-Striker – waiting...', icon: '', active: false },
    FIELDING: { text: 'Fielding – waiting...', icon: '', active: false },
    SPECTATING: { text: 'Spectating match...', icon: '', active: false },
    WAITING: { text: 'Waiting for captain...', icon: '⏳', active: false },
    BATTING_CAPTAIN_PICK: { text: 'You are captain – pick next batter!', icon: '', active: false },
    BOWLING_CAPTAIN_PICK: { text: 'You are captain – pick next bowler!', icon: '', active: false },
}

// ─── Celebration Particle System ──────────────────────────────────────────────

interface Particle {
    id: number; x: number; y: number; vx: number; vy: number
    color: string; size: number; life: number; maxLife: number; shape: 'circle' | 'rect'
}

function makeParticles(count: number, colors: string[], edgeSpread: boolean = false, side: 'left' | 'right' = 'left'): Particle[] {
    return Array.from({ length: count }, (_, i) => {
        let startX = 50;
        let vx = (Math.random() - 0.5) * 8;

        if (edgeSpread) {
            startX = side === 'left' ? Math.random() * 15 : 85 + Math.random() * 15;
            vx = side === 'left' ? Math.random() * 6 + 2 : -(Math.random() * 6 + 2);
        }

        return {
            id: Date.now() + i,
            x: startX, y: 50,
            vx,
            vy: -(Math.random() * 7 + 2),
            color: colors[Math.floor(Math.random() * colors.length)],
            size: Math.random() * 10 + 4,
            life: 60,
            maxLife: 60,
            shape: Math.random() > 0.5 ? 'circle' : 'rect',
        }
    })
}

function CelebrationOverlay({ flash }: { flash: BallFlash | null }) {
    const [particles, setParticles] = useState<Particle[]>([])
    const [label, setLabel] = useState<{ text: string; color: string; size: string } | null>(null)
    const rafRef = useRef<number | null>(null)
    const prevFlashRef = useRef<BallFlash | null>(null)

    useEffect(() => {
        if (!flash || flash === prevFlashRef.current) return
        prevFlashRef.current = flash

        let newParticles: Particle[] = []
        let newLabel: { text: string; color: string; size: string } | null = null

        const side = Math.random() > 0.5 ? 'left' : 'right'

        if (flash.hat_trick) {
            newParticles = makeParticles(80, ['#f59e0b', '#ef4444', '#a855f7', '#06b6d4', '#22c55e'], true, side)
            newLabel = { text: 'HAT-TRICK! ', color: '#f59e0b', size: 'text-5xl' }
        } else if (flash.milestone === 100) {
            newParticles = makeParticles(70, ['#fbbf24', '#f59e0b', '#ef4444', '#ec4899'], true, side)
            newLabel = { text: 'CENTURY! ', color: '#fbbf24', size: 'text-5xl' }
        } else if (flash.milestone === 50) {
            newParticles = makeParticles(50, ['#a3e635', '#22c55e', '#06b6d4'], true, side)
            newLabel = { text: 'FIFTY! ', color: '#a3e635', size: 'text-4xl' }
        } else if (flash.is_out) {
            newParticles = makeParticles(30, ['#ef4444', '#f97316', '#dc2626'], true, side)
            newLabel = { text: 'WICKET!', color: '#ef4444', size: 'text-4xl' }
        } else if ((flash.runs ?? 0) === 6) {
            newParticles = makeParticles(60, ['#fcd34d', '#f59e0b', '#fbbf24', '#fff'], true, side)
            newLabel = { text: 'SIX! ', color: '#fcd34d', size: 'text-5xl' }
        } else if ((flash.runs ?? 0) === 4) {
            newParticles = makeParticles(40, ['#4ade80', '#22c55e', '#86efac', '#fff'], true, side)
            newLabel = { text: 'FOUR! ', color: '#4ade80', size: 'text-4xl' }
        } else if ((flash.runs ?? 0) > 0) {
            newLabel = { text: `+${flash.runs}`, color: '#e2e8f0', size: 'text-3xl' }
        } else {
            newLabel = { text: 'OUT!', color: '#ef4444', size: 'text-4xl' }
        }

        setParticles(newParticles)
        setLabel(newLabel)

        const labelTimer = setTimeout(() => setLabel(null), 1000)
        return () => {
            clearTimeout(labelTimer)
            if (rafRef.current) cancelAnimationFrame(rafRef.current)
        }
    }, [flash])

    useEffect(() => {
        if (particles.length === 0) return
        const animate = () => {
            setParticles(prev => {
                const next = prev
                    .map(p => ({
                        ...p,
                        x: p.x + p.vx,
                        y: p.y + p.vy,
                        vy: p.vy + 0.3,
                        life: p.life - 1,
                    }))
                    .filter(p => p.life > 0)
                return next
            })
            rafRef.current = requestAnimationFrame(animate)
        }
        rafRef.current = requestAnimationFrame(animate)
        return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
    }, [particles.length > 0])

    return (
        <div className="absolute inset-0 pointer-events-none z-20 overflow-hidden">
            {label && (
                <div
                    className={`absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2
                                font-black animate-pulse select-none ${label.size}`}
                    style={{ color: label.color, fontFamily: "'Bebas Neue', display" }}
                >
                    {label.text}
                </div>
            )}
            <svg className="absolute inset-0 w-full h-full">
                {particles.map(p => {
                    const opacity = (p.life / p.maxLife)
                    return p.shape === 'circle' ? (
                        <circle
                            key={p.id}
                            cx={`${p.x}%`} cy={`${p.y}%`}
                            r={p.size / 2}
                            fill={p.color}
                            opacity={opacity}
                        />
                    ) : (
                        <rect
                            key={p.id}
                            x={`${p.x}%`} y={`${p.y}%`}
                            width={p.size} height={p.size / 2}
                            fill={p.color}
                            opacity={opacity}
                            transform={`rotate(${p.x * 3.6}, ${p.x * 3}, ${p.y * 2})`}
                        />
                    )
                })}
            </svg>
        </div>
    )
}

// ─── Captain Picker Modal ─────────────────────────────────────────────────────

function CaptainPickerModal({
    type, options, seconds, onPick, stats
}: {
    type: 'batter' | 'bowler'
    options: CaptainOption[]
    seconds: number
    onPick: (player: string) => void
    stats?: (BatCard | BowlCard)[]
}) {
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-[2px] p-4 sm:p-6">
            <div className="bg-gradient-to-b from-slate-800 to-slate-900 border-2 border-amber-500/50 rounded-2xl p-6 sm:p-8 shadow-[0_0_40px_rgba(245,158,11,0.2)] w-full max-w-sm sm:max-w-md md:max-w-lg flex flex-col max-h-full">
                <div className="text-center mb-6 flex-shrink-0">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-800 border border-amber-500/30 mb-3 shadow-inner">
                        <span className="text-3xl sm:text-4xl">{type === 'batter' ? '🏏' : '🎳'}</span>
                    </div>
                    <h3 className="text-xl sm:text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-amber-300 to-amber-500 tracking-tight">
                        Pick Next {type === 'batter' ? 'Batter' : 'Bowler'}
                    </h3>
                    <p className="text-slate-400 text-xs sm:text-sm mt-1">Select an available player to continue</p>
                    <div className="mt-4 h-2 bg-slate-800 rounded-full overflow-hidden border border-slate-700/50 relative">
                        <div
                            className={`absolute inset-y-0 left-0 bg-gradient-to-r from-amber-500 to-yellow-400 rounded-full transition-all duration-1000 ease-linear ${seconds <= 2 ? 'animate-pulse bg-red-500 from-red-500 to-red-400' : ''}`}
                            style={{ width: `${(seconds / 5) * 100}%` }}
                        />
                    </div>
                    <p className={`text-xs mt-1.5 font-mono font-bold ${seconds <= 2 ? 'text-red-400' : 'text-amber-500'}`}>
                        {seconds}s remaining
                    </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 overflow-y-auto min-h-0 pr-1 custom-scrollbar">
                    {options.map(o => (
                        <button
                            key={o.player}
                            onClick={() => !o.disabled && onPick(o.player)}
                            className={`w-full px-4 py-3 sm:py-4 rounded-xl text-left transition-all relative overflow-hidden group border
                                ${o.disabled
                                    ? 'bg-slate-800/80 text-slate-500 border-slate-700/50 cursor-not-allowed opacity-70'
                                    : 'bg-slate-800 hover:bg-amber-500/10 border-slate-700 hover:border-amber-500/60 text-slate-200 hover:text-amber-100 cursor-pointer shadow-sm hover:shadow-md'
                                }`}
                        >
                            <div className="flex justify-between items-center relative z-10">
                                <div className="flex flex-col min-w-0">
                                    <span className={`font-bold sm:text-lg truncate tracking-tight ${o.disabled ? 'text-slate-500' : 'group-hover:text-amber-400'}`}>
                                        {o.player}
                                    </span>
                                    {stats && !o.disabled && (
                                        <span className="text-xs text-slate-400 mt-0.5">
                                            {type === 'batter'
                                                ? `${(stats.find(s => s.name === o.player) as BatCard)?.runs ?? 0} runs (${(stats.find(s => s.name === o.player) as BatCard)?.balls ?? 0}b)`
                                                : `${(stats.find(s => s.name === o.player) as BowlCard)?.wickets ?? 0}-${(stats.find(s => s.name === o.player) as BowlCard)?.runs ?? 0} (${(stats.find(s => s.name === o.player) as BowlCard)?.overs ?? '0'} ov)`
                                            }
                                        </span>
                                    )}
                                </div>
                                {o.disabled ? (
                                    <Badge variant="outline" className="text-[10px] bg-slate-900 border-slate-700 text-slate-500 py-0">Unavailable</Badge>
                                ) : (
                                    <div className="w-6 h-6 rounded-full bg-slate-700 flex items-center justify-center text-[10px] group-hover:bg-amber-500/20 group-hover:text-amber-400 transition-colors">
                                        ▶
                                    </div>
                                )}
                            </div>
                            {!o.disabled && (
                                <div className="absolute inset-0 bg-gradient-to-r from-amber-500/0 via-amber-500/5 to-amber-500/0 opacity-0 group-hover:opacity-100 transition-opacity transform translate-x-[-100%] group-hover:translate-x-[100%] duration-1000" />
                            )}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    )
}

function CaptainBanner({ type, captain, seconds }: { type: 'batter' | 'bowler'; captain: string; seconds: number }) {
    return (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-slate-900/95 border border-amber-500/60 rounded-xl px-5 py-3 shadow-2xl flex items-center gap-3 animate-slide-down">
            <div>
                <p className="text-amber-400 font-bold text-sm">
                    {captain} is picking the next {type === 'batter' ? 'batter' : 'bowler'}
                </p>
                <div className="h-1 bg-slate-700 rounded-full mt-1.5 overflow-hidden w-36">
                    <div
                        className="h-full bg-amber-400 rounded-full transition-all duration-1000 ease-linear"
                        style={{ width: `${(seconds / 5) * 100}%` }}
                    />
                </div>
            </div>
            <span className="text-amber-300 font-mono font-bold text-base">{seconds}s</span>
        </div>
    )
}

// ─── Main GameBoard ───────────────────────────────────────────────────────────

export default function GameBoard({ state, ballFlash, sendMsg, isHost, countdown }: Props) {
    const [hasSent, setHasSent] = useState(false)
    const [captainCountdown, setCaptainCountdown] = useState(0)
    const captainTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
    const role = ROLE_LABELS[state.my_role] ?? { text: 'Spectating', icon: '', active: false }
    const tournament = state.tournament

    const sendMove = useCallback((move: number) => {
        sendMsg({ action: 'GAME_MOVE', move })
        setHasSent(true)
    }, [sendMsg])

    // Reset hasSent when a new countdown timer starts (seconds === 10)
    useEffect(() => {
        if (countdown?.seconds === 10) {
            setHasSent(false)
        }
    }, [countdown?.seconds])

    // Also reset hasSent when innings changes (innings break) or role changes
    // This prevents buttons from staying disabled after an innings transition
    const prevInningsRef = useRef(state.innings)
    const prevRoleRef = useRef(state.my_role)
    useEffect(() => {
        if (state.innings !== prevInningsRef.current || state.my_role !== prevRoleRef.current) {
            setHasSent(false)
            prevInningsRef.current = state.innings
            prevRoleRef.current = state.my_role
        }
    }, [state.innings, state.my_role])

    const need = state.target ? state.target - state.total_runs : null
    const canAct = role.active && !hasSent && !ballFlash

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (!canAct) return
            if (['0', '1', '2', '3', '4', '5', '6'].includes(e.key)) {
                sendMove(parseInt(e.key))
            }
        }
        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [canAct, sendMove])

    const isCaptainPending = state.needs_batter_choice || state.needs_bowler_choice
    useEffect(() => {
        if (isCaptainPending) {
            setCaptainCountdown(5)
            captainTimerRef.current = setInterval(() => {
                setCaptainCountdown(prev => {
                    if (prev <= 1) {
                        if (captainTimerRef.current) clearInterval(captainTimerRef.current)
                        return 0
                    }
                    return prev - 1
                })
            }, 1000)
        } else {
            if (captainTimerRef.current) clearInterval(captainTimerRef.current)
            setCaptainCountdown(0)
        }
        return () => { if (captainTimerRef.current) clearInterval(captainTimerRef.current) }
    }, [isCaptainPending])

    const isBattingCaptain = state.my_role === 'BATTING_CAPTAIN_PICK'
    const isBowlingCaptain = state.my_role === 'BOWLING_CAPTAIN_PICK'
    const watchingCaptainType: 'batter' | 'bowler' | null =
        !isBattingCaptain && !isBowlingCaptain && isCaptainPending
            ? (state.needs_batter_choice ? 'batter' : 'bowler')
            : null
    const watchingCaptain = watchingCaptainType === 'batter' ? state.batting_captain : watchingCaptainType === 'bowler' ? state.bowling_captain : null

    // Determine target texts
    const targetText = state.target ? `Target: ${state.target} (Need ${need})` : '--'

    return (
        <div className="flex-1 flex flex-col lg:flex-row bg-slate-50 text-slate-900 border-t border-slate-200">
            {watchingCaptainType && watchingCaptain && (
                <CaptainBanner type={watchingCaptainType} captain={watchingCaptain} seconds={captainCountdown} />
            )}

            {/* Main Stage (Stadium Area) */}
            <section className="flex-1 relative flex flex-col bg-white p-4 lg:p-6">

                {/* Mobile Score Header */}
                <div className="lg:hidden mb-3 bg-slate-50 rounded-lg p-4 border border-slate-200">
                    <div className="flex justify-between items-center mb-2">
                        <span className="text-emerald-500 tracking-wider text-3xl" style={DISPLAY_FONT}>{state.total_runs}/{state.wickets}</span>
                        <span className="text-slate-600 text-sm font-semibold">{state.overs} Overs</span>
                    </div>
                    <div className="text-xs text-slate-400 uppercase tracking-wider font-bold">Target: {targetText}</div>
                </div>

                {/* Cricket Field Visual
                    Mobile: aspect-[4/5] gives a prominent, tall field
                    Desktop: flex-1 fills remaining height */}
                <div
                    className="relative w-full aspect-[5/4] lg:aspect-auto lg:flex-1 rounded-2xl overflow-hidden shadow-inner border border-slate-200 group"
                    style={{ background: 'radial-gradient(circle, #2d6a36 0%, #1B4D26 100%)' }}
                >
                    {/* Boundary Circles */}
                    <div className="absolute inset-4 sm:inset-6 border-2 border-white/15 rounded-full opacity-50" />
                    <div className="absolute inset-[15%] sm:inset-[18%] border border-white/10 rounded-full border-dashed opacity-30" />

                    {/* Role Banner — visible on BOTH mobile and desktop */}
                    {role.active && (
                        <div className="absolute top-4 left-0 right-0 flex justify-center z-20">
                            <div className="bg-orange-100 text-orange-800 px-4 py-1.5 rounded-full shadow-lg flex items-center space-x-2 text-xs font-bold uppercase tracking-wider border border-orange-200 backdrop-blur-sm lg:bg-white/95 lg:text-slate-800 lg:border-slate-200 lg:rounded-sm lg:px-6 lg:py-2 lg:shadow-md">
                                <span className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
                                <span>{role.text}</span>
                            </div>
                        </div>
                    )}
                    {!role.active && role.text && (
                        <div className="absolute top-4 left-0 right-0 flex justify-center z-20">
                            <div className="bg-white/80 text-slate-600 px-4 py-1.5 rounded-full shadow flex items-center space-x-2 text-xs font-bold uppercase tracking-wider border border-slate-200 backdrop-blur-sm lg:rounded-sm lg:px-6 lg:py-2">
                                <span>{role.text}</span>
                            </div>
                        </div>
                    )}

                    {/* Central Pitch Box — vertical on mobile, horizontal on desktop */}
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
                        w-24 h-48 sm:w-[60%] sm:h-24 md:h-32
                        bg-[#D2B48C] rounded shadow-xl border-2 border-[#C19A6B]
                        flex flex-col sm:flex-row items-center justify-between py-2 sm:py-0 sm:px-4 opacity-95">
                        {/* Stumps Top / Left */}
                        <div className="flex justify-center sm:justify-start space-x-[2px] sm:gap-1 sm:h-12 md:h-16 sm:items-end relative">
                            <div className="w-1 h-8 sm:h-full bg-slate-800 rounded-sm" />
                            <div className="w-1 h-8 sm:h-full bg-slate-800 rounded-sm" />
                            <div className="w-1 h-8 sm:h-full bg-slate-800 rounded-sm" />
                        </div>
                        {/* PITCH label — rotated on mobile, horizontal on desktop */}
                        <div className="text-center opacity-30 pointer-events-none select-none">
                            <span className="text-2xl sm:text-4xl font-bold tracking-[0.2em] text-[#8B4513] block sm:transform-none -rotate-90 sm:rotate-0" style={DISPLAY_FONT}>PITCH</span>
                        </div>
                        {/* Stumps Bottom / Right */}
                        <div className="flex justify-center sm:justify-start space-x-[2px] sm:gap-1 sm:h-12 md:h-16 sm:items-end relative">
                            <div className="w-1 h-8 sm:h-full bg-slate-800 rounded-sm" />
                            <div className="w-1 h-8 sm:h-full bg-slate-800 rounded-sm" />
                            <div className="w-1 h-8 sm:h-full bg-slate-800 rounded-sm" />
                        </div>
                    </div>

                    {/* Fielder dots */}
                    <div className="absolute top-[30%] left-[20%] w-3 h-3 bg-white rounded-full shadow-lg border-2 border-slate-300" />
                    <div className="absolute bottom-[20%] right-[30%] w-3 h-3 bg-emerald-400 rounded-full shadow-[0_0_10px_rgba(52,211,153,0.8)] animate-bounce" />

                    {/* Mobile countdown bar inside the field */}
                    {countdown && !isCaptainPending && (
                        <div className="absolute bottom-4 left-4 right-4 z-10 lg:hidden">
                            <div className="flex justify-between text-[10px] font-bold text-white/80 mb-1 uppercase tracking-wider">
                                <span>Your turn to {countdown.role}</span>
                                <span>{countdown.seconds}s</span>
                            </div>
                            <div className="h-2 bg-black/30 rounded-full overflow-hidden backdrop-blur">
                                <div
                                    className="h-full bg-emerald-500 rounded-full shadow-[0_0_10px_rgba(16,185,129,0.5)] transition-all duration-1000 ease-linear"
                                    style={{ width: `${(countdown.seconds / 10) * 100}%` }}
                                />
                            </div>
                        </div>
                    )}

                    {/* Celebrations inside stadium */}
                    <CelebrationOverlay flash={ballFlash} />

                    {isBattingCaptain && state.available_batters && (
                        <CaptainPickerModal type="batter" options={state.available_batters} seconds={captainCountdown} onPick={(player) => sendMsg({ action: 'PICK_BATTER', player })} stats={state.batting_card} />
                    )}
                    {isBowlingCaptain && state.available_bowlers && (
                        <CaptainPickerModal type="bowler" options={state.available_bowlers} seconds={captainCountdown} onPick={(player) => sendMsg({ action: 'PICK_BOWLER', player })} stats={state.bowling_card} />
                    )}
                </div>

                {/* Input Area — Number Buttons */}
                <div className="mt-4 sm:mt-6 w-full max-w-3xl mx-auto px-1 sm:px-4 z-10 shrink-0">
                    {/* Desktop-only countdown bar (outside the field) */}
                    <div className={`w-full transition-opacity duration-300 hidden lg:block ${countdown && !isCaptainPending ? 'opacity-100' : 'opacity-0'}`}>
                        {countdown && !isCaptainPending && (
                            <>
                                <div className="flex justify-between items-end mb-2 text-xs font-mono px-2 font-bold uppercase" style={{ color: countdown.role === 'bat' ? '#10B981' : '#64748b' }}>
                                    <span>Your turn to {countdown.role}</span>
                                    <span>{countdown.seconds}s</span>
                                </div>
                                <div className="w-full h-1.5 bg-slate-200 rounded-full mb-4 overflow-hidden">
                                    <div className={`h-full transition-all duration-1000 ease-linear ${countdown.role === 'bat' ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.3)]' : 'bg-slate-500'}`} style={{ width: `${(countdown.seconds / 10) * 100}%` }} />
                                </div>
                            </>
                        )}
                        {(!countdown || isCaptainPending) && <div className="h-6 mb-4" />}
                    </div>

                    {/* Number Buttons */}
                    <div className="bg-white/90 backdrop-blur-xl border border-slate-200 rounded-2xl p-3 flex items-center justify-between sm:justify-center gap-2 sm:gap-4 shadow-xl">
                        {[0, 1, 2, 3, 4, 5, 6].map(n => (
                            <button
                                key={n}
                                onClick={() => sendMove(n)}
                                disabled={!canAct || isCaptainPending}
                                className={`flex-1 sm:flex-initial aspect-square sm:w-16 sm:h-16 rounded-xl flex items-center justify-center transition-all active:scale-95 group relative border text-2xl sm:text-4xl shadow-sm
                                    ${!canAct || isCaptainPending ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                                    ${n === 4
                                        ? 'bg-emerald-500 border-transparent text-white shadow-lg shadow-emerald-500/30 transform scale-110 border-2 border-emerald-400 hover:scale-[1.15] z-10'
                                        : n === 6
                                            ? 'bg-slate-100 border-slate-200 hover:border-purple-600 hover:bg-purple-50 hover:text-purple-600 text-slate-700'
                                            : 'bg-slate-100 border-slate-200 hover:border-emerald-500 hover:bg-emerald-50 hover:text-emerald-500 text-slate-700'}
                                `}
                                style={DISPLAY_FONT}
                            >
                                {n}
                                {n === 0 && <span className="absolute -bottom-3 opacity-0 group-hover:opacity-100 text-[9px] text-emerald-500 font-sans uppercase tracking-wider font-bold transition-opacity hidden sm:inline">Dot</span>}
                                {n === 6 && <span className="absolute -bottom-3 opacity-0 group-hover:opacity-100 text-[9px] text-purple-600 font-sans uppercase tracking-wider font-bold transition-opacity hidden sm:inline">Max</span>}
                            </button>
                        ))}
                    </div>

                    {isHost && (
                        <div className="mt-4 text-center">
                            <Button variant="ghost" className="text-xs text-red-500 hover:bg-red-50 uppercase tracking-widest font-bold" onClick={() => { if (confirm('Cancel this match? It will be a Tie.')) sendMsg({ action: 'CANCEL_MATCH' }) }}>
                                Exit Match
                            </Button>
                        </div>
                    )}
                </div>
            </section>

            {/* RIGHT COLUMN: INFO ASIDE */}
            <aside className="w-full lg:w-[400px] xl:w-[450px] bg-slate-50 border-t lg:border-t-0 lg:border-l border-slate-200 flex flex-col min-h-0 lg:h-full z-10 shadow-sm custom-scrollbar overflow-y-auto pb-6 lg:pb-0">
                {/* Score Status Header - Sticky on desktop */}
                <div className="p-4 sm:p-6 border-b border-slate-200 bg-slate-50 sticky top-0 z-20 shrink-0 hidden lg:block">
                    <div className="flex justify-between items-center mb-4">
                        <span className="text-xs font-bold text-emerald-500 uppercase tracking-widest flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                            Live Stats
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono font-bold">Innings {state.innings}</span>
                    </div>
                    <div className="flex items-center justify-between gap-4">
                        <div className="text-left">
                            <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Batting</span>
                            <span className="block text-2xl text-emerald-500 tracking-wide truncate max-w-[120px]" style={DISPLAY_FONT}>{state.batting_side[0] || 'Team A'}</span>
                        </div>
                        <div className="text-center shrink-0">
                            <span className="block text-3xl font-black text-slate-900 leading-none" style={DISPLAY_FONT}>{state.total_runs}/{state.wickets}</span>
                            <span className="block text-xs text-slate-500 font-bold">({state.overs} ov)</span>
                        </div>
                        <div className="text-right">
                            <span className="block text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-1">Bowling</span>
                            <span className="block text-2xl text-slate-900 tracking-wide truncate max-w-[120px]" style={DISPLAY_FONT}>{state.bowling_side[0] || 'Team B'}</span>
                        </div>
                    </div>
                    {state.target && (
                        <div className="mt-3 text-center text-xs font-bold uppercase tracking-wider text-slate-500 bg-slate-200/50 py-1 rounded">
                            Target: {state.target} (Need {need})
                        </div>
                    )}
                </div>

                {/* Main scrollable stats content */}
                <div className="p-4 sm:p-6 flex-1 space-y-4 sm:space-y-6">
                    {/* H2H Collapsible Component */}
                    {state.striker && state.bowler &&
                        !state.striker.startsWith('CPU') && !state.bowler.startsWith('CPU') && (
                            <HeadToHead
                                player1={state.striker}
                                player2={state.bowler}
                                defaultOpen={false}
                            />
                        )}

                    {/* Batting Squad */}
                    <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm">
                        <div className="bg-gradient-to-r from-emerald-50 to-transparent p-3 border-b border-slate-100 flex justify-between items-center">
                            <h3 className="text-lg tracking-wide text-slate-900" style={DISPLAY_FONT}>Batting Squad</h3>
                            <span className="text-emerald-500 text-lg">🏏</span>
                        </div>
                        <table className="w-full text-left text-xs sm:text-sm">
                            <thead>
                                <tr className="text-[10px] text-slate-500 uppercase tracking-wider font-bold border-b border-slate-100 bg-slate-50/50">
                                    <th className="px-3 sm:px-4 py-2 font-bold">Batter</th>
                                    <th className="px-1 sm:px-2 py-2 text-center font-bold">R</th>
                                    <th className="px-1 sm:px-2 py-2 text-center font-bold">B</th>
                                    <th className="px-1 sm:px-2 py-2 text-center font-bold hidden sm:table-cell">4s</th>
                                    <th className="px-1 sm:px-2 py-2 text-center font-bold hidden sm:table-cell">6s</th>
                                    <th className="px-2 sm:px-2 py-2 text-right font-bold">SR</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 font-mono text-[10px] sm:text-xs">
                                {state.batting_card.map((bc) => (
                                    <tr key={bc.name} className={`${bc.name === state.striker ? 'bg-emerald-500/5' : ''} ${bc.is_out ? 'text-slate-400 line-through opacity-70' : 'text-slate-600'} relative group`}>
                                        <td className={`px-3 sm:px-4 py-2.5 sm:py-3 font-bold flex items-center gap-1.5 ${bc.name === state.striker ? 'text-emerald-600' : 'text-slate-700'} truncate max-w-[100px] sm:max-w-[140px]`}>
                                            {bc.name}
                                            {bc.name === state.striker && <span className="text-emerald-500 text-[10px]">★</span>}
                                            {bc.name === state.striker && <div className="absolute left-0 top-0 bottom-0 w-1 bg-emerald-500"></div>}
                                        </td>
                                        <td className="px-1 sm:px-2 py-2.5 sm:py-3 text-center text-slate-900 font-bold">{bc.runs}</td>
                                        <td className="px-1 sm:px-2 py-2.5 sm:py-3 text-center">{bc.balls}</td>
                                        <td className="px-1 sm:px-2 py-2.5 sm:py-3 text-center hidden sm:table-cell">{bc.fours}</td>
                                        <td className="px-1 sm:px-2 py-2.5 sm:py-3 text-center hidden sm:table-cell">{bc.sixes}</td>
                                        <td className="px-2 sm:px-2 py-2.5 sm:py-3 text-right">{bc.sr}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Bowling Attack */}
                    <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm">
                        <div className="bg-gradient-to-r from-blue-50 to-transparent p-3 border-b border-slate-100 flex justify-between items-center">
                            <h3 className="text-lg tracking-wide text-slate-900" style={DISPLAY_FONT}>Bowling Attack</h3>
                            <span className="text-blue-600 text-lg">⚾</span>
                        </div>
                        <table className="w-full text-left text-xs sm:text-sm">
                            <thead>
                                <tr className="text-[10px] text-slate-500 uppercase tracking-wider font-bold border-b border-slate-100 bg-slate-50/50">
                                    <th className="px-3 sm:px-4 py-2 font-bold">Bowler</th>
                                    <th className="px-1 sm:px-2 py-2 text-center font-bold">O</th>
                                    <th className="px-1 sm:px-2 py-2 text-center font-bold">R</th>
                                    <th className="px-1 sm:px-2 py-2 text-center font-bold text-emerald-600">W</th>
                                    <th className="px-2 sm:px-2 py-2 text-right font-bold">Econ</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 font-mono text-[10px] sm:text-xs">
                                {state.bowling_card.map((bw) => (
                                    <tr key={bw.name} className={`${bw.name === state.bowler ? 'bg-slate-50/80' : ''} text-slate-600 relative`}>
                                        <td className={`px-3 sm:px-4 py-2.5 sm:py-3 font-bold flex items-center gap-1.5 ${bw.name === state.bowler ? 'text-slate-900' : 'text-slate-700'} truncate max-w-[120px] sm:max-w-[150px]`}>
                                            {bw.name}
                                            {bw.name === state.bowler && <span className="text-emerald-500 text-[10px] animate-spin">⚡</span>}
                                        </td>
                                        <td className="px-1 sm:px-2 py-2.5 sm:py-3 text-center">{bw.overs}</td>
                                        <td className="px-1 sm:px-2 py-2.5 sm:py-3 text-center">{bw.runs}</td>
                                        <td className="px-1 sm:px-2 py-2.5 sm:py-3 text-center text-emerald-600 font-bold">{bw.wickets}</td>
                                        <td className="px-2 sm:px-2 py-2.5 sm:py-3 text-right">{bw.econ}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Standings if tournament */}
                    {tournament?.standings?.length ? (
                        <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm">
                            <div className="bg-gradient-to-r from-purple-50 to-transparent p-3 border-b border-slate-100 flex justify-between items-center">
                                <h3 className="text-lg tracking-wide text-slate-900" style={DISPLAY_FONT}>Standings</h3>
                                <span className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">{tournament.phase}</span>
                            </div>
                            <div className="p-2 space-y-1 text-[10px] sm:text-xs font-mono">
                                {tournament.standings.slice(0, 4).map((s, i) => (
                                    <div key={s.player} className="flex justify-between items-center rounded p-1.5 sm:p-2 bg-slate-50/50 hover:bg-slate-50 transition-colors">
                                        <span className="w-4 text-slate-400 font-bold">{i + 1}</span>
                                        <span className="flex-1 truncate text-slate-700 font-bold">{s.player}</span>
                                        <div className="flex gap-2 sm:gap-4 shrink-0 px-2">
                                            <span className="w-4 text-center text-emerald-500 font-bold">{s.won}</span>
                                            <span className="w-4 text-center text-red-400">{s.lost}</span>
                                        </div>
                                        <span className="w-8 text-center text-slate-900 font-black">{s.points}</span>
                                        <span className="w-10 sm:w-12 text-right text-slate-500">
                                            {s.nrr >= 0 ? '+' : ''}{s.nrr.toFixed(2)}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    ) : null}

                </div>
            </aside>
        </div>
    )
}
