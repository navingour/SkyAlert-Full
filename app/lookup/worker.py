from pathlib import Path
import time
import yaml

from app.lookup.queue import lookup_queue
from app.lookup.manager import lookup_manager
from app.logger import logger
from app.event_database import event_db
from app.telegram import TelegramNotifier

from app.config import load_config

config = load_config()


telegram = None

if config["telegram"]["enabled"]:
    telegram = TelegramNotifier(
        config["telegram"]["bot_token"],
        config["telegram"]["chat_id"]
    )


class LookupWorker:

    def run(self):

        logger.info("Lookup Worker Started")

        while True:

            try:

                hex_code = lookup_queue.next()

                if not hex_code:
                    time.sleep(5)
                    continue

                logger.info(
                    "Looking up %s",
                    hex_code
                )

                result = lookup_manager.lookup(
                    hex_code
                )

                if result:

                    row = event_db.update_from_lookup(
                        hex_code,
                        result
                    )

                    if row:

                        flight, registration, aircraft_type = row

                        if telegram:

                            telegram.send(
                                f"""✅ Aircraft Identified

✈ Flight: {flight or 'Unknown'}

🛩 Registration: {registration or 'Unknown'}

🏷 ICAO Type: {aircraft_type or 'Unknown'}

🔷 HEX: {hex_code}
"""
                            )

                    lookup_queue.completed(
                        hex_code
                    )

                    logger.info(
                        "Lookup complete %s",
                        hex_code
                    )

                else:

                    lookup_queue.failed(
                        hex_code
                    )

                    logger.warning(
                        "Lookup failed %s",
                        hex_code
                    )

                time.sleep(2)

            except Exception:

                logger.exception(
                    "Lookup Worker Error"
                )

                time.sleep(5)


worker = LookupWorker()
