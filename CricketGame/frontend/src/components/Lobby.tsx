/**
 * Lobby — Editorial-style match setup page.
 * 
 * DESKTOP (lg+): Two-column grid — Squad List (5 cols) | Configuration (7 cols)
 *   + "Start Match" button centered below on its own row.
 * MOBILE: Stacked cards — Squad List → Configuration → Fixed "Start Match" bar.
 * 
 * Design refs:
 *   PC:     Designs/Lobby-pc/code.html
 *   Mobile: Designs/Lobby-Mobile/code.html
 */
import { useState } from 'react'
import { DndContext, closestCenter, PointerSensor, useSensor, useSensors, useDroppable } from '@dnd-kit/core'
import type { DragEndEvent } from '@dnd-kit/core'
import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

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

interface Props {
    lobby: LobbyData
    username: string
    sendMsg: (msg: Record<string, unknown>) => void
}

const MODE_LABELS: Record<string, string> = {
    '1v1': '1v1 Quick Match',
    'tournament': 'Tournament',
    'team': 'Team Mode',
}

const DISPLAY_FONT = { fontFamily: "'Anton', 'Bebas Neue', 'Teko', sans-serif" }

export default function Lobby({ lobby, username, sendMsg }: Props) {
    const isHost = username === lobby.host
    const normalizedLobbyMode = lobby.mode === '2v2' ? 'team' : lobby.mode
    const [mode, setMode] = useState(normalizedLobbyMode)
    const [overs, setOvers] = useState(lobby.overs)
    const [wickets, setWickets] = useState(lobby.wickets)
    const [hostWantsToPlay, setHostWantsToPlay] = useState(lobby.host_plays ?? true)

    const displayMode = isHost ? mode : normalizedLobbyMode
    const displayOvers = isHost ? overs : lobby.overs
    const displayWickets = isHost ? wickets : lobby.wickets

    // Drag-and-drop sensor for team mode
    const sensors = useSensors(
        useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
    )

    const overOptions = displayMode === 'team' ? [5, 10] : [2, 5]
    const wicketRange = displayMode === 'team' ? [2, 3, 4, 5] : [1, 2, 3]

    const applySettings = () => {
        sendMsg({ action: 'CONFIGURE', mode, overs, wickets, host_plays: hostWantsToPlay })
    }

    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event
        if (!over) return
        const playerName = active.id as string
        const targetTeam = over.id as string
        if (targetTeam === 'A' || targetTeam === 'B') {
            sendMsg({ action: 'ASSIGN_TEAM', player: playerName, team: targetTeam })
        }
    }

    const assignedSet = new Set([...(lobby.teams.A || []), ...(lobby.teams.B || [])])
    const unassignedPlayers = lobby.players.filter(p => !assignedSet.has(p.username))
    const isTeamMode = displayMode === 'team'
    const totalPlayers = lobby.players.length
    const assignedCount = (lobby.teams.A?.length || 0) + (lobby.teams.B?.length || 0)
    const cpuCount = lobby.cpu_count ?? (lobby.cpu_enabled ? 1 : 0)

    const hasBothCaptains = !!lobby.captains.A && !!lobby.captains.B
    const hasFullTeams = assignedCount === totalPlayers
        && (lobby.teams.A?.length || 0) >= 2
        && (lobby.teams.A?.length || 0) === (lobby.teams.B?.length || 0)

    const settingsChanged = isHost && (
        mode !== normalizedLobbyMode ||
        overs !== lobby.overs ||
        wickets !== lobby.wickets ||
        hostWantsToPlay !== (lobby.host_plays ?? true)
    )

    return (
        <div className="w-full px-4 sm:px-6 lg:px-8 py-3 lg:py-6 pb-28 lg:pb-6 flex flex-col">
            {/* ─── Page Title ─── */}
            <div className="flex flex-col md:flex-row md:items-end justify-between mb-4 lg:mb-6 gap-2 lg:gap-4">
                <div>
                    <div className="bg-emerald-500 text-white text-[10px] font-bold uppercase tracking-[0.2em] px-2 py-1 mb-2 inline-block">
                        Lobby Area
                    </div>
                    <h1 className="text-4xl lg:text-5xl uppercase tracking-tight text-slate-900" style={DISPLAY_FONT}>
                        Match Setup
                    </h1>
                </div>
                <div className="flex items-center gap-2 text-slate-400 text-sm font-medium">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    Server Live
                </div>
            </div>

            {/* ─── Main Grid ─── */}
            <div className={`grid gap-6 lg:gap-8 items-start flex-grow ${isTeamMode ? 'grid-cols-1 lg:grid-cols-12' : 'grid-cols-1 lg:grid-cols-12'}`}>

                {/* ═══ COLUMN 1: SQUAD LIST ═══ */}
                <div className={`${isTeamMode ? 'lg:col-span-4' : 'lg:col-span-5'} flex flex-col`}>
                    <div className="bg-white border border-slate-200 shadow-sm rounded-sm overflow-hidden flex flex-col h-full lg:min-h-[500px]">
                        {/* Squad Header */}
                        <div className="p-4 lg:p-6 border-b border-slate-100 flex justify-between items-center bg-slate-50">
                            <h2 className="text-2xl uppercase tracking-wide text-slate-900" style={DISPLAY_FONT}>Squad List</h2>
                            <span className="bg-emerald-500/10 text-emerald-600 text-xs font-bold px-2 py-1 rounded border border-emerald-500/20">
                                {totalPlayers}/22 Players
                            </span>
                        </div>

                        {/* Player Cards */}
                        <div className="p-4 lg:p-6 flex-grow flex flex-col gap-3 overflow-y-auto">
                            {/* Horizontal scroll on mobile, vertical on desktop */}
                            <div className="flex lg:flex-col gap-3 overflow-x-auto lg:overflow-x-visible pb-2 lg:pb-0 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden snap-x lg:snap-none">
                                {lobby.players.map(p => {
                                    const initial = p.username.charAt(0).toUpperCase()
                                    return (
                                        <div
                                            key={p.username}
                                            className="snap-start shrink-0 w-64 lg:w-auto flex items-center justify-between p-3 lg:p-4 bg-slate-800 text-white rounded lg:rounded-none shadow-md border-l-4 border-emerald-500 group transition-all hover:translate-x-1"
                                        >
                                            <div className="flex items-center gap-3 lg:gap-4">
                                                <div className="w-9 h-9 lg:w-10 lg:h-10 rounded bg-emerald-500 flex items-center justify-center text-lg text-white shadow-inner" style={DISPLAY_FONT}>
                                                    {initial}
                                                </div>
                                                <div>
                                                    <div className="font-bold text-sm lg:text-lg leading-none">{p.username}</div>
                                                    {p.username === lobby.host && (
                                                        <div className="text-[10px] uppercase tracking-widest text-slate-400 mt-1">Room Host</div>
                                                    )}
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                {p.username === lobby.host && (
                                                    <span className="bg-white/10 text-white text-[10px] font-bold px-2 py-1 rounded uppercase tracking-wider backdrop-blur-sm">Host</span>
                                                )}
                                                {p.is_captain && (
                                                    <span className="bg-yellow-500/20 text-yellow-300 text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider">Capt</span>
                                                )}
                                                {p.team && (
                                                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${p.team === 'A' ? 'bg-blue-500/30 text-blue-200' : 'bg-purple-500/30 text-purple-200'}`}>
                                                        Team {p.team}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    )
                                })}
                            </div>

                            {/* Waiting placeholder */}
                            {!isTeamMode && (
                                <div className="flex items-center justify-center p-6 lg:p-8 border-2 border-dashed border-slate-200 rounded text-slate-400 flex-col gap-2 bg-slate-50/50">
                                    <span className="text-3xl opacity-50">🏏</span>
                                    <span className="text-sm font-medium uppercase tracking-wide">Waiting for players...</span>
                                </div>
                            )}
                        </div>

                        {/* Add CPU bottom bar */}
                        {isHost && !lobby.cpu_only && (
                            <div className="p-4 lg:p-6 border-t border-slate-100 bg-slate-50">
                                <button
                                    onClick={() => sendMsg({ action: 'ADD_CPU' })}
                                    disabled={displayMode === '1v1' && cpuCount >= 1}
                                    className="w-full flex items-center justify-center gap-2 py-3 border border-slate-300 bg-white hover:bg-slate-100 text-slate-600 font-bold uppercase tracking-widest text-xs transition-all rounded shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    + Add CPU Player
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                {/* ═══ COLUMN 2: CONFIGURATION ═══ */}
                <div className={`${isTeamMode ? 'lg:col-span-4' : 'lg:col-span-7'} flex flex-col`}>
                    <div className="bg-white border border-slate-200 shadow-sm rounded-sm overflow-hidden flex flex-col h-full lg:min-h-[500px] relative">
                        {/* Background gear watermark (PC only) */}
                        <div className="absolute top-0 right-0 p-10 opacity-5 pointer-events-none hidden lg:block">
                            <span className="text-[120px]">⚙️</span>
                        </div>

                        {/* Config Header */}
                        <div className="p-4 lg:p-6 border-b border-slate-100 bg-slate-50 relative z-10">
                            <h2 className="text-2xl uppercase tracking-wide text-slate-900" style={DISPLAY_FONT}>Configuration</h2>
                        </div>

                        {/* Config Controls */}
                        <div className="p-4 lg:p-8 space-y-6 lg:space-y-10 flex-grow relative z-10">
                            {/* Game Mode */}
                            <div className="space-y-3">
                                <label className="block text-[10px] lg:text-xs font-bold text-slate-400 uppercase tracking-widest">Game Mode</label>
                                {/* Mobile: full-width active + 2-col grid for rest; Desktop: flex row */}
                                <div className="hidden lg:flex flex-wrap gap-2">
                                    {Object.entries(MODE_LABELS).map(([val, label]) => (
                                        <button
                                            key={val}
                                            disabled={!isHost}
                                            onClick={() => setMode(val)}
                                            className={`flex-1 min-w-[120px] px-6 py-4 rounded font-bold text-sm uppercase tracking-wide transition-all active:scale-95 ${displayMode === val
                                                ? 'bg-slate-900 text-white shadow-lg ring-2 ring-emerald-500 ring-offset-2'
                                                : 'bg-white border border-slate-200 text-slate-500 hover:text-slate-900 hover:border-slate-400'
                                                } disabled:opacity-60 disabled:cursor-not-allowed`}
                                        >
                                            {label}
                                        </button>
                                    ))}
                                </div>
                                {/* Mobile mode selector */}
                                <div className="lg:hidden space-y-2">
                                    {Object.entries(MODE_LABELS).map(([val, label]) => {
                                        const isActive = displayMode === val
                                        if (isActive) {
                                            return (
                                                <button
                                                    key={val}
                                                    disabled={!isHost}
                                                    className="relative w-full bg-slate-900 text-white py-3 px-4 rounded-lg font-bold text-sm border-2 border-emerald-500 shadow-lg flex items-center justify-center disabled:opacity-60"
                                                >
                                                    {label.toUpperCase()}
                                                    <span className="absolute -top-2 -right-2 w-4 h-4 bg-emerald-500 rounded-full flex items-center justify-center shadow-sm">
                                                        <span className="text-[10px] text-white font-bold">✓</span>
                                                    </span>
                                                </button>
                                            )
                                        }
                                        return null
                                    })}
                                    <div className="grid grid-cols-2 gap-2">
                                        {Object.entries(MODE_LABELS).map(([val, label]) => {
                                            if (displayMode === val) return null
                                            return (
                                                <button
                                                    key={val}
                                                    disabled={!isHost}
                                                    onClick={() => setMode(val)}
                                                    className="bg-white text-slate-600 py-3 px-2 rounded-lg font-bold text-xs border border-slate-200 hover:border-slate-300 uppercase disabled:opacity-60 disabled:cursor-not-allowed"
                                                >
                                                    {label}
                                                </button>
                                            )
                                        })}
                                    </div>
                                </div>
                            </div>

                            {/* Overs & Wickets — side by side on desktop */}
                            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 lg:gap-8">
                                {/* Overs */}
                                <div className="space-y-3">
                                    <label className="block text-[10px] lg:text-xs font-bold text-slate-400 uppercase tracking-widest">Overs</label>
                                    {/* Desktop: separate buttons / Mobile: pill toggle */}
                                    <div className="hidden lg:flex gap-2">
                                        {overOptions.map(o => (
                                            <button
                                                key={o}
                                                disabled={!isHost}
                                                onClick={() => setOvers(o)}
                                                className={`flex-1 px-4 py-3 rounded font-bold text-sm uppercase shadow-md transition-all active:scale-95 ${displayOvers === o
                                                    ? 'bg-slate-900 text-white'
                                                    : 'bg-white border border-slate-200 text-slate-500 hover:border-emerald-500 hover:text-emerald-500'
                                                    } disabled:opacity-60 disabled:cursor-not-allowed`}
                                            >
                                                {o} Overs
                                            </button>
                                        ))}
                                    </div>
                                    {/* Mobile pill toggle */}
                                    <div className="lg:hidden flex bg-slate-100 p-1 rounded-lg border border-slate-200">
                                        {overOptions.map(o => (
                                            <button
                                                key={o}
                                                disabled={!isHost}
                                                onClick={() => setOvers(o)}
                                                className={`flex-1 py-2 rounded text-sm font-bold transition-all ${displayOvers === o
                                                    ? 'bg-slate-900 text-white shadow-sm'
                                                    : 'text-slate-500 hover:bg-white/50'
                                                    } disabled:opacity-60 disabled:cursor-not-allowed`}
                                            >
                                                {o} OVERS
                                            </button>
                                        ))}
                                    </div>
                                </div>

                                {/* Wickets */}
                                <div className="space-y-3">
                                    <label className="block text-[10px] lg:text-xs font-bold text-slate-400 uppercase tracking-widest">Wickets</label>
                                    <div className="flex gap-2">
                                        {wicketRange.map(w => (
                                            <button
                                                key={w}
                                                disabled={!isHost}
                                                onClick={() => setWickets(w)}
                                                className={`w-12 h-10 lg:h-12 flex items-center justify-center rounded font-bold text-lg transition-all active:scale-95 ${displayWickets === w
                                                    ? 'bg-slate-900 text-white shadow-md'
                                                    : 'bg-white border border-slate-200 text-slate-500 hover:border-emerald-500 hover:text-emerald-500'
                                                    } disabled:opacity-60 disabled:cursor-not-allowed`}
                                            >
                                                {w}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            {/* Host participation checkbox */}
                            {isHost && (
                                <div className="pt-2 lg:pt-6 border-t border-slate-100">
                                    <label className="flex items-start gap-3 lg:gap-4 cursor-pointer group p-3 lg:p-4 border border-slate-200 rounded hover:bg-slate-50 transition-colors">
                                        <div className="relative flex items-center mt-0.5">
                                            <input
                                                type="checkbox"
                                                checked={hostWantsToPlay}
                                                onChange={(e) => setHostWantsToPlay(e.target.checked)}
                                                className="peer appearance-none w-5 h-5 lg:w-6 lg:h-6 rounded border-2 border-slate-300 bg-white checked:bg-emerald-500 checked:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 cursor-pointer transition-all"
                                            />
                                            <svg className="absolute w-3 h-3 lg:w-3.5 lg:h-3.5 left-1 lg:left-[5px] text-white pointer-events-none opacity-0 peer-checked:opacity-100 transition-opacity" viewBox="0 0 14 10" fill="none">
                                                <path d="M1 5L4.5 8.5L13 1" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                            </svg>
                                        </div>
                                        <div>
                                            <span className="block font-bold text-slate-900 uppercase tracking-wide text-sm">I want to play</span>
                                            <span className="block text-xs text-slate-500 mt-1">Uncheck this box if you wish to spectate or manage the match only.</span>
                                        </div>
                                    </label>
                                </div>
                            )}

                            {/* CPU Config */}
                            {isHost && !lobby.cpu_only && (
                                <div className="pt-2">
                                    <label className="block text-[10px] lg:text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">
                                        CPU Configuration ({cpuCount})
                                    </label>
                                    <div className="flex gap-3">
                                        <button
                                            onClick={() => sendMsg({ action: 'ADD_CPU' })}
                                            disabled={displayMode === '1v1' && cpuCount >= 1}
                                            className="px-4 py-2 bg-white border border-slate-200 text-slate-600 text-xs font-bold uppercase tracking-wider rounded hover:bg-slate-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            Add CPU
                                        </button>
                                        <button
                                            onClick={() => sendMsg({ action: 'REMOVE_CPU' })}
                                            aria-label="Remove the last added CPU player"
                                            disabled={cpuCount === 0}
                                            className="px-4 py-2 bg-white border border-slate-200 text-slate-400 text-xs font-bold uppercase tracking-wider rounded disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            Remove CPU
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Settings Status Bar (dark bottom strip) */}
                        {isHost && (
                            <div className="mt-auto p-4 lg:p-6 bg-slate-900 border-t border-slate-800 flex justify-between items-center">
                                <div className="flex flex-col lg:flex-row lg:gap-2">
                                    <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider font-mono">Settings</span>
                                    {settingsChanged && (
                                        <span className="text-[10px] text-red-400 font-bold uppercase">Unsaved</span>
                                    )}
                                    {!settingsChanged && (
                                        <span className="text-[10px] text-emerald-400 font-bold uppercase">Saved</span>
                                    )}
                                </div>
                                <button
                                    onClick={applySettings}
                                    className="text-white hover:text-emerald-400 text-xs font-bold uppercase tracking-widest transition-colors"
                                >
                                    Apply Settings
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                {/* ═══ COLUMN 3: TEAM ASSIGNMENT (only in team mode) ═══ */}
                {isTeamMode && (
                    isHost ? (
                        <DndContext
                            sensors={sensors}
                            collisionDetection={closestCenter}
                            onDragEnd={handleDragEnd}
                        >
                            <div className="lg:col-span-4 bg-white border border-slate-200 shadow-sm rounded-sm overflow-hidden flex flex-col lg:min-h-[500px]">
                                <div className="p-4 lg:p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50">
                                    <h2 className="text-2xl uppercase tracking-wide text-slate-900" style={DISPLAY_FONT}>Teams</h2>
                                    <Button
                                        size="sm"
                                        onClick={() => sendMsg({ action: 'RESET_TEAMS' })}
                                        className="bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 text-xs font-bold uppercase tracking-wider"
                                    >
                                        Reset
                                    </Button>
                                </div>
                                <div className="p-4 lg:p-6 flex flex-col gap-4 flex-grow">
                                    {/* Unassigned */}
                                    <div className="bg-slate-50 rounded p-3 border border-slate-200">
                                        <div className="text-[10px] text-slate-500 mb-2 font-bold uppercase tracking-wider">
                                            Available — drag to team or click →
                                        </div>
                                        {unassignedPlayers.length > 0 ? (
                                            <div className="space-y-1.5">
                                                {unassignedPlayers.map(p => (
                                                    <DraggablePlayer key={p.username} player={p} sendMsg={sendMsg} />
                                                ))}
                                            </div>
                                        ) : (
                                            <div className="text-xs text-emerald-500 text-center py-1.5 font-bold">All assigned!</div>
                                        )}
                                    </div>

                                    {/* Drop zones */}
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 flex-1 min-h-0">
                                        <TeamDropZone team="A" lobby={lobby} sendMsg={sendMsg} isHost={true} />
                                        <TeamDropZone team="B" lobby={lobby} sendMsg={sendMsg} isHost={true} />
                                    </div>
                                </div>

                                {/* Captain validation */}
                                {hasFullTeams && !hasBothCaptains && (
                                    <div className="mx-4 lg:mx-6 mb-4 text-center text-[11px] text-amber-500 bg-amber-50 border border-amber-200 rounded py-2 px-3 font-bold uppercase tracking-wider">
                                        Select a captain for each team to start
                                    </div>
                                )}
                            </div>
                        </DndContext>
                    ) : (
                        /* Read-only Teams view for non-host */
                        <div className="lg:col-span-4 bg-white border border-slate-200 shadow-sm rounded-sm overflow-hidden flex flex-col lg:min-h-[500px]">
                            <div className="p-4 lg:p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50">
                                <h2 className="text-2xl uppercase tracking-wide text-slate-900" style={DISPLAY_FONT}>Teams</h2>
                                <Badge className="bg-slate-100 text-slate-500 border-slate-200 text-[10px] uppercase tracking-wider font-bold">Host assigns</Badge>
                            </div>
                            <div className="p-4 lg:p-6 flex flex-col gap-4 flex-grow">
                                {unassignedPlayers.length > 0 && (
                                    <div className="bg-slate-50 rounded p-3 border border-slate-200">
                                        <div className="text-[10px] text-slate-500 mb-2 font-bold uppercase tracking-wider">Waiting to be assigned</div>
                                        <div className="space-y-1.5">
                                            {unassignedPlayers.map(p => (
                                                <div key={p.username} className="flex items-center gap-2 p-2 rounded bg-white border border-slate-200 shadow-sm">
                                                    <span className="text-xs text-slate-900 font-medium">{p.username}</span>
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

            {/* ═══ START MATCH BUTTON ═══ */}
            {isHost ? (
                <>
                    {/* Desktop: centered below grid */}
                    <div className="hidden lg:flex mt-10 justify-center pb-6">
                        {mode !== 'tournament' ? (
                            <button
                                disabled={isTeamMode && (!hasFullTeams || !hasBothCaptains)}
                                onClick={() => { applySettings(); sendMsg({ action: 'START_MATCH' }) }}
                                className="group relative inline-flex items-center justify-center px-12 py-5 text-lg font-bold text-white transition-all duration-200 bg-emerald-500 uppercase tracking-widest hover:bg-emerald-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 shadow-xl hover:shadow-2xl hover:-translate-y-1 rounded-sm overflow-hidden disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:shadow-xl"
                                style={DISPLAY_FONT}
                            >
                                <span className="absolute inset-0 w-full h-full -mt-1 rounded-lg opacity-30 bg-gradient-to-b from-transparent via-transparent to-black" />
                                <span className="relative flex items-center gap-3">
                                    Start Match <span className="text-xl">🏏</span>
                                </span>
                            </button>
                        ) : (
                            <button
                                onClick={() => { applySettings(); sendMsg({ action: 'START_TOURNAMENT' }) }}
                                className="group relative inline-flex items-center justify-center px-12 py-5 text-lg font-bold text-white transition-all duration-200 bg-emerald-500 uppercase tracking-widest hover:bg-emerald-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-emerald-500 shadow-xl hover:shadow-2xl hover:-translate-y-1 rounded-sm overflow-hidden"
                                style={DISPLAY_FONT}
                            >
                                <span className="absolute inset-0 w-full h-full -mt-1 rounded-lg opacity-30 bg-gradient-to-b from-transparent via-transparent to-black" />
                                <span className="relative flex items-center gap-3">
                                    Start Tournament <span className="text-xl">🏆</span>
                                </span>
                            </button>
                        )}
                    </div>

                    {/* Mobile: fixed bottom bar */}
                    <div className="fixed bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-slate-50 via-slate-50 to-transparent z-50 lg:hidden border-t border-slate-200/50 backdrop-blur-sm">
                        <div className="max-w-md mx-auto space-y-1 px-2">
                            {mode !== 'tournament' ? (
                                <button
                                    disabled={isTeamMode && (!hasFullTeams || !hasBothCaptains)}
                                    onClick={() => { applySettings(); sendMsg({ action: 'START_MATCH' }) }}
                                    className="w-full bg-emerald-500 hover:bg-emerald-600 text-white py-3 rounded-lg shadow-lg shadow-emerald-500/20 flex items-center justify-center gap-2 transform transition active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    <span className="text-xl leading-none uppercase italic tracking-wider mt-0.5" style={DISPLAY_FONT}>Start Match</span>
                                    <span className="text-lg leading-none">🏏</span>
                                </button>
                            ) : (
                                <button
                                    onClick={() => { applySettings(); sendMsg({ action: 'START_TOURNAMENT' }) }}
                                    className="w-full bg-emerald-500 hover:bg-emerald-600 text-white py-3 rounded-lg shadow-lg shadow-emerald-500/20 flex items-center justify-center gap-2 transform transition active:scale-[0.98]"
                                >
                                    <span className="text-xl leading-none uppercase italic tracking-wider mt-0.5" style={DISPLAY_FONT}>Start Tournament</span>
                                    <span className="text-lg leading-none">🏆</span>
                                </button>
                            )}
                            <p className="text-center text-[10px] text-slate-400 font-medium">© 2026 E Cricket</p>
                        </div>
                    </div>
                </>
            ) : (
                <div className="mt-6 text-center">
                    <p className="text-slate-500 text-sm bg-white inline-block px-6 py-3 rounded border border-slate-200 font-medium shadow-sm">
                        ⏳ Waiting for host to start the match...
                    </p>
                </div>
            )}
        </div>
    )
}

/* ═══════════════════════════════════════════════════════════════
   DRAGGABLE PLAYER (team mode)
   ═══════════════════════════════════════════════════════════════ */

function DraggablePlayer({ player, sendMsg }: {
    player: { username: string; team: string | null; is_captain: boolean; in_match: boolean }
    sendMsg: (msg: Record<string, unknown>) => void
}) {
    const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: player.username })
    const style = {
        transform: CSS.Transform.toString(transform),
        transition: transition ?? 'transform 200ms ease',
        zIndex: isDragging ? 50 : 'auto' as const,
        opacity: isDragging ? 0.8 : 1,
    }

    return (
        <div
            ref={setNodeRef}
            style={style}
            className={`flex items-center justify-between p-2.5 rounded border transition-all ${isDragging
                ? 'bg-emerald-50 border-emerald-200 shadow-xl shadow-emerald-500/10 scale-105'
                : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50 shadow-sm'
                }`}
        >
            <div {...attributes} {...listeners} className="flex items-center gap-2 cursor-grab active:cursor-grabbing flex-1 min-w-0">
                <span className="text-slate-400 text-xs select-none">⠿</span>
                <span className="text-xs text-slate-900 font-medium truncate">{player.username}</span>
            </div>
            <div className="flex gap-1 flex-shrink-0 ml-2">
                <button
                    aria-label={`Assign ${player.username} to Team A`}
                    title="Assign to Team A"
                    onClick={(e) => { e.stopPropagation(); sendMsg({ action: 'ASSIGN_TEAM', player: player.username, team: 'A' }) }}
                    className="h-5 px-1.5 text-[9px] font-bold rounded bg-blue-50 hover:bg-blue-100 text-blue-600 border border-blue-200 transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                >A</button>
                <button
                    aria-label={`Assign ${player.username} to Team B`}
                    title="Assign to Team B"
                    onClick={(e) => { e.stopPropagation(); sendMsg({ action: 'ASSIGN_TEAM', player: player.username, team: 'B' }) }}
                    className="h-5 px-1.5 text-[9px] font-bold rounded bg-purple-50 hover:bg-purple-100 text-purple-600 border border-purple-200 transition-colors focus-visible:ring-2 focus-visible:ring-purple-500 focus-visible:outline-none"
                >B</button>
            </div>
        </div>
    )
}

/* ═══════════════════════════════════════════════════════════════
   DROPPABLE TEAM ZONE (team mode)
   ═══════════════════════════════════════════════════════════════ */

function TeamDropZone({ team, lobby, sendMsg, isHost }: {
    team: 'A' | 'B'; lobby: LobbyData
    sendMsg: (msg: Record<string, unknown>) => void; isHost: boolean
}) {
    const { setNodeRef, isOver } = useDroppable({ id: team })
    const teamPlayers = lobby.teams[team] || []
    const captain = lobby.captains[team]

    const isA = team === 'A'
    const borderColor = isOver
        ? (isA ? 'border-blue-300 shadow-blue-500/10 shadow-lg' : 'border-purple-300 shadow-purple-500/10 shadow-lg')
        : (isA ? 'border-blue-200' : 'border-purple-200')
    const gradient = isA ? 'from-blue-50/50 to-cyan-50/50' : 'from-purple-50/50 to-pink-50/50'
    const titleColor = isA ? 'text-blue-700' : 'text-purple-700'
    const captainBtnColor = isA
        ? 'bg-blue-50 hover:bg-blue-100 text-blue-600 border-blue-200'
        : 'bg-purple-50 hover:bg-purple-100 text-purple-600 border-purple-200'

    return (
        <div
            ref={setNodeRef}
            className={`rounded border-2 border-dashed transition-all bg-gradient-to-br ${gradient} ${borderColor} p-3 flex flex-col min-h-[100px]`}
        >
            <div className={`font-bold text-sm mb-2 ${titleColor} flex items-center justify-between flex-shrink-0`}>
                <span>{lobby.team_names[team]}</span>
                {captain && (
                    <Badge className="bg-yellow-50 text-yellow-600 border-yellow-200 text-[9px] px-1">{captain}</Badge>
                )}
            </div>
            <div className="space-y-1.5 flex-1">
                {teamPlayers.length > 0 ? (
                    teamPlayers.map(playerName => (
                        <div key={playerName} className="flex items-center justify-between bg-white p-2 rounded border border-slate-200 shadow-sm">
                            <div className="flex items-center gap-1.5">
                                <span className="text-xs text-slate-900 font-medium">{playerName}</span>
                                {captain === playerName && <span className="text-yellow-500 text-xs">👑</span>}
                            </div>
                            {isHost && captain !== playerName && (
                                <button
                                    aria-label={`Make ${playerName} captain`}
                                    title="Make Captain"
                                    onClick={() => sendMsg({ action: 'SET_CAPTAIN', team, captain: playerName })}
                                    className={`h-5 px-1.5 text-[9px] font-bold rounded border transition-colors ${captainBtnColor} focus-visible:ring-2 focus-visible:ring-yellow-500 focus-visible:outline-none`}
                                >
                                    👑
                                </button>
                            )}
                        </div>
                    ))
                ) : (
                    <div className={`text-[10px] text-center py-4 font-medium ${isOver && isHost ? 'text-slate-900' : 'text-slate-400'}`}>
                        {isHost ? (isOver ? 'Drop here!' : 'Drag players here') : 'Waiting for host'}
                    </div>
                )}
            </div>
        </div>
    )
}
