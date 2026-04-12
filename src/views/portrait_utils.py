"""Shared portrait loading and caching for all views.

Provides a single load_portrait() function with a bounded LRU cache
so every view (combat, dialogue, encounter, class select, victory)
uses the same loader and shares cached surfaces.
"""

import os
import pygame

_CACHE_MAX = 64
_cache: dict[str, pygame.Surface | None] = {}


def load_portrait(
    path: str | None,
    size: tuple[int, int] = (64, 64),
) -> pygame.Surface | None:
    """Load, scale, and cache a portrait image. Returns None on failure."""
    if not path:
        return None

    key = f"{path}:{size[0]}x{size[1]}"
    if key in _cache:
        return _cache[key]

    if os.path.exists(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.scale(img, size)
            if len(_cache) >= _CACHE_MAX:
                _cache.pop(next(iter(_cache)))
            _cache[key] = img
            return img
        except Exception:
            pass

    _cache[key] = None
    return None
