from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from web.routers import api
from web.routers import dashboard
from web.routers import settings
from web.routers import ws

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="SkyAlert Aviation Intelligence & Fixed Station Monitoring",
    description="Fixed-location ADS-B aircraft monitoring, analytics, and intelligence platform.",
    version="3.0"
)

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static"
)

# API router
app.include_router(api.router)

# Dashboard / Web Views router
app.include_router(dashboard.router)

# Settings router
app.include_router(settings.router)

# WebSocket router
app.include_router(ws.router)
