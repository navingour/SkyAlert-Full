from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json
from pathlib import Path
import httpx
from app.adapters.base import BaseInputAdapter
from app.models.aircraft import NormalizedAircraft
from app.logger import logger


class ReadsbJsonAdapter(BaseInputAdapter):

    def __init__(self, source_id: str, name: str, config: Dict[str, Any]):
        super().__init__(source_id, name, config)
        self.url_or_path = config.get("url_or_path", "http://localhost/readsb/data/aircraft.json")
        self.timeout = config.get("timeout", 10)
        self.is_file = not (self.url_or_path.startswith("http://") or self.url_or_path.startswith("https://"))
        self.client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> None:
        if not self.is_file:
            if not self.client or self.client.is_closed:
                self.client = httpx.AsyncClient(timeout=self.timeout)
        self.is_connected = True

    async def disconnect(self) -> None:
        if self.client and not self.client.is_closed:
            await self.client.aclose()
        self.is_connected = False

    async def fetch_aircraft(self) -> List[NormalizedAircraft]:
        if not self.is_connected:
            await self.connect()

        try:
            if self.is_file:
                path = Path(self.url_or_path)
                if not path.exists():
                    logger.warning("ReadsbJsonAdapter file not found: %s", self.url_or_path)
                    return []
                data = json.loads(path.read_text(encoding="utf-8"))
            else:
                if not self.client:
                    await self.connect()
                response = await self.client.get(self.url_or_path)
                response.raise_for_status()
                data = response.json()

            raw_list = data.get("aircraft", [])
            self.last_heartbeat = datetime.now(timezone.utc)
            self.is_connected = True

            result = []
            for plane in raw_list:
                hex_code = plane.get("hex")
                if not hex_code:
                    continue

                alt_baro = plane.get("alt_baro")
                if isinstance(alt_baro, str):
                    if alt_baro == "ground":
                        alt_baro = 0
                    else:
                        try:
                            alt_baro = int(alt_baro)
                        except ValueError:
                            alt_baro = None

                normalized = NormalizedAircraft(
                    hex=hex_code,
                    flight=plane.get("flight"),
                    registration=plane.get("r") or plane.get("registration"),
                    aircraft_type=plane.get("t") or plane.get("type") or plane.get("aircraft_type"),
                    latitude=plane.get("lat"),
                    longitude=plane.get("lon"),
                    altitude_baro=alt_baro,
                    altitude_geom=plane.get("alt_geom"),
                    ground_speed=plane.get("gs"),
                    track=plane.get("track"),
                    vertical_rate=plane.get("baro_rate") or plane.get("geom_rate"),
                    squawk=plane.get("squawk"),
                    emergency=plane.get("emergency"),
                    rssi=plane.get("rssi"),
                    distance_km=plane.get("r_dst"),
                    source_id=self.source_id,
                    source_type="readsb_json",
                    raw_telemetry=plane
                )
                result.append(normalized)

            return result

        except Exception as e:
            logger.warning("ReadsbJsonAdapter fetch error: %s", e)
            self.is_connected = False
            return []
