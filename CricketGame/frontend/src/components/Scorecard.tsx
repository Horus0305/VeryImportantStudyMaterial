/**
 * Scorecard — Full match scorecard with batting and bowling tables.
 * Full-width layout fitting viewport.
 */
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

interface BatEntry {
    name: string; runs: number; balls: number; fours: number; sixes: number; sr: number; dismissal: string
}
interface BowlEntry {
    name: string; overs: string; runs: number; wickets: number; econ: number
}
interface InningsData {
    batting: BatEntry[]
    bowling: BowlEntry[]
    total_runs: number
    wickets: number
    overs: string
}
interface StandingsEntry {
    player: string; played: number; won: number; lost: number; tied: number; points: number; nrr: number
}
interface TournamentPayload {
    standings: StandingsEntry[]
    phase: string
    upcoming_matches?: Array<{ label: string; teams: string[] }>
}

interface Props {
    data: Record<string, unknown>
    onBack: () => void
}

function InningsCard({ title, innings }: { title: string; innings: InningsData }) {
    return (
        <Card className="border-slate-700/50 bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm shadow-2xl flex-1 flex flex-col min-h-0">
            <CardHeader className="pb-2 flex-shrink-0">
                <CardTitle className="text-base sm:text-lg font-bold text-white">
                    {title} — {innings.total_runs}/{innings.wickets} ({innings.overs} ov)
                </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col lg:flex-row gap-6 flex-1 min-h-0">
                {/* Batting Table */}
                <div className="flex-1 overflow-x-auto">
                    <h4 className="text-sm font-bold text-yellow-400 mb-2"> Batting</h4>
                    <table className="w-full text-xs font-mono min-w-[350px]">
                        <thead>
                            <tr className="border-b border-slate-700 text-slate-400">
                                <th className="text-left py-1.5 pr-3 font-bold">Batter</th>
                                <th className="text-right px-2 font-bold">R</th>
                                <th className="text-right px-2 font-bold">B</th>
                                <th className="text-right px-2 font-bold">4s</th>
                                <th className="text-right px-2 font-bold">6s</th>
                                <th className="text-right px-2 font-bold">SR</th>
                                <th className="text-left pl-3 font-bold">Dismissal</th>
                            </tr>
                        </thead>
                        <tbody>
                            {innings.batting.map(b => (
                                <tr key={b.name} className="border-b border-slate-700/50 hover:bg-slate-800/30">
                                    <td className="py-1.5 pr-3 font-semibold text-white">{b.name}</td>
                                    <td className="text-right px-2 font-bold text-orange-300">{b.runs}</td>
                                    <td className="text-right px-2 text-slate-300">{b.balls}</td>
                                    <td className="text-right px-2 text-green-400">{b.fours}</td>
                                    <td className="text-right px-2 text-yellow-400">{b.sixes}</td>
                                    <td className="text-right px-2 text-cyan-300">{b.sr.toFixed(1)}</td>
                                    <td className="text-left pl-3 text-slate-400">{b.dismissal}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {/* Bowling Table */}
                <div className="flex-1 overflow-x-auto">
                    <h4 className="text-sm font-bold text-blue-400 mb-2"> Bowling</h4>
                    <table className="w-full text-xs font-mono min-w-[300px]">
                        <thead>
                            <tr className="border-b border-slate-700 text-slate-400">
                                <th className="text-left py-1.5 pr-3 font-bold">Bowler</th>
                                <th className="text-right px-2 font-bold">O</th>
                                <th className="text-right px-2 font-bold">R</th>
                                <th className="text-right px-2 font-bold">W</th>
                                <th className="text-right px-2 font-bold">Econ</th>
                            </tr>
                        </thead>
                        <tbody>
                            {innings.bowling.map(bw => (
                                <tr key={bw.name} className="border-b border-slate-700/50 hover:bg-slate-800/30">
                                    <td className="py-1.5 pr-3 font-semibold text-white">{bw.name}</td>
                                    <td className="text-right px-2 text-slate-300">{bw.overs}</td>
                                    <td className="text-right px-2 text-slate-300">{bw.runs}</td>
                                    <td className="text-right px-2 font-bold text-purple-400">{bw.wickets}</td>
                                    <td className="text-right px-2 text-cyan-300">{bw.econ.toFixed(1)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </CardContent>
        </Card>
    )
}

export default function Scorecard({ data, onBack }: Props) {
    const resultText = data.result_text as string
    const scorecard1 = data.scorecard_1 as InningsData | undefined
    const scorecard2 = data.scorecard_2 as InningsData | undefined
    const tournament = data.tournament as TournamentPayload | undefined
    const standings = tournament?.standings ?? []
    const upcoming = tournament?.upcoming_matches ?? []

    return (
        <div className="w-full h-full flex flex-col px-4 sm:px-6 py-4 gap-4">
            {/* Header */}
            <div className="text-center flex-shrink-0">
                <h1 className="text-2xl sm:text-3xl font-black bg-gradient-to-r from-orange-400 via-pink-500 to-purple-500 bg-clip-text text-transparent">
                     Match Scorecard
                </h1>
                <p className="text-base sm:text-xl font-bold text-yellow-400 mt-1">{resultText}</p>
            </div>

            {/* Innings Cards — stacked or side-by-side */}
            <div className="flex-1 flex flex-col lg:flex-row gap-4 min-h-0">
                {scorecard1 && <InningsCard title="1st Innings" innings={scorecard1} />}
                {scorecard2 && <InningsCard title="2nd Innings" innings={scorecard2} />}
            </div>

            {standings.length > 0 && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <Card className="border-slate-700/50 bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm shadow-2xl">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-base sm:text-lg font-bold text-yellow-400 flex items-center gap-2">
                                 <span>Standings</span>
                                <span className="text-xs uppercase tracking-wider text-slate-400">{tournament?.phase}</span>
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="space-y-1 text-xs font-mono">
                                <div className="flex justify-between text-slate-400 font-bold border-b border-slate-700 pb-1">
                                    <span className="w-5">#</span>
                                    <span className="flex-1">Player</span>
                                    <span className="w-8 text-center">P</span>
                                    <span className="w-8 text-center">W</span>
                                    <span className="w-8 text-center">L</span>
                                    <span className="w-10 text-center">Pts</span>
                                </div>
                                {standings.map((s, i) => (
                                    <div key={s.player} className="flex justify-between rounded p-1.5 bg-slate-800/30">
                                        <span className="w-5 text-slate-500">{i + 1}</span>
                                        <span className="flex-1 truncate text-slate-200">{s.player}</span>
                                        <span className="w-8 text-center text-slate-300">{s.played}</span>
                                        <span className="w-8 text-center text-green-400 font-bold">{s.won}</span>
                                        <span className="w-8 text-center text-red-400">{s.lost}</span>
                                        <span className="w-10 text-center text-yellow-400 font-bold">{s.points}</span>
                                    </div>
                                ))}
                            </div>
                        </CardContent>
                    </Card>

                    <Card className="border-slate-700/50 bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm shadow-2xl">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-base sm:text-lg font-bold text-blue-300 flex items-center gap-2">
                                 <span>Upcoming Matches</span>
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            {upcoming.length ? (
                                <div className="space-y-2 text-sm text-slate-300">
                                    {upcoming.slice(0, 6).map((m, idx) => (
                                        <div key={`${m.label}-${idx}`} className="flex items-center justify-between gap-3 border-b border-slate-700/60 pb-2 last:border-0">
                                            <span className="text-xs uppercase tracking-wider text-slate-500">{m.label}</span>
                                            <span className="flex-1 text-right">{m.teams?.length ? `${m.teams[0] ?? 'TBD'} vs ${m.teams[1] ?? 'TBD'}` : 'TBD'}</span>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <div className="text-sm text-slate-500">No upcoming matches</div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            )}

            {/* Back Button */}
            <div className="text-center flex-shrink-0">
                <Button
                    size="lg"
                    onClick={onBack}
                    className="px-8 sm:px-12 py-4 sm:py-5 text-base sm:text-lg font-bold bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700 text-white shadow-lg"
                >
                     Back to Lobby
                </Button>
            </div>
        </div>
    )
}
