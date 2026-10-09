"""
Cliente para a API JSON-RPC do Omie.

Documentação: https://app.omie.com.br/api/v1/produtos/notaentrada/

Cada chamada é um POST para o endpoint com o corpo:
  {
    "call": "<NomeDoMetodo>",
    "app_key": "<APP_KEY>",
    "app_secret": "<APP_SECRET>",
    "param": [<payload>]
  }
"""

import json
import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

OMIE_BASE_URL = 'https://app.omie.com.br/api/v1/'


def limpar_cnpj(val: str | None) -> str:
    """Remove caracteres não numéricos de um CNPJ/CPF."""
    if not val:
        return ''
    return re.sub(r'\D', '', str(val))


def extrair_cnpj_emitente_chave(chave: str | None) -> str:
    """Na chave de 44 dígitos da NF-e, os dígitos 6 a 19 contêm o CNPJ do emitente."""
    if chave and len(str(chave).strip()) == 44:
        return str(chave).strip()[6:20]
    return ''


class OmieAPIError(Exception):
    """Erro retornado pela API do Omie."""

    def __init__(self, codigo: str, descricao: str):
        self.codigo = codigo
        self.descricao = descricao
        super().__init__(f'[{codigo}] {descricao}')


class OmieConfigError(Exception):
    """Credenciais Omie não configuradas."""


@dataclass
class ItemNotaEntrada:
    """Representa um item de produto dentro de uma Nota de Entrada."""

    cod_item_int: str            # cCodItInt
    n_cod_prod: int              # nCodProd — ID do produto no Omie
    codigo_produto: str          # cCodigo — código interno do produto no Omie
    descricao: str               # cDescricao
    quantidade: float            # nQtde
    valor_unitario: float        # nValUnit
    cfop: str                    # cCFOP
    unidade: str = ''            # cUnid


@dataclass
class NotaEntrada:
    """Representa o cabeçalho + itens de uma Nota de Entrada do Omie."""

    n_cod_nota_ent: int                      # ID interno do Omie
    cod_int_nota_ent: str                    # cCodIntNotaEnt — código de integração
    numero_nfe: str                          # cNumNFe
    serie: str                               # cSerie
    fornecedor_nome: str                     # nome do fornecedor/emitente
    fornecedor_cnpj: str                     # CNPJ
    data_previsao: str                       # dPrevisao (DD/MM/AAAA)
    status: str                              # status da nota
    itens: list[ItemNotaEntrada] = field(default_factory=list)
    chave_nfe: str = ''


def obter_credenciais_omie() -> tuple[str, str]:
    """
    Retorna (app_key, app_secret) do banco de dados (ConfiguracaoOmie) se configurado,
    ou fallback para as variáveis de ambiente (settings.OMIE_APP_KEY / settings.OMIE_APP_SECRET).
    """
    try:
        from estoque.models import ConfiguracaoOmie
        cfg = ConfiguracaoOmie.objects.first()
        if cfg and cfg.app_key and cfg.app_secret:
            return cfg.app_key, cfg.app_secret
    except Exception as exc:
        logger.warning('Não foi possível carregar ConfiguracaoOmie do banco: %s', exc)

    return getattr(settings, 'OMIE_APP_KEY', ''), getattr(settings, 'OMIE_APP_SECRET', '')


class OmieClient:
    """
    Cliente para a API Omie (Recebimento NF-e e Notas de Entrada).

    Uso:
        client = OmieClient()
        resumo = client.listar_recebimentos_fornecedores_periodo('01/10/2026', '08/10/2026')
    """

    ENDPOINT_NOTA_ENTRADA = 'produtos/notaentrada/'
    ENDPOINT_RECEBIMENTO = 'produtos/recebimentonfe/'

    def __init__(self, app_key: str | None = None, app_secret: str | None = None):
        db_key, db_secret = obter_credenciais_omie()
        self.app_key = app_key or db_key
        self.app_secret = app_secret or db_secret
        if not self.app_key or not self.app_secret:
            raise OmieConfigError(
                'Credenciais Omie não configuradas. '
                'Cadastre o App Key e App Secret na tela de integração do Omie ou no arquivo .env.'
            )

    def _chamar(self, endpoint: str, metodo: str, param: dict[str, Any]) -> dict:
        """Executa uma chamada JSON-RPC para a API Omie."""
        url = OMIE_BASE_URL + endpoint
        payload = {
            'call': metodo,
            'app_key': self.app_key,
            'app_secret': self.app_secret,
            'param': [param],
        }
        body = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=body,
            method='POST',
            headers={'Content-Type': 'application/json'},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))

        except urllib.error.HTTPError as exc:
            corpo = exc.read().decode('utf-8', errors='replace')
            logger.error('Omie HTTPError %s: %s', exc.code, corpo)
            try:
                err = json.loads(corpo)
                raise OmieAPIError(
                    str(err.get('faultcode', exc.code)),
                    err.get('faultstring', corpo),
                ) from exc
            except (json.JSONDecodeError, KeyError):
                raise OmieAPIError(str(exc.code), corpo) from exc
        except urllib.error.URLError as exc:
            raise OmieAPIError('NETWORK', str(exc.reason)) from exc

        if 'faultcode' in data:
            raise OmieAPIError(data['faultcode'], data.get('faultstring', ''))

        return data

    # ─── Métodos públicos ────────────────────────────────────────────────────

    def listar_notas_entrada(
        self,
        pagina: int = 1,
        registros_por_pagina: int = 20,
        cnpj_fornecedor: str = '',
        data_inicio: str = '',
        data_fim: str = '',
        ordenar_decrescente: bool = True,
    ) -> dict:
        """
        Lista notas de entrada no Omie com suporte a filtros.

        Retorna o dict bruto da API:
          {
            "nPagina": 1,
            "nTotPaginas": 5,
            "nRegistros": 100,
            "notas": [ {...}, ... ]
          }
        """
        param: dict[str, Any] = {
            'nPagina': pagina,
            'nRegistrosPorPagina': registros_por_pagina,
        }
        if cnpj_fornecedor:
            param['cCnpjForn'] = cnpj_fornecedor.strip()
        if data_inicio:
            param['dEmiInicial'] = data_inicio.strip()
        if data_fim:
            param['dEmiFinal'] = data_fim.strip()

        return self._chamar(self.ENDPOINT_NOTA_ENTRADA, 'ListarNotaEnt', param)

    def listar_nfe_recebidas(
        self,
        pagina: int = 1,
        registros_por_pagina: int = 20,
    ) -> dict:
        """Lista NF-e Recebidas no Omie (capturadas via distribuição DF-e/SEFAZ)."""
        param = {
            'nPagina': pagina,
            'nRegistrosPorPagina': registros_por_pagina,
        }
        return self._chamar('produtos/nferecebida/', 'ListarNFeRecebidas', param)

    def consultar_nota_entrada(self, n_cod_nota_ent: int) -> dict:
        """Consulta o detalhe completo de uma nota de entrada pelo ID Omie."""
        param = {
            'nCodNotaEnt': n_cod_nota_ent,
            'cCodIntNotaEnt': '',
        }
        return self._chamar(self.ENDPOINT_NOTA_ENTRADA, 'ConsultarNotaEnt', param)

    def consultar_produto(self, n_cod_prod: int) -> dict:
        """Consulta dados do produto no Omie pelo nCodProd."""
        param = {'codigo_produto': n_cod_prod}
        return self._chamar('geral/produtos/', 'ConsultarProduto', param)

    # ─── Helpers de parsing ──────────────────────────────────────────────────

    def parse_nota(self, raw: dict, prod_cache: dict[int, dict] | None = None) -> NotaEntrada:
        """
        Converte o dict bruto de ListarNotaEnt / ConsultarNotaEnt em um NotaEntrada estruturado.
        """
        if prod_cache is None:
            prod_cache = {}

        cabec = raw.get('cabec', raw)
        n_cod_nota_ent = int(cabec.get('nCodNotaEnt', raw.get('nCodNotaEnt', 0)))

        # Se a nota da listagem não contiver a lista de produtos, busca o detalhe completo
        produtos_raw = raw.get('produtos', [])
        if not produtos_raw and n_cod_nota_ent:
            try:
                det = self.consultar_nota_entrada(n_cod_nota_ent)
                produtos_raw = det.get('produtos', [])
                if 'totais' in det and 'totais' not in raw:
                    raw['totais'] = det['totais']
            except Exception as exc:
                logger.warning('Erro ao consultar detalhe da nota #%s: %s', n_cod_nota_ent, exc)

        itens = []
        for p in produtos_raw:
            n_cod_prod = int(p.get('nCodProd', 0))
            descricao = p.get('cDescricao', p.get('descricao', ''))
            codigo_produto = p.get('cCodigo', p.get('codigo', ''))
            unidade = p.get('cUnid', p.get('unidade', ''))

            # Se a descrição do produto não veio no payload da nota, busca no cadastro de produtos Omie
            if not descricao and n_cod_prod:
                if n_cod_prod not in prod_cache:
                    try:
                        p_info = self.consultar_produto(n_cod_prod)
                        prod_cache[n_cod_prod] = p_info
                    except Exception as exc:
                        logger.warning('Erro ao consultar produto #%s no Omie: %s', n_cod_prod, exc)
                        prod_cache[n_cod_prod] = {}

                p_info = prod_cache.get(n_cod_prod, {})
                descricao = p_info.get('descricao', f'Produto #{n_cod_prod}')
                codigo_produto = p_info.get('codigo', '')
                unidade = p_info.get('unidade', '')

            itens.append(ItemNotaEntrada(
                cod_item_int=p.get('cCodItInt', str(p.get('nCodIt', ''))),
                n_cod_prod=n_cod_prod,
                codigo_produto=str(codigo_produto),
                descricao=str(descricao),
                quantidade=float(p.get('nQtde', 0)),
                valor_unitario=float(p.get('nValUnit', 0)),
                cfop=str(p.get('cCFOP', '')),
                unidade=str(unidade),
            ))

        # Dados de NFe emitida (pode estar aninhado)
        lista_nfe = raw.get('lista_nfe', [])
        chave = lista_nfe[0].get('cChaveNFe', '') if lista_nfe else ''
        numero_nfe = (
            lista_nfe[0].get('cNumNFe', '') if lista_nfe
            else cabec.get('cNumeroNotaEnt', cabec.get('cNumNFe', ''))
        )
        serie = lista_nfe[0].get('cSerieNFe', '') if lista_nfe else cabec.get('cSerie', '')

        # Fornecedor / emitente
        ide = raw.get('ide', {})
        emit = raw.get('emit', {})
        fornecedor_nome = emit.get('xNome', ide.get('xNome', cabec.get('cNomeForn', '')))
        fornecedor_cnpj = emit.get('CNPJ', ide.get('CNPJ', cabec.get('cCnpjForn', '')))

        return NotaEntrada(
            n_cod_nota_ent=n_cod_nota_ent,
            cod_int_nota_ent=cabec.get('cCodIntNotaEnt', ''),
            numero_nfe=str(numero_nfe),
            serie=str(serie),
            fornecedor_nome=str(fornecedor_nome),
            fornecedor_cnpj=str(fornecedor_cnpj),
            data_previsao=cabec.get('dPrevisao', cabec.get('dEmi', '')),
            status=str(raw.get('status', cabec.get('cStatus', ''))),
            itens=itens,
            chave_nfe=str(chave),
        )

    def listar_notas_parseadas(
        self,
        pagina: int = 1,
        registros_por_pagina: int = 20,
        cnpj_fornecedor: str = '',
        data_inicio: str = '',
        data_fim: str = '',
        ordenar_decrescente: bool = True,
    ) -> tuple[list[NotaEntrada], int, int]:
        """
        Retorna notas de entrada já parseadas e enriquecidas com seus itens.

        Returns:
            (notas, total_paginas, total_registros)
        """
        raw = self.listar_notas_entrada(
            pagina=pagina,
            registros_por_pagina=registros_por_pagina,
            cnpj_fornecedor=cnpj_fornecedor,
            data_inicio=data_inicio,
            data_fim=data_fim,
            ordenar_decrescente=ordenar_decrescente,
        )
        notas_raw = raw.get('notas', raw.get('cadastros', []))

        total_paginas = int(raw.get('nTotalPaginas') or raw.get('nTotPaginas') or 1)
        total_registros = int(raw.get('nTotalRegistros') or raw.get('nRegistros') or len(notas_raw))

        prod_cache: dict[int, dict] = {}
        notas = [self.parse_nota(c, prod_cache=prod_cache) for c in notas_raw]
        if ordenar_decrescente:
            notas.sort(key=lambda n: n.n_cod_nota_ent, reverse=True)
        return notas, total_paginas, total_registros

    def consultar_nota_parseada(self, n_cod_nota_ent: int) -> NotaEntrada:
        """Consulta e retorna uma única nota já parseada com seus itens completos."""
        raw = self.consultar_nota_entrada(n_cod_nota_ent)
        return self.parse_nota(raw)

    def listar_recebimentos(
        self,
        dt_inicio: str = '',
        dt_fim: str = '',
        pagina: int = 1,
        registros_por_pagina: int = 50,
        incluir_detalhes: bool = True,
    ) -> dict:
        """
        Consulta o endpoint /api/v1/produtos/recebimentonfe/ da Omie com a chamada ListarRecebimentos.
        """
        param: dict[str, Any] = {
            'nPagina': pagina,
            'nRegistrosPorPagina': registros_por_pagina,
            'cExibirDetalhes': 'S' if incluir_detalhes else 'N',
        }
        if dt_inicio:
            param['dtEmissaoDe'] = dt_inicio
        if dt_fim:
            param['dtEmissaoAte'] = dt_fim

        return self._chamar(self.ENDPOINT_RECEBIMENTO, 'ListarRecebimentos', param)

    def listar_recebimentos_fornecedores_periodo(
        self,
        dt_inicio: str,
        dt_fim: str,
        apenas_fornecedores: bool = True,
        incluir_detalhes: bool = True,
        max_paginas: int = 10,
    ) -> dict:
        """
        Busca os recebimentos de NF-e na Omie filtrando por período de emissão e documento:
        - Apenas Modelo 55 (NF-e de mercadoria/produtos)
        - Descarta Modelo 57 (CT-e de frete de transportadoras)
        - Descarta emissões próprias (emitente == CNPJ da empresa)
        """
        cnpj_proprio = limpar_cnpj(getattr(settings, 'OMIE_CNPJ_PROPRIO', '06098674000157'))
        todas_notas = []
        pagina = 1
        total_paginas = 1

        while pagina <= total_paginas and pagina <= max_paginas:
            resp = self.listar_recebimentos(
                dt_inicio=dt_inicio,
                dt_fim=dt_fim,
                pagina=pagina,
                registros_por_pagina=50,
                incluir_detalhes=incluir_detalhes,
            )
            total_paginas = int(resp.get('nTotalPaginas') or 1)
            recebimentos = resp.get('recebimentos', [])

            for rec in recebimentos:
                cabec = rec.get('cabec', {})
                modelo = str(cabec.get('cModeloNFe', '')).strip()
                chave = str(cabec.get('cChaveNFe', '')).strip()
                cnpj_cabec = limpar_cnpj(cabec.get('cCNPJ_CPF', ''))
                cnpj_emitente_chave = extrair_cnpj_emitente_chave(chave)
                cnpj_emitente = cnpj_emitente_chave or cnpj_cabec

                eh_nfe = modelo == '55'
                eh_cte = modelo == '57'
                eh_propria = (cnpj_emitente == cnpj_proprio) or (cnpj_cabec == cnpj_proprio)

                # Estrutura padronizada de itens
                itens_limpos = []
                for it in rec.get('itensRecebimento', []):
                    cb = it.get('itensCabec', {})
                    itens_limpos.append({
                        'codigo_produto': str(cb.get('cCodigoProduto', '')),
                        'descricao': str(cb.get('cDescricaoProduto', '')),
                        'ncm': str(cb.get('cNCM', '')),
                        'cfop': str(cb.get('cCFOP', '')),
                        'quantidade': float(cb.get('nQtdeNFe', 0) or 0),
                        'unidade': str(cb.get('cUnidadeNfe', 'UN')),
                        'preco_unitario': float(cb.get('nPrecoUnit', 0) or 0),
                        'valor_total': float(cb.get('vTotalItem', 0) or 0),
                        'id_produto': cb.get('nIdProduto', 0),
                        'id_item': cb.get('nIdItem', 0),
                    })

                # Parcelas
                parcelas_limpas = []
                for p_idx, p in enumerate(rec.get('parcelas', [])):
                    parcelas_limpas.append({
                        'sequencia': int(p.get('nSequencia', p_idx + 1)),
                        'vencimento': str(p.get('dVencimento', '')),
                        'valor': float(p.get('vParcela', 0) or 0),
                    })

                nota_estruturada = {
                    'id_receb': int(cabec.get('nIdReceb', 0)),
                    'id_fornecedor': cabec.get('nIdFornecedor'),
                    'numero_nfe': str(cabec.get('cNumeroNFe', '')),
                    'serie': str(cabec.get('cSerieNFe', '')),
                    'chave_nfe': chave,
                    'data_emissao': str(cabec.get('dEmissaoNFe', '')),
                    'fornecedor_nome': str(cabec.get('cNome', '')),
                    'fornecedor_razao': str(cabec.get('cRazaoSocial', '')),
                    'fornecedor_cnpj': str(cabec.get('cCNPJ_CPF', '')),
                    'valor_total': float(cabec.get('nValorNFe', 0) or 0),
                    'natureza_operacao': str(cabec.get('cNaturezaOperacao', '')),
                    'etapa': str(cabec.get('cEtapa', '')),
                    'itens': itens_limpos,
                    'parcelas': parcelas_limpas,
                    '_meta': {
                        'tipo_doc': 'NF-e (Mercadoria)' if eh_nfe else ('CT-e (Frete)' if eh_cte else f'Modelo {modelo}'),
                        'modelo': modelo,
                        'cnpj_emitente': cnpj_emitente,
                        'eh_propria': eh_propria,
                        'eh_fornecedor_nfe': eh_nfe and not eh_propria,
                    },
                }

                if apenas_fornecedores:
                    if eh_nfe and not eh_propria:
                        todas_notas.append(nota_estruturada)
                else:
                    todas_notas.append(nota_estruturada)

            pagina += 1

        def _chave_data(item):
            d = item.get('data_emissao', '')
            try:
                return datetime.strptime(d, '%d/%m/%Y').date()
            except Exception:
                return datetime.min.date()

        todas_notas.sort(key=_chave_data, reverse=True)

        valor_total = sum(n['valor_total'] for n in todas_notas)
        return {
            'periodo': {'inicio': dt_inicio, 'fim': dt_fim},
            'total_encontradas': len(todas_notas),
            'valor_total': valor_total,
            'notas': todas_notas,
        }

