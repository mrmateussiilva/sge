from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class EstoqueValuation:
    valor_conhecido: Decimal
    total_produtos_com_saldo: int
    produtos_com_custo: int
    produtos_sem_custo: int

    @property
    def calculo_completo(self):
        return self.produtos_sem_custo == 0


def calcular_valor_estoque(produtos):
    valor = Decimal('0.00')
    total_com_saldo = 0
    com_custo = 0
    sem_custo = 0
    for produto in produtos:
        if produto.quantidade_base <= 0:
            continue
        total_com_saldo += 1
        if produto.preco_custo is None:
            sem_custo += 1
            continue
        com_custo += 1
        valor += produto.quantidade_base * produto.preco_custo
    return EstoqueValuation(
        valor_conhecido=valor,
        total_produtos_com_saldo=total_com_saldo,
        produtos_com_custo=com_custo,
        produtos_sem_custo=sem_custo,
    )
