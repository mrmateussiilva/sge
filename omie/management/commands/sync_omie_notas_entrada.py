import datetime
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from omie.models import OmieConfig
from omie.services import sincronizar_notas_entrada, OmieApiError


class Command(BaseCommand):
    help = "Sincroniza notas fiscais de entrada do ERP Omie para o banco de dados local."

    def add_arguments(self, parser):
        parser.add_argument(
            '--data-inicial',
            type=str,
            help='Data inicial para sincronização no formato YYYY-MM-DD (opcional).'
        )
        parser.add_argument(
            '--data-final',
            type=str,
            help='Data final para sincronização no formato YYYY-MM-DD (opcional).'
        )
        parser.add_argument(
            '--dias',
            type=int,
            default=7,
            help='Quantidade de dias para trás para sincronizar caso as datas não sejam informadas (padrão: 7).'
        )
        parser.add_argument(
            '--config-id',
            type=int,
            help='ID da configuração Omie específica que deseja utilizar (opcional).'
        )
        parser.add_argument(
            '--pagina',
            type=int,
            default=1,
            help='Página inicial para sincronização (padrão: 1).'
        )
        parser.add_argument(
            '--registros-por-pagina',
            type=int,
            default=50,
            help='Quantidade de registros por página (padrão: 50).'
        )

    def handle(self, *args, **options):
        config_id = options.get('config_id')
        data_ini_str = options.get('data_inicial')
        data_fim_str = options.get('data_final')
        dias = options.get('dias')

        # Determina a configuração a ser utilizada
        if config_id:
            try:
                config = OmieConfig.objects.get(pk=config_id)
            except OmieConfig.DoesNotExist:
                raise CommandError(f"Configuração Omie com ID {config_id} não encontrada.")
        else:
            config = OmieConfig.objects.filter(ativo=True).first()
            if not config:
                raise CommandError("Nenhuma configuração ativa do Omie encontrada no sistema.")

        # Tratamento de datas e dias
        data_inicial = None
        data_final = None

        if data_ini_str:
            try:
                data_inicial = datetime.datetime.strptime(data_ini_str, "%Y-%m-%d").date()
            except ValueError:
                raise CommandError("O parâmetro --data-inicial deve estar no formato YYYY-MM-DD.")

        if data_fim_str:
            try:
                data_final = datetime.datetime.strptime(data_fim_str, "%Y-%m-%d").date()
            except ValueError:
                raise CommandError("O parâmetro --data-final deve estar no formato YYYY-MM-DD.")

        # Fallback para o parâmetro --dias caso nenhuma data seja fornecida
        if not data_inicial and not data_final and dias:
            hoje = datetime.date.today()
            data_inicial = hoje - datetime.timedelta(days=dias)
            data_final = hoje

        # Obtém o usuário do sistema (opcionalmente o primeiro superusuário para registro de logs)
        User = get_user_model()
        usuario_sistema = User.objects.filter(is_superuser=True).first()

        self.stdout.write(
            f"Iniciando sincronização com Omie usando a configuração '{config.nome}'...\n"
            f"Período: {data_inicial or 'Todas'} até {data_final or 'Todas'}"
        )

        # Executa a sincronização — qualquer OmieApiError da primeira página
        # vira CommandError imediatamente (sem fingir sucesso).
        try:
            resumo = sincronizar_notas_entrada(
                config=config,
                data_inicial=data_inicial,
                data_final=data_final,
                usuario=usuario_sistema,
            )
        except OmieApiError as e:
            raise CommandError(f"Falha na comunicação com a API Omie: {e}")
        except Exception as e:
            raise CommandError(f"Erro inesperado durante a sincronização: {e}")

        # --- Exibição do resumo ---
        criadas = resumo.get('criadas', 0)
        atualizadas = resumo.get('atualizadas', 0)
        erros = resumo.get('erros', 0)
        erros_detalhes = resumo.get('erros_detalhes', [])

        self.stdout.write(f"- Notas Criadas: {criadas}")
        self.stdout.write(f"- Notas Atualizadas: {atualizadas}")
        self.stdout.write(f"- Erros de Nota: {erros}")

        if erros_detalhes:
            self.stdout.write(self.style.WARNING("Detalhes dos erros:"))
            for erro in erros_detalhes:
                self.stderr.write(self.style.ERROR(f"  * {erro}"))

        # Se houver qualquer erro, encerra com CommandError (exit code != 0)
        if erros > 0:
            raise CommandError(
                f"Sincronização concluída com {erros} erro(s). "
                "Verifique os detalhes acima."
            )

        self.stdout.write(self.style.SUCCESS("Sincronização concluída com sucesso!"))
