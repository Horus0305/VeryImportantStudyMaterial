import sqlite3
import json

conn = sqlite3.connect('cricket.db')
c = conn.cursor()

main_humans = {'AniketKS', 'Atharva', 'Sahil', 'Yash', 'Meet', 'Atharva Kolekar', 'hetvig04'}

# 1. Get all tournaments
c.execute('select tournament_id, players, champion from tournament_history')
tournaments = c.fetchall()

to_delete_tids = []
for tid, p_json, champ in tournaments:
    players = json.loads(p_json)
    intersect = set(players) & main_humans
    if len(intersect) < 2:
        to_delete_tids.append(tid)

print(f"Tournaments to delete: {len(to_delete_tids)}")

# 2. Deletes
if to_delete_tids:
    # Delete tournaments
    c.executemany('delete from tournament_history where tournament_id = ?', [(tid,) for tid in to_delete_tids])
    print(f"Deleted {len(to_delete_tids)} tournaments from tournament_history.")

    # Delete corresponding matches
    placeholders = ','.join('?' for _ in to_delete_tids)
    c.execute(f'delete from match_history where mode="tournament" and tournament_id in ({placeholders})', to_delete_tids)
    print("Deleted corresponding matches from match_history.")
else:
    print("No tournaments to delete.")

# 3. Recalculate format_stats for 'tournament' format
# We need to fetch all players
c.execute('select id, username from players')
all_players = c.fetchall()

for player_id, username in all_players:
    # Get all remaining tournament matches for this player
    c.execute('''
        select winner, scorecard_1, scorecard_2 from match_history
        where mode = "tournament"
        and (exists (select 1 from json_each(side_a) where value = ?)
             or exists (select 1 from json_each(side_b) where value = ?))
    ''', (username, username))
    player_matches = c.fetchall()

    matches_played = len(player_matches)
    matches_won = 0
    total_runs = 0
    total_balls_faced = 0
    highest_score = 0
    fours = 0
    sixes = 0
    fifties = 0
    hundreds = 0
    innings_batted = 0
    wickets_taken = 0
    best_bowling_wickets = 0
    best_bowling_runs = 999
    runs_conceded = 0
    overs_bowled = 0.0
    innings_bowled = 0

    for winner, sc_1_raw, sc_2_raw in player_matches:
        # Check if won
        if winner and winner != "TIE":
            winners = [w.strip() for w in winner.split(',') if w.strip()]
            if username in winners:
                matches_won += 1

        # Check scorecard 1 and 2
        for sc_idx, sc_raw in enumerate((sc_1_raw, sc_2_raw)):
            if not sc_raw:
                continue
            try:
                sc = json.loads(sc_raw) if isinstance(sc_raw, str) else sc_raw
            except Exception:
                continue

            # Batting
            batting_cards = sc.get("batting_card", [])
            for bc in batting_cards:
                if bc.get("name") == username:
                    runs = bc.get("runs", 0)
                    balls = bc.get("balls", 0)
                    total_runs += runs
                    total_balls_faced += balls
                    fours += bc.get("fours", 0)
                    sixes += bc.get("sixes", 0)
                    innings_batted += 1
                    if runs > highest_score:
                        highest_score = runs
                    if runs >= 100:
                        hundreds += 1
                    elif runs >= 50:
                        fifties += 1

            # Bowling
            bowling_cards = sc.get("bowling_card", [])
            for bc in bowling_cards:
                if bc.get("name") == username:
                    wkts = bc.get("wickets", 0)
                    runs_c = bc.get("runs_conceded", 0)
                    wickets_taken += wkts
                    runs_conceded += runs_c
                    overs_bowled += bc.get("overs", 0)
                    innings_bowled += 1
                    if wkts > best_bowling_wickets or (wkts == best_bowling_wickets and runs_c < best_bowling_runs):
                        best_bowling_wickets = wkts
                        best_bowling_runs = runs_c

    # Tournaments won/played
    c.execute('select count(*) from tournament_history where champion = ?', (username,))
    tournaments_won = c.fetchone()[0]

    c.execute('select count(*) from tournament_history where exists (select 1 from json_each(players) where value = ?)', (username,))
    tournaments_played = c.fetchone()[0]

    # Check if a row exists in format_stats, otherwise insert, else update
    c.execute('select id from format_stats where player_id = ? and format = "tournament"', (player_id,))
    row = c.fetchone()
    if row:
        c.execute('''
            update format_stats set
                matches_played = ?, matches_won = ?, total_runs = ?, total_balls_faced = ?,
                highest_score = ?, fours = ?, sixes = ?, fifties = ?, hundreds = ?,
                innings_batted = ?, wickets_taken = ?, best_bowling_wickets = ?, best_bowling_runs = ?,
                runs_conceded = ?, overs_bowled = ?, innings_bowled = ?,
                tournaments_played = ?, tournaments_won = ?
            where id = ?
        ''', (
            matches_played, matches_won, total_runs, total_balls_faced,
            highest_score, fours, sixes, fifties, hundreds,
            innings_batted, wickets_taken, best_bowling_wickets, best_bowling_runs,
            runs_conceded, overs_bowled, innings_bowled,
            tournaments_played, tournaments_won, row[0]
        ))
    else:
        c.execute('''
            insert into format_stats (
                player_id, format, matches_played, matches_won, total_runs, total_balls_faced,
                highest_score, fours, sixes, fifties, hundreds, innings_batted,
                wickets_taken, best_bowling_wickets, best_bowling_runs, runs_conceded,
                overs_bowled, innings_bowled, tournaments_played, tournaments_won,
                potm_count, player_of_tournament_count
            ) values (?, "tournament", ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
        ''', (
            player_id, matches_played, matches_won, total_runs, total_balls_faced,
            highest_score, fours, sixes, fifties, hundreds, innings_batted,
            wickets_taken, best_bowling_wickets, best_bowling_runs, runs_conceded,
            overs_bowled, innings_bowled, tournaments_played, tournaments_won
        ))

conn.commit()
print("Recalculated and updated format_stats table successfully.")
conn.close()
