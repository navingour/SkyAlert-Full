from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.models.aircraft import NormalizedAircraft


class BaseInputAdapter(ABC):

    def __init__(self, source_id: str, name: str, config: Dict[str, Any]):
        self.source_id = source_id
        self.name = name
        self.config = config
        self.is_connected = False
        self.last_heartbeat: Optional[datetime] = None
        self.priority: int = config.get("priority", 1)

    @abstractmethod
    async def connect(self) -> None:
        """Establishes connection to the data source."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully closes connection or stream."""
        pass

    @abstractmethod
    async def fetch_aircraft(self) -> List[NormalizedAircraft]:
        """Fetches and converts raw telemetry into a list of NormalizedAircraft objects."""
        pass
