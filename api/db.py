"""
SQLite helper — schema, connection, read/write utilities.
The DB file lives at api/nba.db and is committed to the repo.
Run scripts/fetch_and_seed.py locally to populate/refresh it.
"""
import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "nba.db")


def db_exists() -> bool:
    return os.path.exists(DB_PATH)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


_SCHEMA = """
CREATE TABLE IF NOT EXISTS teams (
    espn_id      TEXT PRIMARY KEY,
    abbreviation TEXT NOT NULL,
    display_name TEXT NOT NULL,
    location     TEXT NOT NULL,
    nickname     TEXT NOT NULL,
    logo_url     TEXT NOT NULL,
    wins         INTEGER DEFAULT 0,
    losses       INTEGER DEFAULT 0,
    updated_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS players (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name        TEXT NOT NULL,
    norm_name        TEXT NOT NULL,
    team_abbr        TEXT NOT NULL,
    pos              TEXT DEFAULT '',
    age              REAL DEFAULT 0,
    games_played     INTEGER DEFAULT 0,
    minutes          REAL DEFAULT 0,
    points           REAL DEFAULT 0,
    rebounds         REAL DEFAULT 0,
    assists          REAL DEFAULT 0,
    steals           REAL DEFAULT 0,
    blocks           REAL DEFAULT 0,
    fga              REAL DEFAULT 0,
    fta              REAL DEFAULT 0,
    field_goal_pct   REAL DEFAULT 0,
    three_point_pct  REAL DEFAULT 0,
    free_throw_pct   REAL DEFAULT 0,
    tov_per_g        REAL DEFAULT 0,
    salary           REAL DEFAULT 0,
    salary_year2     REAL DEFAULT 0,
    salary_year3     REAL DEFAULT 0,
    salary_year4     REAL DEFAULT 0,
    per              REAL DEFAULT 0,
    usg_pct          REAL DEFAULT 0,
    ws               REAL DEFAULT 0,
    ws_per_48        REAL DEFAULT 0,
    bpm              REAL DEFAULT 0,
    obpm             REAL DEFAULT 0,
    dbpm             REAL DEFAULT 0,
    vorp             REAL DEFAULT 0,
    ows              REAL DEFAULT 0,
    dws              REAL DEFAULT 0,
    updated_at       TEXT DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_players_norm_team
    ON players (norm_name, team_abbr);
"""


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(_SCHEMA)


# ── Read ──────────────────────────────────────────────────────────────────────

def load_teams() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM teams").fetchall()
    return [dict(r) for r in rows]


def load_players() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM players").fetchall()
    return [dict(r) for r in rows]


def get_player_by_id(player_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone()
    return dict(row) if row else None


# ── Write ─────────────────────────────────────────────────────────────────────

def upsert_teams(teams: list[dict]) -> None:
    sql = """
        INSERT INTO teams (espn_id, abbreviation, display_name, location, nickname,
                           logo_url, wins, losses, updated_at)
        VALUES (:espn_id, :abbreviation, :display_name, :location, :nickname,
                :logo_url, :wins, :losses, :updated_at)
        ON CONFLICT(espn_id) DO UPDATE SET
            wins       = excluded.wins,
            losses     = excluded.losses,
            updated_at = excluded.updated_at
    """
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.executemany(sql, [{**t, "updated_at": now} for t in teams])


def upsert_players(players: list[dict]) -> None:
    sql = """
        INSERT INTO players (
            full_name, norm_name, team_abbr, pos, age, games_played, minutes,
            points, rebounds, assists, steals, blocks, fga, fta,
            field_goal_pct, three_point_pct, free_throw_pct, tov_per_g,
            salary, salary_year2, salary_year3, salary_year4,
            per, usg_pct, ws, ws_per_48, bpm, obpm, dbpm, vorp, ows, dws,
            updated_at
        ) VALUES (
            :full_name, :norm_name, :team_abbr, :pos, :age, :games_played, :minutes,
            :points, :rebounds, :assists, :steals, :blocks, :fga, :fta,
            :field_goal_pct, :three_point_pct, :free_throw_pct, :tov_per_g,
            :salary, :salary_year2, :salary_year3, :salary_year4,
            :per, :usg_pct, :ws, :ws_per_48, :bpm, :obpm, :dbpm, :vorp, :ows, :dws,
            :updated_at
        )
        ON CONFLICT(norm_name, team_abbr) DO UPDATE SET
            full_name       = excluded.full_name,
            pos             = excluded.pos,
            age             = excluded.age,
            games_played    = excluded.games_played,
            minutes         = excluded.minutes,
            points          = excluded.points,
            rebounds        = excluded.rebounds,
            assists         = excluded.assists,
            steals          = excluded.steals,
            blocks          = excluded.blocks,
            fga             = excluded.fga,
            fta             = excluded.fta,
            field_goal_pct  = excluded.field_goal_pct,
            three_point_pct = excluded.three_point_pct,
            free_throw_pct  = excluded.free_throw_pct,
            tov_per_g       = excluded.tov_per_g,
            salary          = excluded.salary,
            salary_year2    = excluded.salary_year2,
            salary_year3    = excluded.salary_year3,
            salary_year4    = excluded.salary_year4,
            per             = excluded.per,
            usg_pct         = excluded.usg_pct,
            ws              = excluded.ws,
            ws_per_48       = excluded.ws_per_48,
            bpm             = excluded.bpm,
            obpm            = excluded.obpm,
            dbpm            = excluded.dbpm,
            vorp            = excluded.vorp,
            ows             = excluded.ows,
            dws             = excluded.dws,
            updated_at      = excluded.updated_at
    """
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.executemany(sql, [{**p, "updated_at": now} for p in players])


def update_player_salary(player_id: int, salary: float,
                         salary_year2: float = None,
                         salary_year3: float = None,
                         salary_year4: float = None) -> bool:
    """Update only the salary fields for a player. Returns True if row existed."""
    parts = ["salary = :salary", "updated_at = :updated_at"]
    params: dict = {"id": player_id, "salary": salary,
                    "updated_at": datetime.utcnow().isoformat()}
    if salary_year2 is not None:
        parts.append("salary_year2 = :salary_year2")
        params["salary_year2"] = salary_year2
    if salary_year3 is not None:
        parts.append("salary_year3 = :salary_year3")
        params["salary_year3"] = salary_year3
    if salary_year4 is not None:
        parts.append("salary_year4 = :salary_year4")
        params["salary_year4"] = salary_year4
    sql = f"UPDATE players SET {', '.join(parts)} WHERE id = :id"
    with get_conn() as conn:
        cur = conn.execute(sql, params)
        return cur.rowcount > 0


def delete_player(player_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM players WHERE id = ?", (player_id,))
        return cur.rowcount > 0


def insert_player(player: dict) -> int:
    """Insert a brand-new player row. Returns the new row id."""
    now = datetime.utcnow().isoformat()
    keys = [
        "full_name", "norm_name", "team_abbr", "pos", "age", "games_played",
        "minutes", "points", "rebounds", "assists", "steals", "blocks", "fga",
        "fta", "field_goal_pct", "three_point_pct", "free_throw_pct", "tov_per_g",
        "salary", "salary_year2", "salary_year3", "salary_year4",
        "per", "usg_pct", "ws", "ws_per_48", "bpm", "obpm", "dbpm", "vorp", "ows", "dws",
    ]
    cols = ", ".join(keys) + ", updated_at"
    vals = ", ".join(f":{k}" for k in keys) + ", :updated_at"
    row = {k: player.get(k, 0) for k in keys}
    row["full_name"] = player["full_name"]
    row["norm_name"] = player.get("norm_name", player["full_name"].lower().strip())
    row["team_abbr"] = player["team_abbr"]
    row["updated_at"] = now
    with get_conn() as conn:
        cur = conn.execute(f"INSERT INTO players ({cols}) VALUES ({vals})", row)
        return cur.lastrowid
