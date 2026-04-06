"""Config screen — displays all settings, editable where appropriate."""

import pygame
import config as cfg
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK

# Settings used at generation time — displayed but not editable
READONLY_SETTINGS = [
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

# Settings that can be changed at runtime
EDITABLE_SETTINGS = [
    ("GAME_MODE", "Game mode", ["online", "offline_local", "offline_static"]),
    ("LLM_BACKEND", "LLM backend", ["local", "api"]),
    ("LLM_MODEL_PATH", "LLM model path", None),
    ("ANTHROPIC_MODEL", "Anthropic model", None),
    ("IMAGE_BACKEND", "Image backend", ["local", "api"]),
    ("FAL_MODEL", "FAL model", None),
]

# Colors
TITLE_COLOR = (220, 180, 60)
LABEL_COLOR = (180, 180, 180)
VALUE_COLOR = (200, 200, 200)
READONLY_COLOR = (100, 100, 100)
SELECTED_COLOR = (255, 255, 100)
EDITABLE_VALUE_COLOR = (100, 220, 100)
EDITING_COLOR = (255, 200, 80)
SECTION_COLOR = (160, 130, 50)


class ConfigView:
    """Renders the config screen with read-only and editable settings."""

    SCROLL_VISIBLE = 14  # max visible rows before scrolling

    def __init__(self, screen, font):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 24)

        # Build flat list: each entry is (attr, label, readonly, choices)
        self.items: list[tuple[str, str, bool, list | None]] = []
        for attr, label in READONLY_SETTINGS:
            self.items.append((attr, label, True, None))
        for attr, label, choices in EDITABLE_SETTINGS:
            self.items.append((attr, label, False, choices))

        self.selected_index = 0
        self.scroll_offset = 0
        self.editing = False
        self.edit_buffer = ""

        # Track which section headers land at which row for drawing
        self._readonly_count = len(READONLY_SETTINGS)

    def _get_value(self, attr: str) -> str:
        return str(getattr(cfg, attr, ""))

    def _set_value(self, attr: str, value: str):
        """Write a new value back to the config module (runtime only)."""
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

    def draw(self):
        self.screen.fill(BLACK)
        line_h = self.font.get_linesize() + 4
        margin_left = 40
        value_x = SCREEN_WIDTH // 2 + 40

        # Title
        title = self.title_font.render("Configuration", True, TITLE_COLOR)
        self.screen.blit(title, ((SCREEN_WIDTH - title.get_width()) // 2, 20))

        y = 75

        # Section: Read-Only
        ro_header = self.small_font.render("— Generation (read-only) —", True, SECTION_COLOR)
        self.screen.blit(ro_header, (margin_left, y))
        y += 24

        visible_start = self.scroll_offset
        visible_end = self.scroll_offset + self.SCROLL_VISIBLE

        for draw_i, (attr, label, readonly, choices) in enumerate(self.items):
            if draw_i < visible_start or draw_i >= visible_end:
                continue

            # Insert editable section header
            if draw_i == self._readonly_count and visible_start <= draw_i:
                ed_header = self.small_font.render("— Runtime (editable) —", True, SECTION_COLOR)
                self.screen.blit(ed_header, (margin_left, y))
                y += 24

            is_selected = draw_i == self.selected_index
            value = self._get_value(attr)

            # Label
            label_color = SELECTED_COLOR if is_selected else LABEL_COLOR
            if readonly:
                label_color = SELECTED_COLOR if is_selected else READONLY_COLOR
            label_surf = self.font.render(label, True, label_color)
            self.screen.blit(label_surf, (margin_left, y))

            # Value
            if self.editing and is_selected:
                val_text = self.edit_buffer + "_"
                val_color = EDITING_COLOR
            elif readonly:
                val_color = READONLY_COLOR
                val_text = value
            else:
                val_color = EDITABLE_VALUE_COLOR if is_selected else VALUE_COLOR
                val_text = value
            val_surf = self.font.render(val_text, True, val_color)
            self.screen.blit(val_surf, (value_x, y))

            y += line_h

        # Footer
        if self.editing:
            hint = "Type value, Enter to confirm, Esc to cancel"
        else:
            item = self.items[self.selected_index]
            if item[2]:  # readonly
                hint = "Read-only setting (set before generation)"
            elif item[3]:  # has choices
                hint = f"Enter to cycle: {', '.join(item[3])}  |  Esc = back"
            else:
                hint = "Enter to edit  |  Esc = back"
        footer = self.small_font.render(hint, True, (120, 120, 120))
        self.screen.blit(footer, ((SCREEN_WIDTH - footer.get_width()) // 2, SCREEN_HEIGHT - 35))

    def handle_input(self, event) -> str | None:
        """Process a keydown event. Returns 'back' to return to start, or None."""
        if self.editing:
            return self._handle_editing(event)

        if event.key == pygame.K_ESCAPE:
            return "back"

        if event.key == pygame.K_UP:
            self.selected_index = max(0, self.selected_index - 1)
            self._adjust_scroll()
        elif event.key == pygame.K_DOWN:
            self.selected_index = min(len(self.items) - 1, self.selected_index + 1)
            self._adjust_scroll()
        elif event.key == pygame.K_RETURN:
            attr, label, readonly, choices = self.items[self.selected_index]
            if readonly:
                return None
            if choices:
                # Cycle through choices
                current = self._get_value(attr)
                try:
                    idx = choices.index(current)
                    next_val = choices[(idx + 1) % len(choices)]
                except ValueError:
                    next_val = choices[0]
                self._set_value(attr, next_val)
            else:
                # Enter free-text editing mode
                self.editing = True
                self.edit_buffer = self._get_value(attr)
        return None

    def _handle_editing(self, event) -> str | None:
        if event.key == pygame.K_RETURN:
            attr = self.items[self.selected_index][0]
            self._set_value(attr, self.edit_buffer)
            self.editing = False
        elif event.key == pygame.K_ESCAPE:
            self.editing = False
        elif event.key == pygame.K_BACKSPACE:
            self.edit_buffer = self.edit_buffer[:-1]
        else:
            if event.unicode and event.unicode.isprintable():
                self.edit_buffer += event.unicode
        return None

    def _adjust_scroll(self):
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + self.SCROLL_VISIBLE:
            self.scroll_offset = self.selected_index - self.SCROLL_VISIBLE + 1
