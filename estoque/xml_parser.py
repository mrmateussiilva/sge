"""
Parser de XML de Nota Fiscal Eletrônica (NF-e) - Padrão SEFAZ Brasil.

Suporta tanto o envelope nfeProc (nota processada pela SEFAZ)
quanto o envelope NFe diretamente.
"""
import urllib.request
import xml.etree.ElementTree as ET

# Namespace padrão do portal fiscal brasileiro
NS = 'http://www.portalfiscal.inf.br/nfe'


def _find(element, path):
    """Busca um elemento considerando o namespace."""
    return element.find(f'{{{NS}}}{path}')


def _findtext(element, path, default=''):
    """Retorna o texto de um elemento ou string vazia."""
    el = _find(element, path)
    return el.text.strip() if el is not None and el.text else default


def _map_unidade_medida(unidade: str) -> str:
    """Mapeia a unidade da NF-e para os códigos do modelo Produto."""
    u = unidade.upper().strip()
    if u in ('M', 'MT', 'METRO', 'METROS'):
        return 'M'
    if u in ('L', 'LT', 'LITRO', 'LITROS', 'GAL'):
        return 'L'
    if u in ('KG', 'KILO', 'QUILO', 'KILOGRAMA', 'TON'):
        return 'KG'
    if u in ('RL', 'ROLO', 'ROLOS'):
        return 'RL'
    if u in ('CX', 'CAIXA', 'CAIXAS'):
        return 'CX'
    if u in ('PC', 'PCA', 'PECA', 'PECAS'):
        return 'PC'
    if u in ('G', 'GR', 'GRAMA', 'GRAMAS'):
        return 'G'
    if u in ('ML', 'MILILITRO', 'MILILITROS'):
        return 'ML'
    return 'UN'


def _tipo_por_unidade(unidade: str) -> str:
    """
    Infere o tipo de produto pelo código de unidade de medida da NF-e.
    """
    u = unidade.upper().strip()
    if u in ('M', 'MT', 'METRO', 'METROS'):
        return 'TECIDO'
    if u in ('L', 'LT', 'LITRO', 'LITROS', 'GAL'):
        return 'TINTA'
    if u in ('KG', 'G', 'GR', 'GRAMA', 'TON'):
        return 'AVIAMENTO'
    # UN, PC, CX, RL (rolo), etc.
    return 'AVIAMENTO'


def parse_nfe_xml(xml_content: str) -> dict:
    """
    Faz o parse do XML de NF-e e retorna um dicionário estruturado.

    Args:
        xml_content: String com o conteúdo do XML da NF-e.

    Returns:
        {
            'numero_nf': '123',
            'fornecedor': {'nome': 'FORNECEDOR LTDA', 'cnpj': '00000000000000'},
            'itens': [
                {
                    'descricao': 'TECIDO TACTEL',
                    'quantidade': 150.0,
                    'preco_custo': 12.50,
                    'unidade': 'M',
                    'tipo_produto_sugerido': 'TECIDO',
                    'ncm': '60019200',
                    'codigo_produto': '001',
                },
                ...
            ]
        }

    Raises:
        ValueError: Se o XML não for uma NF-e válida ou estiver malformado.
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise ValueError(f'XML inválido ou corrompido: {e}')

    # O XML pode ser <nfeProc> (nota processada) ou <NFe> diretamente
    tag = root.tag.replace(f'{{{NS}}}', '')

    if tag == 'nfeProc':
        nfe = _find(root, 'NFe')
    elif tag == 'NFe':
        nfe = root
    else:
        raise ValueError(
            f'XML não reconhecido como NF-e. Tag raiz encontrada: "{tag}". '
            f'Esperado: "nfeProc" ou "NFe".'
        )

    if nfe is None:
        raise ValueError('Elemento <NFe> não encontrado dentro do XML.')

    inf_nfe = _find(nfe, 'infNFe')
    if inf_nfe is None:
        raise ValueError('Elemento <infNFe> não encontrado. XML de NF-e inválido.')

    # Dados do emitente (fornecedor)
    emit = _find(inf_nfe, 'emit')
    fornecedor = {
        'nome': _findtext(emit, 'xNome') if emit is not None else '',
        'cnpj': _findtext(emit, 'CNPJ') if emit is not None else '',
    }

    # Número da nota
    ide = _find(inf_nfe, 'ide')
    numero_nf = _findtext(ide, 'nNF') if ide is not None else ''

    # Itens da nota
    itens = []
    for det in inf_nfe.findall(f'{{{NS}}}det'):
        prod = _find(det, 'prod')
        if prod is None:
            continue

        descricao = _findtext(prod, 'xProd')
        unidade = _findtext(prod, 'uCom', 'UN')
        ncm = _findtext(prod, 'NCM')
        codigo = _findtext(prod, 'cProd')

        try:
            quantidade = float(_findtext(prod, 'qCom', '0').replace(',', '.'))
        except ValueError:
            quantidade = 0.0

        try:
            preco_custo = float(_findtext(prod, 'vUnCom', '0').replace(',', '.'))
        except ValueError:
            preco_custo = 0.0

        if not descricao:
            continue

        itens.append({
            'descricao': descricao,
            'quantidade': round(quantidade, 4),
            'preco_custo': round(preco_custo, 4),
            'unidade': unidade,
            'unidade_medida': _map_unidade_medida(unidade),
            'tipo_produto_sugerido': _tipo_por_unidade(unidade),
            'ncm': ncm,
            'codigo_produto': codigo,
        })

    if not itens:
        raise ValueError('Nenhum item de produto encontrado nesta NF-e.')

    return {
        'numero_nf': numero_nf,
        'fornecedor': fornecedor,
        'itens': itens,
    }


def fetch_xml_from_url(url: str, timeout: int = 15) -> str:
    """
    Faz o download do XML a partir de uma URL.

    Args:
        url: URL direta para o arquivo XML da NF-e.
        timeout: Tempo máximo de espera em segundos.

    Returns:
        String com o conteúdo do XML.

    Raises:
        ValueError: Em caso de erro de rede, timeout ou resposta inválida.
    """
    if not url.startswith(('http://', 'https://')):
        raise ValueError('URL inválida. Deve começar com http:// ou https://')

    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'SGE/1.0 (Sistema de Gestão de Estoque)',
                'Accept': 'application/xml, text/xml, */*',
            }
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            content_type = response.headers.get('Content-Type', '')
            raw = response.read()

        # Tenta detectar encoding pelo BOM ou header
        if raw.startswith(b'\xef\xbb\xbf'):
            return raw.decode('utf-8-sig')
        return raw.decode('utf-8', errors='replace')

    except urllib.error.HTTPError as e:
        raise ValueError(f'Erro HTTP {e.code} ao acessar a URL: {e.reason}')
    except urllib.error.URLError as e:
        raise ValueError(f'Não foi possível acessar a URL: {e.reason}')
    except TimeoutError:
        raise ValueError('Tempo de conexão esgotado. Verifique a URL e tente novamente.')
