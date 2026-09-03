from pathlib import Path
import sqlite3
import json
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "data" / "aircraft.db"


class EventDatabase:

    def __init__(self):
        self.conn = sqlite3.connect(
            DB_FILE,
            check_same_thread=False
        )
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.create_tables()


    def create_tables(self):

        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            updated_at TEXT,
            hex TEXT,
            flight TEXT,
            registration TEXT,
            aircraft_type TEXT,
            operator TEXT,
            alert_type TEXT,
            title TEXT,
            priority INTEGER,
            squawk TEXT,
            altitude INTEGER,
            speed REAL,
            distance REAL,
            raw_json TEXT
        )
        """)

        try:
            self.conn.execute(
                "ALTER TABLE events ADD COLUMN updated_at TEXT"
            )
        except sqlite3.OperationalError:
            pass

        self.conn.commit()

    def save(self, alert, plane):

        now = datetime.utcnow().isoformat()

        cur = self.conn.execute(
            """
            INSERT INTO events(
                timestamp,
                updated_at,
                hex,
                flight,
                registration,
                aircraft_type,
                operator,
                alert_type,
                title,
                priority,
                squawk,
                altitude,
                speed,
                distance,
                raw_json
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                now,
                now,
                plane.get("hex", "").upper(),
                plane.get("flight", "").strip(),
                plane.get("registration"),
                plane.get("aircraft_type"),
                plane.get("owner"),
                alert["title"],
                alert["title"],
                alert["priority"],
                plane.get("squawk"),
                plane.get("alt_baro"),
                plane.get("gs"),
                plane.get("r_dst"),
                json.dumps(plane)
            )
        )

        self.conn.commit()
        return cur.lastrowid

    def update_lookup(self, event_id, plane):

        self.conn.execute(
            """
            UPDATE events
            SET
                updated_at=?,
                registration=?,
                aircraft_type=?,
                operator=?,
                raw_json=?
            WHERE id=?
            """,
            (
                datetime.utcnow().isoformat(),
                plane.get("registration"),
                plane.get("description"),
                plane.get("owner"),
                json.dumps(plane),
                event_id
            )
        )

        self.conn.commit()

    def update_from_lookup(self, hex_code, aircraft):

        registration = (
            aircraft.get("Registration")
            or aircraft.get("tail")
            or aircraft.get("registration")
        )

        aircraft_type = (
            aircraft.get("ICAOTypeCode")
            or aircraft.get("icaoType")
            or aircraft.get("description")
        )

        operator = (
            aircraft.get("RegisteredOwners")
            or aircraft.get("owner")
        )

        self.conn.execute(
            """
            UPDATE events
            SET
                registration=?,
                aircraft_type=?,
                operator=?,
                updated_at=?
            WHERE id=(
                SELECT id
                FROM events
                WHERE hex=?
                ORDER BY id DESC
                LIMIT 1
            )
            """,
            (
                registration,
                aircraft_type,
                operator,
                datetime.utcnow().isoformat(),
                hex_code.upper(),
            )
        )

        self.conn.commit()

        row = self.conn.execute(
            """
            SELECT
                flight,
                registration,
                aircraft_type
            FROM events
            WHERE hex=?
            ORDER BY id DESC
            LIMIT 1
            """,
            (hex_code.upper(),)
        ).fetchone()

        return row

    def latest(self, limit=100):

        cur = self.conn.execute(
            """
            SELECT
                timestamp,
                title,
                registration,
                aircraft_type,
                flight,
                hex
            FROM events
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        )

        return cur.fetchall()


event_db = EventDatabase()
