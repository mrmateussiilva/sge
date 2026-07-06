import csv
import json
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .log_utils import log_acao
from .models import Categoria, Fornecedor, HistoricoPreco, ItemOrdemCompra, LogAcao, Movimentacao, OrdemCompra, Produto, FechamentoMensal, ItemFechamento
from .xml_parser import fetch_xml_from_url, parse_nfe_xml

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


@login_required
def dashboard(request):
    total_itens = Produto.objects.count()
    valor_total = Produto.objects.aggregate(
        total=Sum(F('quantidade_base') * F('preco_custo'))
    )['total'] or 0
    valor_venda_total = Produto.objects.aggregate(
        total=Sum(F('quantidade_base') * F('preco_venda'))
    )['total'] or 0
    estoque_baixo = Produto.objects.filter(
        quantidade_base__lte=F('estoque_minimo')
    ).select_related('fornecedor')
    ultimas_movimentacoes = Movimentacao.objects.select_related('produto').order_by('-data')[:5]

    hoje = timezone.now()
    inicio_ano = hoje.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    meses = []
    entradas_meses = []
    saidas_meses = []
    for i in range(12):
        mes = inicio_ano + timedelta(days=30 * i)
        label = mes.strftime('%b')
        meses.append(label)
        entradas = Movimentacao.objects.filter(
            tipo='ENTRADA', data__year=mes.year, data__month=mes.month
        ).count()
        saidas = Movimentacao.objects.filter(
            tipo='SAIDA', data__year=mes.year, data__month=mes.month
        ).count()
        entradas_meses.append(entradas)
        saidas_meses.append(saidas)

    valor_por_tipo = Produto.objects.values('tipo_produto').annotate(
        total=Sum(F('quantidade_base') * F('preco_custo'))
    ).order_by()
    tipo_choices = dict(Produto.TIPO_PRODUTO_CHOICES)
    tipo_labels = [tipo_choices.get(t['tipo_produto'], t['tipo_produto']) for t in valor_por_tipo]
    tipo_data = [float(t['total']) for t in valor_por_tipo]

    return render(request, 'estoque/dashboard.html', {
        'total_itens': total_itens,
        'valor_total': valor_total,
        'valor_venda_total': valor_venda_total,
        'lucro_estimado': valor_venda_total - valor_total,
        'estoque_baixo': estoque_baixo,
        'ultimas_movimentacoes': ultimas_movimentacoes,
        'ultimos_logs': LogAcao.objects.select_related('usuario').all()[:5],
        'chart_meses': json.dumps(meses),
        'chart_entradas': json.dumps(entradas_meses),
        'chart_saidas': json.dumps(saidas_meses),
        'chart_tipo_labels': json.dumps(tipo_labels),
        'chart_tipo_data': json.dumps(tipo_data),
    })


@login_required
def lista_produtos(request):
    produtos = Produto.objects.select_related('fornecedor').all().order_by('descricao')
    produtos_data = []
    for p in produtos:
        lucro = float(p.preco_venda) - float(p.preco_custo)
        margem = (lucro / float(p.preco_custo) * 100) if float(p.preco_custo) > 0 else 0
        produtos_data.append({
            'id': p.id,
            'descricao': p.descricao,
            'quantidade': float(p.quantidade_base),
            'estoque_minimo': float(p.estoque_minimo),
            'tipo_produto': p.tipo_produto,
            'fornecedor': p.fornecedor.nome if p.fornecedor else None,
            'preco_custo': float(p.preco_custo),
            'preco_venda': float(p.preco_venda),
            'lucro': round(lucro, 2),
            'margem': round(margem, 1),
            'metros_por_rolo': float(p.metros_por_rolo) if p.metros_por_rolo else 0,
            'litros_por_vidro': float(p.litros_por_vidro) if p.litros_por_vidro else 0,
            'tipo_tinta': p.tipo_tinta,
            'cor_tinta': p.cor_tinta,
            'unidade_medida': p.unidade_medida or 'UN',
        })
    return render(request, 'estoque/lista.html', {
        'produtos_json': json.dumps(produtos_data),
    })


@login_required
def atualiza_estoque(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        produto = Produto.objects.get(id=data['id'])
        produto.quantidade_base += data['variacao']
        produto.save()
        return JsonResponse({'ok': True, 'nova_quantidade': float(produto.quantidade_base)})
    return JsonResponse({'ok': False}, status=405)


@login_required
def registrar_movimentacao(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        produto = Produto.objects.get(id=data['produto_id'])
        Movimentacao.objects.create(
            produto=produto,
            tipo=data['tipo'],
            quantidade=data['quantidade'],
            observacao=data.get('observacao', ''),
        )
        log_acao(request.user, data['tipo'], f'{data["tipo"]} de {data["quantidade"]} de {produto.descricao}', 'Movimentacao')
        return JsonResponse({'ok': True})
    produtos = Produto.objects.all().values('id', 'descricao')
    return render(request, 'estoque/movimentacao.html', {'produtos': list(produtos)})


@login_required
def exportar_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="relatorio_estoque.csv"'

    writer = csv.writer(response)
    writer.writerow(['Descricao', 'Tipo', 'Fornecedor', 'Quantidade', 'Preco Custo', 'Preco Venda', 'Estoque Minimo'])
    produtos = Produto.objects.select_related('fornecedor').all()
    for p in produtos:
        writer.writerow([
            p.descricao,
            p.get_tipo_produto_display(),
            p.fornecedor.nome if p.fornecedor else '',
            float(p.quantidade_base),
            float(p.preco_custo),
            float(p.preco_venda),
            float(p.estoque_minimo),
        ])
    return response


@login_required
def cadastrar_produto(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        produto = Produto.objects.create(
            tipo_produto=data['tipo_produto'],
            descricao=data['descricao'],
            fornecedor_id=data.get('fornecedor_id') or None,
            quantidade_base=data.get('quantidade_base', 0),
            preco_custo=data.get('preco_custo', 0),
            preco_venda=data.get('preco_venda', 0),
            estoque_minimo=data.get('estoque_minimo', 0),
            metros_por_rolo=data.get('metros_por_rolo') or None,
            tipo_tinta=data.get('tipo_tinta', 'N/A'),
            cor_tinta=data.get('cor_tinta', 'INCOLOR'),
            litros_por_vidro=data.get('litros_por_vidro') or None,
            unidade_medida=data.get('unidade_medida', 'UN'),
        )
        log_acao(request.user, 'CRIAR', f'Cadastrou produto {produto.descricao}', 'Produto', produto.id)
        return JsonResponse({'ok': True, 'id': produto.id})
    fornecedores = Fornecedor.objects.all().values('id', 'nome')
    return render(request, 'estoque/cadastrar_produto.html', {
        'fornecedores': list(fornecedores),
    })


@login_required
def editar_produto(request, id):
    produto = get_object_or_404(Produto, id=id)
    if request.method == 'POST':
        data = json.loads(request.body)
        old_preco_custo = produto.preco_custo
        old_preco_venda = produto.preco_venda
        produto.tipo_produto = data['tipo_produto']
        produto.descricao = data['descricao']
        produto.fornecedor_id = data.get('fornecedor_id') or None
        produto.quantidade_base = data.get('quantidade_base', 0)
        produto.preco_custo = data.get('preco_custo', 0)
        produto.preco_venda = data.get('preco_venda', 0)
        produto.estoque_minimo = data.get('estoque_minimo', 0)
        produto.metros_por_rolo = data.get('metros_por_rolo') or None
        produto.tipo_tinta = data.get('tipo_tinta', 'N/A')
        produto.cor_tinta = data.get('cor_tinta', 'INCOLOR')
        produto.litros_por_vidro = data.get('litros_por_vidro') or None
        produto.unidade_medida = data.get('unidade_medida', 'UN')
        preco_custo_mudou = old_preco_custo != produto.preco_custo
        preco_venda_mudou = old_preco_venda != produto.preco_venda
        produto._historico_ja_salvo = True
        produto.save()
        if preco_custo_mudou or preco_venda_mudou:
            HistoricoPreco.objects.create(
                produto=produto,
                preco_custo_antigo=old_preco_custo if preco_custo_mudou else None,
                preco_custo_novo=produto.preco_custo if preco_custo_mudou else None,
                preco_venda_antigo=old_preco_venda if preco_venda_mudou else None,
                preco_venda_novo=produto.preco_venda if preco_venda_mudou else None,
                usuario=request.user,
            )
        log_acao(request.user, 'EDITAR', f'Editou produto {produto.descricao}', 'Produto', produto.id)
        return JsonResponse({'ok': True})
    fornecedores = Fornecedor.objects.all().values('id', 'nome')
    return render(request, 'estoque/editar_produto.html', {
        'produto': produto,
        'fornecedores': list(fornecedores),
        'produto_json': json.dumps({
            'id': produto.id,
            'tipo_produto': produto.tipo_produto,
            'descricao': produto.descricao,
            'fornecedor_id': produto.fornecedor_id or '',
            'quantidade_base': float(produto.quantidade_base) if produto.quantidade_base else '',
            'preco_custo': float(produto.preco_custo) if produto.preco_custo else '',
            'preco_venda': float(produto.preco_venda) if produto.preco_venda else '',
            'estoque_minimo': float(produto.estoque_minimo) if produto.estoque_minimo else '',
            'metros_por_rolo': float(produto.metros_por_rolo) if produto.metros_por_rolo else None,
            'tipo_tinta': produto.tipo_tinta,
            'cor_tinta': produto.cor_tinta,
            'litros_por_vidro': float(produto.litros_por_vidro) if produto.litros_por_vidro else None,
            'unidade_medida': produto.unidade_medida or 'UN',
        }),
    })


@login_required
def excluir_produto(request, id):
    produto = get_object_or_404(Produto, id=id)
    if request.method == 'POST':
        descricao = produto.descricao
        produto.delete()
        log_acao(request.user, 'EXCLUIR', f'Excluiu produto {descricao}', 'Produto', id)
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False}, status=405)


@login_required
def excluir_movimentacao(request, id):
    mov = get_object_or_404(Movimentacao, id=id)
    if request.method == 'POST':
        with transaction.atomic():
            produto = Produto.objects.select_for_update().get(pk=mov.produto.pk)
            if mov.tipo == 'ENTRADA':
                produto.quantidade_base -= mov.quantidade
            else:
                produto.quantidade_base += mov.quantidade
            produto.save()
            descricao = f'{mov.get_tipo_display()} de {mov.quantidade} de {mov.produto.descricao}'
            mov.delete()
        log_acao(request.user, 'EXCLUIR', f'Excluiu movimentacao: {descricao}', 'Movimentacao', id)
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False}, status=405)


@login_required
def detalhe_produto(request, id):
    produto = get_object_or_404(Produto, id=id)
    movimentacoes = Movimentacao.objects.filter(produto=produto).select_related('produto').order_by('-data')
    historico_precos = HistoricoPreco.objects.filter(produto=produto)[:20]
    lucro = float(produto.preco_venda) - float(produto.preco_custo)
    margem = (lucro / float(produto.preco_custo) * 100) if float(produto.preco_custo) > 0 else 0
    return render(request, 'estoque/detalhe.html', {
        'produto': produto,
        'movimentacoes': movimentacoes,
        'historico_precos': historico_precos,
        'lucro': round(lucro, 2),
        'margem': round(margem, 1),
    })


@login_required
def lista_ordens(request):
    ordens = OrdemCompra.objects.select_related('fornecedor').all()
    return render(request, 'estoque/lista_ordens.html', {'ordens': ordens})


@login_required
def criar_ordem(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        with transaction.atomic():
            ordem = OrdemCompra.objects.create(
                fornecedor_id=data.get('fornecedor_id') or None,
                observacao=data.get('observacao', ''),
            )
            for item in data.get('itens', []):
                ItemOrdemCompra.objects.create(
                    ordem=ordem,
                    produto_id=item['produto_id'],
                    quantidade=item['quantidade'],
                    preco_unitario=item['preco_unitario'],
                )
        log_acao(request.user, 'CRIAR', f'Criou ordem de compra #{ordem.id}', 'OrdemCompra', ordem.id)
        return JsonResponse({'ok': True, 'id': ordem.id})
    fornecedores = Fornecedor.objects.all().values('id', 'nome')
    produtos = Produto.objects.all().values('id', 'descricao', 'preco_custo')
    return render(request, 'estoque/criar_ordem.html', {
        'fornecedores': list(fornecedores),
        'produtos': list(produtos),
    })


@login_required
def detalhe_ordem(request, id):
    ordem = get_object_or_404(OrdemCompra.objects.select_related('fornecedor'), id=id)
    itens = ordem.itens.select_related('produto').all()
    itens_total = sum(item.quantidade * item.preco_unitario for item in itens)
    return render(request, 'estoque/detalhe_ordem.html', {
        'ordem': ordem,
        'itens': itens,
        'itens_total': itens_total,
    })


@login_required
def aprovar_ordem(request, id):
    ordem = get_object_or_404(OrdemCompra, id=id)
    if ordem.status != 'PENDENTE':
        return JsonResponse({'ok': False, 'erro': 'Ordem nao esta pendente.'}, status=400)
    ordem.status = 'APROVADA'
    ordem.save()
    log_acao(request.user, 'APROVAR', f'Aprovou ordem de compra #{ordem.id}', 'OrdemCompra', id)
    return JsonResponse({'ok': True})


@login_required
def cancelar_ordem(request, id):
    ordem = get_object_or_404(OrdemCompra, id=id)
    if ordem.status in ('RECEBIDA', 'CANCELADA'):
        return JsonResponse({'ok': False, 'erro': 'Ordem ja finalizada.'}, status=400)
    ordem.status = 'CANCELADA'
    ordem.save()
    log_acao(request.user, 'CANCELAR', f'Cancelou ordem de compra #{ordem.id}', 'OrdemCompra', id)
    return JsonResponse({'ok': True})


@login_required
def receber_ordem(request, id):
    ordem = get_object_or_404(OrdemCompra.objects.select_related('fornecedor'), id=id)
    if ordem.status != 'APROVADA':
        return JsonResponse({'ok': False, 'erro': 'Ordem precisa estar aprovada para ser recebida.'}, status=400)
    with transaction.atomic():
        itens = ordem.itens.select_related('produto').all()
        for item in itens:
            produto = Produto.objects.select_for_update().get(pk=item.produto.pk)
            produto.preco_custo = item.preco_unitario
            produto.save()
            Movimentacao.objects.create(
                produto=produto,
                tipo='ENTRADA',
                quantidade=item.quantidade,
                observacao=f'Recebimento da Ordem #{ordem.id}',
            )
        ordem.status = 'RECEBIDA'
        ordem.save()
    log_acao(request.user, 'RECEBER', f'Recebeu ordem de compra #{ordem.id} no estoque', 'OrdemCompra', id)
    return JsonResponse({'ok': True})


@login_required
def etiqueta_produto(request, id):
    produto = get_object_or_404(Produto, id=id)
    return render(request, 'estoque/etiqueta.html', {'produto': produto})


@login_required
def relatorio_mensal(request):
    hoje = timezone.now()
    data_inicio = request.GET.get('data_inicio', hoje.replace(day=1).strftime('%Y-%m-%d'))
    data_fim = request.GET.get('data_fim', hoje.strftime('%Y-%m-%d'))
    try:
        dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d').replace(tzinfo=timezone.get_current_timezone())
        dt_fim = datetime.strptime(data_fim, '%Y-%m-%d').replace(hour=23, minute=59, second=59, tzinfo=timezone.get_current_timezone())
    except ValueError:
        dt_inicio = hoje.replace(day=1)
        dt_fim = hoje

    movs = Movimentacao.objects.filter(data__gte=dt_inicio, data__lte=dt_fim).select_related('produto')

    total_entradas = movs.filter(tipo='ENTRADA').aggregate(s=Sum('quantidade'))['s'] or 0
    total_saidas = movs.filter(tipo='SAIDA').aggregate(s=Sum('quantidade'))['s'] or 0

    por_produto = movs.values('produto__descricao', 'tipo').annotate(
        total=Sum('quantidade')
    ).order_by('produto__descricao')

    movs_por_produto = {}
    for item in por_produto:
        nome = item['produto__descricao']
        if nome not in movs_por_produto:
            movs_por_produto[nome] = {'entradas': 0, 'saidas': 0}
        if item['tipo'] == 'ENTRADA':
            movs_por_produto[nome]['entradas'] += float(item['total'])
        else:
            movs_por_produto[nome]['saidas'] += float(item['total'])

    produtos_afetados = [
        {'nome': nome, 'entradas': d['entradas'], 'saidas': d['saidas'], 'saldo': d['entradas'] - d['saidas']}
        for nome, d in movs_por_produto.items()
    ]

    return render(request, 'estoque/relatorio.html', {
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'saldo_liquido': total_entradas - total_saidas,
        'total_movimentacoes': movs.count(),
        'produtos_afetados': produtos_afetados,
    })


@login_required
def log_acoes(request):
    logs = LogAcao.objects.select_related('usuario').all()[:50]
    return render(request, 'estoque/log_acoes.html', {'logs': logs})


@login_required
def lista_usuarios(request):
    from django.contrib.auth.models import User, Group
    if not request.user.is_superuser:
        return render(request, 'estoque/lista_usuarios.html', {'erro': 'Apenas administradores podem gerenciar usuarios.'})
    usuarios = User.objects.prefetch_related('groups').all()
    grupos = Group.objects.all()
    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        acao = data.get('acao')
        if acao == 'criar':
            user = User.objects.create_user(
                username=data['username'],
                password=data['password'],
                is_staff=True,
            )
            log_acao(request.user, 'CRIAR', f'Criou usuario {user.username}', 'User', user.id)
        elif acao == 'grupo':
            user = User.objects.get(id=data['user_id'])
            grupo = Group.objects.get(id=data['grupo_id'])
            user.groups.clear()
            user.groups.add(grupo)
            user.is_superuser = (grupo.name == 'Admin')
            user.save()
            log_acao(request.user, 'EDITAR', f'Alterou grupo do usuario {user.username} para {grupo.name}', 'User', user.id)
        return JsonResponse({'ok': True})
    return render(request, 'estoque/lista_usuarios.html', {
        'usuarios': usuarios,
        'grupos': grupos,
    })


@login_required
def template_csv_produtos(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="modelo_importacao_produtos.csv"'
    writer = csv.writer(response)
    writer.writerow(['descricao', 'tipo_produto', 'qt_rolos', 'metros_por_rolo', 'quantidade_base', 'qt_vidros', 'litros_por_vidro', 'preco_custo', 'preco_venda', 'estoque_minimo', 'observacao'])
    writer.writerow(['PAPEL TUCANO', 'PAPEL', '11', '500', '', '', '', '0', '0', '0', ''])
    writer.writerow(['TACTEL - ALEXANDRE', 'TECIDO', '', '', '600', '', '', '0', '0', '0', ''])
    writer.writerow(['BLACK SUBLIMACAO', 'TINTA', '', '', '', '7', '1', '0', '0', '0', ''])
    writer.writerow(['FIO NAUTICO BRANCO', 'AVIAMENTO', '', '', '19', '', '', '0', '0', '0', 'Largura 5mm'])
    return response


@login_required
def importar_csv_produtos(request):
    if request.method == 'POST' and request.FILES.get('arquivo'):
        arquivo = request.FILES['arquivo']
        if not arquivo.name.endswith('.csv'):
            return JsonResponse({'ok': False, 'erro': 'Por favor, envie um arquivo .csv válido.'}, status=400)
            
        try:
            decoded_file = arquivo.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            produtos_criados = 0
            
            with transaction.atomic():
                for row in reader:
                    keys = [k for k in row.keys() if k]
                    descricao_key = next((k for k in keys if 'descricao' in k.lower()), None)
                    if not descricao_key:
                        raise ValueError("Coluna 'descricao' não encontrada no cabeçalho.")
                    
                    descricao = row.get(descricao_key, '').strip()
                    if not descricao:
                        continue
                        
                    tipo = row.get('tipo_produto', 'OUTRO').strip().upper()
                    if tipo not in [c[0] for c in Produto.TIPO_PRODUTO_CHOICES]:
                        tipo = 'OUTRO'
                        
                    def parse_decimal(val):
                        if not val:
                            return 0.0
                        return float(str(val).replace(',', '.').strip())
                        
                    qt_rolos = parse_decimal(row.get('qt_rolos'))
                    metros_por_rolo = parse_decimal(row.get('metros_por_rolo'))
                    qt_vidros = parse_decimal(row.get('qt_vidros'))
                    litros_por_vidro = parse_decimal(row.get('litros_por_vidro'))
                    quantidade_base = parse_decimal(row.get('quantidade_base'))
                    
                    if tipo in ['TECIDO', 'PAPEL'] and qt_rolos > 0 and metros_por_rolo > 0 and quantidade_base == 0:
                        quantidade_base = qt_rolos * metros_por_rolo
                    elif tipo == 'TINTA' and qt_vidros > 0 and litros_por_vidro > 0 and quantidade_base == 0:
                        quantidade_base = qt_vidros * litros_por_vidro
                        
                    desc_com_obs = descricao
                    obs = row.get('observacao', '').strip()
                    if tipo == 'AVIAMENTO' and obs:
                        desc_com_obs = f"{descricao} ({obs})"
                        
                    Produto.objects.create(
                        descricao=desc_com_obs,
                        tipo_produto=tipo,
                        quantidade_base=quantidade_base,
                        metros_por_rolo=metros_por_rolo if metros_por_rolo > 0 else None,
                        litros_por_vidro=litros_por_vidro if litros_por_vidro > 0 else None,
                        preco_custo=parse_decimal(row.get('preco_custo')),
                        preco_venda=parse_decimal(row.get('preco_venda')),
                        estoque_minimo=parse_decimal(row.get('estoque_minimo')),
                    )
                    produtos_criados += 1
            
            log_acao(request.user, 'CRIAR', f'Importou {produtos_criados} produtos via CSV', 'Produto')
            return JsonResponse({'ok': True, 'mensagem': f'{produtos_criados} produtos importados com sucesso!'})
            
        except Exception as e:
            return JsonResponse({'ok': False, 'erro': f'Erro ao processar arquivo: {str(e)}'}, status=400)
            
    return JsonResponse({'ok': False, 'erro': 'Método não permitido ou arquivo não enviado.'}, status=400)


@login_required
def importar_nfe(request):
    """
    Passo 1: Recebe os XMLs da NF-e (um ou mais arquivos, ou URL) e retorna os itens parseados
    em JSON para o frontend exibir o preview editável.
    GET  → renderiza a tela de importação
    POST → processa os XMLs e retorna JSON com os itens
    """
    if request.method == 'GET':
        return render(request, 'estoque/importar_nfe.html')

    # POST: processar XML
    try:
        url = request.POST.get('url', '').strip()
        arquivos = request.FILES.getlist('arquivo')

        itens_acumulados = []
        fornecedores_detectados = set()
        nfs_detectadas = set()

        if url:
            xml_content = fetch_xml_from_url(url)
            parsed = parse_nfe_xml(xml_content)
            fornecedor_nome = parsed['fornecedor'].get('nome', '').strip()
            numero_nf = parsed.get('numero_nf', '').strip()
            if fornecedor_nome:
                fornecedores_detectados.add(fornecedor_nome)
            if numero_nf:
                nfs_detectadas.add(numero_nf)

            for item in parsed['itens']:
                item['fornecedor_nome'] = fornecedor_nome
                item['numero_nf'] = numero_nf
                itens_acumulados.append(item)
        elif arquivos:
            for arquivo in arquivos:
                if not arquivo.name.lower().endswith('.xml'):
                    return JsonResponse({'ok': False, 'erro': f'O arquivo "{arquivo.name}" não é um XML válido.'}, status=400)
                xml_content = arquivo.read().decode('utf-8', errors='replace')
                parsed = parse_nfe_xml(xml_content)
                fornecedor_nome = parsed['fornecedor'].get('nome', '').strip()
                numero_nf = parsed.get('numero_nf', '').strip()
                if fornecedor_nome:
                    fornecedores_detectados.add(fornecedor_nome)
                if numero_nf:
                    nfs_detectadas.add(numero_nf)

                for item in parsed['itens']:
                    item['fornecedor_nome'] = fornecedor_nome
                    item['numero_nf'] = numero_nf
                    itens_acumulados.append(item)
        else:
            return JsonResponse({'ok': False, 'erro': 'Informe um ou mais arquivos XML ou uma URL.'}, status=400)

        # Verifica quais produtos já existem (busca por descrição similar)
        for item in itens_acumulados:
            descricao_lower = item['descricao'].lower()
            similares = Produto.objects.filter(
                descricao__icontains=descricao_lower[:30]
            ).values('id', 'descricao', 'quantidade_base')
            item['similares'] = list(similares)

        # Prepara a resposta consolidada
        resultado = {
            'numero_nf': ', '.join(sorted(list(nfs_detectadas))),
            'fornecedor': {
                'nome': ', '.join(sorted(list(fornecedores_detectados))) if len(fornecedores_detectados) <= 2 else 'Múltiplos Fornecedores'
            },
            'itens': itens_acumulados
        }

        return JsonResponse({'ok': True, 'dados': resultado})

    except ValueError as e:
        return JsonResponse({'ok': False, 'erro': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'erro': f'Erro inesperado ao processar XML: {str(e)}'}, status=500)


@login_required
def confirmar_importacao_nfe(request):
    """
    Passo 2: Recebe os itens confirmados/editados pelo usuário e cria os produtos.
    Cada item pode ter:
    - importar: bool (se false, pula este item)
    - acao: 'criar' | 'atualizar' (se atualizar, soma quantidade ao produto existente)
    - produto_existente_id: int (se acao=atualizar)
    - fornecedor_nome: str (específico do item)
    - numero_nf: str (específico do item)
    """
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'erro': 'Método não permitido.'}, status=405)

    try:
        data = json.loads(request.body)
        global_fornecedor_nome = data.get('fornecedor_nome', '').strip()
        itens = data.get('itens', [])

        criados = 0
        atualizados = 0
        ignorados = 0
        nfs_processadas = set()

        with transaction.atomic():
            for item in itens:
                if not item.get('importar', True):
                    ignorados += 1
                    continue

                acao = item.get('acao', 'criar')
                produto_existente_id = item.get('produto_existente_id')
                item_fornecedor_nome = item.get('fornecedor_nome', '').strip() or global_fornecedor_nome
                item_numero_nf = item.get('numero_nf', '').strip() or data.get('numero_nf', '')
                
                if item_numero_nf:
                    nfs_processadas.add(item_numero_nf)

                # Cria ou recupera o fornecedor específico do item
                item_fornecedor = None
                if item_fornecedor_nome:
                    item_fornecedor, _ = Fornecedor.objects.get_or_create(
                        nome__iexact=item_fornecedor_nome,
                        defaults={'nome': item_fornecedor_nome}
                    )

                if acao == 'atualizar' and produto_existente_id:
                    # Atualiza o estoque do produto existente via Movimentacao
                    try:
                        produto = Produto.objects.get(pk=produto_existente_id)
                        Movimentacao.objects.create(
                            produto=produto,
                            tipo='ENTRADA',
                            quantidade=item['quantidade'],
                            observacao=f'Importação NF-e: {item_numero_nf}',
                        )
                        # Atualiza preço de custo se veio da nota e for maior que 0
                        if item.get('preco_custo', 0) > 0:
                            produto.preco_custo = item['preco_custo']
                            produto.save()
                        atualizados += 1
                    except Produto.DoesNotExist:
                        pass
                else:
                    # Cria novo produto
                    Produto.objects.create(
                        descricao=item['descricao'],
                        tipo_produto=item.get('tipo_produto', 'OUTRO'),
                        unidade_medida=item.get('unidade_medida', 'UN'),
                        quantidade_base=item['quantidade'],
                        preco_custo=item.get('preco_custo', 0),
                        fornecedor=item_fornecedor,
                    )
                    criados += 1

        nfs_str = ', '.join(sorted(list(nfs_processadas)))
        descricao_log = f'Importou itens da(s) NF-e ({nfs_str}): {criados} produtos criados, {atualizados} atualizados'
        log_acao(request.user, 'CRIAR', descricao_log, 'Produto')

        return JsonResponse({
            'ok': True,
            'criados': criados,
            'atualizados': atualizados,
            'ignorados': ignorados,
        })

    except Exception as e:
        return JsonResponse({'ok': False, 'erro': f'Erro ao confirmar importação: {str(e)}'}, status=500)


# ─────────────────────────────────────────────
#  FORNECEDORES
# ─────────────────────────────────────────────

@login_required
def lista_fornecedores(request):
    qs = Fornecedor.objects.annotate(total_produtos=Count('produto')).order_by('nome')
    fornecedores_data = [
        {
            'id': f.id, 'nome': f.nome, 'cnpj': f.cnpj,
            'email': f.email, 'telefone': f.telefone or '',
            'observacao': f.observacao, 'total_produtos': f.total_produtos,
        }
        for f in qs
    ]
    return render(request, 'estoque/fornecedores/lista.html', {
        'fornecedores': qs,
        'fornecedores_json': json.dumps(fornecedores_data),
    })


@login_required
def salvar_fornecedor(request, id=None):
    """Cria (id=None) ou edita (id=int) um fornecedor via JSON."""
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    data = json.loads(request.body)
    nome = data.get('nome', '').strip()
    if not nome:
        return JsonResponse({'ok': False, 'erro': 'Nome é obrigatório.'}, status=400)

    if id:
        fornecedor = get_object_or_404(Fornecedor, id=id)
        acao = 'EDITAR'
    else:
        fornecedor = Fornecedor()
        acao = 'CRIAR'

    fornecedor.nome = nome
    fornecedor.cnpj = data.get('cnpj', '').strip()
    fornecedor.email = data.get('email', '').strip()
    fornecedor.telefone = data.get('telefone', '').strip()
    fornecedor.observacao = data.get('observacao', '').strip()
    fornecedor.save()
    log_acao(request.user, acao, f'{acao} fornecedor: {fornecedor.nome}', 'Fornecedor', fornecedor.id)
    return JsonResponse({'ok': True, 'id': fornecedor.id})


@login_required
def excluir_fornecedor(request, id):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    fornecedor = get_object_or_404(Fornecedor, id=id)
    nome = fornecedor.nome
    fornecedor.delete()
    log_acao(request.user, 'EXCLUIR', f'Excluiu fornecedor: {nome}', 'Fornecedor', id)
    return JsonResponse({'ok': True})


# ─────────────────────────────────────────────
#  CATEGORIAS
# ─────────────────────────────────────────────

@login_required
def lista_categorias(request):
    qs = Categoria.objects.annotate(total_produtos=Count('produtos')).order_by('nome')
    categorias_data = [
        {'id': c.id, 'nome': c.nome, 'descricao': c.descricao, 'cor': c.cor, 'total_produtos': c.total_produtos}
        for c in qs
    ]
    return render(request, 'estoque/categorias/lista.html', {
        'categorias': qs,
        'categorias_json': json.dumps(categorias_data),
    })


@login_required
def salvar_categoria(request, id=None):
    """Cria (id=None) ou edita (id=int) uma categoria via JSON."""
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    data = json.loads(request.body)
    nome = data.get('nome', '').strip()
    if not nome:
        return JsonResponse({'ok': False, 'erro': 'Nome é obrigatório.'}, status=400)

    if id:
        categoria = get_object_or_404(Categoria, id=id)
        acao = 'EDITAR'
    else:
        categoria = Categoria()
        acao = 'CRIAR'

    categoria.nome = nome
    categoria.descricao = data.get('descricao', '').strip()
    categoria.cor = data.get('cor', '#6c757d').strip()
    categoria.save()
    log_acao(request.user, acao, f'{acao} categoria: {categoria.nome}', 'Categoria', categoria.id)
    return JsonResponse({'ok': True, 'id': categoria.id})


@login_required
def excluir_categoria(request, id):
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    categoria = get_object_or_404(Categoria, id=id)
    nome = categoria.nome
    categoria.delete()
    log_acao(request.user, 'EXCLUIR', f'Excluiu categoria: {nome}', 'Categoria', id)
    return JsonResponse({'ok': True})


@login_required
def lista_fechamentos(request):
    fechamentos = FechamentoMensal.objects.prefetch_related('itens').select_related('usuario').all()
    fechamentos_json = []
    for f in fechamentos:
        total_itens = f.itens.count()
        valor_total = sum(float(item.quantidade * item.preco_custo) for item in f.itens.all())
        fechamentos_json.append({
            'id': f.id,
            'data_fechamento': f.data_fechamento.strftime('%d/%m/%Y %H:%M'),
            'usuario': f.usuario.username if f.usuario else '-',
            'referencia_mes_ano': f.referencia_mes_ano,
            'observacao': f.observacao,
            'total_itens': total_itens,
            'valor_total': valor_total,
        })
    return render(request, 'estoque/fechamentos.html', {
        'fechamentos_json': json.dumps(fechamentos_json),
    })


@login_required
def realizar_fechamento(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'erro': 'Método não permitido.'}, status=405)
    try:
        data = json.loads(request.body)
        referencia = data.get('referencia_mes_ano', '').strip()
        observacao = data.get('observacao', '').strip()
        if not referencia:
            return JsonResponse({'ok': False, 'erro': 'Mês/Ano de referência é obrigatório.'}, status=400)
            
        if FechamentoMensal.objects.filter(referencia_mes_ano=referencia).exists():
            return JsonResponse({'ok': False, 'erro': f'Já existe um fechamento realizado para o mês {referencia}.'}, status=400)
            
        with transaction.atomic():
            fechamento = FechamentoMensal.objects.create(
                usuario=request.user,
                referencia_mes_ano=referencia,
                observacao=observacao,
            )
            produtos = Produto.objects.all()
            for p in produtos:
                ItemFechamento.objects.create(
                    fechamento=fechamento,
                    produto=p,
                    descricao=p.descricao,
                    quantidade=p.quantidade_base,
                    preco_custo=p.preco_custo,
                    preco_venda=p.preco_venda,
                )
        log_acao(request.user, 'CRIAR', f'Realizou fechamento de estoque para o mês {referencia}', 'FechamentoMensal', fechamento.id)
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'erro': f'Erro ao realizar fechamento: {str(e)}'}, status=500)


@login_required
def exportar_fechamento_xlsx(request, id):
    fechamento = get_object_or_404(FechamentoMensal, id=id)
    itens = fechamento.itens.select_related('produto', 'produto__fornecedor').all().order_by('descricao')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Fechamento {fechamento.referencia_mes_ano.replace('/', '_')}"

    font_title = Font(name='Segoe UI', size=16, bold=True, color='1E293B')
    font_header = Font(name='Segoe UI', size=11, bold=True, color='FFFFFF')
    font_data = Font(name='Segoe UI', size=11, color='1E293B')
    font_total = Font(name='Segoe UI', size=11, bold=True, color='1E293B')
    
    fill_header = PatternFill(start_color='4F46E5', end_color='4F46E5', fill_type='solid')
    fill_total = PatternFill(start_color='F1F5F9', end_color='F1F5F9', fill_type='solid')
    
    border_thin = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )
    
    ws.merge_cells('A1:I1')
    ws['A1'] = f"S.G.E - Fechamento de Estoque ({fechamento.referencia_mes_ano})"
    ws['A1'].font = font_title
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 40

    ws.merge_cells('A2:I2')
    ws['A2'] = f"Realizado em: {fechamento.data_fechamento.strftime('%d/%m/%Y %H:%M')} por {fechamento.usuario.username if fechamento.usuario else '-'}"
    ws['A2'].font = Font(name='Segoe UI', size=10, italic=True)
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[2].height = 20

    headers = [
        "Descrição do Material", "Tipo", "Fornecedor", 
        "Unid.", "Quantidade", "Preço Custo", 
        "Preço Venda", "Total Custo", "Total Venda"
    ]
    
    ws.append([])
    ws.row_dimensions[4].height = 28
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_num)
        cell.value = header
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal='center' if col_num > 3 else 'left', vertical='center')
        cell.border = border_thin

    start_row = 5
    for item in itens:
        tipo = item.produto.get_tipo_produto_display() if item.produto else '-'
        fornecedor = item.produto.fornecedor.nome if (item.produto and item.produto.fornecedor) else '-'
        unidade = item.produto.get_unidade_medida_display() if item.produto else 'Unidade'
        
        row_data = [
            item.descricao,
            tipo,
            fornecedor,
            unidade,
            float(item.quantidade),
            float(item.preco_custo),
            float(item.preco_venda),
            f"=E{ws.max_row+1}*F{ws.max_row+1}",
            f"=E{ws.max_row+1}*G{ws.max_row+1}",
        ]
        
        ws.append(row_data)
        current_row = ws.max_row
        ws.row_dimensions[current_row].height = 20
        
        for col_idx in range(1, 10):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.font = font_data
            cell.border = border_thin
            
            if col_idx in (4, 5):
                cell.alignment = Alignment(horizontal='center', vertical='center')
            elif col_idx in (6, 7, 8, 9):
                cell.alignment = Alignment(horizontal='right', vertical='center')
            else:
                cell.alignment = Alignment(horizontal='left', vertical='center')
                
            if col_idx in (6, 7, 8, 9):
                cell.number_format = 'R$ #,##0.00'
            elif col_idx == 5:
                cell.number_format = '#,##0.00'

    end_row = ws.max_row
    ws.append([
        "TOTAL GERAL", "", "", "", 
        f"=SUM(E{start_row}:E{end_row})", "", "", 
        f"=SUM(H{start_row}:H{end_row})", 
        f"=SUM(I{start_row}:I{end_row})"
    ])
    
    total_row = ws.max_row
    ws.row_dimensions[total_row].height = 26
    
    for col_idx in range(1, 10):
        cell = ws.cell(row=total_row, column=col_idx)
        cell.font = font_total
        cell.fill = fill_total
        cell.border = border_thin
        
        if col_idx in (5, 8, 9):
            cell.alignment = Alignment(horizontal='center' if col_idx == 5 else 'right', vertical='center')
            if col_idx in (8, 9):
                cell.number_format = 'R$ #,##0.00'
            else:
                cell.number_format = '#,##0.00'
        else:
            cell.alignment = Alignment(horizontal='left', vertical='center')

    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        
        for cell in col:
            if cell.row > 2 and cell.value:
                val_str = str(cell.value)
                if val_str.startswith('='):
                    val_str = "R$ 999.999,99"
                max_len = max(max_len, len(val_str))
                
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="fechamento_estoque_{fechamento.referencia_mes_ano.replace("/", "_")}.xlsx"'
    wb.save(response)
    return response


@login_required
def exportar_atual_xlsx(request):
    produtos = Produto.objects.select_related('fornecedor').all().order_by('descricao')

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Estoque Atual"

    font_title = Font(name='Segoe UI', size=16, bold=True, color='1E293B')
    font_header = Font(name='Segoe UI', size=11, bold=True, color='FFFFFF')
    font_data = Font(name='Segoe UI', size=11, color='1E293B')
    font_total = Font(name='Segoe UI', size=11, bold=True, color='1E293B')
    
    fill_header = PatternFill(start_color='0D6EFD', end_color='0D6EFD', fill_type='solid')
    fill_total = PatternFill(start_color='F1F5F9', end_color='F1F5F9', fill_type='solid')
    
    border_thin = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )
    
    ws.merge_cells('A1:I1')
    ws['A1'] = "S.G.E - Relatório de Posição de Estoque Atual"
    ws['A1'].font = font_title
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[1].height = 40

    ws.merge_cells('A2:I2')
    ws['A2'] = f"Gerado em: {timezone.now().strftime('%d/%m/%Y %H:%M')}"
    ws['A2'].font = Font(name='Segoe UI', size=10, italic=True)
    ws['A2'].alignment = Alignment(horizontal='center', vertical='center')
    ws.row_dimensions[2].height = 20

    headers = [
        "Descrição do Material", "Tipo", "Fornecedor", 
        "Unid.", "Quantidade", "Preço Custo", 
        "Preço Venda", "Total Custo", "Total Venda"
    ]
    
    ws.append([])
    ws.row_dimensions[4].height = 28
    
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col_num)
        cell.value = header
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = Alignment(horizontal='center' if col_num > 3 else 'left', vertical='center')
        cell.border = border_thin

    start_row = 5
    for p in produtos:
        tipo = p.get_tipo_produto_display()
        fornecedor = p.fornecedor.nome if p.fornecedor else '-'
        unidade = p.get_unidade_medida_display()
        
        row_data = [
            p.descricao,
            tipo,
            fornecedor,
            unidade,
            float(p.quantidade_base),
            float(p.preco_custo),
            float(p.preco_venda),
            f"=E{ws.max_row+1}*F{ws.max_row+1}",
            f"=E{ws.max_row+1}*G{ws.max_row+1}",
        ]
        
        ws.append(row_data)
        current_row = ws.max_row
        ws.row_dimensions[current_row].height = 20
        
        for col_idx in range(1, 10):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.font = font_data
            cell.border = border_thin
            
            if col_idx in (4, 5):
                cell.alignment = Alignment(horizontal='center', vertical='center')
            elif col_idx in (6, 7, 8, 9):
                cell.alignment = Alignment(horizontal='right', vertical='center')
            else:
                cell.alignment = Alignment(horizontal='left', vertical='center')
                
            if col_idx in (6, 7, 8, 9):
                cell.number_format = 'R$ #,##0.00'
            elif col_idx == 5:
                cell.number_format = '#,##0.00'

    end_row = ws.max_row
    ws.append([
        "TOTAL GERAL", "", "", "", 
        f"=SUM(E{start_row}:E{end_row})", "", "", 
        f"=SUM(H{start_row}:H{end_row})", 
        f"=SUM(I{start_row}:I{end_row})"
    ])
    
    total_row = ws.max_row
    ws.row_dimensions[total_row].height = 26
    
    for col_idx in range(1, 10):
        cell = ws.cell(row=total_row, column=col_idx)
        cell.font = font_total
        cell.fill = fill_total
        cell.border = border_thin
        
        if col_idx in (5, 8, 9):
            cell.alignment = Alignment(horizontal='center' if col_idx == 5 else 'right', vertical='center')
            if col_idx in (8, 9):
                cell.number_format = 'R$ #,##0.00'
            else:
                cell.number_format = '#,##0.00'
        else:
            cell.alignment = Alignment(horizontal='left', vertical='center')

    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row > 2 and cell.value:
                val_str = str(cell.value)
                if val_str.startswith('='):
                    val_str = "R$ 999.999,99"
                max_len = max(max_len, len(val_str))
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="relatorio_posicao_estoque_atual.xlsx"'
    wb.save(response)
    return response


@login_required
def busca_rapida(request):
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'resultados': []})
    
    produtos = Produto.objects.filter(
        Q(descricao__icontains=q) | Q(fornecedor__nome__icontains=q)
    ).select_related('fornecedor')[:10]
    
    resultados = [
        {
            'id': p.id,
            'descricao': p.descricao,
            'tipo_produto': p.get_tipo_produto_display(),
            'quantidade': float(p.quantidade_base),
            'unidade': p.get_unidade_medida_display() or '',
        }
        for p in produtos
    ]
    return JsonResponse({'resultados': resultados})
