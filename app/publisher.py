import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

STATUS_FILE = DATA_DIR / "status.json"

AIRCRAFT_FILE = DATA_DIR / "current_aircraft.json"


class Publisher:

    def publish_status(
        self,
        aircraft_visible,
        aircraft_seen,
        alerts_today,
        uptime,
    ):

        payload = {

            "timestamp": datetime.now().isoformat(),

            "aircraft_visible": aircraft_visible,

            "aircraft_seen": aircraft_seen,

            "alerts_today": alerts_today,

            "uptime": uptime

        }

        STATUS_FILE.write_text(
            json.dumps(
                payload,
                indent=4
            )
        )

    def publish_aircraft(
        self,
        aircraft
    ):

        payload = []

        for plane in aircraft:

            payload.append({

                "hex": plane.get("hex"),

                "flight": plane.get("flight"),

                "registration": plane.get("registration"),

                "aircraft": plane.get("aircraft_type"),

                "altitude": plane.get("alt_baro"),

                "speed": plane.get("gs"),

                "distance": plane.get("distance"),

                "special": plane.get("special")

            })

        AIRCRAFT_FILE.write_text(
            json.dumps(
                payload,
                indent=4
            )
        )


publisher = Publisher()
