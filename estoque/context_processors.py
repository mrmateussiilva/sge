from .models import Produto
from .services.estoque_status import filtro_baixo


def estoque_baixo(request):
    if not request.user.is_authenticated:
        return {}
    count = Produto.objects.filter(filtro_baixo()).count()
    return {'estoque_baixo_count': count}
