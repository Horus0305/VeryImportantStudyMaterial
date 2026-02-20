/**
 * StandingsView — Tournament standings table and playoff bracket.
 * Full-width layout that fits viewport.
 */
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface StandingsEntry {
    player: string; played: number; won: number; lost: number; tied: number; points: number; nrr: number
}

interface StandingsInfo {
    standings?: StandingsEntry[]
    playoff_bracket?: Record<string, string[] | null>
    playoff_results?: Record<string, string>
}

interface StandingsData {
    standings?: StandingsEntry[]
    phase?: string
    champion?: string
    info?: StandingsInfo
}

interface Props {
    data: StandingsData
    isOver: boolean
    onBack: () => void
}

const PHASE_LABELS: Record<string, string> = {
    group: 'Group Stage',
    qualifier_1: 'Qualifier 1',
    eliminator: 'Eliminator',
    qualifier_2: 'Qualifier 2',
    final: 'FINAL',
    complete: 'Complete',
}

export default function StandingsView({ data, isOver, onBack }: Props) {
    const standings = data.standings ?? data.info?.standings ?? []
    const phase = data.phase ?? ''
    const champion = data.champion
    const playoffBracket = data.info?.playoff_bracket
    const playoffResults = data.info?.playoff_results

    return (
        <div className="w-full h-full flex flex-col px-4 sm:px-6 py-4 gap-4">
            {/* Header */}
            <div className="text-center space-y-2 flex-shrink-0">
                <h1 className="text-2xl sm:text-4xl font-black bg-gradient-to-r from-yellow-400 via-orange-500 to-red-500 bg-clip-text text-transparent">
                    {isOver ? ' Tournament Complete!' : ' Tournament Standings'}
                </h1>
                {champion && (
                    <p className="text-lg sm:text-2xl font-bold text-yellow-400">
                         Champion: {champion}
                    </p>
                )}
                <Badge variant="secondary" className="text-xs sm:text-sm bg-slate-800/50 border-slate-600 text-slate-300">
                    {PHASE_LABELS[phase] ?? phase}
                </Badge>
            </div>

            {/* Main content — Points Table + Playoff side by side */}
            <div className={`flex-1 grid gap-4 min-h-0 ${playoffBracket ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1'}`}>
                {/* Points Table */}
                <Card className="border-slate-700/50 bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm shadow-2xl">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-lg text-white">Points Table</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm font-mono">
                                <thead>
                                    <tr className="border-b border-slate-700 text-slate-400">
                                        <th className="text-left py-2">#</th>
                                        <th className="text-left py-2">Player</th>
                                        <th className="text-right px-2">P</th>
                                        <th className="text-right px-2">W</th>
                                        <th className="text-right px-2">L</th>
                                        <th className="text-right px-2">T</th>
                                        <th className="text-right px-2 font-bold">Pts</th>
                                        <th className="text-right px-2">NRR</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {standings.map((entry, idx) => (
                                        <tr
                                            key={entry.player}
                                            className={`border-b border-slate-700/50 ${idx < 2 ? 'text-yellow-400' : 'text-slate-300'}`}
                                        >
                                            <td className="py-2.5">{idx + 1}</td>
                                            <td className="py-2.5 font-semibold text-white">{entry.player}</td>
                                            <td className="text-right px-2">{entry.played}</td>
                                            <td className="text-right px-2 text-green-400 font-bold">{entry.won}</td>
                                            <td className="text-right px-2 text-red-400">{entry.lost}</td>
                                            <td className="text-right px-2">{entry.tied}</td>
                                            <td className="text-right px-2 font-bold text-orange-300">{entry.points}</td>
                                            <td className="text-right px-2 text-cyan-300">
                                                {entry.nrr >= 0 ? '+' : ''}{entry.nrr.toFixed(3)}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </CardContent>
                </Card>

                {/* Playoff Bracket */}
                {playoffBracket && Object.values(playoffBracket).some(v => v) && (
                    <Card className="border-slate-700/50 bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm shadow-2xl">
                        <CardHeader className="pb-2">
                            <CardTitle className="text-lg text-white">Playoff Bracket</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3 font-mono text-sm">
                            {['qualifier_1', 'eliminator', 'qualifier_2', 'final'].map(key => {
                                const pair = playoffBracket[key]
                                const result = playoffResults?.[key]
                                return (
                                    <div key={key} className="flex items-center gap-3 bg-slate-800/30 rounded-lg p-3 border border-slate-700/30">
                                        <Badge variant="outline" className="min-w-28 justify-center border-slate-600 text-slate-300">
                                            {PHASE_LABELS[key]}
                                        </Badge>
                                        {pair ? (
                                            <span className="text-white">
                                                {pair[0]} vs {pair[1]}
                                                {result && (
                                                    <span className="text-yellow-400 ml-2 font-bold">→ {result}</span>
                                                )}
                                            </span>
                                        ) : (
                                            <span className="text-slate-500">TBD</span>
                                        )}
                                    </div>
                                )
                            })}
                        </CardContent>
                    </Card>
                )}
            </div>

            {/* Bottom */}
            <div className="text-center flex-shrink-0">
                {!isOver ? (
                    <p className="text-slate-400 text-sm animate-pulse font-medium">
                        Next match starting soon...
                    </p>
                ) : (
                    <Button
                        size="lg"
                        onClick={onBack}
                        className="px-8 sm:px-12 py-4 sm:py-5 text-base sm:text-lg font-bold bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700 text-white shadow-lg"
                    >
                         Back to Lobby
                    </Button>
                )}
            </div>
        </div>
    )
}
