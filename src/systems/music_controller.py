"""MusicController — manages pygame.mixer music transitions during gameplay.

Reads the music manifest written by world_gen (manifest["music"]) and
provides named track playback. If a track file is missing or music was
never generated, all operations are silent no-ops.

Track names:
  start_screen      — title / start screen
  maze_{env_type}   — ambient exploration (e.g. maze_village, maze_cave)
  combat            — combat encounters
  puzzle_event      — puzzles and narrative events
  victory           — victory screen
  game_over         — game over screen (plays once, no loop)
"""

import logging
import os

import pygame

logger = logging.getLogger(__name__)


class MusicController:
    """Thin wrapper around pygame.mixer.music with silent fallback.

    Usage:
        music = MusicController(registry.manifest.get("music", {}))
        music.play("start_screen")
        music.play("combat")
        music.stop()
    """

    def __init__(self, music_manifest: dict[str, str] | None = None):
        self._tracks: dict[str, str] = music_manifest or {}
        self._current: str | None = None
        self._maze_track: str | None = None

        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception as e:
                logger.warning("pygame.mixer init failed: %s — music disabled.", e)

        self._fix_wav_mp3_mismatch()

    def _fix_wav_mp3_mismatch(self):
        """Fix .wav paths that are actually MP3 files (or already renamed)."""
        changed = False
        for name, path in list(self._tracks.items()):
            if not path or not path.endswith(".wav"):
                continue
            mp3_path = path[:-4] + ".mp3"

            if not os.path.exists(path) and os.path.exists(mp3_path):
                self._tracks[name] = mp3_path
                changed = True
                continue

            if not os.path.exists(path):
                continue

            try:
                with open(path, "rb") as f:
                    header = f.read(3)
                if header[:3] == b"ID3" or (len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0):
                    os.rename(path, mp3_path)
                    self._tracks[name] = mp3_path
                    changed = True
                    logger.info("Renamed mismatched audio: %s -> %s", path, mp3_path)
            except Exception as e:
                logger.debug("Could not check/rename %s: %s", path, e)

        if changed:
            self._update_manifest_music_paths()

    def _update_manifest_music_paths(self):
        """Persist corrected music paths back to manifest.json."""
        try:
            import json
            manifest_path = os.path.join("data", "manifest.json")
            if not os.path.exists(manifest_path):
                return
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
            manifest["music"] = dict(self._tracks)
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)
            logger.info("Updated manifest.json with corrected music paths.")
        except Exception as e:
            logger.debug("Could not update manifest music paths: %s", e)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def play(self, track_name: str, loops: int = -1) -> None:
        """Play a named track. -1 = loop forever. Silent if file missing."""
        if track_name == self._current:
            return

        path = self._tracks.get(track_name)
        if not path or not os.path.exists(path):
            fallback = os.path.join("data", "music", f"{track_name}.mp3")
            if os.path.exists(fallback):
                path = fallback
                self._tracks[track_name] = path
            else:
                logger.debug("Music track '%s' not found (manifest or fallback).", track_name)
                if self._current is not None:
                    self._stop_quietly()
                return

        try:
            from config import MUSIC_VOLUME
            volume = MUSIC_VOLUME / 100.0
        except Exception:
            volume = 0.6

        if not self._try_load_and_play(path, track_name, volume, loops):
            # First load failed — reinit mixer and retry (handles MP3/OGG
            # files that the default WAV-only mixer config can't decode).
            try:
                pygame.mixer.quit()
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
                if not self._try_load_and_play(path, track_name, volume, loops):
                    self._current = None
            except Exception as e:
                logger.warning(
                    "Music reinit failed for '%s' (%s): %s",
                    track_name, path, e,
                )
                self._current = None

    def _try_load_and_play(self, path: str, track_name: str,
                           volume: float, loops: int) -> bool:
        """Attempt to load and play a music file. Returns True on success."""
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loops)
            self._current = track_name
            logger.debug("Music: playing '%s' (loops=%d)", track_name, loops)
            return True
        except Exception as e:
            logger.warning("Music playback failed for '%s' (%s): %s",
                           track_name, path, e)
            return False

    def stop(self) -> None:
        """Stop music completely."""
        self._stop_quietly()

    def play_maze(self, env_type: str) -> None:
        """Play the maze ambient track for the given environment type."""
        track_name = f"maze_{env_type}"
        self._maze_track = track_name
        self.play(track_name)

    def restore_maze(self) -> None:
        """Return to the last maze track (called when combat/puzzle ends)."""
        if self._maze_track:
            self.play(self._maze_track)

    def play_combat(self) -> None:
        """Switch to combat music."""
        self.play("combat")

    def play_puzzle_event(self) -> None:
        """Switch to puzzle/event music."""
        self.play("puzzle_event")

    def play_start_screen(self) -> None:
        """Play the title / start screen track."""
        self.play("start_screen")

    def play_victory(self) -> None:
        """Play victory screen track (looping)."""
        self.play("victory")

    def play_game_over(self) -> None:
        """Play game over track once (no loop)."""
        self.play("game_over", loops=0)

    @property
    def current_track(self) -> str | None:
        return self._current

    def has_track(self, track_name: str) -> bool:
        """Return True if a track file exists on disk."""
        path = self._tracks.get(track_name)
        return bool(path and os.path.exists(path))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _stop_quietly(self) -> None:
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        self._current = None
