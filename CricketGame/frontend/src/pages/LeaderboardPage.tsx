import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Trophy, Skull, BarChart3, TrendingUp, TrendingDown, Target, Zap, Award, AlertTriangle, Flame, Shield, Lock, Eye, Heart, Clock } from 'lucide-react'

const DISPLAY_FONT = { fontFamily: "'Anton', 'Bebas Neue', sans-serif" }
const API = (import.meta.env.VITE_API_BASE_URL ?? window.location.origin).replace(/\/$/, '')

// ── Types ────────────────────────────────────────────────────────

interface Entry {
    username: string
    matches_played: number
    matches_won: number
    matches_lost: number
    win_pct: number
    total_runs: number
    highest_score: number
    batting_avg: number
    strike_rate: number
    fours: number
    sixes: number
    boundaries: number
    fifties: number
    hundreds: number
    wickets_taken: number
    best_bowling: string
    bowling_avg: number | null
    economy: number | null
    potm_count: number
    tournaments_won: number
    tournaments_played: number
    ducks: number
    ducks_taken: number
    close_losses: number
    heavy_losses: number
    six_shower: number
    max_duck_streak: number
    total_balls: number
    not_out_pct: number
    miser_innings: number
    chasing_avg: number
    wickets_per_ball: number
    balls_per_dismissal: number
    finals_lost: number
}

type MainTab = 'leaderboard' | 'fame' | 'shame'
type BoardTab = 'overall' | 'batting' | 'bowling'

// ── Helpers ──────────────────────────────────────────────────────

const AVATAR_COLORS = [
    'bg-emerald-500', 'bg-blue-500', 'bg-violet-500',
    'bg-amber-500', 'bg-rose-500', 'bg-cyan-500', 'bg-indigo-500', 'bg-pink-500',
]

function Avatar({ name, size = 7 }: { name: string; size?: number }) {
    const color = AVATAR_COLORS[name.charCodeAt(0) % AVATAR_COLORS.length]
    const sz = `w-${size} h-${size}`
    const text = size <= 7 ? 'text-xs' : 'text-sm'
    return (
        <div className={`${sz} ${color} rounded-full flex items-center justify-center text-white ${text} font-bold uppercase shrink-0`}>
            {name[0]}
        </div>
    )
}

function RankBadge({ n }: { n: number }) {
    if (n === 1) return <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-amber-400 text-white text-[11px] font-black shadow-sm">1</span>
    if (n === 2) return <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-slate-300 text-slate-700 text-[11px] font-black shadow-sm">2</span>
    if (n === 3) return <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-amber-700/70 text-white text-[11px] font-black shadow-sm">3</span>
    return <span className="text-slate-500 text-xs font-bold w-6 text-center inline-block">{n}</span>
}

// ── Reusable ranked table ─────────────────────────────────────────

interface ColDef<T> {
    header: string
    key: keyof T | ((row: T) => string | number)
    align?: 'left' | 'right'
    bold?: boolean
    highlight?: string
    hide?: 'sm' | 'md' | 'lg'
}

function RankTable<T extends { username: string }>({
    title, icon, subtitle, accent,
    data, cols, currentUser, maxRows = 10,
}: {
    title: string
    icon: React.ReactNode
    subtitle: string
    accent: 'amber' | 'red'
    data: T[]
    cols: ColDef<T>[]
    currentUser: string
    maxRows?: number
}) {
    const rows = data.slice(0, maxRows)
    const accentBorder = accent === 'amber' ? 'border-amber-200 hover:border-amber-300' : 'border-red-200 hover:border-red-300'
    const accentIcon   = accent === 'amber' ? 'bg-amber-50 group-hover:bg-amber-100' : 'bg-red-50 group-hover:bg-red-100'
    const accentSub    = accent === 'amber' ? 'text-amber-600' : 'text-red-600'

    const getValue = (row: T, col: ColDef<T>) =>
        typeof col.key === 'function' ? col.key(row) : (row[col.key] as string | number)

    const hideClass = (hide?: 'sm' | 'md' | 'lg') => {
        if (hide === 'sm') return 'hidden sm:table-cell'
        if (hide === 'md') return 'hidden md:table-cell'
        if (hide === 'lg') return 'hidden lg:table-cell'
        return ''
    }

    return (
        <div className={`bg-white border ${accentBorder} rounded-2xl overflow-hidden transition-all group shadow-sm`}>
            <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-3">
                <div className={`w-10 h-10 ${accentIcon} rounded-xl flex items-center justify-center transition-colors shrink-0`}>
                    {icon}
                </div>
                <div>
                    <h3 className="text-lg text-slate-900 uppercase leading-none" style={DISPLAY_FONT}>{title}</h3>
                    <p className={`text-[10px] font-bold uppercase tracking-widest ${accentSub} mt-0.5`}>{subtitle}</p>
                </div>
            </div>

            {rows.length === 0 ? (
                <div className="py-8 text-center text-slate-400 text-sm">No data yet</div>
            ) : (
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="bg-slate-50 border-b border-slate-100">
                                <th className="text-left px-4 py-2.5 text-[9px] font-bold uppercase tracking-widest text-slate-400 w-10">#</th>
                                <th className="text-left px-4 py-2.5 text-[9px] font-bold uppercase tracking-widest text-slate-400">Player</th>
                                {cols.map(c => (
                                    <th key={String(c.header)} className={`text-right px-4 py-2.5 text-[9px] font-bold uppercase tracking-widest text-slate-400 ${hideClass(c.hide)}`}>
                                        {c.header}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {rows.map((row, i) => {
                                const isMe = row.username === currentUser
                                return (
                                    <tr key={row.username} className={isMe ? 'bg-emerald-50' : 'hover:bg-slate-50 transition-colors'}>
                                        <td className="px-4 py-2.5"><RankBadge n={i + 1} /></td>
                                        <td className="px-4 py-2.5">
                                            <div className="flex items-center gap-2">
                                                <Avatar name={row.username} />
                                                <span className={`font-semibold text-sm ${isMe ? 'text-emerald-600' : 'text-slate-700'}`}>
                                                    {row.username}
                                                </span>
                                                {isMe && <span className="text-[8px] font-bold uppercase tracking-widest bg-emerald-50 text-emerald-600 rounded-full px-1.5 py-0.5 border border-emerald-200">You</span>}
                                            </div>
                                        </td>
                                        {cols.map(c => (
                                            <td key={String(c.header)} className={`px-4 py-2.5 text-right font-mono text-sm ${c.bold ? 'font-bold text-slate-900' : 'text-slate-500'} ${c.highlight ?? ''} ${hideClass(c.hide)}`}>
                                                {getValue(row, c)}
                                            </td>
                                        ))}
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    )
}

// ── Page ─────────────────────────────────────────────────────────

interface LeaderboardPageProps { username: string }

export default function LeaderboardPage({ username }: LeaderboardPageProps) {
    const navigate = useNavigate()
    const [mainTab, setMainTab] = useState<MainTab>('leaderboard')
    const [boardTab, setBoardTab] = useState<BoardTab>('overall')
    const [data, setData] = useState<Entry[]>([])
    const [loading, setLoading] = useState(true)
    const [fetchError, setFetchError] = useState(false)

    useEffect(() => {
        fetch(`${API}/api/leaderboard?limit=100`)
            .then(r => { if (!r.ok) throw new Error(); return r.json() })
            .then(d => setData(d.leaderboard ?? []))
            .catch(() => setFetchError(true))
            .finally(() => setLoading(false))
    }, [])

    const overallSorted  = useMemo(() => [...data].sort((a, b) => b.matches_won - a.matches_won || b.win_pct - a.win_pct), [data])
    const battingSorted  = useMemo(() => [...data].sort((a, b) => b.total_runs - a.total_runs || b.highest_score - a.highest_score), [data])
    const bowlingSorted  = useMemo(() => [...data].sort((a, b) => b.wickets_taken - a.wickets_taken), [data])

    const ducksTaken     = useMemo(() => [...data].filter(e => e.ducks_taken > 0).sort((a, b) => b.ducks_taken - a.ducks_taken), [data])
    const boundariesSort = useMemo(() => [...data].filter(e => e.boundaries > 0).sort((a, b) => b.boundaries - a.boundaries), [data])
    const sixesSort      = useMemo(() => [...data].filter(e => e.sixes > 0).sort((a, b) => b.sixes - a.sixes), [data])
    const foursSort      = useMemo(() => [...data].filter(e => e.fours > 0).sort((a, b) => b.fours - a.fours), [data])
    const fiftiesSort    = useMemo(() => [...data].filter(e => e.fifties > 0).sort((a, b) => b.fifties - a.fifties || b.highest_score - a.highest_score), [data])
    const finisherSort   = useMemo(() => [...data].filter(e => e.chasing_avg > 0).sort((a, b) => b.chasing_avg - a.chasing_avg), [data])
    const wallSort       = useMemo(() => [...data].filter(e => e.not_out_pct > 0).sort((a, b) => b.not_out_pct - a.not_out_pct), [data])
    const miserSort      = useMemo(() => [...data].filter(e => e.miser_innings > 0).sort((a, b) => b.miser_innings - a.miser_innings), [data])
    const oracleSort     = useMemo(() => [...data].filter(e => e.wickets_per_ball > 0).sort((a, b) => b.wickets_per_ball - a.wickets_per_ball), [data])

    const eligible         = useMemo(() => data.filter(e => e.matches_played >= 3), [data])
    const ducksSort        = useMemo(() => [...data].filter(e => e.ducks > 0).sort((a, b) => b.ducks - a.ducks), [data])
    const closeSort        = useMemo(() => [...eligible].filter(e => e.close_losses > 0).sort((a, b) => b.close_losses - a.close_losses), [eligible])
    const heavySort        = useMemo(() => [...eligible].filter(e => e.heavy_losses > 0).sort((a, b) => b.heavy_losses - a.heavy_losses), [eligible])
    const sixShowerSort    = useMemo(() => [...data].filter(e => e.six_shower > 0).sort((a, b) => b.six_shower - a.six_shower), [data])
    const diamondDuckSort  = useMemo(() => [...data].filter(e => e.max_duck_streak >= 2).sort((a, b) => b.max_duck_streak - a.max_duck_streak), [data])
    const bridesmaidSort   = useMemo(() => [...data].filter(e => e.finals_lost > 0).sort((a, b) => b.finals_lost - a.finals_lost), [data])
    const walkingWktSort   = useMemo(() => [...data].filter(e => e.balls_per_dismissal > 0).sort((a, b) => a.balls_per_dismissal - b.balls_per_dismissal), [data])
    const stonewallerSort  = useMemo(() => [...data].filter(e => e.total_balls >= 30).sort((a, b) => a.strike_rate - b.strike_rate), [data])

    const TAB_LABELS: { id: MainTab; label: string; icon: React.ReactNode }[] = [
        { id: 'leaderboard', label: 'Leaderboard', icon: <BarChart3 size={15} /> },
        { id: 'fame',        label: 'Hall of Fame', icon: <Trophy size={15} /> },
        { id: 'shame',       label: 'Hall of Shame', icon: <Skull size={15} /> },
    ]

    return (
        <div className="min-h-dvh bg-slate-50 text-slate-900 flex flex-col">

            {/* ── NAVBAR ──────────────────────────────────────────── */}
            <nav className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-sm">
                <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center gap-3">
                    <button
                        onClick={() => navigate('/')}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 border border-slate-200 text-slate-600 hover:bg-slate-200 transition-all text-xs font-bold uppercase tracking-wide shrink-0"
                    >
                        <ArrowLeft size={13} />
                        <span className="hidden sm:block">Home</span>
                    </button>
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 bg-linear-to-br from-emerald-500 to-emerald-600 rounded-xl -rotate-6 flex items-center justify-center shadow-sm shadow-emerald-500/20">
                            <span className="text-base -rotate-6">🏏</span>
                        </div>
                        <span className="text-xl uppercase tracking-tight text-slate-900 hidden sm:block" style={DISPLAY_FONT}>
                            E <span className="text-emerald-600">Cricket</span>
                        </span>
                    </div>
                </div>
            </nav>

            <main className="flex-1 max-w-5xl mx-auto w-full px-4 sm:px-6 py-8">

                {/* ── PAGE HEADER ─────────────────────────────────── */}
                <div className="mb-8">
                    <p className="text-xs font-bold uppercase tracking-[0.25em] text-slate-400 mb-1">Tournament records</p>
                    <h1 className="text-6xl sm:text-8xl text-slate-900 uppercase leading-none" style={DISPLAY_FONT}>Stats</h1>
                </div>

                {/* ── MAIN TABS ───────────────────────────────────── */}
                <div className="flex gap-1 bg-slate-100 rounded-xl p-1 w-fit mb-8">
                    {TAB_LABELS.map(t => (
                        <button
                            key={t.id}
                            onClick={() => setMainTab(t.id)}
                            className={`flex items-center gap-1.5 px-4 sm:px-5 py-2 rounded-lg text-xs font-bold uppercase tracking-widest transition-all ${mainTab === t.id
                                ? 'bg-white text-slate-900 shadow-sm'
                                : 'text-slate-500 hover:text-slate-700'
                                }`}
                        >
                            {t.icon}
                            <span className="hidden sm:block">{t.label}</span>
                        </button>
                    ))}
                </div>

                {/* ── LOADING / ERROR ─────────────────────────────── */}
                {loading && (
                    <div className="py-24 text-center">
                        <div className="w-7 h-7 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin mx-auto mb-3" />
                        <p className="text-slate-500 text-sm">Loading stats...</p>
                    </div>
                )}
                {!loading && fetchError && (
                    <div className="py-24 text-center text-slate-500 text-sm">Could not load stats. Is the server running?</div>
                )}

                {!loading && !fetchError && (

                    <>
                        {/* ══════════════════════════════════════════
                            TAB: LEADERBOARD
                        ══════════════════════════════════════════ */}
                        {mainTab === 'leaderboard' && (
                            <div className="space-y-5">
                                {/* Sub-tabs */}
                                <div className="flex gap-1 bg-slate-100 rounded-xl p-1 w-fit">
                                    {(['overall', 'batting', 'bowling'] as BoardTab[]).map(t => (
                                        <button
                                            key={t}
                                            onClick={() => setBoardTab(t)}
                                            className={`px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-widest transition-all ${boardTab === t
                                                ? 'bg-white text-slate-900 shadow-sm'
                                                : 'text-slate-500 hover:text-slate-700'
                                                }`}
                                        >
                                            {t}
                                        </button>
                                    ))}
                                </div>

                                {/* ── OVERALL ── */}
                                {boardTab === 'overall' && (
                                    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
                                        <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
                                            <BarChart3 size={16} className="text-emerald-600" />
                                            <h3 className="text-lg text-slate-900 uppercase" style={DISPLAY_FONT}>Overall Rankings</h3>
                                            <span className="text-xs text-slate-400 ml-1">sorted by wins</span>
                                        </div>
                                        {overallSorted.length === 0 ? (
                                            <EmptyState />
                                        ) : (
                                            <div className="overflow-x-auto">
                                                <table className="w-full text-sm">
                                                    <thead>
                                                        <tr className="bg-slate-50 border-b border-slate-100">
                                                            <Th w="w-10">#</Th>
                                                            <Th align="left">Player</Th>
                                                            <Th>Wins</Th>
                                                            <Th>Losses</Th>
                                                            <Th>MP</Th>
                                                            <Th>Win %</Th>
                                                            <Th hide="sm">Tournaments</Th>
                                                            <Th hide="md">POTM</Th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="divide-y divide-slate-100">
                                                        {overallSorted.map((e, i) => (
                                                            <tr key={e.username} className={e.username === username ? 'bg-emerald-50' : 'hover:bg-slate-50 transition-colors'}>
                                                                <td className="px-4 py-3"><RankBadge n={i + 1} /></td>
                                                                <PlayerCell entry={e} currentUser={username} />
                                                                <td className="px-4 py-3 text-right font-mono font-bold text-emerald-700">{e.matches_won}</td>
                                                                <td className="px-4 py-3 text-right font-mono text-red-500">{e.matches_lost}</td>
                                                                <td className="px-4 py-3 text-right font-mono text-slate-600">{e.matches_played}</td>
                                                                <td className="px-4 py-3 text-right font-mono font-bold text-slate-900">{e.win_pct}%</td>
                                                                <td className="px-4 py-3 text-right font-mono text-slate-500 hidden sm:table-cell">{e.tournaments_won}/{e.tournaments_played}</td>
                                                                <td className="px-4 py-3 text-right font-mono text-amber-600 hidden md:table-cell">{e.potm_count}</td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* ── BATTING ── */}
                                {boardTab === 'batting' && (
                                    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
                                        <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
                                            <BarChart3 size={16} className="text-emerald-600" />
                                            <h3 className="text-lg text-slate-900 uppercase" style={DISPLAY_FONT}>Batting Rankings</h3>
                                            <span className="text-xs text-slate-400 ml-1">sorted by runs</span>
                                        </div>
                                        {battingSorted.length === 0 ? <EmptyState /> : (
                                            <div className="overflow-x-auto">
                                                <table className="w-full text-sm">
                                                    <thead>
                                                        <tr className="bg-slate-50 border-b border-slate-100">
                                                            <Th w="w-10">#</Th>
                                                            <Th align="left">Player</Th>
                                                            <Th>Runs</Th>
                                                            <Th>SR</Th>
                                                            <Th>Avg</Th>
                                                            <Th>HS</Th>
                                                            <Th hide="sm">50s</Th>
                                                            <Th hide="sm">100s</Th>
                                                            <Th hide="md">4s</Th>
                                                            <Th hide="md">6s</Th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="divide-y divide-slate-100">
                                                        {battingSorted.map((e, i) => (
                                                            <tr key={e.username} className={e.username === username ? 'bg-emerald-50' : 'hover:bg-slate-50 transition-colors'}>
                                                                <td className="px-4 py-3"><RankBadge n={i + 1} /></td>
                                                                <PlayerCell entry={e} currentUser={username} />
                                                                <td className="px-4 py-3 text-right font-mono font-bold text-slate-900">{e.total_runs}</td>
                                                                <td className="px-4 py-3 text-right font-mono font-bold text-emerald-700">{e.strike_rate}</td>
                                                                <td className="px-4 py-3 text-right font-mono text-slate-600">{e.batting_avg}</td>
                                                                <td className="px-4 py-3 text-right font-mono text-slate-600">{e.highest_score}</td>
                                                                <td className="px-4 py-3 text-right font-mono text-slate-500 hidden sm:table-cell">{e.fifties}</td>
                                                                <td className="px-4 py-3 text-right font-mono text-slate-500 hidden sm:table-cell">{e.hundreds}</td>
                                                                <td className="px-4 py-3 text-right font-mono text-slate-500 hidden md:table-cell">{e.fours}</td>
                                                                <td className="px-4 py-3 text-right font-mono text-slate-500 hidden md:table-cell">{e.sixes}</td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        )}
                                    </div>
                                )}

                                {/* ── BOWLING ── */}
                                {boardTab === 'bowling' && (
                                    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
                                        <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
                                            <Target size={16} className="text-emerald-600" />
                                            <h3 className="text-lg text-slate-900 uppercase" style={DISPLAY_FONT}>Bowling Rankings</h3>
                                            <span className="text-xs text-slate-400 ml-1">sorted by wickets</span>
                                        </div>
                                        {bowlingSorted.length === 0 ? <EmptyState /> : (
                                            <div className="overflow-x-auto">
                                                <table className="w-full text-sm">
                                                    <thead>
                                                        <tr className="bg-slate-50 border-b border-slate-100">
                                                            <Th w="w-10">#</Th>
                                                            <Th align="left">Player</Th>
                                                            <Th>Wickets</Th>
                                                            <Th>Economy</Th>
                                                            <Th>Avg</Th>
                                                            <Th hide="sm">Best</Th>
                                                            <Th hide="md">Ducks Taken</Th>
                                                        </tr>
                                                    </thead>
                                                    <tbody className="divide-y divide-slate-100">
                                                        {bowlingSorted.map((e, i) => (
                                                            <tr key={e.username} className={e.username === username ? 'bg-emerald-50' : 'hover:bg-slate-50 transition-colors'}>
                                                                <td className="px-4 py-3"><RankBadge n={i + 1} /></td>
                                                                <PlayerCell entry={e} currentUser={username} />
                                                                <td className="px-4 py-3 text-right font-mono font-bold text-slate-900">{e.wickets_taken}</td>
                                                                <td className="px-4 py-3 text-right font-mono font-bold text-emerald-700">{e.economy ?? '—'}</td>
                                                                <td className="px-4 py-3 text-right font-mono text-slate-600">{e.bowling_avg ?? '—'}</td>
                                                                <td className="px-4 py-3 text-right font-mono text-slate-600 hidden sm:table-cell">{e.best_bowling}</td>
                                                                <td className="px-4 py-3 text-right font-mono text-slate-500 hidden md:table-cell">{e.ducks_taken}</td>
                                                            </tr>
                                                        ))}
                                                    </tbody>
                                                </table>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}

                        {/* ══════════════════════════════════════════
                            TAB: HALL OF FAME
                        ══════════════════════════════════════════ */}
                        {mainTab === 'fame' && (
                            <div className="space-y-5">
                                <div className="flex items-center gap-2 mb-2">
                                    <Trophy size={18} className="text-amber-500" />
                                    <p className="text-xs text-slate-500 uppercase tracking-widest font-bold">All-time bests · min 1 match</p>
                                </div>

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">

                                    <RankTable
                                        title="Duck Specialist"
                                        icon={<Target size={18} className="text-amber-600" />}
                                        subtitle="Most duck wickets taken"
                                        accent="amber"
                                        data={ducksTaken}
                                        currentUser={username}
                                        cols={[
                                            { header: 'Ducks', key: 'ducks_taken', bold: true, highlight: 'text-amber-600' },
                                            { header: 'Wickets', key: 'wickets_taken', hide: 'sm' },
                                            { header: 'Econ', key: e => e.economy ?? '—', hide: 'md' },
                                        ]}
                                    />

                                    <RankTable
                                        title="Boundary Beast"
                                        icon={<Zap size={18} className="text-amber-600" />}
                                        subtitle="Most total boundaries (4s + 6s)"
                                        accent="amber"
                                        data={boundariesSort}
                                        currentUser={username}
                                        cols={[
                                            { header: 'Bdry', key: 'boundaries', bold: true, highlight: 'text-amber-600' },
                                            { header: '4s', key: 'fours', hide: 'sm' },
                                            { header: '6s', key: 'sixes', hide: 'sm' },
                                        ]}
                                    />

                                    <RankTable
                                        title="Maximum Machine"
                                        icon={<TrendingUp size={18} className="text-amber-600" />}
                                        subtitle="Most sixes hit"
                                        accent="amber"
                                        data={sixesSort}
                                        currentUser={username}
                                        cols={[
                                            { header: 'Sixes', key: 'sixes', bold: true, highlight: 'text-amber-600' },
                                            { header: 'Runs', key: 'total_runs', hide: 'sm' },
                                            { header: 'SR', key: 'strike_rate', hide: 'md' },
                                        ]}
                                    />

                                    <RankTable
                                        title="Four-Ever"
                                        icon={<BarChart3 size={18} className="text-amber-600" />}
                                        subtitle="Most fours hit"
                                        accent="amber"
                                        data={foursSort}
                                        currentUser={username}
                                        cols={[
                                            { header: 'Fours', key: 'fours', bold: true, highlight: 'text-amber-600' },
                                            { header: 'Runs', key: 'total_runs', hide: 'sm' },
                                            { header: 'SR', key: 'strike_rate', hide: 'md' },
                                        ]}
                                    />

                                    <RankTable
                                        title="The Fifty Club"
                                        icon={<Award size={18} className="text-amber-600" />}
                                        subtitle="Most half-centuries scored"
                                        accent="amber"
                                        data={fiftiesSort}
                                        currentUser={username}
                                        cols={[
                                            { header: '50s', key: 'fifties', bold: true, highlight: 'text-amber-600' },
                                            { header: '100s', key: 'hundreds', hide: 'sm' },
                                            { header: 'Runs', key: 'total_runs', hide: 'sm' },
                                            { header: 'Avg', key: 'batting_avg', hide: 'md' },
                                        ]}
                                    />

                                    <RankTable
                                        title="The Finisher"
                                        icon={<Flame size={18} className="text-amber-600" />}
                                        subtitle="Best batting average while chasing"
                                        accent="amber"
                                        data={finisherSort}
                                        currentUser={username}
                                        cols={[
                                            { header: 'Chase Avg', key: 'chasing_avg', bold: true, highlight: 'text-amber-600' },
                                            { header: 'Runs', key: 'total_runs', hide: 'sm' },
                                            { header: 'SR', key: 'strike_rate', hide: 'md' },
                                        ]}
                                    />

                                    <RankTable
                                        title="The Wall"
                                        icon={<Shield size={18} className="text-amber-600" />}
                                        subtitle="Highest % innings finished not out"
                                        accent="amber"
                                        data={wallSort}
                                        currentUser={username}
                                        cols={[
                                            { header: 'Not Out %', key: (e) => `${e.not_out_pct}%`, bold: true, highlight: 'text-amber-600' },
                                            { header: 'Runs', key: 'total_runs', hide: 'sm' },
                                            { header: 'Avg', key: 'batting_avg', hide: 'md' },
                                        ]}
                                    />

                                    <RankTable
                                        title="The Miser"
                                        icon={<Lock size={18} className="text-amber-600" />}
                                        subtitle="Most bowling spells with economy ≤ 8"
                                        accent="amber"
                                        data={miserSort}
                                        currentUser={username}
                                        cols={[
                                            { header: 'Spells', key: 'miser_innings', bold: true, highlight: 'text-amber-600' },
                                            { header: 'Wkts', key: 'wickets_taken', hide: 'sm' },
                                            { header: 'Econ', key: (e) => e.economy ?? '—', hide: 'md' },
                                        ]}
                                    />

                                    <RankTable
                                        title="The Oracle"
                                        icon={<Eye size={18} className="text-amber-600" />}
                                        subtitle="Best wickets per ball (min 6 wickets)"
                                        accent="amber"
                                        data={oracleSort}
                                        currentUser={username}
                                        cols={[
                                            { header: 'Wkt/Ball', key: (e) => e.wickets_per_ball.toFixed(3), bold: true, highlight: 'text-amber-600' },
                                            { header: 'Wickets', key: 'wickets_taken', hide: 'sm' },
                                            { header: 'Best', key: 'best_bowling', hide: 'md' },
                                        ]}
                                    />

                                </div>
                            </div>
                        )}

                        {/* ══════════════════════════════════════════
                            TAB: HALL OF SHAME
                        ══════════════════════════════════════════ */}
                        {mainTab === 'shame' && (
                            <div className="space-y-5">
                                <div className="flex items-center gap-2 mb-2">
                                    <Skull size={18} className="text-red-500" />
                                    <p className="text-xs text-slate-500 uppercase tracking-widest font-bold">The other kind of record · min 3 matches</p>
                                </div>

                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">

                                    <RankTable
                                        title="Duck Dynasty"
                                        icon={<AlertTriangle size={18} className="text-red-600" />}
                                        subtitle="Most times out for 0 — classic duck"
                                        accent="red"
                                        data={ducksSort}
                                        currentUser={username}
                                        cols={[
                                            { header: 'Ducks', key: 'ducks', bold: true, highlight: 'text-red-600' },
                                            { header: 'MP', key: 'matches_played', hide: 'sm' },
                                            { header: 'Avg', key: 'batting_avg', hide: 'md' },
                                        ]}
                                    />

                                    <RankTable
                                        title="Heartbreak Hotel"
                                        icon={<TrendingDown size={18} className="text-red-600" />}
                                        subtitle="Lost by less than 10 runs — so close"
                                        accent="red"
                                        data={closeSort}
                                        currentUser={username}
                                        cols={[
                                            { header: 'Close L', key: 'close_losses', bold: true, highlight: 'text-red-600' },
                                            { header: 'Total L', key: 'matches_lost', hide: 'sm' },
                                            { header: 'MP', key: 'matches_played', hide: 'md' },
                                        ]}
                                    />

                                    <RankTable
                                        title="Highway Robbery"
                                        icon={<TrendingDown size={18} className="text-red-600" />}
                                        subtitle="Defeated by more than 30 runs — thrashed"
                                        accent="red"
                                        data={heavySort}
                                        currentUser={username}
                                        cols={[
                                            { header: 'Thrashed', key: 'heavy_losses', bold: true, highlight: 'text-red-600' },
                                            { header: 'Total L', key: 'matches_lost', hide: 'sm' },
                                            { header: 'Win%', key: e => `${e.win_pct}%`, hide: 'md' },
                                        ]}
                                    />

                                    <RankTable
                                        title="The Pinata"
                                        icon={<Zap size={18} className="text-red-600" />}
                                        subtitle="Most innings where 3+ sixes were hit off them"
                                        accent="red"
                                        data={sixShowerSort}
                                        currentUser={username}
                                        cols={[
                                            { header: 'Times', key: 'six_shower', bold: true, highlight: 'text-red-600' },
                                            { header: 'Wkts', key: 'wickets_taken', hide: 'sm' },
                                            { header: 'Econ', key: e => e.economy ?? '—', hide: 'md' },
                                        ]}
                                    />

                                    <RankTable
                                        title="Diamond Duck"
                                        icon={<Skull size={18} className="text-red-600" />}
                                        subtitle="Longest streak of consecutive duck innings"
                                        accent="red"
                                        data={diamondDuckSort}
                                        currentUser={username}
                                        cols={[
                                            { header: 'Streak', key: 'max_duck_streak', bold: true, highlight: 'text-red-600' },
                                            { header: 'Total Ducks', key: 'ducks', hide: 'sm' },
                                            { header: 'Avg', key: 'batting_avg', hide: 'md' },
                                        ]}
                                    />

                                    <RankTable
                                        title="Always the Bridesmaid"
                                        icon={<Heart size={18} className="text-red-600" />}
                                        subtitle="Most tournament finals reached without winning"
                                        accent="red"
                                        data={bridesmaidSort}
                                        currentUser={username}
                                        cols={[
                                            { header: 'Finals Lost', key: 'finals_lost', bold: true, highlight: 'text-red-600' },
                                            { header: 'T Won', key: 'tournaments_won', hide: 'sm' },
                                            { header: 'Win%', key: e => `${e.win_pct}%`, hide: 'md' },
                                        ]}
                                    />

                                    <RankTable
                                        title="Walking Wicket"
                                        icon={<AlertTriangle size={18} className="text-red-600" />}
                                        subtitle="Fewest balls survived per dismissal (min 5 dismissals)"
                                        accent="red"
                                        data={walkingWktSort}
                                        currentUser={username}
                                        cols={[
                                            { header: 'Balls/Out', key: 'balls_per_dismissal', bold: true, highlight: 'text-red-600' },
                                            { header: 'Runs', key: 'total_runs', hide: 'sm' },
                                            { header: 'Avg', key: 'batting_avg', hide: 'md' },
                                        ]}
                                    />

                                    <RankTable
                                        title="The Stonewaller"
                                        icon={<Clock size={18} className="text-red-600" />}
                                        subtitle="Lowest batting strike rate (min 30 balls)"
                                        accent="red"
                                        data={stonewallerSort}
                                        currentUser={username}
                                        cols={[
                                            { header: 'SR', key: 'strike_rate', bold: true, highlight: 'text-red-600' },
                                            { header: 'Runs', key: 'total_runs', hide: 'sm' },
                                            { header: 'Balls', key: 'total_balls', hide: 'md' },
                                        ]}
                                    />

                                </div>
                            </div>
                        )}
                    </>
                )}

            </main>
        </div>
    )
}

// ── Tiny shared cells ─────────────────────────────────────────────

function Th({ children, align = 'right', w, hide }: {
    children: React.ReactNode
    align?: 'left' | 'right'
    w?: string
    hide?: 'sm' | 'md' | 'lg'
}) {
    const hideClass = hide === 'sm' ? 'hidden sm:table-cell' : hide === 'md' ? 'hidden md:table-cell' : hide === 'lg' ? 'hidden lg:table-cell' : ''
    return (
        <th className={`${align === 'left' ? 'text-left' : 'text-right'} px-4 py-3 text-[9px] font-bold uppercase tracking-widest text-slate-400 ${w ?? ''} ${hideClass}`}>
            {children}
        </th>
    )
}

function PlayerCell({ entry, currentUser }: { entry: Entry; currentUser: string }) {
    const isMe = entry.username === currentUser
    const COLORS = ['bg-emerald-500', 'bg-blue-500', 'bg-violet-500', 'bg-amber-500', 'bg-rose-500', 'bg-cyan-500', 'bg-indigo-500', 'bg-pink-500']
    const color = COLORS[entry.username.charCodeAt(0) % COLORS.length]
    return (
        <td className="px-4 py-3">
            <div className="flex items-center gap-2">
                <div className={`w-7 h-7 ${color} rounded-full flex items-center justify-center text-white text-xs font-bold uppercase shrink-0`}>
                    {entry.username[0]}
                </div>
                <span className={`font-semibold text-sm ${isMe ? 'text-emerald-600' : 'text-slate-700'}`}>{entry.username}</span>
                {isMe && <span className="text-[8px] font-bold uppercase tracking-widest bg-emerald-50 text-emerald-600 rounded-full px-1.5 py-0.5 border border-emerald-200 shrink-0">You</span>}
            </div>
        </td>
    )
}

function EmptyState() {
    return (
        <div className="py-12 text-center">
            <div className="w-10 h-10 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3">
                <BarChart3 size={18} className="text-slate-400" />
            </div>
            <p className="text-slate-500 font-bold text-sm uppercase tracking-widest">No data yet</p>
            <p className="text-slate-400 text-xs mt-1">Play some matches to fill the board!</p>
        </div>
    )
}
