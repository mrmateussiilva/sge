from django.db import migrations


def seed_categorias_e_vincular_produtos(apps, schema_editor):
    Categoria = apps.get_model('estoque', 'Categoria')
    Produto = apps.get_model('estoque', 'Produto')

    categorias_padrao = [
        ('Papéis', '#0284c7', 'Bobinas e papéis para sublimação e impressão'),
        ('Tecidos', '#10b981', 'Tecidos, malhas e insumos têxteis'),
        ('Tintas', '#8b5cf6', 'Tintas sublimáticas, solventes e recargas'),
        ('Aviamentos', '#f59e0b', 'Aviamentos, fitas, zíperes e acessórios'),
        ('Outros Materiais', '#64748b', 'Embalagens, suprimentos e outros materiais gerais'),
    ]

    mapa_categorias = {}
    for nome, cor, descricao in categorias_padrao:
        cat = Categoria.objects.filter(nome__iexact=nome).first()
        if not cat:
            cat = Categoria.objects.create(nome=nome, cor=cor, descricao=descricao)
        mapa_categorias[nome] = cat

    # Mapeamento do tipo_produto antigo para a respectiva categoria padrão
    tipo_para_categoria = {
        'PAPEL': mapa_categorias.get('Papéis'),
        'TECIDO': mapa_categorias.get('Tecidos'),
        'TINTA': mapa_categorias.get('Tintas'),
        'AVIAMENTO': mapa_categorias.get('Aviamentos'),
        'OUTRO': mapa_categorias.get('Outros Materiais'),
    }

    for tipo, cat in tipo_para_categoria.items():
        if cat:
            Produto.objects.filter(tipo_produto=tipo, categoria__isnull=True).update(categoria=cat)


class Migration(migrations.Migration):

    dependencies = [
        ('estoque', '0023_deparaomie_fator_conversao'),
    ]

    operations = [
        migrations.RunPython(seed_categorias_e_vincular_produtos, migrations.RunPython.noop),
    ]
