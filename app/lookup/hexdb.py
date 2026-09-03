import requests


class HexDBProvider:

    BASE_URL = "https://hexdb.io/api/v1/aircraft"

    def __init__(self):
        pass

    def lookup(self, hex_code):

        try:

            response = requests.get(
                f"{self.BASE_URL}/{hex_code.upper()}",
                timeout=10
            )

            if response.status_code != 200:
                return None

            return response.json()

        except Exception:

            return None	
