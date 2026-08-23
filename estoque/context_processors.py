from .models import Produto
from .services.estoque_status import filtro_baixo


def estoque_baixo(request):
    if not request.user.is_authenticated:
        return {}
    count = Produto.objects.filter(filtro_baixo()).count()
    usuario = request.user
    if usuario.is_superuser:
        operacional = True
        gestao = True
    else:
        perfis = set(usuario.groups.values_list('name', flat=True))
        operacional = bool(perfis & {'Admin', 'Gestor', 'Operador'})
        gestao = bool(perfis & {'Admin', 'Gestor'})

    return {
        'estoque_baixo_count': count,
        'usuario_operacional': operacional,
        'usuario_gestao': gestao,
        'usuario_admin': usuario.is_superuser,
        'usuario_staff': usuario.is_staff,
    }
