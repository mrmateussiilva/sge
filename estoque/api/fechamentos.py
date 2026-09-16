import calendar
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone

from ..models import FechamentoMensal
from ..services.units import UNIDADES, dinheiro_br
from ..views.helpers import data_iso, json_erro, json_ok, resumo_fechamento


@login_required
def listar_fechamentos_api(request):
    """Lista todos os fechamentos mensais históricos e sugere o período atual."""
    hoje = timezone.localdate()
    data_inicio_sugerida = hoje.replace(day=1)
    ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
    data_fim_sugerida = hoje.replace(day=ultimo_dia)

    fechamentos = FechamentoMensal.objects.prefetch_related('itens').select_related('usuario').all()
    fechamentos_data = []

    for f in fechamentos:
        itens = list(f.itens.all())
        total_itens = len(itens)
        valor_total = Decimal('0.00')
        produtos_sem_custo = 0

        for item in itens:
            if item.quantidade > 0 and item.preco_custo is None:
                produtos_sem_custo += 1
            elif item.preco_custo is not None:
                valor_total += item.quantidade * item.preco_custo

        fechamentos_data.append({
            'id': f.id,
            'data_fechamento': f.data_fechamento.isoformat(),
            'data_fechamento_formatada': f.data_fechamento.strftime('%d/%m/%Y %H:%M'),
            'usuario': f.usuario.username if f.usuario else '-',
            'data_inicio': f.data_inicio.isoformat(),
            'data_fim': f.data_fim.isoformat(),
            'periodo_formatado': f.periodo_formatado,
            'observacao': f.observacao,
            'total_itens': total_itens,
            'valor_total': float(valor_total),
            'valor_total_formatado': dinheiro_br(valor_total),
            'produtos_sem_custo': produtos_sem_custo,
            'calculo_completo': produtos_sem_custo == 0,
        })

    return json_ok(
        itens=fechamentos_data,
        periodo_sugerido={
            'data_inicio': data_inicio_sugerida.isoformat(),
            'data_fim': data_fim_sugerida.isoformat(),
            'periodo_formatado': f'{data_inicio_sugerida:%d/%m/%Y} a {data_fim_sugerida:%d/%m/%Y}',
        },
    )


@login_required
def detalhe_fechamento_api(request, id):
    """Retorna detalhes completos e itens do snapshot de um fechamento mensal."""
    fechamento = get_object_or_404(
        FechamentoMensal.objects.select_related('usuario').prefetch_related('itens'),
        id=id,
    )

    itens = []
    valor_total = Decimal('0.00')
    valor_total_venda = Decimal('0.00')
    produtos_sem_custo = 0

    for item in fechamento.itens.all().order_by('descricao'):
        valor_custo = None
        if item.preco_custo is None:
            if item.quantidade > 0:
                produtos_sem_custo += 1
        else:
            valor_custo = item.quantidade * item.preco_custo
            valor_total += valor_custo

        valor_venda = None
        if item.preco_venda is not None:
            valor_venda = item.quantidade * item.preco_venda
            valor_total_venda += valor_venda

        unidade = UNIDADES.get(item.unidade_medida, UNIDADES['OUTRO'])

        itens.append({
            'id': item.id,
            'descricao': item.descricao,
            'tipo': item.get_tipo_produto_display() or '—',
            'categoria': item.categoria_nome or '—',
            'fornecedor': item.fornecedor_nome or '—',
            'unidade': unidade.simbolo or '—',
            'quantidade': float(item.quantidade),
            'preco_custo': float(item.preco_custo) if item.preco_custo is not None else None,
            'preco_custo_formatado': dinheiro_br(item.preco_custo) if item.preco_custo is not None else '-',
            'preco_venda': float(item.preco_venda) if item.preco_venda is not None else None,
            'preco_venda_formatado': dinheiro_br(item.preco_venda) if item.preco_venda is not None else '-',
            'valor_custo': float(valor_custo) if valor_custo is not None else None,
            'valor_custo_formatado': dinheiro_br(valor_custo) if valor_custo is not None else '-',
            'valor_venda': float(valor_venda) if valor_venda is not None else None,
            'valor_venda_formatado': dinheiro_br(valor_venda) if valor_venda is not None else '-',
        })

    return json_ok(
        fechamento={
            'id': fechamento.id,
            'data_fechamento': fechamento.data_fechamento.isoformat(),
            'data_fechamento_formatada': fechamento.data_fechamento.strftime('%d/%m/%Y %H:%M'),
            'usuario': fechamento.usuario.username if fechamento.usuario else '-',
            'data_inicio': fechamento.data_inicio.isoformat(),
            'data_fim': fechamento.data_fim.isoformat(),
            'periodo_formatado': fechamento.periodo_formatado,
            'observacao': fechamento.observacao,
            'total_itens': len(itens),
            'valor_total': float(valor_total),
            'valor_total_formatado': dinheiro_br(valor_total),
            'valor_total_venda': float(valor_total_venda),
            'valor_total_venda_formatado': dinheiro_br(valor_total_venda),
            'produtos_sem_custo': produtos_sem_custo,
            'calculo_completo': produtos_sem_custo == 0,
        },
        itens=itens,
    )


@login_required
def revisar_fechamento_api(request):
    """Prévia/simulação de fechamento antes da efetivação."""
    try:
        inicio = data_iso(request.GET.get('data_inicio'), 'Data inicial')
        fim = data_iso(request.GET.get('data_fim'), 'Data final')
        resumo = resumo_fechamento(inicio, fim)
        return json_ok(resumo=resumo)
    except ValidationError as exc:
        return json_erro('; '.join(exc.messages))
