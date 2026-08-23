from django.db import migrations


def normalizar_perfis(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model('auth', 'User')

    Group.objects.get_or_create(name='Gestor')
    Group.objects.get_or_create(name='Leitura')
    visualizador, _ = Group.objects.get_or_create(name='Visualizador')

    # Usuários antigos sem perfil explícito deixam de herdar permissões por
    # acidente e passam a ter o perfil seguro de leitura.
    for user in User.objects.filter(is_superuser=False, groups__isnull=True).distinct():
        user.groups.add(visualizador)


class Migration(migrations.Migration):
    dependencies = [
        ('estoque', '0016_movimentacao_movimentacao_quantidade_positiva_and_more'),
    ]

    operations = [
        migrations.RunPython(normalizar_perfis, migrations.RunPython.noop),
    ]
