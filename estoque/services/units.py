from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class UnidadeInfo:
    codigo: str
    simbolo: str
    singular: str
    plural: str


UNIDADES = {
    'UN': UnidadeInfo('UN', 'un', 'unidade', 'unidades'),
    'M': UnidadeInfo('M', 'm', 'metro', 'metros'),
    'KG': UnidadeInfo('KG', 'kg', 'quilograma', 'quilogramas'),
    'L': UnidadeInfo('L', 'L', 'litro', 'litros'),
    'G': UnidadeInfo('G', 'g', 'grama', 'gramas'),
    'ML': UnidadeInfo('ML', 'ml', 'mililitro', 'mililitros'),
    'PC': UnidadeInfo('PC', 'pc', 'peça', 'peças'),
    'CX': UnidadeInfo('CX', 'cx', 'caixa', 'caixas'),
    'RL': UnidadeInfo('RL', 'rl', 'rolo', 'rolos'),
    'OUTRO': UnidadeInfo('OUTRO', '', 'unidade', 'unidades'),
}


def decimal_br(valor, casas=2):
    valor = Decimal('0') if valor is None else Decimal(valor)
    quantizado = valor.quantize(Decimal('1').scaleb(-casas))
    inteiro, decimal = f'{quantizado:,.{casas}f}'.split('.')
    return f'{inteiro.replace(",", ".")},{decimal}'


def dinheiro_br(valor):
    return f'R$ {decimal_br(valor, 2)}'


def unidade_base_codigo(produto):
    if produto.tipo_produto in ('PAPEL', 'TECIDO'):
        return 'M'
    if produto.tipo_produto == 'TINTA':
        return 'L'
    return produto.unidade_medida or 'UN'


def unidade_info(produto):
    return UNIDADES.get(unidade_base_codigo(produto), UNIDADES['OUTRO'])


def unidade_simbolo(produto):
    return unidade_info(produto).simbolo


def formatar_quantidade(valor, codigo, casas=2):
    unidade = UNIDADES.get(codigo, UNIDADES['OUTRO'])
    sufixo = f' {unidade.simbolo}' if unidade.simbolo else ''
    return f'{decimal_br(valor, casas)}{sufixo}'


def formatar_quantidade_produto(produto, casas=2):
    return formatar_quantidade(produto.quantidade_base, unidade_base_codigo(produto), casas)


def formatar_capacidade_embalagem(produto):
    if produto.tipo_produto in ('PAPEL', 'TECIDO'):
        return formatar_quantidade(produto.metros_por_rolo, 'M') if produto.metros_por_rolo else '—'
    if produto.tipo_produto == 'TINTA':
        return formatar_quantidade(produto.litros_por_vidro, 'L') if produto.litros_por_vidro else '—'
    return '—'


def embalagens_estimadas(produto):
    if produto.tipo_produto in ('PAPEL', 'TECIDO'):
        return produto.quantidade_rolos_estimada
    if produto.tipo_produto == 'TINTA':
        return produto.quantidade_vidros_estimada
    return Decimal('0')
