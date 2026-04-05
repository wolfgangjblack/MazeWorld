import json
from src.models.items import Food, Drink, Tool, Weapon, SpellScroll, Item, ItemStats

ITEM_CLASS_MAP = {
    "food": Food,
    "drink": Drink,
    "tool": Tool,
    "weapon": Weapon,
    "spell_scroll": Weapon,  # placeholder, overridden below
}

def create_item_from_data(item_id: int, data: dict):
    item_type = data["category"].strip().lower()

    if item_type == "food":
        cls = Food
    elif item_type == "drink":
        cls = Drink
    elif item_type == "tool":
        cls = Tool
    elif item_type == "weapon":
        cls = Weapon
    elif item_type == "spell_scroll":
        cls = SpellScroll
    else:
        cls = Item

    stats_data = data.get("item_stats", {})
    stats = ItemStats(**stats_data)

    kwargs = {
        "category": data["category"],
        "name": data["name"],
        "desc": data.get("desc", ""),
        "quantity": 1,
        "item_stats": stats,
        "room_level": data.get("room_level", 1),
    }

    if cls == Weapon:
        kwargs["weapon_type"] = data.get("weapon_type", "simple")
    elif cls == SpellScroll:
        kwargs["spell_effect"] = data.get("spell_effect", "generic")

    return cls(**kwargs)

def load_json_data(file_path: str):
    with open(file_path, "r") as file:
        return json.load(file)
    