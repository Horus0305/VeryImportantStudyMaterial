/**
 * GameBoard — Live match view with score, ball buttons, and mini scorecard.
 * Designed to fit the full viewport without scrolling.
 * Includes: In-pitch score flash, celebrations, captain picker modal, countdown bar.
 */
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
            // Pick left edge (0-15) or right edge (85-100)
            startX = side === 'left' ? Math.random() * 15 : 85 + Math.random() * 15;
            // Left edge shoots right (positive vx), Right edge shoots left (negative vx)
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

        // eslint-disable-next-line react-hooks/set-state-in-effect
        setParticles(newParticles)

        setLabel(newLabel)

        // Auto-clear label after 1s
        const labelTimer = setTimeout(() => setLabel(null), 1000)
        return () => {
            clearTimeout(labelTimer)
            if (rafRef.current) cancelAnimationFrame(rafRef.current)
        }
    }, [flash])

    // Animate particles
    useEffect(() => {
        if (particles.length === 0) return
        const animate = () => {
            setParticles(prev => {
                const next = prev
                    .map(p => ({
                        ...p,
                        x: p.x + p.vx,
                        y: p.y + p.vy,
                        vy: p.vy + 0.3,   // gentler gravity
                        life: p.life - 1,  // 2× slower than before
                    }))
                    .filter(p => p.life > 0)
                return next
            })
            rafRef.current = requestAnimationFrame(animate)
        }
        rafRef.current = requestAnimationFrame(animate)
        return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
    }, [particles.length > 0])  // eslint-disable-line react-hooks/exhaustive-deps

    return (
        <div className="absolute inset-0 pointer-events-none z-20 overflow-hidden">
            {/* Floating score label in center (Glow removed) */}
            {label && (
                <div
                    className={`absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2
                                font-black animate-pulse select-none ${label.size}`}
                    style={{ color: label.color }}
                >
                    {label.text}
                </div>
            )}

            {/* Particles rendered as SVG */}
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
    type, options, seconds, onPick,
}: {
    type: 'batter' | 'bowler'
    options: CaptainOption[]
    seconds: number
    onPick: (player: string) => void
}) {
    return (
        <div className="absolute inset-0 z-30 flex items-center justify-center bg-black/70 backdrop-blur-md rounded-xl p-4 sm:p-6 overflow-hidden">
            <div className="bg-gradient-to-b from-slate-800 to-slate-900 border-2 border-amber-500/50 rounded-2xl p-6 sm:p-8 shadow-[0_0_40px_rgba(245,158,11,0.2)] w-full max-w-sm sm:max-w-md md:max-w-lg flex flex-col max-h-full">

                {/* Header */}
                <div className="text-center mb-6 flex-shrink-0">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-800 border border-amber-500/30 mb-3 shadow-inner">
                        <span className="text-3xl sm:text-4xl">{type === 'batter' ? '🏏' : '🎳'}</span>
                    </div>
                    <h3 className="text-xl sm:text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-amber-300 to-amber-500 tracking-tight">
                        Pick Next {type === 'batter' ? 'Batter' : 'Bowler'}
                    </h3>
                    <p className="text-slate-400 text-xs sm:text-sm mt-1">Select an available player to continue</p>

                    {/* Countdown bar */}
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

                {/* Grid List of Players */}
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
                                <span className={`font-bold sm:text-lg truncate tracking-tight ${o.disabled ? 'text-slate-500' : 'group-hover:text-amber-400'}`}>
                                    {o.player}
                                </span>
                                {o.disabled ? (
                                    <Badge variant="outline" className="text-[10px] bg-slate-900 border-slate-700 text-slate-500 py-0">Unavailable</Badge>
                                ) : (
                                    <div className="w-6 h-6 rounded-full bg-slate-700 flex items-center justify-center text-[10px] group-hover:bg-amber-500/20 group-hover:text-amber-400 transition-colors">
                                        ▶
                                    </div>
                                )}
                            </div>

                            {/* Hover effect gradient */}
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

// ─── Captain Announcement Banner ─────────────────────────────────────────────

function CaptainBanner({ type, captain, seconds }: { type: 'batter' | 'bowler'; captain: string; seconds: number }) {
    return (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-slate-900/95 border border-amber-500/60 rounded-xl px-5 py-3 shadow-2xl flex items-center gap-3 animate-slide-down">
            <span className="text-2xl">{type === 'batter' ? '' : ''}</span>
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

    useEffect(() => {
        // When countdown resets back to 10 for a new ball, re-enable the run buttons
        if (countdown?.seconds === 10) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setHasSent(false)
        }
    }, [countdown?.seconds])

    const need = state.target ? state.target - state.total_runs : null
    // Disable buttons if we have already sent a move, OR if a celebration (ballFlash) is currently playing
    const canAct = role.active && !hasSent && !ballFlash

    // Keyboard shortcut for ball moves
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

    // Captain countdown timer (visual only — real timeout is on backend)
    const isCaptainPending = state.needs_batter_choice || state.needs_bowler_choice
    useEffect(() => {
        if (isCaptainPending) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
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

    // Determine announcement for non-captain players
    const watchingCaptainType: 'batter' | 'bowler' | null =
        !isBattingCaptain && !isBowlingCaptain && isCaptainPending
            ? (state.needs_batter_choice ? 'batter' : 'bowler')
            : null
    const watchingCaptain =
        watchingCaptainType === 'batter' ? state.batting_captain :
            watchingCaptainType === 'bowler' ? state.bowling_captain : null

    return (
        <div className="w-full max-w-7xl mx-auto flex flex-col h-auto sm:h-[calc(100vh-4rem)] min-h-[calc(100dvh-4rem)] p-3 sm:p-4 gap-3 sm:gap-4 overflow-y-auto sm:overflow-hidden">

            {/* Captain watching banner (for non-captain players) */}
            {watchingCaptainType && watchingCaptain && (
                <CaptainBanner type={watchingCaptainType} captain={watchingCaptain} seconds={captainCountdown} />
            )}

            {/* Row 1: Score Header + Target */}
            <div className="flex flex-col gap-2 bg-gradient-to-r from-slate-800/60 to-slate-900/60 backdrop-blur-sm rounded-xl border border-slate-700/50 px-4 py-3 shadow-2xl flex-shrink-0">
                <div className="flex justify-between items-start sm:items-center">
                    <div>
                        <p className="text-xs sm:text-base text-slate-300 font-medium break-words">
                            Innings {state.innings} • <span className="text-orange-400 font-bold">{state.batting_side.join(', ')}</span>
                            <span className="text-slate-500 ml-1">vs {state.bowling_side.join(', ')}</span>
                        </p>
                    </div>
                    {isHost && (
                        <Button
                            variant="destructive"
                            size="sm"
                            className="h-6 text-[10px] px-2 sm:h-8 sm:text-xs"
                            onClick={() => {
                                if (confirm('Cancel this match? It will be a Tie.')) sendMsg({ action: 'CANCEL_MATCH' })
                            }}
                        >
                            Cancel
                        </Button>
                    )}
                </div>

                <div className="flex justify-between items-end">
                    {state.target ? (
                        <p className="text-[10px] sm:text-sm">
                            <span className="text-blue-300 font-bold block sm:inline"> Target: {state.target}</span>
                            <span className="text-green-300 font-bold block sm:inline sm:ml-2">Need {need} run(s)</span>
                        </p>
                    ) : null}

                    <div className="text-right">
                        <span className="text-3xl sm:text-5xl font-black tracking-tight bg-gradient-to-r from-orange-400 via-pink-500 to-red-500 bg-clip-text text-transparent block leading-none">
                            {state.total_runs}/{state.wickets}
                        </span>
                        <span className="text-slate-400 text-xs sm:text-base font-medium block mt-1">
                            ({state.overs}/{state.total_overs} ov)
                        </span>
                    </div>
                </div>
            </div>

            {/* H2H collapsible — striker vs bowler in all modes (skip CPUs) */}
            {state.striker && state.bowler &&
                !state.striker.startsWith('CPU') && !state.bowler.startsWith('CPU') && (
                    <HeadToHead
                        player1={state.striker}
                        player2={state.bowler}
                        defaultOpen={false}
                    />
                )}

            {/* Row 2: Main content — Stadium + Controls on left, Mini Scorecard on right */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-5 gap-3 sm:gap-4 min-h-0 overflow-visible sm:overflow-hidden">
                {/* Left Column: Stadium + Role + Buttons */}
                <div className="lg:col-span-3 flex flex-col gap-3 min-h-0">

                    {/* Stadium Visual — celebrations are INSIDE this div */}
                    <div className="bg-gradient-to-b from-green-800 to-green-900 rounded-xl relative flex items-center justify-center flex-1 min-h-[160px] border border-green-700/50 overflow-hidden">
                        <div className="absolute inset-4 border-2 border-white/15 border-dashed rounded-full" />

                        {/* Pitch strip — only wickets / stumps, NO names */}
                        <div className="w-full max-w-xs sm:max-w-sm h-14 sm:h-16 bg-gradient-to-b from-amber-700/80 to-amber-800/80 rounded-lg border border-amber-600 flex items-center justify-between px-3 sm:px-4 shadow-inner z-10">
                            <div className="flex gap-0.5">
                                {[0, 1, 2].map(i => (
                                    <div key={i} className="w-1.5 h-8 bg-white rounded-sm shadow" />
                                ))}
                            </div>
                            <div className="text-white/30 text-xs font-mono select-none">PITCH</div>
                            <div className="flex gap-0.5">
                                {[0, 1, 2].map(i => (
                                    <div key={i} className="w-1.5 h-8 bg-white rounded-sm shadow" />
                                ))}
                            </div>
                        </div>

                        {/* Celebration / score flash overlay — fixed inside stadium */}
                        <CelebrationOverlay flash={ballFlash} />

                        {/* Captain picker — also rendered inside stadium overlay */}
                        {isBattingCaptain && state.available_batters && (
                            <CaptainPickerModal
                                type="batter"
                                options={state.available_batters}
                                seconds={captainCountdown}
                                onPick={(player) => sendMsg({ action: 'PICK_BATTER', player })}
                            />
                        )}
                        {isBowlingCaptain && state.available_bowlers && (
                            <CaptainPickerModal
                                type="bowler"
                                options={state.available_bowlers}
                                seconds={captainCountdown}
                                onPick={(player) => sendMsg({ action: 'PICK_BOWLER', player })}
                            />
                        )}
                    </div>

                    {/* Move Status Indicators */}
                    <div className="flex flex-col sm:flex-row justify-center gap-2 sm:gap-6 flex-shrink-0">
                        <div className={`flex items-center justify-center gap-2 px-3 sm:px-4 py-2 rounded-lg border text-xs sm:text-sm font-semibold transition-all ${state.bat_ready
                            ? 'bg-green-500/20 border-green-500/40 text-green-300'
                            : 'bg-slate-800/50 border-slate-700/50 text-slate-400'
                            }`}>
                            {state.bat_ready ? '' : '⏳'} Batter {state.bat_ready ? 'Ready' : 'Choosing...'}
                        </div>
                        <div className={`flex items-center justify-center gap-2 px-3 sm:px-4 py-2 rounded-lg border text-xs sm:text-sm font-semibold transition-all ${state.bowl_ready
                            ? 'bg-green-500/20 border-green-500/40 text-green-300'
                            : 'bg-slate-800/50 border-slate-700/50 text-slate-400'
                            }`}>
                            {state.bowl_ready ? '' : '⏳'} Bowler {state.bowl_ready ? 'Ready' : 'Choosing...'}
                        </div>
                    </div>

                    {/* Role & Number Buttons */}
                    <div className="text-center space-y-3 flex-shrink-0">
                        <Badge
                            className={role.active
                                ? 'text-sm sm:text-base px-4 sm:px-6 py-2 bg-gradient-to-r from-orange-500 to-pink-600 text-white border-0 shadow-lg shadow-orange-500/20 font-bold'
                                : isBattingCaptain || isBowlingCaptain
                                    ? 'text-sm sm:text-base px-4 sm:px-6 py-2 bg-gradient-to-r from-amber-500 to-yellow-600 text-white border-0 shadow-lg font-bold'
                                    : 'text-sm sm:text-base px-4 sm:px-6 py-2 bg-slate-700/50 text-slate-300 border-slate-600 font-medium'}
                        >
                            {role.icon} {role.text}
                        </Badge>

                        <div className="grid grid-cols-4 sm:flex sm:justify-center gap-2 sm:gap-3">
                            {[0, 1, 2, 3, 4, 5, 6].map(n => (
                                <Button
                                    key={n}
                                    size="lg"
                                    className={`w-14 h-14 sm:w-16 sm:h-16 text-xl sm:text-2xl font-black shadow-lg transition-all hover:scale-105 ${n === 6 ? 'bg-gradient-to-br from-yellow-400 to-orange-600 hover:from-yellow-500 hover:to-orange-700 text-white shadow-yellow-500/30' :
                                        n === 4 ? 'bg-gradient-to-br from-green-400 to-emerald-600 hover:from-green-500 hover:to-emerald-700 text-white shadow-green-500/30' :
                                            'bg-slate-800/70 border-2 border-slate-600 text-white hover:bg-slate-700 hover:border-slate-500'
                                        }`}
                                    disabled={!canAct || isCaptainPending}
                                    onClick={() => sendMove(n)}
                                >
                                    {n}
                                </Button>
                            ))}
                        </div>

                        {/* Ball-pick countdown bar wrapper - fixed height prevents layout shift/flicker */}
                        <div className={`w-full max-w-xs sm:max-w-sm mx-auto mt-1 min-h-[32px] transition-opacity duration-300 ${countdown && !isCaptainPending ? 'opacity-100' : 'opacity-0'}`}>
                            {countdown && !isCaptainPending && (
                                <>
                                    <div className="flex justify-between text-xs font-mono mb-1">
                                        <span className={countdown.role === 'bat' ? 'text-orange-400' : 'text-purple-400'}>
                                            {countdown.role === 'bat' ? ' Your turn to bat' : countdown.role === 'bowl' ? ' Your turn to bowl' : ''}
                                        </span>
                                        <span className={`font-bold tabular-nums ${countdown.seconds <= 3 ? 'text-red-400 animate-pulse' : 'text-slate-300'
                                            }`}>{countdown.seconds}s</span>
                                    </div>
                                    <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                                        <div
                                            className={`h-full rounded-full transition-all duration-1000 ease-linear ${countdown.role === 'bat' ? 'bg-orange-500' :
                                                countdown.role === 'bowl' ? 'bg-purple-500' : 'bg-amber-400'
                                                }`}
                                            style={{ width: `${(countdown.seconds / 10) * 100}%` }}
                                        />
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                </div>

                {/* Right Column: Now Playing + Mini Scorecard */}
                <div className="lg:col-span-2 flex flex-col gap-3 min-h-0 overflow-auto">

                    {/* Now Playing bar */}
                    <div className="bg-gradient-to-r from-slate-800/70 to-slate-900/70 backdrop-blur-sm rounded-xl border border-slate-700/50 px-4 py-2.5 shadow-xl flex justify-between items-center gap-4 flex-shrink-0">
                        <div className="flex items-center gap-2 min-w-0">
                            <span className="text-lg"></span>
                            <div className="min-w-0">
                                <p className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Batting</p>
                                <p className="text-sm font-black text-orange-300 truncate">{state.striker}</p>
                            </div>
                        </div>
                        <div className="w-px h-8 bg-slate-700/80" />
                        <div className="flex items-center gap-2 min-w-0 text-right flex-row-reverse">
                            <span className="text-lg"></span>
                            <div className="min-w-0">
                                <p className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold text-right">Bowling</p>
                                <p className="text-sm font-black text-purple-300 truncate text-right">{state.bowler}</p>
                            </div>
                        </div>
                    </div>

                    {/* Batting Card */}
                    <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-4 shadow-2xl flex-1">
                        <h4 className="font-bold text-base mb-2 text-green-400 flex items-center gap-2">
                            <span>Batting</span>
                        </h4>
                        <div className="space-y-1 font-mono text-xs">
                            <div className="flex gap-1 text-slate-400 font-bold border-b border-slate-700 pb-1">
                                <span className="flex-1">Batter</span>
                                <span className="w-7 text-right">R</span>
                                <span className="w-7 text-right">B</span>
                                <span className="w-6 text-right">4s</span>
                                <span className="w-6 text-right">6s</span>
                                <span className="w-10 text-right">SR</span>
                            </div>
                            {state.batting_card.map((bc: BatCard) => (
                                <div
                                    key={bc.name}
                                    className={`flex gap-1 items-center rounded p-1.5 ${bc.name === state.striker
                                        ? 'bg-yellow-500/20 text-yellow-300 font-bold border border-yellow-500/30'
                                        : bc.is_out
                                            ? 'text-slate-500 line-through'
                                            : 'text-slate-300'
                                        }`}
                                >
                                    <span className="flex-1 truncate text-white">
                                        {bc.name}{bc.name === state.striker ? ' *' : ''}
                                    </span>
                                    <span className="w-7 text-right font-bold text-orange-300">{bc.runs}</span>
                                    <span className="w-7 text-right">{bc.balls}</span>
                                    <span className="w-6 text-right text-green-400">{bc.fours}</span>
                                    <span className="w-6 text-right text-yellow-400">{bc.sixes}</span>
                                    <span className="w-10 text-right text-cyan-300">{bc.sr}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Bowling Card */}
                    <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-4 shadow-2xl flex-1">
                        <h4 className="font-bold text-base mb-2 text-purple-400 flex items-center gap-2">
                            <span>Bowling</span>
                        </h4>
                        <div className="space-y-1 font-mono text-xs">
                            <div className="flex justify-between text-slate-400 font-bold border-b border-slate-700 pb-1">
                                <span className="w-24">Bowler</span>
                                <span className="w-10 text-right">O</span>
                                <span className="w-8 text-right">R</span>
                                <span className="w-8 text-right">W</span>
                                <span className="w-10 text-right">Econ</span>
                            </div>
                            {state.bowling_card.map((bw: BowlCard) => (
                                <div
                                    key={bw.name}
                                    className={`flex justify-between rounded p-1.5 ${bw.name === state.bowler
                                        ? 'bg-purple-500/20 text-purple-300 font-bold border border-purple-500/30'
                                        : 'text-slate-300'
                                        }`}
                                >
                                    <span className="w-24 truncate text-white">
                                        {bw.name}{bw.name === state.bowler ? ' *' : ''}
                                    </span>
                                    <span className="w-10 text-right">{bw.overs}</span>
                                    <span className="w-8 text-right">{bw.runs}</span>
                                    <span className="w-8 text-right font-bold text-purple-400">{bw.wickets}</span>
                                    <span className="w-10 text-right text-cyan-300">{bw.econ}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    {tournament?.standings?.length ? (
                        <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-4 shadow-2xl">
                            <div className="flex items-center justify-between mb-2">
                                <h4 className="font-bold text-base text-yellow-400 flex items-center gap-2">
                                    <span>Standings</span>
                                </h4>
                                <span className="text-[10px] uppercase tracking-wider text-slate-400">{tournament.phase}</span>
                            </div>
                            <div className="space-y-1 text-xs font-mono">
                                {tournament.standings.slice(0, 6).map((s, i) => (
                                    <div key={s.player} className="flex justify-between rounded p-1.5 bg-slate-800/30">
                                        <span className="w-5 text-slate-500">{i + 1}</span>
                                        <span className="flex-1 truncate text-slate-200">{s.player}</span>
                                        <span className="w-8 text-center text-slate-300">{s.played}</span>
                                        <span className="w-8 text-center text-green-400 font-bold">{s.won}</span>
                                        <span className="w-8 text-center text-red-400">{s.lost}</span>
                                        <span className="w-10 text-center text-yellow-400 font-bold">{s.points}</span>
                                        <span className="w-14 text-right text-cyan-300">
                                            {s.nrr >= 0 ? '+' : ''}{s.nrr.toFixed(2)}
                                        </span>
                                    </div>
                                ))}
                            </div>

                            {tournament.upcoming_matches?.length ? (
                                <div className="mt-3 border-t border-slate-700/60 pt-3">
                                    <h5 className="text-xs font-bold text-blue-300 uppercase tracking-wider mb-2">Upcoming</h5>
                                    <div className="space-y-1 text-xs text-slate-300">
                                        {tournament.upcoming_matches.slice(0, 5).map((m, idx) => (
                                            <div key={`${m.label}-${idx}`} className="flex justify-between gap-2">
                                                <span className="text-slate-500 uppercase tracking-wider">{m.label}</span>
                                                <span className="flex-1 text-right">{m.teams?.length ? `${m.teams[0] ?? 'TBD'} vs ${m.teams[1] ?? 'TBD'}` : 'TBD'}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ) : null}
                        </div>
                    ) : null}
                </div>
            </div>
        </div>
    )
}
