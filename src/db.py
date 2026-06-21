import sqlite3
import time


def get_connection(db_path: str):
    return sqlite3.connect(db_path)


def init_db(conn: sqlite3.Connection):
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
        puuid TEXT NOT NULL PRIMARY KEY,
        game_name TEXT NOT NULL,
        tagline TEXT NOT NULL,
        league_points INTEGER NOT NULL,
        rank TEXT NOT NULL,
        wins INTEGER NOT NULL,
        losses INTEGER NOT NULL,
        tier TEXT NOT NULL,
        queue TEXT NOT NULL,
        in_top BOOLEAN NOT NULL,
        last_updated_at INTEGER NOT NULL,
        last_match_check_at INTEGER
   );
   """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ladder_history (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        player_puuid TEXT NOT NULL,
        league_points INTEGER NOT NULL,
        rank_position INTEGER NOT NULL,
        wins INTEGER NOT NULL,
        losses INTEGER NOT NULL,
        snapshot_at INTEGER NOT NULL,
        FOREIGN KEY (player_puuid) REFERENCES players (puuid)
    );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matches (
        id TEXT NOT NULL PRIMARY KEY,
        game_version INTEGER NOT NULL,
        duration INTEGER NOT NULL,
        team_win INTEGER NOT NULL,
        created_at INTEGER NOT NULL,
        started_at INTEGER NOT NULL,
        ended_at INTEGER NOT NULL
    );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players_matches (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        player_puuid TEXT NOT NULL,
        match_id TEXT NOT NULL,
        kills INTEGER NOT NULL,
        assists INTEGER NOT NULL,
        deaths INTEGER NOT NULL,
        champion_name VARCHAR(150) NOT NULL,
        champion_level INTEGER NOT NULL,
        champion_exp INTEGER NOT NULL,
        gold_earned INTEGER NOT NULL,
        gold_spent INTEGER NOT NULL,
        position TEXT NOT NULL,
        team_id INTEGER NOT NULL,
        total_damage_dealt_to_champions INTEGER NOT NULL,
        total_minions_killed INTEGER NOT NULL,
        game_surrendered BOOLEAN NOT NULL,
        game_early_surrender BOOLEAN NOT NULL,
        vision_score INTEGER NOT NULL,
        win BOOLEAN NOT NULL,
        
        FOREIGN KEY (player_puuid) REFERENCES players (puuid),
        FOREIGN KEY (match_id) REFERENCES matches (id)
    );
    """)


def upsert_player(conn: sqlite3.Connection, players_data_list: list[tuple]):
    cursor = conn.cursor()
    now = time.time()
    cursor.executemany(
        """
       INSERT INTO players(puuid, game_name, tagline, league_points, rank, wins, losses,
                           tier, queue, in_top, last_updated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
       ON CONFLICT(puuid) DO UPDATE SET
        league_points = excluded.league_points,
        rank = excluded.rank,
        wins = excluded.wins,
        losses = excluded.losses,
        tier = excluded.tier,
        in_top = excluded.in_top,
        last_updated_at = excluded.last_updated_at
    """,
        [(*p, now) for p in players_data_list],
    )


def ensure_player_exists(conn: sqlite3.Connection, player_data):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO players (puuid, game_name, tagline, league_points, rank, wins, losses,
                             tier, queue, in_top, last_updated_at)
        VALUES (?, ?, ?, 0, '-', 0, 0, 'UNRANKED', 'RANKED_SOLO_5x5', FALSE, ?)
        ON CONFLICT(puuid) DO NOTHING
    """,
        (player_data[0], player_data[1], player_data[2], time.time()),
    )


def match_exists(conn: sqlite3.Connection, match_id: str):
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM matches WHERE id = ?", (match_id,))
    return cursor.fetchone() is not None


def insert_match(conn: sqlite3.Connection, match_data: tuple):
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO matches(id, game_version, duration, team_win, created_at, started_at, ended_at) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        match_data,
    )


def insert_players_matches(conn: sqlite3.Connection, participants_data_list: list[tuple]):
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT INTO players_matches(player_puuid, match_id, kills, assists, deaths, champion_name, 
                                    champion_level, champion_exp, gold_earned, gold_spent, position,
                                    team_id, total_damage_dealt_to_champions, 
                                    total_minions_killed, game_surrendered,
                                    game_early_surrender, vision_score, win)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        participants_data_list,
    )


def log_ladder_snapshot(conn: sqlite3.Connection, players_data_list: list[tuple]):
    cursor = conn.cursor()
    now = time.time()
    cursor.executemany(
        """
        INSERT INTO ladder_history (player_puuid, league_points, wins, losses,
                                    rank_position, snapshot_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        [(*p, now) for p in players_data_list],
    )


def deactivate_players(conn, puuids: list[str]):
    cursor = conn.cursor()
    cursor.executemany("UPDATE players SET in_top = FALSE WHERE puuid = ?", [(p,) for p in puuids])


def find_active_players(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("SELECT puuid FROM players WHERE in_top = TRUE")
    return {row[0] for row in cursor.fetchall()}


def get_last_match_check(conn, puuid: str):
    cursor = conn.cursor()
    cursor.execute("SELECT last_match_check_at FROM players WHERE puuid = ?", (puuid,))
    row = cursor.fetchone()
    return row[0] if row else None


def update_last_match_check(conn, puuid: str):
    cursor = conn.cursor()
    timestamp = time.time()
    cursor.execute("UPDATE players SET last_match_check_at = ? WHERE puuid = ?", (timestamp, puuid))
