import os

from dotenv import load_dotenv

load_dotenv()

## Data directory (root for all generated content)
DATA_DIR = os.getenv("DATA_DIR", "data")

### maze settings
# ------------------------------------
# Screen settings
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 700
HUD_HEIGHT = 100
GRID_SIZE = 20

# Maze settings
MIN_HALLWAY_SIZE = 1
MAX_HALLWAY_SIZE = 2
MAZE_WIDTH = SCREEN_WIDTH // GRID_SIZE
MAZE_HEIGHT = (SCREEN_HEIGHT - HUD_HEIGHT) // GRID_SIZE  # Subtract HUD height only
WORLD_SEED = int(os.getenv("WORLD_SEED", "1234"))  # Set to -1 for random seed
STORY_SEED = os.getenv("STORY_SEED", "A local seaside village is under siege by a goblin horde")
NUM_ROOMS = 2  # 5 for base
# Density parameters (% of OPEN/PATH cells, not total cells)
EVENT_DENSITY = 0.10
ITEM_DENSITY = 0.10
NPC_DENSITY = 0.02

# Event type distribution
COMBAT_CHANCE = 0.40
PUZZLE_CHANCE = 0.30
EVENT_CHANCE = 0.30

# Time-gated events: 25% of events are day/night only
TIME_GATE_FRACTION = 0.25

# Legacy aliases for backward compatibility (used by current pipeline.py, maze.py)
EVENT_PERCENT = EVENT_DENSITY
MAP_COLORS = {
    "wall": (40, 40, 40),
    "path": (200, 200, 200),
    "player": (0, 120, 255),
}

# Multi-room progression
DOOR_REVEAL_THRESHOLD = 0.4  # Fraction of encounters to clear before exit door reveals

# Dialogue box
DIALOGUE_BOX_HEIGHT = 100
DIALOGUE_BOX_HEIGHT_ACTIVE = 250

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Game mode
GAME_MODE = os.getenv("GAME_MODE", "offline_static")  # "online" | "offline_local" | "offline_static"

# Post-generation guide
GENERATE_GUIDE = os.getenv("GENERATE_GUIDE", "false").lower() in ("1", "true", "yes")


STARTING_MONEY = 50

## Fog of War settings
# ------------------------------------
FOG_DEFAULT_RADIUS = 3
FOG_DAWN_BONUS = 1
FOG_DAY_BONUS = 2
FOG_DUSK_PENALTY = 1
FOG_NIGHT_PENALTY = 2
FOG_DIM_EDGE = 1

## Day/Night Cycle settings
# ------------------------------------
DAY_NIGHT_CYCLE_LENGTH = 200  # total actions per full day cycle
DAY_NIGHT_REAL_TIME = True  # enable real-time day cycle advancement
DAY_NIGHT_REAL_TIME_SECONDS = 600  # seconds of wall-clock time per full day cycle (default 10 min)

## Night encounter settings
# ------------------------------------
NIGHT_ENCOUNTER_CHANCE = 0.08  # probability of a random night encounter per move at night

## Audio settings
# ------------------------------------
MASTER_VOLUME = max(0, min(100, int(os.getenv("MASTER_VOLUME", "80"))))
MUSIC_VOLUME = max(0, min(100, int(os.getenv("MUSIC_VOLUME", "60"))))
MUSIC_BACKEND = os.getenv("MUSIC_BACKEND", "none")  # "none" | "api"

## SFX settings (ElevenLabs sound effects, generated when MUSIC_BACKEND=api)
# ------------------------------------
SFX_VOLUME = max(0, min(100, int(os.getenv("SFX_VOLUME", "70"))))
ELEVENLABS_API_KEY_ENV = "ELEVENLABS_API_KEY"

## Google GenAI / Lyria 3 (used when MUSIC_BACKEND == "api")
# ------------------------------------
GEMINI_API_KEY_ENV = "GOOGLE_API_KEY"

##GenAI Backend
# ------------------------------------
LLM_BACKEND = os.getenv("LLM_BACKEND", "local")  # "local" for HF transformers, "api" for Anthropic
LLM_MODEL_PATH = os.getenv("LLM_MODEL_PATH", "meta-llama/Llama-3.2-3B-Instruct")
HF_ENV = "hf_write_read"
STORY_CONTEXT_LIMIT = int(os.getenv("STORY_CONTEXT_LIMIT", "1000"))
LLM_CONCURRENCY = int(os.getenv("LLM_CONCURRENCY", "8"))  # max concurrent API requests (ignored for local)

## Anthropic (used when LLM_BACKEND == "api")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
ANTHROPIC_KEY_ENV = "ANTHROPIC_API_KEY"

##Image Generation Backend
# ------------------------------------
IMAGE_BACKEND = os.getenv("IMAGE_BACKEND", "local")  # "local" for diffusers pipeline, "api" for fal.ai API
IMAGE_WIDTH = int(os.getenv("IMAGE_WIDTH", "1024"))
IMAGE_HEIGHT = int(os.getenv("IMAGE_HEIGHT", "1024"))
LOCAL_IMAGE_MODEL_MPS = "stabilityai/sdxl-turbo"
LOCAL_IMAGE_MODEL_CUDA = "black-forest-labs/FLUX.1-schnell"
FAL_MODEL = "fal-ai/nano-banana"
FAL_KEY_ENV = "FAL_KEY"
FAL_NEGATIVE_SUFFIX = (
    " Do not include any text, words, letters, numbers, watermarks, signatures, bananas, or fruit in the image."
)
