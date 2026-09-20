from decimal import Decimal
from io import StringIO

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection
from django.test import TestCase

from .models import (
    Categoria,
    ConfiguracaoOmie,
    Fornecedor,
    HistoricoPreco,
    Movimentacao,
    Produto,
)
from .services.estoque_metrics import agrupar_quantidade_por_unidade
from .services.estoque_status import (
    BAIXO,
    NORMAL,
    SEM_MINIMO,
    ZERADO,
    classificar_estoque,
    filtro_baixo,
    filtro_zerado,
)
from .services.estoque_valuation import calcular_valor_estoque
from .services.omie_client import OmieClient
from .services.units import decimal_br


def adicionar_perfil(usuario, nome):
    grupo = Group.objects.get(name=nome)
    usuario.groups.add(grupo)


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


class MovimentacaoTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        adicionar_perfil(self.user, 'Operador')
        self.produto = Produto.objects.create(
            descricao='PRODUTO TESTE',
            tipo_produto='OUTRO',
            quantidade_base=Decimal('10.00'),
            preco_custo=Decimal('5.50'),
            preco_venda=Decimal('10.00'),
        )

    def test_tipo_de_movimentacao_invalido_nao_altera_saldo(self):
        with self.assertRaises(ValidationError):
            Movimentacao.objects.create(
                produto=self.produto,
                usuario=self.user,
                tipo='AJUSTE_INVALIDO',
                quantidade=Decimal('2.00'),
            )
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_base, Decimal('10.00'))

    def test_movimentacao_existente_e_immutavel(self):
        movimentacao = Movimentacao.objects.create(
            produto=self.produto,
            usuario=self.user,
            tipo='ENTRADA',
            motivo='COMPRA',
            quantidade=Decimal('2.00'),
        )
        movimentacao.quantidade = Decimal('3.00')
        with self.assertRaises(ValidationError):
            movimentacao.save()
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_base, Decimal('12.00'))

    def test_saida_sem_saldo_lanca_validation_error(self):
        with self.assertRaises(ValidationError):
            Movimentacao.objects.create(
                produto=self.produto,
                usuario=self.user,
                tipo='SAIDA',
                quantidade=Decimal('15.00'),
            )
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_base, Decimal('10.00'))

    def test_exclusao_de_movimentacao_bloqueada_exige_estorno(self):
        mov = Movimentacao.objects.create(
            produto=self.produto,
            usuario=self.user,
            tipo='ENTRADA',
            quantidade=Decimal('5.00'),
        )
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.quantidade_base, Decimal('15.00'))

        with self.assertRaises(ValidationError):
            mov.delete()


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

    def test_comando_audit_usernames_executa(self):
        out = StringIO()
        call_command('audit_usernames', stdout=out)
        self.assertIn('Nenhum username conflitante encontrado', out.getvalue())


class HistoricoPrecoTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='priceuser', password='password123')
        adicionar_perfil(self.user, 'Operador')
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

    def test_salvamento_direto_sem_mudar_preco_nao_cria_historico(self):
        self.produto.descricao = 'PRODUTO PRECO EDITADO'
        self.produto.save()

        self.assertFalse(HistoricoPreco.objects.filter(produto=self.produto).exists())


class ConfiguracaoOmieTestCase(TestCase):
    def test_omie_client_usa_credenciais_do_banco(self):
        ConfiguracaoOmie.objects.create(
            app_key='KEY_DO_BANCO',
            app_secret='SECRET_DO_BANCO',
        )

        client = OmieClient()
        self.assertEqual(client.app_key, 'KEY_DO_BANCO')
        self.assertEqual(client.app_secret, 'SECRET_DO_BANCO')

        with connection.cursor() as cursor:
            cursor.execute('SELECT app_secret FROM estoque_configuracaoomie WHERE id = %s', [ConfiguracaoOmie.objects.first().id])
            segredo_bruto = cursor.fetchone()[0]
        self.assertNotEqual(segredo_bruto, 'SECRET_DO_BANCO')
        self.assertTrue(segredo_bruto.startswith('gAAAAA'))
