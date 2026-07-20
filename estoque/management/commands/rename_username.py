from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from estoque.models import LogAcao
from estoque.services.usernames import validate_username_available


class Command(BaseCommand):
    help = 'Renomeia explicitamente um usuário por ID validando conflito case-insensitive.'

    def add_arguments(self, parser):
        parser.add_argument('user_id', type=int)
        parser.add_argument('novo_username')

    def handle(self, *args, **options):
        User = get_user_model()
        user_id = options['user_id']
        novo_username = options['novo_username']

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist as exc:
            raise CommandError(f'Usuário id={user_id} não encontrado.') from exc

        try:
            normalized = validate_username_available(novo_username, instance_pk=user.pk)
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        antigo = user.username
        with transaction.atomic():
            user.username = normalized
            user.save(update_fields=['username'])
            LogAcao.objects.create(
                usuario=None,
                acao='EDITAR',
                descricao=f'Renomeou usuário {antigo} para {normalized}',
                modelo='User',
                objeto_id=user.id,
            )
        self.stdout.write(self.style.SUCCESS(f'Usuário {user.id} renomeado de {antigo} para {normalized}.'))
