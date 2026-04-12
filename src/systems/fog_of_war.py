"""Fog of war visibility system.

Manages a 2D grid of revealed/hidden tiles. All tiles start hidden.
Player reveals tiles within a visibility radius as they move.
Line-of-sight raycasting ensures walls block visibility.
"""

from typing import List

from config import (
    MAZE_WIDTH, MAZE_HEIGHT, FOG_DEFAULT_RADIUS,
    FOG_DAWN_BONUS, FOG_DAY_BONUS, FOG_DUSK_PENALTY, FOG_NIGHT_PENALTY,
    FOG_DIM_EDGE,
)

DEFAULT_VISIBILITY_RADIUS = FOG_DEFAULT_RADIUS
DIM_EDGE_TILES = FOG_DIM_EDGE

_PERIOD_MODIFIERS = {
    "dawn": FOG_DAWN_BONUS,
    "day": FOG_DAY_BONUS,
    "dusk": -FOG_DUSK_PENALTY,
    "night": -FOG_NIGHT_PENALTY,
}


class FogOfWar:
    """Tracks which tiles the player has revealed."""

    def __init__(self, width: int = MAZE_WIDTH, height: int = MAZE_HEIGHT):
        self.width = width
        self.height = height
        # False = hidden, True = revealed (permanently)
        self.revealed: List[List[bool]] = [
            [False for _ in range(width)] for _ in range(height)
        ]

    def get_visibility_radius(self, player, is_night: bool = False,
                              has_torch: bool = False,
                              time_period: str | None = None) -> int:
        """Calculate effective visibility radius.

        Base radius + WIS bonus (+1 per 2 WIS modifier points).
        Varies by time period: dawn/day give bonuses, dusk/night give penalties.
        Torch negates night/dusk penalties.
        """
        radius = DEFAULT_VISIBILITY_RADIUS

        wis_mod = player.get_stat_mod("WIS") if hasattr(player, 'get_stat_mod') else 0
        radius += max(0, wis_mod // 2)

        period = time_period or ("night" if is_night else "day")
        modifier = _PERIOD_MODIFIERS.get(period, 0)
        if modifier < 0 and has_torch:
            modifier = 0
        radius += modifier

        return max(1, radius)

    def update(self, player_x: int, player_y: int, maze,
               radius: int) -> None:
        """Reveal all tiles visible from (player_x, player_y) within radius.

        Uses raycasting: for each tile in the radius circle, cast a ray
        from the player. If any wall tile is encountered before reaching
        the target, the target is not visible.
        """
        # Player's own tile is always revealed
        if 0 <= player_y < self.height and 0 <= player_x < self.width:
            self.revealed[player_y][player_x] = True

        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                tx, ty = player_x + dx, player_y + dy

                # Bounds check
                if not (0 <= tx < self.width and 0 <= ty < self.height):
                    continue

                # Circle check (Euclidean distance)
                if dx * dx + dy * dy > radius * radius:
                    continue

                # Line-of-sight check
                if self._has_line_of_sight(player_x, player_y, tx, ty, maze):
                    self.revealed[ty][tx] = True

    def _has_line_of_sight(self, x0: int, y0: int, x1: int, y1: int,
                           maze) -> bool:
        """Bresenham's line algorithm to check if a wall blocks LOS.

        Returns True if there is a clear line of sight from (x0,y0) to (x1,y1).
        Walls at the target tile itself are still visible (you can see a wall).
        """
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x1 > x0 else -1
        sy = 1 if y1 > y0 else -1
        err = dx - dy

        cx, cy = x0, y0

        while True:
            # Reached target — visible
            if cx == x1 and cy == y1:
                return True

            # Check if current intermediate tile is a wall (blocks LOS)
            # Skip the origin tile
            if (cx, cy) != (x0, y0) and maze.is_wall(cx, cy):
                return False

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                cx += sx
            if e2 < dx:
                err += dx
                cy += sy

    def is_revealed(self, x: int, y: int) -> bool:
        """Check if a tile has been revealed."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.revealed[y][x]
        return False

    def is_currently_visible(self, x: int, y: int, player_x: int,
                             player_y: int, radius: int,
                             maze=None) -> bool:
        """Check if a tile is within the player's current visibility radius and has LOS."""
        dx = x - player_x
        dy = y - player_y
        if dx * dx + dy * dy > radius * radius:
            return False
        if maze is not None:
            return self._has_line_of_sight(player_x, player_y, x, y, maze)
        return True

    def is_dim(self, x: int, y: int, player_x: int, player_y: int,
               radius: int) -> bool:
        """Check if a tile is at the dim edge of visibility."""
        dx = x - player_x
        dy = y - player_y
        dist_sq = dx * dx + dy * dy
        inner = (radius - DIM_EDGE_TILES) ** 2
        outer = radius * radius
        return inner < dist_sq <= outer

    def serialize(self) -> dict:
        """Serialize fog state for save/load."""
        return {
            "width": self.width,
            "height": self.height,
            "revealed": self.revealed,
        }

    @classmethod
    def deserialize(cls, data: dict) -> "FogOfWar":
        """Restore fog state from saved data."""
        fog = cls(width=data["width"], height=data["height"])
        fog.revealed = data["revealed"]
        return fog
