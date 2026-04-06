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
        self.small_font = pygame.font.Font(None, 22)
        self.title_font = pygame.font.Font(None, 36)
        self.quest_font = pygame.font.Font(None, 24)

    def draw_game(self, maze, player, npcs, inventory_active, item_message_active,
                  current_npc, player_at_item, quests=None, debug_reveal=False,
                  quest_log_active=False, quest_log=None, followers=None,
                  item_detail_active=False):
        self.screen.fill(BLACK)

        escort_zones = self._get_escort_zones(quests, player) if quests else None

        if quest_log_active and quest_log:
            self.draw_quest_log(quest_log)
        elif inventory_active:
            self.draw_inventory(player)
            if item_detail_active:
                self.draw_item_detail(player)
        else:
            self.maze_view.draw_maze(self.screen, maze, escort_zones=escort_zones,
                                     debug_reveal=debug_reveal)

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
            not inventory_active
            and not self.dialogue_box.dialogue_active
            and not self.dialogue_box.event_active and not quest_log_active):
            from src.models.npc import MerchantNPC
            if isinstance(current_npc, MerchantNPC):
                text_surface = self.font.render("Enter: Talk  |  S: Shop", True, WHITE)
            else:
                text_surface = self.font.render("Press Enter to talk", True, WHITE)
            self.screen.blit(text_surface, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 50))

        if debug_reveal:
            debug_surface = self.font.render("DEBUG", True, (255, 0, 0))
            self.screen.blit(debug_surface,
                             (SCREEN_WIDTH - debug_surface.get_width() - 10, 10))

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
        bg = pygame.Rect(100, 80, SCREEN_WIDTH - 200, SCREEN_HEIGHT - 160)
        pygame.draw.rect(self.screen, (200, 200, 200), bg)
        pygame.draw.rect(self.screen, (80, 80, 80), bg, 2)

        # Title and money
        title = self.font.render("INVENTORY", True, (0, 0, 0))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 90))
        money_text = self.font.render(f"Gold: {player.money}", True, (180, 150, 0))
        self.screen.blit(money_text, (SCREEN_WIDTH - 280, 90))

        inventory = player.get_inventory()
        y_start = 130
        for index, (item_name, quantity) in enumerate(inventory):
            selected = index == player.selected_item_index
            color = (255, 0, 0) if selected else (0, 0, 0)

            # Equipped indicator
            prefix = ""
            if player.equipped_weapon == item_name:
                prefix = "[E] "

            item_text = f"{prefix}{quantity}x {item_name}"
            text_surface = self.font.render(item_text, True, color)
            self.screen.blit(text_surface, (150, y_start + index * 30))

            # Show item stats on selected
            if selected and item_name in player.inventory:
                item_obj = player.inventory[item_name]
                stats = item_obj.item_stats
                detail_parts = []
                if stats.nutrition_value:
                    detail_parts.append(f"Food:{stats.nutrition_value}")
                if stats.hydration_value:
                    detail_parts.append(f"Water:{stats.hydration_value}")
                if stats.health_value:
                    detail_parts.append(f"HP:{stats.health_value}")
                if stats.attack_dice:
                    detail_parts.append(f"Dmg:{stats.attack_dice}")
                if stats.attribute:
                    detail_parts.append(f"Attr:{stats.attribute}")
                if stats.price:
                    detail_parts.append(f"Val:{stats.price}g")
                if stats.uses > 1:
                    detail_parts.append(f"Uses:{stats.uses}")
                if detail_parts:
                    detail = "  ".join(detail_parts)
                    detail_surface = self.font.render(detail, True, (80, 80, 80))
                    self.screen.blit(detail_surface, (150, y_start + index * 30 + 16))

        controls = "Up/Down: Select  |  Enter/U: Use  |  E: Equip  |  D: Details  |  Esc: Close"
        exit_text = self.font.render(controls, True, (0, 0, 0))
        self.screen.blit(exit_text, (105, SCREEN_HEIGHT - 120))

    def draw_item_detail(self, player):
        """Draw item detail popup overlay for the currently selected inventory item."""
        inventory_items = list(player.inventory.values())
        if not inventory_items or player.selected_item_index >= len(inventory_items):
            return

        item = inventory_items[player.selected_item_index]

        # Semi-transparent backdrop
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(180)
        self.screen.blit(overlay, (0, 0))

        # Detail panel
        panel_w, panel_h = 500, 380
        panel_x = (SCREEN_WIDTH - panel_w) // 2
        panel_y = (SCREEN_HEIGHT - panel_h) // 2
        pygame.draw.rect(self.screen, (50, 45, 40), (panel_x, panel_y, panel_w, panel_h))
        pygame.draw.rect(self.screen, (200, 180, 120), (panel_x, panel_y, panel_w, panel_h), 2)

        y = panel_y + 15
        content_x = panel_x + 20

        # Portrait
        portrait_rect_bottom = y
        if item.profile_image:
            try:
                import os
                if os.path.exists(item.profile_image):
                    img = pygame.image.load(item.profile_image)
                    img = pygame.transform.scale(img, (96, 96))
                    img_x = panel_x + panel_w - 116
                    self.screen.blit(img, (img_x, y))
                    portrait_rect_bottom = y + 96
            except Exception:
                pass

        # Item name
        name_color = (255, 215, 0)
        name_surf = self.title_font.render(item.name, True, name_color)
        self.screen.blit(name_surf, (content_x, y))
        y += 35

        # Category / type
        type_name = type(item).__name__
        cat_surf = self.small_font.render(f"Type: {type_name}  |  Category: {item.category}", True, (160, 160, 160))
        self.screen.blit(cat_surf, (content_x, y))
        y += 22

        # Equipped indicator
        if hasattr(player, 'equipped_weapon') and player.equipped_weapon == item.name:
            eq_surf = self.font.render("[EQUIPPED]", True, (100, 255, 100))
            self.screen.blit(eq_surf, (content_x, y))
            y += 24

        y = max(y, portrait_rect_bottom + 10)

        # Description (word-wrapped)
        y += 5
        desc_label = self.font.render("Description:", True, (200, 200, 200))
        self.screen.blit(desc_label, (content_x, y))
        y += 22
        desc_text = item.desc
        max_line_w = panel_w - 40
        words = desc_text.split()
        lines = []
        current_line = ""
        for word in words:
            test = f"{current_line} {word}".strip()
            if self.small_font.size(test)[0] <= max_line_w:
                current_line = test
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        for line in lines[:4]:
            line_surf = self.small_font.render(line, True, (220, 220, 220))
            self.screen.blit(line_surf, (content_x, y))
            y += 18

        # Stats section
        y += 10
        stats = item.item_stats
        stat_label = self.font.render("Stats:", True, (200, 200, 200))
        self.screen.blit(stat_label, (content_x, y))
        y += 24

        stat_lines = []
        if stats.attack_dice:
            stat_lines.append(f"Damage: {stats.attack_dice}")
        if stats.stat_modifier:
            stat_lines.append(f"Stat: {stats.stat_modifier}")
        if stats.nutrition_value:
            stat_lines.append(f"Nutrition: {stats.nutrition_value:+d}")
        if stats.hydration_value:
            stat_lines.append(f"Hydration: {stats.hydration_value:+d}")
        if stats.health_value:
            stat_lines.append(f"Health: {stats.health_value:+d}")
        if stats.uses > 1:
            stat_lines.append(f"Uses: {stats.uses}")
        if stats.price:
            stat_lines.append(f"Value: {stats.price}g")
        if stats.attribute:
            stat_lines.append(f"Attribute: {stats.attribute}")

        if not stat_lines:
            stat_lines.append("No notable stats.")

        # Render stats in two columns
        col_w = (panel_w - 40) // 2
        for i, stat_text in enumerate(stat_lines):
            sx = content_x + (i % 2) * col_w
            sy = y + (i // 2) * 20
            stat_surf = self.small_font.render(stat_text, True, (180, 220, 180))
            self.screen.blit(stat_surf, (sx, sy))

        # Close hint
        hint = self.small_font.render("Esc / D: Close detail", True, (120, 120, 120))
        self.screen.blit(hint, (panel_x + panel_w // 2 - hint.get_width() // 2,
                                panel_y + panel_h - 25))

    def draw_quest_log(self, quest_log):
        """Draw the quest log overlay with active/completed/failed sections."""
        panel = pygame.Rect(50, 30, SCREEN_WIDTH - 100, SCREEN_HEIGHT - 80)
        pygame.draw.rect(self.screen, (30, 30, 50), panel)
        pygame.draw.rect(self.screen, (180, 180, 200), panel, 2)

        y = 45
        title = self.font.render("QUEST LOG", True, (255, 215, 0))
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, y))
        y += 40

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
                none_text = self.quest_font.render("  (none)", True, (120, 120, 120))
                self.screen.blit(none_text, (90, y))
                y += 22
            for entry in entries:
                prefix = "★ " if entry.get("is_story_quest") else "  "
                title_text = f"{prefix}{entry['title']}"
                if entry.get("type") == "multi_step" and "current_step" in entry:
                    title_text += f" [{entry['current_step']}/{entry['total_steps']}]"
                qt = self.quest_font.render(title_text, True, color)
                self.screen.blit(qt, (90, y))
                y += 22
                if y > SCREEN_HEIGHT - 120:
                    more = self.quest_font.render("  ... (more)", True, (120, 120, 120))
                    self.screen.blit(more, (90, y))
                    break
            y += 10

        exit_text = self.quest_font.render("Press 'Q' or 'Esc' to close", True, (180, 180, 180))
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
