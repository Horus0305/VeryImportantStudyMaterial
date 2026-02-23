/**
 * LoginPage — Premium light-mode sports editorial login.
 *
 * Design: Light bg-slate-50, white glassmorphism cards, emerald accents,
 * Bebas Neue / Anton display font, fully mobile-responsive.
 */
import { useState } from 'react'

const DISPLAY_FONT = { fontFamily: "'Anton', 'Bebas Neue', sans-serif" }

interface LoginPageProps {
    onAuth: (token: string, username: string) => void
}

const API = (import.meta.env.VITE_API_BASE_URL ?? window.location.origin).replace(/\/$/, '')

export default function LoginPage({ onAuth }: LoginPageProps) {
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [isRegister, setIsRegister] = useState(false)

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
        <div className="min-h-[100dvh] sm:min-h-screen bg-slate-50 flex items-center justify-center relative overflow-hidden px-4 py-8">
            {/* Subtle decorative gradients */}
            <div className="absolute top-[-30%] right-[-20%] w-[500px] h-[500px] bg-emerald-200/30 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute bottom-[-20%] left-[-15%] w-[400px] h-[400px] bg-blue-200/20 rounded-full blur-3xl pointer-events-none" />

            <div className="relative z-10 w-full max-w-md">
                {/* Logo & Branding */}
                <div className="text-center mb-6 sm:mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 sm:w-20 sm:h-20 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-2xl shadow-lg shadow-emerald-500/20 mb-4 sm:mb-5 rotate-[-6deg] hover:rotate-0 transition-transform duration-500">
                        <span className="text-3xl sm:text-4xl -rotate-12">🏏</span>
                    </div>

                    <h1 className="text-4xl sm:text-5xl text-slate-900 uppercase tracking-tight leading-none" style={DISPLAY_FONT}>
                        E <span className="text-emerald-600">Cricket</span>
                    </h1>
                    <p className="text-[10px] sm:text-xs font-bold uppercase tracking-[0.25em] text-slate-400 mt-2 sm:mt-3">

                    </p>
                </div>

                {/* Login Card */}
                <div className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-8 shadow-lg">
                    {/* Tab Header */}
                    <div className="flex mb-5 sm:mb-6 bg-slate-100 rounded-xl p-1">
                        <button
                            onClick={() => { setIsRegister(false); setError('') }}
                            className={`flex-1 py-2 sm:py-2.5 rounded-lg text-xs sm:text-sm font-bold uppercase tracking-widest transition-all duration-300 ${!isRegister
                                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/20'
                                : 'text-slate-400 hover:text-slate-600'
                                }`}
                        >
                            Login
                        </button>
                        <button
                            onClick={() => { setIsRegister(true); setError('') }}
                            className={`flex-1 py-2 sm:py-2.5 rounded-lg text-xs sm:text-sm font-bold uppercase tracking-widest transition-all duration-300 ${isRegister
                                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/20'
                                : 'text-slate-400 hover:text-slate-600'
                                }`}
                        >
                            Register
                        </button>
                    </div>

                    <div className="mb-4 sm:mb-5">
                        <h2 className="text-2xl sm:text-3xl text-slate-900 uppercase tracking-wide" style={DISPLAY_FONT}>
                            {isRegister ? 'Create Account' : 'Welcome Back'}
                        </h2>
                        <p className="text-xs sm:text-sm text-slate-500 mt-1">
                            {isRegister ? 'Register to start playing' : 'Login to join a match'}
                        </p>
                    </div>

                    <form onSubmit={handleSubmit}>
                        <div className="space-y-3 sm:space-y-4">
                            <div>
                                <label htmlFor="username" className="block text-[10px] sm:text-xs font-bold uppercase tracking-widest text-slate-400 mb-1.5 sm:mb-2">
                                    Username
                                </label>
                                <input
                                    id="username"
                                    placeholder="Enter your username"
                                    value={username}
                                    onChange={e => setUsername(e.target.value)}
                                    autoFocus
                                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 sm:py-3.5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/10 transition-all text-sm"
                                />
                            </div>
                            <div>
                                <label htmlFor="password" className="block text-[10px] sm:text-xs font-bold uppercase tracking-widest text-slate-400 mb-1.5 sm:mb-2">
                                    Password
                                </label>
                                <input
                                    id="password"
                                    type="password"
                                    placeholder="Enter your password"
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 sm:py-3.5 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/10 transition-all text-sm"
                                />
                            </div>

                            {error && (
                                <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-center gap-2">
                                    <span className="text-red-500 text-base">⚠</span>
                                    <p className="text-xs sm:text-sm text-red-600 font-medium">{error}</p>
                                </div>
                            )}
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="w-full mt-5 sm:mt-6 py-3.5 sm:py-4 bg-gradient-to-r from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 text-white font-bold uppercase tracking-widest text-xs sm:text-sm rounded-xl shadow-md shadow-emerald-600/15 hover:shadow-emerald-500/25 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
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

                {/* Footer */}
                <div className="text-center mt-6 sm:mt-8">
                    <p className="text-[10px] text-slate-400 uppercase tracking-widest font-bold">
                        © 2026 Sports Interactive
                    </p>
                </div>
            </div>
        </div>
    )
}
