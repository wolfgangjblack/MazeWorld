"""Frozen-app entry point.

Runs when MazeWorld is launched as a PyInstaller-packaged .app or .exe.
Forces offline_static mode (no LLM/API calls), routes any uncaught
exception to crash.log in the platform-appropriate save directory so
console-less builds still leave a useful trail.
"""

import os
import sys

os.environ["GAME_MODE"] = "offline_static"
os.environ["LLM_BACKEND"] = "local"
os.environ["MUSIC_BACKEND"] = "none"
os.environ["IMAGE_BACKEND"] = "local"


def main() -> None:
    from main import run_game_only

    try:
        run_game_only()
    except Exception:
        import traceback

        from config import SAVE_DIR

        os.makedirs(SAVE_DIR, exist_ok=True)
        crash_path = os.path.join(SAVE_DIR, "crash.log")
        with open(crash_path, "w") as f:
            traceback.print_exc(file=f)
        sys.exit(1)


if __name__ == "__main__":
    main()
