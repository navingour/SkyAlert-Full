import requests


class Tar1090:

    def __init__(self, url):
        self.url = url

    def get_aircraft(self):

        response = requests.get(
            self.url,
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        return data.get("aircraft", [])
