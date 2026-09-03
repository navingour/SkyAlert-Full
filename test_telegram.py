import yaml
from pathlib import Path
from app.telegram import TelegramNotifier

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config" / "config.yaml"

with open(CONFIG_FILE, "r") as f:
    config = yaml.safe_load(f)

telegram = TelegramNotifier(
    config["telegram"]["bot_token"],
    config["telegram"]["chat_id"]
)

telegram.send("✅ SkyAlert Telegram test successful!")

print("Message sent successfully.")
