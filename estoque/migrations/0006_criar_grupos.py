from django.db import migrations


def criar_grupos(apps, schema_editor):
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType

    admin_group, _ = Group.objects.get_or_create(name='Admin')
    operador_group, _ = Group.objects.get_or_create(name='Operador')
    visualizador_group, _ = Group.objects.get_or_create(name='Visualizador')

    for perm in Permission.objects.all():
        admin_group.permissions.add(perm)

    permissoes_operador = [
        'view_produto', 'add_produto', 'change_produto', 'delete_produto',
        'view_movimentacao', 'add_movimentacao', 'delete_movimentacao',
        'view_fornecedor', 'add_fornecedor', 'change_fornecedor',
        'view_ordemcompra', 'add_ordemcompra', 'change_ordemcompra',
        'view_itemordemcompra', 'add_itemordemcompra', 'change_itemordemcompra',
        'view_logacao',
    ]
    permissoes_visualizador = [
        'view_produto', 'view_movimentacao', 'view_fornecedor',
        'view_ordemcompra', 'view_itemordemcompra', 'view_logacao',
    ]

    for codename in permissoes_operador:
        try:
            operador_group.permissions.add(Permission.objects.get(codename=codename))
        except Permission.DoesNotExist:
            pass

    for codename in permissoes_visualizador:
        try:
            visualizador_group.permissions.add(Permission.objects.get(codename=codename))
        except Permission.DoesNotExist:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0005_logacao'),
    ]

    operations = [
        migrations.RunPython(criar_grupos),
    ]
