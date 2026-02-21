import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'

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
                // After register, auto-login
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
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-white to-slate-100 p-4">
            <div className="w-full max-w-md">
                {/* Header */}
                <div className="text-center mb-8 sm:mb-12">
                    <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900 mb-3 flex items-center justify-center gap-3">
                        <span className="text-emerald-600">🏏</span> E Cricket
                    </h1>
                    <p className="text-slate-500 text-base sm:text-lg font-medium">
                        Professional Edition
                    </p>
                </div>

                <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-xl">
                    <div className="mb-6">
                        <h2 className="text-2xl font-bold text-slate-900 mb-2">
                            {isRegister ? 'Create Account' : 'Welcome Back'}
                        </h2>
                        <p className="text-slate-500">
                            {isRegister
                                ? 'Register to start playing'
                                : 'Login to join a match'}
                        </p>
                    </div>

                    <form onSubmit={handleSubmit}>
                        <div className="space-y-5">
                            <div className="space-y-2">
                                <Label htmlFor="username" className="text-slate-700 font-medium">Username</Label>
                                <Input
                                    id="username"
                                    placeholder="Enter your username"
                                    value={username}
                                    onChange={e => setUsername(e.target.value)}
                                    autoFocus
                                    className="bg-white border-slate-200 text-slate-900 placeholder:text-slate-400 focus:border-emerald-500 focus:ring-emerald-500/20 transition-all"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="password" className="text-slate-700 font-medium">Password</Label>
                                <Input
                                    id="password"
                                    type="password"
                                    placeholder="Enter your password"
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    className="bg-white border-slate-200 text-slate-900 placeholder:text-slate-400 focus:border-emerald-500 focus:ring-emerald-500/20 transition-all"
                                />
                            </div>

                            {error && (
                                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                                    <p className="text-sm text-red-600 font-medium">{error}</p>
                                </div>
                            )}
                        </div>

                        <div className="flex flex-col gap-3 mt-6">
                            <Button
                                type="submit"
                                className="w-full py-6 text-base sm:text-lg bg-emerald-600 hover:bg-emerald-700 text-white shadow-md transition-all font-semibold rounded-xl"
                                disabled={isLoading}
                            >
                                {isLoading ? 'Please wait...' : (isRegister ? ' Register' : ' Login')}
                            </Button>
                            <Button
                                type="button"
                                variant="ghost"
                                className="w-full text-slate-500 hover:text-slate-900 hover:bg-slate-100/50"
                                onClick={() => { setIsRegister(!isRegister); setError('') }}
                            >
                                {isRegister
                                    ? 'Already have an account? Login'
                                    : "Don't have an account? Register"}
                            </Button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    )
}
