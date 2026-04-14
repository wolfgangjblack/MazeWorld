import os

from config import DATA_DIR

DB_CATEGORY_NPC = 1
DB_CATEGORY_ITEM = 2
DB_CATEGORY_EVENT = 3
DB_CATEGORY_QUEST = 4
DB_CATEGORY_MONSTER = 5
DB_CATEGORY_CLASS = 6

DB_BASE = {
    "npc": DB_CATEGORY_NPC * 1000,
    "item": DB_CATEGORY_ITEM * 1000,
    "event": DB_CATEGORY_EVENT * 1000,
    "quest": DB_CATEGORY_QUEST * 1000,
    "monster": DB_CATEGORY_MONSTER * 1000,
    "class": DB_CATEGORY_CLASS * 1000,
}

DB_PATHS = {
    "npc": os.path.join(DATA_DIR, "npcs", "npcs.json"),
    "item": os.path.join(DATA_DIR, "items", "items.json"),
    "event": os.path.join(DATA_DIR, "events", "events.json"),
    "quest": os.path.join(DATA_DIR, "quests", "quests.json"),
    "monster": os.path.join(DATA_DIR, "monsters", "monsters.json"),
    "class": os.path.join(DATA_DIR, "classes", "classes.json"),
}


def next_id(category: str, db: dict | list) -> int:
    """Return the next available XYYY id for a category.

    INVARIANT: IDs must never be deleted from the DB mid-generation.
    This relies on len(db) == number of entries ever created, so
    sequential room generation produces contiguous IDs.
    """
    return DB_BASE[category] + len(db)


def category_of(entity_id: int) -> str:
    """Given an XYYY id, return the category name."""
    x = entity_id // 1000
    for name, base in DB_BASE.items():
        if base // 1000 == x:
            return name
    raise ValueError(f"Unknown category for id {entity_id}")
