/**
 * HeadToHead — Collapsible card showing H2H stats between two players.
 * Fetched from /api/head-to-head/{player1}/{player2}.
 * Shows: Wins, Losses, Batting Best, Bowling Best, Average, Avg Strike Rate.
 */
import { useEffect, useRef, useState } from 'react'

interface H2HPlayerStats {
    wins: number
    losses: number
    ties: number
    batting_best: number
    batting_avg: number
    avg_strike_rate: number
    bowling_best: string
}

interface H2HData {
    has_history: boolean
    total_matches?: number
    [key: string]: H2HPlayerStats | boolean | number | undefined
}

interface Props {
    player1: string
    player2: string
    /** Start expanded (pre-match) or collapsed (during match) */
    defaultOpen?: boolean
}

const API = (import.meta.env.VITE_API_BASE_URL ?? window.location.origin).replace(/\/$/, '')

export default function HeadToHead({ player1, player2, defaultOpen = false }: Props) {
    const [data, setData] = useState<H2HData | null>(null)
    const [open, setOpen] = useState(defaultOpen)
    const [loading, setLoading] = useState(true)
    const cacheRef = useRef<Record<string, H2HData>>({})

    useEffect(() => {
        if (!player1 || !player2 || player1 === player2) {
            // eslint-disable-next-line react-hooks/set-state-in-effect
            setLoading(false)
            return
        }

        const key = `${player1}::${player2}`
        const cached = cacheRef.current[key]
        if (cached) {
            setData(cached)
            setLoading(false)
            return
        }

        const controller = new AbortController()
        setLoading(true)
        fetch(`${API}/api/head-to-head/${encodeURIComponent(player1)}/${encodeURIComponent(player2)}`, {
            signal: controller.signal,
        })
            .then(r => {
                if (!r.ok) {
                    throw new Error('Failed to fetch head-to-head')
                }
                return r.json()
            })
            .then(d => {
                cacheRef.current[key] = d
                setData(d)
            })
            .catch((err: unknown) => {
                if (!(err instanceof DOMException) || err.name !== 'AbortError') {
                    setData(null)
                }
            })
            .finally(() => setLoading(false))
        return () => controller.abort()
    }, [player1, player2])

    // Don't render anything if no history
    if (loading) return null
    if (!data || !data.has_history) return null

    const s1 = data[player1] as H2HPlayerStats
    const s2 = data[player2] as H2HPlayerStats
    if (!s1 || !s2) return null

    const totalMatches = (data.total_matches as number) || 0

    return (
        <div className="w-full bg-white/80 backdrop-blur-sm rounded-xl border border-slate-200 shadow-xl overflow-hidden">
            {/* Toggle Header */}
            <button
                onClick={() => setOpen(prev => !prev)}
                className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-slate-50 transition-colors"
            >
                <div className="flex items-center gap-2">
                    <span className="text-base">️</span>
                    <span className="text-sm font-bold text-slate-900">Head to Head</span>
                    <span className="text-xs text-slate-500 font-medium">({totalMatches} match{totalMatches !== 1 ? 'es' : ''})</span>
                </div>
                <span className={`text-slate-500 text-xs transition-transform duration-200 ${open ? 'rotate-180' : ''}`}>
                    ▼
                </span>
            </button>

            {/* Collapsible Content */}
            <div className={`transition-all duration-300 ease-in-out ${open ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'} overflow-hidden`}>
                <div className="px-4 pb-3 pt-1">
                    {/* Player Names Header */}
                    <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 mb-3">
                        <span className="text-sm font-bold text-orange-600 truncate text-left">{player1}</span>
                        <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-widest">vs</span>
                        <span className="text-sm font-bold text-cyan-600 truncate text-right">{player2}</span>
                    </div>

                    {/* Stats Rows */}
                    <div className="space-y-1.5">
                        <StatRow label="Wins" v1={s1.wins} v2={s2.wins} highlight="higher" />
                        <StatRow label="Losses" v1={s1.losses} v2={s2.losses} highlight="lower" />
                        <StatRow label="Bat Best" v1={s1.batting_best} v2={s2.batting_best} highlight="higher" />
                        <StatRow label="Bat Avg" v1={s1.batting_avg} v2={s2.batting_avg} highlight="higher" />
                        <StatRow label="Avg SR" v1={s1.avg_strike_rate} v2={s2.avg_strike_rate} highlight="higher" />
                        <StatRow label="Bowl Best" v1={s1.bowling_best} v2={s2.bowling_best} isBowling />
                    </div>
                </div>
            </div>
        </div>
    )
}

/** A single stat comparison row */
function StatRow({
    label, v1, v2, highlight, isBowling
}: {
    label: string
    v1: number | string
    v2: number | string
    highlight?: 'higher' | 'lower'
    isBowling?: boolean
}) {
    let p1Better = false
    let p2Better = false

    if (isBowling) {
        // Compare bowling figures: more wickets = better, or same wickets + fewer runs
        const [w1, r1] = String(v1).split('/').map(Number)
        const [w2, r2] = String(v2).split('/').map(Number)
        if (w1 > w2 || (w1 === w2 && r1 < r2)) p1Better = true
        else if (w2 > w1 || (w2 === w1 && r2 < r1)) p2Better = true
    } else if (highlight === 'higher') {
        if (Number(v1) > Number(v2)) p1Better = true
        else if (Number(v2) > Number(v1)) p2Better = true
    } else if (highlight === 'lower') {
        if (Number(v1) < Number(v2)) p1Better = true
        else if (Number(v2) < Number(v1)) p2Better = true
    }

    return (
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 text-xs">
            <span className={`text-left font-mono tabular-nums ${p1Better ? 'text-green-600 font-bold' : 'text-slate-600'}`}>
                {v1}
            </span>
            <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider min-w-[70px] text-center">
                {label}
            </span>
            <span className={`text-right font-mono tabular-nums ${p2Better ? 'text-green-600 font-bold' : 'text-slate-600'}`}>
                {v2}
            </span>
        </div>
    )
}
