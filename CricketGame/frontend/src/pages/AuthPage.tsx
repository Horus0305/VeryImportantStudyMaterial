import { useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'

const DISPLAY_FONT = { fontFamily: "'Anton', 'Bebas Neue', sans-serif" }
const API = (import.meta.env.VITE_API_BASE_URL ?? window.location.origin).replace(/\/$/, '')

interface AuthPageProps {
    onAuth: (token: string, username: string) => void
}

export default function AuthPage({ onAuth }: AuthPageProps) {
    const [searchParams] = useSearchParams()
    const navigate = useNavigate()

    const [isRegister, setIsRegister] = useState(searchParams.get('tab') === 'register')
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [showPassword, setShowPassword] = useState(false)
    const [error, setError] = useState('')
    const [isLoading, setIsLoading] = useState(false)

    const switchTab = (register: boolean) => {
        setIsRegister(register)
        setError('')
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!username.trim() || !password.trim()) {
            setError('Username and password required.')
            return
        }
        setIsLoading(true)
        setError('')

        const endpoint = isRegister ? '/auth/register' : '/auth/login'
        try {
            const res = await fetch(`${API}${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: username.trim(), password }),
            })
            const data = await res.json()
            if (!res.ok) {
                setError(data.detail || 'Something went wrong.')
                setIsLoading(false)
                return
            }
            if (isRegister) {
                const loginRes = await fetch(`${API}/auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: username.trim(), password }),
                })
                const loginData = await loginRes.json()
                if (loginRes.ok) {
                    onAuth(loginData.token, loginData.username)
                } else {
                    setError(loginData.detail || 'Login failed after registration.')
                }
            } else {
                onAuth(data.token, data.username)
            }
        } catch {
            setError('Cannot connect to server. Is the backend running?')
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="min-h-dvh bg-slate-950 text-white flex flex-col">
            {/* Nav */}
            <nav className="bg-slate-950/90 backdrop-blur-md border-b border-white/5 px-4 sm:px-8">
                <div className="max-w-6xl mx-auto h-14 sm:h-16 flex items-center justify-between">
                    <Link to="/" className="flex items-center gap-2.5 group">
                        <div className="w-8 h-8 bg-linear-to-br from-emerald-500 to-emerald-600 rounded-xl -rotate-6 flex items-center justify-center shadow-lg shadow-emerald-500/20 group-hover:rotate-0 transition-transform duration-300">
                            <span className="text-base -rotate-6 group-hover:rotate-6 transition-transform duration-300">🏏</span>
                        </div>
                        <span className="text-xl uppercase tracking-tight text-white" style={DISPLAY_FONT}>
                            E <span className="text-emerald-400">Cricket</span>
                        </span>
                    </Link>
                    <button
                        onClick={() => navigate('/')}
                        className="text-xs font-bold uppercase tracking-widest text-slate-400 hover:text-white transition-colors flex items-center gap-1.5"
                    >
                        ← Back
                    </button>
                </div>
            </nav>

            {/* Auth card — vertically centered in remaining space */}
            <div className="flex-1 flex items-center justify-center px-4 py-12">
                <div className="w-full max-w-sm">
                    {/* Logo mark */}
                    <div className="text-center mb-8">
                        <div className="inline-flex items-center justify-center w-16 h-16 bg-linear-to-br from-emerald-500 to-emerald-600 rounded-2xl shadow-2xl shadow-emerald-500/25 -rotate-6 hover:rotate-0 transition-transform duration-500 cursor-default mb-5">
                            <span className="text-3xl -rotate-6">🏏</span>
                        </div>
                        <h1 className="text-4xl sm:text-5xl text-white uppercase leading-none mb-1" style={DISPLAY_FONT}>
                            {isRegister ? 'Join the Game' : 'Welcome Back'}
                        </h1>
                        <p className="text-slate-400 text-sm">
                            {isRegister ? 'Create an account to start playing' : 'Login to continue your streak'}
                        </p>
                    </div>

                    {/* Card */}
                    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-2xl">
                        {/* Tab toggle */}
                        <div className="flex mb-6 bg-slate-800 rounded-xl p-1">
                            <button
                                onClick={() => switchTab(false)}
                                className={`flex-1 py-2.5 rounded-lg text-xs font-bold uppercase tracking-widest transition-all duration-300 ${!isRegister
                                    ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30'
                                    : 'text-slate-400 hover:text-slate-300'
                                    }`}
                            >
                                Login
                            </button>
                            <button
                                onClick={() => switchTab(true)}
                                className={`flex-1 py-2.5 rounded-lg text-xs font-bold uppercase tracking-widest transition-all duration-300 ${isRegister
                                    ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/30'
                                    : 'text-slate-400 hover:text-slate-300'
                                    }`}
                            >
                                Register
                            </button>
                        </div>

                        <form onSubmit={handleSubmit}>
                            <div className="space-y-4">
                                <div>
                                    <label htmlFor="username" className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1.5">
                                        Username
                                    </label>
                                    <input
                                        id="username"
                                        placeholder="Enter your username"
                                        value={username}
                                        onChange={e => setUsername(e.target.value)}
                                        autoFocus
                                        className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/10 transition-all text-sm"
                                    />
                                </div>
                                <div>
                                    <label htmlFor="password" className="block text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1.5">
                                        Password
                                    </label>
                                    <div className="relative">
                                        <input
                                            id="password"
                                            type={showPassword ? 'text' : 'password'}
                                            placeholder="Enter your password"
                                            value={password}
                                            onChange={e => setPassword(e.target.value)}
                                            className="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 pr-11 text-white placeholder:text-slate-500 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/10 transition-all text-sm"
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setShowPassword(v => !v)}
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 transition-colors p-0.5"
                                            tabIndex={-1}
                                            aria-label={showPassword ? 'Hide password' : 'Show password'}
                                        >
                                            {showPassword ? (
                                                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
                                                    <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
                                                    <line x1="1" y1="1" x2="23" y2="23" />
                                                </svg>
                                            ) : (
                                                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                                                    <circle cx="12" cy="12" r="3" />
                                                </svg>
                                            )}
                                        </button>
                                    </div>
                                </div>

                                {error && (
                                    <div className="bg-red-950/50 border border-red-800/40 rounded-xl p-3 flex items-center gap-2">
                                        <span className="text-red-400 text-sm">⚠</span>
                                        <p className="text-xs text-red-400 font-medium">{error}</p>
                                    </div>
                                )}
                            </div>

                            <button
                                type="submit"
                                disabled={isLoading}
                                className="w-full mt-6 py-4 bg-linear-to-r from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 text-white font-bold uppercase tracking-widest text-sm rounded-xl shadow-lg shadow-emerald-600/20 hover:shadow-emerald-500/30 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
                            >
                                {isLoading ? (
                                    <span className="flex items-center justify-center gap-2">
                                        <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                                        Please wait...
                                    </span>
                                ) : (
                                    isRegister ? '🏏 Create Account' : '⚡ Login'
                                )}
                            </button>
                        </form>
                    </div>

                    <p className="text-center text-[10px] text-slate-600 uppercase tracking-widest font-bold mt-8">
                        © 2026 Sports Interactive
                    </p>
                </div>
            </div>
        </div>
    )
}
