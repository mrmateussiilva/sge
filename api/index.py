import os
import sys
import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vercel_backend")

API_DIR = os.path.dirname(__file__)
sys.path.insert(0, API_DIR)

from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

import database
import models
import schemas
from routers import auth, categorias, dashboard, movimentacoes, produtos, importacao_xml, tags, usuarios

logger.info("All modules imported successfully.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    DEVELOPMENT = os.getenv("DEVELOPMENT", "false").lower() == "true"
    logger.info(f"Running in {'DEVELOPMENT' if DEVELOPMENT else 'PRODUCTION'} mode.")

    critical_vars = ["DATABASE_URL", "SECRET_KEY"]
    for var in critical_vars:
        if not os.getenv(var):
            logger.warning(f"Environment variable {var} is missing!")
        else:
            logger.info(f"Environment variable {var} is configured.")

    if DEVELOPMENT:
        try:
            from database import get_engine, Base
            engine = get_engine()
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created.")
        except Exception as e:
            logger.error(f"Startup database initialization error: {e}")

    yield


app = FastAPI(
    title="Sistema de Estoque",
    version="0.1.0",
    lifespan=lifespan
)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
    "Access-Control-Allow-Headers": "*",
}


@app.middleware("http")
async def cors_and_error_middleware(request: Request, call_next):
    """
    Outermost middleware: ensures CORS headers are always present,
    even when the server returns a 500 error that bypasses CORSMiddleware.
    """
    if request.method == "OPTIONS":
        return Response(status_code=204, headers=CORS_HEADERS)

    try:
        response = await call_next(request)
        for key, value in CORS_HEADERS.items():
            response.headers[key] = value
        return response
    except Exception as exc:
        logger.error(f"Unhandled error caught in middleware: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error", "detail": str(exc)},
            headers=CORS_HEADERS,
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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
        logger.error(f"Database health check failed: {e}")
        return {"status": "error", "message": str(e)}
