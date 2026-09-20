from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from .core.config import settings
from .core.database import init_db
from .services.twin.network_graph import rail_network
from .api import network, trains, twin, scenarios, simulation, conflicts, recommendations, predictions, analytics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("railoptix")

NETWORK_PATH = "scenarios/network/railoptix_network.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("RAILOPTIX starting up...")
    await init_db()
    logger.info("Database initialised.")
    rail_network.load_from_json(NETWORK_PATH)
    logger.info(f"Network loaded: {len(rail_network.get_all_nodes())} nodes, "
                f"{len(rail_network.get_all_sections())} sections, "
                f"{len(rail_network.get_all_routes())} routes.")
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("RAILOPTIX shutting down.")


app = FastAPI(
    title="RAILOPTIX API",
    description="AI-Powered Railway Traffic Control Decision Support System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(network.router)
app.include_router(trains.router)
app.include_router(twin.router)
app.include_router(scenarios.router)
app.include_router(simulation.router)
app.include_router(conflicts.router)
app.include_router(recommendations.router)
app.include_router(predictions.router)
app.include_router(analytics.router)


# ── Global error handler ─────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "error": {"code": "INTERNAL_ERROR", "message": str(exc)},
        },
    )


@app.get("/health", tags=["system"])
def health():
    return {
        "status": "ok",
        "service": "RAILOPTIX",
        "network_loaded": rail_network.is_loaded(),
        "nodes": len(rail_network.get_all_nodes()),
    }


# ── Serve Built Frontend SPA (Production) ────────────────────────────────────
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

FRONTEND_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))

if os.path.exists(FRONTEND_DIST):
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", tags=["frontend"])
    async def serve_spa(full_path: str):
        if full_path.startswith("api") or full_path in ("docs", "redoc", "openapi.json", "health"):
            return JSONResponse(status_code=404, content={"error": "Not Found"})
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        index_file = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.isfile(index_file):
            return FileResponse(index_file)
        return {"message": "RAILOPTIX API. Frontend build not found."}
else:
    @app.get("/", tags=["system"])
    def root():
        return {"message": "Welcome to RAILOPTIX API. See /docs for the full API reference."}
