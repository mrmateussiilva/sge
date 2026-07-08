import os
import base64
import warnings
from cryptography.fernet import Fernet

# Chave padrão estática usada APENAS para fins de desenvolvimento local.
# NUNCA use essa chave em produção.
_DEV_KEY = b't-W8eH1e6k1Z9q7yXp2L5M3nQ4zT6vW7yJp0zK9wS1U='


def _is_debug() -> bool:
    """Retorna True se Django está em modo DEBUG."""
    try:
        from django.conf import settings
        return bool(getattr(settings, 'DEBUG', False))
    except Exception:
        return False


def get_fernet_instance() -> Fernet:
    """
    Retorna uma instância Fernet configurada com a chave de ambiente OMIE_ENCRYPTION_KEY.

    Comportamento:
    - DEBUG=True  → permite chave de desenvolvimento, mas emite RuntimeWarning.
    - DEBUG=False → levanta ImproperlyConfigured se a chave não estiver configurada.
    """
    key_env = os.getenv('OMIE_ENCRYPTION_KEY')

    if key_env:
        try:
            key_bytes = key_env.encode('utf-8')
            return Fernet(key_bytes)
        except Exception as e:
            # Chave inválida no ambiente — nunca silencia, mesmo em DEBUG
            if _is_debug():
                warnings.warn(
                    f"OMIE_ENCRYPTION_KEY configurada é inválida: {e}. "
                    "Utilizando chave de desenvolvimento local.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                return Fernet(_DEV_KEY)
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured(
                f"OMIE_ENCRYPTION_KEY configurada é inválida: {e}"
            )

    # Sem chave no ambiente
    if _is_debug():
        warnings.warn(
            "Variável de ambiente OMIE_ENCRYPTION_KEY não configurada. "
            "Utilizando chave de desenvolvimento padrão (NÃO RECOMENDADO PARA PRODUÇÃO).",
            RuntimeWarning,
            stacklevel=2,
        )
        return Fernet(_DEV_KEY)

    # Produção sem chave → erro explícito
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        "OMIE_ENCRYPTION_KEY não está configurada. "
        "Defina essa variável de ambiente antes de rodar em produção. "
        "Gere uma chave com: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    )


def encrypt_secret(secret_text: str) -> str:
    if not secret_text:
        return ""
    f = get_fernet_instance()
    encrypted_bytes = f.encrypt(secret_text.encode('utf-8'))
    return encrypted_bytes.decode('utf-8')


def decrypt_secret(encrypted_text: str) -> str:
    if not encrypted_text:
        return ""
    f = get_fernet_instance()
    try:
        decrypted_bytes = f.decrypt(encrypted_text.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        warnings.warn(f"Falha ao descriptografar segredo do Omie: {e}", RuntimeWarning, stacklevel=2)
        # Fallback de sobrevivência (dados legados em base64 ou texto puro)
        try:
            return base64.b64decode(encrypted_text.encode('utf-8')).decode('utf-8')
        except Exception:
            return encrypted_text
