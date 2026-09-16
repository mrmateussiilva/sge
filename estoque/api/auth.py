from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from ..models import OrdemCompra, Produto
from ..services.estoque_status import filtro_baixo, filtro_zerado
from ..views.helpers import (
    PERFIS_GESTAO,
    PERFIS_NEGOCIO,
    PERFIS_OPERACIONAIS,
    json_ok,
    usuario_tem_perfil,
)


@login_required
def me(request):
    """Retorna dados do usuário logado, permissões e badges de notificação."""
    user = request.user
    grupos = list(user.groups.values_list('name', flat=True))

    if user.is_superuser:
        perfil = 'Administrador'
    elif grupos:
        perfil = PERFIS_NEGOCIO.get(grupos[0], grupos[0])
    else:
        perfil = 'Visualizador'

    is_admin = user.is_superuser or 'Admin' in grupos
    is_gestao = is_admin or usuario_tem_perfil(user, PERFIS_GESTAO)
    is_operacional = is_gestao or usuario_tem_perfil(user, PERFIS_OPERACIONAIS)

    estoque_baixo_count = Produto.objects.filter(filtro_baixo()).count()
    estoque_zerado_count = Produto.objects.filter(filtro_zerado()).count()
    ordens_pendentes_count = OrdemCompra.objects.filter(status='PENDENTE').count()

    return json_ok(
        user={
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'nome_completo': user.get_full_name() or user.username,
            'is_superuser': user.is_superuser,
            'grupos': grupos,
            'perfil': perfil,
            'permissoes': {
                'operacional': is_operacional,
                'gestao': is_gestao,
                'admin': is_admin,
            },
        },
        alertas={
            'estoque_baixo': estoque_baixo_count,
            'estoque_zerado': estoque_zerado_count,
            'ordens_pendentes': ordens_pendentes_count,
        },
        app={
            'versao': getattr(settings, 'APP_VERSION', '1.4.0'),
            'nome': 'SGE',
        },
    )


@require_POST
def api_logout(request):
    """Encerra a sessão do usuário."""
    logout(request)
    return json_ok(mensagem='Sessão finalizada com sucesso.')
