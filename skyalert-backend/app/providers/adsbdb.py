"""adsbdb.com provider — free, no API key. Aircraft identity + flight route."""
import json
import logging
import urllib.request
from typing import Any, Dict, Optional

logger = logging.getLogger("skyalert.provider.adsbdb")

UA = {"User-Agent": "SkyAlert-Backend/1.0"}


def _get(url: str, timeout: int) -> Optional[Dict[str, Any]]:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.debug("adsbdb request failed %s: %s", url, e)
    return None


class ADSBDBProvider:
    def __init__(self, base_url: str = "https://api.adsbdb.com/v0", timeout: int = 3):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @staticmethod
    def _airport(a: Optional[Dict[str, Any]]) -> Dict[str, Optional[str]]:
        if not isinstance(a, dict):
            return {}
        return {
            "iata": a.get("iata_code"),
            "icao": a.get("icao_code"),
            "name": a.get("name"),
            "city": a.get("municipality") or a.get("city"),
            "country": a.get("country_name") or a.get("country"),
        }

    def aircraft(self, icao_hex: str) -> Optional[Dict[str, Any]]:
        """Return identity + optional flightroute for a hex."""
        data = _get(f"{self.base_url}/aircraft/{icao_hex.strip().upper()}", self.timeout)
        resp = (data or {}).get("response") or {}
        if not isinstance(resp, dict):
            return None
        ac = resp.get("aircraft") or {}
        out = {
            "icao_hex": icao_hex.strip().upper(),
            "registration": ac.get("registration"),
            "aircraft_type": ac.get("icao_type") or ac.get("type"),
            "manufacturer": ac.get("manufacturer"),
            "type_code": ac.get("icao_type") or ac.get("type"),
            "icao_aircraft_type": ac.get("icao_type"),
            "owner": ac.get("registered_owner"),
            "operator": ac.get("registered_owner_operator_flag") or ac.get("registered_owner"),
            "country": ac.get("registered_owner_country_name"),
        }
        fr = resp.get("flightroute")
        if isinstance(fr, dict):
            out["flightroute"] = fr
        return out

    @staticmethod
    def _route_from_flightroute(fr: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not isinstance(fr, dict):
            return None
        origin = ADSBDBProvider._airport(fr.get("origin"))
        dest = ADSBDBProvider._airport(fr.get("destination"))
        if not origin and not dest:
            return None
        return {
            "origin_iata": origin.get("iata"),
            "origin_icao": origin.get("icao"),
            "origin_name": origin.get("name"),
            "origin_city": origin.get("city"),
            "origin_country": origin.get("country"),
            "destination_iata": dest.get("iata"),
            "destination_icao": dest.get("icao"),
            "destination_name": dest.get("name"),
            "destination_city": dest.get("city"),
            "destination_country": dest.get("country"),
        }

    def callsign_route(self, callsign: str) -> Optional[Dict[str, Any]]:
        """Resolve a route (origin/destination, full names) for a callsign."""
        cs = (callsign or "").strip().upper()
        if not cs or cs == "-":
            return None
        data = _get(f"{self.base_url}/callsign/{cs}", self.timeout)
        return self._route_from_flightroute(((data or {}).get("response") or {}).get("flightroute"))

    def aircraft_with_route(self, icao_hex: str, callsign: str = "") -> Optional[Dict[str, Any]]:
        """Combined endpoint: identity + route in a single call.
        GET /aircraft/{mode_s}?callsign={callsign}
        """
        hex_u = (icao_hex or "").strip().upper()
        if not hex_u:
            return None
        url = f"{self.base_url}/aircraft/{hex_u}"
        cs = (callsign or "").strip().upper()
        if cs and cs != "-":
            url += f"?callsign={cs}"
        data = _get(url, self.timeout)
        resp = (data or {}).get("response") or {}
        if not isinstance(resp, dict):
            return None
        ac = resp.get("aircraft") or {}
        out = {
            "icao_hex": hex_u,
            "registration": ac.get("registration"),
            "aircraft_type": ac.get("icao_type") or ac.get("type"),
            "manufacturer": ac.get("manufacturer"),
            "type_code": ac.get("icao_type") or ac.get("type"),
            "icao_aircraft_type": ac.get("icao_type"),
            "owner": ac.get("registered_owner"),
            "operator": ac.get("registered_owner_operator_flag") or ac.get("registered_owner"),
            "country": ac.get("registered_owner_country_name"),
        }
        route = self._route_from_flightroute(resp.get("flightroute"))
        if route:
            out["route"] = route
        return out

    def airline(self, code: str) -> Optional[Dict[str, Any]]:
        """Airline info by ICAO or IATA code. GET /airline/{code}."""
        c = (code or "").strip().upper()
        if not c:
            return None
        data = _get(f"{self.base_url}/airline/{c}", self.timeout)
        resp = (data or {}).get("response")
        # Response may be a dict or a single-element list.
        if isinstance(resp, list):
            a = resp[0] if resp and isinstance(resp[0], dict) else {}
        else:
            a = resp if isinstance(resp, dict) else {}
        if not a:
            return None
        return {
            "name": a.get("name"),
            "icao": a.get("icao"),
            "iata": a.get("iata"),
            "callsign": a.get("callsign"),
            "country": a.get("country_name") or a.get("country"),
        }

    def n_number_to_modes(self, registration: str) -> Optional[str]:
        """Convert registration (N-number) to Mode-S hex. GET /n-number/{reg}."""
        reg = (registration or "").strip().upper()
        if not reg:
            return None
        data = _get(f"{self.base_url}/n-number/{reg}", self.timeout)
        resp = (data or {}).get("response") or {}
        return resp.get("mode_s") or resp.get("modes")

    def modes_to_registration(self, mode_s: str) -> Optional[str]:
        """Convert Mode-S hex to registration. GET /mode-s/{mode_s}."""
        ms = (mode_s or "").strip().upper()
        if not ms:
            return None
        data = _get(f"{self.base_url}/mode-s/{ms}", self.timeout)
        resp = (data or {}).get("response") or {}
        return resp.get("registration") or resp.get("n_number")

    def online(self) -> bool:
        """Service status check. GET /online."""
        data = _get(f"{self.base_url}/online", self.timeout)
        return bool(data)
