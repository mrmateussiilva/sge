import os
import sys
import logging
from contextlib import asynccontextmanager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vercel_backend")

# Robust sys.path setup
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

import database
import models
import schemas
from routers import auth, categorias, dashboard, movimentacoes, produtos, importacao_xml, tags, usuarios

logger.info("Modules imported successfully.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Only run DB init in development and if explicitly requested
    if os.getenv("DEVELOPMENT", "false").lower() == "true":
        try:
            from database import get_engine, Base
            engine = get_engine()
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables verified/created.")
        except Exception as e:
            logger.error(f"Lifespan DB error: {e}")
    yield

app = FastAPI(
    title="Sistema de Estoque",
    version="0.1.0",
    lifespan=lifespan
)

# Standard CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler to ensure CORS on 500 errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global Error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc)},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )

app.include_router(auth.router, prefix="/api")
app.include_router(categorias.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(produtos.router, prefix="/api")
app.include_router(movimentacoes.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(importacao_xml.router, prefix="/api")
app.include_router(usuarios.router, prefix="/api")

@app.get("/api")
def root():
    return {
        "message": "API de estoque em funcionamento.",
        "environment": "Vercel" if os.getenv("VERCEL") else "Local"
    }

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "environment": "Vercel" if os.getenv("VERCEL") else "Local",
        "database_url_configured": bool(os.getenv("DATABASE_URL")),
    }

@app.get("/api/health/db")
def health_db():
    try:
        from database import get_engine
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        return {"status": "error", "message": str(e)}
