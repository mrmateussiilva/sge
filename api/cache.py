import time
from cachetools import TTLCache
from typing import Any, Optional

# In-memory caches for different entities
# Products: 60 seconds
# Categories/Tags: 300 seconds (5 minutes)
# Dashboard: 30 seconds
# Transactions: 30 seconds

_caches = {
    "produtos": TTLCache(maxsize=1, ttl=60),
    "categorias": TTLCache(maxsize=1, ttl=300),
    "tags": TTLCache(maxsize=1, ttl=300),
    "dashboard": TTLCache(maxsize=1, ttl=30),
    "movimentacoes": TTLCache(maxsize=1, ttl=30),
}

def get_cached(key: str) -> Optional[Any]:
    cache = _caches.get(key)
    if cache is not None and "data" in cache:
        return cache["data"]
    return None

def set_cached(key: str, data: Any):
    cache = _caches.get(key)
    if cache is not None:
        cache["data"] = data

def invalidate(key: str):
    cache = _caches.get(key)
    if cache is not None:
        try:
            del cache["data"]
        except KeyError:
            pass

def invalidate_all():
    for key in _caches:
        invalidate(key)
