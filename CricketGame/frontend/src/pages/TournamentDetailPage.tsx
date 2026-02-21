/**
 * TournamentDetailPage — Responsive tournament view.
 *
 * MOBILE (< lg): Tabbed view → STANDINGS | BRACKET | MATCHES
 * DESKTOP (lg+): Single continuous page → Honor Roll → Progression & Standings → Match Archive
 *
 * Design refs:
 *   PC:     TournamentDetail PC/code.html
 *   Mobile: TournamentDetail Mobile - {Standings, Brackets, Matches}
 */
import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { ArrowLeft, Trophy, ListOrdered, ChevronRight } from 'lucide-react'

/* ─── Interfaces ─── */

interface AwardStats {
    player: string
    runs?: number; wickets?: number; sr?: number
    average?: number; economy?: number; overs?: number
}
interface MatchSummary {
    match_id: string; mode: string; timestamp: string; end_timestamp?: string | null
    side_a: string[]; side_b: string[]
    result_text: string; winner: string | null
    potm: string | null; potm_stats: { summary: string } | null
    scorecard_1?: { total_runs: number; wickets: number; overs: string }
    scorecard_2?: { total_runs: number; wickets: number; overs: string }
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
const DISPLAY_FONT = { fontFamily: "'Anton', 'Bebas Neue', 'Teko', sans-serif" }

const INITIAL_COLORS = [
    { bg: 'bg-orange-100', text: 'text-orange-600', border: 'border-orange-200' },
    { bg: 'bg-purple-100', text: 'text-purple-600', border: 'border-purple-200' },
    { bg: 'bg-blue-100', text: 'text-blue-600', border: 'border-blue-200' },
    { bg: 'bg-indigo-100', text: 'text-indigo-600', border: 'border-indigo-200' },
    { bg: 'bg-pink-100', text: 'text-pink-600', border: 'border-pink-200' },
    { bg: 'bg-teal-100', text: 'text-teal-600', border: 'border-teal-200' },
]
function getPlayerColor(name: string, playerList: string[]) {
    const idx = playerList.indexOf(name)
    return INITIAL_COLORS[idx >= 0 ? idx % INITIAL_COLORS.length : 0]
}
function getInitials(name: string) {
    const parts = name.split(' ')
    return parts.length > 1 ? parts.map(p => p[0]).join('').toUpperCase().slice(0, 2) : name.charAt(0).toUpperCase()
}

type TabKey = 'standings' | 'bracket' | 'matches'

/* ═══════════════════════════════════════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════════════════════════════════════ */

export default function TournamentDetailPage() {
    const { tournamentId } = useParams()
    const navigate = useNavigate()
    const [data, setData] = useState<TournamentData | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [activeTab, setActiveTab] = useState<TabKey>('standings')

    useEffect(() => {
        const fetchTournament = async () => {
            try {
                const res = await fetch(`${API}/api/tournament/${tournamentId}`)
                if (res.ok) { setData(await res.json()) }
                else { setError('Tournament not found') }
            } catch { setError('Cannot connect to server') }
            finally { setLoading(false) }
        }
        fetchTournament()
    }, [tournamentId])

    if (loading) {
        return (
            <div className="min-h-screen bg-white flex items-center justify-center">
                <div className="inline-block h-10 w-10 animate-spin rounded-full border-4 border-solid border-emerald-500 border-r-transparent" />
            </div>
        )
    }
    if (error || !data) {
        return (
            <div className="min-h-screen bg-white flex flex-col items-center justify-center gap-4">
                <p className="text-red-600 text-xl">{error}</p>
                <Button onClick={() => navigate(-1)} variant="outline">← Go Back</Button>
            </div>
        )
    }

    // Build playoff match lookup
    const matchLookup: Record<string, MatchSummary> = {}
    const usedMatchIds = new Set<string>()
    const getMatchTime = (m: MatchSummary) => m.end_timestamp ?? m.timestamp

    if (data.playoff_bracket && data.matches) {
        const sortedMatches = [...data.matches].sort((a, b) =>
            new Date(getMatchTime(b)).getTime() - new Date(getMatchTime(a)).getTime()
        )
        for (const phase of ['final', 'qualifier_2', 'eliminator', 'qualifier_1']) {
            const bracket = data.playoff_bracket[phase]
            if (!bracket) continue
            const candidates = sortedMatches.filter(m =>
                ((m.side_a.includes(bracket[0]) && m.side_b.includes(bracket[1]))
                    || (m.side_a.includes(bracket[1]) && m.side_b.includes(bracket[0])))
                && !usedMatchIds.has(m.match_id)
            )
            if (candidates.length > 0) {
                matchLookup[phase] = candidates[0]
                usedMatchIds.add(candidates[0].match_id)
            }
        }
    }

    const dateStr = new Date(data.timestamp).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric'
    })

    const tabs: { key: TabKey; label: string }[] = [
        { key: 'standings', label: 'Standings' },
        { key: 'bracket', label: 'Bracket' },
        { key: 'matches', label: 'Matches' },
    ]

    const awards = buildAwards(data)
    const sortedMatches = [...data.matches].sort((a, b) =>
        new Date(getMatchTime(b)).getTime() - new Date(getMatchTime(a)).getTime()
    )

    return (
        <div className="min-h-screen bg-white text-slate-900 font-sans antialiased selection:bg-emerald-500 selection:text-white">
            {/* ─── Sticky Header ─── */}
            <nav className="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-slate-100">
                <div className="w-full px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-14 lg:h-16">
                        <div className="flex items-center gap-2 lg:gap-6">
                            <button onClick={() => navigate(-1)} className="flex items-center text-sm font-bold uppercase tracking-wider text-slate-900 hover:text-emerald-500 transition-colors">
                                <ArrowLeft className="w-4 h-4 mr-1" /> Back
                            </button>
                            <div className="h-6 w-px bg-slate-200 hidden lg:block" />
                            <span className="text-xl uppercase tracking-wider hidden lg:inline" style={DISPLAY_FONT}>Tournament Hub</span>
                            <h1 className="uppercase text-lg tracking-wide lg:hidden" style={DISPLAY_FONT}>Tournament Hub</h1>
                        </div>
                        <div className="flex items-center gap-2">
                            <span className="text-xs lg:text-sm font-semibold text-slate-400">{dateStr}</span>
                            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                        </div>
                    </div>
                </div>
            </nav>

            {/* ─── Hero Banner (shared mobile/desktop, mobile design style) ─── */}
            <div className="relative w-full overflow-hidden bg-slate-900">
                <div className="absolute inset-0">
                    <img
                        alt="Stadium Background"
                        className="w-full h-full object-cover opacity-40 mix-blend-luminosity group-hover:scale-105 transition-all duration-700"
                        src="https://lh3.googleusercontent.com/aida-public/AB6AXuCNm1cOrvI7AWq5pgPFjqlPLsdeLnOdrecqQTr_J5SFJ3l8JcOr-X5JYP_PvVQ8KK9R5s5mndBRzZQy2i0Mcn78rZ1oOFbasqfTNQvF03lyy8SfXrxDQ9uaWUei6ycT7FZQAxqkmsCgxfNOVNLdh_ld3LQ1CuS3Jdm-51lrdRrYgsEpD3W6yOKVFLbRLl8HSwDUuNpII-NEoSfryDiDhFgnqa_4-JGI4uUTAi0diWMcHkqFQPw15hjM_OKaA9joFglkTDp916DNV0s"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-slate-900/40 to-transparent" />
                </div>
                <div className="absolute -right-10 -top-10 opacity-20">
                    <img alt="Watermark" className="w-64 h-64 rounded-full"
                        src="https://lh3.googleusercontent.com/aida-public/AB6AXuAOZAH5cPYarTf36I2V9juy-qmEvZlzdJLSQDGIQS_yOEc0ZcgmAib6Xiz1bRQgcYmVSzXp3DQKqzPNeid5wq9MobjnWHFvM0blBiieNs3vFoeSAhRS3Jq2tjX0COu8ODkzIFh8us2ytGoxeuSPLtNm_wYc4FwwH2iQnoIas1QYABidwtlTzbOIt-NFUVq_5Pw4EZ4pjWRiBVKN1LPRByHYGi9ocThQUXxEA8toeWCXstt3Lj9aA7vam0Fy-yfL6jA5Mv45KlHOd7WU"
                    />
                </div>
                <div className="relative z-10 flex flex-col justify-end p-6 pb-8 lg:p-8 lg:p-16 min-h-[256px] lg:min-h-[400px]">
                    <div className="mb-4">
                        <span className="bg-emerald-500 text-white text-xs font-bold px-3 py-1 uppercase tracking-[0.2em]">
                            {data.champion ? 'Current Champion' : 'Tournament'}
                        </span>
                    </div>
                    <h2 className="text-6xl lg:text-9xl text-white uppercase tracking-tight leading-none mb-2" style={DISPLAY_FONT}>
                        {data.champion?.toUpperCase() ?? 'IN PROGRESS'}
                    </h2>
                    <p className="text-slate-300 text-sm lg:text-lg font-light tracking-wide max-w-2xl border-l-4 border-emerald-500 pl-3 lg:pl-4 mt-4">
                        {data.champion
                            ? 'Dominating the pitch with strategic brilliance and unmatched skill. The crown returns to the king.'
                            : `${data.players.length} players competing for the championship.`}
                    </p>
                </div>
            </div>

            {/* ═══════════════ MOBILE: Tabbed View ═══════════════ */}
            <div className="lg:hidden">
                {/* Sticky Tab Bar */}
                <div className="sticky top-[56px] z-40 bg-white shadow-sm border-b border-gray-200">
                    <div className="flex justify-between px-2">
                        {tabs.map(tab => (
                            <button
                                key={tab.key}
                                onClick={() => setActiveTab(tab.key)}
                                className={`flex-1 py-4 text-sm font-semibold uppercase tracking-wide border-b-2 transition-colors text-center ${activeTab === tab.key
                                    ? 'border-emerald-500 text-emerald-500'
                                    : 'border-transparent text-gray-500 hover:text-gray-700'
                                    }`}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </div>
                </div>
                {/* Tab Content */}
                <div className="p-4 space-y-6 pb-20">
                    {activeTab === 'standings' && <MobileStandingsTab data={data} awards={awards} />}
                    {activeTab === 'bracket' && (
                        <MobileBracketTab
                            bracket={data.playoff_bracket}
                            results={data.playoff_results}
                            matchLookup={matchLookup}
                            champion={data.champion}
                            onMatchClick={(id) => navigate(`/match/${id}`)}
                        />
                    )}
                    {activeTab === 'matches' && (
                        <MobileMatchesTab
                            matches={sortedMatches}
                            totalCount={data.matches.length}
                            players={data.players}
                            onMatchClick={(id) => navigate(`/match/${id}`)}
                        />
                    )}
                </div>
            </div>

            {/* ═══════════════ DESKTOP: Continuous Page ═══════════════ */}
            <main className="hidden lg:block w-full px-4 sm:px-6 lg:px-8 py-8 space-y-16">
                {/* Honor Roll — 6-col editorial grid */}
                <DesktopHonorRoll awards={awards} />

                {/* Progression & Standings — bracket + full table */}
                <DesktopProgressionStandings
                    data={data}
                    bracket={data.playoff_bracket}
                    results={data.playoff_results}
                    matchLookup={matchLookup}
                    onMatchClick={(id) => navigate(`/match/${id}`)}
                />

                {/* Match Archive — horizontal rows */}
                <DesktopMatchArchive
                    matches={sortedMatches}
                    totalCount={data.matches.length}
                    onMatchClick={(id) => navigate(`/match/${id}`)}
                />
            </main>

            {/* ─── Footer ─── */}
            <footer className="mt-20 border-t border-slate-200 pt-12 pb-8 text-center">
                <span className="text-xl uppercase tracking-wider text-slate-300" style={DISPLAY_FONT}>Tournament Hub</span>
                <p className="text-slate-400 text-sm mt-2">© 2026 Tournament Edition. All stats are subject to verification.</p>
            </footer>
        </div>
    )
}

/* ─── Helpers ─── */

interface Award { label: string; icon: string; player?: string; detail?: string }

function buildAwards(data: TournamentData): Award[] {
    return [
        { label: 'MVP', icon: '⭐', player: data.player_of_tournament?.player, detail: data.player_of_tournament ? `${data.player_of_tournament.runs ?? 0} R • ${data.player_of_tournament.wickets ?? 0} W` : undefined },
        { label: 'Orange Cap', icon: '🏏', player: data.orange_cap?.player, detail: data.orange_cap ? `${data.orange_cap.runs ?? 0} Runs` : undefined },
        { label: 'Purple Cap', icon: '🎯', player: data.purple_cap?.player, detail: data.purple_cap ? `${data.purple_cap.wickets ?? 0} Wickets` : undefined },
        { label: 'Strike Rate', icon: '⚡', player: data.best_strike_rate?.player, detail: data.best_strike_rate ? `${data.best_strike_rate.sr ?? 0} SR` : undefined },
        { label: 'Best Avg', icon: '📊', player: data.best_average?.player, detail: data.best_average ? `Avg ${data.best_average.average ?? 0}` : undefined },
        { label: 'Economy', icon: '🎯', player: data.best_economy?.player, detail: data.best_economy ? `Econ ${data.best_economy.economy ?? 0}` : undefined },
    ].filter(a => a.player)
}

/* ═══════════════════════════════════════════════════════════════
   DESKTOP COMPONENTS
   ═══════════════════════════════════════════════════════════════ */

function DesktopHonorRoll({ awards }: { awards: Award[] }) {
    if (awards.length === 0) return null
    return (
        <section>
            <div className="flex items-center gap-3 mb-6 border-b border-slate-100 pb-2">
                <Trophy className="w-5 h-5 text-emerald-500" />
                <h2 className="text-lg font-bold uppercase tracking-widest text-slate-900">Honor Roll</h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-px bg-slate-200 border border-slate-200">
                {awards.map(a => (
                    <div key={a.label} className="bg-white p-6 flex flex-col justify-between h-40 hover:bg-slate-50 transition-colors group">
                        <div className="flex justify-between items-start">
                            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">{a.label}</span>
                            <span className="text-2xl group-hover:scale-110 transition-transform">{a.icon}</span>
                        </div>
                        <div>
                            <div className="text-2xl font-bold text-slate-900 leading-tight">{a.player}</div>
                            {a.detail && <div className="text-xs text-slate-500 mt-1 font-mono">{a.detail}</div>}
                        </div>
                    </div>
                ))}
            </div>
        </section>
    )
}

function DesktopProgressionStandings({ data, bracket, results, matchLookup, onMatchClick }: {
    data: TournamentData
    bracket: Record<string, string[] | null>
    results: Record<string, string>
    matchLookup: Record<string, MatchSummary>
    onMatchClick: (id: string) => void
}) {
    const phases = [
        { key: 'qualifier_1', label: 'Qualifier 1', color: 'border-emerald-500' },
        { key: 'eliminator', label: 'Eliminator', color: 'border-slate-300' },
        { key: 'qualifier_2', label: 'Qualifier 2', color: 'border-emerald-500' },
        { key: 'final', label: 'The Final', color: '' },
    ]

    return (
        <section>
            <div className="flex items-center gap-3 mb-6 border-b border-slate-100 pb-2">
                <ListOrdered className="w-5 h-5 text-emerald-500" />
                <h2 className="text-lg font-bold uppercase tracking-widest text-slate-900">Progression & Standings</h2>
            </div>
            <div className="bg-white border border-slate-200">
                {/* Bracket Tree */}
                <div className="p-8 border-b border-slate-200 bg-slate-50/50">
                    <div className="relative w-full overflow-x-auto pb-4">
                        <div className="min-w-[800px] flex justify-between relative h-[320px] px-12">
                            {/* Left column: Q1 + Eliminator */}
                            <div className="flex flex-col justify-between z-10 w-64 h-full py-10">
                                {phases.slice(0, 2).map(phase => {
                                    const teams = bracket[phase.key]
                                    const winner = results[phase.key]
                                    const match = matchLookup[phase.key]
                                    return (
                                        <div
                                            key={phase.key}
                                            className={`bg-white border-l-4 ${phase.color} shadow-sm p-4 relative group ${match ? 'cursor-pointer hover:shadow-md' : ''}`}
                                            onClick={() => match && onMatchClick(match.match_id)}
                                        >
                                            <div className={`absolute -top-3 left-0 ${phase.key === 'qualifier_1' ? 'bg-slate-900' : 'bg-slate-400'} text-white text-[10px] font-bold px-2 py-0.5 uppercase tracking-wider`}>
                                                {phase.label}
                                            </div>
                                            {teams ? teams.map(t => (
                                                <div key={t} className={`flex justify-between items-center ${t === winner ? 'mb-2 font-bold text-slate-900' : 'text-slate-400 text-sm'}`}>
                                                    <span className={t === winner ? 'text-emerald-600' : ''}>{t}</span>
                                                    {t === winner
                                                        ? <span className="bg-emerald-500 text-white text-xs px-1.5 rounded">W</span>
                                                        : <span className="text-xs">L</span>
                                                    }
                                                </div>
                                            )) : <div className="text-slate-400 text-xs py-2">TBD</div>}
                                            {match?.result_text && (
                                                <div className="mt-2 text-[10px] text-slate-400 border-t border-slate-100 pt-1 font-mono">{match.result_text}</div>
                                            )}
                                        </div>
                                    )
                                })}
                            </div>

                            {/* Center: Q2 */}
                            <div className="flex flex-col justify-end z-10 w-64 h-full py-10 mx-8">
                                {(() => {
                                    const phase = phases[2]
                                    const teams = bracket[phase.key]
                                    const winner = results[phase.key]
                                    const match = matchLookup[phase.key]
                                    return (
                                        <div
                                            className={`bg-white border-l-4 ${phase.color} shadow-sm p-4 relative ${match ? 'cursor-pointer hover:shadow-md' : ''}`}
                                            onClick={() => match && onMatchClick(match.match_id)}
                                        >
                                            <div className="absolute -top-3 left-0 bg-slate-900 text-white text-[10px] font-bold px-2 py-0.5 uppercase tracking-wider">
                                                {phase.label}
                                            </div>
                                            {teams ? teams.map(t => (
                                                <div key={t} className={`flex justify-between items-center ${t === winner ? 'mb-2 font-bold text-slate-900' : 'text-slate-400 text-sm'}`}>
                                                    <span className={t === winner ? 'text-emerald-600' : ''}>{t}</span>
                                                    {t === winner
                                                        ? <span className="bg-emerald-500 text-white text-xs px-1.5 rounded">W</span>
                                                        : <span className="text-xs">L</span>
                                                    }
                                                </div>
                                            )) : <div className="text-slate-400 text-xs py-2">TBD</div>}
                                            {match?.result_text && (
                                                <div className="mt-2 text-[10px] text-slate-400 border-t border-slate-100 pt-1 font-mono">{match.result_text}</div>
                                            )}
                                        </div>
                                    )
                                })()}
                            </div>

                            {/* Right: Final */}
                            <div className="flex flex-col justify-center z-10 w-64 h-full py-10">
                                {(() => {
                                    const teams = bracket['final']
                                    const winner = results['final']
                                    const match = matchLookup['final']
                                    return (
                                        <div
                                            className={`bg-slate-900 border border-slate-800 shadow-lg p-5 relative scale-110 origin-left ${match ? 'cursor-pointer hover:shadow-xl' : ''}`}
                                            onClick={() => match && onMatchClick(match.match_id)}
                                        >
                                            <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-emerald-500 text-white text-[10px] font-bold px-3 py-0.5 uppercase tracking-widest shadow-lg">
                                                The Final
                                            </div>
                                            {teams ? (
                                                <>
                                                    {teams.map(t => (
                                                        <div key={t} className={`flex justify-between items-center ${t === winner ? 'font-bold text-white text-lg' : 'mb-3 text-slate-400 text-sm border-b border-slate-700 pb-3'}`}>
                                                            <div className="flex items-center gap-2">
                                                                <span>{t}</span>
                                                                {t === winner && <span className="text-emerald-500 text-sm">👑</span>}
                                                            </div>
                                                            {t === winner
                                                                ? <span className="bg-emerald-500 text-white text-xs px-1.5 py-0.5 rounded">W</span>
                                                                : <span className="text-xs">L</span>
                                                            }
                                                        </div>
                                                    ))}
                                                    <div className="mt-3 text-[10px] text-slate-500 border-t border-slate-700 pt-2 font-mono uppercase tracking-wide text-center">
                                                        New Champion
                                                    </div>
                                                </>
                                            ) : <div className="text-slate-400 text-xs py-4 text-center">TBD</div>}
                                        </div>
                                    )
                                })()}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Points Table */}
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="border-b border-slate-200 bg-white text-xs font-bold uppercase tracking-wider text-slate-400">
                                <th className="px-6 py-4 w-16">Pos</th>
                                <th className="px-6 py-4">Club</th>
                                <th className="px-4 py-4 text-center">P</th>
                                <th className="px-4 py-4 text-center">W</th>
                                <th className="px-4 py-4 text-center">L</th>
                                <th className="px-4 py-4 text-center text-emerald-500">Pts</th>
                                <th className="px-6 py-4 text-right">NRR</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 text-sm text-slate-700">
                            {data.standings.map((s, i) => {
                                const clr = getPlayerColor(s.player, data.players)
                                return (
                                    <tr key={s.player} className="hover:bg-slate-50 transition-colors group">
                                        <td className="px-6 py-4 text-slate-400 font-mono">{String(i + 1).padStart(2, '0')}</td>
                                        <td className="px-6 py-4 font-bold text-slate-900 flex items-center gap-3">
                                            <div className={`w-8 h-8 rounded ${clr.bg} flex items-center justify-center ${clr.text}`} style={DISPLAY_FONT}>
                                                {getInitials(s.player)}
                                            </div>
                                            {s.player}
                                        </td>
                                        <td className="px-4 py-4 text-center font-mono">{s.played}</td>
                                        <td className="px-4 py-4 text-center font-bold text-slate-900">{s.won}</td>
                                        <td className="px-4 py-4 text-center text-slate-400">{s.lost}</td>
                                        <td className="px-4 py-4 text-center font-bold text-emerald-500 text-base">{s.points}</td>
                                        <td className={`px-6 py-4 text-right font-mono ${s.nrr >= 0 ? 'text-emerald-600' : 'text-rose-500'}`}>
                                            {s.nrr > 0 ? '+' : ''}{s.nrr.toFixed(3)}
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>
    )
}

function DesktopMatchArchive({ matches, totalCount, onMatchClick }: {
    matches: MatchSummary[]; totalCount: number
    onMatchClick: (id: string) => void
}) {
    return (
        <section>
            <div className="flex items-center justify-between mb-8 border-b border-slate-100 pb-2">
                <div className="flex items-center gap-3">
                    <span className="text-emerald-500 text-xl">🏏</span>
                    <h2 className="text-lg font-bold uppercase tracking-widest text-slate-900">Match Archive</h2>
                </div>
                <span className="text-sm font-semibold text-slate-400">{totalCount} Matches</span>
            </div>
            <div className="space-y-4">
                {matches.map((m, i) => {
                    const matchNum = matches.length - i
                    const sideAName = m.side_a.join(', ')
                    const sideBName = m.side_b.join(', ')
                    const isWinnerA = m.winner && m.side_a.includes(m.winner)
                    return (
                        <div
                            key={m.match_id}
                            onClick={() => onMatchClick(m.match_id)}
                            className="group flex flex-col md:flex-row items-center bg-white border border-slate-200 hover:border-emerald-500 transition-colors p-0 md:h-24 cursor-pointer"
                        >
                            {/* Match number */}
                            <div className="flex-none w-full md:w-24 bg-slate-50 h-full flex flex-col justify-center items-center border-b md:border-b-0 md:border-r border-slate-200 p-2">
                                <span className="text-xs font-bold text-slate-400 uppercase">Match</span>
                                <span className="text-2xl text-slate-900" style={DISPLAY_FONT}>{String(matchNum).padStart(2, '0')}</span>
                            </div>
                            {/* Content */}
                            <div className="flex-grow p-4 md:px-6 flex flex-col md:flex-row items-center justify-between w-full">
                                {/* Teams */}
                                <div className="flex items-center gap-8 w-full md:w-1/3 justify-center md:justify-start">
                                    <div className="text-right">
                                        <span className={`block font-bold text-lg ${isWinnerA ? 'text-slate-900' : 'text-slate-400'}`}>{sideAName}</span>
                                        {isWinnerA && <span className="block text-xs font-mono text-emerald-500">Winner</span>}
                                    </div>
                                    <span className="text-slate-300 text-xl" style={DISPLAY_FONT}>VS</span>
                                    <div className="text-left">
                                        <span className={`block font-bold text-lg ${!isWinnerA && m.winner ? 'text-slate-900' : 'text-slate-400'}`}>{sideBName}</span>
                                        {!isWinnerA && m.winner && <span className="block text-xs font-mono text-emerald-500">Winner</span>}
                                    </div>
                                </div>
                                {/* Result */}
                                <div className="my-4 md:my-0">
                                    <span className="text-sm font-medium bg-emerald-50 text-emerald-700 px-3 py-1 rounded-full border border-emerald-100">
                                        {m.result_text}
                                    </span>
                                </div>
                                {/* PotM */}
                                <div className="w-full md:w-1/3 flex justify-center md:justify-end items-center gap-2 text-sm text-slate-500">
                                    {m.potm && (
                                        <div className="flex items-center gap-1">
                                            <span className="text-amber-500">⭐</span>
                                            <span className="font-medium text-slate-900">{m.potm}</span>
                                            <span className="text-xs text-slate-400">(Top Batter)</span>
                                        </div>
                                    )}
                                </div>
                            </div>
                            {/* Chevron */}
                            <div className="flex-none w-full md:w-12 h-8 md:h-full flex items-center justify-center bg-slate-50 group-hover:bg-emerald-500 transition-colors border-t md:border-t-0 md:border-l border-slate-200">
                                <ChevronRight className="w-5 h-5 text-slate-400 group-hover:text-white transition-colors" />
                            </div>
                        </div>
                    )
                })}
            </div>
        </section>
    )
}

/* ═══════════════════════════════════════════════════════════════
   MOBILE COMPONENTS
   ═══════════════════════════════════════════════════════════════ */

function MobileStandingsTab({ data, awards }: { data: TournamentData; awards: Award[] }) {
    return (
        <div className="space-y-8">
            {/* Honor Roll (horizontal scroll) */}
            {awards.length > 0 && (
                <section>
                    <div className="flex items-center gap-2 mb-4">
                        <Trophy className="w-4 h-4 text-emerald-500" />
                        <h3 className="font-bold text-sm tracking-widest uppercase text-gray-800">Honor Roll</h3>
                    </div>
                    <div className="flex gap-3 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden pb-2 -mx-4 px-4 snap-x">
                        {awards.map(a => (
                            <div key={a.label} className="min-w-[160px] snap-center bg-white border border-gray-100 p-4 rounded-lg shadow-sm">
                                <div className="flex justify-between items-start mb-2">
                                    <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">{a.label}</span>
                                    <span className="text-sm">{a.icon}</span>
                                </div>
                                <div className="font-bold text-lg leading-tight mb-1 text-gray-900">{a.player}</div>
                                {a.detail && <div className="text-xs text-gray-500 font-mono">{a.detail}</div>}
                            </div>
                        ))}
                    </div>
                </section>
            )}

            {/* Standings Table */}
            <section>
                <div className="flex items-center gap-2 mb-4">
                    <ListOrdered className="w-4 h-4 text-emerald-500" />
                    <h3 className="font-bold text-sm tracking-widest uppercase text-gray-800">Progression & Standings</h3>
                </div>
                <div className="bg-white rounded-lg border border-gray-200 overflow-hidden shadow-sm">
                    <table className="w-full text-xs sm:text-sm">
                        <thead className="bg-gray-50 text-gray-500 border-b border-gray-200">
                            <tr>
                                <th className="px-4 py-3 text-left font-medium w-10">#</th>
                                <th className="px-2 py-3 text-left font-medium">Club</th>
                                <th className="px-2 py-3 text-center font-medium w-10">P</th>
                                <th className="px-2 py-3 text-center font-medium w-10 text-emerald-500">PTS</th>
                                <th className="px-4 py-3 text-right font-medium w-16">NRR</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {data.standings.map((s, i) => {
                                const clr = getPlayerColor(s.player, data.players)
                                return (
                                    <tr key={s.player} className="hover:bg-gray-50 transition-colors">
                                        <td className="px-4 py-3 text-gray-400 font-mono">{String(i + 1).padStart(2, '0')}</td>
                                        <td className="px-2 py-3">
                                            <div className="flex items-center gap-2">
                                                <div className={`w-6 h-6 rounded ${clr.bg} ${clr.text} flex items-center justify-center text-[10px] font-bold`}>
                                                    {getInitials(s.player)}
                                                </div>
                                                <span className="font-semibold text-gray-900">{s.player}</span>
                                            </div>
                                        </td>
                                        <td className="px-2 py-3 text-center text-gray-600">{s.played}</td>
                                        <td className="px-2 py-3 text-center font-bold text-emerald-500">{s.points}</td>
                                        <td className={`px-4 py-3 text-right font-mono ${s.nrr >= 0 ? 'text-green-500' : 'text-red-400'}`}>
                                            {s.nrr > 0 ? '+' : ''}{s.nrr.toFixed(3)}
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            </section>
        </div>
    )
}

function MobileBracketTab({ bracket, results, matchLookup, champion, onMatchClick }: {
    bracket: Record<string, string[] | null>; results: Record<string, string>
    matchLookup: Record<string, MatchSummary>; champion: string | null
    onMatchClick: (id: string) => void
}) {
    if (!bracket) return <div className="text-gray-500 text-sm py-10 text-center">No playoff data</div>

    const phases = [
        { key: 'qualifier_1', label: 'Qualifier 1', badgeBg: 'bg-black' },
        { key: 'eliminator', label: 'Eliminator', badgeBg: 'bg-gray-500' },
        { key: 'qualifier_2', label: 'Qualifier 2', badgeBg: 'bg-black' },
        { key: 'final', label: 'The Final', badgeBg: 'bg-emerald-500' },
    ]

    return (
        <div className="space-y-0">
            {phases.map((phase, idx) => {
                const teams = bracket[phase.key]
                const winner = results[phase.key]
                const match = matchLookup[phase.key]
                const isFinal = phase.key === 'final'

                return (
                    <div key={phase.key} className={`relative pl-6 ${idx < phases.length - 1 ? 'border-l-2 border-gray-200' : 'border-l-2 border-transparent'} pb-8`}>
                        <span className={`absolute -left-[9px] top-0 w-4 h-4 rounded-full ${isFinal ? 'bg-emerald-500 animate-pulse' : 'bg-gray-200'} border-2 border-white`} />
                        <div className={`${phase.badgeBg} text-white text-[10px] font-bold uppercase py-1 px-2 inline-block rounded mb-2`}>
                            {phase.label}
                        </div>

                        {isFinal ? (
                            <div
                                className={`bg-gray-900 text-white rounded-lg shadow-lg overflow-hidden relative ${match ? 'cursor-pointer' : ''}`}
                                onClick={() => match && onMatchClick(match.match_id)}
                            >
                                <div className="p-4 relative z-10">
                                    {teams ? teams.map(t => (
                                        <div key={t} className={`flex justify-between items-center ${t === winner ? '' : 'mb-4 border-b border-gray-700 pb-3'}`}>
                                            <div className="flex items-center gap-2">
                                                <span className={t === winner ? 'font-bold text-xl' : 'text-gray-400'}>{t}</span>
                                                {t === winner && <span className="text-emerald-500 text-sm">👑</span>}
                                            </div>
                                            {t === winner
                                                ? <span className="bg-emerald-500 text-white text-xs w-6 h-6 flex items-center justify-center rounded font-bold">W</span>
                                                : <span className="text-gray-500 text-xs font-medium">L</span>
                                            }
                                        </div>
                                    )) : <div className="text-gray-400 text-xs py-2">TBD</div>}
                                </div>
                                {match?.result_text && (
                                    <div className="bg-emerald-500 py-2 text-center text-[10px] uppercase tracking-widest font-semibold text-white">
                                        {match.result_text}
                                    </div>
                                )}
                                {!match && champion && (
                                    <div className="bg-black/40 py-2 text-center text-[10px] uppercase tracking-widest font-semibold text-gray-400">
                                        New Champion
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div
                                className={`bg-white rounded-lg shadow-sm border border-gray-200 p-3 ${match ? 'cursor-pointer hover:shadow-md' : ''} transition-all`}
                                onClick={() => match && onMatchClick(match.match_id)}
                            >
                                {teams ? teams.map(t => (
                                    <div key={t} className={`flex justify-between items-center ${t !== winner && winner ? 'opacity-50' : ''} ${t === winner ? 'mb-2' : ''}`}>
                                        <span className={`${t === winner ? 'font-bold text-gray-900' : 'text-gray-500'}`}>{t}</span>
                                        {t === winner
                                            ? <span className="bg-emerald-500 text-white text-[10px] w-5 h-5 flex items-center justify-center rounded font-bold">W</span>
                                            : winner ? <span className="text-gray-400 text-xs font-medium">L</span> : null
                                        }
                                    </div>
                                )) : <div className="text-gray-400 text-[10px] py-2">TBD</div>}
                                {match?.result_text && (
                                    <div className="mt-2 text-[10px] text-gray-400 border-t border-gray-100 pt-2">{match.result_text}</div>
                                )}
                            </div>
                        )}
                    </div>
                )
            })}
        </div>
    )
}

function MobileMatchesTab({ matches, totalCount, players, onMatchClick }: {
    matches: MatchSummary[]; totalCount: number; players: string[]
    onMatchClick: (id: string) => void
}) {
    const [search, setSearch] = useState('')
    const filtered = search
        ? matches.filter(m =>
            m.side_a.some(s => s.toLowerCase().includes(search.toLowerCase())) ||
            m.side_b.some(s => s.toLowerCase().includes(search.toLowerCase())) ||
            m.result_text.toLowerCase().includes(search.toLowerCase())
        )
        : matches

    return (
        <div className="space-y-4">
            {/* Search */}
            <div className="bg-white border border-gray-200 rounded-lg p-1.5 flex gap-2 shadow-sm">
                <div className="relative flex-1">
                    <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400 text-sm">🔍</span>
                    <input
                        className="w-full bg-gray-50 border-none rounded-md py-1.5 pl-8 pr-3 text-xs focus:ring-1 focus:ring-emerald-500 text-gray-900 placeholder-gray-400"
                        placeholder="Search team or player..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                    />
                </div>
            </div>

            {/* Match list */}
            <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
                <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
                    <h3 className="font-bold text-xs uppercase tracking-widest text-gray-500">Recent Results</h3>
                    <span className="text-[10px] font-medium bg-gray-200 text-gray-600 px-1.5 py-0.5 rounded">All {totalCount} Matches</span>
                </div>
                <div className="divide-y divide-gray-100">
                    {filtered.map((m) => {
                        const sideAName = m.side_a.join(', ')
                        const sideBName = m.side_b.join(', ')
                        const sideAClr = getPlayerColor(m.side_a[0], players)
                        const sideBClr = getPlayerColor(m.side_b[0], players)
                        const isWinnerA = m.winner && m.side_a.includes(m.winner)
                        const dateStr = new Date(m.end_timestamp ?? m.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
                        const matchNum = matches.length - matches.indexOf(m)

                        return (
                            <div key={m.match_id} className="p-4 hover:bg-gray-50 transition-colors cursor-pointer group" onClick={() => onMatchClick(m.match_id)}>
                                <div className="flex justify-between items-start mb-3">
                                    <span className="text-[10px] font-mono text-gray-400">Match {matchNum} • {dateStr}</span>
                                </div>
                                <div className="flex items-center justify-between gap-4">
                                    <div className="flex-1 flex flex-col items-start gap-1">
                                        <div className="flex items-center gap-2">
                                            <div className={`w-8 h-8 rounded-full ${sideAClr.bg} flex items-center justify-center ${sideAClr.text} font-bold text-xs border ${sideAClr.border}`}>
                                                {getInitials(m.side_a[0])}
                                            </div>
                                            <span className={`text-sm ${isWinnerA ? 'font-bold text-gray-900' : 'font-semibold text-gray-500'}`}>{sideAName}</span>
                                            {isWinnerA && <span className="text-emerald-500 text-sm">✅</span>}
                                        </div>
                                    </div>
                                    <div className="text-gray-300 text-xs font-bold">vs</div>
                                    <div className="flex-1 flex flex-col items-end gap-1">
                                        <div className="flex items-center gap-2 flex-row-reverse">
                                            <div className={`w-8 h-8 rounded-full ${sideBClr.bg} flex items-center justify-center ${sideBClr.text} font-bold text-xs border ${sideBClr.border}`}>
                                                {getInitials(m.side_b[0])}
                                            </div>
                                            <span className={`text-sm ${!isWinnerA && m.winner ? 'font-bold text-gray-900' : 'font-semibold text-gray-500'}`}>{sideBName}</span>
                                            {!isWinnerA && m.winner && <span className="text-emerald-500 text-sm">✅</span>}
                                        </div>
                                    </div>
                                </div>
                                <div className="mt-3 pt-3 border-t border-gray-50 flex justify-between items-center">
                                    <p className="text-xs text-emerald-500 font-medium">{m.result_text}</p>
                                    <ChevronRight className="w-4 h-4 text-gray-300 group-hover:translate-x-1 transition-transform" />
                                </div>
                            </div>
                        )
                    })}
                </div>
            </div>
        </div>
    )
}
