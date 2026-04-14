"""SFXController — manages pygame.mixer.Sound playback during gameplay.

Reads the SFX manifest written by world_gen (manifest["sfx"]) and provides
named sound effect playback.  If a sound file is missing or SFX was never
generated, all operations are silent no-ops.

Uses pygame.mixer.Sound + channels (NOT pygame.mixer.music) so SFX can
layer on top of the background music stream without interrupting it.

A dedicated channel is reserved for looping ambient sounds so that
ambience can play continuously while one-shot SFX fire on other channels.
"""

import logging
import os

import pygame

logger = logging.getLogger(__name__)

_AMBIENT_CHANNEL_ID = 7  # reserve channel 7 for ambient loops


class SFXController:
    """Thin wrapper around pygame.mixer.Sound with silent fallback.

    Usage:
        sfx = SFXController(registry.manifest.get("sfx", {}))
        sfx.play("weapon_heavy_swing")
        sfx.play_ambience("village")
        sfx.stop_ambience()
    """

    def __init__(self, sfx_manifest: dict[str, str] | None = None):
        self._sounds: dict[str, pygame.mixer.Sound] = {}
        self._manifest: dict[str, str] = sfx_manifest or {}
        self._current_ambience: str | None = None

        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception as e:
                logger.warning("pygame.mixer init failed: %s — SFX disabled.", e)
                return

        pygame.mixer.set_num_channels(max(pygame.mixer.get_num_channels(), 16))

        try:
            from config import MASTER_VOLUME, SFX_VOLUME
            self._volume = (SFX_VOLUME / 100.0) * (MASTER_VOLUME / 100.0)
        except Exception:
            self._volume = 0.7

        self._ambient_channel = pygame.mixer.Channel(_AMBIENT_CHANNEL_ID)
        self._ambient_volume = self._volume * 0.4

    def _get_sound(self, sfx_name: str) -> pygame.mixer.Sound | None:
        """Load and cache a Sound object. Returns None if file missing."""
        if sfx_name in self._sounds:
            return self._sounds[sfx_name]

        path = self._manifest.get(sfx_name)
        if not path or not os.path.exists(path):
            fallback = os.path.join("data", "sfx", f"{sfx_name}.mp3")
            if os.path.exists(fallback):
                path = fallback
                self._manifest[sfx_name] = path
            else:
                logger.debug("SFX key '%s' not in manifest or on disk.", sfx_name)
                return None

        try:
            sound = pygame.mixer.Sound(path)
            sound.set_volume(self._volume)
            self._sounds[sfx_name] = sound
            return sound
        except Exception as e:
            logger.warning("Failed to load SFX '%s': %s", sfx_name, e)
            return None

    # ------------------------------------------------------------------
    # One-shot SFX
    # ------------------------------------------------------------------

    def play(self, sfx_name: str) -> None:
        """Play a one-shot sound effect. Silent if file missing."""
        sound = self._get_sound(sfx_name)
        if sound:
            sound.play()

    def play_weapon_swing(self, weapon_type: str) -> None:
        """Play the swing sound for a weapon type (light/heavy/simple)."""
        if weapon_type == "wild":
            weapon_type = "light"
        self.play(f"weapon_{weapon_type}_swing")

    def play_weapon_hit(self, weapon_type: str) -> None:
        """Play the hit sound for a weapon type."""
        if weapon_type == "wild":
            weapon_type = "light"
        self.play(f"weapon_{weapon_type}_hit")

    def play_spell(self, spell_type: str, phase: str = "cast") -> None:
        """Play a spell SFX.

        spell_type: damage_single, damage_multi, heal, buff_stat, buff_sustain
        phase: 'cast' or 'impact'
        """
        if spell_type in ("buff_stat", "buff_sustain"):
            key = "spell_buff_cast" if spell_type == "buff_stat" else "spell_reveal_cast"
        elif phase == "impact" and spell_type.startswith("damage"):
            key = f"spell_{spell_type}_impact"
        else:
            key = f"spell_{spell_type}_{phase}"
        self.play(key)

    # ------------------------------------------------------------------
    # Looping ambient sounds
    # ------------------------------------------------------------------

    _AMBIENCE_FALLBACKS = {"dungeon": "cave", "forest": "village"}

    def play_ambience(self, env_type: str) -> None:
        """Start looping ambient sound for an environment type."""
        key = f"ambience_{env_type}"
        if key == self._current_ambience:
            return

        sound = self._get_sound(key)
        if not sound:
            fb = self._AMBIENCE_FALLBACKS.get(env_type)
            if fb:
                sound = self._get_sound(f"ambience_{fb}")
        if not sound:
            self.stop_ambience()
            return

        sound.set_volume(self._ambient_volume)
        self._ambient_channel.play(sound, loops=-1)
        self._current_ambience = key
        logger.debug("Ambience: playing '%s'", key)

    def stop_ambience(self) -> None:
        """Stop the ambient sound loop."""
        try:
            self._ambient_channel.stop()
        except Exception:
            pass
        self._current_ambience = None

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def has_sfx(self, sfx_name: str) -> bool:
        """Return True if a SFX file exists on disk."""
        path = self._manifest.get(sfx_name)
        return bool(path and os.path.exists(path))

    @property
    def current_ambience(self) -> str | None:
        return self._current_ambience
