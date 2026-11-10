from django.apps import AppConfig
from django.db.backends.signals import connection_created


def ativar_sqlite_pragmas(sender, connection, **kwargs):
    if connection.vendor == 'sqlite':
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA journal_mode = WAL;')
            cursor.execute('PRAGMA synchronous = NORMAL;')
            cursor.execute('PRAGMA busy_timeout = 30000;')


class EstoqueConfig(AppConfig):
    name = 'estoque'

    def ready(self):
        import estoque.signals  # noqa
        connection_created.connect(ativar_sqlite_pragmas)
