import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import auth as auth_service
import models
import schemas
from database import Base, SessionLocal, engine
from routers import auth, dashboard, movimentacoes, produtos


Base.metadata.create_all(bind=engine)
DEVELOPMENT = os.getenv("DEVELOPMENT", "true").lower() == "true"


def seed_admin_user() -> None:
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
    finally:
        db.close()


if DEVELOPMENT:
    seed_admin_user()

app = FastAPI(title="Sistema de Estoque", version="0.1.0")

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


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "API de estoque em funcionamento."}
