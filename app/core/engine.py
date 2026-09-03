import asyncio
from typing import List, Dict, Any
from app.logger import logger
from app.config import load_config
from app.adapters.factory import AdapterFactory
from app.state import StateEngine
from app.lookup import AircraftLookup
from app.alert_lookup import AlertLookup
from app.rules import RuleEngine
from app.telegram import TelegramNotifier
from app.notifier import Notifier
from app.core.deduplicator import AircraftDeduplicator
from app.models.aircraft import NormalizedAircraft


class SkyAlertAsyncEngine:

    def __init__(self):
        self.config = load_config()
        self.adapters = AdapterFactory.create_from_config(self.config)
        self.deduplicator = AircraftDeduplicator()
        self.state = StateEngine()
        self.lookup = AircraftLookup()
        self.alert_lookup = AlertLookup()
        self.rules = RuleEngine(self.config)

        self.telegram = None
        if self.config.get("telegram", {}).get("enabled"):
            self.telegram = TelegramNotifier(
                self.config["telegram"]["bot_token"],
                self.config["telegram"]["chat_id"]
            )
        self.notifier = Notifier(self.telegram)
        self.is_running = False

    async def initialize(self):
        logger.info("Initializing SkyAlert Async Engine with %d data source adapters", len(self.adapters))
        for adapter in self.adapters:
            try:
                await adapter.connect()
            except Exception as e:
                logger.warning("Failed to connect adapter %s: %s", adapter.name, e)

        if self.telegram:
            try:
                self.telegram.send("🛫 SkyAlert Async Engine Started\n\nMonitoring ADS-B feeds...")
            except Exception:
                logger.exception("Unable to send startup notification")

    async def poll_all_adapters(self) -> List[NormalizedAircraft]:
        tasks = [adapter.fetch_aircraft() for adapter in self.adapters]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        aggregated: List[NormalizedAircraft] = []
        for res in results:
            if isinstance(res, list):
                aggregated.extend(res)
            elif isinstance(res, Exception):
                logger.warning("Adapter fetch error: %s", res)

        return self.deduplicator.deduplicate(aggregated, self.adapters)


    async def run(self):
        await self.initialize()
        self.is_running = True
        logger.info("=" * 60)
        logger.info("SkyAlert Async Engine Loop Running")
        logger.info("=" * 60)

        poll_interval = self.config.get("general", {}).get("poll_interval", 15)

        while self.is_running:
            try:
                normalized_planes = await self.poll_all_adapters()
                legacy_planes = [plane.to_legacy_dict() for plane in normalized_planes]

                events = self.state.compare(legacy_planes)
                logger.info(
                    "Aircraft=%d New=%d Gone=%d",
                    len(events["current"]),
                    len(events["new"]),
                    len(events["gone"])
                )

                for plane in events["new"]:
                    hexcode = plane.get("hex", "").upper()

                    # Database lookup
                    info = self.lookup.lookup(hexcode)
                    if info:
                        plane["registration"] = info.get("registration", "Unknown")
                        plane["aircraft_type"] = info.get("type", "Unknown")
                        plane["description"] = info.get("description", "Unknown")
                    else:
                        plane["registration"] = "Unknown"
                        plane["aircraft_type"] = "Unknown"
                        plane["description"] = "Unknown"

                    # Special lookup
                    special = self.alert_lookup.get(hexcode)
                    if special:
                        plane["special"] = special

                    # Rule evaluation
                    alerts = self.rules.evaluate(plane, special)
                    if alerts:
                        for alert in alerts:
                            self.notifier.send(alert, plane)

                for plane in events["gone"]:
                    logger.info("GONE | %s", plane.get("hex", ""))

            except Exception:
                logger.exception("SkyAlert Async Engine Error")

            await asyncio.sleep(poll_interval)

    async def shutdown(self):
        self.is_running = False
        for adapter in self.adapters:
            try:
                await adapter.disconnect()
            except Exception:
                pass
        logger.info("SkyAlert Async Engine Shutdown Complete")
