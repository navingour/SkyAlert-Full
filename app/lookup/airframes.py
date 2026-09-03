import requests


class AirframesProvider:

    BASE_URL = "https://api.airframes.io/v1"

    def __init__(self, api_key=""):

        self.api_key = api_key

    def lookup(self, hex_code):

        headers = {}

        if self.api_key:

            headers["X-API-KEY"] = self.api_key

        try:

            response = requests.get(
                f"{self.BASE_URL}/airframes/icao/{hex_code.upper()}",
                headers=headers,
                timeout=10
            )

            if response.status_code != 200:
                return None

            return response.json()

        except Exception:

            return None
