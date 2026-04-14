"""Level-up screen — player picks a new ability or spell from their class pool."""

import pygame

from config import BLACK, SCREEN_HEIGHT, SCREEN_WIDTH, WHITE

GOLD = (220, 180, 60)
HIGHLIGHT = (255, 220, 50)
DIM = (150, 150, 150)
PANEL_BG = (20, 20, 40)
ABILITY_COLOR = (100, 200, 100)
SPELL_COLOR = (100, 150, 255)


class LevelUpView:
    """Displays available abilities/spells and lets the player choose one."""

    def __init__(self, screen, font, player):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 22)
        self.player = player
        self.choices = player.level_up_choices()
        self.selected = 0
        self.done = False
        self.chosen = None  # (type, choice) tuple after selection

    def handle_input(self, event) -> dict | None:
        """Returns {"action": "chosen", "type": str, "choice": obj} or None."""
        if not self.choices:
            # No choices available — skip
            return {"action": "skip"}

        if event.key == pygame.K_UP:
            self.selected = (self.selected - 1) % len(self.choices)
        elif event.key == pygame.K_DOWN:
            self.selected = (self.selected + 1) % len(self.choices)
        elif event.key == pygame.K_RETURN:
            choice_type, choice = self.choices[self.selected]
            self.chosen = (choice_type, choice)
            return {"action": "chosen", "type": choice_type, "choice": choice}
        return None

    def draw(self):
        self.screen.fill(BLACK)

        # Title
        new_level = self.player.level + 1
        title = self.title_font.render(f"Level Up! -> Level {new_level}", True, GOLD)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 40))

        subtitle = self.font.render("Choose a new ability or spell:", True, WHITE)
        self.screen.blit(subtitle, ((SCREEN_WIDTH - subtitle.get_width()) // 2, 90))

        if not self.choices:
            msg = self.font.render("No new abilities available.", True, DIM)
            self.screen.blit(msg, ((SCREEN_WIDTH - msg.get_width()) // 2, 160))
            hint = self.small_font.render("Press Enter to continue", True, DIM)
            self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, SCREEN_HEIGHT - 40))
            return

        # Choice list
        y = 130
        card_w = SCREEN_WIDTH - 80
        card_h = 60
        for i, (ctype, choice) in enumerate(self.choices):
            is_selected = i == self.selected
            x = 40
            cy = y + i * (card_h + 8)

            # Card background
            bg_color = (40, 40, 60) if is_selected else (25, 25, 35)
            pygame.draw.rect(self.screen, bg_color, (x, cy, card_w, card_h))
            border_color = HIGHLIGHT if is_selected else (60, 60, 80)
            pygame.draw.rect(self.screen, border_color, (x, cy, card_w, card_h), 2)

            # Type badge
            badge_color = ABILITY_COLOR if ctype == "ability" else SPELL_COLOR
            badge_text = "ABILITY" if ctype == "ability" else "SPELL"
            badge = self.small_font.render(badge_text, True, badge_color)
            self.screen.blit(badge, (x + 10, cy + 5))

            # Name
            prefix = "> " if is_selected else "  "
            name_color = HIGHLIGHT if is_selected else WHITE
            name = self.font.render(f"{prefix}{choice.name}", True, name_color)
            self.screen.blit(name, (x + 80, cy + 5))

            # Description
            desc = self.small_font.render(choice.description[:80], True, DIM)
            self.screen.blit(desc, (x + 80, cy + 30))

            # Cost info
            costs = []
            if hasattr(choice, 'stamina_cost') and choice.stamina_cost:
                costs.append(f"Stamina: {choice.stamina_cost}")
            if costs:
                cost_text = self.small_font.render(" | ".join(costs), True, (180, 120, 80))
                self.screen.blit(cost_text, (x + card_w - cost_text.get_width() - 10, cy + 5))

        # Hint
        hint = self.small_font.render("Arrow keys to browse, Enter to select", True, DIM)
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, SCREEN_HEIGHT - 40))
