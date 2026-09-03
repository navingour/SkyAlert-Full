"""SkyLink (RapidAPI) provider — optional, key required.

Real-time ADS-B tracking + aircraft enrichment.
Base: https://skylink-api.p.rapidapi.com/v3/adsb
Auth headers: x-rapidapi-key, x-rapidapi-host

Response aircraft fields include:
  icao24, callsign, registration, aircraft_type, type_name, operator,
  latitude, longitude, altitude, ground_speed, heading, vertical_rate,
  squawk, on_ground, last_seen, photo_url
"""
import json
import logging
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger("skyalert.provider.skylink")


class SkyLinkProvider:
    def __init__(self, api_key: str = "", host: str = "skylink-api.p.rapidapi.com",
                 base_url: str = "https://skylink-api.p.rapidapi.com/v3", timeout: int = 4):
        self.api_key = api_key
        self.host = host
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        if not self.enabled:
            return None
        qs = f"?{urllib.parse.urlencode(params)}" if params else ""
        req = urllib.request.Request(self.base_url + path + qs, headers={
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host,
        })
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            logger.debug("skylink request failed %s: %s", path, e)
        return None

    # ── aircraft queries ───────────────────────────────────────────
    def aircraft(self, **filters) -> List[Dict[str, Any]]:
        """GET /adsb/aircraft with optional filters:
        icao24, registration, callsign, airline, lat/lon/radius, bbox,
        min_altitude/max_altitude, min_speed/max_speed.
        Returns list of aircraft dicts."""
        params = {k: v for k, v in filters.items() if v is not None}
        data = self._get("/adsb/aircraft", params or None)
        if not data:
            return []
        return data.get("aircraft", []) or []

    def aircraft_by_hex(self, icao24: str) -> Optional[Dict[str, Any]]:
        """GET /adsb/aircraft/{icao24} — single aircraft detail."""
        h = (icao24 or "").strip().upper()
        if not h:
            return None
        return self._get(f"/adsb/aircraft/{h}")

    def statistics(self) -> Optional[Dict[str, Any]]:
        """GET /adsb/aircraft/statistics — network coverage metrics."""
        return self._get("/adsb/aircraft/statistics")

    # ── normalisation ──────────────────────────────────────────────
    @staticmethod
    def to_identity(a: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Map a SkyLink aircraft record to the internal identity shape."""
        if not isinstance(a, dict):
            return None
        return {
            "registration": a.get("registration"),
            "aircraft_type": a.get("aircraft_type"),
            "manufacturer": a.get("manufacturer"),
            "model": a.get("type_name"),
            "operator": a.get("operator"),
            "type_code": a.get("aircraft_type"),
            "icao_aircraft_type": a.get("aircraft_type"),
            "photo_url": a.get("photo_url"),
        }
