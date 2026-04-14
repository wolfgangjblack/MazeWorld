from src.registry import GameRegistry
from src.models.items import Food, Drink, Tool, Weapon, SpellScroll
from tests.conftest import requires_data


def test_singleton():
    a = GameRegistry()
    b = GameRegistry()
    assert a is b


@requires_data
def test_items_loaded(reg):
    assert len(reg.item_registry) > 0
    for item in reg.item_registry.values():
        assert isinstance(item, (Food, Drink, Tool, Weapon, SpellScroll))


def test_get_item_returns_correct_class(reg):
    for item_id, item in reg.item_registry.items():
        assert isinstance(item, (Food, Drink, Tool, Weapon, SpellScroll))
        assert reg.get_item(item_id) is item


def test_get_item_name(reg):
    for item_id, item in reg.item_registry.items():
        assert reg.get_item_name(item_id) != ""
    assert reg.get_item_name(999) == ""


def test_is_item(reg):
    for item_id in reg.item_registry:
        assert reg.is_item(item_id)
    assert not reg.is_item(0)
    assert not reg.is_item(-1)
    assert not reg.is_item(999)


@requires_data
def test_item_ids(reg):
    ids = reg.item_ids()
    assert len(ids) > 0
    assert set(ids) == set(reg.item_registry.keys())


@requires_data
def test_items_by_class(reg):
    foods = reg.items_by_class(Food)
    drinks = reg.items_by_class(Drink)
    tools = reg.items_by_class(Tool)
    assert len(foods) >= 1
    assert len(drinks) >= 1
    assert len(tools) >= 1
    assert all(isinstance(v, Food) for v in foods.values())
    assert all(isinstance(v, Drink) for v in drinks.values())
    assert all(isinstance(v, Tool) for v in tools.values())


@requires_data
def test_npc_templates(reg):
    assert len(reg.npc_templates) >= 1
    for t in reg.npc_templates:
        assert "id" in t
        assert "type" in t


