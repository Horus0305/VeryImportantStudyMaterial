/**
 * MatchDetailPage — Full scorecard view accessible from profile / history.
 * Pro Sports / Editorial design matching the Stitch scorecard designs.
 *
 * PC:   12-col grid → 4-col sidebar (PotM + Match Info) + 8-col innings
 * Mobile: Single column, stacked layout
 */
import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { ArrowLeft } from 'lucide-react'

/* ─── Interfaces ─── */

interface BatCard {
    name: string; runs: number; balls: number; fours: number; sixes: number
    sr: number; dismissal: string; is_out: boolean
}
interface BowlCard {
    name: string; overs: string; runs: number; wickets: number; econ: number
}
interface ScorecardData {
    batting: BatCard[]; bowling: BowlCard[]
    total_runs: number; wickets: number; overs: string; target: number | null
}
interface PotmData {
    player: string; score: number; summary: string
    runs: number; balls: number; wickets: number; sr: number
    economy: number | null
}
interface MatchData {
    match_id: string; room_code: string; mode: string; timestamp: string
    side_a: string[]; side_b: string[]
    scorecard_1: ScorecardData; scorecard_2: ScorecardData
    result_text: string; winner: string | null
    potm: string | null; potm_stats: PotmData | null
    tournament_id: string | null
}

const API = (import.meta.env.VITE_API_BASE_URL ?? window.location.origin).replace(/\/$/, '')

export default function MatchDetailPage() {
    const { matchId } = useParams()
    const navigate = useNavigate()
    const [match, setMatch] = useState<MatchData | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')

    useEffect(() => {
        const fetchMatch = async () => {
            try {
                const res = await fetch(`${API}/api/match/${matchId}`)
                if (res.ok) {
                    setMatch(await res.json())
                } else {
                    setError('Match not found')
                }
            } catch {
                setError('Cannot connect to server')
            } finally {
                setLoading(false)
            }
        }
        fetchMatch()
    }, [matchId])

    if (loading) {
        return (
            <div className="min-h-screen bg-white flex items-center justify-center">
                <div className="inline-block h-10 w-10 animate-spin rounded-full border-4 border-solid border-emerald-500 border-r-transparent" />
            </div>
        )
    }

    if (error || !match) {
        return (
            <div className="min-h-screen bg-white flex flex-col items-center justify-center gap-4">
                <p className="text-red-600 text-xl">{error}</p>
                <Button onClick={() => navigate(-1)} variant="outline" className="bg-white border-slate-200 text-slate-600 hover:bg-slate-50">
                    ← Go Back
                </Button>
            </div>
        )
    }

    const battingTeam1 = match.side_a.join(', ')
    const battingTeam2 = match.side_b.join(', ')
    const resultText = match.result_text
    const resultParts = resultText.split(/(won)/i)
    const hasWonSplit = resultParts.length >= 3

    const dateStr = new Date(match.timestamp).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric'
    }).toUpperCase()

    return (
        <div className="min-h-screen bg-white text-slate-900 selection:bg-emerald-500 selection:text-white">
            {/* ─── Sticky Header ─── */}
            <nav className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-200">
                <div className="w-full px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-14">
                        <div className="flex items-center gap-4 md:gap-6">
                            <button
                                onClick={() => navigate(-1)}
                                className="flex items-center text-xs font-bold uppercase tracking-widest text-slate-500 hover:text-emerald-500 transition-colors group"
                            >
                                <ArrowLeft className="w-4 h-4 mr-2 group-hover:-translate-x-1 transition-transform" />
                                Back
                            </button>
                            <div className="h-5 w-px bg-slate-200 hidden sm:block" />
                            <h1
                                className="text-2xl uppercase tracking-wider text-slate-900 mt-0.5 hidden sm:block"
                                style={{ fontFamily: "'Bebas Neue', 'Teko', sans-serif" }}
                            >
                                Match Scorecard
                            </h1>
                        </div>
                        <div className="flex items-center gap-3">
                            <div className="px-3 py-1 bg-slate-100 rounded text-xs font-mono font-medium text-slate-500 uppercase tracking-tight">
                                Match ID: #{match.match_id.slice(0, 4)}
                            </div>
                            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide hidden sm:inline">
                                {dateStr}
                            </span>
                        </div>
                    </div>
                </div>
            </nav>

            <main className="w-full px-4 sm:px-6 lg:px-8 py-6 md:py-8">
                {/* ─── Hero Result Banner ─── */}
                <section className="relative overflow-hidden mb-8 h-[320px] md:h-[400px] flex items-end bg-slate-900 rounded-sm group">
                    <div className="absolute inset-0">
                        <img
                            alt="Match Action Background"
                            className="w-full h-full object-cover opacity-60 mix-blend-overlay group-hover:scale-105 transition-transform duration-1000"
                            src="https://lh3.googleusercontent.com/aida-public/AB6AXuCNm1cOrvI7AWq5pgPFjqlPLsdeLnOdrecqQTr_J5SFJ3l8JcOr-X5JYP_PvVQ8KK9R5s5mndBRzZQy2i0Mcn78rZ1oOFbasqfTNQvF03lyy8SfXrxDQ9uaWUei6ycT7FZQAxqkmsCgxfNOVNLdh_ld3LQ1CuS3Jdm-51lrdRrYgsEpD3W6yOKVFLbRLl8HSwDUuNpII-NEoSfryDiDhFgnqa_4-JGI4uUTAi0diWMcHkqFQPw15hjM_OKaA9joFglkTDp916DNV0s"
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-slate-900/40 to-transparent" />
                    </div>
                    <div className="absolute right-[-10%] top-[-20%] w-[60%] h-[120%] bg-blue-900 rounded-full blur-3xl opacity-20 pointer-events-none" />

                    <div className="relative z-10 p-6 md:p-10 w-full">
                        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 md:gap-6">
                            <div>
                                <div className="flex items-center gap-3 mb-3">
                                    <span className="bg-emerald-500 text-white text-[10px] font-bold uppercase tracking-[0.2em] px-2 py-0.5">Result</span>
                                    <span className="text-slate-300 text-xs font-mono uppercase tracking-wider">
                                        {match.mode === 'cpu' ? 'CPU Match' : match.mode === 'tournament' ? 'Tournament' : '1v1'}
                                    </span>
                                </div>
                                {hasWonSplit ? (
                                    <h2
                                        className="text-4xl md:text-6xl lg:text-7xl text-white uppercase leading-[0.9]"
                                        style={{ fontFamily: "'Bebas Neue', 'Teko', sans-serif" }}
                                    >
                                        {resultParts[0]}won<br />
                                        <span className="text-emerald-500">{resultParts.slice(2).join('')}</span>
                                    </h2>
                                ) : (
                                    <h2
                                        className="text-4xl md:text-6xl lg:text-7xl text-white uppercase leading-[0.9]"
                                        style={{ fontFamily: "'Bebas Neue', 'Teko', sans-serif" }}
                                    >
                                        {resultText}
                                    </h2>
                                )}
                            </div>

                            {/* Score Summary Card */}
                            {match.scorecard_1 && match.scorecard_2 && (
                                <div className="bg-white/10 backdrop-blur-sm border border-white/20 p-4 rounded min-w-[180px] md:min-w-[200px]">
                                    <div className="flex justify-between items-center border-b border-white/20 pb-2 mb-2">
                                        <span className="text-white font-bold uppercase tracking-wider text-sm">{battingTeam1}</span>
                                        <span className="text-emerald-400 font-mono font-bold text-lg">
                                            {match.scorecard_1.total_runs}/{match.scorecard_1.wickets}
                                        </span>
                                    </div>
                                    <div className="flex justify-between items-center text-slate-300">
                                        <span className="font-medium uppercase tracking-wider text-xs">{battingTeam2}</span>
                                        <span className="font-mono text-sm">{match.scorecard_2.total_runs}/{match.scorecard_2.wickets}</span>
                                    </div>
                                    <div className="mt-2 text-[10px] text-slate-400 uppercase tracking-widest text-right">
                                        {match.scorecard_1.overs} Overs
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </section>

                {/* ─── Content Grid ─── */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8">
                    {/* Left Sidebar */}
                    <div className="lg:col-span-4 space-y-6">
                        {/* Player of the Match */}
                        {match.potm_stats && (
                            <section className="bg-white border border-slate-200 overflow-hidden">
                                <div className="bg-slate-900 p-4 flex justify-between items-center">
                                    <h3
                                        className="text-white uppercase tracking-wider text-xl"
                                        style={{ fontFamily: "'Bebas Neue', 'Teko', sans-serif" }}
                                    >
                                        Player of the Match
                                    </h3>
                                    <span className="text-emerald-500 text-lg">★</span>
                                </div>
                                <div className="p-6 flex flex-col items-center text-center border-b border-slate-100">
                                    <div className="w-24 h-24 md:w-28 md:h-28 rounded-full bg-slate-100 mb-4 border-2 border-emerald-500 p-1 flex items-center justify-center">
                                        <div className="w-full h-full rounded-full bg-slate-200 flex items-center justify-center">
                                            <span className="text-3xl md:text-4xl font-bold text-slate-600">
                                                {match.potm_stats.player.charAt(0).toUpperCase()}
                                            </span>
                                        </div>
                                    </div>
                                    <h4 className="text-2xl font-bold text-slate-900">{match.potm_stats.player}</h4>
                                    <p className="text-sm text-slate-500 font-mono mt-1">{match.potm_stats.summary}</p>
                                </div>
                                <div className="grid grid-cols-3 divide-x divide-slate-100">
                                    <div className="p-4 text-center hover:bg-slate-50 transition-colors">
                                        <div className="text-xs text-slate-400 uppercase font-bold tracking-widest mb-1">Runs</div>
                                        <div className="text-2xl font-bold text-slate-900" style={{ fontFamily: "'Bebas Neue', 'Teko', sans-serif" }}>
                                            {match.potm_stats.runs}
                                        </div>
                                        <div className="text-[10px] text-slate-400">({match.potm_stats.balls})</div>
                                    </div>
                                    <div className="p-4 text-center hover:bg-slate-50 transition-colors">
                                        <div className="text-xs text-slate-400 uppercase font-bold tracking-widest mb-1">Wickets</div>
                                        <div className="text-2xl font-bold text-slate-900" style={{ fontFamily: "'Bebas Neue', 'Teko', sans-serif" }}>
                                            {match.potm_stats.wickets}
                                        </div>
                                    </div>
                                    <div className="p-4 text-center hover:bg-slate-50 transition-colors">
                                        <div className="text-xs text-slate-400 uppercase font-bold tracking-widest mb-1">SR</div>
                                        <div className="text-2xl font-bold text-emerald-500" style={{ fontFamily: "'Bebas Neue', 'Teko', sans-serif" }}>
                                            {Math.round(match.potm_stats.sr)}
                                        </div>
                                    </div>
                                </div>
                            </section>
                        )}

                        {/* Match Info */}
                        <section className="bg-slate-50 border border-slate-200 p-6">
                            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">Match Info</h4>
                            <div className="space-y-3">
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-slate-500">Teams</span>
                                    <span className="text-sm font-medium text-slate-900 text-right">{battingTeam1} vs {battingTeam2}</span>
                                </div>
                                {match.winner && (
                                    <div className="flex justify-between items-center">
                                        <span className="text-sm text-slate-500">Winner</span>
                                        <span className="text-sm font-medium text-emerald-600 text-right">{match.winner}</span>
                                    </div>
                                )}
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-slate-500">Date</span>
                                    <span className="text-sm font-medium text-slate-900 text-right">
                                        {new Date(match.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-slate-500">Mode</span>
                                    <span className="text-sm font-medium text-slate-900 text-right capitalize">{match.mode}</span>
                                </div>
                            </div>
                        </section>
                    </div>

                    {/* Right Content — Innings */}
                    <div className="lg:col-span-8 space-y-10">
                        {match.scorecard_1 && (
                            <InningsSection
                                innings={match.scorecard_1}
                                label={`${battingTeam1} Innings`}
                                teamInitial={battingTeam1.charAt(0).toUpperCase()}
                                initialBg="bg-orange-100 text-orange-600"
                                potmName={match.potm_stats?.player}
                            />
                        )}
                        {match.scorecard_2 && (
                            <InningsSection
                                innings={match.scorecard_2}
                                label={`${battingTeam2} Innings`}
                                teamInitial={battingTeam2.charAt(0).toUpperCase()}
                                initialBg="bg-slate-100 text-slate-600"
                                potmName={match.potm_stats?.player}
                            />
                        )}
                    </div>
                </div>

                {/* Footer */}
                <footer className="mt-16 border-t border-slate-200 pt-8 pb-6 text-center">
                    <div className="flex items-center justify-center gap-2 mb-4 opacity-50">
                        <span className="text-xl uppercase tracking-wider text-slate-400" style={{ fontFamily: "'Bebas Neue', 'Teko', sans-serif" }}>
                            Tournament Hub
                        </span>
                    </div>
                    <p className="text-slate-400 text-sm">© 2026 Tournament Edition. Official Digital Partner.</p>
                </footer>
            </main>
        </div>
    )
}

/* ─── Sub-components ─── */

function InningsSection({ innings, label, teamInitial, initialBg, potmName }: {
    innings: ScorecardData; label: string; teamInitial: string
    initialBg: string; potmName?: string
}) {
    return (
        <section>
            <div className="flex items-center justify-between mb-4 border-b-2 border-slate-900 pb-2">
                <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 ${initialBg} flex items-center justify-center font-bold rounded text-sm`}>
                        {teamInitial}
                    </div>
                    <h2
                        className="text-xl uppercase tracking-wide text-slate-900 mt-0.5"
                        style={{ fontFamily: "'Bebas Neue', 'Teko', sans-serif" }}
                    >
                        {label}
                    </h2>
                </div>
                <div className="text-right">
                    <span className="text-2xl font-bold text-slate-900" style={{ fontFamily: "'Bebas Neue', 'Teko', sans-serif" }}>
                        {innings.total_runs}/{innings.wickets}
                    </span>
                    <span className="text-sm text-slate-500 font-mono ml-2">({innings.overs} Ov)</span>
                </div>
            </div>

            {/* Batting */}
            <div className="mb-6 overflow-x-auto border border-slate-200 bg-white [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                <table className="w-full text-left text-sm min-w-[500px]">
                    <thead>
                        <tr className="bg-slate-50 text-xs font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200">
                            <th className="px-4 py-3">Batter</th>
                            <th className="px-4 py-3 text-left">Dismissal</th>
                            <th className="px-4 py-3 text-center">R</th>
                            <th className="px-4 py-3 text-center">B</th>
                            <th className="px-4 py-3 text-center">4s</th>
                            <th className="px-4 py-3 text-center">6s</th>
                            <th className="px-4 py-3 text-right">SR</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                        {innings.batting.map(b => (
                            <tr key={b.name} className="hover:bg-slate-50 transition-colors">
                                <td className="px-4 py-3 font-semibold text-slate-900 whitespace-nowrap">
                                    {b.name}
                                    {potmName && b.name === potmName && (
                                        <span className="inline-block ml-1.5 text-emerald-500 text-[10px] align-middle">★</span>
                                    )}
                                </td>
                                <td className="px-4 py-3 text-slate-500 text-xs">{b.dismissal}</td>
                                <td className={`px-4 py-3 text-center font-bold text-slate-900 ${b.runs >= 50 ? 'bg-emerald-50/50' : ''}`}>{b.runs}</td>
                                <td className="px-4 py-3 text-center font-mono text-slate-600">{b.balls}</td>
                                <td className="px-4 py-3 text-center font-mono text-slate-400">{b.fours}</td>
                                <td className="px-4 py-3 text-center font-mono text-slate-400">{b.sixes}</td>
                                <td className="px-4 py-3 text-right font-mono text-slate-900">{b.sr}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Bowling */}
            <div className="overflow-x-auto border border-slate-200 bg-white [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                <table className="w-full text-left text-sm min-w-[400px]">
                    <thead>
                        <tr className="bg-slate-50 text-xs font-bold uppercase tracking-wider text-slate-500 border-b border-slate-200">
                            <th className="px-4 py-3">Bowler</th>
                            <th className="px-4 py-3 text-center">O</th>
                            <th className="px-4 py-3 text-center">M</th>
                            <th className="px-4 py-3 text-center">R</th>
                            <th className="px-4 py-3 text-center text-emerald-500">W</th>
                            <th className="px-4 py-3 text-right">Econ</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                        {innings.bowling.map(b => (
                            <tr key={b.name} className="hover:bg-slate-50 transition-colors">
                                <td className="px-4 py-3 font-medium text-slate-900 whitespace-nowrap">
                                    {b.name}
                                    {potmName && b.name === potmName && (
                                        <span className="inline-block ml-1.5 text-emerald-500 text-[10px] align-middle">★</span>
                                    )}
                                </td>
                                <td className="px-4 py-3 text-center font-mono text-slate-600">{b.overs}</td>
                                <td className="px-4 py-3 text-center font-mono text-slate-400">0</td>
                                <td className="px-4 py-3 text-center font-mono text-slate-600">{b.runs}</td>
                                <td className="px-4 py-3 text-center font-bold text-emerald-500 bg-emerald-50/30">{b.wickets}</td>
                                <td className="px-4 py-3 text-right font-mono text-slate-900">{b.econ}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </section>
    )
}
