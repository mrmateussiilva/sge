from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q

from ..models import Categoria
from ..views.helpers import json_ok


@login_required
def listar_categorias_api(request):
    """Lista todas as categorias com contagem de produtos vinculados."""
    busca = (request.GET.get('busca') or request.GET.get('q') or '').strip()
    categorias = Categoria.objects.annotate(total_produtos=Count('produtos')).order_by('nome')
    total_geral = categorias.count()

    if busca:
        categorias = categorias.filter(
            Q(nome__icontains=busca) | Q(descricao__icontains=busca)
        )

    itens = [
        {
            'id': cat.id,
            'nome': cat.nome,
            'descricao': cat.descricao,
            'cor': cat.cor,
            'total_produtos': cat.total_produtos,
        }
        for cat in categorias
    ]

    return json_ok(
        itens=itens,
        total_categorias=total_geral,
        busca=busca,
    )
