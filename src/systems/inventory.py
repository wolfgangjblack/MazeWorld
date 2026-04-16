"""Inventory management system — item storage, stacking, equipping."""

from typing import Dict, Optional


class InventoryManager:
    """Manages a dictionary-based inventory with stacking and equipment.

    PlayerCharacter delegates its inventory operations to this class.
    The manager holds a reference to the inventory dict and equipped weapon
    state on the owning player.
    """

    def __init__(self, inventory: Dict[str, object], player):
        self._inventory = inventory
        self._player = player

    @property
    def inventory(self) -> Dict[str, object]:
        return self._inventory

    def add(self, item):
        """Add an item, stacking if already present."""
        if item.name in self._inventory:
            self._inventory[item.name].quantity += item.quantity
        else:
            self._inventory[item.name] = item

    def remove(self, item_name: str):
        """Remove one of an item. Deletes entry when quantity hits 0."""
        if item_name in self._inventory:
            self._inventory[item_name].quantity -= 1
            if self._inventory[item_name].quantity == 0:
                del self._inventory[item_name]

    _CATEGORY_ORDER = {"weapon": 5, "food": 1, "drink": 2, "tool": 3, "spell_scroll": 4}

    def get_list(self) -> list[tuple[str, int]]:
        """Return inventory sorted: equipped weapon first, then food/drink/tool/scroll/weapon."""
        equipped = self._player.equipped_weapon
        items = list(self._inventory.values())
        items.sort(key=lambda it: (
            0 if it.name == equipped else 1,
            self._CATEGORY_ORDER.get(it.category, 6),
            it.name,
        ))
        return [(item.name, item.quantity) for item in items]

    def use_selected(self, selected_index: int) -> str:
        """Use the item at the given index. Returns message."""
        items = list(self._inventory.values())
        if not items or selected_index >= len(items):
            return "No item to use."
        item = items[selected_index]
        from src.models.items import EscortItem, Tool, Weapon

        if isinstance(item, EscortItem):
            return item.use(self._player)
        if isinstance(item, Weapon):
            return self.equip_weapon(item.name)
        message = item.use(self._player)
        if isinstance(item, Tool):
            if item.item_stats.uses <= 0:
                self.remove(item.name)
        else:
            self.remove(item.name)
        return message

    def give_selected(self, selected_index: int) -> str:
        """Give the item at the given index. Returns message."""
        items = list(self._inventory.values())
        if not items or selected_index >= len(items):
            return "No item to give."
        item = items[selected_index]
        from src.models.items import EscortItem

        if isinstance(item, EscortItem):
            return item.give()
        message = item.give()
        self.remove(item.name)
        return message

    def equip_weapon(self, weapon_name: str) -> str:
        """Equip or unequip a weapon. Returns message."""
        from src.models.items import Weapon
        from src.models.weapon import WEAPON_CATEGORY_ACCESS, weapon_from_inventory_item

        if weapon_name not in self._inventory:
            return "You don't have that weapon."
        item = self._inventory[weapon_name]
        if not isinstance(item, Weapon):
            return f"{weapon_name} is not a weapon."
        if self._player.equipped_weapon == weapon_name:
            self._player.equipped_weapon = None
            self._player.weapon = None
            return f"You unequipped the {weapon_name}."
        archetype = self._player.player_class.archetype if self._player.player_class else "warrior"
        allowed = WEAPON_CATEGORY_ACCESS.get(archetype, {"simple"})
        if getattr(item, "weapon_category", "simple") not in allowed:
            return "Only warriors and jesters can wield martial weapons."
        self._player.equipped_weapon = weapon_name
        self._player.weapon = weapon_from_inventory_item(item)
        return f"You equipped the {weapon_name}."

    def get_equipped_weapon(self) -> Optional[object]:
        """Return the equipped Weapon object, or None."""
        from src.models.items import Weapon

        ew = self._player.equipped_weapon
        if ew and ew in self._inventory:
            item = self._inventory[ew]
            if isinstance(item, Weapon):
                return item
        self._player.equipped_weapon = None
        return None

    def pick_up_from_maze(self, maze, player_x: int, player_y: int) -> str:
        """Pick up an item at the player's grid position. Returns message."""
        from src.registry import registry

        cell_value = maze.grid[player_y][player_x]
        if registry.is_item(cell_value):
            item_template = registry.get_item(cell_value)
            item = item_template.clone()
            self.add(item)
            maze.grid[player_y][player_x] = 0
            return f"Picked up {item.name}."
        return ""

    def use_spell_scroll(self, scroll_name: str) -> str:
        """Use a spell scroll. Jesters learn the spell permanently."""
        from src.models.items import SpellScroll

        if scroll_name not in self._inventory:
            return "You don't have that scroll."
        item = self._inventory[scroll_name]
        if not isinstance(item, SpellScroll):
            return f"{scroll_name} is not a spell scroll."

        if self._player.player_class and self._player.player_class.archetype == "jester":
            if item.spell_effect not in self._player.learned_spells:
                self._player.learned_spells.append(item.spell_effect)
            self.remove(scroll_name)
            return f"You study the {scroll_name} and learn {item.spell_effect} permanently!"

        result = item.use(self._player)
        self.remove(scroll_name)
        return result
