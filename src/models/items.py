import random
from typing import Optional, Tuple

from pydantic import BaseModel

# Consumable stat scaling by room level (Phase 4)
CONSUMABLE_SCALING: dict[int, float] = {
    1: 1.0,
    2: 1.3,
    3: 1.6,
}
# Level 4+ gets 2.0x
_DEFAULT_SCALING = 2.0


def consumable_scale_factor(room_level: int) -> float:
    """Return the scaling multiplier for a given room level."""
    return CONSUMABLE_SCALING.get(room_level, _DEFAULT_SCALING)


def scale_item_stats(stats: "ItemStats", room_level: int) -> "ItemStats":
    """Return a copy of stats with stamina/health/price scaled by room level."""
    factor = consumable_scale_factor(room_level)
    return stats.model_copy(
        update={
            "stamina_value": int(stats.stamina_value * factor),
            "health_value": int(stats.health_value * factor),
            "price": int(stats.price * factor),
        }
    )


class ItemStats(BaseModel):
    stamina_value: int = 0
    health_value: int = 0
    uses: int = 1
    attribute: Optional[str] = None
    price: int = 0
    attack_dice: Optional[str] = None  # e.g. "1d6", "2d4"
    stat_modifier: Optional[str] = None  # "STR", "DEX", "INT"


class Item(BaseModel):
    """Base class for all items."""

    category: str
    name: str
    desc: str
    quantity: int = 1
    item_stats: ItemStats
    profile_image: Optional[str] = None
    portrait_prompt: Optional[str] = None
    room_level: int = 1

    def use(self):
        """Use the item."""
        return f"You used the {self.name}."

    def give(self):
        """Give the item to someone."""
        return f"You gave away the {self.name}."

    def clone(self):
        return self.model_copy(deep=True)

    def scaled_clone(self, room_level: int = 1):
        """Clone this item with stats scaled to the given room level."""
        copy = self.clone()
        copy.item_stats = scale_item_stats(copy.item_stats, room_level)
        copy.room_level = room_level
        return copy


class Food(Item):
    """Represents food items."""

    def use(self, player):
        """Feed the player. Base stats + player CON modifier."""
        con_mod = player.get_stat_mod("CON") if hasattr(player, "get_stat_mod") else 0
        base_hp = self.item_stats.health_value or 5
        base_stam = self.item_stats.stamina_value or 15
        hp_heal = max(1, base_hp + con_mod)
        stam_heal = max(1, base_stam + 2 * con_mod)
        player.health = min(player.health + hp_heal, player.max_health)
        player.stamina = min(player.stamina + stam_heal, player.max_stamina)
        return f"You ate the {self.name}. (+{hp_heal} HP, +{stam_heal} stamina)"


class Drink(Item):
    """Represents drink items."""

    def use(self, player):
        """Refresh the player. Base stats + player CON modifier."""
        con_mod = player.get_stat_mod("CON") if hasattr(player, "get_stat_mod") else 0
        base_hp = self.item_stats.health_value or 5
        base_stam = self.item_stats.stamina_value or 15
        hp_heal = max(1, base_hp + con_mod)
        stam_heal = max(1, base_stam + 2 * con_mod)
        player.health = min(player.health + hp_heal, player.max_health)
        player.stamina = min(player.stamina + stam_heal, player.max_stamina)
        return f"You drank the {self.name}. (+{hp_heal} HP, +{stam_heal} stamina)"


class Tool(Item):
    """Represents tool items.
    1. Types can be 'bludgeon', 'cutting', 'digging', 'climbing'
    2. Negative stamina_value indicates a cost of using the tool
    3. Uses is the number of times the tool can be used before it breaks.
    """

    def use(self, player):
        """Use the tool. Tools can have negative stamina values as a cost."""
        player.stamina = max(0, player.stamina + self.item_stats.stamina_value)

        # Decrement uses
        self.item_stats.uses -= 1
        if self.item_stats.uses <= 0:
            # The tool breaks
            return f"The {self.name} broke."

        return f"You used the {self.name}. It still seems useful"


class Weapon(Item):
    """Represents weapon items. Determines attack dice + stat modifier.
    Types: heavy (STR), light (DEX), simple (STR/INT).
    Categories: simple (any class) or martial (warrior/jester only).
    """

    weapon_type: str = "simple"  # "heavy", "light", "simple"
    damage_type: str = "physical"  # "slashing", "piercing", "bludgeoning"
    weapon_category: str = "simple"  # "simple", "martial"
    magic_element: Optional[str] = None  # "fire", "water", "forest", "light", "dark"
    rarity: str = "common"  # "common", "uncommon", "rare", "legendary"

    def use(self, player):
        """Equip or unequip the weapon."""
        if player.equipped_weapon == self.name:
            player.equipped_weapon = None
            return f"You unequipped the {self.name}."
        player.equipped_weapon = self.name
        return f"You equipped the {self.name}."

    def roll_damage(self) -> int:
        """Roll attack dice and return damage value."""
        dice_str = self.item_stats.attack_dice or "1d4"
        try:
            num, sides = dice_str.split("d")
            total = sum(random.randint(1, int(sides)) for _ in range(int(num)))
        except (ValueError, TypeError):
            total = random.randint(1, 4)
        return total


class SpellScroll(Item):
    """Consumable single-use spell scroll.
    Solves events/quests/puzzles. Jester class can learn permanently.
    """

    spell_effect: str = "generic"  # describes what the spell does

    def use(self, player):
        """Use the spell scroll. Consumed on use."""
        player.health = min(player.health + self.item_stats.health_value, player.max_health)
        player.stamina = min(player.stamina + self.item_stats.stamina_value, player.max_stamina)
        return f"You cast {self.name}! The scroll crumbles to dust."


class EscortItem(Item):
    """Represents an NPC being escorted. Cannot be consumed or dropped."""

    npc_id: int = 0
    target_zone: Tuple[int, int] = (0, 0)

    def use(self, player):
        return '"Are we there yet?"'

    def give(self):
        return "You can't abandon your escort!"
