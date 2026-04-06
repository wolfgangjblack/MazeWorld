"""Player menu screen — Save, Load, Quest Log, Followers tabs.

Opened with Tab key during normal gameplay (not during combat/events).
"""

import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK

TABS = ["Save/Load", "Quest Log", "Followers"]
SAVE_LOAD_ITEMS = ["Save Game", "Load Game", "Back"]

TITLE_COLOR = (220, 180, 60)
SELECTED_COLOR = (255, 255, 100)
UNSELECTED_COLOR = (180, 180, 180)
DISABLED_COLOR = (80, 80, 80)
STATUS_COLOR = (100, 200, 100)
ERROR_COLOR = (200, 100, 100)
STORY_QUEST_COLOR = (180, 140, 255)
SIDE_QUEST_COLOR = (200, 200, 200)
COMPLETED_COLOR = (120, 120, 120)
FAILED_COLOR = (180, 80, 80)
SECTION_COLOR = (160, 160, 100)
TAB_ACTIVE_COLOR = (255, 220, 80)
TAB_INACTIVE_COLOR = (120, 120, 120)
FOLLOWER_NAME_COLOR = (100, 220, 180)
FOLLOWER_DETAIL_COLOR = (180, 180, 180)


class PlayerMenuView:
    """Player menu with tabs: Save/Load, Quest Log, Followers."""

    def __init__(self, screen, font, can_save=True, has_saves=False,
                 quest_log=None, follower_info=None):
        self.screen = screen
        self.font = font
        self.title_font = pygame.font.Font(None, 48)
        self.small_font = pygame.font.Font(None, 22)
        self.active_tab = 0
        self.selected_index = 0
        self.can_save = can_save
        self.has_saves = has_saves
        self.quest_log = quest_log or {"active": [], "completed": [], "failed": []}
        self.follower_info = follower_info or []
        self.status_message = ""
        self.status_is_error = False
        # Quest log scroll
        self.quest_scroll_offset = 0
        # Follower selection
        self.follower_selected = 0

    def set_status(self, message: str, is_error: bool = False):
        self.status_message = message
        self.status_is_error = is_error

    def update_quest_log(self, quest_log: dict):
        self.quest_log = quest_log

    def update_follower_info(self, follower_info: list[dict]):
        self.follower_info = follower_info

    def draw(self):
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill(BLACK)
        overlay.set_alpha(200)
        self.screen.blit(overlay, (0, 0))

        # Draw tab bar
        self._draw_tabs()

        if self.active_tab == 0:
            self._draw_save_load()
        elif self.active_tab == 1:
            self._draw_quest_log()
        elif self.active_tab == 2:
            self._draw_followers()

        # Hint
        hint_text = "Tab/Esc: Close  |  Left/Right: Switch Tab"
        hint_surface = self.small_font.render(hint_text, True, (100, 100, 100))
        self.screen.blit(hint_surface, (10, SCREEN_HEIGHT - 30))

    def _draw_tabs(self):
        tab_y = 20
        tab_width = SCREEN_WIDTH // len(TABS)
        for i, tab_name in enumerate(TABS):
            color = TAB_ACTIVE_COLOR if i == self.active_tab else TAB_INACTIVE_COLOR
            prefix = "[ " if i == self.active_tab else "  "
            suffix = " ]" if i == self.active_tab else "  "
            text = self.font.render(f"{prefix}{tab_name}{suffix}", True, color)
            x = i * tab_width + (tab_width - text.get_width()) // 2
            self.screen.blit(text, (x, tab_y))

        # Separator line
        pygame.draw.line(self.screen, (80, 80, 80),
                         (20, tab_y + 30), (SCREEN_WIDTH - 20, tab_y + 30))

    # ------------------------------------------------------------------
    # Tab 0: Save / Load
    # ------------------------------------------------------------------

    def _draw_save_load(self):
        title_surface = self.title_font.render("Menu", True, TITLE_COLOR)
        title_x = (SCREEN_WIDTH - title_surface.get_width()) // 2
        self.screen.blit(title_surface, (title_x, 80))

        line_height = self.font.get_linesize()
        start_y = SCREEN_HEIGHT // 2 - 30

        for i, item in enumerate(SAVE_LOAD_ITEMS):
            disabled = self._is_save_load_disabled(i)
            if disabled:
                color = DISABLED_COLOR
            elif i == self.selected_index:
                color = SELECTED_COLOR
            else:
                color = UNSELECTED_COLOR

            prefix = "> " if i == self.selected_index else "  "
            label = item
            if disabled:
                if item == "Save Game":
                    label += " (in combat)"
                elif item == "Load Game":
                    label += " (no saves)"
            text_surface = self.font.render(f"{prefix}{label}", True, color)
            text_x = (SCREEN_WIDTH - text_surface.get_width()) // 2
            self.screen.blit(text_surface, (text_x, start_y + i * (line_height + 10)))

        if self.status_message:
            msg_color = ERROR_COLOR if self.status_is_error else STATUS_COLOR
            msg_surface = self.font.render(self.status_message, True, msg_color)
            msg_x = (SCREEN_WIDTH - msg_surface.get_width()) // 2
            self.screen.blit(
                msg_surface,
                (msg_x, start_y + len(SAVE_LOAD_ITEMS) * (line_height + 10) + 20),
            )

    def _is_save_load_disabled(self, index: int) -> bool:
        item = SAVE_LOAD_ITEMS[index]
        if item == "Save Game" and not self.can_save:
            return True
        if item == "Load Game" and not self.has_saves:
            return True
        return False

    # ------------------------------------------------------------------
    # Tab 1: Quest Log
    # ------------------------------------------------------------------

    def _draw_quest_log(self):
        title_surface = self.title_font.render("Quest Log", True, TITLE_COLOR)
        title_x = (SCREEN_WIDTH - title_surface.get_width()) // 2
        self.screen.blit(title_surface, (title_x, 80))

        y = 130
        margin = 40
        max_y = SCREEN_HEIGHT - 60
        line_h = self.small_font.get_linesize() + 4

        sections = [
            ("Active Quests", self.quest_log.get("active", []), STATUS_COLOR),
            ("Completed", self.quest_log.get("completed", []), COMPLETED_COLOR),
            ("Failed", self.quest_log.get("failed", []), FAILED_COLOR),
        ]

        for section_name, quests, default_color in sections:
            if y > max_y:
                break

            # Section header
            header = self.font.render(f"— {section_name} ({len(quests)}) —", True, SECTION_COLOR)
            self.screen.blit(header, (margin, y))
            y += line_h + 4

            if not quests:
                empty = self.small_font.render("  (none)", True, DISABLED_COLOR)
                self.screen.blit(empty, (margin + 10, y))
                y += line_h
                continue

            for quest in quests:
                if y > max_y:
                    more = self.small_font.render("  (more...)", True, DISABLED_COLOR)
                    self.screen.blit(more, (margin + 10, y - line_h))
                    break

                is_story = quest.get("is_story_quest", False)
                prefix = "\u2605 " if is_story else "  "
                color = STORY_QUEST_COLOR if is_story else default_color

                title = quest.get("title", "Unknown")
                # Multi-step progress
                if quest.get("type") == "multi_step" and "current_step" in quest:
                    step = quest["current_step"]
                    total = quest.get("total_steps", 0)
                    title += f"  [{step}/{total}]"

                title_surface = self.small_font.render(f"{prefix}{title}", True, color)
                self.screen.blit(title_surface, (margin + 10, y))
                y += line_h

                # Show description for active quests
                if section_name == "Active Quests":
                    desc = quest.get("description", "")
                    # Show current objective for multi-step
                    if "current_objective" in quest:
                        desc = f"Current: {quest['current_objective']}"
                    if desc:
                        # Truncate long descriptions
                        if len(desc) > 70:
                            desc = desc[:67] + "..."
                        desc_surface = self.small_font.render(f"    {desc}", True, DISABLED_COLOR)
                        self.screen.blit(desc_surface, (margin + 10, y))
                        y += line_h

            y += 6  # spacing between sections

    # ------------------------------------------------------------------
    # Tab 2: Followers
    # ------------------------------------------------------------------

    def _draw_followers(self):
        title_surface = self.title_font.render("Followers", True, TITLE_COLOR)
        title_x = (SCREEN_WIDTH - title_surface.get_width()) // 2
        self.screen.blit(title_surface, (title_x, 80))

        y = 130
        margin = 40
        line_h = self.font.get_linesize() + 4

        if not self.follower_info:
            empty = self.font.render("No followers in your party.", True, DISABLED_COLOR)
            empty_x = (SCREEN_WIDTH - empty.get_width()) // 2
            self.screen.blit(empty, (empty_x, SCREEN_HEIGHT // 2 - 20))
            return

        count_text = self.small_font.render(
            f"({len(self.follower_info)}/{2} slots)", True, DISABLED_COLOR)
        self.screen.blit(count_text, (SCREEN_WIDTH - margin - count_text.get_width(), 80))

        for i, info in enumerate(self.follower_info):
            is_selected = (i == self.follower_selected)
            prefix = "> " if is_selected else "  "

            # Name
            name_color = SELECTED_COLOR if is_selected else FOLLOWER_NAME_COLOR
            name_surface = self.font.render(
                f"{prefix}{info['name']}", True, name_color)
            self.screen.blit(name_surface, (margin, y))
            y += line_h

            # Quest summary
            if info.get("quest_summary"):
                quest_surface = self.small_font.render(
                    f"    Quest: {info['quest_summary']}", True, FOLLOWER_DETAIL_COLOR)
                self.screen.blit(quest_surface, (margin, y))
                y += line_h - 2

            # Destination
            dest = info.get("destination_room", 0)
            dest_text = f"Room {dest}" if dest > 0 else "This room"
            dest_surface = self.small_font.render(
                f"    Destination: {dest_text}", True, FOLLOWER_DETAIL_COLOR)
            self.screen.blit(dest_surface, (margin, y))
            y += line_h - 2

            # Personality
            if info.get("personality"):
                pers_surface = self.small_font.render(
                    f"    Personality: {info['personality'][:50]}", True, FOLLOWER_DETAIL_COLOR)
                self.screen.blit(pers_surface, (margin, y))
                y += line_h - 2

            y += 10  # spacing between followers

        # Talk hint
        if self.follower_info:
            talk_hint = self.small_font.render(
                "Enter: Talk to selected follower", True, (100, 100, 100))
            self.screen.blit(talk_hint, (margin, SCREEN_HEIGHT - 60))

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    def handle_input(self, event) -> str | None:
        """Process keydown. Returns action string or None.

        Actions: 'save', 'load', 'back', 'talk_follower_N' (N = index).
        """
        if event.key in (pygame.K_TAB, pygame.K_ESCAPE):
            return "back"

        # Tab switching
        if event.key == pygame.K_LEFT:
            self.active_tab = (self.active_tab - 1) % len(TABS)
            self.selected_index = 0
            self.follower_selected = 0
            return None
        if event.key == pygame.K_RIGHT:
            self.active_tab = (self.active_tab + 1) % len(TABS)
            self.selected_index = 0
            self.follower_selected = 0
            return None

        # Tab-specific input
        if self.active_tab == 0:
            return self._handle_save_load_input(event)
        elif self.active_tab == 1:
            return self._handle_quest_log_input(event)
        elif self.active_tab == 2:
            return self._handle_follower_input(event)
        return None

    def _handle_save_load_input(self, event) -> str | None:
        if event.key == pygame.K_UP:
            self.selected_index = (self.selected_index - 1) % len(SAVE_LOAD_ITEMS)
        elif event.key == pygame.K_DOWN:
            self.selected_index = (self.selected_index + 1) % len(SAVE_LOAD_ITEMS)
        elif event.key == pygame.K_RETURN:
            if self._is_save_load_disabled(self.selected_index):
                return None
            selected = SAVE_LOAD_ITEMS[self.selected_index]
            if selected == "Save Game":
                return "save"
            elif selected == "Load Game":
                return "load"
            elif selected == "Back":
                return "back"
        return None

    def _handle_quest_log_input(self, event) -> str | None:
        # Quest log is read-only; Up/Down for scroll would go here
        return None

    def _handle_follower_input(self, event) -> str | None:
        if not self.follower_info:
            return None
        if event.key == pygame.K_UP:
            self.follower_selected = max(0, self.follower_selected - 1)
        elif event.key == pygame.K_DOWN:
            self.follower_selected = min(
                len(self.follower_info) - 1, self.follower_selected + 1)
        elif event.key == pygame.K_RETURN:
            return f"talk_follower_{self.follower_selected}"
        return None
