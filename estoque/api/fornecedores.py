from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q

from ..models import Fornecedor
from ..views.helpers import json_ok


@login_required
def listar_fornecedores_api(request):
    """Lista todos os fornecedores com contagem de produtos vinculados."""
    busca = (request.GET.get('busca') or request.GET.get('q') or '').strip()
    fornecedores = Fornecedor.objects.annotate(total_produtos=Count('produto')).order_by('nome')
    total_geral = fornecedores.count()

    if busca:
        fornecedores = fornecedores.filter(
            Q(nome__icontains=busca)
            | Q(cnpj__icontains=busca)
            | Q(email__icontains=busca)
            | Q(telefone__icontains=busca)
        )

    itens = [
        {
            'id': f.id,
            'nome': f.nome,
            'cnpj': f.cnpj,
            'email': f.email,
            'telefone': f.telefone,
            'observacao': f.observacao,
            'total_produtos': f.total_produtos,
        }
        for f in fornecedores
    ]

    return json_ok(
        itens=itens,
        total_fornecedores=total_geral,
        busca=busca,
    )
