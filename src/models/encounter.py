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


class CombatEvent(Event):
    type: str = "combat"
    damage_type: str = "health"  # "health" | "hunger" | "thirst"
    damage_range: List[int] = Field(default_factory=lambda: [5, 15])
    reward_item_id: Optional[int] = None

    def resolve(self, dice_roll: int, player) -> dict:
        """Roll vs difficulty. Win -> reward. Lose -> take damage."""
        threshold = self.difficulty * 3
        if dice_roll >= threshold:
            self.resolved = True
            return {
                "success": True,
                "message": f"You defeated the {self.name}!",
                "reward_item_id": self.reward_item_id,
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
    if event_type == "puzzle" and "choices" in data:
        data = dict(data)
        data["choices"] = [
            EventChoice(**c) if isinstance(c, dict) else c
            for c in data["choices"]
        ]
    return cls(**data)
