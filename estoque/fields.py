from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models


class EncryptedCharField(models.CharField):
    """Armazena texto sensível criptografado com uma chave Fernet do ambiente."""

    token_prefix = 'gAAAAA'

    def _fernet(self):
        key = getattr(settings, 'OMIE_ENCRYPTION_KEY', '')
        if not key:
            raise ImproperlyConfigured('OMIE_ENCRYPTION_KEY não configurada.')
        try:
            return Fernet(key.encode())
        except (TypeError, ValueError) as exc:
            raise ImproperlyConfigured('OMIE_ENCRYPTION_KEY inválida.') from exc

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if not value:
            return value
        if value.startswith(self.token_prefix):
            try:
                self._fernet().decrypt(value.encode())
            except InvalidToken as exc:
                raise ImproperlyConfigured('Não foi possível descriptografar o segredo Omie.') from exc
            return value
        return self._fernet().encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if not value or not value.startswith(self.token_prefix):
            # Permite a leitura de registros legados até a migration de conversão.
            return value
        try:
            return self._fernet().decrypt(value.encode()).decode()
        except InvalidToken as exc:
            raise ImproperlyConfigured('Não foi possível descriptografar o segredo Omie.') from exc
