from pathlib import Path
import sqlite3
import json
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent

DB_FILE = BASE_DIR / "data" / "aircraft.db"


class AircraftDatabase:

    def __init__(self):

        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")

        self.create_tables()


    def create_tables(self):

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS aircraft(

                hex TEXT PRIMARY KEY,

                registration TEXT,

                model_code TEXT,

                model_name TEXT,

                production_line TEXT,

                owner TEXT,

                engines TEXT,

                age INTEGER,

                status TEXT,

                updated_at TEXT,

                raw_json TEXT

            )
            """
        )

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lookup_queue(

                hex TEXT PRIMARY KEY,

                first_seen TEXT,

                last_attempt TEXT,

                attempts INTEGER DEFAULT 0,

                status TEXT

            )
            """
        )

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_usage(

                provider TEXT,

                usage_date TEXT,

                calls_used INTEGER,

                PRIMARY KEY(provider, usage_date)

            )
            """
        )

        self.conn.commit()

    def lookup(self, hex_code):

        row = self.conn.execute(
            """
            SELECT raw_json
            FROM aircraft
            WHERE hex=?
            """,
            (hex_code.upper(),)
        ).fetchone()

        if not row:
            return None

        return json.loads(row[0])

    def save(self, data):

        hex_code = (
            data.get("ModeS")
            or data.get("icao")
            or data.get("hex")
        )

        if not hex_code:
            return

        registration = (
            data.get("Registration")
            or data.get("tail")
        )

        model_code = (
            data.get("ICAOTypeCode")
            or data.get("icaoType")
        )

        model_name = (
            data.get("Type")
            or data.get("description")
            or data.get("manufacturerModel")
        )

        production_line = (
            data.get("Manufacturer")
            or data.get("manufacturer")
        )

        owner = (
            data.get("RegisteredOwners")
            or data.get("owner")
        )

        engines = (
            data.get("engines")
            or ""
        )

        age = (
            data.get("plane_age")
            or data.get("age")
        )

        status = (
            data.get("plane_status")
            or data.get("status")
            or "active"
        )

        self.conn.execute(
            """
            INSERT OR REPLACE INTO aircraft
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                hex_code.upper(),
                registration,
                model_code,
                model_name,
                production_line,
                owner,
                engines,
                age,
                status,
                datetime.utcnow().isoformat(),
                json.dumps(data)
            )
        )

        self.conn.commit()


aircraft_db = AircraftDatabase()
