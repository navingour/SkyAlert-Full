"""Aircraft identity + route enrichment using configured providers."""
import logging
from typing import Any, Dict, Optional

from app.config import CONFIG
from app.providers.adsbdb import ADSBDBProvider
from app.providers.skylink import SkyLinkProvider

logger = logging.getLogger("skyalert.enrich")


def _providers() -> Dict[str, Any]:
    prov = CONFIG.get("providers", {})
    timeout = int(CONFIG.get("enrichment", {}).get("request_timeout_seconds", 3))
    return {
        "adsbdb": ADSBDBProvider(prov.get("adsbdb", {}).get("base_url", "https://api.adsbdb.com/v0"), timeout)
        if prov.get("adsbdb", {}).get("enabled", True) else None,
        "skylink": SkyLinkProvider(
            prov.get("skylink", {}).get("api_key", ""),
            prov.get("skylink", {}).get("host", "skylink-api.p.rapidapi.com"),
            prov.get("skylink", {}).get("base_url", "https://skylink-api.p.rapidapi.com/v3"),
            timeout,
        ) if prov.get("skylink", {}).get("enabled", False) else None,
    }


class Enricher:
    def __init__(self):
        self.providers = _providers()
        self.enr = CONFIG.get("enrichment", {})

    def resolve_route(self, callsign: str, icao_hex: str) -> Optional[Dict[str, Any]]:
        """Resolve full route (codes + names) for a flight.
        Prefers the combined adsbdb aircraft+callsign endpoint, then callsign."""
        if not self.enr.get("resolve_routes", True):
            return None
        adsbdb = self.providers.get("adsbdb")
        if adsbdb:
            combined = adsbdb.aircraft_with_route(icao_hex, callsign)
            if combined and combined.get("route"):
                return combined["route"]
            route = adsbdb.callsign_route(callsign)
            if route:
                return route
        return None

    def resolve_identity(self, icao_hex: str) -> Optional[Dict[str, Any]]:
        """Resolve registration/type/operator for an airframe."""
        if not self.enr.get("resolve_identity", True):
            return None
        skylink = self.providers.get("skylink")
        if skylink and skylink.enabled:
            data = skylink.aircraft_by_hex(icao_hex)
            if data and isinstance(data.get("aircraft"), dict):
                return skylink.to_identity(data["aircraft"])
        adsbdb = self.providers.get("adsbdb")
        if adsbdb:
            return adsbdb.aircraft(icao_hex)
        return None


enricher = Enricher()
