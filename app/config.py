import os
from pathlib import Path
import yaml

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config" / "config.yaml"


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    if "telegram" in config:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if bot_token:
            config["telegram"]["bot_token"] = bot_token

        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if chat_id:
            config["telegram"]["chat_id"] = chat_id

    if "providers" in config and "airframes" in config["providers"]:
        api_key = os.getenv("AIRFRAMES_API_KEY")
        if api_key:
            config["providers"]["airframes"]["api_key"] = api_key

    return config
