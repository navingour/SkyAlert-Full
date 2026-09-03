from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import httpx
from app.adapters.base import BaseInputAdapter
from app.models.aircraft import NormalizedAircraft
from app.logger import logger


class Tar1090HttpAdapter(BaseInputAdapter):

    def __init__(self, source_id: str, name: str, config: Dict[str, Any]):
        super().__init__(source_id, name, config)
        self.url = config.get("url", "http://localhost/tar1090/data/aircraft.json")
        self.timeout = config.get("timeout", 10)
        self.client: Optional[httpx.AsyncClient] = None

    async def connect(self) -> None:
        if not self.client or self.client.is_closed:
            self.client = httpx.AsyncClient(timeout=self.timeout)
        self.is_connected = True

    async def disconnect(self) -> None:
        if self.client and not self.client.is_closed:
            await self.client.aclose()
        self.is_connected = False

    async def fetch_aircraft(self) -> List[NormalizedAircraft]:
        if not self.is_connected or not self.client:
            await self.connect()

        try:
            response = await self.client.get(self.url)
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
                    source_type="tar1090_http",
                    raw_telemetry=plane
                )
                result.append(normalized)

            return result

        except Exception as e:
            logger.warning("Tar1090HttpAdapter fetch error from %s: %s", self.url, e)
            self.is_connected = False
            return []
