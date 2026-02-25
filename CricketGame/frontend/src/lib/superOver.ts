export interface SuperOverScorecard {
    total_runs: number
    wickets: number
    overs: string
}

export interface SuperOverRound {
    round: number
    scorecard_3: SuperOverScorecard
    scorecard_4: SuperOverScorecard
    bat_team_3: string[]
    bat_team_4: string[]
    is_tied_round: boolean
    round_winner: string | null
}

function asRecord(value: unknown): Record<string, unknown> | null {
    return value && typeof value === 'object' ? (value as Record<string, unknown>) : null
}

function toStringArray(value: unknown): string[] {
    if (!Array.isArray(value)) return []
    return value.filter((entry): entry is string => typeof entry === 'string' && entry.trim().length > 0)
}

function toScorecard(value: unknown): SuperOverScorecard | null {
    const record = asRecord(value)
    if (!record) return null

    const runs = Number(record.total_runs)
    const wickets = Number(record.wickets)
    const overs = record.overs

    if (!Number.isFinite(runs) || !Number.isFinite(wickets) || (typeof overs !== 'string' && typeof overs !== 'number')) {
        return null
    }

    return {
        total_runs: runs,
        wickets,
        overs: String(overs),
    }
}

function normalizeRound(raw: unknown, fallbackRoundNo: number): SuperOverRound | null {
    const record = asRecord(raw)
    if (!record) return null

    const scorecard3 = toScorecard(record.scorecard_3)
    const scorecard4 = toScorecard(record.scorecard_4)
    if (!scorecard3 || !scorecard4) return null

    const round = Number(record.round)
    const roundNo = Number.isFinite(round) && round > 0 ? Math.floor(round) : fallbackRoundNo
    const batTeam3 = toStringArray(record.bat_team_3)
    const batTeam4 = toStringArray(record.bat_team_4)

    const isTiedRound = typeof record.is_tied_round === 'boolean'
        ? record.is_tied_round
        : scorecard3.total_runs === scorecard4.total_runs

    let roundWinner: string | null = null
    if (typeof record.round_winner === 'string' && record.round_winner.trim().length > 0) {
        roundWinner = record.round_winner
    } else if (!isTiedRound) {
        roundWinner = scorecard4.total_runs > scorecard3.total_runs
            ? (batTeam4.length ? batTeam4.join(', ') : 'Team 2')
            : (batTeam3.length ? batTeam3.join(', ') : 'Team 1')
    }

    return {
        round: roundNo,
        scorecard_3: scorecard3,
        scorecard_4: scorecard4,
        bat_team_3: batTeam3,
        bat_team_4: batTeam4,
        is_tied_round: isTiedRound,
        round_winner: roundWinner,
    }
}

function parseTimeline(value: unknown): SuperOverRound[] {
    const raw = typeof value === 'string' ? (() => {
        try {
            return JSON.parse(value)
        } catch {
            return null
        }
    })() : value

    if (!Array.isArray(raw)) return []

    const rounds = raw
        .map((entry, idx) => normalizeRound(entry, idx + 1))
        .filter((entry): entry is SuperOverRound => Boolean(entry))
    rounds.sort((a, b) => a.round - b.round)
    return rounds
}

interface ResolveTimelineInput {
    super_over_timeline?: unknown
    potm_payload?: unknown
    scorecard_3?: unknown
    scorecard_4?: unknown
    bat_team_3?: unknown
    bat_team_4?: unknown
}

export function resolveSuperOverTimeline(input: ResolveTimelineInput): SuperOverRound[] {
    const timeline = parseTimeline(input.super_over_timeline)
    if (timeline.length > 0) return timeline

    const potmPayload = asRecord(input.potm_payload)
    const legacyFromPotm = asRecord(potmPayload?.super_over_data)
    const legacyRound = normalizeRound(
        {
            round: 1,
            scorecard_3: legacyFromPotm?.scorecard_3 ?? input.scorecard_3,
            scorecard_4: legacyFromPotm?.scorecard_4 ?? input.scorecard_4,
            bat_team_3: legacyFromPotm?.bat_team_3 ?? input.bat_team_3,
            bat_team_4: legacyFromPotm?.bat_team_4 ?? input.bat_team_4,
        },
        1,
    )

    return legacyRound ? [legacyRound] : []
}
