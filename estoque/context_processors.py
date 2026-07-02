from django.db.models import F

from .models import Produto


def estoque_baixo(request):
    if not request.user.is_authenticated:
        return {}
    count = Produto.objects.filter(quantidade_base__lte=F('estoque_minimo')).count()
    return {'estoque_baixo_count': count}
