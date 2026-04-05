import random
from pydantic import BaseModel, Field
from typing import Optional, List


class EventChoice(BaseModel):
    """A single choice in a puzzle event."""
    text: str
    stat_check: Optional[str] = None
    tool_attribute: Optional[str] = None
    dc: int = 10
    auto_success: bool = False


class Event(BaseModel):
    """Base event model placed on event tiles in the maze."""
    id: str
    type: str  # "combat" | "puzzle"
    name: str
    description: str
    portrait_prompt: Optional[str] = None
    profile_image: Optional[str] = None
    difficulty: int = 3
    resolved: bool = False

    class Config:
        arbitrary_types_allowed = True


class LootEntry(BaseModel):
    """A single entry in a loot table."""
    item_id: int
    drop_chance: float = 0.5  # 0.0 to 1.0

class CombatEvent(Event):
    type: str = "combat"
    damage_type: str = "health"  # "health" | "hunger" | "thirst"
    damage_range: List[int] = Field(default_factory=lambda: [5, 15])
    reward_item_id: Optional[int] = None
    loot_table: List[LootEntry] = Field(default_factory=list)
    money_drop: List[int] = Field(default_factory=lambda: [0, 0])  # [min, max]

    def resolve(self, dice_roll: int, player) -> dict:
        """Roll vs difficulty. Win -> reward + loot. Lose -> take damage.
        If player has an equipped weapon, add its damage roll as a modifier.
        """
        threshold = self.difficulty * 3
        weapon_bonus = 0
        weapon = player.get_equipped_weapon() if hasattr(player, 'get_equipped_weapon') else None
        if weapon:
            weapon_bonus = weapon.roll_damage()

        total = dice_roll + weapon_bonus
        if total >= threshold:
            self.resolved = True
            # Roll loot drops
            dropped_item_ids = []
            for entry in self.loot_table:
                if random.random() <= entry.drop_chance:
                    dropped_item_ids.append(entry.item_id)
            # Money drop
            money = 0
            if self.money_drop[1] > 0:
                money = random.randint(self.money_drop[0], self.money_drop[1])
            if money > 0:
                player.add_money(money)
            msg = f"You defeated the {self.name}!"
            if money > 0:
                msg += f" Found {money} gold."
            return {
                "success": True,
                "message": msg,
                "reward_item_id": self.reward_item_id,
                "loot_item_ids": dropped_item_ids,
                "money_dropped": money,
            }
        else:
            damage = random.randint(self.damage_range[0], self.damage_range[1])
            if self.damage_type == "health":
                player.health = max(0, player.health - damage)
            elif self.damage_type == "hunger":
                player.hunger = max(0, player.hunger - damage)
            elif self.damage_type == "thirst":
                player.thirst = max(0, player.thirst - damage)
            return {
                "success": False,
                "message": f"The {self.name} hits you for {damage} {self.damage_type} damage!",
                "damage": damage,
                "damage_type": self.damage_type,
            }


class PuzzleEvent(Event):
    type: str = "puzzle"
    choices: List[EventChoice] = Field(default_factory=list)
    reward_item_id: Optional[int] = None

    def resolve(self, choice_index: int, dice_roll: int, player) -> dict:
        """Apply chosen option. Stat/tool check + roll vs DC."""
        if choice_index < 0 or choice_index >= len(self.choices):
            return {"success": False, "message": "Invalid choice."}

        choice = self.choices[choice_index]

        if choice.auto_success:
            return {
                "success": True,
                "message": "You walk away safely.",
                "reward_item_id": None,
            }

        modifier = 0
        if choice.stat_check:
            stat_val = getattr(player, choice.stat_check, 50)
            modifier = stat_val // 20

        if choice.tool_attribute:
            for item in player.inventory.values():
                stats = getattr(item, 'item_stats', None)
                if stats and getattr(stats, 'attribute', None) == choice.tool_attribute:
                    modifier += 5
                    break

        total = dice_roll + modifier
        if total >= choice.dc:
            self.resolved = True
            return {
                "success": True,
                "message": f"Success! You overcame the {self.name}.",
                "reward_item_id": self.reward_item_id,
            }
        else:
            return {
                "success": False,
                "message": f"You failed to overcome the {self.name}. (Rolled {total} vs DC {choice.dc})",
            }


EVENT_TYPE_MAP = {
    "combat": CombatEvent,
    "puzzle": PuzzleEvent,
}


def create_event_from_data(data: dict) -> Event:
    """Construct the appropriate Event subclass from a data dict."""
    event_type = data.get("type", "combat")
    cls = EVENT_TYPE_MAP.get(event_type, CombatEvent)
    data = dict(data)
    if event_type == "puzzle" and "choices" in data:
        data["choices"] = [
            EventChoice(**c) if isinstance(c, dict) else c
            for c in data["choices"]
        ]
    if event_type == "combat" and "loot_table" in data:
        data["loot_table"] = [
            LootEntry(**e) if isinstance(e, dict) else e
            for e in data["loot_table"]
        ]
    return cls(**data)
