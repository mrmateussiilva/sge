from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Produto(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    categoria: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unidade: Mapped[str] = mapped_column(String(30), nullable=False)
    custo: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    preco: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    estoque_atual: Mapped[int] = mapped_column(nullable=False, default=0)
    estoque_minimo: Mapped[int] = mapped_column(nullable=False, default=0)
    localizacao: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    movimentacoes: Mapped[list["Movimentacao"]] = relationship(
        back_populates="produto",
        cascade="all, delete-orphan",
    )


class Movimentacao(Base):
    __tablename__ = "movimentacoes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    quantidade: Mapped[int] = mapped_column(nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    produto: Mapped["Produto"] = relationship(back_populates="movimentacoes")
