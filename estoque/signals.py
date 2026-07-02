from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import HistoricoPreco, Produto


@receiver(post_save, sender=Produto)
def salvar_historico_preco(sender, instance, created, **kwargs):
    if created:
        return
    if getattr(instance, '_historico_ja_salvo', False):
        return
    try:
        old = Produto.objects.get(pk=instance.pk)
    except Produto.DoesNotExist:
        return
    if old.preco_custo == instance.preco_custo and old.preco_venda == instance.preco_venda:
        return
    HistoricoPreco.objects.create(
        produto=instance,
        preco_custo_antigo=old.preco_custo,
        preco_custo_novo=instance.preco_custo,
        preco_venda_antigo=old.preco_venda,
        preco_venda_novo=instance.preco_venda,
    )
