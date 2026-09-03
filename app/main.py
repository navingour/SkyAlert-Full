from pathlib import Path
import time
import yaml

from app.aircraft_database import aircraft_db
from app.logger import logger
from app.tar1090 import Tar1090
from app.state import StateEngine
from app.alert_lookup import AlertLookup
from app.rules import RuleEngine
from app.telegram import TelegramNotifier
from app.notifier import Notifier
from app.heartbeat import Heartbeat
from app.source_health import SourceHealth


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config" / "config.yaml"


def load_config():

    with open(CONFIG_FILE, "r") as f:
        return yaml.safe_load(f)


def main():

    config = load_config()

    receiver = Tar1090(
        config["tar1090"]["url"]
    )

    source_health = SourceHealth()
    state = StateEngine()
    alert_lookup = AlertLookup()
    rules = RuleEngine(config)

    telegram = None

    if config["telegram"]["enabled"]:

        telegram = TelegramNotifier(
            config["telegram"]["bot_token"],
            config["telegram"]["chat_id"]
        )

    notifier = Notifier(telegram)
    heartbeat = Heartbeat()

    logger.info("=" * 60)
    logger.info("SkyAlert Started")
    logger.info("=" * 60)

    if telegram:

        try:

            telegram.send(
                "🛫 SkyAlert Started\n\n"
                "Monitoring aircraft..."
            )

        except Exception:

            logger.exception(
                "Telegram startup message failed"
            )

    while True:

        try:

            aircraft = receiver.get_aircraft()

            health = source_health.success()

            if health["recovered"] and telegram:

                downtime = health["downtime"]

                if downtime is not None:

                    minutes = int(downtime // 60)
                    seconds = int(downtime % 60)

                    downtime_text = (
                        f"{minutes}m {seconds}s"
                    )

                else:

                    downtime_text = "Unknown"

                try:

                    telegram.send(
                        "🟢 SkyAlert Source RECOVERED\n\n"
                        "Aircraft data source is "
                        "reachable again.\n\n"
                        f"Source: {config['tar1090']['url']}\n"
                        f"Downtime: {downtime_text}"
                    )

                except Exception:

                    logger.exception(
                        "Telegram source recovery "
                        "message failed"
                    )

            events = state.compare(aircraft)

            from app.session_tracker import session_tracker
            for plane in aircraft:
                try:
                    session_tracker.process_aircraft_observation(plane)
                except Exception:
                    pass

            logger.info(
                "Aircraft=%d New=%d Gone=%d",
                len(events["current"]),
                len(events["new"]),
                len(events["gone"])
            )

            from app.lookup.queue import lookup_queue

            for plane in events["new"]:

                heartbeat.aircraft_seen()

                hex_code = plane.get(
                    "hex",
                    ""
                ).upper()

                info = aircraft_db.lookup(
                    hex_code
                )

                if not info:

                    lookup_queue.add(hex_code)

                    plane["registration"] = "Loading..."
                    plane["aircraft_type"] = "Unknown"
                    plane["description"] = "Looking up..."

                else:

                    plane["registration"] = info.get(
                        "Registration",
                        "Unknown"
                    )

                    plane["aircraft_type"] = info.get(
                        "ICAOTypeCode",
                        "Unknown"
                    )

                    plane["description"] = (
                        info.get("Type")
                        or info.get("manufacturerModel")
                        or "Unknown"
                    )

                    plane["manufacturer"] = (
                        info.get("Manufacturer")
                        or info.get("manufacturer")
                        or ""
                    )

                    plane["owner"] = (
                        info.get("RegisteredOwners")
                        or info.get("owner")
                        or ""
                    )

                special = alert_lookup.get(
                    hex_code
                )

                alerts = rules.evaluate(
                    plane,
                    special
                )

                if alerts:

                    plane["special"] = special

                    for alert in alerts:

                        heartbeat.alert_sent()

                        notifier.send(
                            alert,
                            plane
                        )

            for plane in events["gone"]:

                logger.info(
                    "GONE | %s",
                    plane.get("hex")
                )

            if telegram and heartbeat.should_send():

                telegram.send(
                    heartbeat.build_message(
                        len(events["current"])
                    )
                )

                heartbeat.reset_hour()

                logger.info(
                    "Heartbeat sent"
                )

        except Exception:

            health = source_health.failure()

            logger.exception(
                "SkyAlert Error"
            )

            if health["down"] and telegram:

                try:

                    source_url = config["tar1090"]["url"]

                    telegram.send(
                        "🔴 SkyAlert Source DOWN\n\n"
                        "Aircraft data source is unreachable.\n\n"
                        f"Source: {source_url}\n"
                        "Failures: 3 consecutive\n\n"
                        "SkyAlert engine is still running, "
                        "but aircraft data is unavailable."
                    )

                except Exception:

                    logger.exception(
                        "Telegram source down "
                        "message failed"
                    )

        time.sleep(
            config["general"]["poll_interval"]
        )


if __name__ == "__main__":

    main()
