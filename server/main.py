"""
main.py — Application entry point.

╔══════════════════════════════════════════════════════════════╗
║  THIS FILE IS COMPLETE — you do not need to change anything. ║
╚══════════════════════════════════════════════════════════════╝

This file does three things only:
  1. Creates the FastAPI app
  2. Sets up logging
  3. Registers the router from routes.py

All actual route logic lives in routes.py.
This separation is the standard pattern in production FastAPI projects.

HOW TO RUN:
  uvicorn server.main:app --reload

  Then open: http://localhost:8000/docs
"""

import logging
from contextlib import asynccontextmanager
from .broadcaster import broadcaster
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from .models import create_tables
from .routes import router

GUI_DIR = Path(__file__).parent.parent / "gui"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="Secure Messenger — Stage 1",
    description="Authenticated, encrypted REST API for private messaging",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)
app.mount("/gui", StaticFiles(directory=GUI_DIR), name="gui")

@app.get("/")
def index():
    return FileResponse(GUI_DIR / "index.html")
