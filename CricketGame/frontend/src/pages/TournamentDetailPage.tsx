/**
 * TournamentDetailPage — Full tournament view with:
 *   1. Awards section (PotT, Orange Cap, Purple Cap, etc.)
 *   2. IPL-style playoff bracket (clickable match nodes)
 *   3. Points table
 *   4. All match scorecards (clickable)
 */
import { useEffect, useState, useRef, forwardRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface AwardStats {
    player: string
    runs?: number
    wickets?: number
    sr?: number
    average?: number
    economy?: number
    overs?: number
}

interface MatchSummary {
    match_id: string; mode: string; timestamp: string; end_timestamp?: string | null
    side_a: string[]; side_b: string[]
    result_text: string; winner: string | null
    potm: string | null; potm_stats: { summary: string } | null
}

interface StandingsEntry {
    player: string; played: number; won: number; lost: number
    tied: number; points: number; nrr: number
}

interface TournamentData {
    tournament_id: string; room_code: string; timestamp: string
    players: string[]; standings: StandingsEntry[]
    playoff_bracket: Record<string, string[] | null>
    playoff_results: Record<string, string>
    match_ids: string[]; champion: string | null
    orange_cap: AwardStats | null; purple_cap: AwardStats | null
    best_strike_rate: AwardStats | null; best_average: AwardStats | null
    best_economy: AwardStats | null; player_of_tournament: AwardStats | null
    matches: MatchSummary[]
}

const API = (import.meta.env.VITE_API_BASE_URL ?? window.location.origin).replace(/\/$/, '')

export default function TournamentDetailPage() {
    const { tournamentId } = useParams()
    const navigate = useNavigate()
    const [data, setData] = useState<TournamentData | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')

    useEffect(() => {
        const fetchTournament = async () => {
            try {
                const res = await fetch(`${API}/api/tournament/${tournamentId}`)
                if (res.ok) {
                    setData(await res.json())
                } else {
                    setError('Tournament not found')
                }
            } catch {
                setError('Cannot connect to server')
            } finally {
                setLoading(false)
            }
        }
        fetchTournament()
    }, [tournamentId])

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
                <div className="animate-pulse text-2xl text-orange-400 font-bold">Loading tournament...</div>
            </div>
        )
    }

    if (error || !data) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex flex-col items-center justify-center gap-4">
                <p className="text-red-400 text-xl">{error}</p>
                <Button onClick={() => navigate(-1)} className="bg-slate-700 hover:bg-slate-600">← Go Back</Button>
            </div>
        )
    }

    // Build a match lookup for the playoff tree
    const matchLookup: Record<string, MatchSummary> = {}
    const usedMatchIds = new Set<string>()

    // Match the playoff bracket entries to actual matches by participants
    // Strategy: Iterate phases in REVERSE order (Final -> Q1) and pick the LATEST unused match
    // This handles cases where teams played in Group stage (earlier) or matched up twice (Q1 + Final)
    const getMatchTime = (match: MatchSummary) => match.end_timestamp ?? match.timestamp
    const formatIstTime = (dateStr: string) =>
        new Date(dateStr).toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit' })

    if (data.playoff_bracket && data.matches) {
        // Sort matches by newest first
        const sortedMatches = [...data.matches].sort((a, b) =>
            new Date(getMatchTime(b)).getTime() - new Date(getMatchTime(a)).getTime()
        )

        const reversePhases = ['final', 'qualifier_2', 'eliminator', 'qualifier_1']

        for (const phase of reversePhases) {
            const bracket = data.playoff_bracket[phase]
            if (!bracket) continue

            // Find all matches between these two participants
            const candidates = sortedMatches.filter(m =>
                ((m.side_a.includes(bracket[0]) && m.side_b.includes(bracket[1]))
                    || (m.side_a.includes(bracket[1]) && m.side_b.includes(bracket[0])))
                && !usedMatchIds.has(m.match_id)
            )

            if (candidates.length > 0) {
                // Pick the most recent one (candidates[0])
                const bestMatch = candidates[0]
                matchLookup[phase] = bestMatch
                usedMatchIds.add(bestMatch.match_id)
            }
        }
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white p-4 sm:p-6">
            <div className="w-full mx-auto px-4 md:px-8">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-6">
                    <div className="flex items-center gap-4">
                        <Button
                            variant="ghost" size="sm"
                            onClick={() => navigate(-1)}
                            className="text-blue-400 hover:text-blue-300 hover:bg-slate-800/50"
                        >
                            ← Back
                        </Button>
                        <div className="h-8 w-px bg-slate-700" />
                        <h1 className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-orange-400 to-pink-600 bg-clip-text text-transparent">
                             Tournament
                        </h1>
                    </div>
                    <Badge className="bg-slate-700/50 text-slate-300 border-slate-600/50 text-xs">
                        {new Date(data.timestamp).toLocaleDateString()}
                    </Badge>
                </div>

                {/* Champion Banner */}
                {data.champion && (
                    <div className="bg-gradient-to-r from-yellow-500/10 to-amber-500/10 border border-yellow-500/30 rounded-2xl p-6 mb-6 text-center shadow-[0_0_50px_-12px_rgba(234,179,8,0.2)]">
                        <div className="text-4xl mb-2 animate-bounce"></div>
                        <div className="text-xs text-yellow-400 font-semibold uppercase tracking-wide">Champion</div>
                        <div className="text-4xl font-black text-yellow-300 mt-2 uppercase tracking-wide drop-shadow-md">{data.champion}</div>
                    </div>
                )}

                {/* Awards Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
                    <AwardCard
                        icon="" label="Player of Tournament" color="from-yellow-500/20 to-amber-500/20" borderColor="border-yellow-500/40"
                        data={data.player_of_tournament}
                        detail={data.player_of_tournament && data.player_of_tournament.runs !== undefined && data.player_of_tournament.wickets !== undefined
                            ? `${data.player_of_tournament.runs} runs, ${data.player_of_tournament.wickets} wkts`
                            : undefined}
                    />
                    <AwardCard
                        icon="" label="Orange Cap" color="from-orange-500/20 to-red-500/20" borderColor="border-orange-500/40"
                        data={data.orange_cap}
                        detail={data.orange_cap && data.orange_cap.runs !== undefined && data.orange_cap.sr !== undefined
                            ? `${data.orange_cap.runs} runs (SR: ${data.orange_cap.sr})`
                            : undefined}
                    />
                    <AwardCard
                        icon="" label="Purple Cap" color="from-purple-500/20 to-violet-500/20" borderColor="border-purple-500/40"
                        data={data.purple_cap}
                        detail={data.purple_cap && data.purple_cap.wickets !== undefined && data.purple_cap.economy !== undefined
                            ? `${data.purple_cap.wickets} wickets (Econ: ${data.purple_cap.economy})`
                            : undefined}
                    />
                    <AwardCard
                        icon="" label="Best Strike Rate" color="from-cyan-500/20 to-blue-500/20" borderColor="border-cyan-500/40"
                        data={data.best_strike_rate}
                        detail={data.best_strike_rate && data.best_strike_rate.sr !== undefined && data.best_strike_rate.runs !== undefined
                            ? `SR: ${data.best_strike_rate.sr} (${data.best_strike_rate.runs} runs)`
                            : undefined}
                    />
                    <AwardCard
                        icon="" label="Best Average" color="from-green-500/20 to-emerald-500/20" borderColor="border-green-500/40"
                        data={data.best_average}
                        detail={data.best_average && data.best_average.average !== undefined && data.best_average.runs !== undefined
                            ? `Avg: ${data.best_average.average} (${data.best_average.runs} runs)`
                            : undefined}
                    />
                    <AwardCard
                        icon="" label="Best Economy" color="from-pink-500/20 to-rose-500/20" borderColor="border-pink-500/40"
                        data={data.best_economy}
                        detail={data.best_economy && data.best_economy.economy !== undefined && data.best_economy.overs !== undefined
                            ? `Econ: ${data.best_economy.economy} (${data.best_economy.overs} ov)`
                            : undefined}
                    />
                </div>

                {/* Playoff Bracket + Points Table side by side */}
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 sm:gap-8 mb-8">
                    {/* Playoff Bracket Tree */}
                    <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-6 shadow-2xl relative overflow-hidden group">
                        <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity pointer-events-none">
                        </div>
                        <h3 className="text-2xl font-bold text-white mb-8 flex items-center gap-3">
                            <span className="text-2xl"></span> Playoff Bracket
                        </h3>
                        <PlayoffTree
                            bracket={data.playoff_bracket}
                            results={data.playoff_results}
                            matchLookup={matchLookup}
                            onMatchClick={(matchId) => navigate(`/match/${matchId}`)}
                        />
                    </div>

                    {/* Points Table */}
                    <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5 sm:p-6 shadow-2xl">
                        <h3 className="text-xl sm:text-2xl font-bold text-white mb-6 flex items-center gap-3">
                            <span className="text-2xl"></span> Points Table
                        </h3>
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm sm:text-base min-w-[520px]">
                                <thead>
                                    <tr className="text-xs uppercase tracking-wider text-slate-400 border-b border-slate-700/50">
                                        <th className="text-left py-3 px-3">#</th>
                                        <th className="text-left py-3 px-3">Player</th>
                                        <th className="text-center py-3">P</th>
                                        <th className="text-center py-3">W</th>
                                        <th className="text-center py-3">L</th>
                                        <th className="text-center py-3">Pts</th>
                                        <th className="text-center py-3">NRR</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.standings.map((s, i) => (
                                        <tr key={s.player} className={`border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors ${i < 4 ? 'bg-gradient-to-r from-emerald-500/5 to-transparent' : ''}`}>
                                            <td className="py-3 px-3 text-slate-500 font-mono">{i + 1}</td>
                                            <td className={`py-3 px-3 font-semibold ${i === 0 ? 'text-yellow-300' : i < 4 ? 'text-emerald-300' : 'text-slate-200'}`}>
                                                {s.player} {i === 0 && ''} {i < 4 && i > 0 && ''}
                                            </td>
                                            <td className="text-center py-3 text-slate-300">{s.played}</td>
                                            <td className="text-center py-3 text-emerald-400 font-bold">{s.won}</td>
                                            <td className="text-center py-3 text-red-400">{s.lost}</td>
                                            <td className="text-center py-3 text-yellow-400 font-bold text-lg">{s.points}</td>
                                            <td className={`text-center py-3 font-mono text-sm ${s.nrr >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                                {s.nrr > 0 ? '+' : ''}{s.nrr}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                {/* All Matches List */}
                <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-6 shadow-2xl">
                    <h3 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                        <span className="text-2xl"></span> All Matches ({data.matches.length})
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                        {data.matches.map((m, i) => (
                            <button
                                key={m.match_id}
                                onClick={() => navigate(`/match/${m.match_id}`)}
                                className="text-left bg-slate-800/50 hover:bg-slate-700/50 rounded-xl p-5 border border-slate-700/50 hover:border-orange-500/30 transition-all group cursor-pointer relative overflow-hidden"
                            >
                                <div className="absolute top-0 right-0 w-20 h-20 bg-orange-500/5 rounded-full -mr-10 -mt-10 pointer-events-none group-hover:bg-orange-500/10 transition-colors"></div>
                                <div className="flex items-center justify-between mb-3 relative z-10">
                                    <Badge variant="outline" className="border-slate-600 text-slate-400 text-[10px] h-5">Match #{i + 1}</Badge>
                                    <span className="text-[10px] text-slate-600 font-mono">{formatIstTime(getMatchTime(m))}</span>
                                </div>
                                <div className="text-base font-bold text-white mb-2 relative z-10">
                                    {m.side_a.join(', ')} <span className="text-slate-500 text-xs font-normal">vs</span> {m.side_b.join(', ')}
                                </div>
                                <div className="text-sm text-emerald-400 font-medium truncate mb-2 relative z-10">{m.result_text}</div>
                                {m.potm && (
                                    <div className="text-xs text-yellow-400 flex items-center gap-1 relative z-10">
                                        <span></span> {m.potm}
                                    </div>
                                )}
                                <div className="absolute bottom-4 right-4 text-orange-400 opacity-0 group-hover:opacity-100 transition-all transform translate-x-4 group-hover:translate-x-0">
                                    →
                                </div>
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    )
}

/** Individual award card */
function AwardCard({ icon, label, color, borderColor, data, detail }: {
    icon: string; label: string; color: string; borderColor: string
    data: AwardStats | null; detail?: string
}) {
    return (
        <div className={`bg-gradient-to-br ${color} rounded-xl border ${borderColor} p-4 text-center hover:scale-105 transition-transform duration-300 shadow-lg`}>
            <div className="text-3xl mb-2 filter drop-shadow-sm">{icon}</div>
            <div className="text-[10px] text-slate-300 uppercase tracking-wider font-bold mb-1 opacity-80">{label}</div>
            {data ? (
                <>
                    <div className="text-base font-bold text-white truncate px-1">{data.player}</div>
                    {detail && <div className="text-[11px] text-slate-100/80 mt-1 font-mono">{detail}</div>}
                </>
            ) : (
                <div className="text-xs text-slate-400 py-1">TBD</div>
            )}
        </div>
    )
}

/** IPL-style playoff bracket tree with dynamic connector lines */
function PlayoffTree({ bracket, results, matchLookup, onMatchClick }: {
    bracket: Record<string, string[] | null>
    results: Record<string, string>
    matchLookup: Record<string, MatchSummary>
    onMatchClick: (matchId: string) => void
}) {
    const containerRef = useRef<HTMLDivElement>(null)
    const nodeRefs = useRef<Record<string, HTMLButtonElement | null>>({})
    const [paths, setPaths] = useState<{ d: string; color: string; width: number; opacity: number }[]>([])

    const phases = [
        { key: 'qualifier_1', label: 'Qualifier 1', position: 'top-left' },
        { key: 'eliminator', label: 'Eliminator', position: 'bottom-left' },
        { key: 'qualifier_2', label: 'Qualifier 2', position: 'center' },
        { key: 'final', label: 'Final', position: 'right' },
    ]

    const setNodeRef = (key: string) => (el: HTMLButtonElement | null) => {
        nodeRefs.current[key] = el
    }

    // Calculate connector paths from the actual DOM positions
    useEffect(() => {
        if (!bracket) return

        const calcPaths = () => {
            const container = containerRef.current
            if (!container) return

            const cRect = container.getBoundingClientRect()
            const getCenter = (key: string) => {
                const el = nodeRefs.current[key]
                if (!el) return null
                const r = el.getBoundingClientRect()
                return {
                    right: r.right - cRect.left,
                    left: r.left - cRect.left,
                    midY: r.top + r.height / 2 - cRect.top,
                }
            }

            const q1 = getCenter('qualifier_1')
            const elim = getCenter('eliminator')
            const q2 = getCenter('qualifier_2')
            const final_ = getCenter('final')

            if (!q1 || !elim || !q2 || !final_) return

            const newPaths: typeof paths = []

            // Helper for elbow connector
            const drawElbow = (x1: number, y1: number, x2: number, y2: number) => {
                const midX = (x1 + x2) / 2
                return `M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`
            }

            // Q1 winner → Final (top path)
            // Starts from Q1 right, goes to Final left
            newPaths.push({
                d: drawElbow(q1.right, q1.midY, final_.left, final_.midY - 20),
                color: '#22d3ee', width: 3, opacity: 0.6,
            })

            // Q1 loser → Q2
            newPaths.push({
                d: drawElbow(q1.right, q1.midY + 10, q2.left, q2.midY - 10),
                color: '#94a3b8', width: 2, opacity: 0.4,
            })

            // Eliminator winner → Q2
            newPaths.push({
                d: drawElbow(elim.right, elim.midY, q2.left, q2.midY + 10),
                color: '#22d3ee', width: 3, opacity: 0.6,
            })

            // Q2 winner → Final (bottom path)
            newPaths.push({
                d: drawElbow(q2.right, q2.midY, final_.left, final_.midY + 20),
                color: '#22d3ee', width: 3, opacity: 0.6,
            })

            setPaths(newPaths)
        }

        // Run on mount + after a short delay (for layoout paint)
        const timer = setTimeout(calcPaths, 100)
        window.addEventListener('resize', calcPaths)
        return () => {
            clearTimeout(timer)
            window.removeEventListener('resize', calcPaths)
        }
    }, [bracket, results])

    if (!bracket) return <div className="text-slate-500 text-sm">No playoff data</div>

    return (
        <div className="relative min-h-[320px] px-8" ref={containerRef}>
            {/* SVG connecting paths */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 0 }}>
                {paths.map((p, i) => (
                    <path
                        key={i}
                        d={p.d}
                        stroke={p.color}
                        strokeWidth={p.width}
                        fill="none"
                        strokeLinecap="round"
                        className="transition-all duration-500 ease-in-out"
                        style={{ filter: 'drop-shadow(0 0 2px rgba(34, 211, 238, 0.3))' }}
                    />
                ))}
            </svg>

            {/* Match Nodes positioned with CSS grid */}
            <div className="relative z-10 grid grid-cols-3 gap-12 items-center h-full" style={{ minHeight: '300px' }}>
                {/* Left column: Q1 + Eliminator */}
                <div className="flex flex-col justify-between gap-12 h-full py-4">
                    <BracketNode
                        ref={setNodeRef('qualifier_1')}
                        phase={phases[0]}
                        bracket={bracket}
                        results={results}
                        matchLookup={matchLookup}
                        onMatchClick={onMatchClick}
                    />
                    <BracketNode
                        ref={setNodeRef('eliminator')}
                        phase={phases[1]}
                        bracket={bracket}
                        results={results}
                        matchLookup={matchLookup}
                        onMatchClick={onMatchClick}
                    />
                </div>

                {/* Center column: Q2 */}
                <div className="flex flex-col justify-center h-full">
                    <div className="mt-24">
                        <BracketNode
                            ref={setNodeRef('qualifier_2')}
                            phase={phases[2]}
                            bracket={bracket}
                            results={results}
                            matchLookup={matchLookup}
                            onMatchClick={onMatchClick}
                        />
                    </div>
                </div>

                {/* Right column: Final */}
                <div className="flex flex-col justify-center h-full">
                    <BracketNode
                        ref={setNodeRef('final')}
                        phase={phases[3]}
                        bracket={bracket}
                        results={results}
                        matchLookup={matchLookup}
                        onMatchClick={onMatchClick}
                    />
                </div>
            </div>
        </div>
    )
}

/** A single bracket match node */
const BracketNode = forwardRef<HTMLButtonElement, {
    phase: { key: string; label: string }
    bracket: Record<string, string[] | null>
    results: Record<string, string>
    matchLookup: Record<string, MatchSummary>
    onMatchClick: (matchId: string) => void
}>(({ phase, bracket, results, matchLookup, onMatchClick }, ref) => {
    const teams = bracket[phase.key]
    const winner = results[phase.key]
    const match = matchLookup[phase.key]
    const isFinal = phase.key === 'final'

    return (
        <button
            ref={ref}
            onClick={() => match && onMatchClick(match.match_id)}
            disabled={!match}
            className={`w-full rounded-xl border p-3 text-left transition-all ${isFinal
                ? 'bg-gradient-to-br from-yellow-500/20 to-amber-500/20 border-yellow-500/40 hover:border-yellow-400/60 shadow-lg shadow-yellow-500/10'
                : 'bg-gradient-to-br from-blue-500/10 to-cyan-500/10 border-blue-500/30 hover:border-blue-400/50'
                } ${match ? 'cursor-pointer hover:scale-105' : 'cursor-default opacity-60'}`}
        >
            <div className="text-[9px] font-semibold uppercase tracking-wider mb-1.5"
                style={{ color: isFinal ? '#fbbf24' : '#60a5fa' }}>
                {phase.label}
            </div>
            {teams ? (
                <div className="space-y-1">
                    {teams.map(t => (
                        <div key={t} className={`text-xs font-medium px-2 py-1 rounded ${winner === t
                            ? 'bg-green-500/20 text-green-300 border border-green-500/30'
                            : 'bg-slate-800/50 text-slate-300'
                            }`}>
                            {winner === t && ' '}{t}
                        </div>
                    ))}
                </div>
            ) : (
                <div className="text-[10px] text-slate-500 py-2">TBD</div>
            )}
            {match?.result_text && (
                <div className="text-[9px] text-slate-400 mt-1.5 truncate">{match.result_text}</div>
            )}
        </button>
    )
})
BracketNode.displayName = 'BracketNode'
