import math

import pygame

from config import GRID_SIZE, HUD_HEIGHT, SCREEN_WIDTH
from src.utils.display_utils import game_to_screen

PERIOD_COLORS = {
    "dawn": (255, 180, 80),
    "day": (255, 255, 150),
    "dusk": (200, 120, 80),
    "night": (100, 100, 200),
}

_CLOCK_RADIUS = 30
_CLOCK_CENTER_X = SCREEN_WIDTH - _CLOCK_RADIUS - 12
_CLOCK_CENTER_Y = HUD_HEIGHT // 2


class PlayerView:
    def draw_player(self, screen, player):
        screen_x, screen_y = game_to_screen(player.x, player.y)
        player_rect = pygame.Rect(screen_x, screen_y, GRID_SIZE, GRID_SIZE)
        pygame.draw.rect(screen, player.color, player_rect)

    def _stamina_bar_color(self, ratio):
        if ratio > 0.5:
            return (0, 200, 0)
        if ratio > 0.25:
            return (255, 200, 0)
        return (200, 50, 50)

    def draw_hud(self, screen, player, time_period=None, day_number=None, period_progress=0.0):
        clock_reserved = _CLOCK_RADIUS * 2 + 30
        bar_width = (SCREEN_WIDTH - 60 - clock_reserved) // 2
        bar_height = 20
        spacing = 20
        hud_y = (HUD_HEIGHT - bar_height) // 2

        health_x = 20
        stamina_x = health_x + bar_width + spacing

        # Health bar (left)
        health_ratio = player.health / player.max_health if player.max_health else 0
        health_rect = pygame.Rect(health_x, hud_y, bar_width * health_ratio, bar_height)
        pygame.draw.rect(screen, (255, 0, 0), health_rect)
        pygame.draw.rect(screen, (255, 255, 255), (health_x, hud_y, bar_width, bar_height), 2)

        # Stamina bar (right)
        stamina_ratio = player.stamina / player.max_stamina if player.max_stamina else 0
        stamina_color = self._stamina_bar_color(stamina_ratio)
        stamina_rect = pygame.Rect(stamina_x, hud_y, bar_width * stamina_ratio, bar_height)
        pygame.draw.rect(screen, stamina_color, stamina_rect)
        pygame.draw.rect(screen, (255, 255, 255), (stamina_x, hud_y, bar_width, bar_height), 2)

        font = pygame.font.SysFont(None, 24)

        health_label = font.render("Health", True, (255, 255, 255))
        health_label_rect = health_label.get_rect(center=(health_x + bar_width // 2, hud_y - 15))
        screen.blit(health_label, health_label_rect)

        health_value = font.render(f"{int(player.health)} / {player.max_health}", True, (255, 255, 255))
        health_value_rect = health_value.get_rect(center=(health_x + bar_width // 2, hud_y + bar_height + 15))
        screen.blit(health_value, health_value_rect)

        stamina_label = font.render("Stamina", True, (255, 255, 255))
        stamina_label_rect = stamina_label.get_rect(center=(stamina_x + bar_width // 2, hud_y - 15))
        screen.blit(stamina_label, stamina_label_rect)

        stamina_value = font.render(f"{int(player.stamina)} / {player.max_stamina}", True, (255, 255, 255))
        stamina_value_rect = stamina_value.get_rect(center=(stamina_x + bar_width // 2, hud_y + bar_height + 15))
        screen.blit(stamina_value, stamina_value_rect)

        if time_period:
            period_name = time_period if isinstance(time_period, str) else time_period.value
            self._draw_time_clock(screen, period_name, period_progress, font)
            if day_number is not None:
                small = pygame.font.SysFont(None, 18)
                day_surf = small.render(f"Day {day_number}", True, (180, 180, 180))
                day_rect = day_surf.get_rect(centerx=_CLOCK_CENTER_X, top=_CLOCK_CENTER_Y + 2)
                screen.blit(day_surf, day_rect)

    def _draw_time_clock(self, screen, period_name, progress, font):
        cx, cy = _CLOCK_CENTER_X, _CLOCK_CENTER_Y
        r = _CLOCK_RADIUS

        # Semi-circle background
        pygame.draw.arc(screen, (60, 60, 70), (cx - r, cy - r, r * 2, r * 2), 0, math.pi, 2)
        pygame.draw.line(screen, (60, 60, 70), (cx - r, cy), (cx + r, cy), 2)

        _ANGLE_RANGES = {
            "dawn": (math.pi, math.pi * 0.55),
            "day": (math.pi * 0.55, math.pi * 0.45),
            "dusk": (math.pi * 0.45, 0),
            "night": (0, math.pi),
        }
        start_a, end_a = _ANGLE_RANGES.get(period_name, (math.pi, 0))
        angle = start_a + (end_a - start_a) * progress

        orb_x = cx + int((r - 8) * math.cos(angle))
        orb_y = cy - int((r - 8) * math.sin(angle))

        if period_name in ("dawn", "day", "dusk"):
            self._draw_sun(screen, orb_x, orb_y, period_name)
        else:
            self._draw_moon(screen, orb_x, orb_y)

    def _draw_sun(self, screen, x, y, period):
        colors = {
            "dawn": (255, 160, 60),
            "day": (255, 230, 50),
            "dusk": (220, 100, 40),
        }
        color = colors.get(period, (255, 230, 50))
        pygame.draw.circle(screen, color, (x, y), 8)
        ray_color = tuple(min(255, c + 40) for c in color)
        for i in range(8):
            a = i * math.pi / 4
            rx = x + int(12 * math.cos(a))
            ry = y - int(12 * math.sin(a))
            pygame.draw.line(screen, ray_color, (x, y), (rx, ry), 1)

    def _draw_moon(self, screen, x, y):
        pygame.draw.circle(screen, (200, 210, 230), (x, y), 7)
        pygame.draw.circle(screen, (40, 40, 60), (x + 3, y - 2), 6)
