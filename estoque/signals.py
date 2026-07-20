from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_save
from django.core.exceptions import ValidationError
from django.dispatch import receiver

from .models import HistoricoPreco, Produto
from .services.usernames import normalize_username, validate_username_available


@receiver(pre_save, sender=Produto)
def guardar_precos_anteriores(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = Produto.objects.only('preco_custo', 'preco_venda').get(pk=instance.pk)
    except Produto.DoesNotExist:
        return
    instance._preco_custo_anterior = old.preco_custo
    instance._preco_venda_anterior = old.preco_venda


@receiver(post_save, sender=Produto)
def salvar_historico_preco(sender, instance, created, **kwargs):
    if created:
        return
    if getattr(instance, '_historico_ja_salvo', False):
        return
    old_preco_custo = getattr(instance, '_preco_custo_anterior', None)
    old_preco_venda = getattr(instance, '_preco_venda_anterior', None)
    if old_preco_custo is None and old_preco_venda is None:
        return

    preco_custo_mudou = old_preco_custo != instance.preco_custo
    preco_venda_mudou = old_preco_venda != instance.preco_venda
    if not preco_custo_mudou and not preco_venda_mudou:
        return

    HistoricoPreco.objects.create(
        produto=instance,
        preco_custo_antigo=old_preco_custo if preco_custo_mudou else None,
        preco_custo_novo=instance.preco_custo if preco_custo_mudou else None,
        preco_venda_antigo=old_preco_venda if preco_venda_mudou else None,
        preco_venda_novo=instance.preco_venda if preco_venda_mudou else None,
    )


@receiver(pre_save, sender=get_user_model())
def normalizar_username_usuario(sender, instance, **kwargs):
    original = instance.username or ''
    normalized = normalize_username(original)
    if not normalized:
        raise ValidationError('Usuário é obrigatório.')

    if instance.pk:
        try:
            old_username = sender.objects.only('username').get(pk=instance.pk).username
        except sender.DoesNotExist:
            old_username = None
        if old_username == original:
            return

    instance.username = validate_username_available(normalized, instance.pk)
