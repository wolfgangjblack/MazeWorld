import json
from src.models.items import Food, Drink, Tool, Item, ItemStats

def create_item_from_data(item_id: int, data: dict):
    # data format example:
    # {
    #    "category": "Food",
    #    "name": "bread",
    #    "desc": "A loaf of bread.",
    #    "item_stats": {"nutrition_value": 20, "hydration_value":0, "health_value":0, "uses":1}
    # }

    # Normalize the type (just in case)
    item_type = data["category"].strip().lower()

    # Determine the class based on 'type'
    if item_type == "food":
        cls = Food
    elif item_type == "drink":
        cls = Drink
    elif item_type == "tool":
        cls = Tool
    else:
        cls = Item  # default fallback if type is not recognized

    # Create the ItemStats from the data
    stats_data = data.get("item_stats", {})
    stats = ItemStats(**stats_data)

    # Instantiate the item
    return cls(
        category=data["category"],  # keep the original string in case we need it
        name=data["name"],
        desc=data["desc"],
        quantity=1,
        item_stats=stats
    )

def load_json_data(file_path: str):
    with open(file_path, "r") as file:
        return json.load(file)
    