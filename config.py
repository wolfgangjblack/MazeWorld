
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
MAZE_SEED = -1 # Set to -1 for random seed
EVENT_PERCENT = 0.1

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

#NPC settings
# ------------------------------------

## Item settings
# ------------------------------------
NUM_FOOD = 2
NUM_DRINKS = 2
NUM_TOOLS = 1

##GenAI Settings
# ------------------------------------
LLM_MODEL_PATH ="meta-llama/Llama-3.2-3B-Instruct" 
#"mlabonne/Meta-Llama-3.1-8B-Instruct-abliterated"
DIFFUSION_MODEL_PATH = "flux_place_holder" 

HF_ENV = "hf_write_read"