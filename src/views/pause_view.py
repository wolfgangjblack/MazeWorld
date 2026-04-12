"""Pause screen — game menu overlay with navigation to all game systems."""

import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK

TITLE_COLOR = (220, 180, 60)
SELECTED_COLOR = (255, 255, 100)
UNSELECTED_COLOR = (180, 180, 180)
DISABLED_COLOR = (80, 80, 80)
TEXT_COLOR = (200, 200, 200)

MENU_ITEMS = [
    "Inventory",
    "Rest",
    "Status",
    "Spells/Abilities",
    "Quest Log",
    "Story Recap",
    "Save/Load",
    "Controls",
    "Start",
    "Exit Game",
]

CONTROLS_TEXT = [
    "Arrow Keys  -  Move",
    "Enter       -  Interact / Pick up",
    "Esc         -  Game Menu (resumes on Esc)",
    "I           -  Inventory",
    "P           -  Player Status",
    "S           -  Spells/Abilities (or Shop near merchant)",
    "Q           -  Quest Log",
    "B           -  Story Recap",
    "R           -  Rest",
    "F1          -  Toggle debug view",
    "",
    "Combat:",
    "Arrows      -  Navigate menu / targets",
    "Enter       -  Confirm action",
    "Esc         -  Back",
    "PageUp/Down -  Scroll combat log",
]


class PauseView:
    """Pause overlay with access to all game menus."""

    def __init__(self, screen, font, can_save=True, has_saves=False):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 22)
        self.selected_index = 0
        self.can_save = can_save
        self.has_saves = has_saves
        self.showing_controls = False
        self.showing_save_load = False
        self.save_load_index = 0
        self.status_message = ""
        self.status_is_error = False

    def set_status(self, message: str, is_error: bool = False):
        self.status_message = message
        self.status_is_error = is_error

    def draw(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill(BLACK)
        overlay.set_alpha(200)
        self.screen.blit(overlay, (0, 0))

        if self.showing_controls:
            self._draw_controls()
            return

        if self.showing_save_load:
            self._draw_save_load()
            return

        title = self.title_font.render("PAUSED", True, TITLE_COLOR)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 30))

        line_height = self.small_font.get_linesize()
        total_menu_h = len(MENU_ITEMS) * (line_height + 6)
        start_y = max(80, (SCREEN_HEIGHT - total_menu_h) // 2 - 20)

        for i, item in enumerate(MENU_ITEMS):
            disabled = self._is_disabled(item)
            if disabled:
                color = DISABLED_COLOR
            elif i == self.selected_index:
                color = SELECTED_COLOR
            else:
                color = UNSELECTED_COLOR

            prefix = "> " if i == self.selected_index else "  "
            label = item
            if disabled:
                label += " (unavailable)"
            surf = self.small_font.render(f"{prefix}{label}", True, color)
            self.screen.blit(surf, ((SCREEN_WIDTH - surf.get_width()) // 2,
                                    start_y + i * (line_height + 6)))

        if self.status_message:
            color = (200, 100, 100) if self.status_is_error else (100, 200, 100)
            msg = self.small_font.render(self.status_message, True, color)
            self.screen.blit(msg, ((SCREEN_WIDTH - msg.get_width()) // 2,
                                   start_y + len(MENU_ITEMS) * (line_height + 6) + 10))

    def _is_disabled(self, item: str) -> bool:
        if item == "Save/Load" and not self.can_save and not self.has_saves:
            return True
        return False

    def _draw_controls(self):
        title = self.title_font.render("CONTROLS", True, TITLE_COLOR)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 60))

        y = 120
        for line in CONTROLS_TEXT:
            if not line:
                y += 10
                continue
            surf = self.small_font.render(line, True, TEXT_COLOR)
            self.screen.blit(surf, (SCREEN_WIDTH // 2 - 150, y))
            y += 24

        hint = self.small_font.render("Press Esc to go back", True, (120, 120, 120))
        self.screen.blit(hint, ((SCREEN_WIDTH - hint.get_width()) // 2, SCREEN_HEIGHT - 40))

    def _draw_save_load(self):
        title = self.title_font.render("SAVE / LOAD", True, TITLE_COLOR)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 60))

        options = []
        if self.can_save:
            options.append(("Save Game", "save"))
        if self.has_saves:
            options.append(("Load Game", "load"))
        options.append(("Back", "back"))

        y = SCREEN_HEIGHT // 2 - len(options) * 15
        for i, (label, _) in enumerate(options):
            color = SELECTED_COLOR if i == self.save_load_index else UNSELECTED_COLOR
            prefix = "> " if i == self.save_load_index else "  "
            surf = self.small_font.render(f"{prefix}{label}", True, color)
            self.screen.blit(surf, ((SCREEN_WIDTH - surf.get_width()) // 2, y + i * 30))

    def handle_input(self, event) -> str | None:
        """Returns action string or None."""
        if self.showing_controls:
            if event.key == pygame.K_ESCAPE:
                self.showing_controls = False
            return None

        if self.showing_save_load:
            return self._handle_save_load_input(event)

        if event.key == pygame.K_ESCAPE:
            return "resume"

        if event.key == pygame.K_UP:
            self.selected_index = (self.selected_index - 1) % len(MENU_ITEMS)
        elif event.key == pygame.K_DOWN:
            self.selected_index = (self.selected_index + 1) % len(MENU_ITEMS)
        elif event.key == pygame.K_RETURN:
            selected = MENU_ITEMS[self.selected_index]
            if selected == "Inventory":
                return "inventory"
            if selected == "Rest":
                return "rest"
            if selected == "Status":
                return "status"
            if selected == "Spells/Abilities":
                return "spells"
            if selected == "Quest Log":
                return "quest_log"
            if selected == "Story Recap":
                return "story"
            if selected == "Save/Load":
                self.showing_save_load = True
                self.save_load_index = 0
                return None
            if selected == "Controls":
                self.showing_controls = True
                return None
            if selected == "Start":
                return "quit_to_start"
            if selected == "Exit Game":
                return "exit_game"
        return None

    def _handle_save_load_input(self, event) -> str | None:
        options = []
        if self.can_save:
            options.append("save")
        if self.has_saves:
            options.append("load")
        options.append("back")

        if event.key == pygame.K_ESCAPE:
            self.showing_save_load = False
            return None
        if event.key == pygame.K_UP:
            self.save_load_index = (self.save_load_index - 1) % len(options)
        elif event.key == pygame.K_DOWN:
            self.save_load_index = (self.save_load_index + 1) % len(options)
        elif event.key == pygame.K_RETURN:
            action = options[self.save_load_index]
            if action == "back":
                self.showing_save_load = False
                return None
            self.showing_save_load = False
            return action
        return None
