import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Bell, Edit3, ChevronRight, Check } from 'lucide-react'

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

const TAB_LABELS: Record<string, string> = {
    overall: 'Overall',
    '1v1': '1v1 Quick Match',
    team: 'Team Mode',
    tournament: 'Tournament',
    cpu: 'CPU Mode',
}

const DISPLAY_FONT = { fontFamily: "'Anton', 'Bebas Neue', sans-serif" }

export default function ProfilePage({ token, username, onRename }: Props) {
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
                    if (statsRes.status === 404) setError('Player not found')
                    else setError('Failed to load stats')
                    return
                }

                setStats(await statsRes.json())
                if (tournamentsRes.ok) setTournamentHistory(await tournamentsRes.json())
            } catch (err) {
                console.error(err)
                setError('Network error')
            } finally {
                setLoading(false)
            }
        }
        fetchInitialData()
    }, [username, navigate])

    useEffect(() => setNameInput(username), [username])

    useEffect(() => {
        const fetchMatches = async () => {
            if (!username) return
            const queryMode = activeTab === 'overall' ? '' : `mode=${activeTab}&`
            if (activeTab === 'tournament') return

            try {
                const res = await fetch(`${API}/api/matches/${username}?${queryMode}`)
                if (res.ok) setMatchHistory(await res.json())
            } catch (err) {
                console.error("Failed to fetch matches:", err)
            }
        }
        fetchMatches()
    }, [username, activeTab])

    const startCpuMatch = async () => {
        setCpuLoading(true)
        try {
            const res = await fetch(`${API}/rooms/cpu?token=${token}`, { method: 'POST' })
            const data = await res.json()
            if (!res.ok) return
            navigate(`/room/${data.room_code}`)
        } catch {
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
            setRenameError('Network error')
        } finally {
            setRenameLoading(false)
        }
    }

    if (loading) {
        return (
            <div className="min-h-screen bg-slate-50 flex items-center justify-center">
                <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="min-h-screen bg-slate-50 flex items-center justify-center">
                <div className="bg-red-50 text-red-600 p-6 rounded-lg font-bold border border-red-200">{error}</div>
            </div>
        )
    }

    return (
        <div className="bg-slate-50 text-slate-900 font-sans min-h-screen pb-32 lg:pb-0">
            {/* Nav */}
            <nav className="border-b border-slate-200 bg-white/90 backdrop-blur-md sticky top-0 z-50">
                <div className="w-full px-4 sm:px-6 lg:px-8 h-14 lg:h-16 flex items-center justify-between">
                    <button onClick={() => navigate('/')} className="flex items-center gap-1.5 lg:gap-2 text-slate-500 hover:text-emerald-600 transition-colors">
                        <ArrowLeft className="w-4 h-4 lg:w-5 lg:h-5" />
                        <span className="text-xs lg:text-sm font-bold uppercase tracking-widest">Back to Hub</span>
                    </button>
                    <div className="flex items-center gap-4 lg:gap-6">
                        <button className="text-slate-400 hover:text-emerald-600 transition-colors hidden sm:block">
                            <Bell className="w-5 h-5" />
                        </button>
                        <div className="h-8 w-8 rounded-full bg-slate-900 text-white flex items-center justify-center text-lg leading-none pt-0.5" style={DISPLAY_FONT}>
                            {username.charAt(0).toUpperCase()}
                        </div>
                    </div>
                </div>
            </nav>

            {/* Hero Header */}
            <header className="relative bg-gradient-to-b from-emerald-50 to-white lg:bg-white border-b border-slate-200 overflow-hidden">
                <div className="absolute right-0 top-0 h-full w-1/3 bg-gradient-to-l from-emerald-50 to-transparent hidden lg:block pointer-events-none"></div>
                <div className="w-full px-4 sm:px-6 lg:px-8 py-8 lg:py-16 relative z-10 flex flex-col lg:flex-row items-center lg:items-center justify-between gap-6 lg:gap-8 text-center lg:text-left">
                    <div className="flex flex-col lg:flex-row items-center lg:items-end gap-4 lg:gap-8">
                        {/* Avatar */}
                        <div className="relative group">
                            <div className="w-24 h-24 lg:w-32 lg:h-32 bg-slate-900 rounded-xl shadow-xl flex items-center justify-center text-emerald-500 transform lg:-rotate-2 border-4 border-white transition-transform duration-300 group-hover:scale-105">
                                <span className="text-6xl lg:text-7xl leading-none" style={DISPLAY_FONT}>{username.charAt(0).toUpperCase()}</span>
                                <div className="absolute -bottom-2 -right-2 lg:-bottom-3 lg:-right-3 w-8 h-8 lg:w-10 lg:h-10 bg-emerald-500 text-white rounded-lg flex items-center justify-center border-2 border-white shadow-sm">
                                    <Check className="w-4 h-4 lg:w-5 lg:h-5 stroke-[3]" />
                                </div>
                            </div>
                        </div>

                        {/* Name & Titles */}
                        <div className="mb-1 flex flex-col items-center lg:items-start">
                            <div className="flex items-center gap-3 mb-3 lg:mb-2">
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider bg-emerald-100/50 lg:bg-emerald-100 text-emerald-700">
                                    Pro Cricket Player
                                </span>
                                <span className="flex items-center gap-1.5 text-[10px] lg:text-xs font-bold text-slate-500 uppercase tracking-widest">
                                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> Online
                                </span>
                            </div>

                            {isEditingName ? (
                                <div className="flex flex-col items-center lg:items-start gap-2 max-w-xs w-full">
                                    <input
                                        value={nameInput}
                                        onChange={e => setNameInput(e.target.value)}
                                        className="w-full text-2xl font-bold bg-white border border-slate-300 rounded px-3 py-1 text-center lg:text-left focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
                                        placeholder="New username"
                                    />
                                    <div className="flex gap-2">
                                        <button onClick={submitRename} disabled={renameLoading} className="text-xs bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1 font-bold uppercase rounded transition-colors disabled:opacity-50">Save</button>
                                        <button onClick={() => { setIsEditingName(false); setNameInput(username) }} className="text-xs bg-slate-200 hover:bg-slate-300 text-slate-700 px-3 py-1 font-bold uppercase rounded transition-colors">Cancel</button>
                                    </div>
                                    {renameError && <span className="text-xs text-red-500 font-bold">{renameError}</span>}
                                </div>
                            ) : (
                                <h1 className="text-5xl md:text-7xl lg:text-8xl leading-none tracking-tight text-slate-900 uppercase truncate max-w-full" style={DISPLAY_FONT}>
                                    {username}
                                </h1>
                            )}
                        </div>
                    </div>

                    {!isEditingName && (
                        <div className="flex flex-col items-center lg:items-end gap-4 w-full lg:w-auto mt-2 lg:mt-0">
                            <button
                                onClick={() => setIsEditingName(true)}
                                className="group w-full lg:w-auto flex items-center justify-center gap-2 px-6 py-3 bg-slate-900 hover:bg-emerald-600 shadow-xl shadow-slate-900/10 hover:shadow-emerald-600/20 text-white transition-all duration-300 font-bold uppercase tracking-widest text-xs lg:text-sm rounded-sm"
                            >
                                <span>Edit Profile</span>
                                <Edit3 className="w-4 h-4 lg:w-5 lg:h-5 group-hover:translate-x-1 transition-transform" />
                            </button>
                        </div>
                    )}
                </div>

                {/* Desktop Tabs */}
                <div className="border-t border-slate-100 bg-white relative z-20 hidden lg:block">
                    <div className="w-full px-8">
                        <div className="flex overflow-x-auto no-scrollbar gap-8">
                            {(Object.keys(TAB_LABELS) as Array<keyof typeof TAB_LABELS>).map(format => (
                                <button
                                    key={format}
                                    onClick={() => setActiveTab(format as typeof activeTab)}
                                    className={`relative py-4 text-sm font-bold uppercase tracking-widest transition-colors whitespace-nowrap border-b-2
                                        ${activeTab === format ? 'text-emerald-600 border-emerald-600' : 'text-slate-400 hover:text-slate-900 border-transparent hover:border-slate-200'}
                                    `}
                                >
                                    {TAB_LABELS[format]}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Mobile Tabs */}
                <div className="border-t border-slate-200 bg-white sticky top-0 z-40 lg:hidden">
                    <div className="flex overflow-x-auto no-scrollbar px-4 gap-6">
                        {(Object.keys(TAB_LABELS) as Array<keyof typeof TAB_LABELS>).map(format => (
                            <button
                                key={format}
                                onClick={() => setActiveTab(format as typeof activeTab)}
                                className={`relative py-3 text-xs font-bold uppercase tracking-widest transition-colors whitespace-nowrap border-b-2
                                    ${activeTab === format ? 'text-emerald-600 border-emerald-600' : 'text-slate-400 hover:text-slate-900 border-transparent'}
                                `}
                            >
                                {TAB_LABELS[format]}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Top Metrics Ribbon */}
                {formatData && (
                    <div className="border-t border-slate-200 bg-slate-50">
                        <div className="w-full px-4 sm:px-6 lg:px-8 py-4 lg:py-6">
                            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-12 divide-x-0 lg:divide-x divide-slate-200">
                                <div className="bg-white lg:bg-transparent p-4 lg:p-0 rounded-lg lg:rounded-none border border-slate-200 lg:border-none flex flex-col lg:px-4 shadow-sm lg:shadow-none">
                                    <span className="text-[10px] lg:text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Matches Played</span>
                                    <span className="text-3xl lg:text-4xl text-slate-800" style={DISPLAY_FONT}>{formatData.matches_played}</span>
                                </div>
                                <div className="bg-white lg:bg-transparent p-4 lg:p-0 rounded-lg lg:rounded-none border border-slate-200 lg:border-none flex flex-col lg:px-4 shadow-sm lg:shadow-none">
                                    <span className="text-[10px] lg:text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Career Wins</span>
                                    <span className="text-3xl lg:text-4xl text-emerald-600" style={DISPLAY_FONT}>{formatData.matches_won}</span>
                                </div>
                                <div className="bg-white lg:bg-transparent p-4 lg:p-0 rounded-lg lg:rounded-none border border-slate-200 lg:border-none flex flex-col lg:px-4 shadow-sm lg:shadow-none">
                                    <span className="text-[10px] lg:text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">Win Rate</span>
                                    <span className="text-3xl lg:text-4xl text-slate-800" style={DISPLAY_FONT}>{winRate}<span className="text-lg lg:text-2xl text-slate-400">%</span></span>
                                </div>
                                <div className="bg-white lg:bg-transparent p-4 lg:p-0 rounded-lg lg:rounded-none border border-slate-200 lg:border-none flex flex-col lg:px-4 shadow-sm lg:shadow-none">
                                    <span className="text-[10px] lg:text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">
                                        {activeTab === 'tournament' ? 'Champion Titles' : 'Major Titles'}
                                    </span>
                                    <div className="flex items-center gap-2 text-3xl lg:text-4xl">
                                        <span className="text-orange-500" style={DISPLAY_FONT}>{activeTab === 'tournament' ? formatData.tournaments_won || 0 : formatData.total_titles || 0}</span>
                                        <span className="text-2xl lg:text-3xl">🏆</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </header>

            {/* Main Content Grid */}
            <main className="w-full px-4 sm:px-6 lg:px-8 py-8 lg:py-12 grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 relative z-0">
                <div className="lg:col-span-8 flex flex-col gap-8 lg:gap-12">

                    {/* CPU Match Start */}
                    {activeTab === 'cpu' && (
                        <div className="bg-slate-900 rounded-xl p-6 shadow-xl text-white flex flex-col sm:flex-row items-center justify-between gap-4 border border-slate-800">
                            <div>
                                <h3 className="text-2xl uppercase italic tracking-wide" style={DISPLAY_FONT}>Quick CPU Match</h3>
                                <p className="text-slate-400 text-xs font-medium uppercase tracking-widest">Single-player practice vs AI</p>
                            </div>
                            <button
                                onClick={startCpuMatch}
                                disabled={cpuLoading}
                                className="w-full sm:w-auto bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white px-8 py-3 rounded text-sm font-bold uppercase tracking-widest transition-colors shadow-lg shadow-emerald-500/20"
                            >
                                {cpuLoading ? 'STARTING...' : 'START MATCH 🏏'}
                            </button>
                        </div>
                    )}

                    {!formatData || formatData.matches_played === 0 ? (
                        <div className="bg-white border text-center p-12 rounded-xl">
                            <span className="text-5xl opacity-50 mb-4 inline-block">🏃</span>
                            <h3 className="text-2xl uppercase tracking-wide text-slate-900" style={DISPLAY_FONT}>No matches yet</h3>
                            <p className="text-sm font-medium text-slate-500 mt-2 uppercase tracking-wide">Play {TAB_LABELS[activeTab]} to populate stats.</p>
                        </div>
                    ) : (
                        <>
                            {/* Batting Stats */}
                            <section>
                                <div className="flex items-center gap-3 mb-4 lg:mb-6 border-b border-slate-200 pb-3">
                                    <div className="w-8 h-8 lg:w-10 lg:h-10 bg-slate-100 rounded flex items-center justify-center text-slate-900">
                                        <span className="text-lg lg:text-xl transform -rotate-45">🏏</span>
                                    </div>
                                    <h2 className="text-2xl lg:text-3xl text-slate-900 uppercase tracking-wide" style={DISPLAY_FONT}>Batting Performance</h2>
                                </div>
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 lg:gap-4">
                                    <div className="p-4 lg:p-5 border border-slate-200 bg-white hover:border-emerald-400 transition-colors group rounded-md lg:rounded-none">
                                        <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 group-hover:text-emerald-600 mb-1 lg:mb-2">Total Runs</div>
                                        <div className="text-3xl lg:text-4xl text-slate-900" style={DISPLAY_FONT}>{formatData.total_runs}</div>
                                    </div>
                                    <div className="p-4 lg:p-5 border border-slate-200 bg-white hover:border-emerald-400 transition-colors group rounded-md lg:rounded-none">
                                        <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 group-hover:text-emerald-600 mb-1 lg:mb-2">Highest Score</div>
                                        <div className="text-3xl lg:text-4xl text-slate-900" style={DISPLAY_FONT}>{formatData.highest_score}</div>
                                    </div>
                                    <div className="p-4 lg:p-5 border border-slate-200 bg-white hover:border-emerald-400 transition-colors group rounded-md lg:rounded-none">
                                        <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 group-hover:text-emerald-600 mb-1 lg:mb-2">Batting Avg</div>
                                        <div className="text-3xl lg:text-4xl text-slate-900" style={DISPLAY_FONT}>{formatData.avg_runs.toFixed(2)}</div>
                                    </div>
                                    <div className="p-4 lg:p-5 border border-slate-200 bg-white hover:border-emerald-400 transition-colors group rounded-md lg:rounded-none">
                                        <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 group-hover:text-emerald-600 mb-1 lg:mb-2">Strike Rate</div>
                                        <div className="text-3xl lg:text-4xl text-slate-900" style={DISPLAY_FONT}>{formatData.avg_strike_rate.toFixed(2)}</div>
                                    </div>
                                    <div className="p-4 lg:p-5 border border-slate-200 bg-white hover:border-emerald-400 transition-colors group rounded-md lg:rounded-none">
                                        <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 group-hover:text-emerald-600 mb-1 lg:mb-2">Fours</div>
                                        <div className="text-3xl lg:text-4xl text-slate-900" style={DISPLAY_FONT}>{formatData.fours}</div>
                                    </div>
                                    <div className="p-4 lg:p-5 border border-slate-200 bg-white hover:border-emerald-400 transition-colors group rounded-md lg:rounded-none">
                                        <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 group-hover:text-emerald-600 mb-1 lg:mb-2">Sixes</div>
                                        <div className="text-3xl lg:text-4xl text-slate-900" style={DISPLAY_FONT}>{formatData.sixes}</div>
                                    </div>
                                    <div className="p-4 lg:p-5 border border-slate-200 bg-white hover:border-emerald-400 transition-colors group rounded-md lg:rounded-none">
                                        <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 group-hover:text-emerald-600 mb-1 lg:mb-2">Fifties</div>
                                        <div className="text-3xl lg:text-4xl text-emerald-600" style={DISPLAY_FONT}>{formatData.fifties}</div>
                                    </div>
                                    <div className="p-4 lg:p-5 border border-slate-200 bg-slate-50 opacity-90 rounded-md lg:rounded-none">
                                        <div className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1 lg:mb-2">Hundreds</div>
                                        <div className="text-3xl lg:text-4xl text-slate-400" style={DISPLAY_FONT}>{formatData.hundreds}</div>
                                    </div>
                                </div>
                            </section>

                            {/* Bowling Stats */}
                            <section>
                                <div className="flex items-center gap-3 mb-4 lg:mb-6 border-b border-slate-200 pb-3">
                                    <div className="w-8 h-8 lg:w-10 lg:h-10 bg-slate-100 rounded flex items-center justify-center text-slate-900">
                                        <span className="text-lg lg:text-xl">🎯</span>
                                    </div>
                                    <h2 className="text-2xl lg:text-3xl text-slate-900 uppercase tracking-wide" style={DISPLAY_FONT}>Bowling Performance</h2>
                                </div>
                                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 lg:gap-4">
                                    <div className="p-4 lg:p-6 border border-slate-200 bg-white flex flex-row sm:flex-col justify-between items-center sm:items-stretch sm:h-32 hover:border-emerald-400 transition-colors rounded-md lg:rounded-none">
                                        <div className="flex flex-col sm:flex-row justify-between sm:items-start order-2 sm:order-1 ml-4 sm:ml-0 text-right sm:text-left">
                                            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Total Wickets</span>
                                            <span className="text-3xl sm:block hidden opacity-20">🎯</span>
                                        </div>
                                        <div className="text-4xl lg:text-5xl text-slate-900 order-1 sm:order-2" style={DISPLAY_FONT}>{formatData.wickets_taken}</div>
                                    </div>
                                    <div className="p-4 lg:p-6 border border-slate-200 bg-emerald-50 lg:bg-white lg:hover:shadow-md flex flex-row sm:flex-col justify-between items-center sm:items-stretch sm:h-32 transition-shadow rounded-md lg:rounded-none relative overflow-hidden group">
                                        <div className="absolute -right-4 -top-4 text-emerald-100 lg:group-hover:text-emerald-50 transition-colors opacity-50 sm:opacity-100 pointer-events-none hidden sm:block">
                                            <span className="text-7xl">⭐</span>
                                        </div>
                                        <div className="flex flex-col sm:flex-row justify-between sm:items-start order-2 sm:order-1 ml-4 sm:ml-0 text-right sm:text-left z-10">
                                            <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-800 lg:text-slate-400">Best Figures</span>
                                        </div>
                                        <div className="text-4xl lg:text-5xl text-emerald-600 order-1 sm:order-2 z-10" style={DISPLAY_FONT}>{formatData.best_bowling}</div>
                                    </div>
                                    <div className="p-4 lg:p-6 border border-slate-200 bg-white flex flex-row sm:flex-col justify-between items-center sm:items-stretch sm:h-32 hover:border-emerald-400 transition-colors rounded-md lg:rounded-none relative overflow-hidden">
                                        <div className="flex flex-col sm:flex-row justify-between sm:items-start order-2 sm:order-1 ml-4 sm:ml-0 text-right sm:text-left z-10">
                                            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">Bowling Avg</span>
                                        </div>
                                        <div className="text-4xl lg:text-5xl text-slate-900 order-1 sm:order-2 z-10" style={DISPLAY_FONT}>{formatData.bowling_average.toFixed(2)}</div>
                                    </div>
                                </div>
                            </section>

                            {/* Tournament History Cards */}
                            {(activeTab === 'overall' || activeTab === 'tournament') && tournamentHistory.length > 0 && (
                                <section>
                                    <div className="flex items-center justify-between mb-4 lg:mb-6 border-b border-slate-200 pb-3">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 bg-slate-100 rounded flex items-center justify-center text-slate-900">
                                                <span className="text-lg">🏆</span>
                                            </div>
                                            <h2 className="text-2xl lg:text-3xl text-slate-900 uppercase tracking-wide leading-none" style={DISPLAY_FONT}>Tournament History</h2>
                                        </div>
                                    </div>

                                    <div className="flex overflow-x-auto lg:grid lg:grid-cols-3 gap-4 pb-4 lg:pb-0 -mx-4 px-4 lg:mx-0 lg:px-0 no-scrollbar snap-x snap-mandatory">
                                        {tournamentHistory.map(t => {
                                            const isChamp = t.champion === username
                                            const isRunnerUp = !isChamp && t.players.includes(username) // Rough proxy for participated in final

                                            // Extract personal stats if possible (fallback logic if personal stats aren't directly available in t)
                                            // The backend returns orange_cap and purple_cap across tournament, we show those if username earned them.
                                            const gotOrange = t.orange_cap?.player === username
                                            const gotPurple = t.purple_cap?.player === username

                                            return (
                                                <div
                                                    key={t.tournament_id}
                                                    onClick={() => navigate(`/tournament/${t.tournament_id}`)}
                                                    role="button"
                                                    tabIndex={0}
                                                    onKeyDown={(e) => e.key === 'Enter' && navigate(`/tournament/${t.tournament_id}`)}
                                                    className={`snap-center min-w-[280px] lg:min-w-0 rounded-lg lg:rounded-none p-5 lg:p-6 relative overflow-hidden transition-all border cursor-pointer active:scale-[0.98] ${isChamp ? 'bg-slate-900 text-white border-slate-800 shadow-xl hover:shadow-2xl' : 'bg-white border-slate-200 lg:hover:shadow-lg hover:border-emerald-300'}`}>
                                                    <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none">
                                                        <span className="text-6xl">{isChamp ? '👑' : '🏆'}</span>
                                                    </div>

                                                    <div className={`text-[10px] font-bold uppercase tracking-widest mb-2 lg:mb-3 ${isChamp ? 'text-emerald-400' : 'text-slate-400'}`}>
                                                        {new Date(t.timestamp).toLocaleDateString()}
                                                    </div>
                                                    <h3 className={`text-2xl lg:text-3xl mb-1 leading-none ${isChamp ? 'text-white' : 'text-slate-900'}`} style={DISPLAY_FONT}>
                                                        Tournament {t.tournament_id.substring(0, 4)}
                                                    </h3>

                                                    <div className={`flex items-center gap-1.5 mb-5 lg:mb-6 font-bold text-[10px] lg:text-xs uppercase tracking-wide ${isChamp ? 'text-orange-400' : isRunnerUp ? 'text-slate-400' : 'text-slate-400'}`}>
                                                        {isChamp ? '🥇 Champion' : isRunnerUp ? '🥈 Participant' : 'Participant'}
                                                    </div>

                                                    <div className={`space-y-2 lg:space-y-2.5 border-t pt-3 lg:pt-4 ${isChamp ? 'border-slate-700' : 'border-slate-100'}`}>
                                                        {gotOrange && (
                                                            <div className="flex justify-between text-sm">
                                                                <span className={isChamp ? 'text-slate-400' : 'text-slate-500'}>Orange Cap</span>
                                                                <span className={`font-bold ${isChamp ? 'text-white' : 'text-slate-900'}`}>{t.orange_cap?.runs} Runs</span>
                                                            </div>
                                                        )}
                                                        {gotPurple && (
                                                            <div className="flex justify-between text-sm">
                                                                <span className={isChamp ? 'text-slate-400' : 'text-slate-500'}>Purple Cap</span>
                                                                <span className={`font-bold ${isChamp ? 'text-white' : 'text-slate-900'}`}>{t.purple_cap?.wickets} Wkts</span>
                                                            </div>
                                                        )}
                                                        {!gotOrange && !gotPurple && (
                                                            <div className="flex justify-between text-sm">
                                                                <span className={isChamp ? 'text-slate-400' : 'text-slate-500'}>Status</span>
                                                                <span className={`font-bold ${isChamp ? 'text-white' : 'text-slate-900'}`}>Completed</span>
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            )
                                        })}
                                    </div>
                                </section>
                            )}
                        </>
                    )}
                </div>

                {/* Right Column: Match Archive (Sticky on Desktop) */}
                <div className="lg:col-span-4 mt-4 lg:mt-0">
                    <div className="bg-white lg:border border-slate-200 lg:sticky lg:top-24 rounded-lg lg:rounded-none overflow-hidden border border-slate-100 shadow-sm lg:shadow-none">
                        <div className="p-4 lg:p-6 border-b border-slate-200 bg-slate-50">
                            <h3 className="text-xl lg:text-2xl text-slate-900 uppercase tracking-wide flex items-center gap-2 leading-none" style={DISPLAY_FONT}>
                                <span className="text-slate-400 mt-1">🕒</span>
                                Match Archive
                            </h3>
                            <p className="text-xs text-slate-500 font-medium mt-1">Last 10 competitive matches</p>
                        </div>

                        <div className="divide-y divide-slate-100">
                            {matchHistory.length === 0 ? (
                                <div className="p-8 text-center text-sm font-medium text-slate-500">No matches found for this mode.</div>
                            ) : matchHistory.map((m) => {
                                const opponent = m.side_a.includes(username) ? m.side_b.join(', ') : m.side_a.join(', ')
                                const winnerNames = (m.winner ?? '')
                                    .split(',')
                                    .map(n => n.trim())
                                    .filter(Boolean)
                                const isWin = winnerNames.includes(username)
                                const isTie = m.winner === 'TIE'
                                const isCancelled = m.winner === null && m.result_text.toLowerCase().includes('cancelled')
                                const displayMode = m.mode === '2v2' ? 'TEAM' : m.mode.toUpperCase()

                                return (
                                    <button
                                        key={m.match_id}
                                        onClick={() => navigate(`/match/${m.match_id}`)}
                                        className="w-full text-left p-4 hover:bg-slate-50 transition-colors group cursor-pointer block"
                                    >
                                        <div className="flex items-start justify-between mb-2">
                                            <div className="flex items-center gap-2">
                                                <span className={`flex items-center justify-center w-5 h-5 lg:w-6 lg:h-6 rounded text-[10px] lg:text-xs font-bold leading-none
                                                    ${isTie ? 'bg-orange-100 text-orange-700' : isWin ? 'bg-emerald-100 text-emerald-700' : isCancelled ? 'bg-slate-200 text-slate-600' : 'bg-red-100 text-red-700'}`}>
                                                    {isCancelled ? '-' : isTie ? 'T' : isWin ? 'W' : 'L'}
                                                </span>
                                                <span className="text-[10px] lg:text-xs font-bold uppercase text-slate-500 tracking-wider truncate max-w-[150px]">
                                                    vs {opponent || 'UNKNOWN'}
                                                </span>
                                            </div>
                                            <span className="text-[10px] text-slate-400 font-bold tracking-wide">
                                                {new Date(m.timestamp).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}
                                            </span>
                                        </div>
                                        <div className="flex justify-between items-end">
                                            <div className="flex-1 min-w-0 pr-2">
                                                <div className={`text-sm font-bold truncate ${isCancelled ? 'line-through decoration-slate-400 text-slate-500' : 'text-slate-800'}`}>
                                                    {m.result_text}
                                                </div>
                                                <div className="flex gap-1.5 mt-1.5 flex-wrap">
                                                    <span className="px-1.5 py-0.5 bg-slate-100 text-slate-600 text-[9px] uppercase font-bold tracking-widest rounded leading-none">{displayMode}</span>
                                                    {m.potm === username && (
                                                        <span className="px-1.5 py-0.5 bg-yellow-100 text-yellow-700 text-[9px] uppercase font-bold tracking-widest rounded leading-none">POTM</span>
                                                    )}
                                                </div>
                                            </div>
                                            <ChevronRight className="w-5 h-5 text-slate-200 group-hover:text-emerald-500 transition-colors flex-shrink-0" />
                                        </div>
                                    </button>
                                )
                            })}
                        </div>
                    </div>
                </div>
            </main>

            {/* Footer */}
            <footer className="bg-white border-t border-slate-200 py-8 lg:py-12 mt-8 lg:mt-0 pb-24 lg:pb-12 text-center lg:text-left">
                <div className="w-full px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-4 lg:gap-6">
                    <div className="flex items-center justify-center lg:justify-start gap-3">
                        <span className="text-xl lg:text-2xl text-slate-900 tracking-tight uppercase" style={DISPLAY_FONT}>
                            CRICKET<span className="text-emerald-600">PRO</span>
                        </span>
                        <span className="text-[10px] lg:text-xs text-slate-400 font-bold tracking-widest px-2 border-l border-slate-300">v2.4.0</span>
                    </div>
                    <div className="text-slate-400 text-[10px] lg:text-sm font-medium uppercase tracking-wider">
                        © 2026 Sports Interactive. All rights reserved.
                    </div>
                </div>
            </footer>
        </div>
    )
}
