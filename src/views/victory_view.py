"""Victory screen — story conclusion, full stats summary, and replay options."""

import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK

TITLE_COLOR = (220, 200, 60)
TEXT_COLOR = (200, 200, 200)
HIGHLIGHT_COLOR = (255, 255, 150)
SELECTED_COLOR = (255, 255, 100)
UNSELECTED_COLOR = (180, 180, 180)

MENU_ITEMS = ["Start New Game", "Quit"]


class VictoryView:
    """Victory screen with full stats summary and replay options."""

    def __init__(self, screen, font, player, time_played: float = 0.0,
                 monsters_killed: int = 0, damage_dealt: int = 0,
                 damage_taken: int = 0, items_used: int = 0,
                 money_earned: int = 0, rooms_cleared: int = 1):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 56)
        self.small_font = pygame.font.Font(None, 22)
        self.player = player
        self.time_played = time_played
        self.monsters_killed = monsters_killed
        self.damage_dealt = damage_dealt
        self.damage_taken = damage_taken
        self.items_used = items_used
        self.money_earned = money_earned
        self.rooms_cleared = rooms_cleared
        self.selected_index = 0
        self.scroll_offset = 0

    def _format_time(self, seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}h {m}m {s}s"
        return f"{m}m {s}s"

    def draw(self):
        self.screen.fill(BLACK)

        # Title
        title = self.title_font.render("VICTORY", True, TITLE_COLOR)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 30))

        # Story conclusion
        name = self.player.name
        cls_name = self.player.player_class.name if self.player.player_class else "Adventurer"
        env = self.player.player_class.environment if self.player.player_class else "the unknown"
        conclusion = f"{name} the {cls_name} has conquered {env}!"
        conc_surf = self.font.render(conclusion, True, HIGHLIGHT_COLOR)
        self.screen.blit(conc_surf, ((SCREEN_WIDTH - conc_surf.get_width()) // 2, 80))

        # Stats summary
        stats_lines = [
            ("Class", cls_name),
            ("Level", str(self.player.level)),
            ("Environment", env),
            ("Rooms Cleared", str(self.rooms_cleared)),
            ("", ""),
            ("Quests Completed", str(len(self.player.completed_quests))),
            ("Quests Failed", str(len(self.player.failed_quests))),
            ("Active Quests", str(len(self.player.active_quests))),
            ("", ""),
            ("Monsters Killed", str(self.monsters_killed)),
            ("Damage Dealt", str(self.damage_dealt)),
            ("Damage Taken", str(self.damage_taken)),
            ("", ""),
            ("Items Used", str(self.items_used)),
            ("Gold Earned", str(self.money_earned)),
            ("Followers Escorted", str(len(self.player.followers))),
            ("", ""),
            ("Time Played", self._format_time(self.time_played)),
        ]

        y = 120 - self.scroll_offset
        col_label_x = SCREEN_WIDTH // 2 - 160
        col_value_x = SCREEN_WIDTH // 2 + 80
        for label, value in stats_lines:
            if y < 110 or y > SCREEN_HEIGHT - 130:
                y += 24
                continue
            if not label:
                y += 12
                continue
            label_surf = self.small_font.render(label, True, TEXT_COLOR)
            value_surf = self.small_font.render(value, True, HIGHLIGHT_COLOR)
            self.screen.blit(label_surf, (col_label_x, y))
            self.screen.blit(value_surf, (col_value_x, y))
            y += 24

        # Menu options
        y = SCREEN_HEIGHT - 100
        for i, item in enumerate(MENU_ITEMS):
            color = SELECTED_COLOR if i == self.selected_index else UNSELECTED_COLOR
            prefix = "> " if i == self.selected_index else "  "
            surf = self.font.render(f"{prefix}{item}", True, color)
            self.screen.blit(surf, ((SCREEN_WIDTH - surf.get_width()) // 2, y))
            y += 36

    def handle_input(self, event) -> str | None:
        """Returns 'new_game' or 'quit', or None."""
        if event.key == pygame.K_UP:
            self.selected_index = (self.selected_index - 1) % len(MENU_ITEMS)
        elif event.key == pygame.K_DOWN:
            self.selected_index = (self.selected_index + 1) % len(MENU_ITEMS)
        elif event.key == pygame.K_RETURN:
            selected = MENU_ITEMS[self.selected_index]
            if selected == "Start New Game":
                return "new_game"
            if selected == "Quit":
                return "quit"
        return None
