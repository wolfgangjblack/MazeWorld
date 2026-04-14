"""Unified Save/Load panel — used inside PauseView and PlayerMenuView.

Provides two sub-tabs (Save / Load) with a scrollable save file list,
new-save creation, overwrite confirmation, and delete confirmation.
"""

import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT

TITLE_COLOR = (220, 180, 60)
SELECTED_COLOR = (255, 255, 100)
UNSELECTED_COLOR = (180, 180, 180)
HEADER_COLOR = (150, 150, 200)
TAB_ACTIVE_COLOR = (255, 220, 80)
TAB_INACTIVE_COLOR = (120, 120, 120)
DISABLED_COLOR = (80, 80, 80)
STATUS_COLOR = (100, 200, 100)
ERROR_COLOR = (200, 100, 100)
CONFIRM_COLOR = (255, 180, 80)
NEW_SAVE_COLOR = (120, 200, 120)

SUB_TABS = ["Save", "Load"]


def _format_time(seconds: float) -> str:
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    if h > 0:
        return f"{h}h {m}m {s}s"
    if m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


class SaveLoadPanel:
    """Two-tab panel for save and load operations.

    Returns action dicts from ``handle_input``:
      - ``{"action": "save_new"}``
      - ``{"action": "save_overwrite", "filepath": str}``
      - ``{"action": "load", "filepath": str}``
      - ``{"action": "delete", "filepath": str}``
      - ``{"action": "back"}``
      - ``None`` (no action yet)
    """

    def __init__(self, screen, font, saves: list[dict],
                 can_save: bool = True, initial_tab: int = 0):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 24)
        self.saves = saves
        self.can_save = can_save
        self.active_tab = initial_tab
        self.selected_index = 0
        self.scroll_offset = 0
        self.max_visible = 5

        self.status_message = ""
        self.status_is_error = False

        self._confirm_mode: str | None = None
        self._confirm_filepath: str | None = None
        self._confirm_index = 0

    def set_status(self, message: str, is_error: bool = False):
        self.status_message = message
        self.status_is_error = is_error

    def refresh_saves(self, saves: list[dict]):
        self.saves = saves
        self.selected_index = min(self.selected_index, self._max_index())
        self.scroll_offset = 0

    def _max_index(self) -> int:
        """Max selectable index (includes '+ New Save' row on Save tab)."""
        count = len(self.saves)
        if self.active_tab == 0 and self.can_save:
            count += 1
        return max(0, count - 1)

    def _is_new_save_row(self) -> bool:
        return (self.active_tab == 0
                and self.can_save
                and self.selected_index == len(self.saves))

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(200)
        self.screen.blit(overlay, (0, 0))

        if self._confirm_mode:
            self._draw_confirm()
            return

        self._draw_tabs()
        self._draw_save_list()
        self._draw_status()
        self._draw_hints()

    def _draw_tabs(self):
        tab_y = 30
        tab_width = SCREEN_WIDTH // len(SUB_TABS)
        for i, name in enumerate(SUB_TABS):
            active = i == self.active_tab
            color = TAB_ACTIVE_COLOR if active else TAB_INACTIVE_COLOR
            prefix = "[ " if active else "  "
            suffix = " ]" if active else "  "
            surf = self.font.render(f"{prefix}{name}{suffix}", True, color)
            x = i * tab_width + (tab_width - surf.get_width()) // 2
            self.screen.blit(surf, (x, tab_y))

        pygame.draw.line(self.screen, (80, 80, 80),
                         (20, tab_y + 30), (SCREEN_WIDTH - 20, tab_y + 30))

    def _draw_save_list(self):
        COL_NAME = 50
        COL_CLASS = 195
        COL_LEVEL = 365
        COL_TIME = 445
        COL_DATE = 560

        headers = [("Name", COL_NAME), ("Class", COL_CLASS),
                    ("Level", COL_LEVEL), ("Time", COL_TIME), ("Saved", COL_DATE)]
        for label, col_x in headers:
            surf = self.small_font.render(label, True, HEADER_COLOR)
            self.screen.blit(surf, (col_x, 80))

        pygame.draw.line(self.screen, HEADER_COLOR,
                         (40, 100), (SCREEN_WIDTH - 40, 100))

        line_height = 50
        start_y = 110

        total_items = len(self.saves)
        has_new_row = self.active_tab == 0 and self.can_save
        if has_new_row:
            total_items += 1

        visible_start = self.scroll_offset
        visible_end = min(visible_start + self.max_visible, total_items)

        if total_items == 0:
            empty = self.font.render("No save files found.", True, DISABLED_COLOR)
            x = (SCREEN_WIDTH - empty.get_width()) // 2
            self.screen.blit(empty, (x, start_y + 40))
            return

        for vi, idx in enumerate(range(visible_start, visible_end)):
            selected = idx == self.selected_index
            y = start_y + vi * line_height

            if idx < len(self.saves):
                save = self.saves[idx]
                color = SELECTED_COLOR if selected else UNSELECTED_COLOR

                prefix = self.font.render("> " if selected else "  ", True, color)
                self.screen.blit(prefix, (30, y))

                name_s = self.font.render(save["character_name"][:16], True, color)
                self.screen.blit(name_s, (COL_NAME, y))

                cls_s = self.font.render(save["character_class"][:16], True, color)
                self.screen.blit(cls_s, (COL_CLASS, y))

                lvl_s = self.font.render(f"Rm {save['room_level']}", True, color)
                self.screen.blit(lvl_s, (COL_LEVEL, y))

                time_s = self.font.render(
                    _format_time(save["time_played_seconds"]), True, color)
                self.screen.blit(time_s, (COL_TIME, y))

                date_s = self.font.render(save["last_save_date"], True, color)
                self.screen.blit(date_s, (COL_DATE, y))

                if selected:
                    seed_s = self.small_font.render(
                        f"Seed: {save['seed']}", True, (100, 100, 100))
                    self.screen.blit(seed_s, (COL_NAME, y + 25))
            else:
                color = SELECTED_COLOR if selected else NEW_SAVE_COLOR
                prefix = "> " if selected else "  "
                surf = self.font.render(f"{prefix}+ New Save", True, color)
                self.screen.blit(surf, (30, y))

        if self.scroll_offset > 0:
            arrow = self.font.render("^ more above", True, (100, 100, 100))
            self.screen.blit(arrow, (SCREEN_WIDTH // 2 - 60, start_y - 20))
        if visible_end < total_items:
            arrow = self.font.render("v more below", True, (100, 100, 100))
            self.screen.blit(arrow, (SCREEN_WIDTH // 2 - 60,
                                     start_y + self.max_visible * line_height + 5))

    def _draw_status(self):
        if not self.status_message:
            return
        color = ERROR_COLOR if self.status_is_error else STATUS_COLOR
        surf = self.font.render(self.status_message, True, color)
        x = (SCREEN_WIDTH - surf.get_width()) // 2
        self.screen.blit(surf, (x, SCREEN_HEIGHT - 70))

    def _draw_hints(self):
        if self.active_tab == 0:
            hint = "Enter: Save  |  Del: Delete  |  Left/Right: Switch Tab  |  Esc: Back"
        else:
            hint = "Enter: Load  |  Del: Delete  |  Left/Right: Switch Tab  |  Esc: Back"
        surf = self.small_font.render(hint, True, (100, 100, 100))
        self.screen.blit(surf, (10, SCREEN_HEIGHT - 30))

    def _draw_confirm(self):
        if self._confirm_mode == "overwrite":
            prompt = "Overwrite this save?"
        elif self._confirm_mode == "delete":
            prompt = "Delete this save?"
        else:
            prompt = "Are you sure?"

        prompt_surf = self.title_font.render(prompt, True, CONFIRM_COLOR)
        x = (SCREEN_WIDTH - prompt_surf.get_width()) // 2
        self.screen.blit(prompt_surf, (x, SCREEN_HEIGHT // 2 - 60))

        options = ["Yes", "No"]
        for i, opt in enumerate(options):
            selected = i == self._confirm_index
            color = SELECTED_COLOR if selected else UNSELECTED_COLOR
            prefix = "> " if selected else "  "
            surf = self.font.render(f"{prefix}{opt}", True, color)
            ox = (SCREEN_WIDTH - surf.get_width()) // 2
            self.screen.blit(surf, (ox, SCREEN_HEIGHT // 2 + i * 40))

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_input(self, event) -> dict | None:
        if self._confirm_mode:
            return self._handle_confirm_input(event)

        if event.key == pygame.K_ESCAPE:
            return {"action": "back"}

        if event.key == pygame.K_LEFT:
            self.active_tab = (self.active_tab - 1) % len(SUB_TABS)
            self.selected_index = 0
            self.scroll_offset = 0
            self.status_message = ""
            return None
        if event.key == pygame.K_RIGHT:
            self.active_tab = (self.active_tab + 1) % len(SUB_TABS)
            self.selected_index = 0
            self.scroll_offset = 0
            self.status_message = ""
            return None

        total = len(self.saves)
        if self.active_tab == 0 and self.can_save:
            total += 1

        if event.key == pygame.K_UP:
            self.selected_index = max(0, self.selected_index - 1)
            if self.selected_index < self.scroll_offset:
                self.scroll_offset = self.selected_index
        elif event.key == pygame.K_DOWN:
            self.selected_index = min(max(0, total - 1), self.selected_index + 1)
            if self.selected_index >= self.scroll_offset + self.max_visible:
                self.scroll_offset = self.selected_index - self.max_visible + 1
        elif event.key == pygame.K_DELETE or event.key == pygame.K_BACKSPACE:
            if self.saves and self.selected_index < len(self.saves):
                self._confirm_mode = "delete"
                self._confirm_filepath = self.saves[self.selected_index]["filepath"]
                self._confirm_index = 1
            return None
        elif event.key == pygame.K_RETURN:
            return self._handle_select()
        return None

    def _handle_select(self) -> dict | None:
        if self.active_tab == 0:
            if not self.can_save:
                return None
            if self._is_new_save_row():
                return {"action": "save_new"}
            if self.saves and self.selected_index < len(self.saves):
                self._confirm_mode = "overwrite"
                self._confirm_filepath = self.saves[self.selected_index]["filepath"]
                self._confirm_index = 1
            return None
        else:
            if self.saves and self.selected_index < len(self.saves):
                save = self.saves[self.selected_index]
                return {"action": "load", "filepath": save["filepath"]}
        return None

    def _handle_confirm_input(self, event) -> dict | None:
        if event.key == pygame.K_ESCAPE:
            self._confirm_mode = None
            return None
        if event.key == pygame.K_UP or event.key == pygame.K_DOWN:
            self._confirm_index = 1 - self._confirm_index
            return None
        if event.key == pygame.K_RETURN:
            if self._confirm_index == 0:
                mode = self._confirm_mode
                filepath = self._confirm_filepath
                self._confirm_mode = None
                if mode == "overwrite":
                    return {"action": "save_overwrite", "filepath": filepath}
                elif mode == "delete":
                    return {"action": "delete", "filepath": filepath}
            else:
                self._confirm_mode = None
        return None
