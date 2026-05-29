import { useNavigate } from 'react-router-dom'

const DISPLAY_FONT = { fontFamily: "'Anton', 'Bebas Neue', sans-serif" }

const FEATURES = [
    {
        icon: '⚡',
        title: 'Real-Time Multiplayer',
        desc: 'Challenge friends or anyone on your network. Zero lag, instant score updates via WebSocket.',
    },
    {
        icon: '🏆',
        title: 'Tournaments',
        desc: 'Run round-robin or knockout tournaments for up to 8 players. Live standings update after every match.',
    },
    {
        icon: '📊',
        title: 'Full Scorecards',
        desc: 'Detailed innings scorecards, economy rates, strike rates, Player of the Match. Cricket stats done right.',
    },
    {
        icon: '🤖',
        title: 'Bot Players',
        desc: 'No friends online? Play against CPU bots with adaptive strategy. Solo or mixed human-bot lobbies.',
    },
]

const MODES = [
    { label: 'Head to Head', icon: '⚔️' },
    { label: 'Team Match', icon: '👥' },
    { label: 'Tournament', icon: '🏆' },
    { label: 'Super Over', icon: '⚡' },
]

export default function LoginPage() {
    const navigate = useNavigate()

    return (
        <div className="bg-slate-950 text-white overflow-x-hidden">

            {/* ── NAV ─────────────────────────────────────────────── */}
            <nav className="sticky top-0 z-50 bg-slate-950/90 backdrop-blur-md border-b border-white/5">
                <div className="max-w-6xl mx-auto px-4 sm:px-8 h-14 sm:h-16 flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 sm:w-9 sm:h-9 bg-linear-to-br from-emerald-500 to-emerald-600 rounded-xl -rotate-6 flex items-center justify-center shadow-lg shadow-emerald-500/20">
                            <span className="text-base sm:text-lg -rotate-6">🏏</span>
                        </div>
                        <span className="text-xl sm:text-2xl uppercase tracking-tight text-white" style={DISPLAY_FONT}>
                            E <span className="text-emerald-400">Cricket</span>
                        </span>
                    </div>
                    <div className="flex items-center gap-2 sm:gap-3">
                        <button
                            onClick={() => navigate('/login')}
                            className="px-3 sm:px-4 py-1.5 sm:py-2 text-slate-300 hover:text-white text-xs sm:text-sm font-bold uppercase tracking-widest transition-colors"
                        >
                            Login
                        </button>
                        <button
                            onClick={() => navigate('/login?tab=register')}
                            className="px-4 sm:px-5 py-1.5 sm:py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs sm:text-sm font-bold uppercase tracking-widest rounded-lg transition-colors shadow-md shadow-emerald-600/20"
                        >
                            Play Free
                        </button>
                    </div>
                </div>
            </nav>

            {/* ── HERO ────────────────────────────────────────────── */}
            <section className="relative min-h-[92vh] flex items-center justify-center overflow-hidden px-4 py-16">
                {/* Background decorative rings */}
                <div className="absolute inset-0 pointer-events-none select-none overflow-hidden">
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[900px] rounded-full border border-emerald-500/5" />
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[650px] h-[650px] rounded-full border border-emerald-500/8" />
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] rounded-full border border-emerald-500/10" />
                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[180px] h-[500px] bg-emerald-900/20 rounded-[40%] blur-sm" />
                    <div className="absolute top-[-15%] right-[-5%] w-[600px] h-[600px] bg-emerald-500/4 rounded-full blur-3xl" />
                    <div className="absolute bottom-[-20%] left-[-10%] w-[500px] h-[500px] bg-blue-500/4 rounded-full blur-3xl" />
                    <div className="absolute top-[10%] left-[5%] w-[300px] h-[300px] bg-amber-500/3 rounded-full blur-3xl" />
                </div>

                <div className="relative z-10 text-center max-w-5xl mx-auto">
                    {/* Live badge */}
                    <div className="inline-flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-4 py-1.5 mb-8 text-xs font-bold uppercase tracking-[0.2em] text-emerald-400">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        Live Multiplayer Cricket
                    </div>

                    {/* Headline */}
                    <h1 className="text-6xl sm:text-8xl lg:text-9xl text-white uppercase leading-[0.88] tracking-tight mb-6" style={DISPLAY_FONT}>
                        The Ultimate<br />
                        <span className="text-emerald-400">Cricket</span><br />
                        Experience
                    </h1>

                    {/* Tagline */}
                    <p className="text-slate-400 text-base sm:text-lg lg:text-xl max-w-2xl mx-auto mb-10 leading-relaxed">
                        Create rooms, challenge friends, compete in tournaments.
                        Real-time multiplayer cricket — in your browser.
                    </p>

                    {/* CTAs */}
                    <div className="flex flex-col sm:flex-row items-center justify-center gap-3 sm:gap-4">
                        <button
                            onClick={() => navigate('/login?tab=register')}
                            className="w-full sm:w-auto px-8 py-4 bg-linear-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white font-bold uppercase tracking-widest text-sm rounded-xl shadow-xl shadow-emerald-500/25 hover:shadow-emerald-400/35 transition-all duration-300 hover:-translate-y-0.5 active:scale-[0.98]"
                        >
                            🏏 Start Playing — It's Free
                        </button>
                        <button
                            onClick={() => navigate('/login')}
                            className="w-full sm:w-auto px-8 py-4 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 text-slate-300 hover:text-white font-bold uppercase tracking-widest text-sm rounded-xl transition-all duration-300"
                        >
                            ⚡ Sign In
                        </button>
                    </div>

                    {/* Game mode pills */}
                    <div className="flex flex-wrap items-center justify-center gap-2 mt-10">
                        {MODES.map(m => (
                            <span key={m.label} className="inline-flex items-center gap-1.5 bg-slate-800/60 border border-slate-700/50 rounded-full px-3 py-1.5 text-xs text-slate-400 font-medium">
                                <span>{m.icon}</span> {m.label}
                            </span>
                        ))}
                    </div>
                </div>

                {/* Scroll hint */}
                <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1 opacity-40">
                    <span className="text-[10px] uppercase tracking-widest text-slate-500">Scroll</span>
                    <div className="w-px h-8 bg-linear-to-b from-slate-500 to-transparent" />
                </div>
            </section>

            {/* ── FEATURES ────────────────────────────────────────── */}
            <section className="bg-slate-900 py-20 sm:py-28 px-4 border-t border-slate-800">
                <div className="max-w-5xl mx-auto">
                    <div className="text-center mb-14">
                        <h2 className="text-4xl sm:text-5xl text-white uppercase leading-none mb-3" style={DISPLAY_FONT}>
                            Why <span className="text-emerald-400">E Cricket</span>?
                        </h2>
                        <p className="text-slate-400 text-sm sm:text-base">Everything you need for the perfect cricket match</p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
                        {FEATURES.map(f => (
                            <div
                                key={f.title}
                                className="group bg-slate-800/40 hover:bg-slate-800/80 border border-slate-700/40 hover:border-emerald-500/30 rounded-2xl p-6 transition-all duration-300 cursor-default"
                            >
                                <div className="w-12 h-12 bg-emerald-500/10 group-hover:bg-emerald-500/20 rounded-xl flex items-center justify-center text-2xl mb-4 transition-colors">
                                    {f.icon}
                                </div>
                                <h3 className="text-base text-white uppercase mb-2 leading-tight" style={DISPLAY_FONT}>{f.title}</h3>
                                <p className="text-slate-400 text-xs sm:text-sm leading-relaxed">{f.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── STATS STRIP ─────────────────────────────────────── */}
            <section className="py-16 sm:py-20 px-4 border-t border-slate-800 bg-slate-950">
                <div className="max-w-4xl mx-auto">
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 text-center">
                        {[
                            { num: '4', label: 'Game Modes', suffix: '' },
                            { num: '8', label: 'Players per Room', suffix: '+' },
                            { num: '20', label: 'Overs Formats', suffix: '' },
                            { num: '₹0', label: 'Cost to Play', suffix: '' },
                        ].map(s => (
                            <div key={s.label} className="space-y-1">
                                <p className="text-4xl sm:text-5xl text-emerald-400 leading-none" style={DISPLAY_FONT}>
                                    {s.num}{s.suffix}
                                </p>
                                <p className="text-slate-500 text-xs sm:text-sm uppercase tracking-widest font-medium">{s.label}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── HOW IT WORKS ────────────────────────────────────── */}
            <section className="bg-slate-900 py-20 sm:py-28 px-4 border-t border-slate-800">
                <div className="max-w-4xl mx-auto">
                    <div className="text-center mb-14">
                        <h2 className="text-4xl sm:text-5xl text-white uppercase leading-none mb-3" style={DISPLAY_FONT}>
                            How It <span className="text-emerald-400">Works</span>
                        </h2>
                        <p className="text-slate-400 text-sm sm:text-base">Up and playing in under 60 seconds</p>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 sm:gap-8 relative">
                        <div className="hidden sm:block absolute top-8 left-[calc(16.7%+16px)] right-[calc(16.7%+16px)] h-px bg-linear-to-r from-emerald-500/30 via-emerald-500/60 to-emerald-500/30" />

                        {[
                            { step: '1', icon: '👤', title: 'Create Account', desc: 'Register in seconds — just a username and password. No email, no verification.' },
                            { step: '2', icon: '🏠', title: 'Create or Join Room', desc: 'Host a new room and share the 6-letter code, or enter someone\'s code to join.' },
                            { step: '3', icon: '🏏', title: 'Play Cricket', desc: 'Toss, pick teams, and start the match. Real-time scoring for every ball.' },
                        ].map(s => (
                            <div key={s.step} className="relative flex flex-col items-center text-center">
                                <div className="w-16 h-16 bg-slate-800 border border-slate-700 rounded-2xl flex items-center justify-center text-3xl mb-4 relative z-10">
                                    {s.icon}
                                    <span className="absolute -top-2 -right-2 w-5 h-5 bg-emerald-500 rounded-full text-[10px] font-bold text-white flex items-center justify-center" style={DISPLAY_FONT}>
                                        {s.step}
                                    </span>
                                </div>
                                <h3 className="text-lg text-white uppercase mb-2" style={DISPLAY_FONT}>{s.title}</h3>
                                <p className="text-slate-400 text-xs sm:text-sm leading-relaxed max-w-[220px]">{s.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ── FINAL CTA ───────────────────────────────────────── */}
            <section className="bg-slate-950 py-20 sm:py-28 px-4 border-t border-slate-800 text-center">
                <div className="max-w-2xl mx-auto">
                    <h2 className="text-5xl sm:text-6xl text-white uppercase leading-none mb-4" style={DISPLAY_FONT}>
                        Ready to <span className="text-emerald-400">Play</span>?
                    </h2>
                    <p className="text-slate-400 text-sm sm:text-base mb-8">
                        Free to play. No downloads. Works on any device.
                    </p>
                    <button
                        onClick={() => navigate('/login?tab=register')}
                        className="px-10 py-4 bg-linear-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white font-bold uppercase tracking-widest text-sm rounded-xl shadow-xl shadow-emerald-500/25 hover:shadow-emerald-400/35 transition-all duration-300 hover:-translate-y-0.5 active:scale-[0.98]"
                    >
                        🏏 Create Free Account
                    </button>
                </div>
            </section>

            {/* ── FOOTER ──────────────────────────────────────────── */}
            <footer className="bg-slate-900 border-t border-slate-800 py-10 px-4">
                <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 bg-emerald-600 rounded-lg flex items-center justify-center text-sm -rotate-6 shadow-lg shadow-emerald-600/20">🏏</div>
                        <span className="text-lg uppercase tracking-tight text-slate-300" style={DISPLAY_FONT}>
                            E <span className="text-emerald-400">Cricket</span>
                        </span>
                    </div>
                    <div className="flex items-center gap-6 text-[10px] text-slate-500 uppercase tracking-widest font-bold">
                        <span>Real-Time Cricket</span>
                        <span className="w-1 h-1 rounded-full bg-slate-700" />
                        <span>© 2026 Sports Interactive</span>
                    </div>
                </div>
            </footer>
        </div>
    )
}
