import sys
from django.core.management.base import BaseCommand
from omie.models import OmieConfig
from omie.services import sincronizar_recebimentos_omie

class Command(BaseCommand):
    help = 'Sincroniza Recebimentos NF-e da Omie (Modelo 55)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=365,
            help='Quantidade de dias para buscar (opcional se não usar filtro local)'
        )
        parser.add_argument(
            '--registros-por-pagina',
            type=int,
            default=50,
            help='Quantidade de registros por página da Omie'
        )

    def handle(self, *args, **options):
        dias = options['dias']
        registros_por_pagina = options['registros_por_pagina']

        config = OmieConfig.objects.filter(ativo=True).first()
        if not config:
            self.stdout.write(self.style.ERROR('Nenhuma configuração Omie ativa encontrada.'))
            sys.exit(1)

        self.stdout.write(self.style.SUCCESS(f"Iniciando sincronização de Recebimentos com Omie usando a configuração '{config.nome}'..."))

        def update_progress(msg):
            self.stdout.write(msg)

        resultados = sincronizar_recebimentos_omie(
            dias=dias, 
            registros_por_pagina=registros_por_pagina,
            update_progress=update_progress
        )

        if "status" in resultados and resultados["status"] == "error":
            self.stdout.write(self.style.ERROR(resultados["mensagem"]))
        else:
            self.stdout.write(f"- Recebimentos Criados: {resultados.get('criadas', 0)}")
            self.stdout.write(f"- Recebimentos Atualizados: {resultados.get('atualizadas', 0)}")
            self.stdout.write(f"- Erros de Processamento: {resultados.get('erros', 0)}")
            self.stdout.write(self.style.SUCCESS('Sincronização concluída!'))
