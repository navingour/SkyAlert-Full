import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.adapters.base import BaseInputAdapter
from app.models.aircraft import NormalizedAircraft
from app.logger import logger


class SbsTcpAdapter(BaseInputAdapter):

    def __init__(self, source_id: str, name: str, config: Dict[str, Any]):
        super().__init__(source_id, name, config)
        self.host = config.get("host", "127.0.0.1")
        self.port = config.get("port", 30003)
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
            logger.info("SbsTcpAdapter connected to %s:%d", self.host, self.port)
        except Exception as e:
            logger.warning("SbsTcpAdapter connection failed to %s:%d: %s", self.host, self.port, e)
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

        lines_read = 0
        while lines_read < 50:
            try:
                line_bytes = await asyncio.wait_for(self.reader.readline(), timeout=0.1)
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="ignore").strip()
                if not line.startswith("MSG"):
                    continue

                parts = line.split(",")
                if len(parts) < 11:
                    continue

                msg_type = parts[1]
                hex_code = parts[4].strip().upper()
                if not hex_code:
                    continue

                if hex_code not in self._cache:
                    self._cache[hex_code] = {"hex": hex_code, "updated": datetime.now(timezone.utc)}

                entry = self._cache[hex_code]
                entry["updated"] = datetime.now(timezone.utc)

                if msg_type == "1" and len(parts) > 10 and parts[10].strip():
                    entry["flight"] = parts[10].strip()
                elif msg_type == "3":
                    if len(parts) > 11 and parts[11].strip():
                        try:
                            entry["alt_baro"] = int(parts[11])
                        except ValueError:
                            pass
                    if len(parts) > 14 and parts[14].strip() and len(parts) > 15 and parts[15].strip():
                        try:
                            entry["lat"] = float(parts[14])
                            entry["lon"] = float(parts[15])
                        except ValueError:
                            pass
                elif msg_type == "4":
                    if len(parts) > 12 and parts[12].strip():
                        try:
                            entry["gs"] = float(parts[12])
                        except ValueError:
                            pass
                    if len(parts) > 13 and parts[13].strip():
                        try:
                            entry["track"] = float(parts[13])
                        except ValueError:
                            pass
                elif msg_type == "6" and len(parts) > 17 and parts[17].strip():
                    entry["squawk"] = parts[17].strip()

                lines_read += 1

            except asyncio.TimeoutError:
                break
            except Exception as e:
                logger.warning("SbsTcpAdapter read line error: %s", e)
                self.is_connected = False
                break

        now = datetime.now(timezone.utc)
        self.last_heartbeat = now
        result = []

        stale_keys = [k for k, v in self._cache.items() if (now - v["updated"]).total_seconds() > 60]
        for k in stale_keys:
            del self._cache[k]

        for entry in self._cache.values():
            result.append(
                NormalizedAircraft(
                    hex=entry["hex"],
                    flight=entry.get("flight"),
                    latitude=entry.get("lat"),
                    longitude=entry.get("lon"),
                    altitude_baro=entry.get("alt_baro"),
                    ground_speed=entry.get("gs"),
                    track=entry.get("track"),
                    squawk=entry.get("squawk"),
                    source_id=self.source_id,
                    source_type="sbs_tcp",
                    raw_telemetry=entry
                )
            )

        return result
