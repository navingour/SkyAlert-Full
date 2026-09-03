"""Query helpers shared by the API and HTML compatibility views."""
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from app.db import db, IST_TZ
from app.util import format_duration, format_ist_datetime

logger = logging.getLogger("skyalert.service")


def _val(row, key, idx):
    return row[key] if isinstance(row, dict) else row[idx]


def _ist_today_range():
    now = datetime.now(IST_TZ)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


def dashboard() -> Dict[str, Any]:
    conn = db.connect()
    cur = conn.cursor()
    ph = db.placeholder
    today_start, today_end = _ist_today_range()
    try:
        def scalar(sql, args=()):
            cur.execute(sql, args)
            r = cur.fetchone()
            return _val(r, list(r.keys())[0] if isinstance(r, dict) else 0, 0) if r else 0

        aircraft_count = scalar("SELECT COUNT(*) FROM aircraft")
        active = scalar(f"SELECT COUNT(*) FROM detection_sessions WHERE ended_at IS NULL")
        seen_today = scalar(
            f"SELECT COUNT(DISTINCT aircraft_id) FROM detection_sessions WHERE started_at >= {ph} AND started_at < {ph}",
            (today_start, today_end))
        sessions_today = scalar(
            f"SELECT COUNT(*) FROM detection_sessions WHERE started_at >= {ph} AND started_at < {ph}",
            (today_start, today_end))
        obs = scalar("SELECT COUNT(*) FROM observations")
        enriched = scalar("SELECT COUNT(*) FROM aircraft_enrichment")

        # duration today (sum of completed session durations)
        cur.execute(
            f"SELECT started_at, ended_at FROM detection_sessions WHERE started_at >= {ph} AND started_at < {ph}",
            (today_start, today_end))
        secs = 0
        for r in cur.fetchall():
            s, e = _val(r, "started_at", 0), _val(r, "ended_at", 1)
            if s and e:
                try:
                    secs += (datetime.fromisoformat(str(e).replace("Z", "+00:00")) -
                             datetime.fromisoformat(str(s).replace("Z", "+00:00"))).total_seconds()
                except Exception:
                    pass

        return {
            "active_aircraft": active,
            "active_sessions": active,
            "aircraft_count": aircraft_count,
            "aircraft_seen_today": seen_today,
            "duration_today": format_duration(secs),
            "duration_today_seconds": int(secs),
            "enriched_count": enriched,
            "observation_count": obs,
            "sessions_today": sessions_today,
            "unknown_count": max(aircraft_count - enriched, 0),
        }
    except Exception as e:
        logger.exception("dashboard error: %s", e)
        return {}
    finally:
        conn.close()


def list_aircraft(search: str = "", status: str = "all") -> List[Dict[str, Any]]:
    conn = db.connect()
    cur = conn.cursor()
    ph = db.placeholder
    where, args = "", []
    if search:
        where = f"""WHERE (a.icao_hex LIKE {ph} OR a.callsign LIKE {ph}
                    OR a.registration LIKE {ph} OR a.operator LIKE {ph})"""
        like = f"%{search}%"
        args = [like, like, like, like]
    try:
        cur.execute(
            f"""SELECT a.id, a.icao_hex, a.callsign, a.registration, a.aircraft_type,
                       a.manufacturer, a.model, a.operator, a.first_seen, a.last_seen,
                       a.total_sessions, a.total_observations,
                       (e.aircraft_id IS NOT NULL) AS is_enriched
                FROM aircraft a
                LEFT JOIN aircraft_enrichment e ON e.aircraft_id = a.id
                {where}
                ORDER BY a.last_seen DESC""",
            tuple(args))
        out = []
        for r in cur.fetchall():
            out.append({
                "id": _val(r, "id", 0),
                "icao_hex": _val(r, "icao_hex", 1),
                "callsign": _val(r, "callsign", 2) or "-",
                "registration": _val(r, "registration", 3) or _val(r, "icao_hex", 1),
                "aircraft_type": _val(r, "aircraft_type", 4) or "Unknown",
                "manufacturer": _val(r, "manufacturer", 5) or "Unknown",
                "model": _val(r, "model", 6) or "Unknown",
                "operator": _val(r, "operator", 7) or "Unknown Operator",
                "first_seen": _val(r, "first_seen", 8),
                "last_seen": _val(r, "last_seen", 9),
                "first_seen_ist": format_ist_datetime(_val(r, "first_seen", 8)),
                "last_seen_ist": format_ist_datetime(_val(r, "last_seen", 9)),
                "lifetime_visits": _val(r, "total_sessions", 10) or 0,
                "lifetime_observations": _val(r, "total_observations", 11) or 0,
                "is_enriched": bool(_val(r, "is_enriched", 12)),
            })
        if status == "known":
            out = [a for a in out if a["is_enriched"]]
        elif status == "unknown":
            out = [a for a in out if not a["is_enriched"]]
        return out
    except Exception as e:
        logger.exception("list_aircraft error: %s", e)
        return []
    finally:
        conn.close()


def aircraft_detail(id_or_hex: Any) -> Optional[Dict[str, Any]]:
    conn = db.connect()
    cur = conn.cursor()
    ph = db.placeholder
    try:
        key = str(id_or_hex).strip()
        # A 6-char alphanumeric token is an ICAO hex, even if it is all digits.
        is_hex = len(key) == 6 and all(c in "0123456789abcdefABCDEF" for c in key)
        row = None
        if is_hex:
            cur.execute(f"SELECT id FROM aircraft WHERE lower(icao_hex) = lower({ph})", (key,))
            row = cur.fetchone()
        if row is None and key.isdigit():
            cur.execute(f"SELECT id FROM aircraft WHERE id = {ph}", (int(key),))
            row = cur.fetchone()
        if not row:
            return None
        ac_id = _val(row, "id", 0)

        cur.execute(f"SELECT * FROM aircraft WHERE id = {ph}", (ac_id,))
        a = cur.fetchone()
        cur.execute(f"SELECT * FROM aircraft_enrichment WHERE aircraft_id = {ph}", (ac_id,))
        e = cur.fetchone()

        cur.execute(
            f"""SELECT id, started_at, last_observed_at, ended_at, observation_count,
                  first_distance_km, first_bearing, last_distance_km, last_bearing,
                  origin_iata, origin_icao, destination_iata, destination_icao,
                  origin_name, origin_city, origin_country,
                  destination_name, destination_city, destination_country
                  FROM detection_sessions WHERE aircraft_id = {ph}
                  ORDER BY started_at DESC LIMIT 100""", (ac_id,))
        sessions = []
        for r in cur.fetchall():
            s, en = _val(r, "started_at", 1), _val(r, "ended_at", 3)
            dur = None
            if s and en:
                try:
                    dur = (datetime.fromisoformat(str(en).replace("Z", "+00:00")) -
                           datetime.fromisoformat(str(s).replace("Z", "+00:00"))).total_seconds()
                except Exception:
                    pass
            sessions.append({
                "id": _val(r, "id", 0),
                "started_at": s,
                "started_at_ist": format_ist_datetime(s),
                "last_observed_at": _val(r, "last_observed_at", 2),
                "ended_at": en,
                "ended_at_ist": format_ist_datetime(en) if en else "Active",
                "duration": format_duration(dur) if dur is not None else "Active",
                "observation_count": _val(r, "observation_count", 4) or 1,
                "first_distance_km": _val(r, "first_distance_km", 5),
                "first_bearing": _val(r, "first_bearing", 6),
                "last_distance_km": _val(r, "last_distance_km", 7),
                "last_bearing": _val(r, "last_bearing", 8),
                "origin_iata": _val(r, "origin_iata", 9),
                "origin_icao": _val(r, "origin_icao", 10),
                "destination_iata": _val(r, "destination_iata", 11),
                "destination_icao": _val(r, "destination_icao", 12),
                "origin_name": _val(r, "origin_name", 13),
                "origin_city": _val(r, "origin_city", 14),
                "origin_country": _val(r, "origin_country", 15),
                "destination_name": _val(r, "destination_name", 16),
                "destination_city": _val(r, "destination_city", 17),
                "destination_country": _val(r, "destination_country", 18),
                "status": "COMPLETED" if en else "ACTIVE",
            })

        def gv(key, idx):
            return _val(a, key, idx) if a else None

        def ev(key):
            return (e.get(key) if isinstance(e, dict) else None) if e else None

        return {
            "id": ac_id,
            "icao_hex": gv("icao_hex", 1),
            "callsign": gv("callsign", 2) or "-",
            "registration": ev("registration") or gv("registration", 3) or gv("icao_hex", 1),
            "aircraft_type": ev("aircraft_type") or gv("aircraft_type", 4) or "Unknown",
            "manufacturer": ev("manufacturer") or gv("manufacturer", 5) or "Unknown",
            "model": ev("model") or gv("model", 6) or "Unknown",
            "operator": ev("operator_name") or gv("operator", 7) or "Unknown Operator",
            "operator_icao": ev("operator_icao"),
            "first_seen": gv("first_seen", 8),
            "last_seen": gv("last_seen", 9),
            "first_seen_ist": format_ist_datetime(gv("first_seen", 8)),
            "last_seen_ist": format_ist_datetime(gv("last_seen", 9)),
            "total_sessions": gv("total_sessions", 10) or 0,
            "total_observations": gv("total_observations", 11) or 0,
            "sessions": sessions,
        }
    except Exception as e:
        logger.exception("aircraft_detail error: %s", e)
        return None
    finally:
        conn.close()


def rare_aircraft(max_visits: int = 5) -> List[Dict[str, Any]]:
    conn = db.connect()
    cur = conn.cursor()
    ph = db.placeholder
    try:
        cur.execute(
            f"""SELECT a.icao_hex, a.callsign, a.registration, a.aircraft_type, a.operator,
                       a.first_seen, a.last_seen, a.total_sessions, a.total_observations
                FROM aircraft a WHERE a.total_sessions <= {ph}
                ORDER BY a.total_sessions ASC, a.last_seen DESC LIMIT 200""", (max_visits,))
        out = []
        for r in cur.fetchall():
            v = _val(r, "total_sessions", 7) or 1
            out.append({
                "icao_hex": _val(r, "icao_hex", 0),
                "callsign": _val(r, "callsign", 1) or "-",
                "registration": _val(r, "registration", 2) or _val(r, "icao_hex", 0),
                "aircraft_type": _val(r, "aircraft_type", 3) or "Unknown",
                "operator": _val(r, "operator", 4) or "Unknown Operator",
                "first_seen_ist": format_ist_datetime(_val(r, "first_seen", 5)),
                "last_seen_ist": format_ist_datetime(_val(r, "last_seen", 6)),
                "visits": v,
                "total_observations": _val(r, "total_observations", 8) or 0,
                "rarity": "very_rare" if v == 1 else ("rare" if v == 2 else "occasional"),
            })
        return out
    except Exception as e:
        logger.exception("rare_aircraft error: %s", e)
        return []
    finally:
        conn.close()
