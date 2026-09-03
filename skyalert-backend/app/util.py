import math
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

IST_TZ = timezone(timedelta(hours=5, minutes=30))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def format_ist_datetime(dt_val: Any) -> str:
    if not dt_val:
        return datetime.now(IST_TZ).strftime("%d %b %H:%M IST")
    try:
        if isinstance(dt_val, str):
            dt = datetime.fromisoformat(dt_val.replace("Z", "+00:00"))
        else:
            dt = dt_val
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST_TZ).strftime("%d %b %H:%M IST")
    except Exception:
        return str(dt_val)


def format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "< 1m"
    try:
        s = int(max(0, seconds))
    except Exception:
        return "< 1m"
    if s < 60:
        return "< 1m"
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    if d:
        return f"{d}d {h}h"
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


def haversine_km(lat1, lon1, lat2, lon2) -> Optional[float]:
    try:
        lat1, lon1, lat2, lon2 = map(float, (lat1, lon1, lat2, lon2))
    except (TypeError, ValueError):
        return None
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return round(6371 * 2 * math.asin(math.sqrt(a)), 2)


def bearing_deg(lat1, lon1, lat2, lon2) -> Optional[float]:
    try:
        lat1, lon1, lat2, lon2 = map(float, (lat1, lon1, lat2, lon2))
    except (TypeError, ValueError):
        return None
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(math.radians(lat2))
    y = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - \
        math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dlon)
    return round((math.degrees(math.atan2(x, y)) + 360) % 360, 1)
