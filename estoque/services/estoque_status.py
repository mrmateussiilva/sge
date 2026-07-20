from dataclasses import dataclass

from django.db.models import F, Q


ZERADO = 'ZERADO'
BAIXO = 'BAIXO'
SEM_MINIMO = 'SEM_MINIMO'
NORMAL = 'NORMAL'


@dataclass(frozen=True)
class EstoqueStatus:
    codigo: str
    label: str


def classificar_estoque(produto):
    quantidade = produto.quantidade_base
    minimo = produto.estoque_minimo
    if quantidade <= 0:
        return EstoqueStatus(ZERADO, 'Zerado')
    if minimo is None or minimo <= 0:
        return EstoqueStatus(SEM_MINIMO, 'Sem mínimo')
    if quantidade <= minimo:
        return EstoqueStatus(BAIXO, 'Baixo')
    return EstoqueStatus(NORMAL, 'Normal')


def filtro_zerado():
    return Q(quantidade_base__lte=0)


def filtro_baixo():
    return Q(quantidade_base__gt=0, estoque_minimo__isnull=False, estoque_minimo__gt=0, quantidade_base__lte=F('estoque_minimo'))


def filtro_sem_minimo():
    return Q(quantidade_base__gt=0) & (Q(estoque_minimo__isnull=True) | Q(estoque_minimo__lte=0))


def filtro_normal():
    return Q(quantidade_base__gt=F('estoque_minimo'), estoque_minimo__isnull=False, estoque_minimo__gt=0)
