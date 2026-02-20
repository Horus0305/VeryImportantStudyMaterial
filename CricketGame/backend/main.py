"""
E - Cricket Tournament — FastAPI Backend
==============================================
Modularized main application entry point.
"""
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from .core.config import HOST, PORT, CORS_ORIGINS_LIST
from .data.database import init_db, start_learning_processor, stop_learning_processor

# Import the new modular routers
from .api.auth import router as auth_router
from .api.rooms import router as rooms_router
from .api.stats import router as stats_router
from .api.ws import router as ws_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_learning_processor()
    print("🏏 Cricket Server ready!")
    yield
    stop_learning_processor()

app = FastAPI(title="Cricket Game API", lifespan=lifespan)

# Setup CORS - dynamically add FRONTEND_URL if provided
allowed_origins = list(CORS_ORIGINS_LIST)
frontend_url = os.environ.get("FRONTEND_URL")
if frontend_url and frontend_url not in allowed_origins:
    allowed_origins.append(frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(rooms_router)
app.include_router(stats_router)
app.include_router(ws_router)

if __name__ == "__main__":
    # No --reload to prevent match interruption
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=False)
