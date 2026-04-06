# TODO: Pygame EXE Packaging

## Part 1: Split main.py into Builder + Game Entry Point

The current `main.py` handles both world generation and the pygame game loop in one file.
Split it so `main.py` becomes the **builder** (generate + package) and `game.py` becomes the
**player-facing entry point** (load data, run pygame).

### 1.1 Create `game.py` (new file)

- [ ] Move all pygame/game-loop code out of `main.py` into `game.py`
  - Move imports: `pygame`, all `src.models.*`, `src.controllers.*`, `src.views.*` imports (lines 13-28)
  - Move `NPC_CLASS_MAP` dict (lines 29-33)
  - Move `setup_game()` function (lines 52-127)
  - Move the pygame init + screen state machine loop from `main()` (lines 153-262)
- [ ] `game.py` should accept no CLI args — it assumes `data/` is fully populated
  - On launch: call `registry.load()`, verify `registry.has_manifest()` is True, then run the game loop
  - If `data/manifest.json` is missing, print an error and exit ("Run main.py to generate a world first")
- [ ] `game.py` must import `config.py` for `SCREEN_WIDTH`, `SCREEN_HEIGHT`, `WORLD_SEED`, `NUM_FOOD`, `NUM_DRINKS`, `NUM_TOOLS`
- [ ] `game.py` must import `src.registry.registry` for data loading

### 1.2 Refactor `main.py` to be the builder

- [ ] Remove all pygame imports and game-loop code from `main.py`
- [ ] Keep: `parse_args()`, `run_generation()`, and the generation logic from `main()`
- [ ] Add a new `--package` flag to `parse_args()` that triggers PyInstaller packaging after generation
- [ ] Add a `run_packaging(seed)` function (placeholder initially) that calls PyInstaller
- [ ] Update the `main()` flow:
  1. Parse args
  2. If `--dev`: generate world (existing behavior), then launch `game.py` via `subprocess` or `os.execv`
  3. If `--package`: generate world, then call `run_packaging(WORLD_SEED)`
  4. Default (no flags): generate world if needed, then launch `game.py`
- [ ] Keep `world_gen.py` working — it just calls `generate_world()` directly, no changes needed

### 1.3 Verify the split

- [ ] `python game.py` launches the game from existing `data/` (no generation)
- [ ] `python main.py --dev` generates world then launches `game.py`
- [ ] `python main.py --package` generates world then builds the exe
- [ ] Existing tests in `tests/` still pass

---

## Part 2: Wire Up PyInstaller Packaging

Bundle `game.py` + `data/` into a distributable exe labeled by world seed.

### 2.1 Create PyInstaller spec file

- [ ] Create `mazeworld.spec` (or `game.spec`) at the repo root
  - Entry point: `game.py`
  - Bundle `data/` as data files (PyInstaller `datas` parameter): `('data', 'data')`
  - Bundle `src/` (all Python modules are imported by `game.py`)
  - Bundle `config.py` (imported at top level)
  - Hidden imports to declare (PyInstaller may not detect these automatically):
    - `src.registry`
    - `src.models.maze`, `src.models.dialogue_box`, `src.models.player`, `src.models.npc`
    - `src.controllers.game_controller`, `src.controllers.screen_controller`
    - `src.views.start_view`, `src.views.class_select_view`, `src.views.room_intro_view`
    - `src.utils.dataloader_utils`
    - `dotenv` (used by `config.py` via `load_dotenv()`)
  - Exclude heavy generation-only deps that the player exe does NOT need:
    - `torch`, `torchvision`, `transformers`, `accelerate`, `diffusers` (AI model libs)
    - `fal_client` (image API)
    - `anthropic` (LLM API)
    - `tqdm` (generation progress bars)
    - `src.generate` (entire generation package)
  - Set `console=False` on Windows for a clean window, `console=True` on macOS/Linux
  - Use `--onefile` mode for a single distributable binary

### 2.2 Handle data path at runtime

- [ ] In `game.py`, detect if running from a PyInstaller bundle:
  ```python
  import sys, os
  if getattr(sys, 'frozen', False):
      BASE_DIR = sys._MEIPASS  # PyInstaller temp dir
  else:
      BASE_DIR = os.path.dirname(os.path.abspath(__file__))
  ```
- [ ] Update all `data/` file path references to use `os.path.join(BASE_DIR, 'data', ...)`
  - `src/registry.py` — `_load_manifest()`, `_load_items()`, `_load_npcs()`, etc. use hardcoded `"data/"` paths
  - `main.py:setup_game()` (moving to `game.py`) uses `"data/maze/maze.json"` directly (line 60)
  - Either pass `BASE_DIR` through, or set `os.chdir(BASE_DIR)` at `game.py` startup before any imports that use relative paths
- [ ] The simplest approach: `os.chdir(BASE_DIR)` at the top of `game.py` before importing `config`/`registry`, so all existing relative paths work unchanged

### 2.3 Implement `run_packaging()` in `main.py`

- [ ] Add `run_packaging(seed)` function that shells out to PyInstaller:
  ```python
  import subprocess
  def run_packaging(seed):
      exe_name = f"MazeWorld_seed{seed}"
      subprocess.run([
          "pyinstaller",
          "--name", exe_name,
          "--onefile",
          "--add-data", "data:data",
          "--add-data", "config.py:.",
          "game.py",
      ], check=True)
  ```
- [ ] Output exe goes to `dist/MazeWorld_seed{WORLD_SEED}` (PyInstaller default output dir)
- [ ] Print the output path when done so the builder knows where to find it

### 2.4 Handle pygame assets

- [ ] Audit for any pygame font/image loading that uses paths not under `data/`:
  - `pygame.font.Font(None, 32)` in `main.py` line 159 — uses default font, no file needed
  - Portrait images are loaded from `data/portraits/` — already bundled
  - Check `src/views/` for any hardcoded asset paths
- [ ] If any view files load assets from outside `data/`, add those paths to the spec's `datas` list

### 2.5 Seed labeling

- [ ] The exe filename includes the seed: `MazeWorld_seed1234` (from `config.WORLD_SEED`)
- [ ] Optionally embed seed in the window title: `pygame.display.set_caption(f"MazeWorld - Seed {WORLD_SEED}")`
- [ ] The `data/manifest.json` inside the bundle already records `world_seed` — this is the canonical reference

### 2.6 Test the packaged exe

- [ ] Build: `python main.py --package` with a known seed
- [ ] Run the output exe and verify:
  - Game launches without errors
  - Maze, NPCs, events, quests load from bundled data
  - Portraits display if they were generated
  - No import errors from excluded generation-only packages
- [ ] Test on a clean machine (or venv without dev deps) to confirm no missing dependencies
- [ ] Test with `WORLD_SEED = -1` (random seed) — ensure the exe name captures the actual seed used

---

## Key Files Reference

| File | Role | Changes Needed |
|------|------|---------------|
| `main.py` | Builder entry point | Remove game loop, add `--package`, add `run_packaging()` |
| `game.py` | **New** — player entry point | Receives game loop from `main.py`, adds `BASE_DIR` detection |
| `config.py` | Shared config | No changes (bundled as-is) |
| `world_gen.py` | Legacy gen entry | No changes |
| `src/generate/pipeline.py` | World generation | No changes (excluded from exe) |
| `src/registry.py` | Data loading | May need `BASE_DIR`-aware paths (or rely on `os.chdir`) |
| `requirements.txt` | Deps | Already has `pyinstaller==6.11.1` |
| `mazeworld.spec` | **New** — PyInstaller spec | Defines bundling, exclusions, hidden imports |
