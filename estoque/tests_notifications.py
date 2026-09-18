from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.db import transaction
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from notifications.client import NotificationClient
from notifications.events import STOCK_LOW, STOCK_ZERO, determine_stock_event
from notifications.admin import NotificationEventConfigAdmin
from notifications.models import NotificationEventConfig

from .models import Movimentacao, Produto
from .views.movimentacoes import excluir_movimentacao


class NotificationClientTests(SimpleTestCase):
    @override_settings(
        NOTIFICATION_WEBHOOK_URL='https://n8n.example.test/webhook',
        NOTIFICATION_TOKEN='token-de-teste',
    )
    @patch('notifications.client.urllib.request.urlopen')
    def test_erro_http_registra_status_e_nao_quebra(self, urlopen):
        urlopen.side_effect = __import__('urllib.error').error.HTTPError(
            url='https://n8n.example.test/webhook',
            code=401,
            msg='Unauthorized',
            hdrs=None,
            fp=BytesIO(b'token invalido'),
        )

        with self.assertLogs('notifications.client', level='WARNING') as logs:
            result = NotificationClient.send(
                event='stock.low',
                source='sge',
                audience='purchasing',
                data={'product_id': 0},
            )

        self.assertFalse(result)
        self.assertIn('status=401', logs.output[0])
        self.assertIn('body=token invalido', logs.output[0])


class StockNotificationEventTests(TestCase):
    def test_cruzamento_do_minimo_retorna_stock_low(self):
        event = determine_stock_event(
            previous_stock=Decimal('60'),
            current_stock=Decimal('48'),
            minimum_stock=Decimal('50'),
        )

        self.assertEqual(event, STOCK_LOW)

    def test_continuar_abaixo_do_minimo_nao_retorna_evento(self):
        event = determine_stock_event(
            previous_stock=Decimal('48'),
            current_stock=Decimal('45'),
            minimum_stock=Decimal('50'),
        )

        self.assertIsNone(event)

    def test_zerar_estoque_retorna_stock_zero(self):
        event = determine_stock_event(
            previous_stock=Decimal('10'),
            current_stock=Decimal('0'),
            minimum_stock=Decimal('20'),
        )

        self.assertEqual(event, STOCK_ZERO)

    def test_saldo_negativo_conceitual_retorna_stock_zero(self):
        event = determine_stock_event(
            previous_stock=Decimal('10'),
            current_stock=Decimal('-5'),
            minimum_stock=Decimal('20'),
        )

        self.assertEqual(event, STOCK_ZERO)

    def test_estoque_ja_zerado_nao_retorna_evento(self):
        event = determine_stock_event(
            previous_stock=Decimal('0'),
            current_stock=Decimal('0'),
            minimum_stock=Decimal('20'),
        )

        self.assertIsNone(event)

    def test_stock_zero_tem_precedencia_sobre_stock_low(self):
        event = determine_stock_event(
            previous_stock=Decimal('10'),
            current_stock=Decimal('0'),
            minimum_stock=Decimal('20'),
        )

        self.assertEqual(event, STOCK_ZERO)
        self.assertNotEqual(event, STOCK_LOW)


class MovimentacaoStockNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='notify-user', password='password123')
        self.admin_user = User.objects.create_superuser(
            username='notify-admin',
            email='notify-admin@example.com',
            password='password123',
        )

    def criar_produto(self, *, quantidade='60.00', minimo='50.00', tipo='OUTRO', unidade='UN'):
        return Produto.objects.create(
            descricao='Produto Notificacao',
            tipo_produto=tipo,
            unidade_medida=unidade,
            quantidade_base=Decimal(quantidade),
            estoque_minimo=Decimal(minimo) if minimo is not None else None,
        )

    @patch('notifications.events.NotificationClient.send', return_value=True)
    def test_stock_low_ativo_envia_com_audience_configurado(self, send):
        produto = self.criar_produto(quantidade='60.00', minimo='50.00', tipo='PAPEL')
        NotificationEventConfig.objects.filter(event='stock.low').update(audience='compras')

        with self.captureOnCommitCallbacks(execute=True):
            Movimentacao.objects.create(
                produto=produto,
                usuario=self.user,
                tipo='SAIDA',
                quantidade=Decimal('12.00'),
            )

        send.assert_called_once_with(
            event='stock.low',
            source='sge',
            audience='compras',
            data={
                'product_id': produto.pk,
                'product': 'Produto Notificacao',
                'current_stock': 48.0,
                'unit': 'M',
                'minimum_stock': 50.0,
            },
        )

    @patch('notifications.events.NotificationClient.send', return_value=True)
    def test_stock_low_desativado_nao_envia(self, send):
        produto = self.criar_produto(quantidade='60.00', minimo='50.00')
        NotificationEventConfig.objects.filter(event='stock.low').update(enabled=False)

        with self.captureOnCommitCallbacks(execute=True):
            Movimentacao.objects.create(
                produto=produto,
                usuario=self.user,
                tipo='SAIDA',
                quantidade=Decimal('12.00'),
            )

        send.assert_not_called()

    @patch('notifications.events.NotificationClient.send', return_value=True)
    def test_continuar_abaixo_do_minimo_nao_registra_novamente(self, send):
        produto = self.criar_produto(quantidade='48.00', minimo='50.00')

        with patch('notifications.events.get_event_config') as get_config:
            with self.captureOnCommitCallbacks(execute=True):
                Movimentacao.objects.create(
                    produto=produto,
                    usuario=self.user,
                    tipo='SAIDA',
                    quantidade=Decimal('3.00'),
                )

        send.assert_not_called()
        get_config.assert_not_called()

    @patch('notifications.events.NotificationClient.send', return_value=True)
    def test_configuracao_inexistente_nao_envia_e_nao_quebra(self, send):
        produto = self.criar_produto(quantidade='60.00', minimo='50.00')
        NotificationEventConfig.objects.filter(event='stock.low').delete()

        with self.assertLogs('notifications.events', level='WARNING'):
            with self.captureOnCommitCallbacks(execute=True):
                Movimentacao.objects.create(
                    produto=produto,
                    usuario=self.user,
                    tipo='SAIDA',
                    quantidade=Decimal('12.00'),
                )

        produto.refresh_from_db()
        self.assertEqual(produto.quantidade_base, Decimal('48.00'))
        send.assert_not_called()

    @patch('notifications.events.NotificationClient.send', return_value=True)
    def test_zerar_registra_stock_zero(self, send):
        produto = self.criar_produto(quantidade='10.00', minimo='20.00')

        with self.captureOnCommitCallbacks(execute=True):
            Movimentacao.objects.create(
                produto=produto,
                usuario=self.user,
                tipo='SAIDA',
                quantidade=Decimal('10.00'),
            )

        send.assert_called_once_with(
            event='stock.zero',
            source='sge',
            audience='purchasing',
            data={
                'product_id': produto.pk,
                'product': 'Produto Notificacao',
                'current_stock': 0.0,
                'unit': 'UN',
            },
        )

    @override_settings(
        NOTIFICATION_WEBHOOK_URL='https://n8n.example.test/webhook',
        NOTIFICATION_TOKEN='token-de-teste',
    )
    @patch('notifications.client.urllib.request.urlopen')
    def test_falha_do_webhook_nao_quebra_movimentacao(self, urlopen):
        urlopen.side_effect = TimeoutError('timeout')
        produto = self.criar_produto(quantidade='60.00', minimo='50.00')

        with self.assertLogs('notifications.client', level='WARNING'):
            with self.captureOnCommitCallbacks(execute=True):
                Movimentacao.objects.create(
                    produto=produto,
                    usuario=self.user,
                    tipo='SAIDA',
                    quantidade=Decimal('12.00'),
                )

        produto.refresh_from_db()
        self.assertEqual(produto.quantidade_base, Decimal('48.00'))

    @patch('notifications.events.NotificationClient.send', return_value=True)
    def test_rollback_nao_executa_envio(self, send):
        produto = self.criar_produto(quantidade='60.00', minimo='50.00')

        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    Movimentacao.objects.create(
                        produto=produto,
                        usuario=self.user,
                        tipo='SAIDA',
                        quantidade=Decimal('12.00'),
                    )
                    raise RuntimeError('rollback intencional')

        send.assert_not_called()
        produto.refresh_from_db()
        self.assertEqual(produto.quantidade_base, Decimal('60.00'))

    @patch('notifications.events.NotificationClient.send', return_value=True)
    def test_exclusao_de_movimentacao_usa_mesma_logica_de_notificacao(self, send):
        produto = self.criar_produto(quantidade='40.00', minimo='50.00')
        mov = Movimentacao.objects.create(
            produto=produto,
            usuario=self.user,
            tipo='ENTRADA',
            quantidade=Decimal('30.00'),
        )
        produto.refresh_from_db()
        self.assertEqual(produto.quantidade_base, Decimal('70.00'))

        request = RequestFactory().post(f'/movimentacao/{mov.pk}/excluir/')
        request.user = self.admin_user

        with self.captureOnCommitCallbacks(execute=True):
            response = excluir_movimentacao(request, mov.pk)

        self.assertEqual(response.status_code, 200)
        send.assert_called_once()
        self.assertEqual(send.call_args.kwargs['event'], 'stock.low')


class NotificationAdminActionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='admin-notify',
            email='admin@example.com',
            password='password123',
        )
        self.request = RequestFactory().post('/admin/notifications/notificationeventconfig/')
        self.request.user = self.user
        self.model_admin = NotificationEventConfigAdmin(NotificationEventConfig, AdminSite())

    @patch('notifications.admin.NotificationClient.send', return_value=True)
    @patch.object(NotificationEventConfigAdmin, 'message_user')
    def test_admin_action_envia_payload_de_teste_stock_low(self, message_user, send):
        config = NotificationEventConfig.objects.get(event='stock.low')
        config.enabled = False
        config.audience = 'compras'
        config.save()

        self.model_admin.send_test_notification(self.request, NotificationEventConfig.objects.filter(pk=config.pk))

        send.assert_called_once_with(
            event='stock.low',
            source='sge',
            audience='compras',
            data={
                'product_id': 0,
                'product': 'Produto de teste',
                'current_stock': 10,
                'minimum_stock': 20,
                'unit': 'un',
            },
        )
        message_user.assert_called()

    @patch('notifications.admin.NotificationClient.send', return_value=True)
    @patch.object(NotificationEventConfigAdmin, 'message_user')
    def test_admin_action_envia_payload_de_teste_stock_zero(self, message_user, send):
        config = NotificationEventConfig.objects.get(event='stock.zero')
        config.audience = 'compras'
        config.save()

        self.model_admin.send_test_notification(self.request, NotificationEventConfig.objects.filter(pk=config.pk))

        send.assert_called_once_with(
            event='stock.zero',
            source='sge',
            audience='compras',
            data={
                'product_id': 0,
                'product': 'Produto de teste',
                'current_stock': 0,
                'unit': 'un',
            },
        )
        message_user.assert_called()
