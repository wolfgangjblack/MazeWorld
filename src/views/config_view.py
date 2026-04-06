"""Config screen — two-tab layout with editable runtime settings and read-only
generation settings.  API keys are persisted to `.env` (gitignored)."""

import os
import re

import pygame
import config as cfg
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK

# ── Tab 0: Editable Config (runtime) ────────────────────────────────────────
# Each entry: (attr, label, choices | None, secret)
EDITABLE_SETTINGS: list[tuple[str, str, list | None, bool]] = [
    ("GAME_MODE", "Game mode", ["online", "offline_local", "offline_static"], False),
    ("LLM_BACKEND", "LLM backend", ["local", "api"], False),
    ("LLM_MODEL_PATH", "LLM model path", None, False),
    ("ANTHROPIC_MODEL", "Anthropic model", None, False),
    ("IMAGE_BACKEND", "Image backend", ["local", "api"], False),
    ("FAL_MODEL", "FAL model", None, False),
    ("ANTHROPIC_API_KEY", "Anthropic API key", None, True),
    ("FAL_KEY", "FAL API key", None, True),
]

# ── Tab 1: Generation Settings (read-only) ──────────────────────────────────
GENERATION_SETTINGS: list[tuple[str, str]] = [
    ("SCREEN_WIDTH", "Screen width (px)"),
    ("SCREEN_HEIGHT", "Screen height (px)"),
    ("HUD_HEIGHT", "HUD height (px)"),
    ("GRID_SIZE", "Grid cell size (px)"),
    ("MIN_HALLWAY_SIZE", "Min hallway size"),
    ("MAX_HALLWAY_SIZE", "Max hallway size"),
    ("MAZE_WIDTH", "Maze width (cells)"),
    ("MAZE_HEIGHT", "Maze height (cells)"),
    ("WORLD_SEED", "World seed"),
    ("STORY_SEED", "Story seed"),
    ("EVENT_PERCENT", "Event percent"),
    ("EVENT_DENSITY", "Event density"),
    ("NUM_FOOD", "Food items"),
    ("NUM_DRINKS", "Drink items"),
    ("NUM_TOOLS", "Tool items"),
    ("NUM_WEAPONS", "Weapon items"),
    ("NUM_SPELL_SCROLLS", "Spell scrolls"),
    ("STARTING_MONEY", "Starting money"),
]

TAB_NAMES = ["Editable Config", "Generation Settings"]

# ── Colours ──────────────────────────────────────────────────────────────────
TITLE_COLOR = (220, 180, 60)
LABEL_COLOR = (180, 180, 180)
VALUE_COLOR = (200, 200, 200)
READONLY_COLOR = (100, 100, 100)
SELECTED_COLOR = (255, 255, 100)
EDITABLE_VALUE_COLOR = (100, 220, 100)
EDITING_COLOR = (255, 200, 80)
TAB_ACTIVE_COLOR = (255, 255, 100)
TAB_INACTIVE_COLOR = (100, 100, 100)
SECRET_COLOR = (180, 100, 100)

_DOTENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env")


def _mask_secret(value: str) -> str:
    """Return a masked representation of a secret value."""
    if not value:
        return "(not set)"
    if len(value) <= 8:
        return "****"
    return f"****...{value[-4:]}"


def _update_dotenv(key: str, value: str) -> None:
    """Write *key=value* into the project `.env` file (create if needed)."""
    path = os.path.normpath(_DOTENV_PATH)
    lines: list[str] = []
    found = False
    if os.path.exists(path):
        with open(path, "r") as fh:
            lines = fh.readlines()
    pattern = re.compile(rf'^{re.escape(key)}\s*=')
    new_lines: list[str] = []
    for line in lines:
        if pattern.match(line):
            new_lines.append(f'{key}="{value}"\n')
            found = True
        else:
            new_lines.append(line)
    if not found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append(f'{key}="{value}"\n')
    with open(path, "w") as fh:
        fh.writelines(new_lines)


class ConfigView:
    """Two-tab config screen: Editable Config | Generation Settings."""

    SCROLL_VISIBLE = 12

    def __init__(self, screen, font):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 24)

        # Build per-tab item lists
        # Editable: (attr, label, choices|None, secret)
        self.editable_items = list(EDITABLE_SETTINGS)
        # Generation: (attr, label)  — always read-only
        self.generation_items = list(GENERATION_SETTINGS)

        self.active_tab = 0  # 0 = editable, 1 = generation
        self.selected_index = 0
        self.scroll_offset = 0
        self.editing = False
        self.edit_buffer = ""

    @property
    def _current_items(self):
        if self.active_tab == 0:
            return self.editable_items
        return self.generation_items

    # Keep legacy `.items` property so external code/tests that reference it
    # still work (returns the union of both lists in the old 4-tuple format).
    @property
    def items(self):
        combined = []
        for attr, label, choices, secret in self.editable_items:
            combined.append((attr, label, False, choices))
        for attr, label in self.generation_items:
            combined.append((attr, label, True, None))
        return combined

    # ── Value helpers ────────────────────────────────────────────────────────
    def _get_value(self, attr: str, secret: bool = False) -> str:
        if secret:
            return os.environ.get(attr, "")
        return str(getattr(cfg, attr, ""))

    def _get_display_value(self, attr: str, secret: bool = False) -> str:
        raw = self._get_value(attr, secret)
        if secret:
            return _mask_secret(raw)
        return raw

    def _set_value(self, attr: str, value: str, secret: bool = False):
        if secret:
            os.environ[attr] = value
            _update_dotenv(attr, value)
            return
        old = getattr(cfg, attr, None)
        if isinstance(old, int):
            try:
                setattr(cfg, attr, int(value))
            except ValueError:
                pass
        elif isinstance(old, float):
            try:
                setattr(cfg, attr, float(value))
            except ValueError:
                pass
        else:
            setattr(cfg, attr, value)

    # ── Drawing ──────────────────────────────────────────────────────────────
    def draw(self):
        self.screen.fill(BLACK)
        margin_left = 40
        value_x = SCREEN_WIDTH // 2 + 40

        # Title
        title = self.title_font.render("Configuration", True, TITLE_COLOR)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 20))

        # Tab bar
        tab_y = 65
        tab_x = margin_left
        for i, name in enumerate(TAB_NAMES):
            if i == self.active_tab:
                label = f"[ {name} ]"
                color = TAB_ACTIVE_COLOR
            else:
                label = f"  {name}  "
                color = TAB_INACTIVE_COLOR
            surf = self.font.render(label, True, color)
            self.screen.blit(surf, (tab_x, tab_y))
            tab_x += surf.get_width() + 20

        # Separator
        sep_y = tab_y + self.font.get_linesize() + 4
        pygame.draw.line(self.screen, TAB_INACTIVE_COLOR,
                         (margin_left, sep_y), (SCREEN_WIDTH - margin_left, sep_y))

        # Items
        line_h = self.font.get_linesize() + 4
        y = sep_y + 8
        items = self._current_items
        vis_start = self.scroll_offset
        vis_end = self.scroll_offset + self.SCROLL_VISIBLE

        for draw_i, item in enumerate(items):
            if draw_i < vis_start or draw_i >= vis_end:
                continue

            is_selected = draw_i == self.selected_index

            if self.active_tab == 0:
                attr, label_text, choices, secret = item
                readonly = False
            else:
                attr, label_text = item
                secret, readonly = False, True

            # Label
            if readonly:
                label_color = SELECTED_COLOR if is_selected else READONLY_COLOR
            else:
                label_color = SELECTED_COLOR if is_selected else LABEL_COLOR
            label_surf = self.font.render(label_text, True, label_color)
            self.screen.blit(label_surf, (margin_left, y))

            # Value
            if self.editing and is_selected:
                val_text = self.edit_buffer + "_"
                val_color = EDITING_COLOR
            elif readonly:
                val_text = str(getattr(cfg, attr, ""))
                val_color = READONLY_COLOR
            else:
                val_text = self._get_display_value(attr, secret)
                val_color = (SECRET_COLOR if secret
                             else EDITABLE_VALUE_COLOR if is_selected
                             else VALUE_COLOR)

            val_surf = self.font.render(val_text, True, val_color)
            self.screen.blit(val_surf, (value_x, y))
            y += line_h

        # Footer
        if self.editing:
            hint = "Type value, Enter to confirm, Esc to cancel"
        elif self.active_tab == 1:
            hint = "Left/Right: switch tab  |  Esc: back"
        else:
            item = items[self.selected_index] if items else None
            if item and len(item) >= 4 and item[2]:
                hint = f"Enter to cycle: {', '.join(item[2])}  |  Left/Right: tab  |  Esc: back"
            elif item and len(item) >= 4 and item[3]:
                hint = "Enter to edit (saved to .env)  |  Left/Right: tab  |  Esc: back"
            else:
                hint = "Enter to edit  |  Left/Right: tab  |  Esc: back"
        footer = self.small_font.render(hint, True, (120, 120, 120))
        self.screen.blit(footer, ((SCREEN_WIDTH - footer.get_width()) // 2, SCREEN_HEIGHT - 35))

    # ── Input handling ───────────────────────────────────────────────────────
    def handle_input(self, event) -> str | None:
        """Process a keydown event. Returns 'back' to return to start, or None."""
        if self.editing:
            return self._handle_editing(event)

        if event.key == pygame.K_ESCAPE:
            return "back"

        if event.key == pygame.K_LEFT:
            self._switch_tab(0)
            return None
        if event.key == pygame.K_RIGHT:
            self._switch_tab(1)
            return None

        items = self._current_items
        if not items:
            return None

        if event.key == pygame.K_UP:
            self.selected_index = max(0, self.selected_index - 1)
            self._adjust_scroll()
        elif event.key == pygame.K_DOWN:
            self.selected_index = min(len(items) - 1, self.selected_index + 1)
            self._adjust_scroll()
        elif event.key == pygame.K_RETURN:
            if self.active_tab == 1:
                return None
            attr, label, choices, secret = items[self.selected_index]
            if choices:
                current = self._get_value(attr, secret)
                try:
                    idx = choices.index(current)
                    next_val = choices[(idx + 1) % len(choices)]
                except ValueError:
                    next_val = choices[0]
                self._set_value(attr, next_val, secret)
            else:
                self.editing = True
                if secret:
                    self.edit_buffer = ""
                else:
                    self.edit_buffer = self._get_value(attr, secret)
        return None

    def _handle_editing(self, event) -> str | None:
        if event.key == pygame.K_RETURN:
            items = self._current_items
            attr = items[self.selected_index][0]
            secret = items[self.selected_index][3]
            self._set_value(attr, self.edit_buffer, secret)
            self.editing = False
        elif event.key == pygame.K_ESCAPE:
            self.editing = False
        elif event.key == pygame.K_BACKSPACE:
            self.edit_buffer = self.edit_buffer[:-1]
        else:
            if event.unicode and event.unicode.isprintable():
                self.edit_buffer += event.unicode
        return None

    def _switch_tab(self, tab: int):
        if tab != self.active_tab:
            self.active_tab = tab
            self.selected_index = 0
            self.scroll_offset = 0
            self.editing = False

    def _adjust_scroll(self):
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + self.SCROLL_VISIBLE:
            self.scroll_offset = self.selected_index - self.SCROLL_VISIBLE + 1
