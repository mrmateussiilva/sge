import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from ..log_utils import log_acao
from ..models import Fornecedor, Produto
from .helpers import exigir_admin_json, json_erro, json_ok, requisicao_htmx


@login_required
def lista_fornecedores(request):
    busca = request.GET.get('q', '').strip()
    contexto = contexto_lista_fornecedores(busca)
    if requisicao_htmx(request) and request.headers.get('HX-Target') == 'fornecedores-resultados':
        return render(request, 'estoque/fornecedores/_resultados.html', contexto)
    return render(request, 'estoque/fornecedores/lista.html', contexto)


def contexto_lista_fornecedores(busca=''):
    fornecedores = Fornecedor.objects.annotate(total_produtos=Count('produto')).order_by('nome')
    total_fornecedores = fornecedores.count()
    if busca:
        fornecedores = fornecedores.filter(
            Q(nome__icontains=busca)
            | Q(cnpj__icontains=busca)
            | Q(email__icontains=busca)
            | Q(telefone__icontains=busca)
        )
    return {
        'fornecedores': fornecedores,
        'total_fornecedores': total_fornecedores,
        'busca': busca,
    }


def resposta_erro_fornecedor(request, mensagem, status=400):
    if requisicao_htmx(request):
        response = render(
            request,
            'estoque/fornecedores/_form_feedback.html',
            {'erro': mensagem},
        )
        response['HX-Retarget'] = '#fornecedor-form-feedback'
        response['HX-Reswap'] = 'innerHTML'
        return response
    return json_erro(mensagem, status=status)


@login_required
def salvar_fornecedor(request, id=None):
    """Cria ou edita um fornecedor via formulário HTMX ou JSON."""
    fornecedor = get_object_or_404(Fornecedor, id=id) if id else None
    if request.method == 'GET':
        return render(request, 'estoque/fornecedores/_form_modal.html', {
            'fornecedor': fornecedor,
            'busca': request.GET.get('q', '').strip(),
        })
    if request.method != 'POST':
        return json_erro('Método não permitido.', status=405)

    try:
        data = request.POST if requisicao_htmx(request) else json.loads(request.body)
    except json.JSONDecodeError:
        return resposta_erro_fornecedor(request, 'JSON inválido.')

    nome = data.get('nome', '').strip()
    if not nome:
        return resposta_erro_fornecedor(request, 'Nome é obrigatório.')

    acao = 'EDITAR' if fornecedor else 'CRIAR'
    fornecedor = fornecedor or Fornecedor()

    fornecedor.nome = nome
    fornecedor.cnpj = (data.get('cnpj') or '').strip()
    fornecedor.email = (data.get('email') or '').strip()
    fornecedor.telefone = (data.get('telefone') or '').strip()
    fornecedor.observacao = (data.get('observacao') or '').strip()
    try:
        fornecedor.full_clean()
        fornecedor.save()
    except ValidationError as exc:
        return resposta_erro_fornecedor(request, '; '.join(exc.messages))

    log_acao(request.user, acao, f'{acao} fornecedor: {fornecedor.nome}', 'Fornecedor', fornecedor.id)
    if requisicao_htmx(request):
        response = render(
            request,
            'estoque/fornecedores/_resultados.html',
            contexto_lista_fornecedores(data.get('q', '').strip()),
        )
        response['HX-Trigger-After-Swap'] = json.dumps({
            'sge:feedback': {
                'message': 'Fornecedor atualizado com sucesso.' if id else 'Fornecedor criado com sucesso.',
                'type': 'success',
            },
            'sge:modal-close': {'id': 'modalFornecedor'},
        })
        return response
    return json_ok(id=fornecedor.id)


@login_required
def excluir_fornecedor(request, id):
    if request.method != 'POST':
        return json_erro('Exclusão deve usar POST.', status=405)
    perm_error = exigir_admin_json(request)
    if perm_error:
        return perm_error
    fornecedor = get_object_or_404(Fornecedor, id=id)
    vinculados = Produto.objects.filter(fornecedor=fornecedor).count()
    if vinculados:
        mensagem = f'O fornecedor não pode ser excluído porque possui {vinculados} produto(s) vinculado(s).'
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
    nome = fornecedor.nome
    fornecedor.delete()
    log_acao(request.user, 'EXCLUIR', f'Excluiu fornecedor: {nome}', 'Fornecedor', id)
    if requisicao_htmx(request):
        response = render(
            request,
            'estoque/fornecedores/_resultados.html',
            contexto_lista_fornecedores(request.POST.get('q', '').strip()),
        )
        response['HX-Trigger-After-Swap'] = json.dumps({
            'sge:feedback': {'message': 'Fornecedor excluído com sucesso.', 'type': 'success'},
        })
        return response
    return json_ok(mensagem='Fornecedor excluído com sucesso.')
