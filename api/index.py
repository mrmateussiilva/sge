import os
import sys
import logging
from contextlib import asynccontextmanager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vercel_backend")

# Add current directory to sys.path
sys.path.append(os.path.dirname(__file__))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

try:
    import auth as auth_service
    import models
    import schemas
    from database import Base, SessionLocal, engine, DATABASE_URL
    from routers import auth, dashboard, movimentacoes, produtos, importacao_xml
    logger.info("Internal modules imported successfully.")
except Exception as e:
    logger.error(f"Error importing internal modules: {e}")
    raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Safe startup tasks
    DEVELOPMENT = os.getenv("DEVELOPMENT", "false").lower() == "true"
    logger.info(f"Running in {'DEVELOPMENT' if DEVELOPMENT else 'PRODUCTION'} mode.")
    
    # Check for critical env vars
    critical_vars = ["DATABASE_URL", "SECRET_KEY"]
    for var in critical_vars:
        if not os.getenv(var):
            logger.warning(f"Environment variable {var} is missing!")
        else:
            logger.info(f"Environment variable {var} is configured.")

    # Initialize DB (carefully)
    try:
        # We only run create_all in dev or if explicitly requested via env for safety
        if DEVELOPMENT:
            logger.info("Development mode: Creating database tables if needed...")
            Base.metadata.create_all(bind=engine)
            
            db = SessionLocal()
            try:
                admin_email = "admin@local"
                admin_user = auth_service.get_usuario_by_email(db, admin_email)
                if admin_user is None:
                    auth_service.create_usuario(
                        db,
                        schemas.UsuarioCreate(
                            nome="Administrador",
                            email=admin_email,
                            senha="admin1234",
                            perfil="admin",
                        ),
                    )
                    logger.info("Admin user seeded.")
            finally:
                db.close()
    except Exception as e:
        logger.error(f"Startup database initialization error: {e}")
    
    yield

app = FastAPI(
    title="Sistema de Estoque", 
    version="0.1.0",
    root_path="/api" if os.getenv("VERCEL") else "",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(produtos.router)
app.include_router(movimentacoes.router)
app.include_router(dashboard.router)
app.include_router(importacao_xml.router)

@app.get("/api")
def root():
    return {"message": "API de estoque em funcionamento no Vercel.", "environment": "Vercel" if os.getenv("VERCEL") else "Local"}

@app.get("/health")
def health():
    return {
        "status": "ok",
        "database_url_configured": bool(os.getenv("DATABASE_URL")),
        "secret_key_configured": bool(os.getenv("SECRET_KEY")),
        "vercel_env": bool(os.getenv("VERCEL"))
    }

@app.get("/health/db")
def health_db():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "error", "message": str(e)}, 500
