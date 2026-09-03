from app.aircraft_database import aircraft_db
from datetime import datetime


class LookupQueue:

    def add(self, hex_code):

        aircraft_db.conn.execute(
            """
            INSERT OR IGNORE INTO lookup_queue
            (
                hex,
                first_seen,
                attempts,
                status
            )
            VALUES
            (
                ?, ?, 0, 'pending'
            )
            """,
            (
                hex_code.upper(),
                datetime.utcnow().isoformat()
            )
        )

        aircraft_db.conn.commit()

    def next(self):

        row = aircraft_db.conn.execute(
            """
            SELECT hex
            FROM lookup_queue
            WHERE status='pending'
            ORDER BY first_seen
            LIMIT 1
            """
        ).fetchone()

        if row:
            return row[0]

        return None

    def completed(self, hex_code):

        aircraft_db.conn.execute(
            """
            DELETE FROM lookup_queue
            WHERE hex=?
            """,
            (hex_code.upper(),)
        )

        aircraft_db.conn.commit()

    def failed(self, hex_code):

        aircraft_db.conn.execute(
            """
            UPDATE lookup_queue
            SET
                attempts = attempts + 1,
                last_attempt = ?,
                status = CASE
                    WHEN attempts + 1 >= 5 THEN 'failed'
                    ELSE 'pending'
                END
            WHERE hex = ?
            """,
            (
                datetime.utcnow().isoformat(),
                hex_code.upper(),
            )
        )

        aircraft_db.conn.commit()


lookup_queue = LookupQueue()
