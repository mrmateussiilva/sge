import calendar
from datetime import datetime

from django.db import migrations, models
from django.db.models import F, Q


def preencher_dados_congelados(apps, schema_editor):
    FechamentoMensal = apps.get_model('estoque', 'FechamentoMensal')
    ItemFechamento = apps.get_model('estoque', 'ItemFechamento')

    for fechamento in FechamentoMensal.objects.all().iterator():
        try:
            inicio = datetime.strptime(fechamento.referencia_mes_ano, '%m/%Y').date().replace(day=1)
        except (TypeError, ValueError):
            inicio = fechamento.data_fechamento.date().replace(day=1)
        fim = inicio.replace(day=calendar.monthrange(inicio.year, inicio.month)[1])
        FechamentoMensal.objects.filter(pk=fechamento.pk).update(
            data_inicio=inicio,
            data_fim=fim,
        )

    itens = ItemFechamento.objects.select_related(
        'produto__categoria',
        'produto__fornecedor',
    )
    for item in itens.iterator():
        produto = item.produto
        if not produto:
            continue
        if produto.tipo_produto in ('PAPEL', 'TECIDO'):
            unidade = 'M'
        elif produto.tipo_produto == 'TINTA':
            unidade = 'L'
        else:
            unidade = produto.unidade_medida or 'UN'
        ItemFechamento.objects.filter(pk=item.pk).update(
            tipo_produto=produto.tipo_produto,
            unidade_medida=unidade,
            categoria_nome=produto.categoria.nome if produto.categoria else '',
            fornecedor_nome=produto.fornecedor.nome if produto.fornecedor else '',
        )


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0014_add_configuracao_omie'),
    ]

    operations = [
        migrations.AddField(
            model_name='fechamentomensal',
            name='data_fim',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='fechamentomensal',
            name='data_inicio',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='fechamentomensal',
            name='referencia_mes_ano',
            field=models.CharField(
                blank=True,
                help_text='Referência legada MM/AAAA, preenchida para períodos mensais completos.',
                max_length=7,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name='itemfechamento',
            name='categoria_nome',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='itemfechamento',
            name='fornecedor_nome',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='itemfechamento',
            name='tipo_produto',
            field=models.CharField(
                blank=True,
                choices=[
                    ('TECIDO', 'Tecido'),
                    ('PAPEL', 'Papel'),
                    ('TINTA', 'Tinta'),
                    ('AVIAMENTO', 'Aviamento'),
                    ('OUTRO', 'Outro'),
                ],
                default='',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='itemfechamento',
            name='unidade_medida',
            field=models.CharField(
                blank=True,
                choices=[
                    ('UN', 'Unidade (un)'),
                    ('M', 'Metros (m)'),
                    ('KG', 'Quilogramas (kg)'),
                    ('L', 'Litros (L)'),
                    ('RL', 'Rolo (rl)'),
                    ('CX', 'Caixa (cx)'),
                    ('PC', 'Peça (pc)'),
                    ('G', 'Gramas (g)'),
                    ('ML', 'Mililitros (ml)'),
                    ('OUTRO', 'Outro'),
                ],
                default='',
                max_length=10,
            ),
        ),
        migrations.RunPython(preencher_dados_congelados, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='fechamentomensal',
            name='data_fim',
            field=models.DateField(),
        ),
        migrations.AlterField(
            model_name='fechamentomensal',
            name='data_inicio',
            field=models.DateField(),
        ),
        migrations.AddConstraint(
            model_name='fechamentomensal',
            constraint=models.UniqueConstraint(
                fields=('data_inicio', 'data_fim'),
                name='fechamento_periodo_unico',
            ),
        ),
        migrations.AddConstraint(
            model_name='fechamentomensal',
            constraint=models.CheckConstraint(
                condition=Q(data_fim__gte=F('data_inicio')),
                name='fechamento_periodo_datas_validas',
            ),
        ),
    ]
