from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TipoMovimentacao = Literal["entrada", "saida", "ajuste"]


class ProdutoBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=150)
    sku: str = Field(..., min_length=1, max_length=80)
    categoria: str | None = Field(default=None, max_length=100)
    unidade: str = Field(..., min_length=1, max_length=30)
    custo: Decimal = Field(..., ge=0)
    preco: Decimal = Field(..., ge=0)
    estoque_atual: int = Field(default=0, ge=0)
    estoque_minimo: int = Field(default=0, ge=0)
    localizacao: str | None = Field(default=None, max_length=100)


class ProdutoCreate(ProdutoBase):
    pass


class ProdutoUpdate(ProdutoBase):
    pass


class ProdutoResponse(ProdutoBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MovimentacaoBase(BaseModel):
    produto_id: int = Field(..., gt=0)
    tipo: TipoMovimentacao
    quantidade: int = Field(..., ge=0)
    motivo: str | None = Field(default=None, max_length=255)


class MovimentacaoCreate(MovimentacaoBase):
    pass


class MovimentacaoResponse(MovimentacaoBase):
    id: int
    created_at: datetime
    produto: ProdutoResponse

    model_config = ConfigDict(from_attributes=True)


class DashboardResponse(BaseModel):
    total_produtos: int
    produtos_com_estoque_baixo: list[ProdutoResponse]
    ultimas_movimentacoes: list[MovimentacaoResponse]
