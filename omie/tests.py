import decimal
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from unittest.mock import patch

from estoque.models import Fornecedor, Produto, Categoria, Movimentacao
from omie.models import OmieConfig, OmieNotaEntrada, OmieNotaEntradaItem, OmieProdutoMapping
from omie.crypto import encrypt_secret, decrypt_secret
from omie.services import (
    normalizar_nota_entrada, normalizar_item_nota,
    aprovar_nota_entrada, sincronizar_notas_entrada
)

User = get_user_model()


@override_settings(DEBUG=True)
class OmieCryptoTestCase(TestCase):
    def test_encrypt_decrypt_secret(self):
        secret = "minha_chave_super_secreta_123"
        encrypted = encrypt_secret(secret)
        self.assertNotEqual(secret, encrypted)
        decrypted = decrypt_secret(encrypted)
        self.assertEqual(secret, decrypted)

    def test_omie_config_secret_methods(self):
        config = OmieConfig(nome="Config Teste", app_key="key123")
        config.set_app_secret("my_super_secret")
        config.save()

        # Recarrega do banco
        config_db = OmieConfig.objects.get(pk=config.pk)
        self.assertNotEqual(config_db.app_secret_encrypted, "my_super_secret")
        self.assertEqual(config_db.get_app_secret(), "my_super_secret")


class OmieNormalizationTestCase(TestCase):
    def test_normalizar_nota_entrada(self):
        raw_json = {
            "cabecalho": {
                "nIdReceb": 98765,
                "cCodInt": "INT-987",
                "cChaveNFe": "35191100000000000000550010000001231000001234",
                "nNumNota": "555",
                "cSerieNota": "2",
                "dDtEmissao": "10/05/2026",
                "dDtEntrada": "12/05/2026",
                "nValNota": 1250.75
            },
            "fornecedor": {
                "cNome": "FORNECEDOR DE MATERIAIS LTDA",
                "cCNPJ": "12.345.678/0001-90"
            }
        }
        res = normalizar_nota_entrada(raw_json)
        self.assertEqual(res["omie_codigo_nota"], "98765")
        self.assertEqual(res["omie_codigo_integracao"], "INT-987")
        self.assertEqual(res["chave_nfe"], "35191100000000000000550010000001231000001234")
        self.assertEqual(res["numero_nf"], "555")
        self.assertEqual(res["serie"], "2")
        self.assertEqual(res["fornecedor_nome"], "FORNECEDOR DE MATERIAIS LTDA")
        self.assertEqual(res["fornecedor_cnpj"], "12345678000190")
        self.assertEqual(res["data_emissao"].strftime("%Y-%m-%d"), "2026-05-10")
        self.assertEqual(res["data_entrada"].strftime("%Y-%m-%d"), "2026-05-12")
        self.assertEqual(res["valor_total"], decimal.Decimal("1250.75"))

    def test_normalizar_item_nota(self):
        raw_item = {
            "prod_det": {
                "nSequencia": 3,
                "nIdProd": 88877,
                "cCodProdFor": "PF-444",
                "cDescricao": "TECIDO DE ALGODAO CRU",
                "cNCM": "52081100",
                "cCFOP": "1102",
                "cUnidade": "RL",
                "nQtde": 5.5,
                "nValUnit": 120.0,
                "nValTotal": 660.0
            }
        }
        res = normalizar_item_nota(raw_item)
        self.assertEqual(res["sequencia"], 3)
        self.assertEqual(res["codigo_produto_omie"], "88877")
        self.assertEqual(res["codigo_produto_fornecedor"], "PF-444")
        self.assertEqual(res["descricao"], "TECIDO DE ALGODAO CRU")
        self.assertEqual(res["ncm"], "52081100")
        self.assertEqual(res["cfop"], "1102")
        self.assertEqual(res["unidade_nota"], "RL")
        self.assertEqual(res["quantidade_nota"], decimal.Decimal("5.5"))
        self.assertEqual(res["valor_unitario"], decimal.Decimal("120.0000"))
        self.assertEqual(res["valor_total"], decimal.Decimal("660.00"))


class OmieAprovacaoTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.categoria = Categoria.objects.create(nome="Categoria A", cor="#ffffff")
        self.fornecedor = Fornecedor.objects.create(nome="Fornecedor Teste", cnpj="99888777000100")
        self.produto = Produto.objects.create(
            tipo_produto="TECIDO",
            unidade_medida="M",
            descricao="Tecido de Algodão Teste",
            categoria=self.categoria,
            fornecedor=self.fornecedor,
            quantidade_base=10.0, # estoque inicial
            preco_custo=5.0,
            preco_venda=10.0
        )
        self.nota = OmieNotaEntrada.objects.create(
            numero_nf="1234",
            serie="1",
            fornecedor_nome="Fornecedor Teste",
            fornecedor_cnpj="99888777000100",
            fornecedor=self.fornecedor,
            valor_total=200.0,
            status="PENDENTE"
        )
        self.item1 = OmieNotaEntradaItem.objects.create(
            nota=self.nota,
            sequencia=1,
            descricao="Tecido Item 1",
            unidade_nota="RL",
            quantidade_nota=2.00,
            valor_unitario=50.00,
            valor_total=100.00,
            produto=self.produto,
            quantidade_convertida=200.00, # 2 rolos = 200 metros
            unidade_convertida="M"
        )
        self.item2 = OmieNotaEntradaItem.objects.create(
            nota=self.nota,
            sequencia=2,
            descricao="Item Ignorado",
            unidade_nota="UN",
            quantidade_nota=1.00,
            valor_unitario=100.00,
            valor_total=100.00,
            status="IGNORADO"
        )

    def test_pode_aprovar(self):
        # Nota inicial está pronta para aprovação (todos os itens não ignorados têm produto)
        self.assertTrue(self.nota.pode_aprovar())

        # Se removermos o produto do item1 (não ignorado) não deve poder aprovar
        self.item1.produto = None
        self.item1.save()
        self.assertFalse(self.nota.pode_aprovar())

    def test_aprovar_nota_entrada_sucesso(self):
        # Quantidade inicial é 10.0
        res = aprovar_nota_entrada(self.nota, self.user)
        self.assertTrue(res["sucesso"])
        self.assertEqual(res["itens_importados"], 1)

        # Verifica alteração no banco
        self.nota.refresh_from_db()
        self.assertEqual(self.nota.status, "IMPORTADA")
        self.assertEqual(self.nota.aprovado_por, self.user)

        self.item1.refresh_from_db()
        self.assertEqual(self.item1.status, "IMPORTADO")
        self.assertIsNotNone(self.item1.movimentacao)

        # Verifica estoque do produto
        self.produto.refresh_from_db()
        # Inicial 10.0 + Importação 200.0 (quantidade_convertida) = 210.0
        self.assertEqual(self.produto.quantidade_base, decimal.Decimal("210.00"))

        # Verifica se movimentação foi criada corretamente
        mov = self.item1.movimentacao
        self.assertEqual(mov.produto, self.produto)
        self.assertEqual(mov.quantidade, decimal.Decimal("200.00"))
        self.assertEqual(mov.tipo, "ENTRADA")

    def test_aprovar_nota_ja_importada_bloqueio(self):
        # Aprova a nota pela primeira vez
        aprovar_nota_entrada(self.nota, self.user)

        # Tenta aprovar novamente, deve falhar
        with self.assertRaises(Exception):
            aprovar_nota_entrada(self.nota, self.user)


@override_settings(DEBUG=True)
class OmieSincronizacaoTestCase(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nome="Categoria B", cor="#aaaaaa")
        self.fornecedor = Fornecedor.objects.create(nome="Fornecedor Parcial", cnpj="11.222.333/0001-44")
        self.produto = Produto.objects.create(
            tipo_produto="TINTA",
            unidade_medida="L",
            descricao="Tinta Sublimática Azul",
            categoria=self.categoria,
            fornecedor=self.fornecedor,
            quantidade_base=5.00
        )
        self.config = OmieConfig.objects.create(
            nome="Config Sync",
            ativo=True,
            app_key="key_test"
        )
        self.config.set_app_secret("secret_test")
        self.config.save()

        # Cria mapping prévio
        self.mapping = OmieProdutoMapping.objects.create(
            fornecedor=self.fornecedor,
            fornecedor_cnpj="11222333000144",
            codigo_produto_omie="PR-999",
            produto=self.produto,
            unidade_nota="VD",
            fator_conversao_para_base=2.000000, # 1 Vidro = 2 Litros
            ativo=True
        )

    @patch("omie.services.listar_notas_entrada")
    def test_sincronizar_notas_entrada_mapeia_automaticamente(self, mock_listar):
        mock_response = {
            "nTotalPaginas": 1,
            "notas": [
                {
                    "cabec": {
                        "nCodNotaEnt": 1122,
                        "cChaveNFe": "35191100000000000000550010000009999000009999",
                        "cNumeroNotaEnt": "9999",
                        "cSerieNota": "1",
                        "dPrevisao": "01/07/2026",
                        "nCodCli": 456
                    },
                    "totais": {
                        "nTotalNotaEnt": 100.0,
                        "nMercadorias": 100.0
                    },
                    "fornecedor": {
                        "cNome": "Fornecedor Parcial",
                        "cCNPJ": "11.222.333/0001-44"
                    },
                    "produtos": [
                        {
                            "nSequencia": 1,
                            "nCodProd": "PR-999",
                            "cCodProdFor": "FR-999",
                            "cDescricao": "Tinta Azul Omie",
                            "cNCM": "32151100",
                            "cCFOP": "1102",
                            "cUnidade": "VD",
                            "nQtde": 3.0,
                            "nValUnit": 33.3333,
                            "nCodIt": 789,
                            "codigo_local_estoque": "EST-1"
                        }
                    ]
                }
            ]
        }
        mock_listar.return_value = mock_response

        # Executa sync
        resumo = sincronizar_notas_entrada(self.config)
        self.assertEqual(resumo["criadas"], 1)
        self.assertEqual(resumo["erros"], 0)

        # Verifica nota salva
        nota = OmieNotaEntrada.objects.get(numero_nf="9999")
        self.assertEqual(nota.fornecedor, self.fornecedor)

        # Verifica item salvo com mapping aplicado
        item = nota.itens.get(sequencia=1)
        self.assertEqual(item.produto, self.produto)
        # 3.0 Vidros * 2.0 (fator) = 6.0 Litros
        self.assertEqual(item.quantidade_convertida, decimal.Decimal("6.00"))
        self.assertEqual(item.unidade_convertida, "L")
        self.assertEqual(item.status, "VINCULADO")

    @patch("omie.services.omie_call")
    def test_sincronizar_notas_entrada_enriquece_dados_via_api(self, mock_omie_call):
        # Configura as chamadas simuladas de API da Omie para retornar códigos
        # na listagem e resolver os detalhes via ConsultarCliente / ConsultarProduto.
        def side_effect(config, endpoint, call, param):
            if call == "ListarNotaEnt":
                return {
                    "nTotalPaginas": 1,
                    "notas": [
                        {
                            "cabec": {
                                "nCodNotaEnt": 5566,
                                "cChaveNFe": "35191100000000000000550010000008888000008888",
                                "cNumeroNotaEnt": "8888",
                                "cSerieNota": "1",
                                "dPrevisao": "05/07/2026",
                                "nCodCli": 456
                            },
                            "totais": {
                                "nTotalNotaEnt": 500.0,
                                "nMercadorias": 500.0
                            },
                            "produtos": [
                                {
                                    "nSequencia": 1,
                                    "nCodProd": 9999,
                                    "cCodProdFor": "FR-888",
                                    "nQtde": 5.0,
                                    "nValUnit": 100.0,
                                    "nCodIt": 789,
                                    "codigo_local_estoque": "EST-1"
                                }
                            ]
                        }
                    ]
                }
            elif call == "ConsultarCliente":
                self.assertEqual(param.get("codigo_cliente_omie"), 456)
                return {
                    "codigo_cliente_omie": 456,
                    "razao_social": "Fornecedor Parcial",
                    "nome_fantasia": "Fantasia Parcial",
                    "cnpj_cpf": "11.222.333/0001-44",
                    "email": "forn@parcial.com"
                }
            elif call == "ConsultarProduto":
                self.assertEqual(param.get("codigo_produto"), 9999)
                return {
                    "codigo_produto": 9999,
                    "descricao": "Tinta Sublimática Azul",
                    "unidade": "L",
                    "ncm": "32151100"
                }
            return {}

        mock_omie_call.side_effect = side_effect

        # Executa sync
        resumo = sincronizar_notas_entrada(self.config)
        self.assertEqual(resumo["criadas"], 1)
        self.assertEqual(resumo["erros"], 0)

        # Verifica nota salva enriquecida
        nota = OmieNotaEntrada.objects.get(numero_nf="8888")
        self.assertEqual(nota.fornecedor_nome, "Fornecedor Parcial")
        self.assertEqual(nota.fornecedor_cnpj, "11222333000144")
        self.assertEqual(nota.fornecedor, self.fornecedor)

        # Verifica item salvo enriquecido
        item = nota.itens.get(sequencia=1)
        self.assertEqual(item.descricao, "Tinta Sublimática Azul")
        self.assertEqual(item.unidade_nota, "L")
        self.assertEqual(item.ncm, "32151100")


class OmieViewsTestCase(TestCase):
    def setUp(self):
        from django.urls import reverse
        self.reverse = reverse
        self.user = User.objects.create_user(username="operador", password="password123")
        self.client.login(username="operador", password="password123")

        self.categoria = Categoria.objects.create(nome="Tecidos", cor="#ff0000")
        self.fornecedor = Fornecedor.objects.create(nome="Distribuidora de Tecidos", cnpj="22333444000199")
        self.produto = Produto.objects.create(
            tipo_produto="TECIDO",
            unidade_medida="M",
            descricao="Linho Cru",
            categoria=self.categoria,
            fornecedor=self.fornecedor,
            quantidade_base=0,
            preco_custo=10.0,
            preco_venda=20.0
        )
        self.nota = OmieNotaEntrada.objects.create(
            numero_nf="8877",
            serie="1",
            fornecedor_nome="Distribuidora de Tecidos",
            fornecedor_cnpj="22333444000199",
            fornecedor=self.fornecedor,
            valor_total=150.00,
            status="PENDENTE"
        )
        self.item = OmieNotaEntradaItem.objects.create(
            nota=self.nota,
            sequencia=1,
            descricao="Linho Tecido",
            unidade_nota="RL",
            quantidade_nota=1.5,
            valor_unitario=100.0,
            valor_total=150.0,
            status="PENDENTE"
        )

    def test_lista_notas_omie_view(self):
        url = self.reverse('lista_notas_omie')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "8877")
        self.assertContains(resp, "Distribuidora de Tecidos")

    def test_detalhe_nota_omie_view(self):
        url = self.reverse('detalhe_nota_omie', args=[self.nota.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Linho Tecido")

    def test_salvar_vinculos_omie_view(self):
        url = self.reverse('salvar_vinculos_omie', args=[self.nota.id])
        data = {
            f'produto_{self.item.id}': self.produto.id,
            f'fator_{self.item.id}': '10.0',
            f'status_{self.item.id}': 'VINCULADO'
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302) # Redirects
        self.item.refresh_from_db()
        self.assertEqual(self.item.produto, self.produto)
        self.assertEqual(self.item.quantidade_convertida, decimal.Decimal('15.00'))
        self.assertEqual(self.item.status, 'VINCULADO')

    def test_aprovar_nota_omie_view(self):
        # Primeiro vincula
        self.item.produto = self.produto
        self.item.quantidade_convertida = decimal.Decimal('15.00')
        self.item.unidade_convertida = 'M'
        self.item.status = 'VINCULADO'
        self.item.save()

        url = self.reverse('aprovar_nota_omie', args=[self.nota.id])
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        
        self.nota.refresh_from_db()
        self.assertEqual(self.nota.status, 'IMPORTADA')
        
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_base, decimal.Decimal('15.00'))

    def test_ignorar_e_reativar_nota_omie_view(self):
        url_ignorar = self.reverse('ignorar_nota_omie', args=[self.nota.id])
        resp = self.client.post(url_ignorar)
        self.assertEqual(resp.status_code, 302)
        self.nota.refresh_from_db()
        self.assertEqual(self.nota.status, 'IGNORADA')

        url_reativar = self.reverse('reativar_nota_omie', args=[self.nota.id])
        resp = self.client.post(url_reativar)
        self.assertEqual(resp.status_code, 302)
        self.nota.refresh_from_db()
        self.assertEqual(self.nota.status, 'PENDENTE')

