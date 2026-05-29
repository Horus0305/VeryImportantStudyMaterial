/**
 * RoomPage — The main game hub.
 * Handles: Room creation/joining, lobby, toss, game, scorecard, and tournament.
 * Uses a WebSocket for real-time communication with the backend.
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { LogOut, Copy, User } from 'lucide-react'
import Lobby from '@/components/Lobby'
import TossScreen from '@/components/TossScreen'
import GameBoard from '@/components/GameBoard'
import Scorecard from '@/components/Scorecard'
import StandingsView from '@/components/StandingsView'
import EmojiOverlay, { type EmojiOverlayHandle } from '@/components/EmojiOverlay'
import HomeScreen from '@/components/HomeScreen'

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

    const emojiOverlayRef = useRef<EmojiOverlayHandle>(null)
    const myRoleRef = useRef<string>('')
    const [emojiPickerOpen, setEmojiPickerOpen] = useState(false)

    const wsRef = useRef<WebSocket | null>(null)
    const [isReconnecting, setIsReconnecting] = useState(false)
    const reconnectAttemptsRef = useRef(0)
    const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    // Whether this connect() call is a reconnect (don't reset screen to lobby)
    const reconnectingRef = useRef(false)

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
                break

            case 'INNINGS_BREAK':
                // Brief pause handled by server, next MATCH_STATE comes automatically
                break

            case 'MATCH_OVER':
                // Delay transition to scorecard so the last ball celebration finishes
                setScorecardData(msg)
                setTimeout(() => {
                    setScreen('scorecard')
                    setMatchState(null)
                }, 2500)
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
                // Allow transition from scorecard to standings so the user
                // doesn't stay stuck on the scorecard when next match starts.
                // Block only during active game / toss (those transitions are
                // driven by TOSS_CALLER / MATCH_STATE events).
                if (screen !== 'game' && screen !== 'toss' && screen !== 'toss_result'
                    && screen !== 'toss_choose' && screen !== 'toss_decision') setScreen('standings')
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

            case 'EMOJI_REACTION': {
                const activeRoles = new Set(['BATTING', 'BOWLING'])
                if (!activeRoles.has(myRoleRef.current)) {
                    emojiOverlayRef.current?.addReaction(msg.player as string, msg.emoji as string)
                }
                break
            }

            case 'PLAYER_DISCONNECTED': {
                const who = msg.username as string
                setError(`${who} disconnected — waiting for them to reconnect...`)
                setTimeout(() => setError(''), 10000)
                break
            }

            case 'PLAYER_RECONNECTED': {
                const who = msg.username as string
                setError(`${who} reconnected!`)
                setTimeout(() => setError(''), 3000)
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

    // Keep role ref in sync so the WS handler can check it without a stale closure
    useEffect(() => { myRoleRef.current = matchState?.my_role ?? '' }, [matchState?.my_role])

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

    // Connect WebSocket (isReconnect=true skips the lobby screen reset)
    const connectWs = useCallback((code: string, isReconnect = false) => {
        if (wsRef.current) {
            wsRef.current.close()
            wsRef.current = null
        }

        reconnectingRef.current = isReconnect
        const wsUrl = `${WS_BASE}/ws/${code}?token=${token}`
        const ws = new WebSocket(wsUrl)

        ws.onopen = () => {
            console.log(isReconnect ? '[WS] Reconnected to room' : '[WS] Connected to room', code)
            reconnectAttemptsRef.current = 0
            setIsReconnecting(false)
            setRoomCode(code)
            // On a fresh connect go to lobby; on reconnect the server will push
            // the right screen (MATCH_STATE / TOURNAMENT_STANDINGS / TOSS_*)
            if (!reconnectingRef.current) {
                setScreen('lobby')
            }
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
            console.log('[WS] Disconnected from room', evt.code, evt.reason)
            if (evt.code === 4001) {
                // Token expired or invalid — force re-login
                onLogout()
                return
            }
            if (evt.code === 4000) {
                // Replaced by a newer session from the same user — no action needed
                return
            }
            if (evt.code === 4004) {
                setIsReconnecting(false)
                setError(evt.reason || 'Room not found.')
                return
            }
            // Unexpected disconnect — try to reconnect if we have a room code
            const currentCode = code
            if (currentCode) {
                setIsReconnecting(true)
                const attempt = reconnectAttemptsRef.current
                if (attempt >= 10) {
                    setIsReconnecting(false)
                    setError('Connection lost. Please refresh the page.')
                    return
                }
                // Exponential backoff: 1s, 1.5s, 2.25s … capped at 15s
                const delay = Math.min(1000 * Math.pow(1.5, attempt), 15000)
                reconnectAttemptsRef.current = attempt + 1
                reconnectTimerRef.current = setTimeout(() => {
                    connectWs(currentCode, true)
                }, delay)
            }
        }

        ws.onerror = () => {
            // onerror is always followed by onclose, so let onclose handle reconnect
        }

        wsRef.current = ws
    }, [token, onLogout])

    // Auto-connect if URL has room code
    useEffect(() => {
        if (urlRoomCode && !wsRef.current) {
            connectWs(urlRoomCode)
        }
        return () => {
            if (reconnectTimerRef.current) {
                clearTimeout(reconnectTimerRef.current)
                reconnectTimerRef.current = null
            }
            wsRef.current?.close()
            wsRef.current = null
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
        setMatchState(null)
        // If a tournament is active, go to standings instead of the lobby
        // so the user doesn't get stuck on a blank lobby mid-tournament.
        if (standingsData && (standingsData as Record<string, unknown>).standings) {
            setScreen('standings')
        } else {
            setScreen('lobby')
        }
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
            <HomeScreen
                username={username}
                token={token}
                onCreateRoom={createRoom}
                onJoinRoom={(code) => { setJoinCode(code); navigate(`/room/${code}`) }}
                onLogout={onLogout}
                error={error}
            />
        )
    }

    const EMOJIS = ['🔥', '😱', '👏', '💀', '🎉', '😤']
    // Emoji picker: only spectators during a live match, or anyone on the standings screen
    const showEmojiBar = (screen === 'game' && matchState?.my_role === 'SPECTATING')
        || screen === 'standings'

    return (
        <div className="min-h-dvh flex flex-col bg-slate-950 text-white overflow-y-auto sm:overflow-hidden">
            {/* Floating emoji reactions — imperative overlay, zero React re-renders */}
            <EmojiOverlay ref={emojiOverlayRef} />

            {/* Emoji picker — single trigger button, expands on tap */}
            {showEmojiBar && (
                <>
                    {emojiPickerOpen && (
                        <div
                            className="fixed inset-0 z-[165]"
                            onClick={() => setEmojiPickerOpen(false)}
                        />
                    )}
                    <div className="fixed bottom-6 left-3 z-[170] flex flex-col items-center gap-1.5">
                        {emojiPickerOpen && (
                            <div className="flex flex-col items-center gap-1.5 mb-1">
                                {EMOJIS.map(emoji => (
                                    <button
                                        key={emoji}
                                        onClick={() => {
                                            sendMsg({ action: 'EMOJI_REACTION', emoji })
                                            setEmojiPickerOpen(false)
                                        }}
                                        className="w-9 h-9 rounded-full bg-white/95 backdrop-blur-sm border border-slate-200 shadow-md hover:scale-125 active:scale-95 transition-transform text-lg flex items-center justify-center"
                                    >
                                        {emoji}
                                    </button>
                                ))}
                            </div>
                        )}
                        <button
                            onClick={() => setEmojiPickerOpen(o => !o)}
                            className="w-10 h-10 rounded-full bg-white/95 backdrop-blur-sm border border-slate-200 shadow-lg hover:scale-110 active:scale-95 transition-transform text-xl flex items-center justify-center"
                        >
                            {emojiPickerOpen ? '✕' : '😊'}
                        </button>
                    </div>
                </>
            )}

            {/* Reconnecting overlay — shown whenever the WS dropped mid-game */}
            {isReconnecting && (
                <div className="fixed inset-0 z-[200] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
                    <div className="bg-slate-900 border border-white/10 rounded-2xl p-8 shadow-2xl flex flex-col items-center gap-5 max-w-xs w-full">
                        <div className="w-14 h-14 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin" />
                        <div className="text-center">
                            <h2 className="text-xl font-black text-white uppercase tracking-wide">Reconnecting</h2>
                            <p className="text-sm text-slate-400 mt-1">
                                Connection lost. Trying to get you back in…
                            </p>
                            <p className="text-xs text-slate-500 mt-2 font-mono">
                                Attempt {reconnectAttemptsRef.current} of 10
                            </p>
                        </div>
                    </div>
                </div>
            )}
            {/* Header Area */}
            <div className="flex-shrink-0 z-20 relative">
                {/* ─── Top Nav: Editorial Style ─── */}
                <nav className="sticky top-0 z-50 bg-slate-950/90 backdrop-blur-md border-b border-white/5">
                    <div className="w-full px-4 sm:px-6 lg:px-8">
                        <div className="flex items-center justify-between h-14 lg:h-16">
                            {/* Left: Brand + Room Code */}
                            <div className="flex items-center gap-3 lg:gap-5">
                                <div className="flex items-center gap-2">
                                    <div className="w-8 h-8 bg-linear-to-br from-emerald-500 to-emerald-600 rounded-xl -rotate-6 flex items-center justify-center shadow-lg shadow-emerald-500/20">
                                        <span className="text-base -rotate-6">🏏</span>
                                    </div>
                                    <span className="text-xl uppercase tracking-tight text-white hidden sm:block" style={{ fontFamily: "'Anton', 'Bebas Neue', sans-serif" }}>E <span className="text-emerald-400">Cricket</span></span>
                                </div>
                                {roomCode && (
                                    <div className="flex items-center gap-1.5 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5">
                                        <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">Room</span>
                                        <span className="font-mono font-bold text-white text-sm tracking-widest">{roomCode}</span>
                                    </div>
                                )}
                            </div>

                            {/* Right: User + Actions */}
                            <div className="flex items-center gap-2">
                                <div className="hidden sm:flex items-center gap-1.5 bg-white/5 rounded-lg px-2.5 py-1.5">
                                    <div className="w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                                        <span className="text-[10px] text-white font-bold uppercase">{username[0]}</span>
                                    </div>
                                    <span className="text-xs font-bold text-slate-300">{username}</span>
                                </div>
                                <button
                                    onClick={() => { navigate('/'); setScreen('home'); }}
                                    className="text-xs font-bold text-slate-400 hover:text-white uppercase tracking-wide transition-colors px-2 py-1.5"
                                >
                                    Home
                                </button>
                                {serverIP && isLocalhost && (
                                    <button
                                        className="text-xs font-bold uppercase tracking-wider bg-white/5 border border-white/10 hover:border-emerald-500/50 hover:text-emerald-400 text-slate-400 px-3 py-1.5 rounded-lg transition-all"
                                        onClick={() => {
                                            navigator.clipboard.writeText(shareLink).then(() => {
                                                setError('Link copied!')
                                                setTimeout(() => setError(''), 5000)
                                            }).catch(() => {
                                                setError(`Copy manually: ${shareLink}`)
                                                setTimeout(() => setError(''), 10000)
                                            })
                                        }}
                                    >
                                        Copy Link
                                    </button>
                                )}
                                <button
                                    onClick={onLogout}
                                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20 transition-all text-xs font-bold uppercase tracking-wide"
                                >
                                    <LogOut className="w-3.5 h-3.5" />
                                    <span className="hidden sm:block">Out</span>
                                </button>
                            </div>
                        </div>
                    </div>
                </nav>

                {/* Sub-Header for lobby (mobile copy link + home) */}
                {screen === 'lobby' && (
                    <div className="bg-slate-900/60 border-b border-white/5 px-4 sm:px-6 py-2 flex items-center justify-between text-sm lg:hidden">
                        <div className="flex items-center gap-2 text-slate-400">
                            <User className="w-4 h-4" />
                            <span className="font-medium text-xs">{username}</span>
                        </div>
                        <div className="flex items-center gap-3">
                            <button
                                className="text-emerald-400 hover:text-emerald-300 font-medium text-xs flex items-center gap-1 transition-colors"
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
                                className="text-slate-400 hover:text-white font-semibold text-xs"
                            >
                                Home
                            </button>
                        </div>
                    </div>
                )}
            </div>

            {error && (
                <div className="bg-red-500/10 border-b border-red-500/20 text-red-400 text-center py-2 text-sm font-medium">
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
                        lobbyPlayers={lobby?.players?.map(p => p.username)}
                    />
                )}

                {screen === 'game' && matchState && (
                    <GameBoard
                        state={matchState}
                        ballFlash={ballFlash}
                        sendMsg={sendMsg}
                        isHost={lobby?.host === username}
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
