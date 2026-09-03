import json
from datetime import datetime

from app.aircraft_database import aircraft_db


class AircraftUpdater:

    def save(self, data):

        aircraft_db.conn.execute(
            """
            INSERT OR REPLACE INTO aircraft(

                hex,
                registration,
                model_code,
                model_name,
                production_line,
                owner,
                engines,
                age,
                status,
                updated_at,
                raw_json

            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                data.get("ModeS"),
                data.get("Registration"),
                data.get("ICAOTypeCode"),
                data.get("Type"),
                data.get("Manufacturer"),
                data.get("RegisteredOwners"),
                None,
                None,
                "active",
                datetime.now().isoformat(),
                json.dumps(data)
            )
        )

        aircraft_db.conn.commit()


updater = AircraftUpdater()
