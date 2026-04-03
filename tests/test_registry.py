from src.registry import GameRegistry
from src.models.items import Food, Drink, Tool

EXPECTED_IDS = [200, 201, 202, 203, 300, 301, 302, 303, 400, 401, 402, 403]


def test_singleton():
    a = GameRegistry()
    b = GameRegistry()
    assert a is b


def test_items_loaded(reg):
    assert len(reg.item_registry) == 12
    for item_id in EXPECTED_IDS:
        assert item_id in reg.item_registry


def test_get_item_returns_correct_class(reg):
    assert isinstance(reg.get_item(200), Food)
    assert isinstance(reg.get_item(300), Drink)
    assert isinstance(reg.get_item(400), Tool)


def test_get_item_name(reg):
    assert reg.get_item_name(200) == "bread"
    assert reg.get_item_name(301) == "juice"
    assert reg.get_item_name(402) == "pickaxe"
    assert reg.get_item_name(999) == ""


def test_is_item(reg):
    for item_id in EXPECTED_IDS:
        assert reg.is_item(item_id)
    assert not reg.is_item(0)
    assert not reg.is_item(1)
    assert not reg.is_item(-1)
    assert not reg.is_item(999)


def test_item_ids(reg):
    ids = reg.item_ids()
    assert sorted(ids) == sorted(EXPECTED_IDS)


def test_items_by_class(reg):
    foods = reg.items_by_class(Food)
    drinks = reg.items_by_class(Drink)
    tools = reg.items_by_class(Tool)
    assert len(foods) == 4
    assert len(drinks) == 4
    assert len(tools) == 4
    assert all(isinstance(v, Food) for v in foods.values())
    assert all(isinstance(v, Drink) for v in drinks.values())
    assert all(isinstance(v, Tool) for v in tools.values())


def test_npc_templates(reg):
    assert len(reg.npc_templates) == 3
    types = {t["type"] for t in reg.npc_templates}
    assert types == {"StaticNPC", "RandomNPC", "AggressiveNPC"}
    ids = {t["id"] for t in reg.npc_templates}
    assert ids == {100, 101, 102}


def test_starter_inventory(reg):
    assert set(reg.starter_inventory.keys()) == {"bread", "water", "hammer"}
    assert isinstance(reg.starter_inventory["bread"], Food)
    assert isinstance(reg.starter_inventory["water"], Drink)
    assert isinstance(reg.starter_inventory["hammer"], Tool)
