import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from ..log_utils import log_acao
from ..models import Categoria
from .helpers import exigir_admin_json, json_erro, json_ok, requisicao_htmx


@login_required
def lista_categorias(request):
    busca = request.GET.get('q', '').strip()
    contexto = contexto_lista_categorias(busca)
    if requisicao_htmx(request) and request.headers.get('HX-Target') == 'categorias-resultados':
        return render(request, 'estoque/categorias/_resultados.html', contexto)
    return render(request, 'estoque/categorias/lista.html', contexto)


def contexto_lista_categorias(busca=''):
    categorias = Categoria.objects.annotate(total_produtos=Count('produtos')).order_by('nome')
    total_categorias = categorias.count()
    if busca:
        categorias = categorias.filter(
            Q(nome__icontains=busca) | Q(descricao__icontains=busca)
        )
    return {
        'categorias': categorias,
        'total_categorias': total_categorias,
        'busca': busca,
    }


def resposta_erro_categoria(request, mensagem, status=400):
    if requisicao_htmx(request):
        response = render(
            request,
            'estoque/categorias/_form_feedback.html',
            {'erro': mensagem},
        )
        response['HX-Retarget'] = '#categoria-form-feedback'
        response['HX-Reswap'] = 'innerHTML'
        return response
    return json_erro(mensagem, status=status)


@login_required
def salvar_categoria(request, id=None):
    """Cria ou edita uma categoria via formulário HTMX ou JSON."""
    categoria = get_object_or_404(Categoria, id=id) if id else None
    if request.method == 'GET':
        return render(request, 'estoque/categorias/_form_modal.html', {
            'categoria': categoria,
            'busca': request.GET.get('q', '').strip(),
        })
    if request.method != 'POST':
        return json_erro('Método não permitido.', status=405)

    try:
        data = request.POST if requisicao_htmx(request) else json.loads(request.body)
    except json.JSONDecodeError:
        return resposta_erro_categoria(request, 'JSON inválido.')

    nome = data.get('nome', '').strip()
    if not nome:
        return resposta_erro_categoria(request, 'Nome é obrigatório.')

    cor = (data.get('cor') or '#6c757d').strip()
    if len(cor) != 7 or not cor.startswith('#') or not all(
        caractere in '0123456789abcdefABCDEF' for caractere in cor[1:]
    ):
        return resposta_erro_categoria(request, 'Cor inválida. Use o formato hexadecimal #RRGGBB.')

    acao = 'EDITAR' if categoria else 'CRIAR'
    categoria = categoria or Categoria()

    categoria.nome = nome
    categoria.descricao = (data.get('descricao') or '').strip()
    categoria.cor = cor
    try:
        categoria.full_clean()
        categoria.save()
    except ValidationError as exc:
        return resposta_erro_categoria(request, '; '.join(exc.messages))
    except IntegrityError:
        return resposta_erro_categoria(request, 'Já existe uma categoria com este nome.')

    log_acao(request.user, acao, f'{acao} categoria: {categoria.nome}', 'Categoria', categoria.id)
    if requisicao_htmx(request):
        response = render(
            request,
            'estoque/categorias/_resultados.html',
            contexto_lista_categorias(data.get('q', '').strip()),
        )
        response['HX-Trigger-After-Swap'] = json.dumps({
            'sge:feedback': {
                'message': 'Categoria atualizada com sucesso.' if id else 'Categoria criada com sucesso.',
                'type': 'success',
            },
            'sge:modal-close': {'id': 'modalCategoria'},
        })
        return response
    return json_ok(id=categoria.id)


@login_required
def excluir_categoria(request, id):
    if request.method != 'POST':
        return json_erro('Exclusão deve usar POST.', status=405)
    perm_error = exigir_admin_json(request)
    if perm_error:
        return perm_error
    categoria = get_object_or_404(Categoria, id=id)
    vinculados = categoria.produtos.count()
    if vinculados:
        mensagem = f'A categoria não pode ser excluída porque possui {vinculados} produto(s) vinculado(s).'
        if requisicao_htmx(request):
            response = HttpResponse()
            response['HX-Reswap'] = 'none'
            response['HX-Trigger'] = json.dumps({
                'sge:feedback': {'message': mensagem, 'type': 'danger'},
            })
            return response
        return json_erro(
            mensagem,
            codigo='VINCULO_IMPEDITIVO',
        )
    nome = categoria.nome
    categoria.delete()
    log_acao(request.user, 'EXCLUIR', f'Excluiu categoria: {nome}', 'Categoria', id)
    if requisicao_htmx(request):
        response = render(
            request,
            'estoque/categorias/_resultados.html',
            contexto_lista_categorias(request.POST.get('q', '').strip()),
        )
        response['HX-Trigger-After-Swap'] = json.dumps({
            'sge:feedback': {'message': 'Categoria excluída com sucesso.', 'type': 'success'},
        })
        return response
    return json_ok(mensagem='Categoria excluída com sucesso.')
