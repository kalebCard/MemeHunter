"""
meme_hunter.api.app - Factoría de Aplicación ASGI FastAPI (Cockpit v8.0).
Provee endpoints REST estructurados, WebSockets para telemetría < 5ms y servicio de archivos estáticos.
"""

from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from meme_hunter.core.config import get_settings
from meme_hunter.api.routers import system, strategies, dag, quant


def create_app() -> FastAPI:
    """Factoría de la aplicación FastAPI."""
    settings = get_settings()

    app = FastAPI(
        title="Meme Hunter Cockpit API",
        description="API Institucional ASGI para Monitoreo y Orquestación Multi-Agente",
        version="8.2.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # Middleware CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Registro de Routers
    app.include_router(system.router)
    app.include_router(strategies.router)
    app.include_router(dag.router)
    app.include_router(quant.router)

    # WebSocket para Telemetría de Baja Latencia (< 5ms)
    @app.websocket("/ws/telemetry")
    async def websocket_telemetry(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                # Esperar mensajes o transmitir latidos
                data = await websocket.receive_text()
                await websocket.send_json({
                    "type": "TELEMETRY_ACK",
                    "payload": data,
                    "status": "HEALTHY",
                })
        except WebSocketDisconnect:
            pass

    # Servir archivos estáticos del dashboard si existen
    dashboard_dir = settings.ROOT_DIR / "dashboard"
    if dashboard_dir.exists():
        app.mount("/static", StaticFiles(directory=str(dashboard_dir)), name="static")

    return app
