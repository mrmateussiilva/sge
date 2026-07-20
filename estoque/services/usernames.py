from collections import defaultdict

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError


def normalize_username(username):
    return (username or '').strip().lower()


def validate_username_available(username, instance_pk=None):
    normalized = normalize_username(username)
    if not normalized:
        raise ValidationError('Usuário é obrigatório.')
    qs = get_user_model().objects.filter(username__iexact=normalized)
    if instance_pk:
        qs = qs.exclude(pk=instance_pk)
    if qs.exists():
        raise ValidationError('Já existe um usuário com este nome, ignorando maiúsculas e minúsculas.')
    return normalized


def find_case_insensitive_duplicates():
    grupos = defaultdict(list)
    User = get_user_model()
    for user in User.objects.prefetch_related('groups').all().order_by('username', 'id'):
        grupos[normalize_username(user.username)].append(user)
    return {key: users for key, users in grupos.items() if key and len(users) > 1}
