"""Shared portrait loading and caching for all views.

Provides a single load_portrait() function with a bounded LRU cache
so every view (combat, dialogue, encounter, class select, victory)
uses the same loader and shares cached surfaces.
"""

import logging
import os

import pygame

from config import resolve_data_path

logger = logging.getLogger(__name__)

_CACHE_MAX = 64
_cache: dict[str, pygame.Surface | None] = {}


def load_portrait(
    path: str | None,
    size: tuple[int, int] = (128, 128),
) -> pygame.Surface | None:
    """Load, scale, and cache a portrait image. Returns None on failure."""
    if not path:
        return None

    resolved = resolve_data_path(path)
    key = f"{resolved}:{size[0]}x{size[1]}"
    if key in _cache:
        return _cache[key]

    if resolved and os.path.exists(resolved):
        try:
            img = pygame.image.load(resolved).convert_alpha()
            img = pygame.transform.scale(img, size)
            if len(_cache) >= _CACHE_MAX:
                _cache.pop(next(iter(_cache)))
            _cache[key] = img
            return img
        except Exception:
            logger.debug("Failed to load portrait: %s", resolved, exc_info=True)

    _cache[key] = None
    return None
