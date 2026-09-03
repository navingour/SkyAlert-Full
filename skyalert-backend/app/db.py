"""Unified database layer. SQLite by default; PostgreSQL via DATABASE_URL."""
import os
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("skyalert.db")

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE = BASE_DIR / "data" / "skyalert_relational.db"

IST_TZ = timezone(timedelta(hours=5, minutes=30))


def _is_pg_url(url: str) -> bool:
    return bool(url) and ("postgres" in url or "postgresql" in url)


class Database:
    def __init__(self):
        self.pg_url = os.environ.get("DATABASE_URL", "").strip()
        self.is_pg = _is_pg_url(self.pg_url)
        self.sqlite_path = os.environ.get("SKYALERT_DB", str(DEFAULT_SQLITE))
        Path(self.sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def connect(self):
        if self.is_pg:
            import psycopg2
            import psycopg2.extras
            return psycopg2.connect(self.pg_url, cursor_factory=psycopg2.extras.RealDictCursor)
        conn = sqlite3.connect(self.sqlite_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    @property
    def placeholder(self) -> str:
        return "%s" if self.is_pg else "?"

    def init_schema(self):
        conn = self.connect()
        cur = conn.cursor()
        id_type = "SERIAL PRIMARY KEY" if self.is_pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
        ts = "TIMESTAMPTZ" if self.is_pg else "TEXT"

        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS aircraft (
            id {id_type},
            icao_hex VARCHAR(10) UNIQUE NOT NULL,
            callsign VARCHAR(20),
            registration VARCHAR(20),
            aircraft_type VARCHAR(20),
            manufacturer VARCHAR(100),
            model VARCHAR(100),
            operator VARCHAR(100),
            first_seen {ts},
            last_seen {ts},
            total_sessions INTEGER DEFAULT 0,
            total_observations INTEGER DEFAULT 0,
            created_at {ts} DEFAULT CURRENT_TIMESTAMP,
            updated_at {ts} DEFAULT CURRENT_TIMESTAMP
        );""")

        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS aircraft_enrichment (
            id {id_type},
            aircraft_id INTEGER NOT NULL REFERENCES aircraft(id) ON DELETE CASCADE,
            registration VARCHAR(20),
            aircraft_type VARCHAR(20),
            manufacturer VARCHAR(100),
            model VARCHAR(100),
            operator_name VARCHAR(150),
            operator_icao VARCHAR(10),
            operator_iata VARCHAR(10),
            country VARCHAR(100),
            source VARCHAR(50),
            source_url VARCHAR(255),
            manufacturer_icao VARCHAR(20),
            operator_callsign VARCHAR(50),
            owner VARCHAR(150),
            serial_number VARCHAR(50),
            type_code VARCHAR(20),
            icao_aircraft_type VARCHAR(20),
            built VARCHAR(20),
            first_flight_date VARCHAR(20),
            category VARCHAR(50),
            created_at {ts} DEFAULT CURRENT_TIMESTAMP,
            updated_at {ts} DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_enrichment_aircraft UNIQUE(aircraft_id)
        );""")

        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS detection_sessions (
            id {id_type},
            aircraft_id INTEGER NOT NULL REFERENCES aircraft(id) ON DELETE CASCADE,
            started_at {ts} NOT NULL,
            last_observed_at {ts} NOT NULL,
            ended_at {ts},
            observation_count INTEGER DEFAULT 0,
            first_distance_km REAL,
            first_bearing REAL,
            last_distance_km REAL,
            last_bearing REAL,
            origin_iata VARCHAR(10),
            origin_icao VARCHAR(10),
            destination_iata VARCHAR(10),
            destination_icao VARCHAR(10),
            origin_name VARCHAR(200),
            origin_city VARCHAR(100),
            origin_country VARCHAR(100),
            destination_name VARCHAR(200),
            destination_city VARCHAR(100),
            destination_country VARCHAR(100)
        );""")

        # Idempotent column migrations for both route codes and full names.
        for col, ctype in [
            ("origin_iata", "VARCHAR(10)"), ("origin_icao", "VARCHAR(10)"),
            ("destination_iata", "VARCHAR(10)"), ("destination_icao", "VARCHAR(10)"),
            ("origin_name", "VARCHAR(200)"), ("origin_city", "VARCHAR(100)"),
            ("origin_country", "VARCHAR(100)"), ("destination_name", "VARCHAR(200)"),
            ("destination_city", "VARCHAR(100)"), ("destination_country", "VARCHAR(100)"),
        ]:
            try:
                cur.execute(f"ALTER TABLE detection_sessions ADD COLUMN {col} {ctype};")
            except Exception:
                pass

        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS observations (
            id {id_type},
            aircraft_id INTEGER NOT NULL REFERENCES aircraft(id) ON DELETE CASCADE,
            session_id INTEGER REFERENCES detection_sessions(id) ON DELETE SET NULL,
            timestamp {ts} NOT NULL,
            altitude_baro INTEGER,
            altitude_geom INTEGER,
            ground_speed REAL,
            track REAL,
            latitude REAL,
            longitude REAL,
            vertical_rate INTEGER,
            squawk VARCHAR(10),
            distance_km REAL,
            bearing REAL,
            raw_data TEXT,
            created_at {ts} DEFAULT CURRENT_TIMESTAMP
        );""")

        cur.execute(f"""
        CREATE TABLE IF NOT EXISTS alert_history (
            id {id_type},
            timestamp {ts} NOT NULL,
            hex VARCHAR(10) NOT NULL,
            flight VARCHAR(20),
            registration VARCHAR(20),
            aircraft_type VARCHAR(20),
            operator VARCHAR(100),
            alert_type VARCHAR(50),
            title VARCHAR(120),
            priority INTEGER DEFAULT 3,
            squawk VARCHAR(10),
            altitude INTEGER,
            speed REAL,
            distance REAL,
            raw_json TEXT,
            updated_at {ts}
        );""")

        for stmt in [
            "CREATE INDEX IF NOT EXISTS idx_aircraft_hex ON aircraft(icao_hex);",
            "CREATE INDEX IF NOT EXISTS idx_aircraft_last_seen ON aircraft(last_seen);",
            "CREATE INDEX IF NOT EXISTS idx_sessions_aircraft ON detection_sessions(aircraft_id);",
            "CREATE INDEX IF NOT EXISTS idx_sessions_started ON detection_sessions(started_at);",
            "CREATE INDEX IF NOT EXISTS idx_sessions_ac_started ON detection_sessions(aircraft_id, started_at DESC);",
            "CREATE INDEX IF NOT EXISTS idx_obs_session ON observations(session_id);",
            "CREATE INDEX IF NOT EXISTS idx_obs_aircraft ON observations(aircraft_id);",
            "CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alert_history(timestamp);",
        ]:
            cur.execute(stmt)

        conn.commit()
        conn.close()


db = Database()
