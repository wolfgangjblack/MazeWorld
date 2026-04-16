from src.models.items import EscortItem, Food, ItemStats, Weapon
from src.models.npc import MerchantNPC
from src.models.player import PlayerCharacter
from tests.conftest import requires_data


def _make_merchant(shop_inventory=None):
    return MerchantNPC(
        x=5,
        y=5,
        id=1999,
        name="Test Merchant",
        job="merchant",
        environment="city",
        shop_inventory=shop_inventory or [],
    )


def _make_player(money=100):
    p = PlayerCharacter(x=4, y=5, money=money)
    return p


class TestMerchantNPC:
    def test_get_shop_items_empty(self):
        m = _make_merchant()
        assert m.get_shop_items() == []

    def test_get_shop_items_filters_zero_stock(self):
        m = _make_merchant(
            shop_inventory=[
                {"item_id": 2000, "price": 10, "stock": 0},
                {"item_id": 2001, "price": 15, "stock": 2},
            ]
        )
        available = m.get_shop_items()
        assert len(available) == 1
        assert available[0]["item_id"] == 2001

    @requires_data
    def test_buy_from_success(self, reg):
        m = _make_merchant(
            shop_inventory=[
                {"item_id": 2000, "price": 10, "stock": 3},
            ]
        )
        player = _make_player(money=50)
        expected_name = reg.get_item_name(2000)
        msg = m.buy_from(0, player)
        assert "Bought" in msg
        assert player.money == 40
        assert expected_name in player.inventory
        assert m.shop_inventory[0]["stock"] == 2

    def test_buy_from_insufficient_funds(self, reg):
        m = _make_merchant(
            shop_inventory=[
                {"item_id": 2000, "price": 100, "stock": 1},
            ]
        )
        player = _make_player(money=10)
        msg = m.buy_from(0, player)
        assert "enough money" in msg.lower()
        assert player.money == 10

    def test_buy_from_invalid_index(self, reg):
        m = _make_merchant(
            shop_inventory=[
                {"item_id": 2000, "price": 10, "stock": 1},
            ]
        )
        player = _make_player()
        msg = m.buy_from(5, player)
        assert "Invalid" in msg

    def test_sell_to_success(self, reg):
        m = _make_merchant()
        player = _make_player(money=0)
        food = Food(
            category="food",
            name="apple",
            desc="test",
            item_stats=ItemStats(stamina_value=10, price=20),
        )
        player.inventory = {"apple": food}
        msg = m.sell_to("apple", player)
        assert "Sold" in msg
        assert player.money == 10  # half of 20
        assert "apple" not in player.inventory

    def test_sell_to_no_item(self):
        m = _make_merchant()
        player = _make_player()
        player.inventory = {}
        msg = m.sell_to("nonexistent", player)
        assert "don't have" in msg.lower()

    def test_sell_escort_item_rejected(self):
        m = _make_merchant()
        player = _make_player()
        escort = EscortItem(
            category="escort",
            name="Bob (escort)",
            desc="test",
            item_stats=ItemStats(),
        )
        player.inventory = {"Bob (escort)": escort}
        msg = m.sell_to("Bob (escort)", player)
        assert "can't sell" in msg.lower()

    def test_sell_clears_equipped_weapon(self, reg):
        m = _make_merchant()
        player = _make_player(money=0)
        weapon = Weapon(
            category="weapon",
            name="sword",
            desc="test",
            weapon_type="simple",
            item_stats=ItemStats(attack_dice="1d6", price=30),
        )
        player.inventory = {"sword": weapon}
        player.equipped_weapon = "sword"
        m.sell_to("sword", player)
        assert player.equipped_weapon is None

    @requires_data
    def test_buy_reduces_stock(self, reg):
        m = _make_merchant(
            shop_inventory=[
                {"item_id": 2000, "price": 5, "stock": 1},
            ]
        )
        player = _make_player(money=100)
        m.buy_from(0, player)
        # Stock is now 0, so get_shop_items should be empty
        assert len(m.get_shop_items()) == 0
