import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from ..models import LogAcao, Movimentacao, Produto
from ..services.estoque_metrics import valor_por_tipo
from ..services.estoque_status import filtro_baixo, filtro_zerado
from ..services.estoque_valuation import calcular_valor_estoque
from ..services.units import dinheiro_br


@login_required
def dashboard(request):
    produtos_base = Produto.objects.select_related('fornecedor').all()
    produtos_lista = list(produtos_base)
    total_itens = len(produtos_lista)
    estoque_zerado_count = Produto.objects.filter(filtro_zerado()).count()
    estoque_baixo = Produto.objects.filter(filtro_baixo()).select_related('fornecedor')
    valuation = calcular_valor_estoque(produtos_lista)
    ultimas_movimentacoes = Movimentacao.objects.select_related('produto', 'usuario').order_by('-data')[:5]

    hoje = timezone.now()
    ano_atual = hoje.year
    try:
        ano_selecionado = int(request.GET.get('ano', ano_atual))
    except ValueError:
        ano_selecionado = ano_atual

    anos_disponiveis = list(Movimentacao.objects.dates('data', 'year', order='DESC'))
    anos = sorted(list(set([a.year for a in anos_disponiveis] + [ano_atual])), reverse=True)
    
    meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    entradas_meses = []
    saidas_meses = []
    for m in range(1, 13):
        entradas = Movimentacao.objects.filter(
            tipo='ENTRADA', data__year=ano_selecionado, data__month=m
        ).count()
        saidas = Movimentacao.objects.filter(
            tipo='SAIDA', data__year=ano_selecionado, data__month=m
        ).count()
        entradas_meses.append(entradas)
        saidas_meses.append(saidas)

    if request.GET.get('ajax') == '1':
        return JsonResponse({
            'meses': meses_nomes,
            'entradas': entradas_meses,
            'saidas': saidas_meses,
        })

    valores_por_tipo = valor_por_tipo(produtos_lista)
    tipo_choices = dict(Produto.TIPO_PRODUTO_CHOICES)
    tipo_labels = [tipo_choices.get(tipo, tipo) for tipo in valores_por_tipo.keys()]
    tipo_data = [float(total) for total in valores_por_tipo.values()]

    valor_total = valuation.valor_conhecido

    return render(request, 'estoque/dashboard.html', {
        'total_itens': total_itens,
        'estoque_zerado_count': estoque_zerado_count,
        'valor_total': valor_total,
        'valuation': valuation,
        'valor_total_formatado': dinheiro_br(valor_total),
        'estoque_baixo': estoque_baixo,
        'ultimas_movimentacoes': ultimas_movimentacoes,
        'ultimos_logs': LogAcao.objects.select_related('usuario').all()[:5],
        'chart_meses': json.dumps(meses_nomes),
        'chart_entradas': json.dumps(entradas_meses),
        'chart_saidas': json.dumps(saidas_meses),
        'chart_tipo_labels': json.dumps(tipo_labels),
        'chart_tipo_data': json.dumps(tipo_data),
        'anos_disponiveis': anos,
        'ano_selecionado': ano_selecionado,
    })
