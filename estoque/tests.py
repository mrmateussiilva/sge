from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
import json

from .models import Produto, Fornecedor, Movimentacao, FechamentoMensal, ItemFechamento


class MovimentacaoTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client.login(username='testuser', password='password123')
        self.produto = Produto.objects.create(
            descricao='PRODUTO TESTE',
            tipo_produto='OUTRO',
            quantidade_base=Decimal('10.00'),
            preco_custo=Decimal('5.50'),
            preco_venda=Decimal('10.00'),
        )

    def test_registrar_entrada_com_quantidade_string(self):
        response = self.client.post(
            reverse('registrar_movimentacao'),
            data=json.dumps({
                'produto_id': self.produto.id,
                'tipo': 'ENTRADA',
                'quantidade': '4.00',
                'observacao': '',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_base, Decimal('14.00'))

    def test_registrar_movimentacao_com_quantidade_invalida_retorna_400(self):
        response = self.client.post(
            reverse('registrar_movimentacao'),
            data=json.dumps({
                'produto_id': self.produto.id,
                'tipo': 'ENTRADA',
                'quantidade': '',
                'observacao': '',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['ok'])
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_base, Decimal('10.00'))


class FechamentoTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.client.login(username='testuser', password='testpassword')
        
        self.fornecedor = Fornecedor.objects.create(nome="FORNECEDOR TESTE")
        self.produto = Produto.objects.create(
            descricao="PRODUTO TESTE",
            tipo_produto="OUTRO",
            quantidade_base=10.0,
            preco_custo=5.50,
            preco_venda=10.00,
            fornecedor=self.fornecedor
        )

    def test_realizar_e_listar_fechamentos(self):
        # 1. Create a closure
        response = self.client.post(
            reverse('realizar_fechamento'),
            data=json.dumps({
                'referencia_mes_ano': '06/2026',
                'observacao': 'Fechamento de teste'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])

        # Check database records
        self.assertEqual(FechamentoMensal.objects.count(), 1)
        fechamento = FechamentoMensal.objects.first()
        self.assertEqual(fechamento.referencia_mes_ano, '06/2026')
        self.assertEqual(fechamento.itens.count(), 1)
        item = fechamento.itens.first()
        self.assertEqual(item.descricao, 'PRODUTO TESTE')
        self.assertEqual(item.quantidade, 10.0)

        # 2. List closures
        response = self.client.get(reverse('lista_fechamentos'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '06/2026')

    def test_exportar_fechamento_xlsx(self):
        # Create closure
        fechamento = FechamentoMensal.objects.create(
            referencia_mes_ano='06/2026',
            usuario=self.user
        )
        ItemFechamento.objects.create(
            fechamento=fechamento,
            produto=self.produto,
            descricao=self.produto.descricao,
            quantidade=self.produto.quantidade_base,
            preco_custo=self.produto.preco_custo,
            preco_venda=self.produto.preco_venda
        )

        response = self.client.get(reverse('exportar_fechamento_xlsx', args=[fechamento.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_exportar_atual_xlsx(self):
        response = self.client.get(reverse('exportar_atual_xlsx'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
