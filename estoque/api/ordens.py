from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404

from ..models import Fornecedor, OrdemCompra
from ..services.units import dinheiro_br
from ..views.helpers import json_ok


def serializar_ordem_resumo(ordem):
    itens = list(ordem.itens.all())
    total_itens = len(itens)
    valor_total = sum((item.quantidade * item.preco_unitario for item in itens), Decimal('0.00'))

    return {
        'id': ordem.id,
        'fornecedor': {
            'id': ordem.fornecedor.id,
            'nome': ordem.fornecedor.nome,
        } if ordem.fornecedor else None,
        'status': ordem.status,
        'status_display': ordem.get_status_display(),
        'data_criacao': ordem.data_criacao.isoformat(),
        'data_criacao_formatada': ordem.data_criacao.strftime('%d/%m/%Y %H:%M'),
        'observacao': ordem.observacao,
        'total_itens': total_itens,
        'valor_total': float(valor_total),
        'valor_total_formatado': dinheiro_br(valor_total),
    }


@login_required
def listar_ordens_api(request):
    """Lista paginada de ordens de compra."""
    busca = (request.GET.get('busca') or request.GET.get('q') or '').strip()
    status_selecionado = request.GET.get('status', '').strip().upper()
    fornecedor_selecionado = request.GET.get('fornecedor', '').strip()

    try:
        page_size = min(int(request.GET.get('page_size', 25)), 100)
    except (TypeError, ValueError):
        page_size = 25

    qs = OrdemCompra.objects.select_related('fornecedor').prefetch_related('itens').all().order_by('-data_criacao')

    if busca:
        qs = qs.filter(
            Q(fornecedor__nome__icontains=busca) | Q(observacao__icontains=busca)
        )
    if status_selecionado:
        qs = qs.filter(status=status_selecionado)
    if fornecedor_selecionado == 'SEM_FORNECEDOR':
        qs = qs.filter(fornecedor__isnull=True)
    elif fornecedor_selecionado:
        if fornecedor_selecionado.isdigit():
            qs = qs.filter(fornecedor_id=int(fornecedor_selecionado))
        else:
            qs = qs.filter(fornecedor__nome=fornecedor_selecionado)

    paginator = Paginator(qs, page_size)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    itens = [serializar_ordem_resumo(ordem) for ordem in page_obj]

    fornecedores_unicos = list(
        Fornecedor.objects.filter(ordemcompra__isnull=False)
        .values('id', 'nome').distinct().order_by('nome')
    )

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
        status_choices=[{'value': val, 'label': lbl} for val, lbl in OrdemCompra.STATUS_CHOICES],
        fornecedores_com_ordens=fornecedores_unicos,
        filtros_aplicados={
            'busca': busca,
            'status': status_selecionado,
            'fornecedor': fornecedor_selecionado,
        },
    )


@login_required
def detalhe_ordem_api(request, id):
    """Retorna detalhes da ordem de compra e seus itens."""
    ordem = get_object_or_404(
        OrdemCompra.objects.select_related('fornecedor').prefetch_related('itens__produto'),
        id=id,
    )

    itens = []
    valor_total = Decimal('0.00')
    for item in ordem.itens.all():
        subtotal = item.quantidade * item.preco_unitario
        valor_total += subtotal
        itens.append({
            'id': item.id,
            'produto_id': item.produto_id,
            'produto_descricao': item.produto.descricao,
            'produto_unidade': item.produto.unidade_simbolo,
            'quantidade': float(item.quantidade),
            'preco_unitario': float(item.preco_unitario),
            'preco_unitario_formatado': dinheiro_br(item.preco_unitario),
            'subtotal': float(subtotal),
            'subtotal_formatado': dinheiro_br(subtotal),
        })

    return json_ok(
        ordem={
            'id': ordem.id,
            'fornecedor': {
                'id': ordem.fornecedor.id,
                'nome': ordem.fornecedor.nome,
            } if ordem.fornecedor else None,
            'status': ordem.status,
            'status_display': ordem.get_status_display(),
            'data_criacao': ordem.data_criacao.isoformat(),
            'data_criacao_formatada': ordem.data_criacao.strftime('%d/%m/%Y %H:%M'),
            'observacao': ordem.observacao,
            'total_itens': len(itens),
            'valor_total': float(valor_total),
            'valor_total_formatado': dinheiro_br(valor_total),
        },
        itens=itens,
    )
