import requests


class TelegramNotifier:

    def __init__(self, token, chat_id):

        self.token = token
        self.chat_id = chat_id

    def send(self, message):

        url = (
            f"https://api.telegram.org/"
            f"bot{self.token}/sendMessage"
        )

        payload = {

            "chat_id": self.chat_id,

            "text": message

        }

        response = requests.post(
            url,
            json=payload,
            timeout=20
        )

        response.raise_for_status()
