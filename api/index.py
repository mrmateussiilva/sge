import os
import sys
import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vercel_backend")

API_DIR = os.path.dirname(__file__)
sys.path.insert(0, API_DIR)

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

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

class CorsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            response = Response(status_code=200)
        else:
            response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS,PATCH"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(CorsMiddleware)

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
        from sqlalchemy.orm import Session
        session: Session = next(get_engine().connect().execution_options(auto_commit=True))
        session.execute(text("SELECT 1"))
        session.close()
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "error", "message": str(e)}
