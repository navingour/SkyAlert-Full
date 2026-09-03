import math


class RuleEngine:

    def __init__(self, config):
        self.config = config

    def _in_radius(self, lat, lon, center_lat, center_lon, radius_km):
        if lat is None or lon is None:
            return False
        R = 6371.0
        dlat = math.radians(center_lat - lat)
        dlon = math.radians(center_lon - lon)
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(lat))
            * math.cos(math.radians(center_lat))
            * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c
        return distance <= radius_km

    def evaluate(self, plane, special):

        alerts = []

        flight = plane.get("flight", "").strip().upper()
        registration = plane.get("registration", "")
        aircraft_type = plane.get("aircraft_type", "").upper()
        squawk = str(plane.get("squawk", ""))
        altitude = plane.get("alt_baro")
        speed = plane.get("gs")
        lat = plane.get("lat")
        lon = plane.get("lon")

        # ------------------------------------------------
        # SQUAWK ALERTS
        # ------------------------------------------------

        if self.config.get("alerts", {}).get("squawk", True):

            squawk_cfg = self.config.get("squawk", {})

            if squawk in squawk_cfg.get("hijack", ["7500"]):

                alerts.append({
                    "priority": 1,
                    "title": "🚨 HIJACK (7500)"
                })

            elif squawk in squawk_cfg.get("radio_failure", ["7600"]):

                alerts.append({
                    "priority": 1,
                    "title": "📻 RADIO FAILURE (7600)"
                })

            elif squawk in squawk_cfg.get("emergency", ["7700"]):

                alerts.append({
                    "priority": 1,
                    "title": "🚨 GENERAL EMERGENCY (7700)"
                })

        # ------------------------------------------------
        # SPECIAL AIRCRAFT DATABASE
        # ------------------------------------------------

        if special:

            campaign = special.get("campaign", "")

            if campaign == "Mil" and self.config.get("alerts", {}).get("military", True):

                alerts.append({
                    "priority": 2,
                    "title": "🪖 MILITARY AIRCRAFT"
                })

            elif campaign == "Gov" and self.config.get("alerts", {}).get("government", True):

                alerts.append({
                    "priority": 2,
                    "title": "👑 GOVERNMENT AIRCRAFT"
                })

            elif campaign == "Police" and self.config.get("alerts", {}).get("police", True):

                alerts.append({
                    "priority": 2,
                    "title": "🚓 POLICE AIRCRAFT"
                })

        # ------------------------------------------------
        # RARE AIRCRAFT
        # ------------------------------------------------

        if self.config.get("alerts", {}).get("rare_aircraft", True):

            rare_types = self.config.get("rare_aircraft", {}).get("aircraft_types", [])

            if aircraft_type in rare_types:

                alerts.append({
                    "priority": 3,
                    "title": "⭐ RARE AIRCRAFT"
                })

        # ------------------------------------------------
        # WATCHLIST
        # ------------------------------------------------

        if self.config.get("alerts", {}).get("watchlist", True):

            watch = self.config.get("watchlist", {})

            if registration in watch.get("registrations", []):

                alerts.append({
                    "priority": 4,
                    "title": "👀 WATCHLIST REGISTRATION"
                })

            if flight:

                for prefix in watch.get("flights", []):

                    if flight.startswith(prefix):

                        alerts.append({
                            "priority": 4,
                            "title": "👀 WATCHLIST FLIGHT"
                        })

                        break

            if special:

                operator = special.get("operator", "")

                if operator in watch.get("operators", []):

                    alerts.append({
                        "priority": 4,
                        "title": "👀 WATCHLIST OPERATOR"
                    })

        # ------------------------------------------------
        # GEOFENCE & BOUNDARY RULES
        # ------------------------------------------------

        geofence_cfg = self.config.get("geofence", {})
        if geofence_cfg.get("enabled"):
            c_lat = geofence_cfg.get("latitude")
            c_lon = geofence_cfg.get("longitude")
            radius = geofence_cfg.get("radius_km", 50)
            if c_lat and c_lon and self._in_radius(lat, lon, c_lat, c_lon, radius):
                alerts.append({
                    "priority": 4,
                    "title": f"📍 GEOFENCE ZONE ({geofence_cfg.get('name', 'Restricted Area')})"
                })

        # ------------------------------------------------
        # ALTITUDE / SPEED THRESHOLD RULES
        # ------------------------------------------------

        thresholds = self.config.get("thresholds", {})
        if thresholds.get("enabled"):
            min_alt = thresholds.get("min_altitude")
            max_speed = thresholds.get("max_speed")
            if min_alt and altitude is not None and altitude < min_alt:
                alerts.append({
                    "priority": 4,
                    "title": f"⚠️ LOW ALTITUDE ALERT (<{min_alt} ft)"
                })
            if max_speed and speed is not None and speed > max_speed:
                alerts.append({
                    "priority": 4,
                    "title": f"⚡ HIGH SPEED ALERT (>{max_speed} kt)"
                })

        return alerts
