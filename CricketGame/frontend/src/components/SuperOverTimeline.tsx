import type { SuperOverRound } from '@/lib/superOver'

interface Props {
    rounds: SuperOverRound[]
}

function formatTeam(team: string[], fallback: string): string {
    return team.length ? team.join(', ') : fallback
}

export default function SuperOverTimeline({ rounds }: Props) {
    if (!rounds.length) return null

    return (
        <section className="border border-slate-200 bg-white p-4 md:p-5">
            <div className="flex items-center justify-between mb-4 border-b border-slate-200 pb-2">
                <h3
                    className="text-xl uppercase tracking-wide text-slate-900"
                    style={{ fontFamily: "'Bebas Neue', 'Teko', sans-serif" }}
                >
                    Super Over Timeline
                </h3>
                <span className="text-xs uppercase tracking-widest text-slate-500 font-bold">
                    {rounds.length} Round{rounds.length > 1 ? 's' : ''}
                </span>
            </div>

            <div className="space-y-3">
                {rounds.map((round) => {
                    const team3 = formatTeam(round.bat_team_3, 'Team 1')
                    const team4 = formatTeam(round.bat_team_4, 'Team 2')
                    const status = round.is_tied_round
                        ? 'Tied'
                        : `Won by ${round.round_winner ?? (round.scorecard_4.total_runs > round.scorecard_3.total_runs ? team4 : team3)}`

                    return (
                        <div key={`so-round-${round.round}`} className="border border-slate-200 rounded-sm p-3">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-xs font-bold uppercase tracking-widest text-slate-500">
                                    SO{round.round}
                                </span>
                                <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded ${round.is_tied_round ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700'}`}>
                                    {status}
                                </span>
                            </div>
                            <div className="space-y-1.5 text-sm">
                                <div className="flex items-center justify-between gap-3">
                                    <span className="font-medium text-slate-700 truncate">{team3}</span>
                                    <span className="font-mono font-bold text-slate-900 whitespace-nowrap">
                                        {round.scorecard_3.total_runs}/{round.scorecard_3.wickets} ({round.scorecard_3.overs} Ov)
                                    </span>
                                </div>
                                <div className="flex items-center justify-between gap-3">
                                    <span className="font-medium text-slate-700 truncate">{team4}</span>
                                    <span className="font-mono font-bold text-slate-900 whitespace-nowrap">
                                        {round.scorecard_4.total_runs}/{round.scorecard_4.wickets} ({round.scorecard_4.overs} Ov)
                                    </span>
                                </div>
                            </div>
                        </div>
                    )
                })}
            </div>
        </section>
    )
}
