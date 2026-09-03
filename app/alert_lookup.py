import csv
from pathlib import Path

from app.logger import logger

BASE_DIR = Path(__file__).resolve().parent.parent
DB_FILE = BASE_DIR / "data" / "alerts" / "plane-alert-db.csv"


class AlertLookup:

    def __init__(self):

        self.aircraft = {}

        self.load()

    def load(self):

        if not DB_FILE.exists():
            logger.warning("Alert database not found: %s", DB_FILE)
            return

        with open(DB_FILE, newline="", encoding="utf-8") as f:

            reader = csv.DictReader(f)

            for row in reader:

                hexcode = row.get("$ICAO", "").strip().upper()

                if not hexcode:
                    continue

                self.aircraft[hexcode] = {
                    "registration": row.get("$Registration", "").strip(),
                    "operator": row.get("$Operator", "").strip(),
                    "aircraft": row.get("$Type", "").strip(),
                    "icao_type": row.get("$ICAO Type", "").strip(),
                    "campaign": row.get("#CMPG", "").strip(),
                    "category": row.get("Category", "").strip(),
                    "tag1": row.get("$Tag 1", "").strip(),
                    "tag2": row.get("$#Tag 2", "").strip(),
                    "tag3": row.get("$#Tag 3", "").strip(),
                    "link": row.get("$#Link", "").strip(),
                }

        logger.info(
            "Loaded %d special aircraft",
            len(self.aircraft)
        )

    def get(self, hexcode):

        if not hexcode:
            return None

        return self.aircraft.get(hexcode.upper())
