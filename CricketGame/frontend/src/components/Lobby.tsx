import { useEffect, useState } from 'react'
import { DndContext, closestCenter, PointerSensor, useSensor, useSensors, useDroppable } from '@dnd-kit/core'
import type { DragEndEvent } from '@dnd-kit/core'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

interface LobbyData {
    players: Array<{ username: string; team: string | null; is_captain: boolean; in_match: boolean; is_disconnected?: boolean }>
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

interface Props {
    lobby: LobbyData
    username: string
    sendMsg: (msg: Record<string, unknown>) => void
}

const MODE_LABELS: Record<string, string> = {
    '1v1': '1v1 Quick',
    'tournament': 'Tournament',
    'team': 'Team Mode',
}

const DF = { fontFamily: "'Anton', 'Bebas Neue', sans-serif" }

export default function Lobby({ lobby, username, sendMsg }: Props) {
    const isHost = username === lobby.host
    const normalizedMode = lobby.mode === '2v2' ? 'team' : lobby.mode
    const [mode, setMode] = useState(normalizedMode)
    const [overs, setOvers] = useState(lobby.overs)
    const [wickets, setWickets] = useState(lobby.wickets)
    const [hostWantsToPlay, setHostWantsToPlay] = useState(lobby.host_plays ?? true)

    useEffect(() => {
        setMode(normalizedMode)
        setOvers(lobby.overs)
        setWickets(lobby.wickets)
        setHostWantsToPlay(lobby.host_plays ?? true)
    }, [normalizedMode, lobby.overs, lobby.wickets, lobby.host_plays])

    const displayMode    = isHost ? mode : normalizedMode
    const displayOvers   = isHost ? overs : lobby.overs
    const displayWickets = isHost ? wickets : lobby.wickets

    const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }))

    const overOptions  = displayMode === 'team' ? [5, 10] : [2, 5]
    const wicketRange  = displayMode === 'team' ? [2, 3, 4, 5] : [1, 2, 3]

    const applySettings = () => sendMsg({ action: 'CONFIGURE', mode, overs, wickets, host_plays: hostWantsToPlay })

    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event
        if (!over) return
        const target = over.id as string
        if (target === 'A' || target === 'B') {
            sendMsg({ action: 'ASSIGN_TEAM', player: active.id as string, team: target })
        }
    }

    const assignedSet      = new Set([...(lobby.teams.A || []), ...(lobby.teams.B || [])])
    const unassignedPlayers = lobby.players.filter(p => !assignedSet.has(p.username))
    const isTeamMode       = displayMode === 'team'
    const totalPlayers     = lobby.players.length
    const assignedCount    = (lobby.teams.A?.length || 0) + (lobby.teams.B?.length || 0)
    const cpuCount         = lobby.cpu_count ?? (lobby.cpu_enabled ? 1 : 0)
    const hasBothCaptains  = !!lobby.captains.A && !!lobby.captains.B
    const hasFullTeams     = assignedCount === totalPlayers
        && (lobby.teams.A?.length || 0) >= 2
        && (lobby.teams.A?.length || 0) === (lobby.teams.B?.length || 0)
    const settingsChanged  = isHost && (
        mode !== normalizedMode || overs !== lobby.overs ||
        wickets !== lobby.wickets || hostWantsToPlay !== (lobby.host_plays ?? true)
    )

    // ── Shared button helpers ─────────────────────────────────────
    const activeBtn  = 'bg-emerald-600/20 border-2 border-emerald-500 text-white'
    const inactiveBtn = 'bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:border-white/20 disabled:opacity-50 disabled:cursor-not-allowed'

    return (
        <div className="w-full px-4 sm:px-6 lg:px-8 py-4 lg:py-8 pb-28 lg:pb-8 flex flex-col">

            {/* ── Page header ─── */}
            <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-6 gap-2">
                <div>
                    <div className="inline-flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-3 py-1 mb-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        Lobby
                    </div>
                    <h1 className="text-4xl lg:text-5xl text-white uppercase leading-none" style={DF}>Match Setup</h1>
                </div>
                <p className="text-xs text-slate-500 font-mono">Room · {lobby.room_code}</p>
            </div>

            {/* ── Main grid ─── */}
            <div className={`grid gap-5 items-start flex-grow ${isTeamMode ? 'grid-cols-1 lg:grid-cols-12' : 'grid-cols-1 lg:grid-cols-12'}`}>

                {/* ═══ SQUAD LIST ═══ */}
                <div className={`${isTeamMode ? 'lg:col-span-4' : 'lg:col-span-5'} flex flex-col`}>
                    <div className="bg-slate-900 border border-white/8 rounded-2xl overflow-hidden flex flex-col lg:min-h-[500px]">
                        <div className="px-5 py-4 border-b border-white/8 flex justify-between items-center">
                            <h2 className="text-2xl text-white uppercase" style={DF}>Squad</h2>
                            <span className="bg-emerald-500/10 text-emerald-400 text-xs font-bold px-2.5 py-1 rounded-full border border-emerald-500/20">
                                {totalPlayers} Players
                            </span>
                        </div>

                        <div className="p-4 lg:p-5 flex-grow flex flex-col gap-3 overflow-y-auto">
                            <div className="flex lg:flex-col gap-3 overflow-x-auto lg:overflow-x-visible pb-2 lg:pb-0 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                                {lobby.players.map(p => {
                                    const disc = p.is_disconnected === true
                                    return (
                                        <div
                                            key={p.username}
                                            className={`shrink-0 w-60 lg:w-auto flex items-center justify-between px-3 py-3 rounded-xl border-l-4 transition-all hover:translate-x-0.5 ${disc
                                                ? 'bg-slate-800/40 border-red-500 opacity-60'
                                                : 'bg-slate-800 border-emerald-500'
                                            }`}
                                        >
                                            <div className="flex items-center gap-3">
                                                <div className={`w-9 h-9 rounded-lg flex items-center justify-center text-sm text-white font-bold relative ${disc ? 'bg-slate-600' : 'bg-emerald-600'}`} style={DF}>
                                                    {p.username[0].toUpperCase()}
                                                    {disc && <span className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-red-500 border-2 border-slate-900" />}
                                                </div>
                                                <div>
                                                    <div className={`font-bold text-sm leading-none ${disc ? 'text-slate-400' : 'text-white'}`}>{p.username}</div>
                                                    {disc
                                                        ? <div className="text-[10px] text-red-400 mt-0.5 uppercase tracking-widest">Disconnected</div>
                                                        : p.username === lobby.host && <div className="text-[10px] text-slate-500 mt-0.5 uppercase tracking-widest">Host</div>
                                                    }
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-1.5">
                                                {!disc && p.username === lobby.host && (
                                                    <span className="bg-white/10 text-white text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider">Host</span>
                                                )}
                                                {p.is_captain && (
                                                    <span className="bg-amber-500/20 text-amber-300 text-[9px] font-bold px-2 py-0.5 rounded-full uppercase">Capt</span>
                                                )}
                                                {p.team && (
                                                    <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase ${p.team === 'A' ? 'bg-blue-500/20 text-blue-300' : 'bg-violet-500/20 text-violet-300'}`}>
                                                        {p.team}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    )
                                })}
                            </div>

                            {!isTeamMode && (
                                <div className="flex items-center justify-center p-6 border-2 border-dashed border-white/8 rounded-xl text-slate-600 flex-col gap-2">
                                    <span className="text-2xl opacity-40">🏏</span>
                                    <span className="text-xs font-medium uppercase tracking-wide">Waiting for players…</span>
                                </div>
                            )}
                        </div>

                        {isHost && !lobby.cpu_only && (
                            <div className="p-4 border-t border-white/8">
                                <button
                                    onClick={() => sendMsg({ action: 'ADD_CPU' })}
                                    disabled={displayMode === '1v1' && cpuCount >= 1}
                                    className={`w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-xs font-bold uppercase tracking-widest transition-all ${inactiveBtn}`}
                                >
                                    + Add CPU Player
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                {/* ═══ CONFIGURATION ═══ */}
                <div className={`${isTeamMode ? 'lg:col-span-4' : 'lg:col-span-7'} flex flex-col`}>
                    <div className="bg-slate-900 border border-white/8 rounded-2xl overflow-hidden flex flex-col lg:min-h-[500px]">
                        <div className="px-5 py-4 border-b border-white/8">
                            <h2 className="text-2xl text-white uppercase" style={DF}>Configuration</h2>
                        </div>

                        <div className="p-5 lg:p-7 space-y-7 flex-grow">
                            {/* Game Mode */}
                            <div className="space-y-2.5">
                                <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest">Game Mode</label>
                                <div className="flex flex-wrap gap-2">
                                    {Object.entries(MODE_LABELS).map(([val, label]) => (
                                        <button
                                            key={val}
                                            disabled={!isHost}
                                            onClick={() => setMode(val)}
                                            className={`flex-1 min-w-[100px] px-4 py-3 rounded-xl font-bold text-sm uppercase tracking-wide transition-all active:scale-95 ${displayMode === val ? activeBtn : inactiveBtn}`}
                                        >
                                            {label}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Overs & Wickets */}
                            <div className="grid grid-cols-2 gap-5">
                                <div className="space-y-2.5">
                                    <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest">Overs</label>
                                    <div className="flex gap-2">
                                        {overOptions.map(o => (
                                            <button
                                                key={o}
                                                disabled={!isHost}
                                                onClick={() => setOvers(o)}
                                                className={`flex-1 py-3 rounded-xl font-bold text-sm uppercase tracking-wide transition-all active:scale-95 ${displayOvers === o ? activeBtn : inactiveBtn}`}
                                            >
                                                {o}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                                <div className="space-y-2.5">
                                    <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest">Wickets</label>
                                    <div className="flex gap-2">
                                        {wicketRange.map(w => (
                                            <button
                                                key={w}
                                                disabled={!isHost}
                                                onClick={() => setWickets(w)}
                                                className={`flex-1 py-3 rounded-xl font-bold text-lg transition-all active:scale-95 ${displayWickets === w ? activeBtn : inactiveBtn}`}
                                            >
                                                {w}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            {/* Host participation */}
                            {isHost && (
                                <div className="border-t border-white/8 pt-6">
                                    <label className="flex items-start gap-3 cursor-pointer group p-3.5 border border-white/8 hover:border-white/15 rounded-xl transition-colors">
                                        <div className="relative flex items-center mt-0.5">
                                            <input
                                                type="checkbox"
                                                checked={hostWantsToPlay}
                                                onChange={e => setHostWantsToPlay(e.target.checked)}
                                                className="peer appearance-none w-5 h-5 rounded border-2 border-white/20 bg-white/5 checked:bg-emerald-500 checked:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 cursor-pointer transition-all"
                                            />
                                            <svg className="absolute w-3 h-3 left-1 text-white pointer-events-none opacity-0 peer-checked:opacity-100 transition-opacity" viewBox="0 0 14 10" fill="none">
                                                <path d="M1 5L4.5 8.5L13 1" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                                            </svg>
                                        </div>
                                        <div>
                                            <span className="block font-bold text-white uppercase tracking-wide text-sm">I want to play</span>
                                            <span className="block text-xs text-slate-500 mt-0.5">Uncheck to spectate or manage the match only.</span>
                                        </div>
                                    </label>
                                </div>
                            )}

                            {/* CPU Config */}
                            {isHost && !lobby.cpu_only && (
                                <div>
                                    <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2.5">
                                        CPU Players ({cpuCount})
                                    </label>
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => sendMsg({ action: 'ADD_CPU' })}
                                            disabled={displayMode === '1v1' && cpuCount >= 1}
                                            className={`px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wider transition-all ${inactiveBtn}`}
                                        >
                                            + Add CPU
                                        </button>
                                        <button
                                            onClick={() => sendMsg({ action: 'REMOVE_CPU' })}
                                            disabled={cpuCount === 0}
                                            className={`px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wider transition-all ${inactiveBtn}`}
                                        >
                                            Remove
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Settings footer */}
                        {isHost && (
                            <div className="px-5 py-4 bg-white/3 border-t border-white/8 flex justify-between items-center">
                                <div className="flex items-center gap-2">
                                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Settings</span>
                                    {settingsChanged
                                        ? <span className="text-[10px] text-amber-400 font-bold uppercase">· Unsaved</span>
                                        : <span className="text-[10px] text-emerald-400 font-bold uppercase">· Saved</span>
                                    }
                                </div>
                                <button
                                    onClick={applySettings}
                                    className="text-xs text-white hover:text-emerald-400 font-bold uppercase tracking-widest transition-colors"
                                >
                                    Apply →
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                {/* ═══ TEAM ASSIGNMENT ═══ */}
                {isTeamMode && (
                    isHost ? (
                        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
                            <div className="lg:col-span-4 bg-slate-900 border border-white/8 rounded-2xl overflow-hidden flex flex-col lg:min-h-[500px]">
                                <div className="px-5 py-4 border-b border-white/8 flex items-center justify-between">
                                    <h2 className="text-2xl text-white uppercase" style={DF}>Teams</h2>
                                    <button
                                        onClick={() => sendMsg({ action: 'RESET_TEAMS' })}
                                        className="text-xs font-bold text-red-400 hover:text-red-300 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 px-3 py-1.5 rounded-lg uppercase tracking-wider transition-all"
                                    >
                                        Reset
                                    </button>
                                </div>
                                <div className="p-4 lg:p-5 flex flex-col gap-4 flex-grow">
                                    <div className="bg-white/4 rounded-xl p-3 border border-white/8">
                                        <div className="text-[10px] text-slate-500 mb-2 font-bold uppercase tracking-wider">
                                            Available — drag to team or click →
                                        </div>
                                        {unassignedPlayers.length > 0 ? (
                                            <div className="space-y-1.5">
                                                {unassignedPlayers.map(p => <DraggablePlayer key={p.username} player={p} sendMsg={sendMsg} />)}
                                            </div>
                                        ) : (
                                            <div className="text-xs text-emerald-400 text-center py-1.5 font-bold">All assigned ✓</div>
                                        )}
                                    </div>
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 flex-1 min-h-0">
                                        <TeamDropZone team="A" lobby={lobby} sendMsg={sendMsg} isHost={true} />
                                        <TeamDropZone team="B" lobby={lobby} sendMsg={sendMsg} isHost={true} />
                                    </div>
                                    {hasFullTeams && !hasBothCaptains && (
                                        <div className="text-center text-[11px] text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-xl py-2.5 px-3 font-bold uppercase tracking-wider">
                                            Select a captain for each team to continue
                                        </div>
                                    )}
                                </div>
                            </div>
                        </DndContext>
                    ) : (
                        <div className="lg:col-span-4 bg-slate-900 border border-white/8 rounded-2xl overflow-hidden flex flex-col lg:min-h-[500px]">
                            <div className="px-5 py-4 border-b border-white/8 flex items-center justify-between">
                                <h2 className="text-2xl text-white uppercase" style={DF}>Teams</h2>
                                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider bg-white/5 border border-white/10 px-2.5 py-1 rounded-full">Host assigns</span>
                            </div>
                            <div className="p-4 lg:p-5 flex flex-col gap-4 flex-grow">
                                {unassignedPlayers.length > 0 && (
                                    <div className="bg-white/4 rounded-xl p-3 border border-white/8">
                                        <div className="text-[10px] text-slate-500 mb-2 font-bold uppercase tracking-wider">Waiting to be assigned</div>
                                        <div className="space-y-1.5">
                                            {unassignedPlayers.map(p => (
                                                <div key={p.username} className="flex items-center gap-2 p-2 rounded-lg bg-white/5 border border-white/8">
                                                    <span className="text-xs text-white font-medium">{p.username}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 flex-1 min-h-0">
                                    <TeamDropZone team="A" lobby={lobby} sendMsg={sendMsg} isHost={false} />
                                    <TeamDropZone team="B" lobby={lobby} sendMsg={sendMsg} isHost={false} />
                                </div>
                            </div>
                        </div>
                    )
                )}
            </div>

            {/* ═══ START MATCH ═══ */}
            {isHost ? (
                <>
                    {/* Desktop */}
                    <div className="hidden lg:flex mt-10 justify-center pb-4">
                        <button
                            disabled={isTeamMode && (!hasFullTeams || !hasBothCaptains)}
                            onClick={() => { applySettings(); sendMsg({ action: mode === 'tournament' ? 'START_TOURNAMENT' : 'START_MATCH' }) }}
                            className="relative px-14 py-5 bg-linear-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white font-bold uppercase tracking-widest text-lg rounded-xl shadow-xl shadow-emerald-500/25 hover:shadow-emerald-400/35 hover:-translate-y-0.5 transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0"
                            style={DF}
                        >
                            {mode === 'tournament' ? '🏆 Start Tournament' : '🏏 Start Match'}
                        </button>
                    </div>
                    {/* Mobile fixed bottom */}
                    <div className="fixed bottom-0 left-0 right-0 p-3 bg-linear-to-t from-slate-950 via-slate-950/95 to-transparent z-50 lg:hidden">
                        <div className="max-w-md mx-auto">
                            <button
                                disabled={isTeamMode && (!hasFullTeams || !hasBothCaptains)}
                                onClick={() => { applySettings(); sendMsg({ action: mode === 'tournament' ? 'START_TOURNAMENT' : 'START_MATCH' }) }}
                                className="w-full bg-linear-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 text-white py-3.5 rounded-xl shadow-xl shadow-emerald-500/20 flex items-center justify-center gap-2 transition-all active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed font-bold uppercase tracking-widest text-sm"
                                style={DF}
                            >
                                {mode === 'tournament' ? '🏆 Start Tournament' : '🏏 Start Match'}
                            </button>
                        </div>
                    </div>
                </>
            ) : (
                <div className="mt-8 text-center">
                    <p className="text-slate-500 text-sm bg-white/5 border border-white/8 inline-block px-6 py-3 rounded-xl font-medium">
                        ⏳ Waiting for host to start…
                    </p>
                </div>
            )}
        </div>
    )
}

/* ─── Draggable Player ─────────────────────────────────────────── */

function DraggablePlayer({ player, sendMsg }: {
    player: { username: string; team: string | null; is_captain: boolean; in_match: boolean }
    sendMsg: (msg: Record<string, unknown>) => void
}) {
    const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: player.username })
    const style = { transform: CSS.Transform.toString(transform), transition: transition ?? 'transform 200ms ease', zIndex: isDragging ? 50 : 'auto' as const, opacity: isDragging ? 0.85 : 1 }

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={`flex items-center justify-between p-2.5 rounded-lg border transition-all ${isDragging
                ? 'bg-emerald-500/15 border-emerald-500/40 shadow-xl scale-105'
                : 'bg-white/5 border-white/10 hover:border-white/20 hover:bg-white/8'
            }`}
        >
            <div {...attributes} {...listeners} className="flex items-center gap-2 cursor-grab active:cursor-grabbing flex-1 min-w-0">
                <span className="text-slate-600 text-xs select-none">⠿</span>
                <span className="text-xs text-white font-medium truncate">{player.username}</span>
            </div>
            <div className="flex gap-1 shrink-0 ml-2">
                <button
                    onClick={e => { e.stopPropagation(); sendMsg({ action: 'ASSIGN_TEAM', player: player.username, team: 'A' }) }}
                    className="h-5 px-1.5 text-[9px] font-bold rounded-md bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 border border-blue-500/30 transition-colors"
                >A</button>
                <button
                    onClick={e => { e.stopPropagation(); sendMsg({ action: 'ASSIGN_TEAM', player: player.username, team: 'B' }) }}
                    className="h-5 px-1.5 text-[9px] font-bold rounded-md bg-violet-500/20 hover:bg-violet-500/30 text-violet-300 border border-violet-500/30 transition-colors"
                >B</button>
            </div>
        </div>
    )
}

/* ─── Team Drop Zone ───────────────────────────────────────────── */

function TeamDropZone({ team, lobby, sendMsg, isHost }: {
    team: 'A' | 'B'; lobby: LobbyData
    sendMsg: (msg: Record<string, unknown>) => void; isHost: boolean
}) {
    const { setNodeRef, isOver } = useDroppable({ id: team })
    const teamPlayers = lobby.teams[team] || []
    const captain     = lobby.captains[team]
    const isA         = team === 'A'

    const borderColor = isOver
        ? (isA ? 'border-blue-400/60 bg-blue-500/8' : 'border-violet-400/60 bg-violet-500/8')
        : (isA ? 'border-blue-500/20' : 'border-violet-500/20')
    const titleColor  = isA ? 'text-blue-300' : 'text-violet-300'
    const capBtnColor = isA
        ? 'bg-blue-500/15 hover:bg-blue-500/25 text-blue-300 border-blue-500/30'
        : 'bg-violet-500/15 hover:bg-violet-500/25 text-violet-300 border-violet-500/30'

    return (
        <div
            ref={setNodeRef}
            className={`rounded-xl border-2 border-dashed transition-all ${borderColor} p-3 flex flex-col min-h-[100px]`}
        >
            <div className={`font-bold text-sm mb-2 ${titleColor} flex items-center justify-between shrink-0`} style={DF}>
                <span>{lobby.team_names[team]}</span>
                {captain && (
                    <span className="text-amber-300 text-[9px] font-bold bg-amber-500/15 border border-amber-500/20 px-1.5 py-0.5 rounded-full">
                        {captain} 👑
                    </span>
                )}
            </div>
            <div className="space-y-1.5 flex-1">
                {teamPlayers.length > 0 ? (
                    teamPlayers.map(name => (
                        <div key={name} className="flex items-center justify-between bg-white/5 p-2 rounded-lg border border-white/8">
                            <div className="flex items-center gap-1.5">
                                <span className="text-xs text-white font-medium">{name}</span>
                                {captain === name && <span className="text-amber-400 text-xs">👑</span>}
                            </div>
                            {isHost && captain !== name && (
                                <button
                                    onClick={() => sendMsg({ action: 'SET_CAPTAIN', team, captain: name })}
                                    className={`h-5 px-1.5 text-[9px] font-bold rounded-md border transition-colors ${capBtnColor}`}
                                >
                                    👑
                                </button>
                            )}
                        </div>
                    ))
                ) : (
                    <div className={`text-[10px] text-center py-4 font-medium ${isOver && isHost ? 'text-white' : 'text-slate-600'}`}>
                        {isHost ? (isOver ? 'Drop here!' : 'Drag players here') : 'Waiting for host'}
                    </div>
                )}
            </div>
        </div>
    )
}
