from app.aircraft_database import aircraft_db
from app.lookup.hexdb import HexDBProvider
from app.lookup.airframes import AirframesProvider
from app.logger import logger
from app.config import load_config


class LookupManager:

    def __init__(self):

        config = load_config()


        self.providers = []

        if config["providers"]["hexdb"]["enabled"]:
            self.providers.append(
                HexDBProvider()
            )

        if config["providers"]["airframes"]["enabled"]:
            self.providers.append(
                AirframesProvider(
                    config["providers"]["airframes"]["api_key"]
                )
            )

    def merge(self, aircraft, new_data):

        if not new_data:
            return aircraft

        for key, value in new_data.items():

            if value in (
                None,
                "",
                [],
                {}
            ):
                continue

            if key not in aircraft or not aircraft[key]:

                aircraft[key] = value

        return aircraft

    def lookup(self, hex_code):

        aircraft = aircraft_db.lookup(hex_code)

        if aircraft:

            logger.info(
                "Aircraft cache | %s",
                hex_code
            )

            return aircraft

        aircraft = {}

        for provider in self.providers:

            data = provider.lookup(hex_code)

            aircraft = self.merge(
                aircraft,
                data
            )

        if aircraft:

            aircraft_db.save(aircraft)

            logger.info(
                "Aircraft learned | %s",
                hex_code
            )

            return aircraft

        return None


lookup_manager = LookupManager()
