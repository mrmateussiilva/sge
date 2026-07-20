from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import Group, User
import json
from io import StringIO

from .models import Categoria, FechamentoMensal, Fornecedor, HistoricoPreco, ItemFechamento, LogAcao, Movimentacao, Produto
from .services.estoque_metrics import agrupar_quantidade_por_unidade
from .services.estoque_status import BAIXO, NORMAL, SEM_MINIMO, ZERADO, classificar_estoque, filtro_baixo, filtro_zerado
from .services.estoque_valuation import calcular_valor_estoque
from .services.units import decimal_br


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
        self.assertIn('Saldo insuficiente', data['erro'])
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_base, Decimal('10.00'))

    def test_paginas_operacionais_renderizam(self):
        for name in (
            'dashboard',
            'lista_produtos',
            'registrar_movimentacao',
            'cadastrar_produto',
            'relatorio_mensal',
            'lista_fornecedores',
            'lista_categorias',
            'lista_fechamentos',
            'log_acoes',
            'lista_usuarios',
        ):
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


class DominioEstoqueTestCase(TestCase):
    def criar_produto(self, **kwargs):
        defaults = {
            'descricao': 'PRODUTO',
            'tipo_produto': 'OUTRO',
            'unidade_medida': 'UN',
            'quantidade_base': Decimal('0.00'),
        }
        defaults.update(kwargs)
        return Produto.objects.create(**defaults)

    def test_unidade_base_e_formatacao_por_tipo(self):
        papel = self.criar_produto(descricao='PAPEL', tipo_produto='PAPEL', unidade_medida='UN', quantidade_base=Decimal('3000.00'))
        tecido = self.criar_produto(descricao='TECIDO', tipo_produto='TECIDO', unidade_medida='UN', quantidade_base=Decimal('1250.50'))
        tinta = self.criar_produto(descricao='TINTA', tipo_produto='TINTA', quantidade_base=Decimal('45.30'))
        unitario = self.criar_produto(descricao='UNITARIO', tipo_produto='OUTRO', unidade_medida='UN', quantidade_base=Decimal('18.00'))

        self.assertEqual(papel.unidade_simbolo, 'm')
        self.assertEqual(tecido.unidade_simbolo, 'm')
        self.assertEqual(tinta.unidade_simbolo, 'L')
        self.assertEqual(unitario.unidade_simbolo, 'un')
        self.assertEqual(papel.quantidade_formatada, '3.000,00 m')
        self.assertEqual(tinta.quantidade_formatada, '45,30 L')
        self.assertEqual(unitario.quantidade_formatada, '18,00 un')
        self.assertEqual(decimal_br(Decimal('1234.5')), '1.234,50')

    def test_estimativa_de_rolos_nao_altera_saldo_real(self):
        produto = self.criar_produto(
            tipo_produto='PAPEL',
            quantidade_base=Decimal('1000.00'),
            metros_por_rolo=Decimal('250.00'),
        )

        self.assertEqual(produto.quantidade_rolos_estimada, Decimal('4.00'))
        self.assertEqual(produto.quantidade_base, Decimal('1000.00'))

    def test_agregacao_de_movimentacoes_e_por_unidade(self):
        user = User.objects.create_user(username='movuser', password='password123')
        papel = self.criar_produto(descricao='PAPEL', tipo_produto='PAPEL')
        tinta = self.criar_produto(descricao='TINTA', tipo_produto='TINTA')
        outro = self.criar_produto(descricao='OUTRO', tipo_produto='OUTRO', unidade_medida='UN')
        movs = [
            Movimentacao.objects.create(produto=papel, usuario=user, tipo='ENTRADA', quantidade=Decimal('3000.00')),
            Movimentacao.objects.create(produto=tinta, usuario=user, tipo='ENTRADA', quantidade=Decimal('45.00')),
            Movimentacao.objects.create(produto=outro, usuario=user, tipo='ENTRADA', quantidade=Decimal('10.00')),
        ]

        totais = agrupar_quantidade_por_unidade(movs)
        self.assertEqual(totais['M'], Decimal('3000.00'))
        self.assertEqual(totais['L'], Decimal('45.00'))
        self.assertEqual(totais['UN'], Decimal('10.00'))

    def test_valuation_diferencia_zero_explicito_de_custo_ausente(self):
        vazio = calcular_valor_estoque([])
        self.assertTrue(vazio.calculo_completo)
        self.assertEqual(vazio.valor_conhecido, Decimal('0.00'))

        com_custo = self.criar_produto(quantidade_base=Decimal('10.00'), preco_custo=Decimal('5.00'))
        custo_zero = self.criar_produto(quantidade_base=Decimal('3.00'), preco_custo=Decimal('0.00'))
        sem_custo = self.criar_produto(quantidade_base=Decimal('7.00'), preco_custo=None)

        valuation = calcular_valor_estoque([com_custo, custo_zero, sem_custo])
        self.assertEqual(valuation.valor_conhecido, Decimal('50.00'))
        self.assertEqual(valuation.total_produtos_com_saldo, 3)
        self.assertEqual(valuation.produtos_com_custo, 2)
        self.assertEqual(valuation.produtos_sem_custo, 1)
        self.assertFalse(valuation.calculo_completo)

    def test_classificacao_de_estoque_e_querysets_disjuntos(self):
        casos = [
            (Decimal('0'), Decimal('0'), ZERADO),
            (Decimal('0'), Decimal('10'), ZERADO),
            (Decimal('5'), Decimal('10'), BAIXO),
            (Decimal('10'), Decimal('10'), BAIXO),
            (Decimal('11'), Decimal('10'), NORMAL),
            (Decimal('5'), Decimal('0'), SEM_MINIMO),
            (Decimal('5'), None, SEM_MINIMO),
        ]
        for idx, (saldo, minimo, esperado) in enumerate(casos):
            produto = self.criar_produto(descricao=f'P{idx}', quantidade_base=saldo, estoque_minimo=minimo)
            self.assertEqual(classificar_estoque(produto).codigo, esperado)

        baixos = set(Produto.objects.filter(filtro_baixo()).values_list('id', flat=True))
        zerados = set(Produto.objects.filter(filtro_zerado()).values_list('id', flat=True))
        self.assertTrue(baixos.isdisjoint(zerados))

    def test_lista_produtos_explica_contadores_filtrados(self):
        user = User.objects.create_user(username='listuser', password='password123')
        self.client.login(username='listuser', password='password123')
        categoria = Categoria.objects.create(nome='Tecidos')
        fornecedor = Fornecedor.objects.create(nome='Fornecedor A')
        self.criar_produto(descricao='TECIDO AZUL', tipo_produto='TECIDO', categoria=categoria, fornecedor=fornecedor, quantidade_base=Decimal('5'), estoque_minimo=Decimal('10'))
        self.criar_produto(descricao='TINTA CYAN', tipo_produto='TINTA', quantidade_base=Decimal('0'), estoque_minimo=Decimal('10'))

        response = self.client.get(reverse('lista_produtos'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Produtos nesta categoria')
        self.assertContains(response, 'Baixo nesta categoria')
        self.assertContains(response, 'Zerado nesta categoria')


class UsernameDominioTestCase(TestCase):
    def test_criacao_normaliza_espacos_e_minusculas(self):
        user = User.objects.create_user(username='  Robson  ', password='password123')
        self.assertEqual(user.username, 'robson')

    def test_bloqueia_username_duplicado_case_insensitive(self):
        User.objects.create_user(username='robson', password='password123')
        with self.assertRaises(ValidationError):
            User.objects.create_user(username='Robson', password='password123')

    def test_edicao_do_proprio_usuario_sem_falso_conflito(self):
        user = User.objects.create_user(username='mateus', password='password123')
        user.is_staff = True
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.username, 'mateus')

    def test_interface_de_usuarios_bloqueia_duplicado(self):
        admin = User.objects.create_superuser(username='admin', password='password123')
        User.objects.create_user(username='robson', password='password123')
        self.client.login(username='admin', password='password123')

        response = self.client.post(
            reverse('lista_usuarios'),
            data=json.dumps({'acao': 'criar', 'username': ' ROBSON ', 'password': 'password123'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()['ok'])

    def test_comando_audit_usernames_executa(self):
        out = StringIO()
        call_command('audit_usernames', stdout=out)
        self.assertIn('Nenhum username conflitante encontrado', out.getvalue())


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


class FluxosOperacionaisTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username='adminop', password='password123')
        self.operador = User.objects.create_user(username='operadorop', password='password123')
        self.fornecedor = Fornecedor.objects.create(nome='Fornecedor Operacional')
        self.produto = Produto.objects.create(
            descricao='TECIDO OPERACIONAL',
            tipo_produto='TECIDO',
            quantidade_base=Decimal('45.30'),
            estoque_minimo=Decimal('20.00'),
            preco_custo=Decimal('10.00'),
            fornecedor=self.fornecedor,
        )

    def test_movimentacao_exibe_saldo_unidade_minimo_fornecedor_e_status(self):
        self.client.login(username='operadorop', password='password123')
        response = self.client.get(reverse('registrar_movimentacao'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '45,30 m')
        self.assertContains(response, '20,00 m')
        self.assertContains(response, 'Fornecedor Operacional')
        self.assertContains(response, 'Quantidade em')

    def test_saida_maior_que_saldo_e_bloqueada_no_backend(self):
        self.client.login(username='operadorop', password='password123')
        response = self.client.post(
            reverse('registrar_movimentacao'),
            data=json.dumps({'produto_id': self.produto.id, 'tipo': 'SAIDA', 'quantidade': '99'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['codigo'], 'SALDO_INSUFICIENTE')
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_base, Decimal('45.30'))

    def test_quantidade_zero_e_negativa_sao_bloqueadas(self):
        self.client.login(username='operadorop', password='password123')
        for quantidade in ('0', '-1'):
            with self.subTest(quantidade=quantidade):
                response = self.client.post(
                    reverse('registrar_movimentacao'),
                    data=json.dumps({'produto_id': self.produto.id, 'tipo': 'ENTRADA', 'quantidade': quantidade}),
                    content_type='application/json',
                )
                self.assertEqual(response.status_code, 400)

    def test_saida_que_deixa_estoque_baixo_registra_status(self):
        self.client.login(username='operadorop', password='password123')
        response = self.client.post(
            reverse('registrar_movimentacao'),
            data=json.dumps({'produto_id': self.produto.id, 'tipo': 'SAIDA', 'quantidade': '30.30'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status_estoque'], 'BAIXO')
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_base, Decimal('15.00'))

    def test_exclusao_via_get_e_bloqueada(self):
        self.client.login(username='adminop', password='password123')
        response = self.client.get(reverse('excluir_produto', args=[self.produto.id]))
        self.assertEqual(response.status_code, 405)

    def test_usuario_sem_permissao_nao_exclui_produto(self):
        self.client.login(username='operadorop', password='password123')
        response = self.client.post(reverse('excluir_produto', args=[self.produto.id]))
        self.assertEqual(response.status_code, 403)

    def test_fornecedor_com_produto_vinculado_nao_exclui(self):
        self.client.login(username='adminop', password='password123')
        response = self.client.post(reverse('excluir_fornecedor', args=[self.fornecedor.id]))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['codigo'], 'VINCULO_IMPEDITIVO')

    def test_exclusao_de_movimentacao_recalcula_saldo_e_log(self):
        self.client.login(username='adminop', password='password123')
        mov = Movimentacao.objects.create(
            produto=self.produto,
            usuario=self.admin,
            tipo='ENTRADA',
            quantidade=Decimal('10.00'),
        )
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_base, Decimal('55.30'))

        response = self.client.post(reverse('excluir_movimentacao', args=[mov.id]))

        self.assertEqual(response.status_code, 200)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_base, Decimal('45.30'))
        self.assertTrue(LogAcao.objects.filter(acao='EXCLUIR', modelo='Movimentacao', objeto_id=mov.id).exists())

    def test_revisao_fechamento_e_valor_parcial(self):
        Produto.objects.create(descricao='SEM CUSTO', tipo_produto='OUTRO', quantidade_base=Decimal('5'), preco_custo=None)
        self.client.login(username='operadorop', password='password123')

        response = self.client.get(reverse('revisar_fechamento'), {'referencia_mes_ano': '07/2026'})

        self.assertEqual(response.status_code, 200)
        resumo = response.json()['resumo']
        self.assertEqual(resumo['referencia_mes_ano'], '07/2026')
        self.assertEqual(resumo['produtos_sem_custo'], 1)
        self.assertFalse(resumo['calculo_completo'])

    def test_fechamento_duplicado_e_bloqueado_e_snapshot_preservado(self):
        self.client.login(username='operadorop', password='password123')
        payload = {'referencia_mes_ano': '07/2026', 'observacao': 'teste'}
        first = self.client.post(reverse('realizar_fechamento'), data=json.dumps(payload), content_type='application/json')
        second = self.client.post(reverse('realizar_fechamento'), data=json.dumps(payload), content_type='application/json')

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(FechamentoMensal.objects.filter(referencia_mes_ano='07/2026').count(), 1)
        self.assertTrue(LogAcao.objects.filter(acao='CRIAR', modelo='FechamentoMensal').exists())

    def test_alteracao_de_perfil_requer_admin(self):
        grupo, _ = Group.objects.get_or_create(name='Operador')
        self.client.login(username='operadorop', password='password123')
        response = self.client.post(
            reverse('lista_usuarios'),
            data=json.dumps({'acao': 'grupo', 'user_id': self.operador.id, 'grupo_id': grupo.id}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_alteracao_de_perfil_registra_log(self):
        grupo, _ = Group.objects.get_or_create(name='Operador')
        self.client.login(username='adminop', password='password123')
        response = self.client.post(
            reverse('lista_usuarios'),
            data=json.dumps({'acao': 'grupo', 'user_id': self.operador.id, 'grupo_id': grupo.id}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.operador.refresh_from_db()
        self.assertTrue(self.operador.is_staff)
        self.assertTrue(LogAcao.objects.filter(acao='EDITAR', modelo='User', objeto_id=self.operador.id).exists())

    def test_nao_remove_propria_administracao(self):
        self.client.login(username='adminop', password='password123')
        response = self.client.post(
            reverse('lista_usuarios'),
            data=json.dumps({'acao': 'grupo', 'user_id': self.admin.id, 'grupo_id': None}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_superuser)
