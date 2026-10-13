from decimal import Decimal
import json

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, ExpressionWrapper, F, Q, Sum
from django.shortcuts import get_object_or_404

from ..log_utils import log_acao
from ..models import Categoria, Fornecedor, HistoricoPreco, Movimentacao, Produto
from ..services.estoque_status import filtro_baixo, filtro_zerado
from ..services.units import dinheiro_br, embalagens_estimadas, formatar_quantidade, unidade_info
from ..views.helpers import json_erro, json_ok, produto_lista_vue_json
from ..views.produtos import ordenar_produtos


def serializar_produto_detalhado(produto):
    """Serializa produto com todos os campos necessários para visualização e edição."""
    custo = produto.preco_custo
    venda = produto.preco_venda
    lucro = (venda - custo) if venda is not None and custo is not None else None
    margem = (lucro / custo * 100) if lucro is not None and custo and custo > 0 else None
    unidade = unidade_info(produto)

    return {
        'id': produto.id,
        'descricao': produto.descricao,
        'tipo_produto': produto.tipo_produto,
        'tipo_label': produto.get_tipo_produto_display(),
        'unidade_medida': produto.unidade_medida,
        'unidade_simbolo': unidade.simbolo,
        'unidade_nome': unidade.plural,
        'quantidade': float(produto.quantidade_base),
        'quantidade_formatada': produto.quantidade_formatada,
        'estoque_minimo': float(produto.estoque_minimo) if produto.estoque_minimo is not None else None,
        'status_estoque': produto.status_estoque,
        'preco_custo': float(custo) if custo is not None else None,
        'preco_venda': float(venda) if venda is not None else None,
        'preco_custo_formatado': dinheiro_br(custo) if custo is not None else 'Não cadastrado',
        'preco_venda_formatado': dinheiro_br(venda) if venda is not None else 'Não cadastrado',
        'lucro': float(round(lucro, 2)) if lucro is not None else None,
        'margem': float(round(margem, 1)) if margem is not None else None,
        'fornecedor': {
            'id': produto.fornecedor.id,
            'nome': produto.fornecedor.nome,
        } if produto.fornecedor else None,
        'categoria': {
            'id': produto.categoria.id,
            'nome': produto.categoria.nome,
            'cor': produto.categoria.cor,
        } if produto.categoria else None,
        'metros_por_rolo': float(produto.metros_por_rolo) if produto.metros_por_rolo else None,
        'litros_por_vidro': float(produto.litros_por_vidro) if produto.litros_por_vidro else None,
        'embalagens_estimadas': float(embalagens_estimadas(produto)),
        'tipo_tinta': produto.tipo_tinta,
        'cor_tinta': produto.cor_tinta,
    }


@login_required
def listar_produtos_api(request):
    """Lista de produtos com filtros completos, abas, paginação e resumo financeiro."""
    busca = (request.GET.get('busca') or request.GET.get('q') or '').strip()
    filtro_raw = (request.GET.get('filtro') or request.GET.get('estoque') or '').strip().upper()
    filtro_estoque = {
        'BAIXO': 'BAIXO',
        'ZERADO': 'ZERADO',
        'OK': 'OK',
        'NORMAL': 'OK',
    }.get(filtro_raw, '')

    fornecedor_selecionado = (request.GET.get('fornecedor') or '').strip()
    categoria_selecionada = (request.GET.get('categoria') or '').strip()
    tipo_selecionado = (request.GET.get('tipo') or '').strip().upper()

    aba_param = (request.GET.get('aba') or '').strip()
    aba_upper = aba_param.upper()

    if not aba_param or aba_upper in {'TODOS', 'ALL'}:
        aba = 'TODOS'
    elif aba_upper == 'SEM_CATEGORIA':
        aba = 'SEM_CATEGORIA'
    elif aba_param.isdigit():
        aba = aba_param
    elif aba_upper in {'PAPEL', 'TECIDO', 'TINTA', 'AVIAMENTO', 'OUTRO'}:
        aba = aba_upper
    else:
        # Se for passado o nome de uma categoria
        cat_match = Categoria.objects.filter(nome__iexact=aba_param).first()
        aba = str(cat_match.id) if cat_match else 'TODOS'

    sort = (request.GET.get('sort') or 'descricao').strip()
    if sort not in {'descricao', 'fornecedor', 'categoria', 'metros_por_rolo', 'quantidade', 'preco_custo'}:
        sort = 'descricao'
    direction = 'desc' if request.GET.get('dir') == 'desc' else 'asc'

    try:
        page_size = max(1, min(int(request.GET.get('page_size', 25)), 100))
    except (TypeError, ValueError):
        page_size = 25

    qs = Produto.objects.select_related('fornecedor', 'categoria').all()

    if busca:
        qs = qs.filter(Q(descricao__icontains=busca) | Q(fornecedor__nome__icontains=busca))
    if filtro_estoque == 'ZERADO':
        qs = qs.filter(filtro_zerado())
    elif filtro_estoque == 'BAIXO':
        qs = qs.filter(filtro_baixo())
    elif filtro_estoque == 'OK':
        qs = qs.exclude(filtro_zerado()).exclude(filtro_baixo())

    if fornecedor_selecionado == 'SEM_FORNECEDOR':
        qs = qs.filter(fornecedor__isnull=True)
    elif fornecedor_selecionado:
        if fornecedor_selecionado.isdigit():
            qs = qs.filter(fornecedor_id=int(fornecedor_selecionado))
        else:
            qs = qs.filter(fornecedor__nome=fornecedor_selecionado)

    if tipo_selecionado and tipo_selecionado in {'PAPEL', 'TECIDO', 'TINTA', 'AVIAMENTO', 'OUTRO'}:
        qs = qs.filter(tipo_produto=tipo_selecionado)

    if categoria_selecionada and aba == 'TODOS':
        if categoria_selecionada.isdigit():
            qs = qs.filter(categoria_id=int(categoria_selecionada))
        elif categoria_selecionada.upper() == 'SEM_CATEGORIA':
            qs = qs.filter(categoria__isnull=True)
        else:
            qs = qs.filter(categoria__nome__iexact=categoria_selecionada)

    # Contagens agregadas por categoria sobre a base filtrada
    contagens = {
        row['categoria_id']: row
        for row in qs.values('categoria_id').annotate(
            count=Count('id'),
            critical=Count('id', filter=Q(quantidade_base__lte=0) | filtro_baixo()),
        )
    }

    total_todos = sum(row['count'] for row in contagens.values())
    critico_todos = any(row['critical'] > 0 for row in contagens.values())

    tabs = [
        {
            'key': 'TODOS',
            'label': 'Todas',
            'cor': None,
            'active': aba == 'TODOS',
            'count': total_todos,
            'critical': critico_todos,
        }
    ]

    for cat in Categoria.objects.all().order_by('nome'):
        cat_key = str(cat.id)
        dados_cat = contagens.get(cat.id, {})
        tabs.append({
            'key': cat_key,
            'label': cat.nome,
            'cor': cat.cor,
            'active': aba == cat_key,
            'count': dados_cat.get('count', 0),
            'critical': dados_cat.get('critical', 0) > 0,
        })

    dados_sem_cat = contagens.get(None, {})
    sem_cat_count = dados_sem_cat.get('count', 0)
    if sem_cat_count > 0 or aba == 'SEM_CATEGORIA':
        tabs.append({
            'key': 'SEM_CATEGORIA',
            'label': 'Sem Categoria',
            'cor': '#94a3b8',
            'active': aba == 'SEM_CATEGORIA',
            'count': sem_cat_count,
            'critical': dados_sem_cat.get('critical', 0) > 0,
        })

    # Filtrar produtos pela aba selecionada
    if aba == 'TODOS':
        produtos_filtrados = qs
    elif aba == 'SEM_CATEGORIA':
        produtos_filtrados = qs.filter(categoria__isnull=True)
    elif aba.isdigit():
        produtos_filtrados = qs.filter(categoria_id=int(aba))
    elif aba in {'PAPEL', 'TECIDO', 'TINTA', 'AVIAMENTO', 'OUTRO'}:
        produtos_filtrados = qs.filter(tipo_produto=aba)
    else:
        produtos_filtrados = qs

    produtos_ordenados = ordenar_produtos(produtos_filtrados, sort, direction)

    # Resumo agregado da listagem filtrada
    valor_estoque = ExpressionWrapper(
        F('quantidade_base') * F('preco_custo'),
        output_field=Produto._meta.get_field('preco_custo'),
    )
    resumo = produtos_filtrados.aggregate(
        total_itens=Count('id'),
        valor_custo=Sum(valor_estoque),
        sem_custo=Count('id', filter=Q(quantidade_base__gt=0, preco_custo__isnull=True)),
        baixos=Count('id', filter=filtro_baixo()),
        zerados=Count('id', filter=filtro_zerado()),
    )
    valor_custo = resumo['valor_custo'] or Decimal('0')

    paginator = Paginator(produtos_ordenados, page_size)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    itens = [produto_lista_vue_json(p) for p in page_obj]

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
        resumo={
            'total_itens': resumo['total_itens'] or 0,
            'valor_custo': float(valor_custo),
            'valor_custo_formatado': dinheiro_br(valor_custo),
            'sem_custo': resumo['sem_custo'] or 0,
            'baixos': resumo['baixos'] or 0,
            'zerados': resumo['zerados'] or 0,
        },
        abas=tabs,
        filtros_aplicados={
            'busca': busca,
            'aba': aba,
            'tipo': tipo_selecionado,
            'estoque': filtro_estoque,
            'fornecedor': fornecedor_selecionado,
            'categoria': categoria_selecionada,
            'sort': sort,
            'dir': direction,
        },
    )


@login_required
def detalhe_produto_api(request, id):
    """Retorna o detalhe completo de um produto com movimentações recentes e histórico de preços."""
    produto = get_object_or_404(
        Produto.objects.select_related('fornecedor', 'categoria'),
        id=id,
    )

    movimentacoes_qs = Movimentacao.objects.filter(produto=produto).select_related('usuario').order_by('-data')[:50]
    movimentacoes = [
        {
            'id': mov.id,
            'tipo': mov.tipo,
            'tipo_display': mov.get_tipo_display(),
            'motivo': mov.motivo,
            'motivo_display': mov.get_motivo_display(),
            'quantidade': float(mov.quantidade),
            'quantidade_formatada': formatar_quantidade(mov.quantidade, produto.unidade_base_codigo),
            'usuario': mov.usuario.username if mov.usuario else '-',
            'data': mov.data.isoformat(),
            'data_formatada': mov.data.strftime('%d/%m/%Y %H:%M'),
            'observacao': mov.observacao,
        }
        for mov in movimentacoes_qs
    ]

    historico_precos_qs = HistoricoPreco.objects.filter(produto=produto).select_related('usuario').order_by('-data')[:20]
    historico_precos = [
        {
            'id': hp.id,
            'data': hp.data.isoformat(),
            'data_formatada': hp.data.strftime('%d/%m/%Y %H:%M'),
            'usuario': hp.usuario.username if hp.usuario else '-',
            'preco_custo_antigo': float(hp.preco_custo_antigo) if hp.preco_custo_antigo is not None else None,
            'preco_custo_novo': float(hp.preco_custo_novo) if hp.preco_custo_novo is not None else None,
            'preco_venda_antigo': float(hp.preco_venda_antigo) if hp.preco_venda_antigo is not None else None,
            'preco_venda_novo': float(hp.preco_venda_novo) if hp.preco_venda_novo is not None else None,
            'preco_custo_antigo_formatado': dinheiro_br(hp.preco_custo_antigo) if hp.preco_custo_antigo is not None else '-',
            'preco_custo_novo_formatado': dinheiro_br(hp.preco_custo_novo) if hp.preco_custo_novo is not None else '-',
            'preco_venda_antigo_formatado': dinheiro_br(hp.preco_venda_antigo) if hp.preco_venda_antigo is not None else '-',
            'preco_venda_novo_formatado': dinheiro_br(hp.preco_venda_novo) if hp.preco_venda_novo is not None else '-',
        }
        for hp in historico_precos_qs
    ]

    return json_ok(
        produto=serializar_produto_detalhado(produto),
        movimentacoes=movimentacoes,
        historico_precos=historico_precos,
    )


@login_required
def opcoes_produto_api(request):
    """Retorna as opções estáticas e relacionamentos para formulários de produto."""
    fornecedores = [
        {'id': f.id, 'nome': f.nome}
        for f in Fornecedor.objects.all().order_by('nome')
    ]
    categorias = [
        {'id': c.id, 'nome': c.nome, 'cor': c.cor}
        for c in Categoria.objects.all().order_by('nome')
    ]

    produtos = [
        {
            'id': p.id,
            'descricao': p.descricao,
            'unidade_medida': p.unidade_medida,
            'tipo_produto': p.tipo_produto,
            'quantidade_formatada': p.quantidade_formatada,
            'quantidade': float(p.quantidade_base),
            'preco_custo': float(p.preco_custo) if p.preco_custo is not None else None,
        }
        for p in Produto.objects.all().order_by('descricao')
    ]

    return json_ok(
        tipos_produto=[{'value': val, 'label': lbl} for val, lbl in Produto.TIPO_PRODUTO_CHOICES],
        unidades_medida=[{'value': val, 'label': lbl} for val, lbl in Produto.UNIDADE_MEDIDA_CHOICES],
        tipos_tinta=[{'value': val, 'label': lbl} for val, lbl in Produto.TIPO_TINTA_CHOICES],
        cores_tinta=[{'value': val, 'label': lbl} for val, lbl in Produto.COR_CHOICES],
        fornecedores=fornecedores,
        categorias=categorias,
        produtos=produtos,
    )


@login_required
def acao_em_massa_produtos_api(request):
    """
    Executa ações em lote em uma lista de produtos:
    - alterar_categoria: define categoria para os produtos selecionados
    - remover_categoria: desvincula a categoria dos produtos selecionados
    """
    if request.method != 'POST':
        return json_erro('Método não permitido.', status=405)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return json_erro('JSON inválido.')

    ids = data.get('ids', [])
    if not isinstance(ids, list) or not ids:
        return json_erro('Selecione ao menos um produto para executar a ação.')

    try:
        produto_ids = [int(i) for i in ids]
    except (ValueError, TypeError):
        return json_erro('Lista de IDs inválida.')

    if len(produto_ids) > 500:
        return json_erro('Limite de 500 produtos por operação excedido.')

    acao = str(data.get('acao', '')).strip().lower()

    if acao == 'alterar_categoria':
        categoria_id = data.get('categoria_id')
        if not categoria_id:
            return json_erro('Informe a categoria desejada.')
        try:
            categoria = Categoria.objects.get(id=int(categoria_id))
        except (Categoria.DoesNotExist, ValueError, TypeError):
            return json_erro('Categoria selecionada não foi encontrada.', status=404)

        with transaction.atomic():
            atualizados = Produto.objects.filter(id__in=produto_ids).update(categoria=categoria)
            log_acao(
                request.user,
                'EDITAR',
                f'Categoria "{categoria.nome}" aplicada em massa a {atualizados} produto(s).',
                'Produto',
                None,
            )
        return json_ok(
            atualizados=atualizados,
            mensagem=f'Categoria "{categoria.nome}" aplicada com sucesso a {atualizados} produto(s).',
        )

    elif acao == 'remover_categoria':
        with transaction.atomic():
            atualizados = Produto.objects.filter(id__in=produto_ids).update(categoria=None)
            log_acao(
                request.user,
                'EDITAR',
                f'Categoria removida em massa de {atualizados} produto(s).',
                'Produto',
                None,
            )
        return json_ok(
            atualizados=atualizados,
            mensagem=f'Categoria removida com sucesso de {atualizados} produto(s).',
        )

    else:
        return json_erro(f'Ação "{acao}" não reconhecida.')

