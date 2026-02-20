/**
 * Lobby — Host controls, player list, game settings, team assignment.
 * Full-width layout with smooth drag-and-drop team assignment + click fallbacks.
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

    // Lower activation distance for smoother drag start
    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: { distance: 5 },
        })
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

    return (
        <div className="w-full h-full flex flex-col px-4 py-3 gap-3">
            {/* Main Grid */}
            <div className={`flex-1 grid gap-4 min-h-0 ${isTeamMode ? 'grid-cols-1 lg:grid-cols-3' : 'grid-cols-1 lg:grid-cols-2'}`}>

                {/* Column 1: Player List */}
                <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5 shadow-2xl flex flex-col min-h-0">
                    <div className="flex items-center justify-between mb-3 flex-shrink-0">
                        <h3 className="text-xl font-bold text-white flex items-center gap-2">
                            <span className="text-2xl"></span>
                            Players ({lobby.players.length})
                        </h3>
                        <Badge className="bg-gradient-to-r from-orange-500 to-pink-600 text-white border-0 text-xs px-2.5 py-1">
                            {MODE_LABELS[normalizedLobbyMode] ?? normalizedLobbyMode}
                        </Badge>
                    </div>
                    <div className="space-y-1.5 flex-1 overflow-y-auto min-h-0">
                        {lobby.players.map(p => (
                            <div
                                key={p.username}
                                className="flex items-center justify-between p-3 rounded-xl bg-slate-800/70 border border-slate-700/50 hover:bg-slate-700/50 transition-all"
                            >
                                <div className="flex items-center gap-2">
                                    <span className="text-sm font-semibold text-white">{p.username}</span>
                                    {p.username === lobby.host && (
                                        <Badge className="bg-blue-500/20 text-blue-300 border-blue-500/30 text-[10px] px-1.5">Host</Badge>
                                    )}
                                    {p.is_captain && (
                                        <Badge className="bg-yellow-500/20 text-yellow-300 border-yellow-500/30 text-[10px] px-1.5"></Badge>
                                    )}
                                </div>
                                <div className="flex items-center gap-1.5">
                                    {p.team && (
                                        <Badge className={`text-[10px] ${p.team === 'A' ? 'bg-blue-500/20 text-blue-300 border-blue-500/30' : 'bg-purple-500/20 text-purple-300 border-purple-500/30'}`}>
                                            Team {p.team}
                                        </Badge>
                                    )}
                                </div>
                            </div>
                        ))}
                        {lobby.players.length === 0 && (
                            <p className="text-slate-400 text-sm text-center py-4">No players yet...</p>
                        )}
                    </div>
                </div>

                {/* Column 2: Match Settings */}
                <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5 shadow-2xl flex flex-col min-h-0">
                    <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2 flex-shrink-0">
                        <span className="text-2xl">️</span> Match Settings
                    </h3>
                    <div className="space-y-4 flex-1">
                        {/* Mode */}
                        <div>
                            <label className="text-xs font-semibold mb-1.5 block text-slate-300 uppercase tracking-wide">Mode</label>
                            <div className="flex gap-2 flex-wrap">
                                {Object.entries(MODE_LABELS).map(([val, label]) => (
                                    <Button
                                        key={val}
                                        variant={displayMode === val ? 'default' : 'outline'}
                                        size="sm"
                                        disabled={!isHost}
                                        onClick={() => setMode(val)}
                                        className={displayMode === val
                                            ? 'bg-gradient-to-r from-orange-500 to-pink-600 hover:from-orange-600 hover:to-pink-700 text-white border-0 text-xs font-semibold'
                                            : 'bg-slate-800/50 border-slate-600 text-slate-300 hover:text-white hover:bg-slate-700/50 text-xs'}
                                    >
                                        {label}
                                    </Button>
                                ))}
                            </div>
                        </div>

                        {/* Overs */}
                        <div>
                            <label className="text-xs font-semibold mb-1.5 block text-slate-300 uppercase tracking-wide">Overs</label>
                            <div className="flex gap-2">
                                {overOptions.map(o => (
                                    <Button
                                        key={o}
                                        variant={displayOvers === o ? 'default' : 'outline'}
                                        size="sm"
                                        disabled={!isHost}
                                        onClick={() => setOvers(o)}
                                        className={displayOvers === o
                                            ? 'bg-gradient-to-r from-blue-500 to-cyan-600 hover:from-blue-600 hover:to-cyan-700 text-white border-0 font-semibold text-xs'
                                            : 'bg-slate-800/50 border-slate-600 text-slate-300 hover:text-white hover:bg-slate-700/50 text-xs'}
                                    >
                                        {o} overs
                                    </Button>
                                ))}
                            </div>
                        </div>

                        {/* Wickets */}
                        <div>
                            <label className="text-xs font-semibold mb-1.5 block text-slate-300 uppercase tracking-wide">Wickets</label>
                            <div className="flex gap-2">
                                {wicketRange.map(w => (
                                    <Button
                                        key={w}
                                        variant={displayWickets === w ? 'default' : 'outline'}
                                        size="sm"
                                        disabled={!isHost}
                                        onClick={() => setWickets(w)}
                                        className={displayWickets === w
                                            ? 'bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white border-0 font-semibold text-xs'
                                            : 'bg-slate-800/50 border-slate-600 text-slate-300 hover:text-white hover:bg-slate-700/50 text-xs'}
                                    >
                                        {w}
                                    </Button>
                                ))}
                            </div>
                        </div>

                        {/* Host Participation */}
                        {isHost && (
                            <div className="border-t border-slate-700/50 pt-3">
                                <label className="flex items-center gap-3 cursor-pointer hover:bg-slate-800/30 p-2 rounded-lg transition-colors">
                                    <input
                                        type="checkbox"
                                        checked={hostWantsToPlay}
                                        onChange={(e) => setHostWantsToPlay(e.target.checked)}
                                        className="w-4 h-4 rounded border-slate-600 bg-slate-900/50 text-orange-500 focus:ring-orange-500/20 cursor-pointer"
                                    />
                                    <div>
                                        <div className="text-sm font-medium text-white">I want to play</div>
                                        <div className="text-[10px] text-slate-400">Uncheck to spectate/manage only</div>
                                    </div>
                                </label>
                            </div>
                        )}

                        {isHost && !lobby.cpu_only && (
                            <div className="border-t border-slate-700/50 pt-3">
                                <div className="text-xs font-semibold mb-1.5 block text-slate-300 uppercase tracking-wide">CPU ({cpuCount})</div>
                                <div className="flex gap-2">
                                    <Button
                                        size="sm"
                                        disabled={displayMode === '1v1' && cpuCount >= 1}
                                        onClick={() => sendMsg({ action: 'ADD_CPU' })}
                                        className="bg-slate-800/50 border-slate-600 text-slate-300 hover:text-white hover:bg-slate-700/50 text-xs"
                                        variant="outline"
                                    >
                                        Add CPU
                                    </Button>
                                    <Button
                                        size="sm"
                                        disabled={cpuCount === 0}
                                        onClick={() => sendMsg({ action: 'REMOVE_CPU' })}
                                        className="bg-slate-800/50 border-slate-600 text-slate-300 hover:text-white hover:bg-slate-700/50 text-xs"
                                        variant="outline"
                                    >
                                        Remove CPU
                                    </Button>
                                </div>
                            </div>
                        )}

                        {isHost && (
                            <Button
                                onClick={applySettings}
                                className="w-full bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700 text-white text-sm font-semibold py-2"
                            >
                                 Apply Settings
                            </Button>
                        )}
                    </div>
                </div>

                {/* Column 3: Team Assignment — visible to all in team mode, interactive for host only */}
                {isTeamMode && (
                    isHost ? (
                        <DndContext
                            sensors={sensors}
                            collisionDetection={closestCenter}
                            onDragEnd={handleDragEnd}
                        >
                            <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5 shadow-2xl flex flex-col min-h-0">
                                <div className="flex items-center justify-between mb-3 flex-shrink-0">
                                    <h3 className="text-xl font-bold text-white flex items-center gap-2">
                                        <span className="text-2xl"></span> Teams
                                    </h3>
                                    <Button
                                        size="sm"
                                        onClick={() => sendMsg({ action: 'RESET_TEAMS' })}
                                        className="bg-red-500/20 hover:bg-red-500/40 text-red-300 hover:text-white border border-red-500/30 text-xs font-semibold"
                                    >
                                         Reset
                                    </Button>
                                </div>

                                <div className="flex flex-col gap-3 flex-1 min-h-0">
                                    {/* Unassigned Players — draggable */}
                                    <div className="bg-slate-900/50 rounded-xl p-3 border border-slate-700/50 flex-shrink-0">
                                        <div className="text-[10px] text-slate-400 mb-2 font-semibold uppercase tracking-wide">
                                            Available — drag to team or click →
                                        </div>
                                        {unassignedPlayers.length > 0 ? (
                                            <div className="space-y-1.5">
                                                {unassignedPlayers.map(p => (
                                                    <DraggablePlayer
                                                        key={p.username}
                                                        player={p}
                                                        sendMsg={sendMsg}
                                                    />
                                                ))}
                                            </div>
                                        ) : (
                                            <div className="text-xs text-green-400 text-center py-1.5 font-semibold"> All assigned!</div>
                                        )}
                                    </div>

                                    {/* Drop Zones — side by side */}
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 flex-1 min-h-0">
                                        <TeamDropZone team="A" lobby={lobby} sendMsg={sendMsg} isHost={true} />
                                        <TeamDropZone team="B" lobby={lobby} sendMsg={sendMsg} isHost={true} />
                                    </div>
                                </div>

                                {/* Captain validation warning */}
                                {hasFullTeams && !hasBothCaptains && (
                                    <div className="mt-2 flex-shrink-0 text-center text-[11px] text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg py-2 px-3 font-medium">
                                        ️ Select a captain for each team to start
                                    </div>
                                )}
                            </div>
                        </DndContext>
                    ) : (
                        /* Read-only Teams view for non-host players */
                        <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5 shadow-2xl flex flex-col min-h-0">
                            <div className="flex items-center justify-between mb-3 flex-shrink-0">
                                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                                    <span className="text-2xl"></span> Teams
                                </h3>
                                <Badge className="bg-slate-700/50 text-slate-400 border-slate-600 text-[10px]">Host assigns</Badge>
                            </div>

                            <div className="flex flex-col gap-3 flex-1 min-h-0">
                                {/* Unassigned Players — read-only */}
                                {unassignedPlayers.length > 0 && (
                                    <div className="bg-slate-900/50 rounded-xl p-3 border border-slate-700/50 flex-shrink-0">
                                        <div className="text-[10px] text-slate-400 mb-2 font-semibold uppercase tracking-wide">
                                            Waiting to be assigned
                                        </div>
                                        <div className="space-y-1.5">
                                            {unassignedPlayers.map(p => (
                                                <div key={p.username} className="flex items-center gap-2 p-2 rounded-lg bg-slate-800/40 border border-slate-700/30">
                                                    <span className="text-xs text-white font-medium">{p.username}</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* Team Zones — read-only */}
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 flex-1 min-h-0">
                                    <TeamDropZone team="A" lobby={lobby} sendMsg={sendMsg} isHost={false} />
                                    <TeamDropZone team="B" lobby={lobby} sendMsg={sendMsg} isHost={false} />
                                </div>
                            </div>
                        </div>
                    )
                )}
            </div>

            {/* Bottom Action Bar */}
            <div className="flex-shrink-0 text-center">
                {isHost ? (
                    <div className="flex flex-col sm:flex-row gap-4 justify-center">
                        {mode !== 'tournament' && (
                            <Button
                                size="lg"
                                disabled={isTeamMode && (!hasFullTeams || !hasBothCaptains)}
                                className="px-12 py-5 text-lg bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white shadow-lg hover:shadow-green-500/50 transition-all font-bold disabled:opacity-40 disabled:cursor-not-allowed"
                                onClick={() => {
                                    applySettings()
                                    sendMsg({ action: 'START_MATCH' })
                                }}
                            >
                                 Start Match
                            </Button>
                        )}
                        {mode === 'tournament' && (
                            <Button
                                size="lg"
                                className="px-12 py-5 text-lg bg-gradient-to-r from-yellow-500 to-orange-600 hover:from-yellow-600 hover:to-orange-700 text-white shadow-lg hover:shadow-yellow-500/50 transition-all font-bold"
                                onClick={() => {
                                    applySettings()
                                    sendMsg({ action: 'START_TOURNAMENT' })
                                }}
                            >
                                 Start Tournament
                            </Button>
                        )}
                    </div>
                ) : (
                    <p className="text-slate-400 text-sm bg-slate-800/30 inline-block px-6 py-3 rounded-xl border border-slate-700/50 font-medium">
                        ⏳ Waiting for host to start the match...
                    </p>
                )}
            </div>
        </div>
    )
}

/** Draggable player chip with click-to-assign fallback buttons */
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
            className={`flex items-center justify-between p-2.5 rounded-lg border transition-all ${isDragging
                ? 'bg-orange-500/20 border-orange-500/50 shadow-xl shadow-orange-500/20 scale-105'
                : 'bg-slate-800/40 border-slate-700/30 hover:border-slate-500/50 hover:bg-slate-700/40'
                }`}
        >
            {/* Drag handle area */}
            <div
                {...attributes}
                {...listeners}
                className="flex items-center gap-2 cursor-grab active:cursor-grabbing flex-1 min-w-0"
            >
                <span className="text-slate-500 text-xs select-none">⠿</span>
                <span className="text-xs text-white font-semibold truncate">{player.username}</span>
            </div>
            {/* Click-to-assign buttons */}
            <div className="flex gap-1 flex-shrink-0 ml-2">
                <button
                    onClick={(e) => { e.stopPropagation(); sendMsg({ action: 'ASSIGN_TEAM', player: player.username, team: 'A' }) }}
                    className="h-5 px-1.5 text-[9px] font-bold rounded bg-blue-500/30 hover:bg-blue-500/60 text-blue-200 border border-blue-500/40 transition-colors"
                >
                    A
                </button>
                <button
                    onClick={(e) => { e.stopPropagation(); sendMsg({ action: 'ASSIGN_TEAM', player: player.username, team: 'B' }) }}
                    className="h-5 px-1.5 text-[9px] font-bold rounded bg-purple-500/30 hover:bg-purple-500/60 text-purple-200 border border-purple-500/40 transition-colors"
                >
                    B
                </button>
            </div>
        </div>
    )
}

/** Droppable team zone with captain selector */
function TeamDropZone({ team, lobby, sendMsg, isHost }: {
    team: 'A' | 'B'
    lobby: LobbyData
    sendMsg: (msg: Record<string, unknown>) => void
    isHost: boolean
}) {
    const { setNodeRef, isOver } = useDroppable({ id: team })

    const teamPlayers = lobby.teams[team] || []
    const captain = lobby.captains[team]

    const isA = team === 'A'
    const borderColor = isOver
        ? (isA ? 'border-blue-400 shadow-blue-500/20 shadow-lg' : 'border-purple-400 shadow-purple-500/20 shadow-lg')
        : (isA ? 'border-blue-500/30' : 'border-purple-500/30')
    const gradient = isA ? 'from-blue-500/10 to-cyan-500/10' : 'from-purple-500/10 to-pink-500/10'
    const titleColor = isA ? 'text-blue-300' : 'text-purple-300'
    const captainBtnColor = isA
        ? 'bg-blue-500/30 hover:bg-blue-500/60 text-blue-200 border-blue-500/40'
        : 'bg-purple-500/30 hover:bg-purple-500/60 text-purple-200 border-purple-500/40'

    return (
        <div
            ref={setNodeRef}
            className={`rounded-xl border-2 border-dashed transition-all bg-gradient-to-br ${gradient} ${borderColor} p-3 flex flex-col min-h-[100px]`}
        >
            <div className={`font-bold text-sm mb-2 ${titleColor} flex items-center justify-between flex-shrink-0`}>
                <span>{lobby.team_names[team]}</span>
                {captain && (
                    <Badge className="bg-yellow-500/20 text-yellow-300 border-yellow-500/30 text-[9px] px-1">
                         {captain}
                    </Badge>
                )}
            </div>
            <div className="space-y-1.5 flex-1">
                {teamPlayers.length > 0 ? (
                    teamPlayers.map(playerName => (
                        <div key={playerName} className="flex items-center justify-between bg-slate-800/50 p-2 rounded-lg border border-slate-700/30">
                            <div className="flex items-center gap-1.5">
                                <span className="text-xs text-white font-medium">{playerName}</span>
                                {captain === playerName && <span className="text-yellow-400 text-xs"></span>}
                            </div>
                            {isHost && captain !== playerName && (
                                <button
                                    onClick={() => sendMsg({ action: 'SET_CAPTAIN', team, captain: playerName })}
                                    className={`h-5 px-1.5 text-[9px] font-bold rounded border transition-colors ${captainBtnColor}`}
                                >
                                    
                                </button>
                            )}
                        </div>
                    ))
                ) : (
                    <div className={`text-[10px] text-center py-4 font-medium ${isOver && isHost ? 'text-white' : 'text-slate-500'}`}>
                        {isHost ? (isOver ? ' Drop here!' : 'Drag players here') : 'Waiting for host'}
                    </div>
                )}
            </div>
        </div>
    )
}
