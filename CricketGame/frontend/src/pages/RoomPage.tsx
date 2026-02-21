/**
 * RoomPage — The main game hub.
 * Handles: Room creation/joining, lobby, toss, game, scorecard, and tournament.
 * Uses a WebSocket for real-time communication with the backend.
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { LogOut, Copy, User } from 'lucide-react'
import Lobby from '@/components/Lobby'
import TossScreen from '@/components/TossScreen'
import GameBoard from '@/components/GameBoard'
import Scorecard from '@/components/Scorecard'
import StandingsView from '@/components/StandingsView'

// Types
interface LobbyData {
    players: Array<{ username: string; team: string | null; is_captain: boolean; in_match: boolean }>
    host: string
    mode: string
    overs: number
    wickets: number
    teams: Record<string, string[]>
    team_names: Record<string, string>
    captains: Record<string, string | null>
    room_code: string
    cpu_enabled?: boolean
    cpu_only?: boolean
    cpu_count?: number
    host_plays?: boolean
}

interface BatCard {
    name: string; runs: number; balls: number; fours: number; sixes: number; sr: number; dismissal: string; is_out: boolean
}
interface BowlCard {
    name: string; overs: string; runs: number; wickets: number; econ: number
}
interface StandingsEntry {
    player: string; played: number; won: number; lost: number; tied: number; points: number; nrr: number
}
interface TournamentPayload {
    standings: StandingsEntry[]
    phase: string
    upcoming_matches?: Array<{ label: string; teams: string[] }>
}

interface MatchState {
    mode: string
    innings: number
    batting_side: string[]
    bowling_side: string[]
    striker: string
    non_striker: string | null
    bowler: string
    total_runs: number
    wickets: number
    overs: string
    total_overs: number
    target: number | null
    batting_card: BatCard[]
    bowling_card: BowlCard[]
    my_role: string
    bat_ready?: boolean
    bowl_ready?: boolean
    tournament?: TournamentPayload
    needs_batter_choice?: boolean
    needs_bowler_choice?: boolean
    available_batters?: Array<{ player: string; disabled: boolean }>
    available_bowlers?: Array<{ player: string; disabled: boolean }>
    batting_captain?: string | null
    bowling_captain?: string | null
}

type Screen = 'home' | 'lobby' | 'toss' | 'toss_result' | 'toss_choose' | 'toss_decision' | 'game' | 'scorecard' | 'standings' | 'tournament_over'

interface Props {
    token: string
    username: string
    onLogout: () => void
}

const API = (import.meta.env.VITE_API_BASE_URL ?? window.location.origin).replace(/\/$/, '')
const WS_BASE = (import.meta.env.VITE_WS_BASE_URL ?? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`).replace(/\/$/, '')

export default function RoomPage({ token, username, onLogout }: Props) {
    const { roomCode: urlRoomCode } = useParams<{ roomCode: string }>()
    const navigate = useNavigate()

    const initialScreen = (() => {
        const params = new URLSearchParams(window.location.search)
        const urlScreen = params.get('screen') as Screen | null
        if (urlScreen) return urlScreen
        return urlRoomCode ? 'lobby' : 'home'
    })()
    const [screen, setScreen] = useState<Screen>(initialScreen)
    const [roomCode, setRoomCode] = useState(urlRoomCode ?? '')
    const [joinCode, setJoinCode] = useState('')

    // Game state
    const [lobby, setLobby] = useState<LobbyData | null>(null)
    const [matchState, setMatchState] = useState<MatchState | null>(null)
    const [tossData, setTossData] = useState<Record<string, unknown>>({})
    const [scorecardData, setScorecardData] = useState<Record<string, unknown>>({})
    const [standingsData, setStandingsData] = useState<Record<string, unknown>>({})
    const [ballFlash, setBallFlash] = useState<Record<string, unknown> | null>(null)
    const [error, setError] = useState('')
    const [serverIP, setServerIP] = useState<string | null>(null)
    // Countdown timer: sent by COUNTDOWN server event, counts down locally
    const [countdown, setCountdown] = useState<{ role: string; seconds: number } | null>(null)
    const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null)

    const wsRef = useRef<WebSocket | null>(null)

    // Update URL when screen changes
    useEffect(() => {
        const params = new URLSearchParams(window.location.search)
        if (screen === 'home') {
            window.history.replaceState({}, '', '/')
        } else {
            params.set('screen', screen)
            window.history.replaceState({}, '', `?${params.toString()}`)
        }
    }, [screen])

    // WebSocket message handler
    const handleWsMessage = useCallback((msg: Record<string, unknown>) => {
        const type = msg.type as string

        switch (type) {
            case 'LOBBY_UPDATE':
                setLobby(msg as unknown as LobbyData)
                if (screen === 'home') setScreen('lobby')
                break

            case 'TOSS_CALLER':
            case 'TOSS_WAITING':
                setTossData(msg)
                setScreen('toss')
                break

            case 'TOSS_RESULT':
                setTossData(msg)
                setScreen('toss_result')
                break

            case 'TOSS_CHOOSE':
                setScreen('toss_choose')
                break

            case 'TOSS_DECISION':
                setTossData(msg)
                setScreen('toss_decision')
                setTimeout(() => setScreen('game'), 3000)
                break

            case 'MATCH_STATE':
                setMatchState(msg as unknown as MatchState)
                if (screen !== 'game') setScreen('game')
                break

            case 'BALL_RESULT':
                setBallFlash(msg)
                setTimeout(() => setBallFlash(null), 1500)
                // Clear any running countdown — ball was resolved
                if (countdownRef.current) clearInterval(countdownRef.current)
                setCountdown(null)
                break

            case 'COUNTDOWN': {
                // Fresh countdown from server (role: bat | bowl | captain, seconds: N)
                if (countdownRef.current) clearInterval(countdownRef.current)
                const role = msg.role as string
                const seconds = msg.seconds as number
                setCountdown({ role, seconds })
                countdownRef.current = setInterval(() => {
                    setCountdown(prev => {
                        if (!prev || prev.seconds <= 1) {
                            if (countdownRef.current) clearInterval(countdownRef.current!)
                            return null
                        }
                        return { ...prev, seconds: prev.seconds - 1 }
                    })
                }, 1000)
                break
            }

            case 'INNINGS_BREAK':
                // Brief pause handled by server, next MATCH_STATE comes automatically
                break

            case 'MATCH_OVER':
                setScorecardData(msg)
                setScreen('scorecard')
                setMatchState(null)
                break

            case 'MATCH_CANCELLED':
                setMatchState(null)
                if (msg.tournament) {
                    setStandingsData(msg.tournament as Record<string, unknown>)
                    setScreen('standings')
                    setError(msg.msg as string)
                    setTimeout(() => setError(''), 5000)
                } else {
                    setScreen('lobby')
                    setError(msg.msg as string)
                    setTimeout(() => setError(''), 5000)
                }
                break

            case 'TOURNAMENT_STANDINGS':
                setStandingsData(msg)
                if (screen !== 'game' && screen !== 'toss' && screen !== 'scorecard') setScreen('standings')
                break

            case 'TOURNAMENT_PHASE':
                // Tournament match announcement
                setStandingsData(msg)
                break

            case 'TOURNAMENT_OVER':
                setStandingsData(msg)
                if (msg.tournament_id) {
                    navigate(`/tournament/${msg.tournament_id as string}`)
                    setScreen('lobby')
                } else {
                    setScreen('tournament_over')
                }
                break

            case 'ERROR':
                setError(msg.msg as string)
                setTimeout(() => setError(''), 5000)
                break

            case 'AUTO_MOVE_WARNING': {
                const strikes = msg.strikes as number
                const max = msg.max as number
                const player = msg.player as string
                setError(`️ ${player} is taking too long! (${strikes}/${max} auto-plays used)`)
                setTimeout(() => setError(''), 4000)
                break
            }

            case 'CHOOSE_BATTER':
            case 'CHOOSE_BOWLER':
                // These events come from the backend to announce captain selection.
                // The actual picker UI is driven by MATCH_STATE (my_role), so no extra state needed.
                // Just show a brief notification for non-captain players.
                break
        }
    }, [screen, navigate])

    // Ref to hold the latest message handler (prevents WebSocket reconnection on state changes)
    const handleWsMessageRef = useRef(handleWsMessage)
    useEffect(() => {
        handleWsMessageRef.current = handleWsMessage
    }, [handleWsMessage])

    // Fetch server's local IP on mount for LAN play
    useEffect(() => {
        const fetchServerIP = async () => {
            try {
                const res = await fetch(`${API}/network/local-ip`)
                const data = await res.json()
                if (data.local_ip && data.local_ip !== 'localhost' && !data.local_ip.startsWith('127.')) {
                    setServerIP(data.local_ip)
                }
            } catch {
                // Could not fetch server IP, continue with localhost
            }
        }
        fetchServerIP()
    }, [])

    // Connect WebSocket
    const connectWs = useCallback((code: string) => {
        if (wsRef.current) {
            wsRef.current.close()
        }

        const wsUrl = `${WS_BASE}/ws/${code}?token=${token}`
        const ws = new WebSocket(wsUrl)

        ws.onopen = () => {
            console.log(' Connected to room', code)
            setRoomCode(code)
            setScreen('lobby')
        }

        ws.onmessage = (evt) => {
            try {
                const msg = JSON.parse(evt.data)
                handleWsMessageRef.current(msg)
            } catch {
                console.error('Invalid message from server')
            }
        }

        ws.onclose = (evt) => {
            console.log(' Disconnected from room', evt.code, evt.reason)
            if (evt.code === 4001) {
                // Token expired or invalid — force re-login
                onLogout()
                return
            }
            if (evt.code === 4004) {
                setError(evt.reason || 'Room not found.')
            }
        }

        ws.onerror = () => {
            // Only set generic error if we haven't set a specific one
            setError((prev) => prev || 'WebSocket connection failed.')
        }

        wsRef.current = ws
    }, [token, onLogout])

    // Auto-connect if URL has room code
    useEffect(() => {
        if (urlRoomCode && !wsRef.current) {
            connectWs(urlRoomCode)
        }
        return () => {
            wsRef.current?.close()
            wsRef.current = null  // Null the ref to allow reconnection
        }
    }, [urlRoomCode, connectWs])

    // Send to server
    const sendMsg = useCallback((msg: Record<string, unknown>) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(msg))
        }
    }, [])

    // Room creation
    const createRoom = async () => {
        try {
            const res = await fetch(`${API}/rooms?token=${token}`, { method: 'POST' })
            const data = await res.json()
            if (res.ok) {
                const code = data.room_code as string
                navigate(`/room/${code}`)
                // Connection is handled by useEffect when URL changes
            } else {
                setError(data.detail || 'Failed to create room.')
            }
        } catch {
            setError('Cannot connect to server.')
        }
    }

    // Room joining
    const joinRoom = () => {
        const code = joinCode.trim().toUpperCase()
        if (!code) return
        navigate(`/room/${code}`)
        // Connection is handled by useEffect when URL changes
    }

    const backToLobby = () => {
        setScreen('lobby')
        setMatchState(null)
    }

    // Generate shareable link — always prefer LAN IP when available (so friends on the same network can connect)
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    const shareLink = serverIP && isLocalhost
        ? `http://${serverIP}:${window.location.port}/room/${roomCode}`
        : `${window.location.origin}/room/${roomCode}`
    // Short display version: just IP:port/room/code
    const shareLinkDisplay = serverIP && isLocalhost
        ? `${serverIP}:${window.location.port}/room/${roomCode}`
        : shareLink

    // ── Render ──

    if (screen === 'home') {
        return (
            <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
                <div className="w-full max-w-lg space-y-6">
                    {/* Header */}
                    <div className="text-center space-y-3 mb-8">
                        <h1 className="text-5xl font-extrabold text-slate-900 flex items-center justify-center gap-3">
                            <span className="text-emerald-600">🏏</span> E Cricket
                        </h1>
                        <p className="text-xl text-slate-600">Welcome, <span className="font-semibold text-emerald-700">{username}</span>!</p>
                    </div>

                    {/* Create Room Card */}
                    <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm">
                        <h3 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
                            Create a Room
                        </h3>
                        <Button
                            onClick={createRoom}
                            className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-6 text-lg shadow-sm transition-all rounded-xl"
                            size="lg"
                        >
                            Create New Room
                        </Button>
                        <p className="text-xs text-slate-500 mt-3 text-center">
                            You'll be the host. Share the room link with friends.
                        </p>
                    </div>

                    {/* Join Room Card */}
                    <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm">
                        <h3 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
                            Join a Room
                        </h3>
                        <div className="space-y-3">
                            <Input
                                placeholder="Enter room code (e.g. ABC123)"
                                value={joinCode}
                                onChange={e => setJoinCode(e.target.value.toUpperCase())}
                                onKeyDown={e => e.key === 'Enter' && joinRoom()}
                                className="bg-white border-slate-200 text-slate-900 placeholder:text-slate-400 focus:border-emerald-500 focus:ring-emerald-500/20"
                            />
                            <Button
                                onClick={joinRoom}
                                variant="secondary"
                                className="w-full bg-slate-900 hover:bg-slate-800 text-white font-semibold py-6 text-lg shadow-sm transition-all rounded-xl"
                            >
                                Join Room
                            </Button>
                        </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex gap-3 justify-center pt-2">
                        <Button
                            variant="outline"
                            onClick={() => navigate('/profile')}
                            className="flex items-center gap-2 bg-white border-slate-300 text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                        >
                            View Profile
                        </Button>
                        <Button
                            variant="ghost"
                            onClick={onLogout}
                            className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                            Logout
                        </Button>
                    </div>

                    {error && (
                        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-center">
                            <p className="text-red-600 font-medium">{error}</p>
                        </div>
                    )}
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-[100dvh] sm:min-h-screen flex flex-col bg-slate-50 overflow-y-auto sm:overflow-hidden">
            {/* Header Area */}
            <div className="flex-shrink-0 z-20 relative">
                {/* ─── Top Nav: Editorial Style ─── */}
                <nav className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-200">
                    <div className="w-full px-4 sm:px-6 lg:px-8">
                        <div className="flex items-center justify-between h-14 lg:h-20">
                            {/* Left: Brand + Room Code */}
                            <div className="flex items-center gap-3 lg:gap-6">
                                <div className="flex items-center gap-2">
                                    <span className="text-emerald-500 text-2xl lg:text-3xl -rotate-12">🏏</span>
                                    <span className="text-xl lg:text-2xl uppercase tracking-wider italic" style={{ fontFamily: "'Anton', 'Bebas Neue', sans-serif" }}>E Cricket</span>
                                </div>
                                {roomCode && (
                                    <>
                                        <div className="h-8 w-px bg-slate-200 hidden lg:block" />
                                        {/* Desktop room code */}
                                        <div className="hidden lg:flex items-center bg-slate-100 rounded px-3 py-1.5 border border-slate-200">
                                            <span className="text-xs font-bold text-slate-500 uppercase mr-2 tracking-wider">Room Code</span>
                                            <span className="font-mono font-bold text-slate-900 tracking-widest">{roomCode}</span>
                                        </div>
                                        {/* Mobile room code */}
                                        <div className="lg:hidden flex items-center gap-2 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200">
                                            <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">Code</span>
                                            <span className="font-mono font-bold text-slate-900 text-sm">{roomCode}</span>
                                        </div>
                                    </>
                                )}
                            </div>

                            {/* Right: User + Actions */}
                            <div className="flex items-center gap-3 lg:gap-6">
                                {/* Desktop: full actions */}
                                <div className="hidden lg:flex items-center gap-4">
                                    <div className="flex items-center gap-2">
                                        <div className="w-8 h-8 rounded bg-emerald-500 text-white flex items-center justify-center font-bold text-sm" style={{ fontFamily: "'Anton', sans-serif" }}>
                                            {username.charAt(0).toUpperCase()}
                                        </div>
                                        <span className="text-sm font-bold text-slate-900">{username}</span>
                                    </div>
                                    <button
                                        onClick={() => { navigate('/'); setScreen('home'); }}
                                        className="text-sm font-medium text-slate-500 hover:text-emerald-500 transition-colors"
                                    >
                                        Home
                                    </button>
                                    {serverIP && isLocalhost && (
                                        <div className="flex items-center bg-slate-50 rounded border border-slate-200 pl-3 pr-1 py-1 gap-2">
                                            <span className="text-xs font-mono text-slate-400 truncate max-w-[100px]">{shareLinkDisplay}</span>
                                            <button
                                                className="text-xs font-bold uppercase tracking-wider bg-white border border-slate-200 hover:border-emerald-500 hover:text-emerald-500 px-3 py-1 rounded transition-all shadow-sm"
                                                onClick={() => {
                                                    navigator.clipboard.writeText(shareLink).then(() => {
                                                        if (serverIP && isLocalhost) {
                                                            setError(`LAN link copied: ${shareLink}`)
                                                        } else if (isLocalhost) {
                                                            setError(`Copied localhost link — server IP unavailable. Link: ${shareLink}`)
                                                        } else {
                                                            setError('Link copied!')
                                                        }
                                                        setTimeout(() => setError(''), 5000)
                                                    }).catch(() => {
                                                        setError(`Copy manually: ${shareLink}`)
                                                        setTimeout(() => setError(''), 10000)
                                                    })
                                                }}
                                            >
                                                Copy Link
                                            </button>
                                        </div>
                                    )}
                                </div>
                                {/* Mobile: logout icon */}
                                <button
                                    onClick={onLogout}
                                    className="text-slate-400 hover:text-red-500 transition-colors lg:hidden"
                                >
                                    <LogOut className="w-5 h-5" />
                                </button>
                                {/* Desktop: logout button */}
                                <button
                                    onClick={onLogout}
                                    className="hidden lg:flex text-sm font-bold text-red-500 hover:text-red-700 uppercase tracking-widest border border-red-100 bg-red-50 hover:bg-red-100 px-4 py-2 rounded transition-colors"
                                >
                                    Logout
                                </button>
                            </div>
                        </div>
                    </div>
                </nav>

                {/* Sub-Header for lobby (mobile copy link + home) */}
                {screen === 'lobby' && (
                    <div className="bg-slate-50 border-b border-slate-200 px-4 sm:px-6 py-2 flex items-center justify-between text-sm lg:hidden">
                        <div className="flex items-center gap-2 text-slate-600">
                            <User className="w-4 h-4" />
                            <span className="font-medium text-xs">{username}</span>
                        </div>
                        <div className="flex items-center gap-3">
                            <button
                                className="text-emerald-600 hover:text-emerald-700 font-medium text-xs flex items-center gap-1 transition-colors"
                                onClick={() => {
                                    navigator.clipboard.writeText(shareLink).then(() => {
                                        if (serverIP && isLocalhost) {
                                            setError(`LAN link copied: ${shareLink}`)
                                        } else {
                                            setError('Link copied!')
                                        }
                                        setTimeout(() => setError(''), 5000)
                                    }).catch(() => {
                                        setError(`Copy manually: ${shareLink}`)
                                        setTimeout(() => setError(''), 10000)
                                    })
                                }}
                            >
                                <Copy className="w-3.5 h-3.5" />
                                Copy Link
                            </button>
                            <button
                                onClick={() => { navigate('/'); setScreen('home'); }}
                                className="text-slate-600 hover:text-slate-900 font-semibold text-xs"
                            >
                                Home
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {error && (
                <div className="bg-red-50 border-b border-red-200 text-red-600 text-center py-2 text-sm font-medium">
                    {error}
                </div>
            )}

            {/* Screen Router */}
            <div className="flex-1 min-h-0 overflow-y-auto">
                {screen === 'lobby' && lobby && (
                    <Lobby
                        lobby={lobby}
                        username={username}
                        sendMsg={sendMsg}
                    />
                )}

                {(screen === 'toss' || screen === 'toss_result' || screen === 'toss_choose' || screen === 'toss_decision') && (
                    <TossScreen
                        screen={screen}
                        tossData={tossData}
                        username={username}
                        sendMsg={sendMsg}
                        isHost={lobby?.host === username}
                    />
                )}

                {screen === 'game' && matchState && (
                    <GameBoard
                        state={matchState}
                        ballFlash={ballFlash}
                        sendMsg={sendMsg}
                        isHost={lobby?.host === username}
                        countdown={countdown}
                    />
                )}

                {screen === 'scorecard' && (
                    <Scorecard
                        data={scorecardData}
                        onBack={backToLobby}
                    />
                )}

                {(screen === 'standings' || screen === 'tournament_over') && (
                    <StandingsView
                        data={standingsData}
                        isOver={screen === 'tournament_over'}
                        onBack={backToLobby}
                    />
                )}
            </div>

            {/* Editorial Footer (desktop lobby only) */}
            {screen === 'lobby' && (
                <footer className="hidden lg:flex mt-auto border-t border-slate-200 py-8 bg-white">
                    <div className="w-full px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-4">
                        <span className="text-lg uppercase tracking-wider text-slate-300" style={{ fontFamily: "'Anton', sans-serif" }}>E Cricket Hub</span>
                        <p className="text-slate-400 text-xs">© 2026 Tournament Edition. Game responsibly.</p>
                    </div>
                </footer>
            )}
        </div>
    )
}
