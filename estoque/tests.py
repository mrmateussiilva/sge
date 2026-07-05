from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
import json

from .models import Produto, Fornecedor, Movimentacao
from .xml_parser import parse_nfe_xml

class NFeImportationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123', is_staff=True)
        self.client.login(username='testuser', password='password123')

        # Sample XML content
        self.xml_content_1 = """<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
            <NFe>
                <infNFe>
                    <ide>
                        <nNF>1001</nNF>
                    </ide>
                    <emit>
                        <xNome>FORNECEDOR ALPHA</xNome>
                        <CNPJ>11111111000111</CNPJ>
                    </emit>
                    <det nItem="1">
                        <prod>
                            <cProd>PAPEL01</cProd>
                            <xProd>PAPEL GLOSS PREMIUM</xProd>
                            <NCM>48119090</NCM>
                            <uCom>RL</uCom>
                            <qCom>5.0000</qCom>
                            <vUnCom>80.0000</vUnCom>
                        </prod>
                    </det>
                </infNFe>
            </NFe>
        </nfeProc>"""

        self.xml_content_2 = """<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">
            <NFe>
                <infNFe>
                    <ide>
                        <nNF>1002</nNF>
                    </ide>
                    <emit>
                        <xNome>FORNECEDOR BETA</xNome>
                        <CNPJ>22222222000122</CNPJ>
                    </emit>
                    <det nItem="1">
                        <prod>
                            <cProd>TINTA01</cProd>
                            <xProd>TINTA CYAN SUBLIMACAO</xProd>
                            <NCM>32151100</NCM>
                            <uCom>L</uCom>
                            <qCom>2.0000</qCom>
                            <vUnCom>120.0000</vUnCom>
                        </prod>
                    </det>
                </infNFe>
            </NFe>
        </nfeProc>"""

    def test_xml_parser(self):
        parsed = parse_nfe_xml(self.xml_content_1)
        self.assertEqual(parsed['numero_nf'], '1001')
        self.assertEqual(parsed['fornecedor']['nome'], 'FORNECEDOR ALPHA')
        self.assertEqual(len(parsed['itens']), 1)
        self.assertEqual(parsed['itens'][0]['descricao'], 'PAPEL GLOSS PREMIUM')
        self.assertEqual(parsed['itens'][0]['quantidade'], 5.0)
        self.assertEqual(parsed['itens'][0]['preco_custo'], 80.0)

    def test_import_multiple_files_view(self):
        file1 = SimpleUploadedFile("nf1001.xml", self.xml_content_1.encode('utf-8'), content_type="text/xml")
        file2 = SimpleUploadedFile("nf1002.xml", self.xml_content_2.encode('utf-8'), content_type="text/xml")

        response = self.client.post(reverse('importar_nfe'), {
            'arquivo': [file1, file2]
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(len(data['dados']['itens']), 2)
        
        # Verify both suppliers are in the list
        self.assertIn('FORNECEDOR ALPHA', data['dados']['fornecedor']['nome'])
        self.assertIn('FORNECEDOR BETA', data['dados']['fornecedor']['nome'])

    def test_confirmar_importacao_nfe(self):
        payload = {
            "fornecedor_nome": "Multiples",
            "numero_nf": "1001, 1002",
            "itens": [
                {
                    "descricao": "PAPEL GLOSS PREMIUM",
                    "quantidade": 5.0,
                    "preco_custo": 80.0,
                    "tipo_produto": "PAPEL",
                    "unidade_medida": "RL",
                    "fornecedor_nome": "FORNECEDOR ALPHA",
                    "numero_nf": "1001",
                    "importar": True,
                    "acao": "criar"
                },
                {
                    "descricao": "TINTA CYAN SUBLIMACAO",
                    "quantidade": 2.0,
                    "preco_custo": 120.0,
                    "tipo_produto": "TINTA",
                    "unidade_medida": "L",
                    "fornecedor_nome": "FORNECEDOR BETA",
                    "numero_nf": "1002",
                    "importar": True,
                    "acao": "criar"
                }
            ]
        }
        
        response = self.client.post(
            reverse('confirmar_importacao_nfe'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertTrue(res_data['ok'])
        self.assertEqual(res_data['criados'], 2)

        # Check database records
        self.assertEqual(Produto.objects.count(), 2)
        p1 = Produto.objects.get(descricao="PAPEL GLOSS PREMIUM")
        self.assertEqual(p1.fornecedor.nome, "FORNECEDOR ALPHA")
        self.assertEqual(p1.quantidade_base, 5.0)

        p2 = Produto.objects.get(descricao="TINTA CYAN SUBLIMACAO")
        self.assertEqual(p2.fornecedor.nome, "FORNECEDOR BETA")
        self.assertEqual(p2.quantidade_base, 2.0)
        
        # Verify supplier beta exists
        self.assertTrue(Fornecedor.objects.filter(nome="FORNECEDOR BETA").exists())
