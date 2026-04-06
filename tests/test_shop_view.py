"""Tests for the ShopView UI class (non-rendering logic)."""

import pytest
import pygame

from src.views.shop_view import ShopView
from src.models.npc import MerchantNPC
from src.models.player import PlayerCharacter
from src.models.items import Food, ItemStats


@pytest.fixture(autouse=True)
def init_pygame():
    pygame.init()
    pygame.display.set_mode((800, 700))
    yield
    pygame.quit()


def _make_merchant(shop_inventory=None):
    return MerchantNPC(
        x=5, y=5, id=999, name="Test Merchant",
        job="merchant", environment="city",
        shop_inventory=shop_inventory or [],
    )


def _make_player(money=100):
    p = PlayerCharacter(x=4, y=5, money=money)
    return p


def _key_event(key):
    return pygame.event.Event(pygame.KEYDOWN, key=key)


class TestShopViewNavigation:
    def test_initial_state(self):
        merchant = _make_merchant()
        player = _make_player()
        screen = pygame.display.get_surface()
        font = pygame.font.Font(None, 28)
        view = ShopView(screen, font, merchant, player)
        assert view.active_column == "buy"
        assert view.buy_index == 0
        assert view.sell_index == 0
        assert view.confirming is False

    def test_switch_column(self):
        merchant = _make_merchant()
        player = _make_player()
        screen = pygame.display.get_surface()
        font = pygame.font.Font(None, 28)
        view = ShopView(screen, font, merchant, player)
        view.handle_input(_key_event(pygame.K_RIGHT))
        assert view.active_column == "sell"
        view.handle_input(_key_event(pygame.K_LEFT))
        assert view.active_column == "buy"

    def test_close_on_escape(self):
        merchant = _make_merchant()
        player = _make_player()
        screen = pygame.display.get_surface()
        font = pygame.font.Font(None, 28)
        view = ShopView(screen, font, merchant, player)
        result = view.handle_input(_key_event(pygame.K_ESCAPE))
        assert result == "close"

    def test_navigate_buy_items(self, reg):
        merchant = _make_merchant(shop_inventory=[
            {"item_id": 200, "price": 10, "stock": 2},
            {"item_id": 201, "price": 15, "stock": 1},
        ])
        player = _make_player()
        screen = pygame.display.get_surface()
        font = pygame.font.Font(None, 28)
        view = ShopView(screen, font, merchant, player)
        assert view.buy_index == 0
        view.handle_input(_key_event(pygame.K_DOWN))
        assert view.buy_index == 1
        view.handle_input(_key_event(pygame.K_UP))
        assert view.buy_index == 0

    def test_navigate_sell_items(self, reg):
        player = _make_player()
        food1 = Food(category="food", name="bread", desc="t",
                     item_stats=ItemStats(price=10))
        food2 = Food(category="food", name="apple", desc="t",
                     item_stats=ItemStats(price=5))
        player.inventory = {"bread": food1, "apple": food2}

        merchant = _make_merchant()
        screen = pygame.display.get_surface()
        font = pygame.font.Font(None, 28)
        view = ShopView(screen, font, merchant, player)
        view.active_column = "sell"
        view.handle_input(_key_event(pygame.K_DOWN))
        assert view.sell_index == 1


class TestShopViewConfirm:
    def test_buy_triggers_confirm(self, reg):
        merchant = _make_merchant(shop_inventory=[
            {"item_id": 200, "price": 10, "stock": 2},
        ])
        player = _make_player()
        screen = pygame.display.get_surface()
        font = pygame.font.Font(None, 28)
        view = ShopView(screen, font, merchant, player)
        # Press Enter to initiate confirm
        result = view.handle_input(_key_event(pygame.K_RETURN))
        assert result is None  # not yet confirmed
        assert view.confirming is True
        assert view.confirm_action["type"] == "buy"

    def test_confirm_buy(self, reg):
        merchant = _make_merchant(shop_inventory=[
            {"item_id": 200, "price": 10, "stock": 2},
        ])
        player = _make_player()
        screen = pygame.display.get_surface()
        font = pygame.font.Font(None, 28)
        view = ShopView(screen, font, merchant, player)
        view.handle_input(_key_event(pygame.K_RETURN))  # initiate
        result = view.handle_input(_key_event(pygame.K_RETURN))  # confirm
        assert result == {"action": "buy", "index": 0}
        assert view.confirming is False

    def test_cancel_confirm(self, reg):
        merchant = _make_merchant(shop_inventory=[
            {"item_id": 200, "price": 10, "stock": 2},
        ])
        player = _make_player()
        screen = pygame.display.get_surface()
        font = pygame.font.Font(None, 28)
        view = ShopView(screen, font, merchant, player)
        view.handle_input(_key_event(pygame.K_RETURN))  # initiate
        result = view.handle_input(_key_event(pygame.K_ESCAPE))  # cancel
        assert result is None
        assert view.confirming is False

    def test_sell_triggers_confirm(self, reg):
        player = _make_player()
        food = Food(category="food", name="bread", desc="t",
                    item_stats=ItemStats(price=20))
        player.inventory = {"bread": food}

        merchant = _make_merchant()
        screen = pygame.display.get_surface()
        font = pygame.font.Font(None, 28)
        view = ShopView(screen, font, merchant, player)
        view.active_column = "sell"
        view.handle_input(_key_event(pygame.K_RETURN))  # initiate
        assert view.confirming is True
        assert view.confirm_action["type"] == "sell"
        assert view.confirm_action["price"] == 10  # half of 20

    def test_confirm_sell(self, reg):
        player = _make_player()
        food = Food(category="food", name="bread", desc="t",
                    item_stats=ItemStats(price=20))
        player.inventory = {"bread": food}

        merchant = _make_merchant()
        screen = pygame.display.get_surface()
        font = pygame.font.Font(None, 28)
        view = ShopView(screen, font, merchant, player)
        view.active_column = "sell"
        view.handle_input(_key_event(pygame.K_RETURN))  # initiate
        result = view.handle_input(_key_event(pygame.K_RETURN))  # confirm
        assert result == {"action": "sell", "item_name": "bread"}


class TestShopViewEdgeCases:
    def test_buy_empty_shop(self, reg):
        merchant = _make_merchant(shop_inventory=[])
        player = _make_player()
        screen = pygame.display.get_surface()
        font = pygame.font.Font(None, 28)
        view = ShopView(screen, font, merchant, player)
        result = view.handle_input(_key_event(pygame.K_RETURN))
        assert result is None
        assert view.confirming is False

    def test_sell_empty_inventory(self, reg):
        merchant = _make_merchant()
        player = _make_player()
        player.inventory = {}
        screen = pygame.display.get_surface()
        font = pygame.font.Font(None, 28)
        view = ShopView(screen, font, merchant, player)
        view.active_column = "sell"
        result = view.handle_input(_key_event(pygame.K_RETURN))
        assert result is None
        assert view.confirming is False

    def test_draw_does_not_crash(self, reg):
        merchant = _make_merchant(shop_inventory=[
            {"item_id": 200, "price": 10, "stock": 2},
        ])
        player = _make_player()
        food = Food(category="food", name="bread", desc="a tasty loaf",
                    item_stats=ItemStats(price=10))
        player.inventory = {"bread": food}
        screen = pygame.display.get_surface()
        font = pygame.font.Font(None, 28)
        view = ShopView(screen, font, merchant, player)
        view.draw()  # Should not raise

    def test_navigate_past_bounds(self, reg):
        merchant = _make_merchant(shop_inventory=[
            {"item_id": 200, "price": 10, "stock": 1},
        ])
        player = _make_player()
        screen = pygame.display.get_surface()
        font = pygame.font.Font(None, 28)
        view = ShopView(screen, font, merchant, player)
        view.handle_input(_key_event(pygame.K_UP))  # Can't go below 0
        assert view.buy_index == 0
        view.handle_input(_key_event(pygame.K_DOWN))  # Only 1 item, stays at 0
        assert view.buy_index == 0
