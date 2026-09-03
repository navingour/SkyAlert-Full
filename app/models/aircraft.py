from datetime import datetime, timezone
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator


class NormalizedAircraft(BaseModel):
    hex: str = Field(..., description="24-bit ICAO hex code in uppercase")
    flight: Optional[str] = Field(None, description="Callsign / Flight Number")
    registration: Optional[str] = Field(None, description="Tail Registration Number")
    aircraft_type: Optional[str] = Field(None, description="ICAO Aircraft Type Code")
    model_name: Optional[str] = Field(None, description="Full Model Name")
    manufacturer: Optional[str] = Field(None, description="Manufacturer")
    owner: Optional[str] = Field(None, description="Registered Owner / Operator")

    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    altitude_baro: Optional[int] = Field(None, description="Barometric Altitude in Feet")
    altitude_geom: Optional[int] = Field(None, description="Geometric Altitude in Feet")
    ground_speed: Optional[float] = Field(None, description="Ground Speed in Knots")
    track: Optional[float] = Field(None, description="Track / Heading Angle in Degrees")
    vertical_rate: Optional[int] = Field(None, description="Vertical Speed in Feet/Min")

    squawk: Optional[str] = Field(None, description="4-digit Octal Squawk Code")
    emergency: Optional[str] = Field(None, description="Emergency State Indicator")

    source_id: str = Field("default", description="Identifier of the ingestion source adapter")
    source_type: str = Field("http_json", description="Adapter type indicator")
    rssi: Optional[float] = Field(None, description="Signal strength in dBFS")
    distance_km: Optional[float] = Field(None, description="Radial distance from receiver in km")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_telemetry: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("hex", mode="before")
    @classmethod
    def clean_hex(cls, v: Any) -> str:
        if isinstance(v, str):
            return v.strip().upper()
        return str(v).strip().upper()

    @field_validator("flight", mode="before")
    @classmethod
    def clean_flight(cls, v: Any) -> Optional[str]:
        if isinstance(v, str):
            cleaned = v.strip()
            return cleaned if cleaned else None
        return None

    def to_legacy_dict(self) -> Dict[str, Any]:
        """Backward compatibility helper converting NormalizedAircraft to legacy SkyAlert dictionary format."""
        res = {
            "hex": self.hex,
            "flight": self.flight or "",
            "registration": self.registration,
            "aircraft_type": self.aircraft_type,
            "description": self.model_name or self.aircraft_type or "Unknown",
            "manufacturer": self.manufacturer or "",
            "owner": self.owner or "",
            "alt_baro": self.altitude_baro,
            "gs": self.ground_speed,
            "track": self.track,
            "squawk": self.squawk or "",
            "lat": self.latitude,
            "lon": self.longitude,
            "r_dst": self.distance_km,
            "source": self.source_id,
        }
        if self.raw_telemetry:
            for k, v in self.raw_telemetry.items():
                if k not in res:
                    res[k] = v
        return res
