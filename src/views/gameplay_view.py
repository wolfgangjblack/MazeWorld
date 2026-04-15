import pygame

from config import BLACK, SCREEN_HEIGHT, SCREEN_WIDTH, WHITE
from src.registry import registry
from src.views.dialogue_view import DialogueBoxView
from src.views.encounter_view import EncounterView
from src.views.maze_view import MazeView
from src.views.npc_view import NPCView
from src.views.player_view import PlayerView


class GameView:
    def __init__(self, screen, font, dialogue_box):
        self.screen = screen
        self.font = font
        self.dialogue_box = dialogue_box
        self.maze_view = MazeView()
        self.npc_view = NPCView()
        self.player_view = PlayerView()
        self.dialogue_view = DialogueBoxView(screen, font)
        self.encounter_view = EncounterView(screen, font)
        self.small_font = pygame.font.Font(None, 22)
        self.title_font = pygame.font.Font(None, 36)
        self.quest_font = pygame.font.Font(None, 24)

    def draw_game(
        self,
        maze,
        player,
        npcs,
        inventory_active,
        item_message_active,
        current_npc,
        player_at_item,
        quests=None,
        debug_reveal=False,
        shop_active=False,
        shop_npc=None,
        shop_mode="buy",
        shop_selected_index=0,
        quest_log_active=False,
        quest_log=None,
        followers=None,
        fog=None,
        visibility_radius=3,
        night_alpha=0,
        time_period=None,
        day_number=None,
        period_progress=0.0,
        item_detail_active=False,
        event_type_map=None,
        event_flag_map=None,
        dialogue_choices=None,
        dialogue_choice_index=0,
    ):
        self.screen.fill(BLACK)

        escort_zones = self._get_escort_zones(quests, player) if quests else None

        if quest_log_active and quest_log:
            self.draw_quest_log(quest_log)
        elif inventory_active:
            self.draw_inventory(player)
            if item_detail_active:
                self.draw_item_detail(player)
        else:
            self.maze_view.draw_maze(
                self.screen,
                maze,
                escort_zones=escort_zones,
                debug_reveal=debug_reveal,
                fog=fog,
                player_x=player.x,
                player_y=player.y,
                visibility_radius=visibility_radius,
                night_alpha=night_alpha,
                event_type_map=event_type_map,
                event_flag_map=event_flag_map,
            )

            for npc in npcs:
                # Only draw NPCs in revealed/visible tiles (if fog active)
                if fog and not debug_reveal:
                    if not fog.is_currently_visible(npc.x, npc.y, player.x, player.y, visibility_radius, maze=maze):
                        continue
                self.npc_view.draw_npc(self.screen, npc)

            self.player_view.draw_player(self.screen, player)
            self.player_view.draw_hud(
                self.screen, player, time_period=time_period, day_number=day_number, period_progress=period_progress
            )

            # Show follower count in HUD area
            if followers:
                follower_names = ", ".join(f.name for f in followers)
                ft = self.font.render(f"Followers: {follower_names}", True, (180, 255, 180))
                self.screen.blit(ft, (10, SCREEN_HEIGHT - 70))

        if (
            current_npc
            and not item_message_active
            and not inventory_active
            and not self.dialogue_box.dialogue_active
            and not self.dialogue_box.event_active
            and not quest_log_active
        ):
            from src.models.npc import MerchantNPC

            if isinstance(current_npc, MerchantNPC):
                text_surface = self.font.render("Enter: Talk  |  S: Shop", True, WHITE)
            else:
                text_surface = self.font.render("Press Enter to talk", True, WHITE)
            self.screen.blit(text_surface, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 50))

        if debug_reveal:
            debug_surface = self.font.render("DEBUG", True, (255, 0, 0))
            self.screen.blit(debug_surface, (SCREEN_WIDTH - debug_surface.get_width() - 10, 10))

        self.draw_dialogue_and_messages(
            player, maze, item_message_active, player_at_item,
            dialogue_choices=dialogue_choices, dialogue_choice_index=dialogue_choice_index,
        )

    def _get_escort_zones(self, quests, player):
        """Return a list of (x, y) target zones for active escort quests."""
        zones = []
        if not quests:
            return zones
        for quest in quests.values():
            if quest.type == "escort" and quest.status == "active" and quest.id in player.active_quests:
                tz = getattr(quest, "target_zone", None)
                if tz:
                    zones.append(tuple(tz))
        return zones

    def draw_inventory(self, player):
        from src.views.portrait_utils import load_portrait

        M = 20
        detail_h = 155
        title_h = 40
        ctrl_h = 25
        list_top = M + title_h + 5
        list_bottom = SCREEN_HEIGHT - M - detail_h - ctrl_h - 10
        panel_w = SCREEN_WIDTH - M * 2

        # Outer frame
        pygame.draw.rect(self.screen, (25, 25, 40), (M, M, panel_w, SCREEN_HEIGHT - M * 2))
        pygame.draw.rect(self.screen, (100, 100, 130), (M, M, panel_w, SCREEN_HEIGHT - M * 2), 2)

        # Title bar
        title = self.font.render("Inventory", True, (255, 215, 0))
        self.screen.blit(title, (M + 15, M + 10))
        money_text = self.small_font.render(f"Gold: {player.money}", True, (200, 170, 50))
        self.screen.blit(money_text, (SCREEN_WIDTH - M - money_text.get_width() - 15, M + 14))
        pygame.draw.line(self.screen, (80, 80, 100), (M, M + title_h), (SCREEN_WIDTH - M, M + title_h))

        inventory = player.get_inventory()
        row_h = 26
        half_space = 8
        stride = row_h + half_space
        visible_count = max(1, (list_bottom - list_top) // stride)
        scroll = getattr(player, "_inv_scroll", 0)
        total = len(inventory)

        for vi in range(visible_count):
            idx = scroll + vi
            if idx >= total:
                break
            item_name, quantity = inventory[idx]
            selected = idx == player.selected_item_index
            y = list_top + vi * stride

            if selected:
                sel_rect = pygame.Rect(M + 4, y - 2, panel_w - 8, row_h + 4)
                pygame.draw.rect(self.screen, (55, 55, 85), sel_rect)

            is_equipped = player.equipped_weapon == item_name
            prefix = "[E] " if is_equipped else ""
            color = (255, 255, 100) if selected else ((140, 220, 140) if is_equipped else (200, 200, 200))
            name_surf = self.font.render(f"  {prefix}{item_name}", True, color)
            self.screen.blit(name_surf, (M + 12, y + 2))

            qty_surf = self.font.render(f"x{quantity}", True, color)
            self.screen.blit(qty_surf, (SCREEN_WIDTH - M - qty_surf.get_width() - 15, y + 2))

        if total > visible_count:
            start_show = scroll + 1
            end_show = min(scroll + visible_count, total)
            ind = self.small_font.render(f"{start_show}-{end_show} / {total}", True, (100, 100, 100))
            self.screen.blit(ind, (SCREEN_WIDTH - M - ind.get_width() - 15, list_bottom + 2))

        # Separator before detail panel
        detail_y = SCREEN_HEIGHT - M - detail_h - ctrl_h - 5
        pygame.draw.line(self.screen, (80, 80, 100), (M, detail_y - 3), (SCREEN_WIDTH - M, detail_y - 3))

        # Detail panel
        det_rect = pygame.Rect(M + 4, detail_y, panel_w - 8, detail_h)
        pygame.draw.rect(self.screen, (35, 33, 48), det_rect)
        pygame.draw.rect(self.screen, (80, 80, 100), det_rect, 1)

        if inventory and 0 <= player.selected_item_index < total:
            sel_name, _ = inventory[player.selected_item_index]
            if sel_name in player.inventory:
                item_obj = player.inventory[sel_name]
                cx = M + 18
                cy = detail_y + 8
                portrait_w = 0

                portrait_surf = load_portrait(getattr(item_obj, "profile_image", None), (80, 80))
                if portrait_surf:
                    px = SCREEN_WIDTH - M - 95
                    self.screen.blit(portrait_surf, (px, cy))
                    pygame.draw.rect(self.screen, (100, 100, 130), (px, cy, 80, 80), 1)
                    portrait_w = 92

                desc_max_w = panel_w - 40 - portrait_w

                nm = self.font.render(item_obj.name, True, (255, 215, 0))
                self.screen.blit(nm, (cx, cy))
                cy += 22

                desc_lines = self._wrap_inv_text(item_obj.desc, desc_max_w)
                for dl in desc_lines[:3]:
                    ds = self.small_font.render(dl, True, (190, 190, 190))
                    self.screen.blit(ds, (cx, cy))
                    cy += 16

                cy = detail_y + detail_h - 30
                stats = item_obj.item_stats
                stat_parts = []
                if stats.attack_dice:
                    stat_parts.append(f"Dmg: {stats.attack_dice}")
                if stats.stat_modifier:
                    stat_parts.append(f"Stat: {stats.stat_modifier}")
                if stats.stamina_value:
                    stat_parts.append(f"Stam: {stats.stamina_value:+d}")
                if stats.health_value:
                    stat_parts.append(f"HP: {stats.health_value:+d}")
                if stats.attribute:
                    stat_parts.append(f"Attr: {stats.attribute}")
                if stats.uses > 1:
                    stat_parts.append(f"Uses: {stats.uses}")

                stat_str = "  |  ".join(stat_parts) if stat_parts else "No notable stats"
                stat_s = self.small_font.render(stat_str, True, (150, 200, 150))
                self.screen.blit(stat_s, (cx, cy))
                if stats.price:
                    val_s = self.small_font.render(f"Value: {stats.price}g", True, (200, 180, 100))
                    self.screen.blit(val_s, (SCREEN_WIDTH - M - val_s.get_width() - 18, cy))

        # Controls bar
        ctrl_y = SCREEN_HEIGHT - M - ctrl_h
        pygame.draw.line(self.screen, (80, 80, 100), (M, ctrl_y - 3), (SCREEN_WIDTH - M, ctrl_y - 3))
        ctrl = self.small_font.render(
            "Up/Down: Select  |  Enter: Use  |  E: Equip  |  D: Details  |  Esc: Close", True, (100, 100, 100)
        )
        self.screen.blit(ctrl, (M + 12, ctrl_y + 2))

    def _wrap_inv_text(self, text, max_w):
        words = text.split()
        lines, cur = [], ""
        for w in words:
            test = f"{cur} {w}".strip()
            if self.small_font.size(test)[0] <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

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
        if hasattr(player, "equipped_weapon") and player.equipped_weapon == item.name:
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
        if stats.stamina_value:
            stat_lines.append(f"Stamina: {stats.stamina_value:+d}")
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
        self.screen.blit(hint, (panel_x + panel_w // 2 - hint.get_width() // 2, panel_y + panel_h - 25))

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

        # Combat record section
        combat_stats = quest_log.get("combat_stats", {})
        if combat_stats and y < SCREEN_HEIGHT - 160:
            pygame.draw.line(self.screen, (80, 80, 100), (70, y), (SCREEN_WIDTH - 70, y))
            y += 8
            hdr = self.font.render("— Combat Record —", True, (150, 150, 200))
            self.screen.blit(hdr, (70, y))
            y += 28
            lines = [
                f"Combats Won: {combat_stats.get('combats_won', 0)}",
                f"Monsters Killed: {combat_stats.get('monsters_killed', 0)}",
                f"Combats Fled: {combat_stats.get('combats_fled', 0)}",
            ]
            enc = quest_log.get("encounters_cleared", 0)
            total_enc = quest_log.get("total_encounters", 0)
            if total_enc:
                lines.append(f"Encounters: {enc}/{total_enc}")
            for line in lines:
                if y > SCREEN_HEIGHT - 90:
                    break
                surf = self.quest_font.render(f"  {line}", True, (180, 200, 180))
                self.screen.blit(surf, (90, y))
                y += 22

        exit_bg = pygame.Rect(0, SCREEN_HEIGHT - 80, SCREEN_WIDTH, 40)
        pygame.draw.rect(self.screen, (30, 30, 50), exit_bg)
        pygame.draw.line(self.screen, (80, 80, 100), (50, SCREEN_HEIGHT - 80), (SCREEN_WIDTH - 50, SCREEN_HEIGHT - 80))
        exit_text = self.quest_font.render("Press 'Q' or 'Esc' to close", True, (200, 200, 210))
        self.screen.blit(exit_text, (SCREEN_WIDTH // 2 - exit_text.get_width() // 2, SCREEN_HEIGHT - 72))

    def draw_dialogue_and_messages(
        self, player, maze, item_message_active, player_at_item,
        dialogue_choices=None, dialogue_choice_index=0,
    ):
        if self.dialogue_box.event_active:
            event = self.dialogue_box.current_event
            if event and event.type in ("puzzle", "event"):
                self.encounter_view.draw(self.dialogue_box)
            else:
                self.dialogue_view.draw(self.dialogue_box)
        elif item_message_active or self.dialogue_box.dialogue_active:
            self.dialogue_view.draw(
                self.dialogue_box, choices=dialogue_choices, choice_index=dialogue_choice_index,
            )
        elif player_at_item:
            item_id = maze.grid[player.y][player.x]
            item_name = registry.get_item_name(item_id)
            prompt = f"Press 'Enter' to pick up {item_name}"
            self.dialogue_box.set_item_message(prompt)
            self.dialogue_view.draw(self.dialogue_box)
        else:
            self.dialogue_box.clear_item_message()
