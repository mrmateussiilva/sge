from datetime import datetime, timedelta
import logging
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand
from django.utils import timezone

from estoque.models import ConfiguracaoOmie, ImportacaoNFe
from estoque.services.omie_client import OmieClient, OmieConfigError, OmieAPIError
from notifications.events import NFE_RECEIVED, notify_nfe_received
from notifications.models import NotificationLog

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Executa a sincronização em segundo plano das NF-e de fornecedores emitidas na Omie.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=30,
            help='Número de dias retroativos a consultar (padrão: 30).',
        )
        parser.add_argument(
            '--forcar',
            action='store_true',
            help='Executa mesmo se auto_sync_ativo estiver desmarcado.',
        )

    def handle(self, *args, **options):
        dias = options['dias']
        forcar = options['forcar']

        cfg = ConfiguracaoOmie.objects.first()
        if not forcar and cfg and not cfg.auto_sync_ativo:
            self.stdout.write(self.style.WARNING('Sincronização automática está desativada na configuração.'))
            return

        hoje = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
        dt_inicio = (hoje - timedelta(days=dias)).strftime('%d/%m/%Y')
        dt_fim = hoje.strftime('%d/%m/%Y')

        self.stdout.write(f'Iniciando sincronização Omie para o período: {dt_inicio} até {dt_fim}...')

        try:
            client = OmieClient()
            resumo = client.listar_recebimentos_fornecedores_periodo(
                dt_inicio=dt_inicio,
                dt_fim=dt_fim,
                apenas_fornecedores=True,
                incluir_detalhes=True,
            )
        except OmieConfigError as exc:
            msg = f'Credenciais Omie não configuradas: {exc}'
            self.stderr.write(self.style.ERROR(msg))
            return
        except OmieAPIError as exc:
            msg = f'Erro retornado pela API Omie [{exc.codigo}]: {exc.descricao}'
            self.stderr.write(self.style.ERROR(msg))
            return
        except Exception as exc:
            msg = f'Falha inesperada ao consultar Omie: {exc}'
            logger.exception(msg)
            self.stderr.write(self.style.ERROR(msg))
            return

        todas_notas = resumo.get('notas', [])
        ids_receb = [n['id_receb'] for n in todas_notas if n.get('id_receb')]
        importadas_ids = set(
            ImportacaoNFe.objects.filter(n_cod_nota_ent__in=ids_receb).values_list('n_cod_nota_ent', flat=True)
        )

        novas_notas = [n for n in todas_notas if n.get('id_receb') not in importadas_ids]

        # Notificar sobre notas novas
        for n in novas_notas:
            num = n.get('numero_nfe') or ''
            forn = n.get('fornecedor_nome') or ''
            v_tot = n.get('valor_total') or 0
            chv = n.get('chave_nfe') or ''
            ja_notificada = NotificationLog.objects.filter(
                event=NFE_RECEIVED,
                payload__data__numero_nfe=str(num),
                payload__data__fornecedor=str(forn),
            ).exists()
            if not ja_notificada:
                try:
                    notify_nfe_received(
                        numero_nfe=str(num),
                        fornecedor_nome=str(forn),
                        valor_total=v_tot,
                        chave_nfe=str(chv),
                    )
                except Exception as notif_err:
                    logger.warning('Falha ao notificar nova NF-e %s: %s', num, notif_err)

        agora = timezone.now()
        status_msg = f'{len(todas_notas)} NF-e consultadas ({len(novas_notas)} nova(s) pendente(s))'

        if cfg:
            cfg.ultimo_sync_em = agora
            cfg.ultimo_sync_status = status_msg
            cfg.save(update_fields=['ultimo_sync_em', 'ultimo_sync_status'])

        self.stdout.write(
            self.style.SUCCESS(
                f'Sincronização concluída com sucesso! '
                f'Total consultadas: {len(todas_notas)} | Novas pendentes: {len(novas_notas)}'
            )
        )
