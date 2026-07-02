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
from .models import Fornecedor, HistoricoPreco, ItemOrdemCompra, LogAcao, Movimentacao, OrdemCompra, Produto


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
    page = request.GET.get('page', 1)
    produtos = Produto.objects.select_related('fornecedor').all().order_by('descricao')
    paginator = Paginator(produtos, 50)
    page_obj = paginator.get_page(page)
    produtos_data = []
    for p in page_obj:
        lucro = float(p.preco_venda) - float(p.preco_custo)
        margem = (lucro / float(p.preco_custo) * 100) if float(p.preco_custo) > 0 else 0
        produtos_data.append({
            'id': p.id,
            'descricao': p.descricao,
            'quantidade': float(p.quantidade_base),
            'tipo_produto': p.tipo_produto,
            'fornecedor': p.fornecedor.nome if p.fornecedor else None,
            'preco_custo': float(p.preco_custo),
            'preco_venda': float(p.preco_venda),
            'lucro': round(lucro, 2),
            'margem': round(margem, 1),
        })
    return render(request, 'estoque/lista.html', {
        'produtos': page_obj,
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
