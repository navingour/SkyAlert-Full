import httpx
from typing import Dict, Any, Optional
from app.logger import logger


class WebhookNotifier:

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send_async(self, alert: Dict[str, Any], plane: Dict[str, Any]) -> bool:
        if not self.webhook_url:
            return False

        payload = {
            "event": "aircraft_alert",
            "alert": alert,
            "plane": plane
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(self.webhook_url, json=payload)
                return res.status_code in (200, 201, 202, 204)
        except Exception as e:
            logger.warning("Webhook dispatch error to %s: %s", self.webhook_url, e)
            return False
