import pygame

from config import BLACK, GRID_SIZE, WHITE
from src.models.items import Drink, Food, Tool
from src.registry import registry
from src.utils.display_utils import game_to_screen

EVENT_COLOR = (0, 0, 0)  # Black — events are invisible during normal gameplay
DEBUG_COMBAT_COLOR = (200, 50, 50)  # Red — combat encounters
DEBUG_PUZZLE_COLOR = (50, 150, 220)  # Blue — puzzles
DEBUG_EVENT_COLOR = (50, 200, 100)  # Green — narrative events
DEBUG_EVENT_FALLBACK = (128, 0, 128)  # Purple — unknown type
DEBUG_GATE_COLOR = (180, 140, 30)  # Dark gold — gate encounter (debug)
BOSS_TILE_COLOR = (140, 20, 20)  # Dark red — climax boss (always visible)
DOOR_COLOR = (255, 215, 0)  # Gold for revealed exit doors
ESCORT_HIGHLIGHT = (0, 180, 0, 100)  # Semi-transparent green for escort zones

# Fog of war colors
FOG_HIDDEN_COLOR = (10, 10, 15)  # Near-black for hidden tiles
FOG_REVEALED_COLOR = (40, 40, 50)  # Dark gray for revealed-but-not-visible tiles
FOG_DIM_ALPHA = 90  # Semi-transparent overlay for dim edge tiles

# Night overlay color (dark blue tint)
NIGHT_OVERLAY_COLOR = (10, 10, 50)


class MazeView:
    _EVENT_TYPE_COLORS = {
        "combat": DEBUG_COMBAT_COLOR,
        "puzzle": DEBUG_PUZZLE_COLOR,
        "event": DEBUG_EVENT_COLOR,
    }

    def draw_maze(
        self,
        screen,
        maze,
        escort_zones=None,
        debug_reveal=False,
        fog=None,
        player_x=0,
        player_y=0,
        visibility_radius=3,
        night_alpha=0,
        event_type_map=None,
        event_flag_map=None,
    ):
        for y, row in enumerate(maze.grid):
            for x, cell in enumerate(row):
                screen_x, screen_y = game_to_screen(x, y)
                rect = pygame.Rect(screen_x, screen_y, GRID_SIZE, GRID_SIZE)

                # Fog of war: if fog is active and tile is not revealed, draw hidden
                if fog and not debug_reveal:
                    if not fog.is_revealed(x, y):
                        pygame.draw.rect(screen, FOG_HIDDEN_COLOR, rect)
                        continue

                # Draw the tile normally
                if cell == maze.wall_tile_id:
                    pygame.draw.rect(screen, WHITE, rect)
                elif cell == maze.event_tile_id:
                    eflag = (event_flag_map or {}).get((x, y), "")
                    if eflag == "climax_boss":
                        pygame.draw.rect(screen, BLACK, rect)
                        inner = pygame.Rect(screen_x + 2, screen_y + 2, GRID_SIZE - 4, GRID_SIZE - 4)
                        pygame.draw.rect(screen, BOSS_TILE_COLOR, inner)
                    elif eflag == "gate" and debug_reveal:
                        pygame.draw.rect(screen, BLACK, rect)
                        inner = pygame.Rect(screen_x + 2, screen_y + 2, GRID_SIZE - 4, GRID_SIZE - 4)
                        pygame.draw.rect(screen, DEBUG_GATE_COLOR, inner)
                    elif debug_reveal:
                        pygame.draw.rect(screen, BLACK, rect)
                        etype = (event_type_map or {}).get((x, y), "")
                        dcolor = self._EVENT_TYPE_COLORS.get(etype, DEBUG_EVENT_FALLBACK)
                        event_rect = pygame.Rect(
                            screen_x + GRID_SIZE // 4,
                            screen_y + GRID_SIZE // 4,
                            GRID_SIZE // 2,
                            GRID_SIZE // 2,
                        )
                        pygame.draw.rect(screen, dcolor, event_rect)
                    else:
                        pygame.draw.rect(screen, BLACK, rect)
                elif cell == maze.door_tile_id:
                    # Revealed exit door — gold tile
                    pygame.draw.rect(screen, BLACK, rect)
                    door_rect = pygame.Rect(
                        screen_x + 2,
                        screen_y + 2,
                        GRID_SIZE - 4,
                        GRID_SIZE - 4,
                    )
                    pygame.draw.rect(screen, DOOR_COLOR, door_rect)
                elif cell == 0:
                    pygame.draw.rect(screen, BLACK, rect)
                elif registry.is_item(cell):
                    pygame.draw.rect(screen, BLACK, rect)
                    item = registry.get_item(cell)
                    if isinstance(item, Food):
                        color = (255, 215, 0)
                    elif isinstance(item, Drink):
                        color = (30, 144, 255)
                    elif isinstance(item, Tool):
                        color = (255, 0, 255)
                    else:
                        color = (200, 200, 200)

                    item_rect = pygame.Rect(
                        screen_x + GRID_SIZE // 4,
                        screen_y + GRID_SIZE // 4,
                        GRID_SIZE // 2,
                        GRID_SIZE // 2,
                    )
                    pygame.draw.rect(screen, color, item_rect)

                # Apply fog dimming for revealed-but-not-currently-visible tiles
                if fog and not debug_reveal:
                    if not fog.is_currently_visible(x, y, player_x, player_y, visibility_radius, maze=maze):
                        dim = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
                        dim.fill((0, 0, 0, 140))
                        screen.blit(dim, (screen_x, screen_y))
                    elif fog.is_dim(x, y, player_x, player_y, visibility_radius):
                        dim = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
                        dim.fill((0, 0, 0, FOG_DIM_ALPHA))
                        screen.blit(dim, (screen_x, screen_y))

        # Night overlay on the entire maze area
        if night_alpha > 0 and not debug_reveal:
            maze_h = len(maze.grid) * GRID_SIZE
            maze_w = (len(maze.grid[0]) if maze.grid else 0) * GRID_SIZE
            _, top_y = game_to_screen(0, 0)
            overlay = pygame.Surface((maze_w, maze_h), pygame.SRCALPHA)
            overlay.fill((*NIGHT_OVERLAY_COLOR, night_alpha))
            screen.blit(overlay, (0, top_y))

        if escort_zones:
            for tx, ty in escort_zones:
                for ox in range(-2, 3):
                    for oy in range(-2, 3):
                        hx, hy = tx + ox, ty + oy
                        sx, sy = game_to_screen(hx, hy)
                        highlight = pygame.Surface((GRID_SIZE, GRID_SIZE), pygame.SRCALPHA)
                        highlight.fill((0, 180, 0, 60))
                        screen.blit(highlight, (sx, sy))
