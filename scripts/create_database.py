import sqlite3
from pathlib import Path


# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_FILE = DATA_DIR / "football.db"

DATA_DIR.mkdir(exist_ok=True)


connection = sqlite3.connect(DB_FILE)
cursor = connection.cursor()


# Enable foreign-key enforcement
cursor.execute("PRAGMA foreign_keys = ON")


# ---------------------------------------------------------
# Countries
# ---------------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS countries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    code TEXT NOT NULL UNIQUE,
    timezone TEXT NOT NULL
)
""")


# ---------------------------------------------------------
# Competitions
# ---------------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS competitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_id INTEGER,
    name TEXT NOT NULL,
    short_name TEXT,
    type TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'domestic',

    FOREIGN KEY (country_id)
        REFERENCES countries(id),

    UNIQUE(country_id, name)
)
""")


# ---------------------------------------------------------
# Seasons
# ---------------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS seasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competition_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,

    FOREIGN KEY (competition_id)
        REFERENCES competitions(id),

    UNIQUE(competition_id, name)
)
""")


# ---------------------------------------------------------
# Teams
# ---------------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_id INTEGER,
    name TEXT NOT NULL,
    short_name TEXT,
    slug TEXT NOT NULL UNIQUE,
    logo TEXT,

    FOREIGN KEY (country_id)
        REFERENCES countries(id)
)
""")


# ---------------------------------------------------------
# Teams participating in competitions/seasons
# ---------------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS competition_teams (
    competition_id INTEGER NOT NULL,
    season_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,

    PRIMARY KEY (
        competition_id,
        season_id,
        team_id
    ),

    FOREIGN KEY (competition_id)
        REFERENCES competitions(id),

    FOREIGN KEY (season_id)
        REFERENCES seasons(id),

    FOREIGN KEY (team_id)
        REFERENCES teams(id)
)
""")


# ---------------------------------------------------------
# Fixtures
# ---------------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS fixtures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    season_id INTEGER NOT NULL,

    home_team_id INTEGER NOT NULL,
    away_team_id INTEGER NOT NULL,

    kickoff TEXT,
    status TEXT NOT NULL DEFAULT 'scheduled',

    venue TEXT,
    round TEXT,

    FOREIGN KEY (season_id)
        REFERENCES seasons(id),

    FOREIGN KEY (home_team_id)
        REFERENCES teams(id),

    FOREIGN KEY (away_team_id)
        REFERENCES teams(id),

    CHECK (home_team_id != away_team_id)
)
""")


# ---------------------------------------------------------
# Sources
# ---------------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    url TEXT
)
""")


# ---------------------------------------------------------
# Fixture sources
# ---------------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS fixture_sources (
    fixture_id INTEGER NOT NULL,
    source_id INTEGER NOT NULL,

    source_fixture_id TEXT,

    source_date TEXT,
    source_kickoff TEXT,

    last_checked TEXT,

    PRIMARY KEY (
        fixture_id,
        source_id
    ),

    FOREIGN KEY (fixture_id)
        REFERENCES fixtures(id)
        ON DELETE CASCADE,

    FOREIGN KEY (source_id)
        REFERENCES sources(id)
)
""")


connection.commit()
connection.close()


print(f"Database created successfully:")
print(DB_FILE)
