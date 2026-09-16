from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from ..models import Movimentacao
from ..services.units import formatar_quantidade
from ..views.helpers import json_ok


MOTIVOS_SAIDA = [
    {'value': 'PRODUCAO', 'label': 'Uso em Produção / Consumo'},
    {'value': 'AVARIA', 'label': 'Avaria / Defeito / Perda'},
    {'value': 'VENCIMENTO', 'label': 'Vencimento / Descarte'},
    {'value': 'AJUSTE', 'label': 'Ajuste de Inventário'},
    {'value': 'OUTRO', 'label': 'Outro'},
]

MOTIVOS_ENTRADA = [
    {'value': 'COMPRA', 'label': 'Compra / Reposição'},
    {'value': 'DEVOLUCAO', 'label': 'Devolução'},
    {'value': 'AJUSTE', 'label': 'Ajuste de Inventário'},
    {'value': 'OUTRO', 'label': 'Outro'},
]


@login_required
def listar_movimentacoes_api(request):
    """Lista paginada de movimentações de estoque com filtros."""
    busca = (request.GET.get('busca') or request.GET.get('q') or '').strip()
    produto_id = request.GET.get('produto_id')
    tipo = request.GET.get('tipo', '').strip().upper()
    motivo = request.GET.get('motivo', '').strip().upper()
    data_inicio = request.GET.get('data_inicio', '').strip()
    data_fim = request.GET.get('data_fim', '').strip()

    try:
        page_size = min(int(request.GET.get('page_size', 25)), 100)
    except (TypeError, ValueError):
        page_size = 25

    qs = Movimentacao.objects.select_related('produto', 'usuario').all().order_by('-data')

    if busca:
        qs = qs.filter(
            Q(produto__descricao__icontains=busca)
            | Q(observacao__icontains=busca)
            | Q(usuario__username__icontains=busca)
        )
    if produto_id and str(produto_id).isdigit():
        qs = qs.filter(produto_id=int(produto_id))
    if tipo in ('ENTRADA', 'SAIDA'):
        qs = qs.filter(tipo=tipo)
    if motivo:
        qs = qs.filter(motivo=motivo)
    if data_inicio:
        try:
            dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').replace(tzinfo=timezone.get_current_timezone())
            qs = qs.filter(data__gte=dt_inicio)
        except ValueError:
            pass
    if data_fim:
        try:
            dt_fim = datetime.strptime(data_fim, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.get_current_timezone())
            qs = qs.filter(data__lte=dt_fim)
        except ValueError:
            pass

    paginator = Paginator(qs, page_size)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    itens = [
        {
            'id': mov.id,
            'produto_id': mov.produto_id,
            'produto_descricao': mov.produto.descricao,
            'produto_unidade': mov.produto.unidade_simbolo,
            'tipo': mov.tipo,
            'tipo_display': mov.get_tipo_display(),
            'motivo': mov.motivo,
            'motivo_display': mov.get_motivo_display(),
            'quantidade': float(mov.quantidade),
            'quantidade_formatada': formatar_quantidade(mov.quantidade, mov.produto.unidade_base_codigo),
            'usuario': mov.usuario.username if mov.usuario else '-',
            'data': mov.data.isoformat(),
            'data_formatada': mov.data.strftime('%d/%m/%Y %H:%M'),
            'observacao': mov.observacao,
        }
        for mov in page_obj
    ]

    return json_ok(
        itens=itens,
        paginacao={
            'pagina_atual': page_obj.number,
            'total_paginas': paginator.num_pages,
            'total_itens': paginator.count,
            'tem_proxima': page_obj.has_next(),
            'tem_anterior': page_obj.has_previous(),
            'itens_por_pagina': page_size,
        },
        motivos_entrada=MOTIVOS_ENTRADA,
        motivos_saida=MOTIVOS_SAIDA,
    )
