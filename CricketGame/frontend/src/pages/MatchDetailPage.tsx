/**
 * MatchDetailPage — Full scorecard view for a completed match.
 * Shows both innings scorecards side-by-side and Player of the Match.
 */
import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface BatCard {
    name: string; runs: number; balls: number; fours: number; sixes: number
    sr: number; dismissal: string; is_out: boolean
}

interface BowlCard {
    name: string; overs: string; runs: number; wickets: number; econ: number
}

interface Scorecard {
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
    scorecard_1: Scorecard; scorecard_2: Scorecard
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
            <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
                <div className="animate-pulse text-2xl text-orange-400 font-bold">Loading match...</div>
            </div>
        )
    }

    if (error || !match) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex flex-col items-center justify-center gap-4">
                <p className="text-red-400 text-xl">{error}</p>
                <Button onClick={() => navigate(-1)} className="bg-slate-700 hover:bg-slate-600">← Go Back</Button>
            </div>
        )
    }

    const modeLabel = match.mode === 'team' || match.mode === '2v2'
        ? 'Team Mode'
        : match.mode === 'tournament'
            ? 'Tournament'
            : match.mode === 'cpu'
                ? 'CPU'
                : '1v1'

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
                            Match Scorecard
                        </h1>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Badge className="bg-orange-500/20 text-orange-300 border-orange-500/30">
                            {modeLabel}
                        </Badge>
                        <Badge className="bg-slate-700/50 text-slate-300 border-slate-600/50 text-xs">
                            {match.match_id}
                        </Badge>
                    </div>
                </div>

                {/* Result Banner */}
                <div className="bg-gradient-to-r from-green-500/10 to-emerald-500/10 border border-green-500/30 rounded-2xl p-5 sm:p-6 mb-6 text-center">
                    <p className="text-xl sm:text-2xl font-bold text-green-300"> {match.result_text}</p>
                    <div className="flex flex-col sm:flex-row justify-center gap-2 sm:gap-6 mt-3 text-sm text-slate-400">
                        <span>{match.side_a.join(', ')} vs {match.side_b.join(', ')}</span>
                        <span>•</span>
                        <span>{new Date(match.timestamp).toLocaleDateString()}</span>
                    </div>
                </div>

                {/* Player of the Match Card */}
                {match.potm_stats && (
                    <div className="bg-gradient-to-r from-yellow-500/10 to-amber-500/10 border border-yellow-500/30 rounded-2xl p-5 sm:p-6 mb-6 flex flex-col lg:flex-row items-start lg:items-center gap-4 lg:gap-6">
                        <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-full bg-gradient-to-br from-yellow-400 to-amber-600 flex items-center justify-center text-2xl sm:text-3xl shadow-lg shadow-yellow-500/20">
                            
                        </div>
                        <div className="flex-1">
                            <div className="text-xs text-yellow-400 font-semibold uppercase tracking-wide mb-1">Player of the Match</div>
                            <div className="text-xl sm:text-2xl font-bold text-white">{match.potm_stats.player}</div>
                            <div className="text-sm text-yellow-300 mt-1">{match.potm_stats.summary}</div>
                        </div>
                        <div className="grid grid-cols-3 gap-3 text-center w-full lg:w-auto">
                            <StatBox label="Runs" value={match.potm_stats.runs} />
                            <StatBox label="Wickets" value={match.potm_stats.wickets} />
                            <StatBox label="SR" value={match.potm_stats.sr} />
                        </div>
                    </div>
                )}

                {/* Innings Scorecards */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {match.scorecard_1 && (
                        <InningsCard
                            innings={match.scorecard_1}
                            label="1st Innings"
                            battingTeam={match.side_a.join(', ')}
                        />
                    )}
                    {match.scorecard_2 && (
                        <InningsCard
                            innings={match.scorecard_2}
                            label="2nd Innings"
                            battingTeam={match.side_b.join(', ')}
                        />
                    )}
                </div>
            </div>
        </div>
    )
}

function StatBox({ label, value }: { label: string; value: number | string | null }) {
    return (
        <div className="bg-slate-800/50 rounded-xl p-3 border border-slate-700/50">
            <div className="text-lg font-bold text-white">{value ?? '-'}</div>
            <div className="text-[10px] text-slate-400 uppercase">{label}</div>
        </div>
    )
}

function InningsCard({ innings, label, battingTeam }: {
    innings: Scorecard; label: string; battingTeam: string
}) {
    return (
        <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                    <span className="text-xl"></span> {label}
                </h3>
                <div className="flex gap-2">
                    <Badge className="bg-blue-500/20 text-blue-300 border-blue-500/30 text-xs">
                        {battingTeam}
                    </Badge>
                    <Badge className="bg-green-500/20 text-green-300 border-green-500/30 font-bold">
                        {innings.total_runs}/{innings.wickets} ({innings.overs} ov)
                    </Badge>
                </div>
            </div>

            {/* Batting Table */}
            <div className="mb-4">
                <div className="text-xs text-slate-400 font-semibold uppercase tracking-wide mb-2">Batting</div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="text-xs text-slate-400 border-b border-slate-700/50">
                                <th className="text-left py-2 px-2">Batter</th>
                                <th className="text-center py-2 px-1">R</th>
                                <th className="text-center py-2 px-1">B</th>
                                <th className="text-center py-2 px-1">4s</th>
                                <th className="text-center py-2 px-1">6s</th>
                                <th className="text-center py-2 px-1">SR</th>
                                <th className="text-left py-2 px-2">Dismissal</th>
                            </tr>
                        </thead>
                        <tbody>
                            {innings.batting.map(b => (
                                <tr key={b.name} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                                    <td className="py-2 px-2 font-medium text-white">{b.name}</td>
                                    <td className={`text-center py-2 px-1 font-bold ${b.runs >= 50 ? 'text-yellow-400' : b.runs >= 30 ? 'text-green-400' : 'text-white'}`}>
                                        {b.runs}
                                    </td>
                                    <td className="text-center py-2 px-1 text-slate-300">{b.balls}</td>
                                    <td className="text-center py-2 px-1 text-blue-400">{b.fours}</td>
                                    <td className="text-center py-2 px-1 text-purple-400">{b.sixes}</td>
                                    <td className={`text-center py-2 px-1 ${b.sr > 150 ? 'text-green-400 font-bold' : 'text-slate-300'}`}>
                                        {b.sr}
                                    </td>
                                    <td className="py-2 px-2 text-xs text-slate-400">{b.dismissal}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Bowling Table */}
            <div>
                <div className="text-xs text-slate-400 font-semibold uppercase tracking-wide mb-2">Bowling</div>
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="text-xs text-slate-400 border-b border-slate-700/50">
                                <th className="text-left py-2 px-2">Bowler</th>
                                <th className="text-center py-2 px-1">O</th>
                                <th className="text-center py-2 px-1">R</th>
                                <th className="text-center py-2 px-1">W</th>
                                <th className="text-center py-2 px-1">Econ</th>
                            </tr>
                        </thead>
                        <tbody>
                            {innings.bowling.map(b => (
                                <tr key={b.name} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                                    <td className="py-2 px-2 font-medium text-white">{b.name}</td>
                                    <td className="text-center py-2 px-1 text-slate-300">{b.overs}</td>
                                    <td className="text-center py-2 px-1 text-slate-300">{b.runs}</td>
                                    <td className={`text-center py-2 px-1 font-bold ${b.wickets >= 3 ? 'text-red-400' : b.wickets >= 2 ? 'text-yellow-400' : 'text-white'}`}>
                                        {b.wickets}
                                    </td>
                                    <td className={`text-center py-2 px-1 ${b.econ < 6 ? 'text-green-400' : b.econ > 10 ? 'text-red-400' : 'text-slate-300'}`}>
                                        {b.econ}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    )
}
