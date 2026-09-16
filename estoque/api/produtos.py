from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, ExpressionWrapper, F, Q, Sum
from django.shortcuts import get_object_or_404

from ..models import Categoria, Fornecedor, HistoricoPreco, Movimentacao, Produto
from ..services.estoque_status import filtro_baixo, filtro_zerado
from ..services.units import dinheiro_br, embalagens_estimadas, unidade_info
from ..views.helpers import json_ok, produto_lista_vue_json
from ..views.produtos import PRODUTO_TABS, ordenar_produtos


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
    aba = (request.GET.get('aba') or request.GET.get('tipo') or 'PAPEL').strip().upper()

    abas_validas = {tab['key'] for tab in PRODUTO_TABS}
    if aba not in abas_validas and aba != 'TODOS':
        aba = 'PAPEL'

    sort = (request.GET.get('sort') or 'descricao').strip()
    if sort not in {'descricao', 'fornecedor', 'categoria', 'metros_por_rolo', 'quantidade', 'preco_custo'}:
        sort = 'descricao'
    direction = 'desc' if request.GET.get('dir') == 'desc' else 'asc'

    try:
        page_size = min(int(request.GET.get('page_size', 25)), 100)
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

    if categoria_selecionada:
        if categoria_selecionada.isdigit():
            qs = qs.filter(categoria_id=int(categoria_selecionada))
        else:
            qs = qs.filter(categoria__nome=categoria_selecionada)

    # Contagens por aba
    contagens = {
        row['tipo_produto']: row
        for row in qs.values('tipo_produto').annotate(
            count=Count('id'),
            critical=Count('id', filter=Q(quantidade_base__lte=0) | filtro_baixo()),
        )
    }

    tabs = []
    for tab in PRODUTO_TABS:
        dados_tab = contagens.get(tab['key'], {})
        tabs.append({
            **tab,
            'active': tab['key'] == aba,
            'count': dados_tab.get('count', 0),
            'critical': dados_tab.get('critical', 0) > 0,
        })

    # Filtrar produtos pela aba selecionada, exceto se TODOS foi pedido explicitamente
    if aba != 'TODOS':
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
            'quantidade_formatada': mov.quantidade_formatada,
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

    return json_ok(
        tipos_produto=[{'value': val, 'label': lbl} for val, lbl in Produto.TIPO_PRODUTO_CHOICES],
        unidades_medida=[{'value': val, 'label': lbl} for val, lbl in Produto.UNIDADE_MEDIDA_CHOICES],
        tipos_tinta=[{'value': val, 'label': lbl} for val, lbl in Produto.TIPO_TINTA_CHOICES],
        cores_tinta=[{'value': val, 'label': lbl} for val, lbl in Produto.COR_CHOICES],
        fornecedores=fornecedores,
        categorias=categorias,
    )
