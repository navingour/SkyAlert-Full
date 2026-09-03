"""
SkyAlert State Engine
"""

from typing import List


class StateEngine:

    def __init__(self):
        self.previous = {}
        self.initialized = False

    def compare(self, aircraft: List[dict]):

        current = {}

        for plane in aircraft:

            hex_code = plane.get("hex")

            if not hex_code:
                continue

            current[hex_code.upper()] = plane

        # First scan only builds the baseline.
        if not self.initialized:

            self.previous = current
            self.initialized = True

            return {
                "new": [],
                "gone": [],
                "current": current
            }

        previous_keys = set(self.previous.keys())
        current_keys = set(current.keys())

        new_keys = current_keys - previous_keys
        gone_keys = previous_keys - current_keys

        new_aircraft = [current[k] for k in new_keys]
        gone_aircraft = [self.previous[k] for k in gone_keys]

        self.previous = current

        return {
            "new": new_aircraft,
            "gone": gone_aircraft,
            "current": current
        }
