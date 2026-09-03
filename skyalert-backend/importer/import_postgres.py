"""Import from the existing Debian PostgreSQL database into the new database.

Usage:
    DATABASE_URL=postgresql://new_db_url \
    OLD_DATABASE_URL=postgresql://old_db_url \
    python -m importer.import_postgres
"""
import os
import logging

import psycopg2
import psycopg2.extras

from app.db import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("importer.postgres")

ROUTE_COLS = ["origin_iata", "origin_icao", "destination_iata", "destination_icao",
              "origin_name", "origin_city", "origin_country",
              "destination_name", "destination_city", "destination_country"]


def run(old_url: str):
    src = psycopg2.connect(old_url, cursor_factory=psycopg2.extras.RealDictCursor)
    scur = src.cursor()
    dst = db.connect()
    dcur = dst.cursor()
    ph = db.placeholder

    scur.execute("SELECT * FROM aircraft")
    ac_map = {}
    for r in scur.fetchall():
        dcur.execute(f"SELECT id FROM aircraft WHERE icao_hex = {ph}", (r["icao_hex"],))
        ex = dcur.fetchone()
        if ex:
            new_id = ex["id"] if isinstance(ex, dict) else ex[0]
        else:
            dcur.execute(
                f"""INSERT INTO aircraft (icao_hex, callsign, registration, aircraft_type,
                    manufacturer, model, operator, first_seen, last_seen, total_sessions,
                    total_observations, created_at, updated_at)
                    VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph},{ph})""",
                (r["icao_hex"], r.get("callsign"), r.get("registration"), r.get("aircraft_type"),
                 r.get("manufacturer"), r.get("model"), r.get("operator"), r.get("first_seen"),
                 r.get("last_seen"), r.get("total_sessions"), r.get("total_observations"),
                 r.get("created_at"), r.get("updated_at")))
            dcur.execute(f"SELECT id FROM aircraft WHERE icao_hex = {ph}", (r["icao_hex"],))
            g = dcur.fetchone()
            new_id = g["id"] if isinstance(g, dict) else g[0]
        ac_map[r["id"]] = new_id
    logger.info("aircraft imported/mapped: %d", len(ac_map))

    scur.execute("SELECT * FROM detection_sessions")
    n = 0
    cols = None
    for r in scur.fetchall():
        if cols is None:
            cols = list(r.keys())
        if r["aircraft_id"] not in ac_map:
            continue
        new_ac = ac_map[r["aircraft_id"]]
        dcur.execute(
            f"SELECT id FROM detection_sessions WHERE aircraft_id = {ph} AND started_at = {ph}",
            (new_ac, r["started_at"]))
        if dcur.fetchone():
            continue
        base = ["aircraft_id", "started_at", "last_observed_at", "ended_at", "observation_count",
                "first_distance_km", "first_bearing", "last_distance_km", "last_bearing"]
        route_present = [c for c in ROUTE_COLS if c in cols]
        ins = base + route_present
        vals = [new_ac, r["started_at"], r["last_observed_at"], r["ended_at"], r.get("observation_count"),
                r.get("first_distance_km"), r.get("first_bearing"), r.get("last_distance_km"), r.get("last_bearing")]
        vals += [r.get(c) for c in route_present]
        dcur.execute(f"INSERT INTO detection_sessions ({', '.join(ins)}) VALUES ({', '.join([ph]*len(ins))})", tuple(vals))
        n += 1
    logger.info("detection_sessions imported: %d", n)

    dst.commit()
    dst.close()
    src.close()
    logger.info("Import complete.")


if __name__ == "__main__":
    old = os.environ.get("OLD_DATABASE_URL")
    if not old:
        print("Set OLD_DATABASE_URL to the existing Debian PostgreSQL URL.")
        raise SystemExit(1)
    run(old)
