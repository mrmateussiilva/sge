from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil: Mapped[str] = mapped_column(String(50), nullable=False, default="operador")
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Categoria(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    produtos: Mapped[list["Produto"]] = relationship(back_populates="categoria_obj")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    cor: Mapped[str | None] = mapped_column(String(7), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    produtos: Mapped[list["Produto"]] = relationship(back_populates="tag_obj")


class Produto(Base):
    __tablename__ = "produtos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    nome: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categorias.id"), nullable=True)
    tag_id: Mapped[int | None] = mapped_column(ForeignKey("tags.id"), nullable=True)
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
    categoria_obj: Mapped["Categoria | None"] = relationship(back_populates="produtos")
    tag_obj: Mapped["Tag | None"] = relationship(back_populates="produtos")


class Movimentacao(Base):
    __tablename__ = "movimentacoes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"), nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    quantidade: Mapped[int] = mapped_column(nullable=False)
    motivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    produto: Mapped["Produto"] = relationship(back_populates="movimentacoes")


class NotaImportada(Base):
    __tablename__ = "notas_importadas"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chave_acesso: Mapped[str] = mapped_column(String(44), nullable=False, unique=True, index=True)
    numero_nota: Mapped[str] = mapped_column(String(20), nullable=False)
    serie: Mapped[str] = mapped_column(String(10), nullable=False)
    fornecedor_nome: Mapped[str] = mapped_column(String(150), nullable=False)
    fornecedor_cnpj: Mapped[str] = mapped_column(String(20), nullable=False)
    valor_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    data_emissao: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
