from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from estoque.models import LogAcao, Movimentacao
from estoque.services.usernames import find_case_insensitive_duplicates


class Command(BaseCommand):
    help = 'Lista usernames duplicados por comparação case-insensitive.'

    def handle(self, *args, **options):
        duplicates = find_case_insensitive_duplicates()
        if not duplicates:
            self.stdout.write(self.style.SUCCESS('Nenhum username conflitante encontrado.'))
            return

        User = get_user_model()
        for normalized, users in duplicates.items():
            self.stdout.write(self.style.WARNING(f'Conflito: {normalized}'))
            for user in users:
                groups = ', '.join(user.groups.values_list('name', flat=True)) or '-'
                movs = Movimentacao.objects.filter(usuario=user).count()
                logs = LogAcao.objects.filter(usuario=user).count()
                self.stdout.write(
                    f'  id={user.id} username={user.username} '
                    f'staff={user.is_staff} superuser={user.is_superuser} '
                    f'groups={groups} movimentacoes={movs} logs={logs}'
                )
