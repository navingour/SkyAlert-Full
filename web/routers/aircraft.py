import sqlite3
from pathlib import Path

import requests

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from web.services.config_manager import config_manager


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_FILE = BASE_DIR / "data" / "aircraft.db"

router = APIRouter()


@router.get("/api/aircraft")
async def aircraft():

    config = config_manager.load()

    url = config["tar1090"]["url"]

    try:

        response = requests.get(
            url,
            timeout=5
        )

        response.raise_for_status()

        data = response.json()

        live_aircraft = data.get("aircraft", [])

        if not live_aircraft:

            return JSONResponse([])


        # -------------------------------------------------
        # Get aircraft information from local database
        # -------------------------------------------------

        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row

        enriched = []

        for aircraft in live_aircraft:

            hex_code = aircraft.get("hex")

            model_code = None
            model_name = None
            registration = None

            if hex_code:

                row = conn.execute(
                    """
                    SELECT
                        registration,
                        model_code,
                        model_name
                    FROM aircraft
                    WHERE lower(hex) = lower(?)
                    LIMIT 1
                    """,
                    (hex_code,)
                ).fetchone()

                if row:

                    registration = row["registration"]
                    model_code = row["model_code"]
                    model_name = row["model_name"]


            # -------------------------------------------------
            # Aircraft type
            # -------------------------------------------------

            aircraft_type = (
                model_code
                or model_name
                or aircraft.get("t")
                or aircraft.get("type")
                or "Unknown"
            )


            # -------------------------------------------------
            # Speed
            #
            # tar1090 "gs" = ground speed in knots
            # Convert knots -> km/h
            # -------------------------------------------------

            speed_kmh = None

            if aircraft.get("gs") is not None:

                try:

                    speed_kmh = round(
                        float(aircraft["gs"]) * 1.852
                    )

                except (ValueError, TypeError):

                    speed_kmh = None


            # -------------------------------------------------
            # Altitude
            #
            # alt_baro is normally feet
            # -------------------------------------------------

            altitude_ft = aircraft.get("alt_baro")

            if isinstance(altitude_ft, (int, float)):

                altitude_ft = round(altitude_ft)


            # -------------------------------------------------
            # Build response
            # -------------------------------------------------

            enriched.append(
                {
                    **aircraft,

                    "registration": (
                        registration
                        or aircraft.get("registration")
                        or aircraft.get("r")
                        or "-"
                    ),

                    "aircraft_type": aircraft_type,

                    "speed_kmh": speed_kmh,

                    "altitude_ft": altitude_ft
                }
            )


        conn.close()

        return JSONResponse(enriched)


    except Exception as e:

        return JSONResponse(
            {
                "error": str(e)
            },
            status_code=500
        )
