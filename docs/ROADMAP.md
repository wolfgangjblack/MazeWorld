# MazeWorld Roadmap

## Vision

MazeWorld is a procedurally generated RPG that supports three tiers of content generation. Running `python main.py` pre-generates all game assets and packages a standalone executable. The mode determines how much content is baked at build time vs. generated live at runtime.

## Architecture

### Build Layer (`main.py`)
The builder orchestrates all pre-generation pipelines, writes output to `data/`, and packages the game via PyInstaller. Each run produces a fresh, self-contained game that can be distributed.

### Game Layer (packaged executable)
The game reads from the bundled `data/` directory and presents the player with start, load, config, and settings screens. The mode (baked into the build) determines whether dialogue and images come from static files, a local model, or an API.

### Generation Backend
Every generative capability (NPC dialogue, personalities, events, images) routes through a backend interface. The mode selects which implementation backs that interface:

| Capability | Static (Mode 1) | Local (Mode 2) | Online (Mode 3) |
|---|---|---|---|
| NPC dialogue | Pre-baked dialogue trees, multiple choice | Local LLM (Llama) | Claude API |
| NPC personalities | Pre-generated JSON | Local LLM | Claude API |
| Story / events | Pre-written seeds | Local LLM | Claude API |
| Images / portraits | Pre-generated assets on disk | Local diffusion (FLUX) | fal API |
| Player input | Multiple choice | Free text | Free text |

---

## Phase 1 — Foundation

Restructure the codebase to separate building from playing, and establish the core systems that all three modes depend on.

- Split `main.py` (builder) from game entry point (`game.py`)
- Add mode selection to `config.py` and build pipeline
- Create game manifest (`data/game_manifest.json`) that records mode, seed, asset index
- Build screen state machine: Start, New Game, Load, Config, Quit
- Config screen: resolution, volume; API key entry for online mode
- Consolidate duplicate item registry loading into a single shared module
- Add `__init__.py` files to packages
- Clean up stale `utils/` directory at project root
- Fix NPC environment bug (inherit from maze, not random)

## Phase 2 — Pre-Generation Pipeline

Build the `main.py` orchestrator that generates all game content and writes it to `data/`.

- Maze generation: write layouts to `data/mazes/` (one per level)
- World config generation: environment themes, level count, difficulty → `data/world/`
- NPC personality generation: wire `generate_llm_primatives.py` into the pipeline → `data/npcs/`
- NPC portrait generation: complete `generate_image_primatives.py`, save images → `data/images/`
- Event / quest generation: define quest model, generate seeds → `data/events/`, `data/quests/`
- Dialogue tree generation (Mode 1): generate scripted conversation branches → `data/dialogues/`
- Game manifest: write build metadata after generation completes
- PyInstaller packaging: bundle game entry point + `data/` into distributable exe

## Phase 3 — Generation Backend Abstraction

Create the interface layer so the game runtime can dispatch to static, local, or API backends.

- Define generation backend interface (dialogue, personality, events, images)
- Implement static backend: reads from `data/` JSON and assets
- Implement local backend: wraps current Llama/FLUX code
- Implement online backend: Claude API for text, fal API for images
- Lazy model loading for local mode (don't load at import time)
- Mode 1 dialogue UI: multiple-choice response selection in dialogue box

## Phase 4 — Game Systems

Build the gameplay systems that make MazeWorld a complete game.

- Quest system: quest model, triggers, progression tracking, completion
- Event system: flesh out event tiles with generated encounters, dice-roll mechanics
- NPC awareness of nearby events ("I think I saw something nearby...")
- Combat system
- Save / load: serialize and restore full game state
- Portal system: transitions between levels
- Level themes and backgrounds
- Logging: generation logs, play event logs, performance metrics

## Phase 5 — Polish

- Start / load / end game screens with visual design
- Sound and music
- Improved maze rendering (themed tiles, lighting)
- NPC portrait display in dialogue
- Difficulty scaling across levels
- Mac support for local LLM/diffusion generation (MPS optimization)
- Build size optimization for Mode 2 (model weight management)
