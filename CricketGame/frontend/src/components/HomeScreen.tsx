import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogOut, User, Trophy, ChevronRight } from 'lucide-react'

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
        <div className="min-h-dvh bg-slate-950 text-white flex flex-col overflow-x-hidden">

            {/* ── Decorative background ───────────────────────── */}
            <div className="fixed inset-0 pointer-events-none select-none overflow-hidden">
                <div className="absolute top-[-20%] right-[-10%] w-150 h-150 rounded-full bg-emerald-500/5 blur-3xl" />
                <div className="absolute bottom-[-20%] left-[-10%] w-125 h-125 rounded-full bg-blue-500/5 blur-3xl" />
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-200 h-200 rounded-full border border-white/2" />
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-125 h-125 rounded-full border border-white/3" />
            </div>

            {/* ── NAVBAR ──────────────────────────────────────── */}
            <nav className="sticky top-0 z-40 bg-slate-950/80 backdrop-blur-md border-b border-white/5">
                <div className="max-w-2xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 bg-linear-to-br from-emerald-500 to-emerald-600 rounded-xl -rotate-6 flex items-center justify-center shadow-lg shadow-emerald-500/20">
                            <span className="text-base -rotate-6">🏏</span>
                        </div>
                        <span className="text-xl uppercase tracking-tight" style={DISPLAY_FONT}>
                            E <span className="text-emerald-400">Cricket</span>
                        </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                        <button
                            onClick={() => navigate('/leaderboard')}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 hover:bg-amber-500/20 transition-all text-xs font-bold uppercase tracking-wide"
                        >
                            <Trophy size={12} />
                            <span className="hidden sm:block">Stats</span>
                        </button>
                        <button
                            onClick={() => navigate('/profile')}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-slate-300 hover:bg-white/10 transition-all text-xs font-bold uppercase tracking-wide"
                        >
                            <User size={12} />
                            <span className="hidden sm:block">Profile</span>
                        </button>
                        <button
                            onClick={onLogout}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20 transition-all text-xs font-bold uppercase tracking-wide"
                        >
                            <LogOut size={12} />
                        </button>
                    </div>
                </div>
            </nav>

            {/* ── MAIN ────────────────────────────────────────── */}
            <div className="relative flex-1 flex items-center justify-center px-4 py-10">
                <div className="w-full max-w-lg space-y-4">

                    {/* Welcome */}
                    <div className="mb-8">
                        <p className="text-xs font-bold uppercase tracking-[0.25em] text-slate-500 mb-1">Welcome back</p>
                        <h1 className="text-6xl sm:text-7xl text-white uppercase leading-none" style={DISPLAY_FONT}>
                            {username}
                        </h1>
                        <div className="mt-3 flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                            <span className="text-xs text-slate-400 font-medium uppercase tracking-widest">Ready to play</span>
                        </div>
                    </div>

                    {/* Create Room */}
                    <button
                        onClick={onCreateRoom}
                        className="group w-full relative bg-emerald-600/10 hover:bg-emerald-600/20 border border-emerald-500/20 hover:border-emerald-500/50 rounded-2xl p-5 sm:p-6 text-left transition-all duration-300 hover:shadow-lg hover:shadow-emerald-500/10"
                    >
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 bg-emerald-500/15 group-hover:bg-emerald-500/25 border border-emerald-500/20 rounded-xl flex items-center justify-center text-2xl transition-colors">
                                    ⚡
                                </div>
                                <div>
                                    <h3 className="text-2xl text-white uppercase leading-none mb-1" style={DISPLAY_FONT}>
                                        Create Room
                                    </h3>
                                    <p className="text-xs text-slate-400">Host a match · Share the code with friends</p>
                                </div>
                            </div>
                            <ChevronRight size={20} className="text-emerald-500 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
                        </div>
                        {/* Glow line */}
                        <div className="absolute bottom-0 left-6 right-6 h-px bg-linear-to-r from-transparent via-emerald-500/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    </button>

                    {/* Join Room */}
                    <div className="bg-slate-900/60 border border-white/8 hover:border-white/15 rounded-2xl p-5 sm:p-6 transition-all duration-300">
                        <div className="flex items-center gap-4 mb-4">
                            <div className="w-12 h-12 bg-white/5 border border-white/10 rounded-xl flex items-center justify-center text-2xl">
                                🎯
                            </div>
                            <div>
                                <h3 className="text-2xl text-white uppercase leading-none mb-1" style={DISPLAY_FONT}>
                                    Join Room
                                </h3>
                                <p className="text-xs text-slate-400">Enter the 6-letter room code</p>
                            </div>
                        </div>
                        <div className="flex gap-2">
                            <input
                                placeholder="ROOM CODE"
                                value={joinCode}
                                onChange={e => setJoinCode(e.target.value.toUpperCase())}
                                onKeyDown={e => e.key === 'Enter' && joinCode.trim() && onJoinRoom(joinCode.trim())}
                                maxLength={8}
                                className="flex-1 bg-slate-800/80 border border-white/10 focus:border-emerald-500/60 focus:ring-2 focus:ring-emerald-500/10 rounded-xl px-4 py-3 text-white placeholder:text-slate-600 font-mono tracking-[0.3em] text-center uppercase text-sm focus:outline-none transition-all"
                            />
                            <button
                                onClick={() => joinCode.trim() && onJoinRoom(joinCode.trim())}
                                className="px-5 py-3 bg-white/8 hover:bg-white/15 border border-white/10 hover:border-white/20 rounded-xl text-white font-bold uppercase tracking-widest text-xs transition-all active:scale-[0.97]"
                            >
                                Join
                            </button>
                        </div>
                    </div>

                    {/* Stats / Leaderboard CTA */}
                    <button
                        onClick={() => navigate('/leaderboard')}
                        className="group w-full flex items-center justify-between bg-amber-500/5 hover:bg-amber-500/10 border border-amber-500/15 hover:border-amber-500/30 rounded-2xl px-5 py-4 transition-all duration-300"
                    >
                        <div className="flex items-center gap-3">
                            <Trophy size={18} className="text-amber-400" />
                            <div className="text-left">
                                <p className="text-sm font-bold text-amber-300 uppercase tracking-widest" style={DISPLAY_FONT}>
                                    Stats & Leaderboards
                                </p>
                                <p className="text-xs text-slate-500 mt-0.5">Rankings · Hall of Fame · Hall of Shame</p>
                            </div>
                        </div>
                        <ChevronRight size={16} className="text-amber-500/50 group-hover:text-amber-400 group-hover:translate-x-1 transition-all" />
                    </button>

                    {error && (
                        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 flex items-center gap-2">
                            <span className="text-red-400 text-sm">⚠</span>
                            <p className="text-xs text-red-400 font-medium">{error}</p>
                        </div>
                    )}

                    <p className="text-center text-[10px] text-slate-700 uppercase tracking-widest font-bold pt-2">
                        © 2026 Sports Interactive
                    </p>
                </div>
            </div>
        </div>
    )
}
