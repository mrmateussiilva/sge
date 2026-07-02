"""
Script de importação do estoque.xlsx para o banco de dados SGE.

Lógica de importação:
- PAPEL: Nome → descricao, Metro Rolo → metros_por_rolo, Qt Rolos → rolos (calcula total metros)
- TECIDO: Nome → descricao, METROS → quantidade_base (metros direto)
- AVIAMENTOS: Nome → descricao, QUANTIDADE → quantidade_base, OBSERVAÇÃO → extra info
- TINTA: COR → cor_tinta, TIPO → tipo_tinta, Qt. Vidros → vidros, Litros P/ unidade → litros_por_vidro
"""
import os
import sys
import django

# Configura o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, '/app')
django.setup()

import openpyxl
from estoque.models import Produto, Fornecedor

TIPO_TINTA_MAP = {
    'SUBLIMAÇÃO': 'SUBLIMACAO',
    'SUBLIMACAO': 'SUBLIMACAO',
    'SOLVENTE': 'SOLVENTE',
}

COR_MAP = {
    'BLACK': 'BLACK',
    'YELLOW': 'YELLOW',
    'MAGENTA': 'MAGENTA',
    'CYAN': 'CYAN',
    'LIGHT_CYAN': 'LIGHT_CYAN',
    'LIGHT CYAN': 'LIGHT_CYAN',
    'LIGHT_MAGENTA': 'LIGHT_MAGENTA',
    'LIGHT MAGENTA': 'LIGHT_MAGENTA',
    'BRANCO': 'BRANCO',
}

wb = openpyxl.load_workbook('/app/estoque.xlsx')
ws = wb.active

rows = list(ws.iter_rows(values_only=True))

produtos_criados = 0
erros = []

def clean_str(val):
    return str(val).strip() if val else ''

def safe_decimal(val, default=0):
    try:
        return float(val) if val else default
    except (TypeError, ValueError):
        return default

section = None

for i, row in enumerate(rows):
    col0 = clean_str(row[0]).upper()

    # Detecta seções
    if col0 in ('PAPEL', 'TECIDO', 'AVIAMENTOS', 'TINTA'):
        section = col0
        print(f"\n>>> Seção: {section}")
        continue

    # Pula cabeçalhos e linhas vazias
    if not row[0] or col0 in ('NOME', 'COR'):
        continue
    if all(v is None for v in row):
        continue

    try:
        if section == 'PAPEL':
            nome = clean_str(row[0])
            metros_por_rolo = safe_decimal(row[1])
            qt_rolos = safe_decimal(row[2])
            total_metros = metros_por_rolo * qt_rolos

            p = Produto.objects.create(
                tipo_produto='PAPEL',
                descricao=nome,
                quantidade_base=total_metros,
                metros_por_rolo=metros_por_rolo if metros_por_rolo > 0 else None,
            )
            print(f"  [PAPEL] {nome} - {total_metros:.0f} metros ({qt_rolos:.0f} rolos de {metros_por_rolo:.0f} m)")
            produtos_criados += 1

        elif section == 'TECIDO':
            nome = clean_str(row[0])
            fornecedor_nome = clean_str(row[1])
            metros = safe_decimal(row[2])

            fornecedor = None
            if fornecedor_nome:
                fornecedor, _ = Fornecedor.objects.get_or_create(nome=fornecedor_nome.title())

            p = Produto.objects.create(
                tipo_produto='TECIDO',
                descricao=nome,
                quantidade_base=metros,
                fornecedor=fornecedor,
            )
            print(f"  [TECIDO] {nome} - {metros:.0f} metros (fornecedor: {fornecedor_nome or '-'})")
            produtos_criados += 1

        elif section == 'AVIAMENTOS':
            nome = clean_str(row[0])
            observacao = clean_str(row[1])
            quantidade = safe_decimal(row[2])
            descricao_completa = f"{nome} ({observacao})" if observacao else nome

            p = Produto.objects.create(
                tipo_produto='AVIAMENTO',
                descricao=descricao_completa,
                quantidade_base=quantidade,
            )
            print(f"  [AVIAMENTO] {descricao_completa} - qtd: {quantidade:.0f}")
            produtos_criados += 1

        elif section == 'TINTA':
            cor_raw = clean_str(row[0]).upper()
            tipo_raw = clean_str(row[1]).upper()
            qt_vidros = safe_decimal(row[2])
            litros_por_vidro = safe_decimal(row[3], default=1)
            total_litros = qt_vidros * litros_por_vidro

            cor = COR_MAP.get(cor_raw, 'INCOLOR')
            tipo_tinta = TIPO_TINTA_MAP.get(tipo_raw, 'N/A')

            descricao = f"Tinta {tipo_raw.title()} - {cor_raw.title()}"

            p = Produto.objects.create(
                tipo_produto='TINTA',
                descricao=descricao,
                quantidade_base=total_litros,
                cor_tinta=cor,
                tipo_tinta=tipo_tinta,
                litros_por_vidro=litros_por_vidro if litros_por_vidro > 0 else None,
            )
            print(f"  [TINTA] {descricao} - {total_litros:.0f} L ({qt_vidros:.0f} vidros de {litros_por_vidro:.1f} L)")
            produtos_criados += 1

    except Exception as e:
        erros.append(f"Linha {i+1}: {e}")
        print(f"  [ERRO] Linha {i+1}: {e}")

print(f"\n{'='*50}")
print(f"Importação concluída: {produtos_criados} produtos criados.")
if erros:
    print(f"{len(erros)} erros encontrados:")
    for e in erros:
        print(f"  - {e}")
