from decimal import Decimal
import json

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse

from .models import Categoria, FechamentoMensal, Fornecedor, ItemFechamento, ItemOrdemCompra, Movimentacao, OrdemCompra, Produto


class ApiV1Tests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin_api',
            email='admin@api.com',
            password='adminpassword123',
        )
        self.operador_user = User.objects.create_user(
            username='operador_api',
            email='operador@api.com',
            password='operadorpassword123',
        )
        grupo_operador, _ = Group.objects.get_or_create(name='Operador')
        self.operador_user.groups.add(grupo_operador)

        self.fornecedor = Fornecedor.objects.create(
            nome='Fornecedor Teste API',
            cnpj='12.345.678/0001-90',
            email='contato@fornecedor.com',
        )
        self.categoria = Categoria.objects.create(
            nome='Categoria Papel Teste',
            cor='#3b82f6',
        )
        self.produto_papel = Produto.objects.create(
            tipo_produto='PAPEL',
            descricao='Papel Fotográfico 180g',
            fornecedor=self.fornecedor,
            categoria=self.categoria,
            quantidade_base=Decimal('50.00'),
            estoque_minimo=Decimal('20.00'),
            preco_custo=Decimal('10.00'),
            preco_venda=Decimal('18.00'),
            metros_por_rolo=Decimal('50.00'),
        )
        self.produto_zerado = Produto.objects.create(
            tipo_produto='TECIDO',
            descricao='Tecido Algodão Branco',
            quantidade_base=Decimal('0.00'),
            estoque_minimo=Decimal('10.00'),
        )

    def test_endpoint_sem_autenticacao_redireciona_ou_bloqueia(self):
        url = reverse('api_v1:me')
        response = self.client.get(url)
        # @login_required padrão do django redireciona para login
        self.assertEqual(response.status_code, 302)

    def test_me_endpoint_superuser(self):
        self.client.force_login(self.admin_user)
        url = reverse('api_v1:me')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['user']['username'], 'admin_api')
        self.assertTrue(data['user']['permissoes']['admin'])
        self.assertTrue(data['user']['permissoes']['operacional'])
        self.assertIn('alertas', data)
        self.assertGreaterEqual(data['alertas']['estoque_zerado'], 1)

    def test_dashboard_e_chart_api(self):
        self.client.force_login(self.operador_user)
        url = reverse('api_v1:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['resumo']['total_itens'], 2)
        self.assertEqual(data['resumo']['estoque_zerado'], 1)
        self.assertIn('itens_criticos', data)

        url_chart = reverse('api_v1:dashboard_chart')
        res_chart = self.client.get(url_chart)
        self.assertEqual(res_chart.status_code, 200)
        chart_data = res_chart.json()
        self.assertTrue(chart_data['ok'])
        self.assertEqual(len(chart_data['mensal']['meses']), 12)
        self.assertIn('por_tipo', chart_data)

    def test_produtos_lista_e_detalhe_api(self):
        self.client.force_login(self.operador_user)
        # Listagem
        url = reverse('api_v1:produtos_lista')
        response = self.client.get(url, {'aba': 'PAPEL'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['ok'])
        self.assertEqual(len(data['itens']), 1)
        self.assertEqual(data['itens'][0]['descricao'], 'Papel Fotográfico 180g')
        self.assertIn('resumo', data)
        self.assertIn('paginacao', data)
        self.assertIn('abas', data)

        # Filtro de estoque zerado
        res_zerados = self.client.get(url, {'aba': 'TODOS', 'filtro': 'ZERADO'})
        self.assertEqual(res_zerados.status_code, 200)
        zerados_data = res_zerados.json()
        self.assertEqual(len(zerados_data['itens']), 1)
        self.assertEqual(zerados_data['itens'][0]['descricao'], 'Tecido Algodão Branco')

        # Detalhe do produto
        url_detalhe = reverse('api_v1:produtos_detalhe', kwargs={'id': self.produto_papel.id})
        res_detalhe = self.client.get(url_detalhe)
        self.assertEqual(res_detalhe.status_code, 200)
        detalhe_data = res_detalhe.json()
        self.assertTrue(detalhe_data['ok'])
        self.assertEqual(detalhe_data['produto']['id'], self.produto_papel.id)
        self.assertEqual(detalhe_data['produto']['fornecedor']['nome'], 'Fornecedor Teste API')

        # Opções do produto
        url_opcoes = reverse('api_v1:produtos_opcoes')
        res_opcoes = self.client.get(url_opcoes)
        self.assertEqual(res_opcoes.status_code, 200)
        opcoes_data = res_opcoes.json()
        self.assertTrue(opcoes_data['ok'])
        self.assertIn('tipos_produto', opcoes_data)
        self.assertIn('fornecedores', opcoes_data)

    def test_movimentacoes_api(self):
        self.client.force_login(self.operador_user)
        # Registrar movimentação via POST JSON
        url_registrar = reverse('api_v1:movimentacoes_registrar')
        payload = {
            'produto_id': self.produto_papel.id,
            'tipo': 'ENTRADA',
            'quantidade': '15.00',
            'motivo': 'COMPRA',
            'observacao': 'Entrada teste via API',
        }
        res_post = self.client.post(
            url_registrar,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(res_post.status_code, 200)
        post_data = res_post.json()
        self.assertTrue(post_data['ok'])

        self.produto_papel.refresh_from_db()
        self.assertEqual(self.produto_papel.quantidade_base, Decimal('65.00'))

        # Listar movimentações
        url_lista = reverse('api_v1:movimentacoes_lista')
        res_lista = self.client.get(url_lista)
        self.assertEqual(res_lista.status_code, 200)
        lista_data = res_lista.json()
        self.assertTrue(lista_data['ok'])
        self.assertGreaterEqual(len(lista_data['itens']), 1)
        self.assertEqual(lista_data['itens'][0]['tipo'], 'ENTRADA')

    def test_detalhe_produto_com_movimentacao_formata_unidade_base(self):
        self.client.force_login(self.operador_user)
        Movimentacao.objects.create(produto=self.produto_papel, tipo='ENTRADA', quantidade='2.50')
        response = self.client.get(reverse('api_v1:produtos_detalhe', args=[self.produto_papel.pk]))
        self.assertEqual(response.status_code, 200)
        mov = response.json()['movimentacoes'][0]
        self.assertEqual(mov['quantidade'], 2.5)
        self.assertEqual(mov['quantidade_formatada'], '2,50 m')

    def test_detalhe_fornece_campos_para_edicao_sem_perda(self):
        self.client.force_login(self.operador_user)
        produto = Produto.objects.create(
            descricao='Material em kg', tipo_produto='OUTRO', unidade_medida='KG',
            fornecedor=self.fornecedor, categoria=self.categoria,
            preco_custo=Decimal('0'), preco_venda=None, estoque_minimo=Decimal('0'),
        )
        detalhe = self.client.get(reverse('api_v1:produtos_detalhe', args=[produto.pk])).json()['produto']
        self.assertEqual(detalhe['unidade_medida'], 'KG')
        self.assertEqual(detalhe['fornecedor']['id'], self.fornecedor.pk)
        self.assertEqual(detalhe['categoria']['id'], self.categoria.pk)
        self.assertEqual(detalhe['preco_custo'], 0)
        self.assertIsNone(detalhe['preco_venda'])
        self.assertEqual(detalhe['estoque_minimo'], 0)

    def test_paginacao_normaliza_tamanho_em_todas_as_listagens(self):
        self.client.force_login(self.admin_user)
        for endpoint in ('produtos_lista', 'movimentacoes_lista', 'ordens_lista', 'logs'):
            for informado, esperado in [('0', 1), ('-1', 1), ('abc', 25), ('', 25), ('101', 100), ('10', 10)]:
                with self.subTest(endpoint=endpoint, page_size=informado):
                    response = self.client.get(reverse(f'api_v1:{endpoint}'), {'page_size': informado})
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()['paginacao']['itens_por_pagina'], esperado)

    def test_busca_e_paginacao_alcancam_produtos_apos_os_primeiros_cem(self):
        self.client.force_login(self.operador_user)
        Produto.objects.bulk_create([
            Produto(descricao=f'Insumo {index:03d}') for index in range(101)
        ])
        url = reverse('api_v1:produtos_lista')
        primeira = self.client.get(url, {'aba': 'TODOS', 'page_size': 100}).json()
        self.assertEqual(len(primeira['itens']), 100)
        self.assertNotIn('Insumo 100', [p['descricao'] for p in primeira['itens']])
        segunda = self.client.get(url, {'aba': 'TODOS', 'page_size': 100, 'page': 2}).json()
        self.assertIn('Insumo 100', [p['descricao'] for p in segunda['itens']])
        busca = self.client.get(url, {'aba': 'TODOS', 'busca': 'Insumo 100'}).json()
        self.assertEqual([p['descricao'] for p in busca['itens']], ['Insumo 100'])

    def test_ordens_api(self):
        self.client.force_login(self.operador_user)
        # Criar ordem de compra via POST JSON
        url_criar = reverse('api_v1:ordens_criar')
        payload = {
            'fornecedor_id': self.fornecedor.id,
            'observacao': 'Ordem de teste API',
            'itens': [
                {
                    'produto_id': self.produto_papel.id,
                    'quantidade': '10',
                    'preco_unitario': '9.50',
                }
            ],
        }
        res_criar = self.client.post(
            url_criar,
            data=json.dumps(payload),
            content_type='application/json',
        )
        self.assertEqual(res_criar.status_code, 200)
        ordem_id = res_criar.json()['id']

        # Listar ordens
        url_lista = reverse('api_v1:ordens_lista')
        res_lista = self.client.get(url_lista)
        self.assertEqual(res_lista.status_code, 200)
        ordens_data = res_lista.json()
        self.assertTrue(ordens_data['ok'])
        self.assertEqual(len(ordens_data['itens']), 1)
        self.assertEqual(ordens_data['itens'][0]['id'], ordem_id)
        self.assertEqual(ordens_data['itens'][0]['status'], 'PENDENTE')

        # Detalhe da ordem
        url_detalhe = reverse('api_v1:ordens_detalhe', kwargs={'id': ordem_id})
        res_detalhe = self.client.get(url_detalhe)
        self.assertEqual(res_detalhe.status_code, 200)
        detalhe_data = res_detalhe.json()
        self.assertTrue(detalhe_data['ok'])
        self.assertEqual(detalhe_data['ordem']['id'], ordem_id)
        self.assertEqual(len(detalhe_data['itens']), 1)
        self.assertEqual(detalhe_data['itens'][0]['preco_unitario'], 9.5)

        # Aprovar ordem
        url_aprovar = reverse('api_v1:ordens_aprovar', kwargs={'id': ordem_id})
        res_aprovar = self.client.post(url_aprovar)
        self.assertEqual(res_aprovar.status_code, 200)
        self.assertTrue(res_aprovar.json()['ok'])

    def test_categorias_e_fornecedores_api(self):
        self.client.force_login(self.operador_user)
        # Categorias
        url_cat = reverse('api_v1:categorias_lista')
        res_cat = self.client.get(url_cat)
        self.assertEqual(res_cat.status_code, 200)
        cat_data = res_cat.json()
        self.assertTrue(cat_data['ok'])
        self.assertEqual(len(cat_data['itens']), 1)
        self.assertEqual(cat_data['itens'][0]['nome'], 'Categoria Papel Teste')

        # Fornecedores
        url_forn = reverse('api_v1:fornecedores_lista')
        res_forn = self.client.get(url_forn)
        self.assertEqual(res_forn.status_code, 200)
        forn_data = res_forn.json()
        self.assertTrue(forn_data['ok'])
        self.assertEqual(len(forn_data['itens']), 1)
        self.assertEqual(forn_data['itens'][0]['nome'], 'Fornecedor Teste API')

    def test_fechamentos_api(self):
        self.client.force_login(self.operador_user)
        # Revisar fechamento
        url_revisar = reverse('api_v1:fechamentos_revisar')
        res_revisar = self.client.get(url_revisar, {'data_inicio': '2026-01-01', 'data_fim': '2026-01-31'})
        self.assertEqual(res_revisar.status_code, 200)
        rev_data = res_revisar.json()
        self.assertTrue(rev_data['ok'])
        self.assertIn('resumo', rev_data)

        # Criar fechamento
        from datetime import date
        fechamento = FechamentoMensal.objects.create(
            data_inicio=date(2026, 1, 1),
            data_fim=date(2026, 1, 31),
            usuario=self.operador_user,
            observacao='Teste de fechamento',
        )
        ItemFechamento.objects.create(
            fechamento=fechamento,
            descricao='Item Congelado Teste',
            quantidade=Decimal('10.00'),
            preco_custo=Decimal('5.00'),
        )

        # Listar fechamentos
        url_lista = reverse('api_v1:fechamentos_lista')
        res_lista = self.client.get(url_lista)
        self.assertEqual(res_lista.status_code, 200)
        lista_data = res_lista.json()
        self.assertTrue(lista_data['ok'])
        self.assertEqual(len(lista_data['itens']), 1)

        # Detalhe fechamento
        url_detalhe = reverse('api_v1:fechamentos_detalhe', kwargs={'id': fechamento.id})
        res_detalhe = self.client.get(url_detalhe)
        self.assertEqual(res_detalhe.status_code, 200)
        detalhe_data = res_detalhe.json()
        self.assertTrue(detalhe_data['ok'])
        self.assertEqual(len(detalhe_data['itens']), 1)
        self.assertEqual(detalhe_data['itens'][0]['descricao'], 'Item Congelado Teste')

    def test_relatorio_e_logs_api(self):
        self.client.force_login(self.operador_user)
        url_relatorio = reverse('api_v1:relatorio_mensal')
        res_rel = self.client.get(url_relatorio)
        self.assertEqual(res_rel.status_code, 200)
        self.assertTrue(res_rel.json()['ok'])

        url_logs = reverse('api_v1:logs')
        res_logs = self.client.get(url_logs)
        self.assertEqual(res_logs.status_code, 200)
        self.assertTrue(res_logs.json()['ok'])

    def test_usuarios_api_permissao(self):
        url = reverse('api_v1:usuarios')
        # Operador não tem permissão de superuser
        self.client.force_login(self.operador_user)
        res_operador = self.client.get(url)
        self.assertEqual(res_operador.status_code, 403)

        # Superuser tem acesso
        self.client.force_login(self.admin_user)
        res_admin = self.client.get(url)
        self.assertEqual(res_admin.status_code, 200)
        data = res_admin.json()
        self.assertTrue(data['ok'])
        self.assertGreaterEqual(len(data['usuarios']), 2)
        self.assertIn('perfis', data)

    def test_criar_e_alterar_usuario_api(self):
        self.client.force_login(self.admin_user)
        url_criar = reverse('api_v1:usuarios_criar')

        # Criar novo usuário
        res_criar = self.client.post(
            url_criar,
            json.dumps({
                'username': 'novo_usuario_teste',
                'password': 'novopassword123',
                'email': 'novo@teste.com',
            }),
            content_type='application/json',
        )
        self.assertEqual(res_criar.status_code, 200)
        self.assertTrue(res_criar.json()['ok'])
        user_id = res_criar.json()['id']

        # Alterar perfil do usuário
        url_perfil = reverse('api_v1:usuarios_perfil', args=[user_id])
        res_perfil = self.client.post(
            url_perfil,
            json.dumps({'is_active': False}),
            content_type='application/json',
        )
        self.assertEqual(res_perfil.status_code, 200)
        self.assertTrue(res_perfil.json()['ok'])

        # Verificar se usuário foi desativado
        user_atualizado = User.objects.get(id=user_id)
        self.assertFalse(user_atualizado.is_active)

    def test_spa_view_integration(self):
        from django.conf import settings
        dist_dir = settings.BASE_DIR / 'frontend' / 'dist'
        index_file = dist_dir / 'index.html'
        created_temp = False
        if not index_file.exists():
            dist_dir.mkdir(parents=True, exist_ok=True)
            index_file.write_text('<!DOCTYPE html><html><body><div id="root"></div></body></html>', encoding='utf-8')
            created_temp = True

        try:
            for rota in ('/', '/app/', '/produtos/'):
                with self.subTest(rota=rota, autenticado=False):
                    res_anon = self.client.get(rota)
                    self.assertEqual(res_anon.status_code, 302)
                    self.assertIn('/accounts/login/', res_anon['Location'])

            self.client.force_login(self.admin_user)
            for rota in ('/', '/app/', '/produtos/'):
                with self.subTest(rota=rota, autenticado=True):
                    res_auth = self.client.get(rota)
                    self.assertEqual(res_auth.status_code, 200)
                    self.assertIn('text/html', res_auth['Content-Type'])
                    self.assertContains(res_auth, '<div id="root"></div>', html=True)
        finally:
            if created_temp:
                index_file.unlink(missing_ok=True)
