"""Shop screen view — two-column buy/sell layout for MerchantNPC interaction."""

import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK
from src.registry import registry


# Colours
BG_COLOR = (220, 210, 180)
BORDER_COLOR = (100, 80, 40)
TITLE_COLOR = (100, 60, 20)
GOLD_COLOR = (180, 150, 0)
SELECTED_COLOR = (200, 0, 0)
NORMAL_COLOR = (0, 0, 0)
DESC_COLOR = (80, 80, 80)
HEADER_COLOR = (60, 60, 60)
DIVIDER_COLOR = (150, 130, 90)
CONFIRM_BG = (40, 40, 40)
CONFIRM_TEXT = (255, 255, 100)
CONTROLS_COLOR = (60, 60, 60)


class ShopView:
    """Two-column shop: Buy (left) | Sell (right).

    handle_input() returns action dicts or strings:
      - {"action": "buy", "index": int}
      - {"action": "sell", "item_name": str}
      - "close"
      - None (no action yet)
    """

    MAX_VISIBLE = 10

    def __init__(self, screen, font, merchant_npc, player):
        self.screen = screen
        self.font = font
        self.small_font = pygame.font.Font(None, 22)
        self.title_font = pygame.font.Font(None, 40)
        self.merchant = merchant_npc
        self.player = player

        self.active_column = "buy"  # "buy" or "sell"
        self.buy_index = 0
        self.sell_index = 0
        self.buy_scroll = 0
        self.sell_scroll = 0

        # Confirm prompt state
        self.confirming = False
        self.confirm_action = None  # dict describing pending action

    @property
    def selected_index(self):
        return self.buy_index if self.active_column == "buy" else self.sell_index

    def _buy_items(self):
        return self.merchant.get_shop_items()

    def _sell_items(self):
        return self.player.get_inventory()

    def draw(self):
        # Background panel
        panel = pygame.Rect(30, 40, SCREEN_WIDTH - 60, SCREEN_HEIGHT - 80)
        pygame.draw.rect(self.screen, BG_COLOR, panel)
        pygame.draw.rect(self.screen, BORDER_COLOR, panel, 3)

        # Title and gold
        title = self.title_font.render(f"{self.merchant.name}'s Shop", True, TITLE_COLOR)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))
        gold = self.font.render(f"Gold: {self.player.money}", True, GOLD_COLOR)
        self.screen.blit(gold, (SCREEN_WIDTH - 180, 52))

        # Column layout
        mid_x = SCREEN_WIDTH // 2
        col_top = 90
        col_bottom = SCREEN_HEIGHT - 110

        # Vertical divider
        pygame.draw.line(self.screen, DIVIDER_COLOR,
                         (mid_x, col_top), (mid_x, col_bottom), 2)

        # Column headers
        buy_header_color = SELECTED_COLOR if self.active_column == "buy" else HEADER_COLOR
        sell_header_color = SELECTED_COLOR if self.active_column == "sell" else HEADER_COLOR
        bh = self.font.render("-- BUY --", True, buy_header_color)
        sh = self.font.render("-- SELL --", True, sell_header_color)
        self.screen.blit(bh, (mid_x // 2 - bh.get_width() // 2, col_top))
        self.screen.blit(sh, (mid_x + mid_x // 2 - sh.get_width() // 2, col_top))

        item_top = col_top + 28
        line_h = 38

        # Draw BUY column
        buy_items = self._buy_items()
        visible_buy = buy_items[self.buy_scroll:self.buy_scroll + self.MAX_VISIBLE]
        for i, entry in enumerate(visible_buy):
            real_idx = self.buy_scroll + i
            item = registry.get_item(entry["item_id"])
            if not item:
                continue
            selected = self.active_column == "buy" and real_idx == self.buy_index
            color = SELECTED_COLOR if selected else NORMAL_COLOR
            x = 50
            y = item_top + i * line_h

            name_surf = self.font.render(item.name, True, color)
            price_surf = self.font.render(f"{entry['price']}g", True, color)
            stock_surf = self.small_font.render(f"x{entry['stock']}", True, color)
            self.screen.blit(name_surf, (x, y))
            self.screen.blit(price_surf, (mid_x - 100, y))
            self.screen.blit(stock_surf, (mid_x - 40, y))

            if selected:
                desc = item.desc[:50] + ("..." if len(item.desc) > 50 else "")
                desc_surf = self.small_font.render(desc, True, DESC_COLOR)
                self.screen.blit(desc_surf, (x, y + 18))

        # Scroll indicators for buy
        if self.buy_scroll > 0:
            self.screen.blit(self.small_font.render("^ more ^", True, DESC_COLOR),
                             (mid_x // 2 - 25, item_top - 14))
        if self.buy_scroll + self.MAX_VISIBLE < len(buy_items):
            self.screen.blit(self.small_font.render("v more v", True, DESC_COLOR),
                             (mid_x // 2 - 25, item_top + self.MAX_VISIBLE * line_h))

        # Draw SELL column
        sell_items = self._sell_items()
        visible_sell = sell_items[self.sell_scroll:self.sell_scroll + self.MAX_VISIBLE]
        for i, (item_name, quantity) in enumerate(visible_sell):
            real_idx = self.sell_scroll + i
            selected = self.active_column == "sell" and real_idx == self.sell_index
            color = SELECTED_COLOR if selected else NORMAL_COLOR
            x = mid_x + 20
            y = item_top + i * line_h

            item_obj = self.player.inventory.get(item_name)
            sell_price = max(1, item_obj.item_stats.price // 2) if item_obj else 0

            prefix = "[E] " if self.player.equipped_weapon == item_name else ""
            name_surf = self.font.render(f"{prefix}{quantity}x {item_name}", True, color)
            self.screen.blit(name_surf, (x, y))
            if sell_price > 0:
                price_surf = self.small_font.render(f"Sell: {sell_price}g", True, color)
                self.screen.blit(price_surf, (SCREEN_WIDTH - 130, y))

            if selected and item_obj:
                desc = item_obj.desc[:50] + ("..." if len(item_obj.desc) > 50 else "")
                desc_surf = self.small_font.render(desc, True, DESC_COLOR)
                self.screen.blit(desc_surf, (x, y + 18))

        # Scroll indicators for sell
        if self.sell_scroll > 0:
            self.screen.blit(self.small_font.render("^ more ^", True, DESC_COLOR),
                             (mid_x + mid_x // 2 - 25, item_top - 14))
        if self.sell_scroll + self.MAX_VISIBLE < len(sell_items):
            self.screen.blit(self.small_font.render("v more v", True, DESC_COLOR),
                             (mid_x + mid_x // 2 - 25, item_top + self.MAX_VISIBLE * line_h))

        # Confirm prompt overlay
        if self.confirming and self.confirm_action:
            self._draw_confirm()

        # Controls bar
        if self.confirming:
            ctrl = "Enter: Confirm  |  Esc: Cancel"
        else:
            ctrl = "Left/Right: Switch column  |  Up/Down: Select  |  Enter: Buy/Sell  |  Esc: Close"
        ctrl_surf = self.small_font.render(ctrl, True, CONTROLS_COLOR)
        self.screen.blit(ctrl_surf, (SCREEN_WIDTH // 2 - ctrl_surf.get_width() // 2,
                                     SCREEN_HEIGHT - 60))

    def _draw_confirm(self):
        """Draw a confirmation prompt overlay."""
        box_w, box_h = 360, 100
        box_x = (SCREEN_WIDTH - box_w) // 2
        box_y = (SCREEN_HEIGHT - box_h) // 2
        pygame.draw.rect(self.screen, CONFIRM_BG, (box_x, box_y, box_w, box_h))
        pygame.draw.rect(self.screen, CONFIRM_TEXT, (box_x, box_y, box_w, box_h), 2)

        action = self.confirm_action
        if action["type"] == "buy":
            msg = f"Buy {action['name']} for {action['price']}g?"
        else:
            msg = f"Sell {action['name']} for {action['price']}g?"
        msg_surf = self.font.render(msg, True, CONFIRM_TEXT)
        self.screen.blit(msg_surf, (box_x + box_w // 2 - msg_surf.get_width() // 2,
                                    box_y + 20))
        hint = self.small_font.render("Enter: Yes  |  Esc: No", True, (180, 180, 180))
        self.screen.blit(hint, (box_x + box_w // 2 - hint.get_width() // 2, box_y + 60))

    def handle_input(self, event):
        """Process keydown. Returns action dict, 'close', or None."""
        if self.confirming:
            return self._handle_confirm_input(event)

        if event.key == pygame.K_ESCAPE:
            return "close"

        # Column switching
        if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            self.active_column = "sell" if self.active_column == "buy" else "buy"
            return None

        # Navigation
        if event.key == pygame.K_UP:
            self._move_selection(-1)
            return None
        if event.key == pygame.K_DOWN:
            self._move_selection(1)
            return None

        # Confirm action
        if event.key == pygame.K_RETURN:
            return self._initiate_confirm()

        return None

    def _move_selection(self, direction):
        if self.active_column == "buy":
            max_idx = max(0, len(self._buy_items()) - 1)
            self.buy_index = max(0, min(max_idx, self.buy_index + direction))
            # Scroll
            if self.buy_index < self.buy_scroll:
                self.buy_scroll = self.buy_index
            elif self.buy_index >= self.buy_scroll + self.MAX_VISIBLE:
                self.buy_scroll = self.buy_index - self.MAX_VISIBLE + 1
        else:
            max_idx = max(0, len(self._sell_items()) - 1)
            self.sell_index = max(0, min(max_idx, self.sell_index + direction))
            if self.sell_index < self.sell_scroll:
                self.sell_scroll = self.sell_index
            elif self.sell_index >= self.sell_scroll + self.MAX_VISIBLE:
                self.sell_scroll = self.sell_index - self.MAX_VISIBLE + 1

    def _initiate_confirm(self):
        """Set up the confirm prompt for the current selection."""
        if self.active_column == "buy":
            items = self._buy_items()
            if not items or self.buy_index >= len(items):
                return None
            entry = items[self.buy_index]
            item = registry.get_item(entry["item_id"])
            if not item:
                return None
            self.confirm_action = {
                "type": "buy",
                "index": self.buy_index,
                "name": item.name,
                "price": entry["price"],
            }
        else:
            inv = self._sell_items()
            if not inv or self.sell_index >= len(inv):
                return None
            item_name = inv[self.sell_index][0]
            item_obj = self.player.inventory.get(item_name)
            if not item_obj:
                return None
            sell_price = max(1, item_obj.item_stats.price // 2)
            self.confirm_action = {
                "type": "sell",
                "item_name": item_name,
                "name": item_name,
                "price": sell_price,
            }
        self.confirming = True
        return None

    def _handle_confirm_input(self, event):
        """Handle input during confirm prompt."""
        if event.key == pygame.K_ESCAPE:
            self.confirming = False
            self.confirm_action = None
            return None
        if event.key == pygame.K_RETURN:
            action = self.confirm_action
            self.confirming = False
            self.confirm_action = None
            if action["type"] == "buy":
                return {"action": "buy", "index": action["index"]}
            else:
                return {"action": "sell", "item_name": action["item_name"]}
        return None
