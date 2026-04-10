import os
from dotenv import load_dotenv

load_dotenv()

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
MAZE_HEIGHT = (SCREEN_HEIGHT - 100- HUD_HEIGHT) // GRID_SIZE  # Leaving space for dialogue box
WORLD_SEED = 1234 # Set to -1 for random seed
STORY_SEED = "A fire cult plans to infiltrate the castle nobility and take over the kingdom"  # 1-liner story prompt; empty = LLM generates freely
NUM_ROOMS = 5
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
NUM_FOOD = 2
NUM_DRINKS = 2
NUM_TOOLS = 1
NUM_WEAPONS = 2
NUM_SPELL_SCROLLS = 1
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
GAME_MODE = os.getenv("GAME_MODE", "online")  # "online" | "offline_local" | "offline_static"


STARTING_MONEY = 50

## Fog of War settings
# ------------------------------------
FOG_DEFAULT_RADIUS = 3
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
MUSIC_BACKEND = os.getenv("MUSIC_BACKEND", "none")  # "none" | "local" | "api"

##GenAI Backend
# ------------------------------------
LLM_BACKEND = os.getenv("LLM_BACKEND", "local")  # "local" for HF transformers, "api" for Anthropic
LLM_MODEL_PATH = "meta-llama/Llama-3.2-3B-Instruct"
HF_ENV = "hf_write_read"
STORY_CONTEXT_LIMIT = int(os.getenv("STORY_CONTEXT_LIMIT", "1000"))

## Anthropic (used when LLM_BACKEND == "api")
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
ANTHROPIC_KEY_ENV = "ANTHROPIC_API_KEY"

##Image Generation Backend
# ------------------------------------
IMAGE_BACKEND = os.getenv("IMAGE_BACKEND", "local")  # "local" for diffusers pipeline, "api" for fal.ai API
LOCAL_IMAGE_MODEL_MPS = "stabilityai/sdxl-turbo"
LOCAL_IMAGE_MODEL_CUDA = "black-forest-labs/FLUX.1-schnell"
FAL_MODEL = "fal-ai/nano-banana-pro"
FAL_KEY_ENV = "FAL_KEY"
FAL_SUPPORTED_MODELS = {
    "flux-schnell": "fal-ai/flux/schnell",
    "nano-banana-pro": "fal-ai/nano-banana-pro",
    "flux-pro": "fal-ai/flux-pro/v1.1",
}
