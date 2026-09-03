from app.logger import logger
from datetime import datetime
from app.event_database import event_db


class Notifier:

    def __init__(self, telegram=None):
        self.telegram = telegram

    def send(self, alert, plane):

        special = plane.get("special") or  {}

        # -------------------------------------------------
        # Aircraft information
        # -------------------------------------------------

        flight = plane.get("flight", "").strip() or "Unknown"
        registration = plane.get("registration", "Unknown")
        aircraft = plane.get("description", "Unknown")
        aircraft_type = plane.get("aircraft_type", "Unknown")
        manufacturer = plane.get("manufacturer") or ""
        owner = plane.get("owner") or ""
       

        hexcode = plane.get("hex", "").upper()
        squawk = plane.get("squawk", "----")

        altitude = plane.get("alt_baro")
        altitude = (
            "Unknown"
            if altitude is None
            else f"{altitude:,} ft"
        )

        distance = plane.get("r_dst")
        distance = (
            "Unknown"
            if distance is None
            else f"{round(distance, 1)} km"
        )

        heading = plane.get("track")
        heading = (
            "Unknown"
            if heading is None
            else f"{round(heading)}°"
        )

        gs = plane.get("gs")
        speed = (
            "Unknown"
            if gs is None
            else f"{round(gs * 1.852)} km/h"
        )

        operator = special.get("operator", "")
        category = special.get("category", "")
        campaign = special.get("campaign", "")

        tags = []

        for key in ("tag1", "tag2", "tag3"):
            value = special.get(key, "").strip()

            if value:
                tags.append(value)

        # -------------------------------------------------
        # Build Telegram Message
        # -------------------------------------------------

        message = f"""{alert['title']}

✈ Flight: {flight}

🛩 Registration: {registration}

📋 Aircraft: {aircraft}

🏷 ICAO Type: {aircraft_type}
"""

        if manufacturer:
            message += f"\n🏭 Manufacturer: {manufacturer}"

        if owner:
            message += f"\n👤 Owner: {owner}"

        message += f"""

🎯 Squawk: {squawk}

📏 Altitude: {altitude}

🚀 Speed: {speed}

🧭 Heading: {heading}

📍 Distance: {distance}

🔷 HEX: {hexcode}
"""

        if operator:
            message += f"""

👥 Operator

{operator}
"""

        if campaign:
            message += f"""

🎖 Campaign

{campaign}
"""

        if category:
            message += f"""

📂 Category

{category}
"""

        if tags:
            message += "\n\n🏷 Tags"

            for tag in tags:
                message += f"\n• {tag}"

        message += f"""

🕒 {datetime.now().strftime('%d %b %Y %H:%M:%S')}
"""

        logger.info(message)

        # -------------------------------------------------
        # Save event to database
        # -------------------------------------------------

        try:
            logger.info("Saving event to database")
            event_id = event_db.save(alert, plane)
            plane["_event_id"] = event_id
        except Exception:
            logger.exception("Failed to save event")

        # -------------------------------------------------
        # Telegram
        # -------------------------------------------------

        if self.telegram:

            try:
                self.telegram.send(message)

            except Exception:
                logger.exception("Telegram notification failed")
