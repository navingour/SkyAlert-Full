# SkyAlert Standalone Backend

A single-service Debian backend that records live ADS-B data from tar1090/readsb
into a relational SQL database, enriches it with aircraft identity and full flight
routes (adsbdb.com, with airport/city/country names), and serves the API + HTML
surface consumed by the existing SkyAlert frontend.

## What it does

- **Collects** live aircraft from a tar1090 `aircraft.json` feed.
- **Records** aircraft, detection sessions (visits), observations, and alerts.
- **Enriches** each new detection session with a full route
  (`origin_iata/icao/name/city/country`, `destination_*`) via adsbdb.com.
- **Enriches** unknown airframes with registration/type/operator.
- **Serves** a clean JSON API plus the HTML compatibility pages the current
  frontend already reads — so the frontend works unchanged.
- **SkyLink (RapidAPI)** is supported as an optional enrichment provider.

### Enrichment providers

**adsbdb.com** (default, free, no key):
- `GET /aircraft/{mode_s}` — identity
- `GET /aircraft/{mode_s}?callsign={cs}` — identity + route in one call
- `GET /callsign/{callsign}` — route with full airport/city/country names
- `GET /airline/{icao_or_iata}` — airline name/codes
- `GET /n-number/{reg}` and `/mode-s/{mode_s}` — registration ↔ hex conversion
- `GET /online` — status

**SkyLink (RapidAPI)** (optional, set `providers.skylink.api_key`):
- `GET /v3/adsb/aircraft` with filters (`icao24`, `registration`, `callsign`,
  `airline`, `lat,lon,radius`, `bbox`, altitude/speed ranges)
- `GET /v3/adsb/aircraft/{icao24}` — single aircraft detail (with `photo_url`)
- `GET /v3/adsb/aircraft/statistics` — coverage metrics

## Database

- **SQLite by default** (zero config): `data/skyalert_relational.db`.
- **PostgreSQL**: set `DATABASE_URL=postgresql://user:pass@host:5432/db`.

The schema is created automatically on first run.

## Install on Debian

```bash
sudo bash install.sh
```

This creates `/opt/skyalert-backend`, a virtualenv, installs dependencies, and
enables + starts the `skyalert-backend` systemd service on port **8091**.

## Point it at your live data

Edit `config/config.yaml` **before** install (or edit `/opt/skyalert-backend/config/config.yaml` after):

```yaml
tar1090:
  url: "http://127.0.0.1/tar1090/data/aircraft.json"
station:
  latitude: 22.5726
  longitude: 88.3639
```

Then `sudo systemctl restart skyalert-backend`.

## Import your existing recording

**SQLite (current Mac/local recording):**

```bash
sudo -u skyalert /opt/skyalert-backend/venv/bin/python \
  -m importer.import_sqlite /path/to/old/skyalert_relational.db
```

**PostgreSQL (current Debian recording):**

```bash
cd /opt/skyalert-backend
DATABASE_URL="postgresql://user:pass@127.0.0.1:5432/skyalert_new" \
OLD_DATABASE_URL="postgresql://user:pass@127.0.0.1:5432/skyalert" \
venv/bin/python -m importer.import_postgres
```

Importers are idempotent — they skip aircraft/sessions that already exist.

## Frontend integration (with fallback)

The existing frontend reads its data source from `skyalert_api.url` in
`config/config.yaml`. Point it at this new backend:

```yaml
skyalert_api:
  url: "http://127.0.0.1:8091/api"
```

If the new backend is unreachable, the frontend falls back to the previously
configured Debian backend automatically.

## API surface

| Endpoint | Description |
|---|---|
| `GET /api/dashboard` | KPI summary |
| `GET /api/live-aircraft` | Live feed `{live, identity}` per aircraft |
| `GET /api/rare-aircraft?max_visits=N` | Rare aircraft |
| `GET /api/status` | Service + collector status |
| `GET /skyalert/` | HTML aircraft list (compat) |
| `GET /skyalert/aircraft/{id}` | HTML aircraft detail + sessions (compat) |
