/**
 * Scorecard — Post-match scorecard (Pro Sports / Editorial style).
 *
 * PC:   12-col grid → 4-col sidebar (PotM + Match Info) + 8-col innings stacked
 * Mobile: Single column, both innings displayed sequentially
 *
 * Design reference: scorecard PC/Mobile designs (Bebas Neue headings,
 * dark hero banner, editorial table layout, sidebar PotM card).
 */
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ArrowLeft } from 'lucide-react'

/* ─── Interfaces ─── */

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
interface PotmData {
    player: string; score: number; summary: string
    runs: number; balls: number; wickets: number; sr: number
    economy: number | null
}
interface Props {
    data: Record<string, unknown>
    onBack: () => void
}

/* ─── Batting Table ─── */

function BattingTable({ batting, potmName }: { batting: BatEntry[]; potmName?: string }) {
    return (
        <div className="overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
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
                    {batting.map(b => (
                        <tr key={b.name} className="hover:bg-slate-50 transition-colors group">
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
                            <td className="px-4 py-3 text-right font-mono text-slate-900">{typeof b.sr === 'number' ? b.sr.toFixed(2) : b.sr}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

/* ─── Bowling Table ─── */

function BowlingTable({ bowling, potmName }: { bowling: BowlEntry[]; potmName?: string }) {
    return (
        <div className="overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
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
                    {bowling.map(bw => (
                        <tr key={bw.name} className="hover:bg-slate-50 transition-colors group">
                            <td className="px-4 py-3 font-medium text-slate-900 whitespace-nowrap">
                                {bw.name}
                                {potmName && bw.name === potmName && (
                                    <span className="inline-block ml-1.5 text-emerald-500 text-[10px] align-middle">★</span>
                                )}
                            </td>
                            <td className="px-4 py-3 text-center font-mono text-slate-600">{bw.overs}</td>
                            <td className="px-4 py-3 text-center font-mono text-slate-400">0</td>
                            <td className="px-4 py-3 text-center font-mono text-slate-600">{bw.runs}</td>
                            <td className="px-4 py-3 text-center font-bold text-emerald-500 bg-emerald-50/30">{bw.wickets}</td>
                            <td className="px-4 py-3 text-right font-mono text-slate-900">{typeof bw.econ === 'number' ? bw.econ.toFixed(2) : bw.econ}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

/* ─── Innings Section ─── */

function InningsSection({ innings, label, teamInitial, initialBg, potmName }: {
    innings: InningsData; label: string; teamInitial: string
    initialBg: string; potmName?: string
}) {
    return (
        <section>
            {/* Innings Header */}
            <div className="flex items-center justify-between mb-4 border-b-2 border-slate-900 pb-2">
                <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 ${initialBg} flex items-center justify-center font-bold rounded text-sm`}>
                        {teamInitial}
                    </div>
                    <h2 className="text-xl font-bold uppercase tracking-wide text-slate-900" style={{ fontFamily: "'Bebas Neue', 'Teko', sans-serif" }}>
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

            {/* Batting Table */}
            <div className="mb-6 border border-slate-200 bg-white overflow-hidden">
                <BattingTable batting={innings.batting} potmName={potmName} />
            </div>

            {/* Bowling Table */}
            <div className="border border-slate-200 bg-white overflow-hidden">
                <BowlingTable bowling={innings.bowling} potmName={potmName} />
            </div>
        </section>
    )
}

/* ─── Main Scorecard Component ─── */

export default function Scorecard({ data, onBack }: Props) {
    const resultText = (data.result_text as string) ?? ''
    const scorecard1 = data.scorecard_1 as InningsData | undefined
    const scorecard2 = data.scorecard_2 as InningsData | undefined
    const potm = data.potm as PotmData | undefined
    const tournament = data.tournament as TournamentPayload | undefined
    const standings = tournament?.standings ?? []
    const upcoming = tournament?.upcoming_matches ?? []
    const winner = (data.winner as string) ?? ''
    const sideA = (data.side_a as string[]) ?? []
    const sideB = (data.side_b as string[]) ?? []

    const battingTeam1 = sideA.length ? sideA.join(', ') : 'Team A'
    const battingTeam2 = sideB.length ? sideB.join(', ') : 'Team B'

    // Split result cleverly for display font
    const resultParts = resultText.split(/(won)/i)
    const hasWonSplit = resultParts.length >= 3

    return (
        <div className="w-full min-h-full bg-white text-slate-900 overflow-y-auto selection:bg-emerald-500 selection:text-white">
            {/* ─── Sticky Header ─── */}
            <nav className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-200">
                <div className="w-full px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-14">
                        <div className="flex items-center gap-4 md:gap-6">
                            <button
                                onClick={onBack}
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
                            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
                                {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).toUpperCase()}
                            </span>
                        </div>
                    </div>
                </div>
            </nav>

            <main className="w-full px-4 sm:px-6 lg:px-8 py-6 md:py-8">
                {/* ─── Hero Result Banner ─── */}
                <section className="relative overflow-hidden mb-8 h-[320px] md:h-[400px] flex items-end bg-slate-900 rounded-sm group">
                    {/* Background image */}
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

                            {/* Score Summary Card (glassmorphism) */}
                            {scorecard1 && scorecard2 && (
                                <div className="bg-white/10 backdrop-blur-sm border border-white/20 p-4 rounded min-w-[180px] md:min-w-[200px]">
                                    <div className="flex justify-between items-center border-b border-white/20 pb-2 mb-2">
                                        <span className="text-white font-bold uppercase tracking-wider text-sm">{battingTeam1}</span>
                                        <span className="text-emerald-400 font-mono font-bold text-lg">
                                            {scorecard1.total_runs}/{scorecard1.wickets}
                                        </span>
                                    </div>
                                    <div className="flex justify-between items-center text-slate-300">
                                        <span className="font-medium uppercase tracking-wider text-xs">{battingTeam2}</span>
                                        <span className="font-mono text-sm">{scorecard2.total_runs}/{scorecard2.wickets}</span>
                                    </div>
                                    <div className="mt-2 text-[10px] text-slate-400 uppercase tracking-widest text-right">
                                        {scorecard1.overs} Overs
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </section>

                {/* ─── Content Grid: Sidebar + Innings ─── */}
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8">
                    {/* Left Sidebar */}
                    <div className="lg:col-span-4 space-y-6">
                        {/* Player of the Match Card */}
                        {potm && (
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
                                                {potm.player.charAt(0).toUpperCase()}
                                            </span>
                                        </div>
                                    </div>
                                    <h4 className="text-2xl font-bold text-slate-900">{potm.player}</h4>
                                    <p className="text-sm text-slate-500 font-mono mt-1">{potm.summary}</p>
                                </div>
                                <div className="grid grid-cols-3 divide-x divide-slate-100">
                                    <div className="p-4 text-center hover:bg-slate-50 transition-colors">
                                        <div className="text-xs text-slate-400 uppercase font-bold tracking-widest mb-1">Runs</div>
                                        <div className="text-2xl font-bold text-slate-900" style={{ fontFamily: "'Bebas Neue', 'Teko', sans-serif" }}>
                                            {potm.runs}
                                        </div>
                                        <div className="text-[10px] text-slate-400">({potm.balls})</div>
                                    </div>
                                    <div className="p-4 text-center hover:bg-slate-50 transition-colors">
                                        <div className="text-xs text-slate-400 uppercase font-bold tracking-widest mb-1">Wickets</div>
                                        <div className="text-2xl font-bold text-slate-900" style={{ fontFamily: "'Bebas Neue', 'Teko', sans-serif" }}>
                                            {potm.wickets}
                                        </div>
                                        {potm.economy !== null && (
                                            <div className="text-[10px] text-slate-400">{potm.economy?.toFixed(1)} Econ</div>
                                        )}
                                    </div>
                                    <div className="p-4 text-center hover:bg-slate-50 transition-colors">
                                        <div className="text-xs text-slate-400 uppercase font-bold tracking-widest mb-1">SR</div>
                                        <div className="text-2xl font-bold text-emerald-500" style={{ fontFamily: "'Bebas Neue', 'Teko', sans-serif" }}>
                                            {typeof potm.sr === 'number' ? Math.round(potm.sr) : potm.sr}
                                        </div>
                                    </div>
                                </div>
                            </section>
                        )}

                        {/* Match Info Card */}
                        <section className="bg-slate-50 border border-slate-200 p-6">
                            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">Match Info</h4>
                            <div className="space-y-3">
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-slate-500">Teams</span>
                                    <span className="text-sm font-medium text-slate-900 text-right">{battingTeam1} vs {battingTeam2}</span>
                                </div>
                                {winner && (
                                    <div className="flex justify-between items-center">
                                        <span className="text-sm text-slate-500">Winner</span>
                                        <span className="text-sm font-medium text-emerald-600 text-right">{winner}</span>
                                    </div>
                                )}
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-slate-500">Date</span>
                                    <span className="text-sm font-medium text-slate-900 text-right">
                                        {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                                    </span>
                                </div>
                            </div>
                        </section>
                    </div>

                    {/* Right Content — Innings */}
                    <div className="lg:col-span-8 space-y-10">
                        {scorecard1 && (
                            <InningsSection
                                innings={scorecard1}
                                label={`${battingTeam1} Innings`}
                                teamInitial={battingTeam1.charAt(0).toUpperCase()}
                                initialBg="bg-orange-100 text-orange-600"
                                potmName={potm?.player}
                            />
                        )}
                        {scorecard2 && (
                            <InningsSection
                                innings={scorecard2}
                                label={`${battingTeam2} Innings`}
                                teamInitial={battingTeam2.charAt(0).toUpperCase()}
                                initialBg="bg-slate-100 text-slate-600"
                                potmName={potm?.player}
                            />
                        )}
                    </div>
                </div>

                {/* ─── Tournament Standings & Upcoming ─── */}
                {standings.length > 0 && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-10">
                        <Card className="border-slate-200 bg-white shadow-sm">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-base sm:text-lg font-bold text-slate-900 flex items-center gap-2">
                                    <span>🏆 Standings</span>
                                    <span className="text-xs uppercase tracking-wider text-slate-500">{tournament?.phase}</span>
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-1 text-xs font-mono">
                                    <div className="flex justify-between text-slate-500 font-bold border-b border-slate-200 pb-1">
                                        <span className="w-5">#</span>
                                        <span className="flex-1">Player</span>
                                        <span className="w-8 text-center">P</span>
                                        <span className="w-8 text-center">W</span>
                                        <span className="w-8 text-center">L</span>
                                        <span className="w-10 text-center">Pts</span>
                                        <span className="w-12 text-right">NRR</span>
                                    </div>
                                    {standings.map((s, i) => (
                                        <div key={s.player} className={`flex justify-between rounded p-1.5 border border-slate-100 ${i < 4 ? 'bg-emerald-50/30' : 'bg-slate-50'}`}>
                                            <span className={`w-5 ${i < 4 ? 'text-emerald-500 font-bold' : 'text-slate-500'}`}>{i + 1}</span>
                                            <span className="flex-1 truncate text-slate-900 font-medium">{s.player}</span>
                                            <span className="w-8 text-center text-slate-600">{s.played}</span>
                                            <span className="w-8 text-center text-green-600 font-bold">{s.won}</span>
                                            <span className="w-8 text-center text-red-600">{s.lost}</span>
                                            <span className="w-10 text-center text-orange-600 font-bold">{s.points}</span>
                                            <span className={`w-12 text-right ${s.nrr >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                                                {s.nrr >= 0 ? '+' : ''}{typeof s.nrr === 'number' ? s.nrr.toFixed(2) : s.nrr}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            </CardContent>
                        </Card>

                        <Card className="border-slate-200 bg-white shadow-sm">
                            <CardHeader className="pb-2">
                                <CardTitle className="text-base sm:text-lg font-bold text-slate-900 flex items-center gap-2">
                                    <span>📅 Upcoming</span>
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                {upcoming.length ? (
                                    <div className="space-y-2 text-sm text-slate-600">
                                        {upcoming.slice(0, 6).map((m, idx) => (
                                            <div key={`${m.label}-${idx}`} className="flex items-center justify-between gap-3 border-b border-slate-100 pb-2 last:border-0">
                                                <span className="text-xs uppercase tracking-wider text-slate-500 font-medium">{m.label}</span>
                                                <span className="flex-1 text-right text-slate-900 font-medium">
                                                    {m.teams?.length ? `${m.teams[0] ?? 'TBD'} vs ${m.teams[1] ?? 'TBD'}` : 'TBD'}
                                                </span>
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

                {/* ─── Footer ─── */}
                <footer className="mt-16 border-t border-slate-200 pt-8 pb-6 text-center">
                    <Button
                        size="lg"
                        onClick={onBack}
                        className="px-10 py-5 text-sm font-bold uppercase tracking-widest bg-slate-900 hover:bg-slate-800 text-white rounded transition-all"
                    >
                        Back to Lobby
                    </Button>
                </footer>
            </main>
        </div>
    )
}
