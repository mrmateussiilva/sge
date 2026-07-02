from .models import LogAcao


def log_acao(usuario, acao, descricao, modelo='', objeto_id=None):
    if not usuario or not usuario.is_authenticated:
        return
    LogAcao.objects.create(
        usuario=usuario,
        acao=acao,
        descricao=descricao[:500],
        modelo=modelo,
        objeto_id=objeto_id,
    )
