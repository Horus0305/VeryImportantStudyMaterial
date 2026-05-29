import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogOut, User, Trophy } from 'lucide-react'

const DISPLAY_FONT = { fontFamily: "'Anton', 'Bebas Neue', sans-serif" }

interface HomeScreenProps {
    username: string
    token: string
    onCreateRoom: () => void
    onJoinRoom: (code: string) => void
    onLogout: () => void
    error: string
}

export default function HomeScreen({ username, onCreateRoom, onJoinRoom, onLogout, error }: HomeScreenProps) {
    const navigate = useNavigate()
    const [joinCode, setJoinCode] = useState('')

    return (
        <div className="min-h-dvh bg-slate-50 flex flex-col">

            {/* ── NAVBAR ──────────────────────────────────────────── */}
            <nav className="sticky top-0 z-40 bg-white border-b border-slate-200 shadow-sm">
                <div className="max-w-2xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 flex-shrink-0">
                        <div className="w-8 h-8 bg-linear-to-br from-emerald-500 to-emerald-600 rounded-xl -rotate-6 flex items-center justify-center shadow-sm shadow-emerald-500/20">
                            <span className="text-base -rotate-6">🏏</span>
                        </div>
                        <span className="text-xl uppercase tracking-tight text-slate-900 hidden sm:block" style={DISPLAY_FONT}>
                            E <span className="text-emerald-600">Cricket</span>
                        </span>
                    </div>

                    <div className="flex items-center gap-2">
                        <div className="hidden sm:flex items-center gap-1.5 bg-slate-100 rounded-lg px-2.5 py-1.5">
                            <div className="w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
                                <span className="text-[10px] text-white font-bold uppercase">{username[0]}</span>
                            </div>
                            <span className="text-xs font-bold text-slate-700">{username}</span>
                        </div>
                        <button
                            onClick={() => navigate('/leaderboard')}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100 transition-all text-xs font-bold uppercase tracking-wide"
                        >
                            <Trophy size={13} />
                            <span className="hidden sm:block">Leaderboard</span>
                        </button>
                        <button
                            onClick={() => navigate('/profile')}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-all text-xs font-bold uppercase tracking-wide"
                        >
                            <User size={13} />
                            <span className="hidden sm:block">Profile</span>
                        </button>
                        <button
                            onClick={onLogout}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-50 border border-red-200 text-red-600 hover:bg-red-100 transition-all text-xs font-bold uppercase tracking-wide"
                        >
                            <LogOut size={13} />
                            <span className="hidden sm:block">Logout</span>
                        </button>
                    </div>
                </div>
            </nav>

            {/* ── MAIN ────────────────────────────────────────────── */}
            <div className="flex-1 flex items-center justify-center px-4 py-10">
                <div className="w-full max-w-lg space-y-5">

                    {/* Welcome */}
                    <div className="text-center">
                        <div className="inline-flex items-center justify-center w-14 h-14 bg-linear-to-br from-emerald-500 to-emerald-600 rounded-2xl shadow-lg shadow-emerald-500/20 mb-4 -rotate-6 hover:rotate-0 transition-transform duration-500 cursor-default">
                            <span className="text-2xl -rotate-6">🏏</span>
                        </div>
                        <h1 className="text-4xl sm:text-5xl text-slate-900 uppercase leading-none" style={DISPLAY_FONT}>
                            E <span className="text-emerald-600">Cricket</span>
                        </h1>
                        <p className="text-sm text-slate-500 mt-2">
                            Welcome back, <span className="font-bold text-emerald-700">{username}</span>!
                        </p>
                    </div>

                    {/* Create Room */}
                    <div className="group bg-white rounded-2xl border border-slate-200 p-5 sm:p-7 shadow-sm hover:shadow-md hover:border-emerald-300 transition-all duration-300">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-10 h-10 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-center text-xl group-hover:bg-emerald-100 transition-colors">
                                ⚡
                            </div>
                            <div>
                                <h3 className="text-lg sm:text-xl text-slate-900 uppercase" style={DISPLAY_FONT}>Create a Room</h3>
                                <p className="text-xs text-slate-400">Host a new match. Share the code with friends.</p>
                            </div>
                        </div>
                        <button
                            onClick={onCreateRoom}
                            className="w-full py-3.5 sm:py-4 bg-linear-to-r from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 text-white font-bold uppercase tracking-widest text-xs sm:text-sm rounded-xl shadow-md shadow-emerald-600/15 hover:shadow-emerald-500/25 transition-all duration-300 active:scale-[0.98]"
                        >
                            🏏 Create New Room
                        </button>
                    </div>

                    {/* Join Room */}
                    <div className="group bg-white rounded-2xl border border-slate-200 p-5 sm:p-7 shadow-sm hover:shadow-md hover:border-blue-300 transition-all duration-300">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-10 h-10 bg-blue-50 border border-blue-200 rounded-xl flex items-center justify-center text-xl group-hover:bg-blue-100 transition-colors">
                                🎯
                            </div>
                            <div>
                                <h3 className="text-lg sm:text-xl text-slate-900 uppercase" style={DISPLAY_FONT}>Join a Room</h3>
                                <p className="text-xs text-slate-400">Enter the room code to join an existing match.</p>
                            </div>
                        </div>
                        <div className="space-y-3">
                            <input
                                placeholder="Enter room code (e.g. ABC123)"
                                value={joinCode}
                                onChange={e => setJoinCode(e.target.value.toUpperCase())}
                                onKeyDown={e => e.key === 'Enter' && joinCode.trim() && onJoinRoom(joinCode.trim())}
                                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 sm:py-3.5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10 transition-all text-sm font-mono tracking-widest text-center uppercase"
                                maxLength={8}
                            />
                            <button
                                onClick={() => joinCode.trim() && onJoinRoom(joinCode.trim())}
                                className="w-full py-3.5 sm:py-4 bg-linear-to-r from-slate-800 to-slate-900 hover:from-slate-700 hover:to-slate-800 text-white font-bold uppercase tracking-widest text-xs sm:text-sm rounded-xl shadow-md shadow-slate-900/10 hover:shadow-slate-800/20 transition-all duration-300 active:scale-[0.98]"
                            >
                                🎯 Join Room
                            </button>
                        </div>
                    </div>

                    {/* Leaderboard CTA */}
                    <button
                        onClick={() => navigate('/leaderboard')}
                        className="w-full flex items-center justify-center gap-2.5 py-3.5 bg-white border border-amber-200 hover:border-amber-300 hover:bg-amber-50 rounded-2xl text-amber-700 font-bold uppercase tracking-widest text-xs transition-all duration-300 shadow-sm group"
                    >
                        <Trophy size={15} className="group-hover:scale-110 transition-transform" />
                        Leaderboard & Hall of Fame
                    </button>

                    {error && (
                        <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-center justify-center gap-2">
                            <span className="text-red-500">⚠</span>
                            <p className="text-xs text-red-600 font-medium">{error}</p>
                        </div>
                    )}

                    <p className="text-center text-[10px] text-slate-400 uppercase tracking-widest font-bold pt-1">
                        © 2026 Sports Interactive
                    </p>
                </div>
            </div>
        </div>
    )
}
