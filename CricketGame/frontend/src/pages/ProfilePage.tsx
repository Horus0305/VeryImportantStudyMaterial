import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'

interface FormatStats {
    format: string
    matches_played: number
    matches_won: number
    total_runs: number
    total_balls_faced: number
    avg_runs: number
    avg_strike_rate: number
    highest_score: number
    fours: number
    sixes: number
    fifties: number
    hundreds: number
    wickets_taken: number
    best_bowling: string
    bowling_average: number
    tournaments_played?: number
    tournaments_won?: number
    potm_count?: number
    player_of_tournament_count?: number
    total_titles?: number
}

interface PlayerStats {
    username: string
    overall?: FormatStats
    '1v1'?: FormatStats
    'team'?: FormatStats
    'cpu'?: FormatStats
    'tournament'?: FormatStats
}

interface Props {
    token: string
    username: string
    onLogout: () => void
    onRename: (token: string, username: string) => void
}

interface MatchHistoryEntry {
    match_id: string; mode: string; timestamp: string
    side_a: string[]; side_b: string[]
    result_text: string; winner: string | null
    potm: string | null
}

interface TournamentHistoryEntry {
    tournament_id: string; timestamp: string; champion: string | null
    players: string[]
    orange_cap: { player: string; runs: number } | null
    purple_cap: { player: string; wickets: number } | null
    player_of_tournament: { player: string } | null
}

const API = (import.meta.env.VITE_API_BASE_URL ?? window.location.origin).replace(/\/$/, '')

export default function ProfilePage({ token, username, onLogout, onRename }: Props) {
    const navigate = useNavigate()
    const [stats, setStats] = useState<PlayerStats | null>(null)
    const [activeTab, setActiveTab] = useState<'overall' | '1v1' | 'team' | 'cpu' | 'tournament'>('overall')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')
    const [matchHistory, setMatchHistory] = useState<MatchHistoryEntry[]>([])
    const [tournamentHistory, setTournamentHistory] = useState<TournamentHistoryEntry[]>([])
    const [isEditingName, setIsEditingName] = useState(false)
    const [nameInput, setNameInput] = useState(username)
    const [renameError, setRenameError] = useState('')
    const [renameLoading, setRenameLoading] = useState(false)
    const [cpuLoading, setCpuLoading] = useState(false)
    const [cpuError, setCpuError] = useState('')

    useEffect(() => {
        const fetchInitialData = async () => {
            if (!username) return
            setLoading(true)
            try {
                const [statsRes, tournamentsRes] = await Promise.all([
                    fetch(`${API}/auth/stats/${username}`),
                    fetch(`${API}/api/tournaments/${username}`)
                ])

                if (!statsRes.ok) {
                    if (statsRes.status === 404) {
                        setError('Player not found')
                    } else {
                        setError('Failed to load stats')
                    }
                    return
                }

                setStats(await statsRes.json())
                if (tournamentsRes.ok) {
                    setTournamentHistory(await tournamentsRes.json())
                }
            } catch (err) {
                console.error(err)
                setError('Network error')
            } finally {
                setLoading(false)
            }
        }
        fetchInitialData()
    }, [username, navigate])

    useEffect(() => {
        setNameInput(username)
    }, [username])

    useEffect(() => {
        const fetchMatches = async () => {
            if (!username) return
            // For overall, fetch recent matches without mode filter
            // For tournament, strictly speaking we might not show matches, but if we did, it would be tournament matches
            const queryMode = activeTab === 'overall' ? '' : `mode=${activeTab}&`
            if (activeTab === 'tournament') return // We only show tournament list for this tab

            try {
                const res = await fetch(`${API}/api/matches/${username}?${queryMode}limit=10`)
                if (res.ok) {
                    setMatchHistory(await res.json())
                }
            } catch (err) {
                console.error("Failed to fetch matches:", err)
            }
        }
        fetchMatches()
    }, [username, activeTab])

    const startCpuMatch = async () => {
        setCpuLoading(true)
        setCpuError('')
        try {
            const res = await fetch(`${API}/rooms/cpu?token=${token}`, { method: 'POST' })
            const data = await res.json()
            if (!res.ok) {
                setCpuError(data.detail || 'Failed to start CPU match')
                return
            }
            navigate(`/room/${data.room_code}`)
        } catch {
            setCpuError('Cannot connect to server. Is the backend running?')
        } finally {
            setCpuLoading(false)
        }
    }

    const formatData = stats?.[activeTab]
    const winRate = formatData
        ? (formatData.matches_played > 0
            ? ((formatData.matches_won / formatData.matches_played) * 100).toFixed(1)
            : '0.0')
        : '0.0'

    const submitRename = async () => {
        const nextName = nameInput.trim()
        if (!nextName || nextName === username) {
            setIsEditingName(false)
            setRenameError('')
            return
        }
        setRenameLoading(true)
        setRenameError('')
        try {
            const res = await fetch(`${API}/auth/rename`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, new_username: nextName }),
            })
            const data = await res.json()
            if (!res.ok) {
                setRenameError(data.detail || 'Rename failed')
                return
            }
            onRename(data.token, data.username)
            setIsEditingName(false)
        } catch {
            setRenameError('Cannot connect to server. Is the backend running?')
        } finally {
            setRenameLoading(false)
        }
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-foreground p-4 sm:p-6">
            {/* Header */}
            <div className="w-full max-w-[1920px] mx-auto px-4 md:px-8">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
                    <div className="flex items-center gap-4">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => navigate('/')}
                            className="text-blue-400 hover:text-blue-300 hover:bg-slate-800/50"
                        >
                            ← Back to Lobby
                        </Button>
                        <div className="h-8 w-px bg-border" />
                        <h1 className="text-2xl sm:text-3xl font-bold bg-gradient-to-r from-orange-400 to-pink-600 bg-clip-text text-transparent">
                            Player Profile
                        </h1>
                    </div>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={onLogout}
                        className="text-red-400 hover:text-red-300 hover:bg-slate-800/50"
                    >
                        Logout
                    </Button>
                </div>

                {/* Player Header Card */}
                <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5 sm:p-8 mb-6 shadow-2xl">
                    <div className="flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-6">
                        <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-gradient-to-br from-orange-500 to-pink-600 flex items-center justify-center text-3xl sm:text-4xl font-bold text-white shadow-lg">
                            {username.charAt(0).toUpperCase()}
                        </div>
                        <div>
                            <div className="flex items-center gap-3 mb-2">
                                {isEditingName ? (
                                    <Input
                                        value={nameInput}
                                        onChange={e => setNameInput(e.target.value)}
                                        className="h-10 w-full sm:w-56 bg-slate-900/50 border-slate-600 text-white placeholder:text-slate-500 focus:border-orange-500 focus:ring-orange-500/20"
                                    />
                                ) : (
                                    <h2 className="text-3xl sm:text-4xl font-bold text-white">{username}</h2>
                                )}
                                {isEditingName ? (
                                    <div className="flex gap-2">
                                        <Button
                                            size="sm"
                                            onClick={submitRename}
                                            disabled={renameLoading}
                                            className="bg-gradient-to-r from-orange-500 to-pink-600 hover:from-orange-600 hover:to-pink-700"
                                        >
                                            {renameLoading ? 'Saving...' : 'Save'}
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            onClick={() => { setIsEditingName(false); setNameInput(username); setRenameError('') }}
                                            className="text-slate-300 hover:text-white hover:bg-slate-800/50"
                                        >
                                            Cancel
                                        </Button>
                                    </div>
                                ) : (
                                    <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => { setIsEditingName(true); setRenameError('') }}
                                        className="text-slate-300 hover:text-white hover:bg-slate-800/50"
                                    >
                                        Edit Name
                                    </Button>
                                )}
                            </div>
                            {renameError && (
                                <div className="text-xs text-red-300 mb-2">{renameError}</div>
                            )}
                            <div className="flex gap-3">
                                <Badge className="bg-orange-500/20 text-orange-300 border-orange-500/30">
                                    🏏 Cricket Player
                                </Badge>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Format Tabs */}
                <div className="flex flex-wrap gap-2 mb-6">
                    {(['overall', '1v1', 'team', 'cpu', 'tournament'] as const).map((format) => (
                        <button
                            key={format}
                            onClick={() => setActiveTab(format)}
                            className={`px-4 sm:px-6 py-2.5 sm:py-3 rounded-xl font-semibold transition-all duration-300 text-sm sm:text-base ${activeTab === format
                                ? 'bg-gradient-to-r from-orange-500 to-pink-600 text-white shadow-lg scale-105'
                                : 'bg-slate-800/50 text-slate-400 hover:text-white hover:bg-slate-700/50'
                                }`}
                        >
                            {format === 'overall' && 'Overall'}
                            {format === '1v1' && '1v1 Battles'}
                            {format === 'team' && 'Team Mode'}
                            {format === 'cpu' && 'CPU Mode'}
                            {format === 'tournament' && 'Tournaments'}
                        </button>
                    ))}
                </div>

                {activeTab === 'cpu' && (
                    <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5 sm:p-6 shadow-xl mb-6">
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                            <div>
                                <div className="text-xl font-bold text-white">Play vs CPU</div>
                                <div className="text-sm text-slate-400">Single-player 1v1 match with weighted CPU moves.</div>
                            </div>
                            <Button
                                onClick={startCpuMatch}
                                disabled={cpuLoading}
                                className="bg-gradient-to-r from-orange-500 to-pink-600 hover:from-orange-600 hover:to-pink-700"
                            >
                                {cpuLoading ? 'Starting...' : 'Start Match'}
                            </Button>
                        </div>
                        {cpuError && (
                            <div className="text-xs text-red-300 mt-3">{cpuError}</div>
                        )}
                    </div>
                )}

                {loading ? (
                    <div className="text-center py-16 sm:py-20">
                        <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-orange-500 border-r-transparent"></div>
                        <p className="mt-4 text-slate-400">Loading stats...</p>
                    </div>
                ) : error ? (
                    <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center text-red-300">
                        {error}
                    </div>
                ) : !formatData || formatData.matches_played === 0 ? (
                    <div className="bg-slate-800/30 rounded-xl p-8 sm:p-12 text-center border border-slate-700/50">
                        <div className="text-6xl mb-4">😢</div>
                        <h3 className="text-2xl font-bold text-white mb-2">No Matches Played</h3>
                        <p className="text-slate-400">Start playing {activeTab} to see your stats here!</p>
                        <Button
                            onClick={() => navigate('/')}
                            className="mt-6 bg-gradient-to-r from-orange-500 to-pink-600 hover:from-orange-600 hover:to-pink-700"
                        >
                            Play Now
                        </Button>
                    </div>
                ) : (
                    <div className="space-y-6">
                        {/* Match Record */}
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                            <StatCard
                                label="Matches"
                                value={formatData.matches_played}
                                icon="🎮"
                                gradient="from-blue-500 to-cyan-500"
                            />
                            <StatCard
                                label="Wins"
                                value={formatData.matches_won}
                                icon="🏆"
                                gradient="from-green-500 to-emerald-500"
                            />
                            <StatCard
                                label="Win Rate"
                                value={winRate + '%'}
                                icon="📈"
                                gradient="from-purple-500 to-pink-500"
                            />

                            {/* Dynamic 4th Card */}
                            {activeTab === 'tournament' ? (
                                <StatCard
                                    label="Player of Tournament"
                                    value={formatData.player_of_tournament_count || 0}
                                    icon="🌟"
                                    gradient="from-yellow-500 to-orange-500"
                                />
                            ) : activeTab === 'overall' ? (
                                <StatCard
                                    label="Titles Won"
                                    value={formatData.total_titles || 0}
                                    icon="👑"
                                    gradient="from-yellow-500 to-orange-500"
                                />
                            ) : (
                                <StatCard
                                    label="Player of Match"
                                    value={formatData.potm_count || 0}
                                    icon="⭐"
                                    gradient="from-orange-500 to-red-500"
                                />
                            )}
                        </div>

                        {/* Batting Stats */}
                        <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5 sm:p-6 shadow-xl">
                            <h3 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                                <span>🏏 Batting Statistics</span>
                            </h3>
                            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                                <StatItem label="Total Runs" value={formatData.total_runs} />
                                <StatItem label="Highest Score" value={formatData.highest_score} highlight />
                                <StatItem label="Average" value={formatData.avg_runs.toFixed(2)} />
                                <StatItem label="Strike Rate" value={formatData.avg_strike_rate.toFixed(2)} />
                                <StatItem label="Fours" value={formatData.fours} />
                                <StatItem label="Sixes" value={formatData.sixes} />
                                <StatItem label="Fifties" value={formatData.fifties} />
                                <StatItem label="Hundreds" value={formatData.hundreds} highlight />
                            </div>
                        </div>

                        {/* Bowling Stats */}
                        {formatData.wickets_taken > 0 && (
                            <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5 sm:p-6 shadow-xl">
                                <h3 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                                    <span>🎯 Bowling Statistics</span>
                                </h3>
                                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                                    <StatItem label="Wickets" value={formatData.wickets_taken} />
                                    <StatItem label="Best Bowling" value={formatData.best_bowling} highlight />
                                    <StatItem label="Bowling Avg" value={formatData.bowling_average.toFixed(2)} />
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Match History Section - For Overall, 1v1, team */}
                {(activeTab === 'overall' || activeTab === '1v1' || activeTab === 'team' || activeTab === 'cpu') && matchHistory.length > 0 && (
                    <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5 sm:p-6 shadow-xl mt-6">
                        <h3 className="text-2xl font-bold text-white mb-4 flex items-center gap-3">
                            <span>📜 Match History</span>
                            <span className="text-sm font-normal text-slate-400">({matchHistory.length} recent)</span>
                        </h3>
                        <div className="space-y-2">
                            {matchHistory
                                .map(m => {
                                    const opponent = m.side_a.includes(username)
                                        ? m.side_b.join(', ')
                                        : m.side_a.join(', ')
                                    const isWin = m.winner?.includes(username)
                                    const isTie = m.winner === 'TIE'

                                    const displayMode = m.mode === '2v2' ? 'team' : m.mode
                                    return (
                                        <button
                                            key={m.match_id}
                                            onClick={() => navigate(`/match/${m.match_id}`)}
                                            className="w-full text-left flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 bg-slate-800/50 hover:bg-slate-700/50 rounded-xl p-4 border border-slate-700/50 hover:border-orange-500/30 transition-all group cursor-pointer"
                                        >
                                            <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold ${isTie ? 'bg-yellow-500/20 text-yellow-300' :
                                                isWin ? 'bg-green-500/20 text-green-300' :
                                                    'bg-red-500/20 text-red-300'
                                                }`}>
                                                {isTie ? 'T' : isWin ? 'W' : 'L'}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="text-sm font-semibold text-white">
                                                    vs {opponent}
                                                </div>
                                                <div className="text-xs text-slate-400 truncate">
                                                    {m.result_text}
                                                </div>
                                            </div>
                                            <div className="flex flex-row sm:flex-col items-center sm:items-end gap-2 sm:gap-1">
                                                <Badge className={`text-[10px] ${displayMode === 'tournament' ? 'bg-purple-500/20 text-purple-300 border-purple-500/30' :
                                                    displayMode === 'team' ? 'bg-blue-500/20 text-blue-300 border-blue-500/30' :
                                                        'bg-slate-700/50 text-slate-300 border-slate-600/50'
                                                    }`}>
                                                    {displayMode}
                                                </Badge>
                                                {m.potm === username && (
                                                    <span className="text-[10px] text-yellow-400"> PotM</span>
                                                )}
                                            </div>
                                            <div className="text-[10px] text-slate-500 w-full sm:w-16 text-left sm:text-right">
                                                {new Date(m.timestamp).toLocaleDateString()}
                                            </div>
                                            <span className="text-sm text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity">→</span>
                                        </button>
                                    )
                                })}
                        </div>
                    </div>
                )}

                {/* Tournament History Section - For Overall and Tournament */}
                {(activeTab === 'overall' || activeTab === 'tournament') && tournamentHistory.length > 0 && (
                    <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5 sm:p-6 shadow-xl mt-6">
                        <h3 className="text-2xl font-bold text-white mb-4 flex items-center gap-3">
                            <span>🏆 Recent Tournaments</span>
                        </h3>
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                            {tournamentHistory.map(t => (
                                <button
                                    key={t.tournament_id}
                                    onClick={() => navigate(`/tournament/${t.tournament_id}`)}
                                    className="text-left bg-gradient-to-br from-slate-800/70 to-slate-900/70 hover:from-slate-700/70 hover:to-slate-800/70 rounded-xl p-5 border border-slate-700/50 hover:border-yellow-500/30 transition-all group cursor-pointer"
                                >
                                    <div className="flex items-center justify-between mb-3">
                                        <span className="text-2xl">🏆</span>
                                        <span className="text-[10px] text-slate-500">
                                            {new Date(t.timestamp).toLocaleDateString()}
                                        </span>
                                    </div>
                                    {t.champion && (
                                        <div className="mb-2">
                                            <span className="text-[10px] text-yellow-400 uppercase tracking-wider font-semibold">👑 Champion</span>
                                            <div className={`text-lg font-bold ${t.champion === username ? 'text-yellow-300' : 'text-white'}`}>
                                                {t.champion} {t.champion === username && '👑'}
                                            </div>
                                        </div>
                                    )}
                                    <div className="space-y-1 text-[11px] text-slate-400">
                                        {t.orange_cap && <div>🟠 {t.orange_cap.player}: {t.orange_cap.runs} runs</div>}
                                        {t.purple_cap && <div>🟣 {t.purple_cap.player}: {t.purple_cap.wickets} wkts</div>}
                                    </div>
                                    <div className="text-[10px] text-blue-400 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
                                        View details →
                                    </div>
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}

// Helper Components
function StatCard({ label, value, icon, gradient }: { label: string; value: string | number; icon: string; gradient: string }) {
    return (
        <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-4 sm:p-6 shadow-lg hover:scale-105 transition-transform duration-300">
            <div className={`w-11 h-11 sm:w-12 sm:h-12 rounded-lg bg-gradient-to-br ${gradient} flex items-center justify-center text-2xl mb-3 shadow-lg`}>
                {icon}
            </div>
            <div className="text-2xl sm:text-3xl font-bold text-white mb-1">{value}</div>
            <div className="text-sm text-slate-400">{label}</div>
        </div>
    )
}

function StatItem({ label, value, highlight = false }: { label: string; value: string | number; highlight?: boolean }) {
    return (
        <div className={`p-3 sm:p-4 rounded-lg ${highlight ? 'bg-gradient-to-br from-orange-500/10 to-pink-500/10 border border-orange-500/30' : 'bg-slate-800/30'}`}>
            <div className="text-sm text-slate-400 mb-1">{label}</div>
            <div className={`text-xl sm:text-2xl font-bold ${highlight ? 'bg-gradient-to-r from-orange-400 to-pink-600 bg-clip-text text-transparent' : 'text-white'}`}>
                {value}
            </div>
        </div>
    )
}
