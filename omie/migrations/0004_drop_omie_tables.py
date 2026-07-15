from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('omie', '0003_omierecebimentonfe_omierecebimentoitem'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                'DROP TABLE IF EXISTS omie_omierecebimentoitem',
                'DROP TABLE IF EXISTS omie_omierecebimentonfe',
                'DROP TABLE IF EXISTS omie_omienotaentradaitem',
                'DROP TABLE IF EXISTS omie_omienotaentrada',
                'DROP TABLE IF EXISTS omie_omieprodutomapping',
                'DROP TABLE IF EXISTS omie_omieconfig',
            ],
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
