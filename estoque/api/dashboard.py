from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.utils import timezone

from ..models import LogAcao, Movimentacao, Produto
from ..services.estoque_metrics import valor_por_tipo
from ..services.estoque_status import filtro_baixo, filtro_zerado
from ..services.estoque_valuation import calcular_valor_estoque
from ..services.units import dinheiro_br, formatar_quantidade
from ..views.helpers import json_ok, produto_operacional_json


@login_required
def dashboard_metricas(request):
    """Retorna os dados consolidados para o Dashboard do sistema."""
    produtos_base = Produto.objects.select_related('fornecedor', 'categoria').all()
    produtos_lista = list(produtos_base)
    total_itens = len(produtos_lista)
    estoque_zerado_count = Produto.objects.filter(filtro_zerado()).count()
    estoque_baixo_qs = Produto.objects.filter(filtro_baixo()).select_related('fornecedor')
    estoque_baixo_count = estoque_baixo_qs.count()

    valuation = calcular_valor_estoque(produtos_lista)

    itens_criticos = [
        produto_operacional_json(p)
        for p in estoque_baixo_qs[:10]
    ]

    ultimas_movimentacoes = [
        {
            'id': mov.id,
            'produto_id': mov.produto_id,
            'produto_descricao': mov.produto.descricao,
            'tipo': mov.tipo,
            'tipo_display': mov.get_tipo_display(),
            'motivo': mov.motivo,
            'motivo_display': mov.get_motivo_display(),
            'quantidade': float(mov.quantidade),
            'quantidade_formatada': formatar_quantidade(mov.quantidade, mov.produto.unidade_base_codigo),
            'unidade_simbolo': mov.produto.unidade_simbolo,
            'data': mov.data.isoformat(),
            'data_formatada': mov.data.strftime('%d/%m/%Y %H:%M'),
            'usuario': mov.usuario.username if mov.usuario else '-',
            'observacao': mov.observacao,
        }
        for mov in Movimentacao.objects.select_related('produto', 'usuario').order_by('-data')[:5]
    ]

    ultimos_logs = [
        {
            'id': log.id,
            'data': log.data.isoformat(),
            'data_formatada': log.data.strftime('%d/%m/%Y %H:%M'),
            'usuario': log.usuario.username if log.usuario else '-',
            'acao': log.acao,
            'descricao': log.descricao,
            'modelo': log.modelo,
            'objeto_id': log.objeto_id,
        }
        for log in LogAcao.objects.select_related('usuario').order_by('-data')[:5]
    ]

    return json_ok(
        resumo={
            'total_itens': total_itens,
            'estoque_zerado': estoque_zerado_count,
            'estoque_baixo': estoque_baixo_count,
            'valor_total': float(valuation.valor_conhecido),
            'valor_total_formatado': dinheiro_br(valuation.valor_conhecido),
            'produtos_sem_custo': valuation.produtos_sem_custo,
            'calculo_completo': valuation.calculo_completo,
        },
        itens_criticos=itens_criticos,
        ultimas_movimentacoes=ultimas_movimentacoes,
        ultimos_logs=ultimos_logs,
    )


@login_required
def dashboard_chart(request):
    """Retorna os dados dos gráficos de movimentação mensal e valor por tipo."""
    hoje = timezone.now()
    ano_atual = hoje.year
    try:
        ano_selecionado = int(request.GET.get('ano', ano_atual))
    except (TypeError, ValueError):
        ano_selecionado = ano_atual

    anos_disponiveis = list(Movimentacao.objects.dates('data', 'year', order='DESC'))
    anos = sorted(list(set([a.year for a in anos_disponiveis] + [ano_atual])), reverse=True)

    meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    movimentos_por_mes = {
        row['data__month']: row
        for row in Movimentacao.objects.filter(data__year=ano_selecionado)
        .values('data__month')
        .annotate(
            entradas=Count('id', filter=Q(tipo='ENTRADA')),
            saidas=Count('id', filter=Q(tipo='SAIDA')),
        )
    }
    entradas_meses = [movimentos_por_mes.get(m, {}).get('entradas', 0) for m in range(1, 13)]
    saidas_meses = [movimentos_por_mes.get(m, {}).get('saidas', 0) for m in range(1, 13)]

    # Distribuição por tipo de produto
    produtos_lista = list(Produto.objects.all())
    valores_tipo = valor_por_tipo(produtos_lista)
    total_valor = sum(valores_tipo.values())
    tipo_choices = dict(Produto.TIPO_PRODUTO_CHOICES)

    distribuicao_tipos = []
    for tipo, total in valores_tipo.items():
        total_float = float(total)
        percentual = round((total_float / float(total_valor) * 100), 1) if total_valor > 0 else 0
        distribuicao_tipos.append({
            'tipo': tipo,
            'label': tipo_choices.get(tipo, tipo),
            'valor': total_float,
            'valor_formatado': dinheiro_br(total),
            'percentual': percentual,
        })

    return json_ok(
        ano_selecionado=ano_selecionado,
        anos_disponiveis=anos,
        mensal={
            'meses': meses_nomes,
            'entradas': entradas_meses,
            'saidas': saidas_meses,
        },
        por_tipo=distribuicao_tipos,
    )
