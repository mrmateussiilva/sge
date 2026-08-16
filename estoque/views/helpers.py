from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.http import JsonResponse

from ..models import FechamentoMensal, Produto
from ..services.estoque_status import filtro_baixo, filtro_zerado
from ..services.estoque_valuation import calcular_valor_estoque
from ..services.fechamentos import validar_periodo
from ..services.units import dinheiro_br, embalagens_estimadas, formatar_quantidade, unidade_info


def decimal_ou_none(value):
    if value in (None, ''):
        return None
    if isinstance(value, Decimal):
        return value
    texto = str(value).strip()
    if ',' in texto:
        texto = texto.replace('.', '').replace(',', '.')
    return Decimal(texto)


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
    """Retorna True apenas para requisições HTMX de partial — exclui navegação
    via hx-boost, que envia HX-Request mas também HX-Boosted e deve receber
    a página completa com layout."""
    return (
        request.headers.get('HX-Request') == 'true'
        and not request.headers.get('HX-Boosted')
    )


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


def produto_lista_vue_json(produto):
    custo = produto.preco_custo
    venda = produto.preco_venda
    lucro = (venda - custo) if venda is not None and custo is not None else None
    margem = (lucro / custo * 100) if lucro is not None and custo and custo > 0 else None
    unidade = unidade_info(produto)
    return {
        'id': produto.id,
        'descricao': produto.descricao,
        'quantidade': float(produto.quantidade_base),
        'quantidade_formatada': produto.quantidade_formatada,
        'estoque_minimo': float(produto.estoque_minimo) if produto.estoque_minimo is not None else 0,
        'status_estoque': produto.status_estoque,
        'tipo_produto': produto.tipo_produto,
        'tipo_label': produto.get_tipo_produto_display(),
        'fornecedor': produto.fornecedor.nome if produto.fornecedor else None,
        'preco_custo': float(custo) if custo is not None else None,
        'preco_venda': float(venda) if venda is not None else None,
        'preco_custo_formatado': dinheiro_br(custo) if custo is not None else 'Não cadastrado',
        'preco_venda_formatado': dinheiro_br(venda) if venda is not None else 'Não cadastrado',
        'margem': float(round(margem, 1)) if margem is not None else None,
        'metros_por_rolo': float(produto.metros_por_rolo) if produto.metros_por_rolo else 0,
        'litros_por_vidro': float(produto.litros_por_vidro) if produto.litros_por_vidro else 0,
        'embalagens_estimadas': float(embalagens_estimadas(produto)),
        'tipo_tinta': produto.tipo_tinta,
        'cor_tinta': produto.cor_tinta,
        'unidade_simbolo': unidade.simbolo,
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
