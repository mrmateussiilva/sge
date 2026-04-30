"""
In-memory cache using only Python stdlib — no external dependencies.
Uses a simple dict with monotonic timestamps for TTL control.
"""
import time
from typing import Any, Optional

# TTLs in seconds per cache key
_TTL: dict[str, int] = {
    "produtos": 60,
    "categorias": 300,
    "tags": 300,
    "dashboard": 30,
    "movimentacoes": 30,
}

# Internal store: key -> (data, expires_at)
_store: dict[str, tuple[Any, float]] = {}


def get_cached(key: str) -> Optional[Any]:
    entry = _store.get(key)
    if entry is None:
        return None
    data, expires_at = entry
    if time.monotonic() < expires_at:
        return data
    # Expired — remove and return None
    del _store[key]
    return None


def set_cached(key: str, data: Any) -> None:
    ttl = _TTL.get(key, 60)
    _store[key] = (data, time.monotonic() + ttl)


def invalidate(key: str) -> None:
    _store.pop(key, None)


def invalidate_all() -> None:
    _store.clear()
