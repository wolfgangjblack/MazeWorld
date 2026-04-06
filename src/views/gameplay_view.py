import pygame
from config import BLACK, WHITE, SCREEN_WIDTH, SCREEN_HEIGHT
from src.views.npc_view import NPCView
from src.views.maze_view import MazeView
from src.views.player_view import PlayerView
from src.views.dialogue_view import DialogueBoxView
from src.registry import registry


class GameView:
    def __init__(self, screen, font, dialogue_box):
        self.screen = screen
        self.font = font
        self.dialogue_box = dialogue_box
        self.maze_view = MazeView()
        self.npc_view = NPCView()
        self.player_view = PlayerView()
        self.dialogue_view = DialogueBoxView(screen, font)

    def draw_game(self, maze, player, npcs, inventory_active, item_message_active,
                  current_npc, player_at_item, quests=None,
                  quest_log_active=False, quest_log=None, followers=None):
        self.screen.fill(BLACK)

        escort_zones = self._get_escort_zones(quests, player) if quests else None

        if quest_log_active and quest_log:
            self.draw_quest_log(quest_log)
        elif inventory_active:
            self.draw_inventory(player)
        else:
            self.maze_view.draw_maze(self.screen, maze, escort_zones=escort_zones)

            for npc in npcs:
                self.npc_view.draw_npc(self.screen, npc)

            self.player_view.draw_player(self.screen, player)
            self.player_view.draw_hud(self.screen, player)

            # Show follower count in HUD area
            if followers:
                follower_names = ", ".join(f.name for f in followers)
                ft = self.font.render(f"Followers: {follower_names}", True, (180, 255, 180))
                self.screen.blit(ft, (10, SCREEN_HEIGHT - 70))

        if (current_npc and not item_message_active and
            not inventory_active and not self.dialogue_box.dialogue_active
            and not self.dialogue_box.event_active and not quest_log_active):
            text_surface = self.font.render("Press Enter to talk", True, WHITE)
            self.screen.blit(text_surface, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 50))

        self.draw_dialogue_and_messages(player, maze, item_message_active, player_at_item)

    def _get_escort_zones(self, quests, player):
        """Return a list of (x, y) target zones for active escort quests."""
        zones = []
        if not quests:
            return zones
        for quest in quests.values():
            if (quest.type == "escort" and quest.status == "active"
                    and quest.id in player.active_quests):
                tz = getattr(quest, 'target_zone', None)
                if tz:
                    zones.append(tuple(tz))
        return zones

    def draw_inventory(self, player):
        pygame.draw.rect(self.screen,
                         (200, 200, 200),
                         pygame.Rect(100, 100, SCREEN_WIDTH - 200, SCREEN_HEIGHT - 200))
        inventory = player.get_inventory()
        for index, (item, quantity) in enumerate(inventory):
            color = (255, 0, 0) if index == player.selected_item_index else (0, 0, 0)
            item_text = f"{quantity}x {item}"
            text_surface = self.font.render(item_text, True, color)
            self.screen.blit(text_surface, (150, 150 + index * 40))

        exit_text = self.font.render("Press 'Esc' to exit", True, (0, 0, 0))
        self.screen.blit(exit_text, (150, SCREEN_HEIGHT - 150))

    def draw_quest_log(self, quest_log):
        """Draw the quest log overlay with active/completed/failed sections."""
        panel = pygame.Rect(50, 30, SCREEN_WIDTH - 100, SCREEN_HEIGHT - 80)
        pygame.draw.rect(self.screen, (30, 30, 50), panel)
        pygame.draw.rect(self.screen, (180, 180, 200), panel, 2)

        y = 45
        title = self.font.render("QUEST LOG", True, (255, 215, 0))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, y))
        y += 40

        small_font = pygame.font.Font(None, 24)

        sections = [
            ("Active Quests", quest_log.get("active", []), (100, 255, 100)),
            ("Completed", quest_log.get("completed", []), (150, 150, 150)),
            ("Failed", quest_log.get("failed", []), (255, 80, 80)),
        ]
        for section_name, entries, color in sections:
            header = self.font.render(f"— {section_name} ({len(entries)}) —", True, color)
            self.screen.blit(header, (70, y))
            y += 30
            if not entries:
                none_text = small_font.render("  (none)", True, (120, 120, 120))
                self.screen.blit(none_text, (90, y))
                y += 22
            for entry in entries:
                # Story quests get a star
                prefix = "★ " if entry.get("is_story_quest") else "  "
                title_text = f"{prefix}{entry['title']}"
                if entry.get("type") == "multi_step" and "current_step" in entry:
                    title_text += f" [{entry['current_step']}/{entry['total_steps']}]"
                qt = small_font.render(title_text, True, color)
                self.screen.blit(qt, (90, y))
                y += 22
                if y > SCREEN_HEIGHT - 120:
                    more = small_font.render("  ... (more)", True, (120, 120, 120))
                    self.screen.blit(more, (90, y))
                    break
            y += 10

        exit_text = small_font.render("Press 'Q' or 'Esc' to close", True, (180, 180, 180))
        self.screen.blit(exit_text, (SCREEN_WIDTH // 2 - exit_text.get_width() // 2,
                                     SCREEN_HEIGHT - 60))

    def draw_dialogue_and_messages(self, player, maze, item_message_active, player_at_item):
        if self.dialogue_box.event_active:
            self.dialogue_view.draw(self.dialogue_box)
        elif item_message_active or self.dialogue_box.dialogue_active:
            self.dialogue_view.draw(self.dialogue_box)
        elif player_at_item:
            item_id = maze.grid[player.y][player.x]
            item_name = registry.get_item_name(item_id)
            prompt = f"Press 'Enter' to pick up {item_name}"
            self.dialogue_box.set_item_message(prompt)
            self.dialogue_view.draw(self.dialogue_box)
        else:
            self.dialogue_box.clear_item_message()
