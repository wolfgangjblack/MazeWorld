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
STORY_SEED = ""  # 1-liner story prompt; empty = LLM generates freely
NUM_ROOMS = int(os.getenv("NUM_ROOMS", "1"))
EVENT_PERCENT = 0.1
EVENT_DENSITY = EVENT_PERCENT  # Alias: configurable encounter density
QUEST_DENSITY = float(os.getenv("QUEST_DENSITY", "0.1"))
MAP_COLORS = {
    "wall": (40, 40, 40),
    "path": (200, 200, 200),
    "player": (0, 120, 255),
}

# Multi-room progression
NUM_ROOMS = 1  # Number of rooms in the dungeon (1 = single room, no progression)
DOOR_REVEAL_THRESHOLD = 0.4  # Fraction of encounters to clear before exit door reveals

# Dialogue box
DIALOGUE_BOX_HEIGHT = 100
DIALOGUE_BOX_HEIGHT_ACTIVE = 250

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Game mode
GAME_MODE = os.getenv("GAME_MODE", "online")  # "online" | "offline_local" | "offline_static"

#NPC settings
# ------------------------------------

## Item settings
# ------------------------------------
NUM_FOOD = 2
NUM_DRINKS = 2
NUM_TOOLS = 1
NUM_WEAPONS = 2
NUM_SPELL_SCROLLS = 1
STARTING_MONEY = 50

## Fog of War settings
# ------------------------------------
FOG_DEFAULT_RADIUS = 3
FOG_NIGHT_PENALTY = 2
FOG_DIM_EDGE = 1

## Day/Night Cycle settings
# ------------------------------------
DAY_NIGHT_CYCLE_LENGTH = 200  # total actions per full day cycle

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
