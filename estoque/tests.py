from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
import json

from .models import FechamentoMensal, Fornecedor, HistoricoPreco, ItemFechamento, Movimentacao, Produto


class LoginTemplateTestCase(TestCase):
    def test_login_renderiza_com_next(self):
        response = self.client.get(f"{reverse('login')}?next=/produtos/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Acessar o SGE')
        self.assertContains(response, 'name="next" value="/produtos/"')
        self.assertContains(response, 'autocomplete="username"')
        self.assertContains(response, 'autocomplete="current-password"')

    def test_login_invalido_exibe_mensagem_generica_e_preserva_usuario(self):
        response = self.client.post(
            reverse('login'),
            data={
                'username': 'operador',
                'password': 'senha-incorreta',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Usuário ou senha inválidos.')
        self.assertContains(response, 'value="operador"')


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

    def test_registrar_saida_sem_saldo_retorna_400_com_erro(self):
        response = self.client.post(
            reverse('registrar_movimentacao'),
            data=json.dumps({
                'produto_id': self.produto.id,
                'tipo': 'SAIDA',
                'quantidade': '15.00',
                'observacao': '',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['ok'])
        self.assertIn('Quantidade indisponível', data['erro'])
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_base, Decimal('10.00'))

    def test_paginas_operacionais_renderizam(self):
        for name in ('dashboard', 'lista_produtos', 'registrar_movimentacao', 'cadastrar_produto'):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)

    def test_cadastrar_produto_com_campos_minimos(self):
        response = self.client.post(
            reverse('cadastrar_produto'),
            data=json.dumps({
                'tipo_produto': 'OUTRO',
                'unidade_medida': 'UN',
                'descricao': 'PRODUTO MINIMO',
                'quantidade_base': 0,
                'preco_custo': 0,
                'preco_venda': 0,
                'estoque_minimo': 0,
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        self.assertTrue(Produto.objects.filter(descricao='PRODUTO MINIMO').exists())


class HistoricoPrecoTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='priceuser', password='password123')
        self.client.login(username='priceuser', password='password123')
        self.produto = Produto.objects.create(
            descricao='PRODUTO PRECO',
            tipo_produto='OUTRO',
            quantidade_base=Decimal('10.00'),
            preco_custo=Decimal('5.50'),
            preco_venda=Decimal('10.00'),
        )

    def test_salvamento_direto_cria_historico_quando_preco_muda(self):
        self.produto.preco_custo = Decimal('6.25')
        self.produto.save()

        historico = HistoricoPreco.objects.get(produto=self.produto)
        self.assertEqual(historico.preco_custo_antigo, Decimal('5.50'))
        self.assertEqual(historico.preco_custo_novo, Decimal('6.25'))
        self.assertIsNone(historico.preco_venda_antigo)
        self.assertIsNone(historico.preco_venda_novo)
        self.assertIsNone(historico.usuario)

    def test_salvamento_direto_sem_mudar_preco_nao_cria_historico(self):
        self.produto.descricao = 'PRODUTO PRECO EDITADO'
        self.produto.save()

        self.assertFalse(HistoricoPreco.objects.filter(produto=self.produto).exists())

    def test_editar_produto_cria_um_historico_com_usuario(self):
        response = self.client.post(
            reverse('editar_produto', args=[self.produto.id]),
            data=json.dumps({
                'tipo_produto': 'OUTRO',
                'unidade_medida': 'UN',
                'descricao': 'PRODUTO PRECO',
                'quantidade_base': '10.00',
                'preco_custo': '6.00',
                'preco_venda': '12.00',
                'estoque_minimo': '0.00',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        historicos = HistoricoPreco.objects.filter(produto=self.produto)
        self.assertEqual(historicos.count(), 1)
        historico = historicos.get()
        self.assertEqual(historico.preco_custo_antigo, Decimal('5.50'))
        self.assertEqual(historico.preco_custo_novo, Decimal('6.00'))
        self.assertEqual(historico.preco_venda_antigo, Decimal('10.00'))
        self.assertEqual(historico.preco_venda_novo, Decimal('12.00'))
        self.assertEqual(historico.usuario, self.user)


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
