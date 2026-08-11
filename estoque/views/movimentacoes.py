import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from ..log_utils import log_acao
from ..models import Movimentacao, Produto
from .helpers import json_erro, json_ok, produto_operacional_json, requisicao_htmx


@login_required
def info_produto_movimentacao(request):
    produto_id = request.GET.get('produto_id')
    if not produto_id:
        return HttpResponse('')
    try:
        produto = Produto.objects.select_related('fornecedor').get(id=produto_id)
        return render(request, 'estoque/movimentacao/_produto_info.html', {'produto': produto})
    except Produto.DoesNotExist:
        return HttpResponse('')


@login_required
def registrar_movimentacao(request):
    if request.method == 'POST':
        is_json = (request.content_type == 'application/json')
        is_htmx = requisicao_htmx(request)
        try:
            if is_json:
                data = json.loads(request.body)
            else:
                data = request.POST

            produto_id = data.get('produto_id')
            tipo = data.get('tipo')
            quantidade_raw = data.get('quantidade')
            observacao = data.get('observacao', '')

            if not produto_id or not tipo or not quantidade_raw:
                err_msg = 'Campos obrigatórios ausentes.'
                if is_json: return json_erro(err_msg)
                return HttpResponse(err_msg, status=400)

            produto = Produto.objects.get(id=produto_id)
            quantidade = Decimal(str(quantidade_raw))

            if quantidade <= 0:
                err_msg = 'Quantidade deve ser maior que zero.'
                if is_json: return json_erro(err_msg)
                return HttpResponse(err_msg, status=400)

            if tipo == 'SAIDA' and produto.quantidade_base < quantidade:
                err_msg = 'Saldo insuficiente para esta saída.'
                if is_json: return json_erro(err_msg, codigo='SALDO_INSUFICIENTE')
                return HttpResponse(err_msg, status=400)

            Movimentacao.objects.create(
                produto=produto,
                usuario=request.user,
                tipo=tipo,
                quantidade=quantidade,
                observacao=observacao,
            )
            produto.refresh_from_db()
            log_acao(request.user, tipo, f'{tipo} de {quantidade} {produto.unidade_simbolo} de {produto.descricao}', 'Movimentacao')

            if is_json:
                return json_ok(
                    mensagem='Movimentação registrada com sucesso.',
                    saldo_atual=produto.quantidade_formatada,
                    status_estoque=produto.status_estoque,
                )

            if is_htmx:
                movimentacoes_qs = Movimentacao.objects.select_related('produto', 'usuario').order_by('-data')
                paginator = Paginator(movimentacoes_qs, 25)
                page_obj = paginator.get_page(1)
                response = render(request, 'estoque/movimentacao/_historico_tabela.html', {
                    'page_obj': page_obj,
                    'movimentacoes': page_obj,
                })
                response['HX-Trigger'] = 'estoqueAtualizado'
                return response

        except (json.JSONDecodeError, KeyError, InvalidOperation, TypeError, ValueError):
            err_msg = 'Dados ou quantidade inválida.'
            if is_json: return json_erro(err_msg)
            return HttpResponse(err_msg, status=400)
        except Produto.DoesNotExist:
            err_msg = 'Produto não encontrado.'
            if is_json: return json_erro(err_msg, status=404)
            return HttpResponse(err_msg, status=404)
        except ValidationError as e:
            err_msg = '; '.join(e.messages)
            if is_json: return json_erro(err_msg, codigo='SALDO_INSUFICIENTE')
            return HttpResponse(err_msg, status=400)

    lista_produtos_qs = Produto.objects.select_related('fornecedor').all().order_by('descricao')
    produtos = [produto_operacional_json(p) for p in lista_produtos_qs]
    movimentacoes_qs = Movimentacao.objects.select_related('produto', 'usuario').order_by('-data')
    paginator = Paginator(movimentacoes_qs, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'produtos': produtos,
        'lista_produtos_qs': lista_produtos_qs,
        'page_obj': page_obj,
        'movimentacoes': page_obj,
    }

    if requisicao_htmx(request):
        return render(request, 'estoque/movimentacao/_historico_tabela.html', context)

    return render(request, 'estoque/movimentacao.html', context)


@login_required
def excluir_movimentacao(request, id):
    mov = get_object_or_404(Movimentacao, id=id)
    if request.method == 'POST':
        if not request.user.is_superuser:
            if request.headers.get('HX-Request'):
                return HttpResponse('Permissão negada.', status=403)
            return json_erro('Permissão negada.', status=403, codigo='PERMISSAO_NEGADA')

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

        if request.headers.get('HX-Request'):
            movimentacoes_qs = Movimentacao.objects.select_related('produto', 'usuario').order_by('-data')
            paginator = Paginator(movimentacoes_qs, 25)
            page_obj = paginator.get_page(1)
            response = render(request, 'estoque/movimentacao/_historico_tabela.html', {
                'page_obj': page_obj,
                'movimentacoes': page_obj,
            })
            response['HX-Trigger'] = 'estoqueAtualizado'
            return response

        return json_ok(mensagem='Movimentação excluída e saldo recalculado com sucesso.', nova_quantidade=produto.quantidade_formatada)
    return json_erro('Exclusão deve usar POST.', status=405)
