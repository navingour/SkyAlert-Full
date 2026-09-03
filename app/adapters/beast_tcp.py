import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.adapters.base import BaseInputAdapter
from app.models.aircraft import NormalizedAircraft
from app.logger import logger


class BeastTcpAdapter(BaseInputAdapter):

    def __init__(self, source_id: str, name: str, config: Dict[str, Any]):
        super().__init__(source_id, name, config)
        self.host = config.get("host", "127.0.0.1")
        self.port = config.get("port", 30005)
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._cache: Dict[str, Dict[str, Any]] = {}

    async def connect(self) -> None:
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=5.0
            )
            self.is_connected = True
            logger.info("BeastTcpAdapter connected to %s:%d", self.host, self.port)
        except Exception as e:
            logger.warning("BeastTcpAdapter connection failed to %s:%d: %s", self.host, self.port, e)
            self.is_connected = False

    async def disconnect(self) -> None:
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except Exception:
                pass
        self.reader = None
        self.writer = None
        self.is_connected = False

    async def fetch_aircraft(self) -> List[NormalizedAircraft]:
        if not self.is_connected or not self.reader:
            await self.connect()
            if not self.is_connected or not self.reader:
                return []

        try:
            raw_data = await asyncio.wait_for(self.reader.read(1024), timeout=0.1)
            if not raw_data:
                self.is_connected = False
                return []
            self.last_heartbeat = datetime.now(timezone.utc)
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.warning("BeastTcpAdapter read error: %s", e)
            self.is_connected = False

        result = []
        for entry in self._cache.values():
            result.append(
                NormalizedAircraft(
                    hex=entry["hex"],
                    flight=entry.get("flight"),
                    source_id=self.source_id,
                    source_type="beast_tcp",
                    raw_telemetry=entry
                )
            )

        return result
