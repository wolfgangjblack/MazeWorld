"""Victory screen — end-of-game stats summary and final message."""

import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE
from src.utils.text_utils import draw_wrapped_text


GOLD = (220, 180, 60)
DIM = (150, 150, 150)
STAT_COLOR = (180, 220, 255)
PANEL_BG = (20, 20, 40)


class VictoryView:
    """Displays victory screen with game stats summary."""

    def __init__(self, screen, font, player, stats: dict, total_rooms: int,
                 story_paragraph: str = ""):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 56)
        self.big_font = pygame.font.Font(None, 40)
        self.small_font = pygame.font.Font(None, 24)
        self.player = player
        self.stats = stats
        self.total_rooms = total_rooms
        self.story_paragraph = story_paragraph

    def handle_input(self, event) -> str | None:
        """Returns 'quit' or 'menu'."""
        if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
            return "quit"
        if event.key == pygame.K_RETURN:
            return "menu"
        return None

    def draw(self):
        self.screen.fill(BLACK)

        # Title
        title = self.title_font.render("VICTORY!", True, GOLD)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 30))

        # Subtitle
        p = self.player
        class_name = p.player_class.name if p.player_class else "Adventurer"
        archetype = p.player_class.archetype if p.player_class else ""
        subtitle = self.big_font.render(
            f"{p.name} the {class_name}", True, WHITE)
        self.screen.blit(subtitle, ((SCREEN_WIDTH - subtitle.get_width()) // 2, 90))

        # Stats panel
        panel_x, panel_y = 60, 150
        panel_w, panel_h = SCREEN_WIDTH - 120, 400
        pygame.draw.rect(self.screen, PANEL_BG, (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.rect(self.screen, GOLD, (panel_x, panel_y, panel_w, panel_h), 2)

        # Stat lines
        stats_lines = [
            ("Class", f"{class_name} ({archetype})" if archetype else class_name),
            ("Level", str(p.level)),
            ("Rooms Cleared", f"{self.stats.get('rooms_cleared', 0)}/{self.total_rooms}"),
            ("Monsters Killed", str(self.stats.get("monsters_killed", 0))),
            ("Quests Completed", str(len(p.completed_quests))),
            ("Quests Failed", str(len(p.failed_quests))),
            ("Followers Escorted", str(len(p.followers))),
            ("Items in Inventory", str(len(p.inventory))),
            ("Health", f"{p.health}/{p.max_health}"),
            ("Gold", str(p.money)),
        ]

        # Abilities/spells
        if p.abilities:
            stats_lines.append(("Abilities", ", ".join(a.name for a in p.abilities)))
        if p.spells:
            stats_lines.append(("Spells", ", ".join(s.name for s in p.spells)))

        y = panel_y + 20
        for label, value in stats_lines:
            label_surf = self.font.render(f"{label}:", True, DIM)
            value_surf = self.font.render(value[:50], True, STAT_COLOR)
            self.screen.blit(label_surf, (panel_x + 20, y))
            self.screen.blit(value_surf, (panel_x + 230, y))
            y += 32

        # Victory narrative (Bible-driven)
        if self.story_paragraph:
            y += 10
            draw_wrapped_text(self.screen, self.story_paragraph,
                              panel_x + 20, y, panel_w - 40,
                              self.small_font, STAT_COLOR)

        # Hint
        hint = self.small_font.render(
            "Enter = Main Menu  |  Esc/Q = Quit", True, DIM)
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, SCREEN_HEIGHT - 30))

