import json
from decimal import InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from ..log_utils import log_acao
from ..models import Fornecedor, ItemOrdemCompra, Movimentacao, OrdemCompra, Produto
from .helpers import decimal_ou_none, json_erro, requisicao_htmx


@login_required
def lista_ordens(request):
    busca = (request.GET.get('busca') or request.GET.get('q') or '').strip()
    status_selecionado = request.GET.get('status', '').strip()
    fornecedor_selecionado = request.GET.get('fornecedor', '').strip()

    qs = OrdemCompra.objects.select_related('fornecedor').all().order_by('-data_criacao')

    if busca:
        qs = qs.filter(
            Q(fornecedor__nome__icontains=busca) | Q(observacao__icontains=busca)
        )
    if status_selecionado:
        qs = qs.filter(status=status_selecionado)
    if fornecedor_selecionado == 'SEM_FORNECEDOR':
        qs = qs.filter(fornecedor__isnull=True)
    elif fornecedor_selecionado:
        qs = qs.filter(fornecedor__nome=fornecedor_selecionado)

    fornecedores_unicos = list(
        Fornecedor.objects.filter(ordemcompra__isnull=False)
        .values_list('nome', flat=True).distinct().order_by('nome')
    )

    paginator = Paginator(qs, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    extra_params = f"&busca={busca}&status={status_selecionado}&fornecedor={fornecedor_selecionado}"
    tem_filtros_ativos = bool(busca or status_selecionado or fornecedor_selecionado)

    context = {
        'page_obj': page_obj,
        'ordens': page_obj,
        'busca': busca,
        'status_selecionado': status_selecionado,
        'fornecedor_selecionado': fornecedor_selecionado,
        'fornecedores_unicos': fornecedores_unicos,
        'status_choices': OrdemCompra.STATUS_CHOICES,
        'extra_params': extra_params,
        'tem_filtros_ativos': tem_filtros_ativos,
    }

    if requisicao_htmx(request):
        return render(request, 'estoque/ordens/_lista_resultados.html', context)
    return render(request, 'estoque/lista_ordens.html', context)


def contexto_form_ordem(data=None, itens=None):
    produtos = [
        {
            'id': produto.id,
            'id_str': str(produto.id),
            'descricao': produto.descricao,
            'preco_custo': produto.preco_custo,
        }
        for produto in Produto.objects.all().order_by('descricao')
    ]
    return {
        'fornecedores': Fornecedor.objects.all().order_by('nome'),
        'produtos': produtos,
        'form_data': {
            'fornecedor_id': data.get('fornecedor_id', '') if data is not None else '',
            'observacao': data.get('observacao', '') if data is not None else '',
        },
        'form_itens': itens or [],
    }


def itens_ordem_de_post(post_data):
    produto_ids = post_data.getlist('produto_id')
    quantidades = post_data.getlist('quantidade')
    precos = post_data.getlist('preco_unitario')
    itens = []

    for idx in range(max(len(produto_ids), len(quantidades), len(precos))):
        produto_id = produto_ids[idx] if idx < len(produto_ids) else ''
        quantidade = quantidades[idx] if idx < len(quantidades) else ''
        preco_unitario = precos[idx] if idx < len(precos) else ''
        if not produto_id and not quantidade and not preco_unitario:
            continue
        itens.append({
            'produto_id': produto_id,
            'quantidade': quantidade,
            'preco_unitario': preco_unitario,
        })
    return itens


def validar_itens_ordem(itens):
    if not itens:
        raise ValidationError('Inclua ao menos um item na ordem.')

    itens_validados = []
    for item in itens:
        produto_id = item.get('produto_id')
        quantidade = decimal_ou_none(item.get('quantidade'))
        preco_unitario = decimal_ou_none(item.get('preco_unitario'))

        if not produto_id:
            raise ValidationError('Selecione um produto para todos os itens.')
        if quantidade is None or quantidade <= 0:
            raise ValidationError('Quantidade deve ser maior que zero em todos os itens.')
        if preco_unitario is None or preco_unitario < 0:
            raise ValidationError('Preço unitário não pode ser negativo.')
        if not Produto.objects.filter(pk=produto_id).exists():
            raise ValidationError('Produto informado não foi encontrado.')

        itens_validados.append({
            'produto_id': produto_id,
            'quantidade': quantidade,
            'preco_unitario': preco_unitario,
        })
    return itens_validados


@login_required
def criar_ordem(request):
    if request.method == 'POST':
        is_json = request.content_type.startswith('application/json')
        try:
            data = json.loads(request.body) if is_json else request.POST
            itens_raw = data.get('itens', []) if is_json else itens_ordem_de_post(request.POST)
            itens = validar_itens_ordem(itens_raw)
            with transaction.atomic():
                ordem = OrdemCompra.objects.create(
                    fornecedor_id=data.get('fornecedor_id') or None,
                    observacao=data.get('observacao', ''),
                )
                for item in itens:
                    ItemOrdemCompra.objects.create(
                        ordem=ordem,
                        produto_id=item['produto_id'],
                        quantidade=item['quantidade'],
                        preco_unitario=item['preco_unitario'],
                    )
            log_acao(request.user, 'CRIAR', f'Criou ordem de compra #{ordem.id}', 'OrdemCompra', ordem.id)
            if is_json:
                return JsonResponse({'ok': True, 'id': ordem.id})
            messages.success(request, f'Ordem de compra #{ordem.id} criada com sucesso.')
            return redirect('detalhe_ordem', id=ordem.id)
        except (json.JSONDecodeError, InvalidOperation, TypeError, ValueError):
            if is_json:
                return json_erro('Dados inválidos.')
            messages.error(request, 'Dados inválidos.')
            return render(request, 'estoque/criar_ordem.html', contexto_form_ordem(request.POST, itens_ordem_de_post(request.POST)), status=400)
        except ValidationError as exc:
            if is_json:
                return json_erro('; '.join(exc.messages))
            messages.error(request, '; '.join(exc.messages))
            return render(request, 'estoque/criar_ordem.html', contexto_form_ordem(request.POST, itens_ordem_de_post(request.POST)), status=400)
    return render(request, 'estoque/criar_ordem.html', contexto_form_ordem())


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
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'erro': 'Método não permitido.'}, status=405)
    ordem = get_object_or_404(OrdemCompra, id=id)
    if ordem.status != 'PENDENTE':
        return JsonResponse({'ok': False, 'erro': 'Ordem nao esta pendente.'}, status=400)
    ordem.status = 'APROVADA'
    ordem.save()
    log_acao(request.user, 'APROVAR', f'Aprovou ordem de compra #{ordem.id}', 'OrdemCompra', id)
    return JsonResponse({'ok': True})


@login_required
def cancelar_ordem(request, id):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'erro': 'Método não permitido.'}, status=405)
    ordem = get_object_or_404(OrdemCompra, id=id)
    if ordem.status in ('RECEBIDA', 'CANCELADA'):
        return JsonResponse({'ok': False, 'erro': 'Ordem ja finalizada.'}, status=400)
    ordem.status = 'CANCELADA'
    ordem.save()
    log_acao(request.user, 'CANCELAR', f'Cancelou ordem de compra #{ordem.id}', 'OrdemCompra', id)
    return JsonResponse({'ok': True})


@login_required
def receber_ordem(request, id):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'erro': 'Método não permitido.'}, status=405)
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
