import csv
import json
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .log_utils import log_acao
from .models import Categoria, Fornecedor, HistoricoPreco, ItemOrdemCompra, LogAcao, Movimentacao, OrdemCompra, Produto, FechamentoMensal, ItemFechamento
from .services.estoque_metrics import agrupar_quantidade_por_unidade, serializar_totais_unidade, valor_por_tipo
from .services.estoque_status import filtro_baixo, filtro_zerado
from .services.estoque_valuation import calcular_valor_estoque
from .services.units import decimal_br, dinheiro_br, formatar_capacidade_embalagem, formatar_quantidade, unidade_base_codigo, unidade_info
from .services.usernames import validate_username_available

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def decimal_ou_none(value):
    if value in (None, ''):
        return None
    return Decimal(str(value))


@login_required
def dashboard(request):
    produtos_base = Produto.objects.select_related('fornecedor').all()
    produtos_lista = list(produtos_base)
    total_itens = len(produtos_lista)
    estoque_zerado_count = Produto.objects.filter(filtro_zerado()).count()
    estoque_baixo = Produto.objects.filter(filtro_baixo()).select_related('fornecedor')
    valuation = calcular_valor_estoque(produtos_lista)
    ultimas_movimentacoes = Movimentacao.objects.select_related('produto', 'usuario').order_by('-data')[:5]

    hoje = timezone.now()
    ano_atual = hoje.year
    try:
        ano_selecionado = int(request.GET.get('ano', ano_atual))
    except ValueError:
        ano_selecionado = ano_atual

    # Obter anos que possuem movimentações para o seletor
    anos_disponiveis = list(Movimentacao.objects.dates('data', 'year', order='DESC'))
    anos = sorted(list(set([a.year for a in anos_disponiveis] + [ano_atual])), reverse=True)
    
    # Gerar dados mensais corretos para o ano selecionado
    meses_nomes = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    entradas_meses = []
    saidas_meses = []
    for m in range(1, 13):
        entradas = Movimentacao.objects.filter(
            tipo='ENTRADA', data__year=ano_selecionado, data__month=m
        ).count()
        saidas = Movimentacao.objects.filter(
            tipo='SAIDA', data__year=ano_selecionado, data__month=m
        ).count()
        entradas_meses.append(entradas)
        saidas_meses.append(saidas)

    if request.GET.get('ajax') == '1':
        return JsonResponse({
            'meses': meses_nomes,
            'entradas': entradas_meses,
            'saidas': saidas_meses,
        })

    valores_por_tipo = valor_por_tipo(produtos_lista)
    tipo_choices = dict(Produto.TIPO_PRODUTO_CHOICES)
    tipo_labels = [tipo_choices.get(tipo, tipo) for tipo in valores_por_tipo.keys()]
    tipo_data = [float(total) for total in valores_por_tipo.values()]

    valor_total = valuation.valor_conhecido

    return render(request, 'estoque/dashboard.html', {
        'total_itens': total_itens,
        'estoque_zerado_count': estoque_zerado_count,
        'valor_total': valor_total,
        'valuation': valuation,
        'valor_total_formatado': dinheiro_br(valor_total),
        'estoque_baixo': estoque_baixo,
        'ultimas_movimentacoes': ultimas_movimentacoes,
        'ultimos_logs': LogAcao.objects.select_related('usuario').all()[:5],
        'chart_meses': json.dumps(meses_nomes),
        'chart_entradas': json.dumps(entradas_meses),
        'chart_saidas': json.dumps(saidas_meses),
        'chart_tipo_labels': json.dumps(tipo_labels),
        'chart_tipo_data': json.dumps(tipo_data),
        'anos_disponiveis': anos,
        'ano_selecionado': ano_selecionado,
    })


@login_required
def lista_produtos(request):
    produtos = Produto.objects.select_related('fornecedor', 'categoria').all().order_by('descricao')
    produtos_data = []
    for p in produtos:
        preco_custo = p.preco_custo
        preco_venda = p.preco_venda
        lucro = (preco_venda - preco_custo) if preco_venda is not None and preco_custo is not None else None
        margem = (lucro / preco_custo * 100) if lucro is not None and preco_custo and preco_custo > 0 else None
        unidade = unidade_info(p)
        produtos_data.append({
            'id': p.id,
            'descricao': p.descricao,
            'quantidade': float(p.quantidade_base),
            'quantidade_formatada': p.quantidade_formatada,
            'estoque_minimo': float(p.estoque_minimo) if p.estoque_minimo is not None else None,
            'estoque_minimo_formatado': formatar_quantidade(p.estoque_minimo, unidade.codigo) if p.estoque_minimo is not None else 'Sem mínimo',
            'status_estoque': p.status_estoque,
            'tipo_produto': p.tipo_produto,
            'tipo_label': p.get_tipo_produto_display(),
            'fornecedor': p.fornecedor.nome if p.fornecedor else None,
            'categoria_id': p.categoria_id,
            'categoria': p.categoria.nome if p.categoria else None,
            'preco_custo': float(preco_custo) if preco_custo is not None else None,
            'preco_venda': float(preco_venda) if preco_venda is not None else None,
            'preco_custo_formatado': dinheiro_br(preco_custo) if preco_custo is not None else 'Não cadastrado',
            'preco_venda_formatado': dinheiro_br(preco_venda) if preco_venda is not None else 'Não cadastrado',
            'lucro': float(lucro) if lucro is not None else None,
            'margem': float(round(margem, 1)) if margem is not None else None,
            'metros_por_rolo': float(p.metros_por_rolo) if p.metros_por_rolo else 0,
            'litros_por_vidro': float(p.litros_por_vidro) if p.litros_por_vidro else 0,
            'capacidade_embalagem': formatar_capacidade_embalagem(p),
            'embalagens_estimadas': float(p.quantidade_rolos_estimada if p.tipo_produto in ('PAPEL', 'TECIDO') else p.quantidade_vidros_estimada),
            'tipo_tinta': p.tipo_tinta,
            'cor_tinta': p.cor_tinta,
            'unidade_medida': unidade.codigo,
            'unidade_simbolo': unidade.simbolo,
            'unidade_nome': unidade.singular,
        })
    return render(request, 'estoque/lista.html', {
        'produtos_json': json.dumps(produtos_data),
    })


@login_required
def atualiza_estoque(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            produto = Produto.objects.get(id=data['id'])
            variacao = Decimal(str(data['variacao']))
            if variacao == 0:
                return JsonResponse({'ok': True, 'nova_quantidade': float(produto.quantidade_base), 'nova_quantidade_formatada': produto.quantidade_formatada})
            tipo = 'ENTRADA' if variacao > 0 else 'SAIDA'
            quantidade = abs(variacao)
            with transaction.atomic():
                Movimentacao.objects.create(
                    produto=produto,
                    usuario=request.user,
                    tipo=tipo,
                    quantidade=quantidade,
                    observacao='Ajuste rápido de estoque',
                )
            produto.refresh_from_db()
            return JsonResponse({'ok': True, 'nova_quantidade': float(produto.quantidade_base), 'nova_quantidade_formatada': produto.quantidade_formatada, 'status_estoque': produto.status_estoque})
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'erro': 'JSON inválido.'}, status=400)
        except KeyError as e:
            return JsonResponse({'ok': False, 'erro': f'Campo obrigatório ausente: {e.args[0]}.'}, status=400)
        except (InvalidOperation, TypeError, ValueError):
            return JsonResponse({'ok': False, 'erro': 'Variação de estoque inválida.'}, status=400)
        except Produto.DoesNotExist:
            return JsonResponse({'ok': False, 'erro': 'Produto não encontrado.'}, status=404)
        except ValidationError as e:
            return JsonResponse({'ok': False, 'erro': '; '.join(e.messages)}, status=400)
    return JsonResponse({'ok': False}, status=405)


@login_required
def registrar_movimentacao(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            produto = Produto.objects.get(id=data['produto_id'])
            Movimentacao.objects.create(
                produto=produto,
                usuario=request.user,
                tipo=data['tipo'],
                quantidade=data['quantidade'],
                observacao=data.get('observacao', ''),
            )
            log_acao(request.user, data['tipo'], f'{data["tipo"]} de {data["quantidade"]} de {produto.descricao}', 'Movimentacao')
            return JsonResponse({'ok': True})
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'erro': 'JSON inválido.'}, status=400)
        except KeyError as e:
            return JsonResponse({'ok': False, 'erro': f'Campo obrigatório ausente: {e.args[0]}.'}, status=400)
        except Produto.DoesNotExist:
            return JsonResponse({'ok': False, 'erro': 'Produto não encontrado.'}, status=404)
        except ValidationError as e:
            return JsonResponse({'ok': False, 'erro': '; '.join(e.messages)}, status=400)
    produtos = Produto.objects.all().values('id', 'descricao')
    movimentacoes = Movimentacao.objects.select_related('produto', 'usuario').order_by('-data')[:50]
    return render(request, 'estoque/movimentacao.html', {
        'produtos': list(produtos),
        'movimentacoes': movimentacoes,
    })


@login_required
def exportar_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="relatorio_estoque.csv"'

    writer = csv.writer(response)
    writer.writerow(['Descricao', 'Tipo', 'Fornecedor', 'Unidade Base', 'Quantidade', 'Preco Custo', 'Preco Venda', 'Estoque Minimo'])
    produtos = Produto.objects.select_related('fornecedor').all()
    for p in produtos:
        writer.writerow([
            p.descricao,
            p.get_tipo_produto_display(),
            p.fornecedor.nome if p.fornecedor else '',
            p.unidade_simbolo,
            p.quantidade_formatada,
            p.preco_custo if p.preco_custo is not None else '',
            p.preco_venda if p.preco_venda is not None else '',
            p.estoque_minimo if p.estoque_minimo is not None else '',
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
            preco_custo=decimal_ou_none(data.get('preco_custo')),
            preco_venda=decimal_ou_none(data.get('preco_venda')),
            estoque_minimo=decimal_ou_none(data.get('estoque_minimo')),
            metros_por_rolo=data.get('metros_por_rolo') or None,
            tipo_tinta=data.get('tipo_tinta', 'N/A'),
            cor_tinta=data.get('cor_tinta', 'INCOLOR'),
            litros_por_vidro=data.get('litros_por_vidro') or None,
            unidade_medida=data.get('unidade_medida', 'UN'),
            categoria_id=data.get('categoria_id') or None,
        )
        log_acao(request.user, 'CRIAR', f'Cadastrou produto {produto.descricao}', 'Produto', produto.id)
        return JsonResponse({'ok': True, 'id': produto.id})
    fornecedores = Fornecedor.objects.all().values('id', 'nome')
    categorias = Categoria.objects.all().values('id', 'nome')
    return render(request, 'estoque/cadastrar_produto.html', {
        'fornecedores': list(fornecedores),
        'categorias': list(categorias),
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
        produto.preco_custo = decimal_ou_none(data.get('preco_custo'))
        produto.preco_venda = decimal_ou_none(data.get('preco_venda'))
        produto.estoque_minimo = decimal_ou_none(data.get('estoque_minimo'))
        produto.metros_por_rolo = data.get('metros_por_rolo') or None
        produto.tipo_tinta = data.get('tipo_tinta', 'N/A')
        produto.cor_tinta = data.get('cor_tinta', 'INCOLOR')
        produto.litros_por_vidro = data.get('litros_por_vidro') or None
        produto.unidade_medida = data.get('unidade_medida', 'UN')
        produto.categoria_id = data.get('categoria_id') or None
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
    categorias = Categoria.objects.all().values('id', 'nome')
    return render(request, 'estoque/editar_produto.html', {
        'produto': produto,
        'fornecedores': list(fornecedores),
        'categorias': list(categorias),
        'produto_json': json.dumps({
            'id': produto.id,
            'tipo_produto': produto.tipo_produto,
            'descricao': produto.descricao,
            'fornecedor_id': produto.fornecedor_id or '',
            'categoria_id': produto.categoria_id or '',
            'quantidade_base': float(produto.quantidade_base) if produto.quantidade_base else '',
            'preco_custo': float(produto.preco_custo) if produto.preco_custo is not None else '',
            'preco_venda': float(produto.preco_venda) if produto.preco_venda is not None else '',
            'estoque_minimo': float(produto.estoque_minimo) if produto.estoque_minimo is not None else '',
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
    lucro = (produto.preco_venda - produto.preco_custo) if produto.preco_venda is not None and produto.preco_custo is not None else None
    margem = (lucro / produto.preco_custo * 100) if lucro is not None and produto.preco_custo and produto.preco_custo > 0 else None
    return render(request, 'estoque/detalhe.html', {
        'produto': produto,
        'movimentacoes': movimentacoes,
        'historico_precos': historico_precos,
        'lucro': round(lucro, 2) if lucro is not None else None,
        'margem': round(margem, 1) if margem is not None else None,
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
                usuario=request.user,
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
    total_entradas_unidade = serializar_totais_unidade(agrupar_quantidade_por_unidade(movs.filter(tipo='ENTRADA')))
    total_saidas_unidade = serializar_totais_unidade(agrupar_quantidade_por_unidade(movs.filter(tipo='SAIDA')))

    por_produto = movs.values('produto__descricao', 'produto__tipo_produto', 'produto__unidade_medida', 'tipo').annotate(
        total=Sum('quantidade')
    ).order_by('produto__descricao')

    movs_por_produto = {}
    for item in por_produto:
        nome = item['produto__descricao']
        if nome not in movs_por_produto:
            fake_produto = type('ProdutoUnidade', (), {
                'tipo_produto': item['produto__tipo_produto'],
                'unidade_medida': item['produto__unidade_medida'],
            })()
            movs_por_produto[nome] = {'entradas': Decimal('0'), 'saidas': Decimal('0'), 'unidade': unidade_base_codigo(fake_produto)}
        if item['tipo'] == 'ENTRADA':
            movs_por_produto[nome]['entradas'] += item['total']
        else:
            movs_por_produto[nome]['saidas'] += item['total']

    produtos_afetados = [
        {
            'nome': nome,
            'entradas': formatar_quantidade(d['entradas'], d['unidade']),
            'saidas': formatar_quantidade(d['saidas'], d['unidade']),
            'saldo': formatar_quantidade(d['entradas'] - d['saidas'], d['unidade']),
        }
        for nome, d in movs_por_produto.items()
    ]

    return render(request, 'estoque/relatorio.html', {
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'total_entradas_unidade': total_entradas_unidade,
        'total_saidas_unidade': total_saidas_unidade,
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
            try:
                username = validate_username_available(data.get('username'))
                user = User.objects.create_user(
                    username=username,
                    password=data['password'],
                    is_staff=True,
                )
            except ValidationError as e:
                return JsonResponse({'ok': False, 'erro': '; '.join(e.messages)}, status=400)
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
                        if val in (None, ''):
                            return None
                        text = str(val).replace(',', '.').strip()
                        return Decimal(text) if text else None

                    def parse_decimal_zero(val):
                        parsed = parse_decimal(val)
                        return parsed if parsed is not None else Decimal('0')
                        
                    qt_rolos = parse_decimal_zero(row.get('qt_rolos'))
                    metros_por_rolo = parse_decimal_zero(row.get('metros_por_rolo'))
                    qt_vidros = parse_decimal_zero(row.get('qt_vidros'))
                    litros_por_vidro = parse_decimal_zero(row.get('litros_por_vidro'))
                    quantidade_base = parse_decimal_zero(row.get('quantidade_base'))
                    
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
        itens = list(f.itens.all())
        total_itens = len(itens)
        valor_total = Decimal('0.00')
        produtos_sem_custo = 0
        for item in itens:
            if item.quantidade > 0 and item.preco_custo is None:
                produtos_sem_custo += 1
            elif item.preco_custo is not None:
                valor_total += item.quantidade * item.preco_custo
        fechamentos_json.append({
            'id': f.id,
            'data_fechamento': f.data_fechamento.strftime('%d/%m/%Y %H:%M'),
            'usuario': f.usuario.username if f.usuario else '-',
            'referencia_mes_ano': f.referencia_mes_ano,
            'observacao': f.observacao,
            'total_itens': total_itens,
            'valor_total': float(valor_total),
            'produtos_sem_custo': produtos_sem_custo,
            'calculo_completo': produtos_sem_custo == 0,
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
        unidade = item.produto.unidade_simbolo if item.produto else ''
        preco_custo = item.preco_custo
        preco_venda = item.preco_venda
        
        row_data = [
            item.descricao,
            tipo,
            fornecedor,
            unidade,
            float(item.quantidade),
            float(preco_custo) if preco_custo is not None else None,
            float(preco_venda) if preco_venda is not None else None,
            f"=E{ws.max_row+1}*F{ws.max_row+1}" if preco_custo is not None else None,
            f"=E{ws.max_row+1}*G{ws.max_row+1}" if preco_venda is not None else None,
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
        "Quantidades por unidade não são somadas", "", "",
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
            cell.alignment = Alignment(horizontal='left' if col_idx == 5 else 'right', vertical='center')
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
        unidade = p.unidade_simbolo
        preco_custo = p.preco_custo
        preco_venda = p.preco_venda
        
        row_data = [
            p.descricao,
            tipo,
            fornecedor,
            unidade,
            float(p.quantidade_base),
            float(preco_custo) if preco_custo is not None else None,
            float(preco_venda) if preco_venda is not None else None,
            f"=E{ws.max_row+1}*F{ws.max_row+1}" if preco_custo is not None else None,
            f"=E{ws.max_row+1}*G{ws.max_row+1}" if preco_venda is not None else None,
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
        "Quantidades por unidade não são somadas", "", "",
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
            cell.alignment = Alignment(horizontal='left' if col_idx == 5 else 'right', vertical='center')
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
            'quantidade': p.quantidade_formatada,
            'unidade': p.unidade_simbolo,
        }
        for p in produtos
    ]
    return JsonResponse({'resultados': resultados})
