from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from routers import dashboard, movimentacoes, produtos


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistema de Estoque", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(produtos.router)
app.include_router(movimentacoes.router)
app.include_router(dashboard.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "API de estoque em funcionamento."}
