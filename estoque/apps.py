from django.apps import AppConfig


class EstoqueConfig(AppConfig):
    name = 'estoque'

    def ready(self):
        import estoque.signals  # noqa
