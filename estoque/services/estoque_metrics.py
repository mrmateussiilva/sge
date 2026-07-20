from collections import OrderedDict
from decimal import Decimal

from django.db.models import Count, Sum

from .units import UNIDADES, unidade_base_codigo


def agrupar_quantidade_por_unidade(itens, quantidade_attr='quantidade', produto_attr='produto'):
    totais = OrderedDict()
    for item in itens:
        produto = getattr(item, produto_attr)
        codigo = unidade_base_codigo(produto)
        totais[codigo] = totais.get(codigo, Decimal('0.00')) + getattr(item, quantidade_attr)
    return totais


def totais_movimentacao_por_unidade(movs):
    return {
        'ENTRADA': agrupar_quantidade_por_unidade(movs.filter(tipo='ENTRADA')),
        'SAIDA': agrupar_quantidade_por_unidade(movs.filter(tipo='SAIDA')),
    }


def contadores_por_tipo(qs):
    return qs.values('tipo_produto').annotate(total=Count('id')).order_by('tipo_produto')


def saldo_produtos_por_unidade(produtos):
    totais = OrderedDict()
    for produto in produtos:
        codigo = unidade_base_codigo(produto)
        totais[codigo] = totais.get(codigo, Decimal('0.00')) + produto.quantidade_base
    return totais


def serializar_totais_unidade(totais):
    return [
        {
            'codigo': codigo,
            'simbolo': UNIDADES.get(codigo, UNIDADES['OUTRO']).simbolo,
            'quantidade': valor,
        }
        for codigo, valor in totais.items()
    ]


def valor_por_tipo(produtos):
    dados = OrderedDict()
    for produto in produtos:
        if produto.preco_custo is None:
            continue
        dados[produto.tipo_produto] = dados.get(produto.tipo_produto, Decimal('0.00')) + (produto.quantidade_base * produto.preco_custo)
    return dados
