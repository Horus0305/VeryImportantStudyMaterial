async def send_match_state(manager, room) -> None:
    match = room.match
    if not match:
        return
    innings = match.active_innings
    if not innings:
        return

    pending = room.pending_moves

    # Determine which team is batting/bowling to find captains
    batting_team = None
    bowling_team = None
    for team_key, members in room.teams.items():
        if innings.batting_side and innings.batting_side[0] in members:
            batting_team = team_key
        elif innings.bowling_side and innings.bowling_side[0] in members:
            bowling_team = team_key
    batting_captain = room.captains.get(batting_team) if batting_team else None
    bowling_captain = room.captains.get(bowling_team) if bowling_team else None

    base_state = {
        "type": "MATCH_STATE",
        "mode": match.mode,
        "innings": match.current_innings,
        "batting_side": innings.batting_side,
        "bowling_side": innings.bowling_side,
        "striker": innings.striker,
        "non_striker": innings.non_striker,
        "bowler": innings.current_bowler,
        "total_runs": innings.total_runs,
        "wickets": innings.wickets_fallen,
        "overs": innings.overs_display,
        "total_overs": innings.total_overs,
        "target": innings.target,
        "batting_card": [innings.batting_cards[n].to_dict() for n in innings.batting_side],
        "bowling_card": [innings.bowling_cards[n].to_dict() for n in innings.bowling_side],
        "bat_ready": "bat" in pending,
        "bowl_ready": "bowl" in pending,
        # Captain selection state
        "needs_batter_choice": innings.needs_batter_choice,
        "needs_bowler_choice": innings.needs_bowler_choice,
        "available_batters": innings.available_next_batters() if innings.needs_batter_choice else [],
        "available_bowlers": innings.available_next_bowlers() if innings.needs_bowler_choice else [],
        "batting_captain": batting_captain,
        "bowling_captain": bowling_captain,
    }
    if room.tournament and match.mode == "tournament":
        base_state["tournament"] = manager._build_tournament_payload(room.tournament, skip_current=True)



    for username, p in room.players.items():
        state = dict(base_state)
        if innings.needs_batter_choice or innings.needs_bowler_choice:
            # During captain selection, active role is "captain" — not regular batting/bowling
            if innings.needs_batter_choice and username == batting_captain:
                state["my_role"] = "BATTING_CAPTAIN_PICK"
            elif innings.needs_bowler_choice and username == bowling_captain:
                state["my_role"] = "BOWLING_CAPTAIN_PICK"
            else:
                state["my_role"] = "WAITING"
        elif username == innings.striker:
            state["my_role"] = "BATTING"
        elif username == innings.current_bowler:
            state["my_role"] = "BOWLING"
        elif username in innings.batting_side:
            state["my_role"] = "NON_STRIKER"
        elif username in innings.bowling_side:
            state["my_role"] = "FIELDING"
        else:
            state["my_role"] = "SPECTATING"
        await manager.send(p, state)

