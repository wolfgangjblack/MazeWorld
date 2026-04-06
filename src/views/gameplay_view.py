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
                  current_npc, player_at_item, quests=None, debug_reveal=False,
                  shop_active=False, shop_npc=None, shop_mode="buy",
                  shop_selected_index=0):
        self.screen.fill(BLACK)

        escort_zones = self._get_escort_zones(quests, player) if quests else None

        if shop_active and shop_npc:
            self.draw_shop(player, shop_npc, shop_mode, shop_selected_index)
        elif inventory_active:
            self.draw_inventory(player)
        else:
            self.maze_view.draw_maze(self.screen, maze, escort_zones=escort_zones,
                                     debug_reveal=debug_reveal)

            for npc in npcs:
                self.npc_view.draw_npc(self.screen, npc)

            self.player_view.draw_player(self.screen, player)
            self.player_view.draw_hud(self.screen, player)

        if (current_npc and not item_message_active and
            not inventory_active and not shop_active
            and not self.dialogue_box.dialogue_active
            and not self.dialogue_box.event_active):
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

        controls = "Up/Down: Select  |  Enter/U: Use  |  E: Equip  |  Esc: Close"
        exit_text = self.font.render(controls, True, (0, 0, 0))
        self.screen.blit(exit_text, (120, SCREEN_HEIGHT - 120))

    def draw_shop(self, player, merchant_npc, mode, selected_index):
        """Draw the shop interface with buy/sell columns."""
        bg = pygame.Rect(50, 60, SCREEN_WIDTH - 100, SCREEN_HEIGHT - 120)
        pygame.draw.rect(self.screen, (220, 210, 180), bg)
        pygame.draw.rect(self.screen, (100, 80, 40), bg, 3)

        # Header
        shop_title = self.font.render(f"{merchant_npc.name}'s Shop", True, (100, 60, 20))
        self.screen.blit(shop_title, (SCREEN_WIDTH // 2 - shop_title.get_width() // 2, 70))
        money_text = self.font.render(f"Your Gold: {player.money}", True, (180, 150, 0))
        self.screen.blit(money_text, (SCREEN_WIDTH - 230, 70))

        # Tab indicator
        buy_color = (180, 0, 0) if mode == "buy" else (80, 80, 80)
        sell_color = (180, 0, 0) if mode == "sell" else (80, 80, 80)
        self.screen.blit(self.font.render("[B]uy", True, buy_color), (100, 100))
        self.screen.blit(self.font.render("[S]ell", True, sell_color), (200, 100))

        col_x = 80
        y_start = 130
        line_height = 28

        if mode == "buy":
            available = merchant_npc.get_shop_items()
            for i, entry in enumerate(available):
                item = registry.get_item(entry["item_id"])
                if not item:
                    continue
                selected = i == selected_index
                color = (200, 0, 0) if selected else (0, 0, 0)
                name_text = f"{item.name}"
                price_text = f"{entry['price']}g"
                stock_text = f"x{entry['stock']}"

                self.screen.blit(self.font.render(name_text, True, color),
                                 (col_x, y_start + i * line_height))
                self.screen.blit(self.font.render(price_text, True, color),
                                 (col_x + 300, y_start + i * line_height))
                self.screen.blit(self.font.render(stock_text, True, color),
                                 (col_x + 400, y_start + i * line_height))

                if selected and item:
                    desc_surface = self.font.render(item.desc[:60], True, (80, 80, 80))
                    self.screen.blit(desc_surface, (col_x, y_start + i * line_height + 14))
        else:
            # Sell mode - show player inventory
            inventory = player.get_inventory()
            for i, (item_name, quantity) in enumerate(inventory):
                selected = i == selected_index
                color = (200, 0, 0) if selected else (0, 0, 0)
                item_obj = player.inventory.get(item_name)
                sell_price = max(1, item_obj.item_stats.price // 2) if item_obj else 0

                self.screen.blit(self.font.render(f"{quantity}x {item_name}", True, color),
                                 (col_x, y_start + i * line_height))
                if sell_price > 0:
                    self.screen.blit(self.font.render(f"Sell: {sell_price}g", True, color),
                                     (col_x + 350, y_start + i * line_height))

        controls = "Up/Down: Select  |  Enter: Confirm  |  B/S: Switch Tab  |  Esc: Close"
        self.screen.blit(self.font.render(controls, True, (60, 60, 60)),
                         (80, SCREEN_HEIGHT - 90))

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
