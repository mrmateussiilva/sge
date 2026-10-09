from decimal import Decimal
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from estoque.models import (
    ConfiguracaoOmie,
    HistoricoPreco,
    ImportacaoNFe,
    Movimentacao,
    Produto,
)
from estoque.services.omie_client import (
    OmieClient,
    extrair_cnpj_emitente_chave,
    limpar_cnpj,
)

User = get_user_model()


class OmieHelpersTestCase(TestCase):
    def test_limpar_cnpj(self):
        self.assertEqual(limpar_cnpj('06.098.674/0001-57'), '06098674000157')
        self.assertEqual(limpar_cnpj(''), '')
        self.assertEqual(limpar_cnpj(None), '')

    def test_extrair_cnpj_emitente_chave(self):
        # Chave de 44 dígitos: posições 6 a 19 contêm o CNPJ
        # Exemplo: 32 2610 31800170004333 55 001 000003425 1 00157877 7
        chave = '32261031800170004333550010000034251001578777'
        self.assertEqual(extrair_cnpj_emitente_chave(chave), '31800170004333')
        self.assertEqual(extrair_cnpj_emitente_chave('invalida'), '')
        self.assertEqual(extrair_cnpj_emitente_chave(''), '')


class OmieClientRecebimentosTestCase(TestCase):
    @patch.object(OmieClient, '_chamar')
    def test_listar_recebimentos_fornecedores_filtra_modelo_e_propria(self, mock_chamar):
        mock_chamar.return_value = {
            'nPagina': 1,
            'nTotalPaginas': 1,
            'recebimentos': [
                {
                    'cabec': {
                        'nIdReceb': 1001,
                        'cNumeroNFe': '000001',
                        'cSerieNFe': '1',
                        'cModeloNFe': '55',
                        'dEmissaoNFe': '05/10/2026',
                        'cNome': 'FORNECEDOR TECIDOS',
                        'cRazaoSocial': 'TECIDOS LTDA',
                        'cCNPJ_CPF': '12.345.678/0001-90',
                        'cChaveNFe': '35261012345678000190550010000000011000000001',
                        'nValorNFe': 1500.50,
                        'cEtapa': '40',
                    },
                    'itensRecebimento': [
                        {
                            'itensCabec': {
                                'cCodigoProduto': 'TEC01',
                                'cDescricaoProduto': 'TECIDO DRY FIT',
                                'nQtdeNFe': 100,
                                'cUnidadeNfe': 'M',
                                'nPrecoUnit': 15.00,
                                'vTotalItem': 1500.00,
                            }
                        }
                    ],
                    'parcelas': [
                        {'nSequencia': 1, 'dVencimento': '05/11/2026', 'vParcela': 1500.50}
                    ]
                },
                {
                    # Modelo 57 (CT-e de transporte) — deve ser filtrado
                    'cabec': {
                        'nIdReceb': 1002,
                        'cNumeroNFe': '000002',
                        'cModeloNFe': '57',
                        'dEmissaoNFe': '06/10/2026',
                        'cNome': 'TRANSPORTADORA AGUIA',
                        'cCNPJ_CPF': '99.888.777/0001-11',
                        'nValorNFe': 200.00,
                    },
                    'itensRecebimento': []
                },
                {
                    # Emissão Própria (CNPJ próprio 06098674000157) — deve ser filtrada
                    'cabec': {
                        'nIdReceb': 1003,
                        'cNumeroNFe': '000003',
                        'cModeloNFe': '55',
                        'dEmissaoNFe': '07/10/2026',
                        'cNome': 'BLIZU SUBLIMACAO',
                        'cCNPJ_CPF': '06.098.674/0001-57',
                        'cChaveNFe': '35261006098674000157550010000000031000000003',
                        'nValorNFe': 500.00,
                    },
                    'itensRecebimento': []
                }
            ]
        }

        client = OmieClient(app_key='TEST_KEY', app_secret='TEST_SECRET')
        resumo = client.listar_recebimentos_fornecedores_periodo(
            dt_inicio='01/10/2026',
            dt_fim='10/10/2026',
            apenas_fornecedores=True,
        )

        self.assertEqual(resumo['total_encontradas'], 1)
        self.assertEqual(resumo['valor_total'], 1500.50)
        nota = resumo['notas'][0]
        self.assertEqual(nota['numero_nfe'], '000001')
        self.assertEqual(nota['fornecedor_nome'], 'FORNECEDOR TECIDOS')
        self.assertEqual(len(nota['itens']), 1)
        self.assertEqual(nota['itens'][0]['descricao'], 'TECIDO DRY FIT')
        self.assertEqual(len(nota['parcelas']), 1)

    @patch.object(OmieClient, '_chamar')
    def test_listar_recebimentos_parcelas_dict_e_itens_nulos(self, mock_chamar):
        """Valida que a estrutura real da Omie (parcelas como dict e itensRecebimento nulo) é tratada sem erros."""
        mock_chamar.return_value = {
            'nPagina': 1,
            'nTotalPaginas': 1,
            'recebimentos': [
                {
                    'cabec': {
                        'nIdReceb': 2001,
                        'cNumeroNFe': '000170482',
                        'cSerieNFe': '2',
                        'cModeloNFe': '55',
                        'dEmissaoNFe': '07/01/2026',
                        'cNome': 'FABR.DE ELAST. SAO JOSE LTDA.',
                        'cCNPJ_CPF': '53.859.989/0001-50',
                        'cChaveNFe': '35260153859989000150550020001704821430212899',
                        'nValorNFe': 1358.50,
                    },
                    'itensRecebimento': [
                        {
                            'itensCabec': {
                                'cCodigoProduto': '3014RL50',
                                'cDescricaoProduto': 'ELASTICO LASTEX',
                                'nQtdeNFe': 10,
                                'nPrecoUnit': 15.15,
                                'vTotalItem': 151.50,
                            }
                        }
                    ],
                    # Formato real retornado pela Omie: dict com parcelasLista
                    'parcelas': {
                        'cCodParcela': '999',
                        'nQtdParcela': 2,
                        'parcelasLista': [
                            {'nSequencia': 1, 'dVencimento': '04/02/2026', 'vParcela': 679.25},
                            {'nSequencia': 2, 'dVencimento': '04/03/2026', 'vParcela': 679.25},
                        ]
                    }
                },
                {
                    'cabec': {
                        'nIdReceb': 2002,
                        'cNumeroNFe': '000099',
                        'cModeloNFe': '55',
                        'dEmissaoNFe': '08/01/2026',
                        'cNome': 'FORNECEDOR SEM ITENS',
                        'cCNPJ_CPF': '99.999.999/0001-99',
                        'nValorNFe': 50.0,
                    },
                    # itensRecebimento como None e parcelas à vista sem parcelasLista
                    'itensRecebimento': None,
                    'parcelas': {'cCodParcela': '000', 'nQtdParcela': 1}
                }
            ]
        }

        client = OmieClient(app_key='TEST_KEY', app_secret='TEST_SECRET')
        resumo = client.listar_recebimentos_fornecedores_periodo(
            dt_inicio='01/01/2026',
            dt_fim='10/01/2026',
        )

        self.assertEqual(resumo['total_encontradas'], 2)
        n1 = resumo['notas'][0]  # ordenado por data: 08/01 depois 07/01
        self.assertEqual(n1['numero_nfe'], '000099')
        self.assertEqual(len(n1['itens']), 0)
        self.assertEqual(len(n1['parcelas']), 0)

        n2 = resumo['notas'][1]
        self.assertEqual(n2['numero_nfe'], '000170482')
        self.assertEqual(len(n2['itens']), 1)
        self.assertEqual(len(n2['parcelas']), 2)
        self.assertEqual(n2['parcelas'][0]['valor'], 679.25)


class OmieAPITestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='operador', password='senha-forte-123')
        self.admin = User.objects.create_superuser(username='admin', password='senha-forte-123')

    @patch.object(OmieClient, 'listar_recebimentos_fornecedores_periodo')
    def test_listar_notas_omie_api(self, mock_listar):
        mock_listar.return_value = {
            'periodo': {'inicio': '01/10/2026', 'fim': '10/10/2026'},
            'total_encontradas': 1,
            'valor_total': 1200.00,
            'notas': [
                {
                    'id_receb': 5001,
                    'numero_nfe': '1234',
                    'serie': '1',
                    'chave_nfe': '35261011111111000190550010000012341000000001',
                    'data_emissao': '08/10/2026',
                    'fornecedor_nome': 'EUROTEXTIL',
                    'fornecedor_razao': 'EURO TEXTIL S/A',
                    'fornecedor_cnpj': '11.111.111/0001-90',
                    'valor_total': 1200.00,
                    'itens': [{'descricao': 'BOBINA DE PAPEL', 'quantidade': 10, 'valor_total': 1200.00}],
                    'parcelas': [],
                }
            ],
        }

        self.client.force_login(self.user)
        url = reverse('api_v1:omie_notas')
        resp = self.client.get(url, {'dias': 15})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(len(data['notas']), 1)
        self.assertEqual(data['kpis']['total_notas'], 1)
        self.assertEqual(data['kpis']['valor_total'], 1200.00)
        self.assertEqual(data['kpis']['fornecedores_ativos'], 1)
        self.assertEqual(len(data['top_fornecedores']), 1)
        self.assertEqual(data['top_fornecedores'][0]['nome'], 'EUROTEXTIL')

    def test_consultar_e_salvar_configuracao_omie(self):
        # Usuário comum não pode salvar configuração
        self.client.force_login(self.user)
        url_salvar = reverse('api_v1:omie_configuracao_salvar')
        resp_negada = self.client.post(
            url_salvar,
            {'app_key': 'NOVA_KEY', 'app_secret': 'NOVO_SECRET'},
            content_type='application/json',
        )
        self.assertEqual(resp_negada.status_code, 403)

        # Admin pode salvar
        self.client.force_login(self.admin)
        resp_ok = self.client.post(
            url_salvar,
            {'app_key': 'NOVA_KEY', 'app_secret': 'NOVO_SECRET'},
            content_type='application/json',
        )
        self.assertEqual(resp_ok.status_code, 200)
        self.assertTrue(resp_ok.json()['ok'])

        # Consulta configuração
        url_consultar = reverse('api_v1:omie_configuracao')
        resp_get = self.client.get(url_consultar)
        self.assertEqual(resp_get.status_code, 200)
        data_get = resp_get.json()
        self.assertTrue(data_get['configurado'])
        self.assertTrue(data_get['app_key_mascarada'].startswith('NOVA'))

    def test_importar_nota_omie_api_sucesso(self):
        # Produto existente
        prod_existente = Produto.objects.create(
            descricao='BOBINA PAPEL 100M',
            tipo_produto='PAPEL',
            unidade_medida='M',
            quantidade_base=Decimal('50.00'),
            preco_custo=Decimal('10.00'),
        )

        self.client.force_login(self.user)
        url_importar = reverse('api_v1:omie_importar', kwargs={'id_receb': 9901})

        payload = {
            'numero_nfe': 'NF-9901',
            'fornecedor_nome': 'PAPELARIA CENTRAL',
            'fornecedor_cnpj': '22.333.444/0001-55',
            'itens': [
                {
                    'descricao_omie': 'BOBINA PAPEL 100M',
                    'quantidade': 100,
                    'valor_unitario': 12.50,
                    'acao': 'vincular',
                    'produto_id': prod_existente.id,
                    'atualizar_custo': True,
                },
                {
                    'descricao_omie': 'TINTA SUBLIMATICA CYAN',
                    'quantidade': 5,
                    'valor_unitario': 45.00,
                    'acao': 'criar',
                    'novo_produto': {
                        'descricao': 'Tinta Sublimática Cyan 1L',
                        'tipo_produto': 'TINTA',
                        'unidade_medida': 'L',
                        'estoque_minimo': 2,
                    },
                    'atualizar_custo': True,
                },
            ],
        }

        resp = self.client.post(url_importar, payload, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['movimentacoes_criadas'], 2)

        # Verificar produto existente: saldo aumentou em 100 e custo atualizou
        prod_existente.refresh_from_db()
        self.assertEqual(prod_existente.quantidade_base, Decimal('150.00'))
        self.assertEqual(prod_existente.preco_custo, Decimal('12.50'))

        # Verificar histórico de preço registrado
        hp = HistoricoPreco.objects.filter(produto=prod_existente).first()
        self.assertIsNotNone(hp)
        self.assertEqual(hp.preco_custo_antigo, Decimal('10.00'))
        self.assertEqual(hp.preco_custo_novo, Decimal('12.50'))

        # Verificar novo produto criado com entrada de estoque
        novo_prod = Produto.objects.filter(descricao='Tinta Sublimática Cyan 1L').first()
        self.assertIsNotNone(novo_prod)
        self.assertEqual(novo_prod.quantidade_base, Decimal('5.00'))
        self.assertEqual(novo_prod.tipo_produto, 'TINTA')
        self.assertEqual(novo_prod.unidade_medida, 'L')
        self.assertEqual(novo_prod.preco_custo, Decimal('45.00'))

        # Verificar movimentações
        movs = Movimentacao.objects.filter(motivo='COMPRA')
        self.assertEqual(movs.count(), 2)

        # Verificar idempotência gravada
        self.assertTrue(ImportacaoNFe.objects.filter(n_cod_nota_ent=9901).exists())

        # Tentar importar a mesma nota novamente deve ser rejeitado
        resp_repetida = self.client.post(url_importar, payload, content_type='application/json')
        self.assertEqual(resp_repetida.status_code, 400)
        self.assertFalse(resp_repetida.json()['ok'])
        self.assertEqual(resp_repetida.json()['codigo'], 'JA_IMPORTADO')
