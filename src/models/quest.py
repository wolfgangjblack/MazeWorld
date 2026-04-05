from pydantic import BaseModel, Field
from typing import Optional, List


class QuestReward(BaseModel):
    item_id: Optional[int] = None
    xp: int = 0


class Quest(BaseModel):
    """Base quest model."""
    id: str
    type: str  # "fetch" | "escort" | "delivery" | "dialogue_gated" | "combat"
    title: str
    description: str
    giver_npc_id: int
    reward: QuestReward = Field(default_factory=QuestReward)
    prerequisite_quest_id: Optional[str] = None
    status: str = "not_started"  # "not_started" | "active" | "completed" | "failed"
    portrait_prompt: Optional[str] = None
    profile_image: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class FetchQuest(Quest):
    type: str = "fetch"
    target_items: List[dict] = Field(default_factory=list)  # [{"item_id": 201, "count": 2}]

    def check_completion(self, player) -> bool:
        for req in self.target_items:
            item_id = req["item_id"]
            count = req.get("count", 1)
            held = sum(
                1 for item in player.inventory.values()
                if getattr(item, 'item_stats', None)
                and item.name  # just need the right items
            )
            found = 0
            for item in player.inventory.values():
                from src.registry import registry
                for rid, ritem in registry.item_registry.items():
                    if rid == item_id and ritem.name == item.name:
                        found += item.quantity
                        break
            if found < count:
                return False
        return True


class EscortQuest(Quest):
    type: str = "escort"
    escort_npc_id: int = 0
    target_zone: List[int] = Field(default_factory=lambda: [0, 0])

    def check_completion(self, player_x: int, player_y: int) -> bool:
        zone_x, zone_y = self.target_zone
        return (zone_x - 2 <= player_x <= zone_x + 2
                and zone_y - 2 <= player_y <= zone_y + 2)


class DeliveryQuest(Quest):
    type: str = "delivery"
    delivery_item_id: int = 0
    target_npc_id: int = 0

    def check_completion(self, talking_to_npc_id: int, player) -> bool:
        if talking_to_npc_id != self.target_npc_id:
            return False
        for item in player.inventory.values():
            from src.registry import registry
            for rid, ritem in registry.item_registry.items():
                if rid == self.delivery_item_id and ritem.name == item.name:
                    return True
        return False


class DialogueGatedQuest(Quest):
    type: str = "dialogue_gated"
    dialogue_tree: dict = Field(default_factory=dict)
    can_fail: bool = True

    def check_completion(self, dialogue_result: str) -> bool:
        return dialogue_result == "success"


class CombatQuest(Quest):
    type: str = "combat"
    target_event_id: str = ""

    def check_completion(self, event_resolved: bool) -> bool:
        return event_resolved


QUEST_TYPE_MAP = {
    "fetch": FetchQuest,
    "escort": EscortQuest,
    "delivery": DeliveryQuest,
    "dialogue_gated": DialogueGatedQuest,
    "combat": CombatQuest,
}


def create_quest_from_data(data: dict) -> Quest:
    """Construct the appropriate Quest subclass from a data dict."""
    quest_type = data.get("type", "fetch")
    cls = QUEST_TYPE_MAP.get(quest_type, Quest)
    if "reward" in data and isinstance(data["reward"], dict):
        data = dict(data)
        data["reward"] = QuestReward(**data["reward"])
    return cls(**data)
