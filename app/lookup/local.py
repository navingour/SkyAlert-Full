from app.aircraft_database import aircraft_db


class LocalLookup:

    def lookup(self, hex_code):

        row = aircraft_db.conn.execute(
            """
            SELECT
                registration,
                model_code,
                model_name,
                production_line,
                owner
            FROM aircraft
            WHERE hex=?
            """,
            (hex_code.upper(),)
        ).fetchone()

        if not row:
            return None

        return {
            "Registration": row[0],
            "ICAOTypeCode": row[1],
            "Type": row[2],
            "Manufacturer": row[3],
            "RegisteredOwners": row[4]
        }


local_lookup = LocalLookup()
