from django.db import migrations


def criptografar_segredos_omie(apps, schema_editor):
    ConfiguracaoOmie = apps.get_model('estoque', 'ConfiguracaoOmie')
    for config in ConfiguracaoOmie.objects.exclude(app_secret='').iterator():
        # O campo criptografa no get_prep_value durante o save.
        config.save(update_fields=['app_secret'])


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0019_alter_configuracaoomie_app_secret'),
    ]

    operations = [
        migrations.RunPython(criptografar_segredos_omie, migrations.RunPython.noop),
    ]
