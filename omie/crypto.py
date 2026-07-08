import os
import base64
import warnings
from cryptography.fernet import Fernet

# Chave padrão estática usada apenas para fins de desenvolvimento local
DEV_KEY = b't-W8eH1e6k1Z9q7yXp2L5M3nQ4zT6vW7yJp0zK9wS1U='

def get_fernet_instance():
    key_env = os.getenv('OMIE_ENCRYPTION_KEY')
    if key_env:
        try:
            # Garante que a chave do ambiente seja convertida para bytes adequadamente
            key_bytes = key_env.encode('utf-8')
            return Fernet(key_bytes)
        except Exception as e:
            warnings.warn(
                f"Erro ao inicializar Fernet com a chave OMIE_ENCRYPTION_KEY do ambiente: {e}. "
                "Utilizando chave de desenvolvimento local.",
                RuntimeWarning
            )
    else:
        warnings.warn(
            "Variável de ambiente OMIE_ENCRYPTION_KEY não configurada. "
            "Utilizando chave de desenvolvimento padrão (NÃO RECOMENDADO PARA PRODUÇÃO).",
            RuntimeWarning
        )
    return Fernet(DEV_KEY)

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
        warnings.warn(f"Falha ao descriptografar segredo do Omie: {e}", RuntimeWarning)
        # Fallback de sobrevivência (se já estivesse em texto puro ou codificação simples antes)
        try:
            return base64.b64decode(encrypted_text.encode('utf-8')).decode('utf-8')
        except Exception:
            return encrypted_text
