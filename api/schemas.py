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
    estoque_atual: int = Field(default=0, ge=0, strict=True)
    estoque_minimo: int = Field(default=0, ge=0, strict=True)
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
    produto_id: int = Field(..., gt=0, strict=True)
    tipo: TipoMovimentacao
    quantidade: int = Field(..., ge=1, strict=True)
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


class UsuarioBase(BaseModel):
    nome: str = Field(..., min_length=1, max_length=150)
    email: str = Field(..., min_length=5, max_length=150)
    perfil: str = Field(default="operador", min_length=1, max_length=50)


class UsuarioCreate(UsuarioBase):
    senha: str = Field(..., min_length=6, max_length=128)


class UsuarioLogin(BaseModel):
    email: str = Field(..., min_length=5, max_length=150)
    senha: str = Field(..., min_length=1, max_length=128)


class UsuarioResponse(UsuarioBase):
    id: int
    ativo: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    usuario: UsuarioResponse

class NotaMeta(BaseModel):
    numero_nota: str
    serie: str
    chave_acesso: str
    data_emissao: str | None = None
    fornecedor_nome: str
    fornecedor_cnpj: str
    valor_total: float

class XmlProduto(BaseModel):
    codigo: str
    descricao: str
    ncm: str | None = None
    cfop: str | None = None
    unidade: str
    quantidade: float
    valor_unitario: float
    valor_total: float
    status: str | None = None

class PreviewXmlResponse(BaseModel):
    nota: NotaMeta
    produtos: list[XmlProduto]

class ConfirmarImportacaoPayload(BaseModel):
    nota: NotaMeta
    produtos: list[XmlProduto]
