from datetime import datetime
import time


class Heartbeat:

    def __init__(self):

        self.last_hour = -1

        self.start_time = time.time()

        self.new_aircraft = 0

        self.alerts_today = 0

        self.aircraft_db = 625083

        self.special_db = 16959

    def aircraft_seen(self):

        self.new_aircraft += 1

    def alert_sent(self):

        self.alerts_today += 1

    def uptime(self):

        seconds = int(time.time() - self.start_time)

        hours = seconds // 3600

        minutes = (seconds % 3600) // 60

        return f"{hours}h {minutes}m"

    def should_send(self):

        hour = datetime.now().hour

        if hour != self.last_hour:

            self.last_hour = hour

            return True

        return False

    def build_message(self, aircraft_visible):

        return f"""💚 SkyAlert Heartbeat

━━━━━━━━━━━━━━━━━━

🟢 Status : Healthy

🕒 Time : {time.strftime("%d-%b-%Y %H:%M:%S")}

⏱ Uptime : {self.uptime()}

📡 Aircraft Visible : {aircraft_visible}

✈ New This Hour : {self.new_aircraft}

🚨 Alerts Today : {self.alerts_today}

📦 Aircraft DB : {self.aircraft_db:,}

⭐ Special DB : {self.special_db:,}

━━━━━━━━━━━━━━━━━━

SkyAlert is monitoring normally."""

    def reset_hour(self):

        self.new_aircraft = 0
