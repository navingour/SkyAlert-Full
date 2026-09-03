from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import asyncio
from app.config import load_config
from app.adapters.factory import AdapterFactory
from app.core.deduplicator import AircraftDeduplicator
from app.logger import logger

router = APIRouter()


class ConnectionManager:

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)


ws_manager = ConnectionManager()


from app.db_manager import db_manager

@router.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    config = load_config()
    adapters = AdapterFactory.create_from_config(config)
    deduplicator = AircraftDeduplicator()

    try:
        while True:
            tasks = [adapter.fetch_aircraft() for adapter in adapters]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            aggregated = []
            for res in results:
                if isinstance(res, list):
                    aggregated.extend(res)

            deduped = deduplicator.deduplicate(aggregated, adapters)
            payload = []
            conn = None
            try:
                conn = db_manager.get_connection()
                cur = conn.cursor()
                for plane in deduped:
                    p_dict = plane.to_legacy_dict()
                    hex_code = (p_dict.get("hex") or p_dict.get("icao_hex") or "").upper()
                    if hex_code:
                        cur.execute(
                            """
                            SELECT ds.origin_iata, ds.origin_icao, ds.destination_iata, ds.destination_icao
                            FROM detection_sessions ds
                            JOIN aircraft a ON ds.aircraft_id = a.id
                            WHERE a.icao_hex = ? AND ds.ended_at IS NULL LIMIT 1
                            """,
                            (hex_code,)
                        )
                        r_row = cur.fetchone()
                        if r_row:
                            r_o_iata = r_row[0] if isinstance(r_row, (tuple, list)) else r_row["origin_iata"]
                            r_o_icao = r_row[1] if isinstance(r_row, (tuple, list)) else r_row["origin_icao"]
                            r_d_iata = r_row[2] if isinstance(r_row, (tuple, list)) else r_row["destination_iata"]
                            r_d_icao = r_row[3] if isinstance(r_row, (tuple, list)) else r_row["destination_icao"]
                            if r_o_iata or r_o_icao or r_d_iata or r_d_icao:
                                p_dict["route"] = {
                                    "origin_iata": r_o_iata,
                                    "origin_icao": r_o_icao,
                                    "destination_iata": r_d_iata,
                                    "destination_icao": r_d_icao
                                }
                    payload.append(p_dict)
            finally:
                if conn:
                    try: conn.close()
                    except Exception: pass

            await websocket.send_json(payload)
            await asyncio.sleep(2)

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning("WebSocket stream disconnected: %s", e)
        ws_manager.disconnect(websocket)
