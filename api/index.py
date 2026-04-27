import os
import sys
import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vercel_backend")

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text


def safe_import_modules():
    from database import Base, SessionLocal
    try:
        import models
    except Exception as e:
        logger.warning(f"Could not import models: {e}")

    try:
        import schemas
    except Exception as e:
        logger.warning(f"Could not import schemas: {e}")

    try:
        from routers import auth, dashboard, movimentacoes, produtos, importacao_xml, usuarios
        return auth, dashboard, movimentacoes, produtos, importacao_xml, usuarios
    except Exception as e:
        logger.error(f"Error importing routers: {e}")
        raise


routers = safe_import_modules()
auth, dashboard, movimentacoes, produtos, importacao_xml, usuarios = routers


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
            from database import get_engine
            from database import Base
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
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
        from database import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "error", "message": str(e)}
