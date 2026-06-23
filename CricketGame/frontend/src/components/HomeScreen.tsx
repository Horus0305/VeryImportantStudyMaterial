import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogOut, User, BarChart3, ChevronRight } from 'lucide-react'

const DF = { fontFamily: "'Anton', 'Bebas Neue', sans-serif" }

interface HomeScreenProps {
    username: string
    token: string
    onCreateRoom: (password: string) => Promise<boolean>
    onJoinRoom: (code: string) => void
    onLogout: () => void
    error: string
}

export default function HomeScreen({ username, onCreateRoom, onJoinRoom, onLogout, error }: HomeScreenProps) {
    const navigate = useNavigate()
    const [joinCode, setJoinCode] = useState('')
    const [showPasscodeModal, setShowPasscodeModal] = useState(false)
    const [passcode, setPasscode] = useState('')
    const [passcodeError, setPasscodeError] = useState('')
    const [isCreating, setIsCreating] = useState(false)

    const handleConfirmCreate = async (e?: React.FormEvent) => {
        if (e) e.preventDefault()
        if (!passcode.trim()) {
            setPasscodeError('Passcode is required')
            return
        }
        setIsCreating(true)
        setPasscodeError('')
        const success = await onCreateRoom(passcode)
        setIsCreating(false)
        if (success) {
            setShowPasscodeModal(false)
            setPasscode('')
        }
    }

    return (
        <div className="min-h-dvh bg-slate-50 flex flex-col">

            {/* ── NAVBAR ──────────────────────────────────────────── */}
            <nav className="sticky top-0 z-40 bg-white border-b border-slate-200 shadow-sm">
                <div className="max-w-2xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 bg-linear-to-br from-emerald-500 to-emerald-600 rounded-xl -rotate-6 flex items-center justify-center shadow-sm shadow-emerald-500/20">
                            <span className="text-base -rotate-6">🏏</span>
                        </div>
                        <span className="text-xl uppercase tracking-tight text-slate-900 hidden sm:block" style={DF}>
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
                            <BarChart3 size={13} />
                            <span className="hidden sm:block">Stats</span>
                        </button>
                        <button
                            onClick={() => navigate('/profile')}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 transition-all text-xs font-bold uppercase tracking-wide"
                        >
                            <User size={13} />
                            <span className="hidden sm:block">Profile</span>
                        </button>
                        <button
                            onClick={onLogout}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-50 border border-red-200 text-red-600 hover:bg-red-100 transition-all text-xs font-bold uppercase tracking-wide"
                        >
                            <LogOut size={13} />
                        </button>
                    </div>
                </div>
            </nav>

            {/* ── MAIN ────────────────────────────────────────────── */}
            <div className="flex-1 flex items-center justify-center px-4 py-10">
                <div className="w-full max-w-lg space-y-4">

                    {/* Welcome */}
                    <div className="text-center mb-8">
                        <div className="inline-flex items-center justify-center w-14 h-14 bg-linear-to-br from-emerald-500 to-emerald-600 rounded-2xl shadow-lg shadow-emerald-500/20 mb-4 -rotate-6 hover:rotate-0 transition-transform duration-500 cursor-default">
                            <span className="text-2xl -rotate-6">🏏</span>
                        </div>
                        <h1 className="text-4xl sm:text-5xl text-slate-900 uppercase leading-none" style={DF}>
                            E <span className="text-emerald-600">Cricket</span>
                        </h1>
                        <p className="text-sm text-slate-500 mt-2">
                            Welcome back, <span className="font-bold text-emerald-700">{username}</span>
                        </p>
                    </div>

                    {/* Create Room */}
                    <div className="group bg-white rounded-2xl border border-slate-200 p-5 sm:p-7 shadow-sm hover:shadow-md hover:border-emerald-300 transition-all duration-300">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-10 h-10 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-center text-xl group-hover:bg-emerald-100 transition-colors">
                                ⚡
                            </div>
                            <div>
                                <h3 className="text-lg sm:text-xl text-slate-900 uppercase" style={DF}>Create a Room</h3>
                                <p className="text-xs text-slate-400">Host a new match. Share the code with friends.</p>
                            </div>
                        </div>
                        <button
                            onClick={() => setShowPasscodeModal(true)}
                            className="w-full py-3.5 sm:py-4 bg-linear-to-r from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 text-white font-bold uppercase tracking-widest text-xs sm:text-sm rounded-xl shadow-md shadow-emerald-600/15 transition-all duration-300 active:scale-[0.98]"
                        >
                            Create New Room
                        </button>
                    </div>

                    {/* Join Room */}
                    <div className="group bg-white rounded-2xl border border-slate-200 p-5 sm:p-7 shadow-sm hover:shadow-md hover:border-blue-300 transition-all duration-300">
                        <div className="flex items-center gap-3 mb-4">
                            <div className="w-10 h-10 bg-blue-50 border border-blue-200 rounded-xl flex items-center justify-center text-xl group-hover:bg-blue-100 transition-colors">
                                🎯
                            </div>
                            <div>
                                <h3 className="text-lg sm:text-xl text-slate-900 uppercase" style={DF}>Join a Room</h3>
                                <p className="text-xs text-slate-400">Enter the room code to join an existing match.</p>
                            </div>
                        </div>
                        <div className="space-y-3">
                            <input
                                placeholder="Enter room code (e.g. ABC123)"
                                value={joinCode}
                                onChange={e => setJoinCode(e.target.value.toUpperCase())}
                                onKeyDown={e => e.key === 'Enter' && joinCode.trim() && onJoinRoom(joinCode.trim())}
                                maxLength={8}
                                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 sm:py-3.5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/10 transition-all text-sm font-mono tracking-widest text-center uppercase"
                            />
                            <button
                                onClick={() => joinCode.trim() && onJoinRoom(joinCode.trim())}
                                className="w-full py-3.5 sm:py-4 bg-linear-to-r from-slate-800 to-slate-900 hover:from-slate-700 hover:to-slate-800 text-white font-bold uppercase tracking-widest text-xs sm:text-sm rounded-xl shadow-md shadow-slate-900/10 transition-all duration-300 active:scale-[0.98]"
                            >
                                Join Room
                            </button>
                        </div>
                    </div>

                    {/* Stats CTA */}
                    <button
                        onClick={() => navigate('/leaderboard')}
                        className="w-full flex items-center justify-between bg-white border border-slate-200 hover:border-amber-300 hover:bg-amber-50/50 rounded-2xl px-5 py-4 transition-all duration-300 shadow-sm group"
                    >
                        <div className="flex items-center gap-3">
                            <BarChart3 size={18} className="text-amber-600" />
                            <div className="text-left">
                                <p className="text-sm font-bold text-slate-800 uppercase tracking-wide" style={DF}>Stats & Leaderboards</p>
                                <p className="text-xs text-slate-400 mt-0.5">Rankings · Hall of Fame · Hall of Shame</p>
                            </div>
                        </div>
                        <ChevronRight size={16} className="text-slate-400 group-hover:text-amber-600 group-hover:translate-x-0.5 transition-all" />
                    </button>

                    {error && !showPasscodeModal && (
                        <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-center justify-center gap-2">
                            <span className="text-red-500 text-sm">⚠</span>
                            <p className="text-xs text-red-600 font-medium">{error}</p>
                        </div>
                    )}

                    <p className="text-center text-[10px] text-slate-400 uppercase tracking-widest font-bold pt-1">
                        © 2026 Sports Interactive
                    </p>
                </div>
            </div>

            {/* Passcode Modal */}
            {showPasscodeModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-md">
                    <div className="w-full max-w-sm bg-white rounded-2xl border border-slate-200 shadow-2xl p-6 sm:p-8 transform transition-all scale-100">
                        {/* Modal Header */}
                        <div className="text-center mb-6">
                            <div className="inline-flex items-center justify-center w-12 h-12 bg-emerald-50 border border-emerald-100 text-emerald-600 rounded-xl mb-3 text-2xl">
                                🔐
                            </div>
                            <h3 className="text-xl font-black text-slate-900 uppercase tracking-wide" style={DF}>
                                Host Passcode Required
                            </h3>
                            <p className="text-xs text-slate-400 mt-1.5">
                                Enter the master host passcode to create a game room.
                            </p>
                        </div>

                        {/* Modal Body / Form */}
                        <form onSubmit={handleConfirmCreate} className="space-y-4">
                            <div>
                                <label htmlFor="modal-passcode" className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1.5">
                                    Passcode
                                </label>
                                <input
                                    id="modal-passcode"
                                    type="password"
                                    placeholder="Enter passcode"
                                    value={passcode}
                                    onChange={e => {
                                        setPasscode(e.target.value)
                                        setPasscodeError('')
                                    }}
                                    autoFocus
                                    disabled={isCreating}
                                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/10 transition-all text-sm font-mono text-center tracking-widest"
                                />
                            </div>

                            {/* Show passcode error or the global room creation error */}
                            {(passcodeError || error) && (
                                <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-center gap-2">
                                    <span className="text-red-500 text-xs">⚠</span>
                                    <p className="text-xs text-red-600 font-medium">{passcodeError || error}</p>
                                </div>
                            )}

                            {/* Actions */}
                            <div className="flex gap-3 pt-2">
                                <button
                                    type="button"
                                    onClick={() => {
                                        setShowPasscodeModal(false)
                                        setPasscode('')
                                        setPasscodeError('')
                                    }}
                                    disabled={isCreating}
                                    className="flex-1 py-3 border border-slate-200 hover:bg-slate-50 text-slate-500 hover:text-slate-800 font-bold uppercase tracking-widest text-xs rounded-xl transition-all"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={isCreating}
                                    className="flex-1 py-3 bg-linear-to-r from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 text-white font-bold uppercase tracking-widest text-xs rounded-xl shadow-md shadow-emerald-600/15 transition-all disabled:opacity-50 flex items-center justify-center gap-1.5"
                                >
                                    {isCreating ? (
                                        <>
                                            <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                            Verifying...
                                        </>
                                    ) : (
                                        'Confirm Host'
                                    )}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    )
}
