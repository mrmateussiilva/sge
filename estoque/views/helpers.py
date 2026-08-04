from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.http import JsonResponse

from ..models import FechamentoMensal, Produto
from ..services.estoque_status import filtro_baixo, filtro_zerado
from ..services.estoque_valuation import calcular_valor_estoque
from ..services.fechamentos import validar_periodo
from ..services.units import dinheiro_br, formatar_quantidade, unidade_info


def decimal_ou_none(value):
    if value in (None, ''):
        return None
    return Decimal(str(value))


def data_iso(value, nome_campo):
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise ValidationError(f'{nome_campo} inválida. Use o formato AAAA-MM-DD.')


PERFIS_NEGOCIO = {
    'Admin': 'Administrador',
    'Gestor': 'Gestor de estoque',
    'Operador': 'Operador',
    'Leitura': 'Somente leitura',
    'Visualizador': 'Somente leitura',
}


def json_ok(**kwargs):
    return JsonResponse({'ok': True, **kwargs})


def json_erro(mensagem, status=400, codigo='VALIDACAO'):
    return JsonResponse({'ok': False, 'erro': mensagem, 'codigo': codigo}, status=status)


def requisicao_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def usuario_pode_alterar(request):
    return request.user.is_superuser


def exigir_admin_json(request):
    if not usuario_pode_alterar(request):
        return json_erro('Permissão negada.', status=403, codigo='PERMISSAO_NEGADA')
    return None


def produto_operacional_json(produto):
    minimo = produto.estoque_minimo
    return {
        'id': produto.id,
        'descricao': produto.descricao,
        'fornecedor': produto.fornecedor.nome if produto.fornecedor else '',
        'quantidade': float(produto.quantidade_base),
        'quantidade_formatada': produto.quantidade_formatada,
        'estoque_minimo': float(minimo) if minimo is not None else None,
        'estoque_minimo_formatado': formatar_quantidade(minimo, produto.unidade_base_codigo) if minimo is not None else 'Sem mínimo configurado',
        'unidade_codigo': produto.unidade_base_codigo,
        'unidade_simbolo': produto.unidade_simbolo,
        'unidade_nome': unidade_info(produto).plural,
        'status_estoque': produto.status_estoque,
    }


def resumo_fechamento(data_inicio, data_fim):
    validar_periodo(data_inicio, data_fim)
    produtos = list(Produto.objects.select_related('fornecedor').all())
    valuation = calcular_valor_estoque(produtos)
    sem_fornecedor = sum(1 for p in produtos if not p.fornecedor_id)
    return {
        'data_inicio': data_inicio.isoformat(),
        'data_fim': data_fim.isoformat(),
        'periodo_formatado': f'{data_inicio:%d/%m/%Y} a {data_fim:%d/%m/%Y}',
        'total_produtos': len(produtos),
        'produtos_zerados': Produto.objects.filter(filtro_zerado()).count(),
        'produtos_baixos': Produto.objects.filter(filtro_baixo()).count(),
        'produtos_sem_custo': valuation.produtos_sem_custo,
        'produtos_sem_fornecedor': sem_fornecedor,
        'valor_conhecido': float(valuation.valor_conhecido),
        'valor_conhecido_formatado': dinheiro_br(valuation.valor_conhecido),
        'calculo_completo': valuation.calculo_completo,
        'duplicado': FechamentoMensal.objects.filter(
            data_inicio=data_inicio,
            data_fim=data_fim,
        ).exists(),
    }
