"""Import existing SkyAlert recording (SQLite skyalert_relational.db) into the
new standalone database. Safe to re-run: skips existing ICAO hex and session ids.

Usage:
    python -m importer.import_sqlite /path/to/old/skyalert_relational.db
"""
import sqlite3
import sys
import logging

from app.db import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("importer.sqlite")

ROUTE_COLS = ["origin_iata", "origin_icao", "destination_iata", "destination_icao",
              "origin_name", "origin_city", "origin_country",
              "destination_name", "destination_city", "destination_country"]


def _cols(src, table):
    return [r[1] for r in src.execute(f"PRAGMA table_info({table})").fetchall()]


def run(old_path: str):
    src = sqlite3.connect(old_path)
    src.row_factory = sqlite3.Row
    dst = db.connect()
    dcur = dst.cursor()
    ph = db.placeholder

    # aircraft id mapping old->new
    ac_map = {}
    for r in src.execute("SELECT * FROM aircraft").fetchall():
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
                (r["icao_hex"], r["callsign"], r["registration"], r["aircraft_type"],
                 r["manufacturer"], r["model"], r["operator"], r["first_seen"], r["last_seen"],
                 r["total_sessions"], r["total_observations"], r["created_at"], r["updated_at"]))
            dcur.execute(f"SELECT id FROM aircraft WHERE icao_hex = {ph}", (r["icao_hex"],))
            e2 = dcur.fetchone()
            new_id = e2["id"] if isinstance(e2, dict) else e2[0]
        ac_map[r["id"]] = new_id
    logger.info("aircraft imported/mapped: %d", len(ac_map))

    # enrichment
    try:
        enr_cols = _cols(src, "aircraft_enrichment")
        n = 0
        for r in src.execute("SELECT * FROM aircraft_enrichment").fetchall():
            old_ac = r["aircraft_id"]
            if old_ac not in ac_map:
                continue
            new_ac = ac_map[old_ac]
            dcur.execute(f"SELECT id FROM aircraft_enrichment WHERE aircraft_id = {ph}", (new_ac,))
            if dcur.fetchone():
                continue
            fields = [c for c in enr_cols if c not in ("id", "aircraft_id")]
            vals = [r[c] for c in fields]
            dcur.execute(
                f"INSERT INTO aircraft_enrichment (aircraft_id, {', '.join(fields)}) VALUES ({ph}, {', '.join([ph]*len(fields))})",
                (new_ac, *vals))
            n += 1
        logger.info("enrichment imported: %d", n)
    except Exception as e:
        logger.warning("enrichment import skipped: %s", e)

    # detection_sessions
    sess_cols = _cols(src, "detection_sessions")
    sess_map = {}
    route_present = [c for c in ROUTE_COLS if c in sess_cols]
    n = 0
    for r in src.execute("SELECT * FROM detection_sessions").fetchall():
        old_ac = r["aircraft_id"]
        if old_ac not in ac_map:
            continue
        new_ac = ac_map[old_ac]
        # skip if identical session already imported (same aircraft + started_at)
        dcur.execute(
            f"SELECT id FROM detection_sessions WHERE aircraft_id = {ph} AND started_at = {ph}",
            (new_ac, r["started_at"]))
        if dcur.fetchone():
            continue
        base = ["aircraft_id", "started_at", "last_observed_at", "ended_at", "observation_count",
                "first_distance_km", "first_bearing", "last_distance_km", "last_bearing"]
        cols = base + route_present
        vals = [new_ac, r["started_at"], r["last_observed_at"], r["ended_at"], r["observation_count"],
                r["first_distance_km"], r["first_bearing"], r["last_distance_km"], r["last_bearing"]]
        vals += [r[c] for c in route_present]
        dcur.execute(
            f"INSERT INTO detection_sessions ({', '.join(cols)}) VALUES ({', '.join([ph]*len(cols))})",
            tuple(vals))
        dcur.execute(
            f"SELECT id FROM detection_sessions WHERE aircraft_id = {ph} AND started_at = {ph}",
            (new_ac, r["started_at"]))
        g = dcur.fetchone()
        sess_map[r["id"]] = g["id"] if isinstance(g, dict) else g[0]
        n += 1
    logger.info("detection_sessions imported: %d", n)

    # observations
    try:
        obs_cols = _cols(src, "observations")
        n = 0
        for r in src.execute("SELECT * FROM observations").fetchall():
            old_ac = r["aircraft_id"]
            if old_ac not in ac_map:
                continue
            new_ac = ac_map[old_ac]
            new_sess = sess_map.get(r["session_id"])
            fields = ["aircraft_id", "session_id", "timestamp", "altitude_baro", "altitude_geom",
                      "ground_speed", "track", "latitude", "longitude", "vertical_rate", "squawk",
                      "distance_km", "bearing", "raw_data", "created_at"]
            fields = [f for f in fields if f in obs_cols]
            vals = []
            for f in fields:
                if f == "aircraft_id":
                    vals.append(new_ac)
                elif f == "session_id":
                    vals.append(new_sess)
                else:
                    vals.append(r[f])
            dcur.execute(
                f"INSERT INTO observations ({', '.join(fields)}) VALUES ({', '.join([ph]*len(fields))})",
                tuple(vals))
            n += 1
        logger.info("observations imported: %d", n)
    except Exception as e:
        logger.warning("observations import skipped: %s", e)

    dst.commit()
    dst.close()
    src.close()
    logger.info("Import complete.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m importer.import_sqlite /path/to/old/skyalert_relational.db")
        sys.exit(1)
    run(sys.argv[1])
