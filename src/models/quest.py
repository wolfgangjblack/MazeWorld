from typing import List, Optional

from pydantic import BaseModel, Field


class QuestReward(BaseModel):
    item_id: Optional[int] = None
    # TODO: No XP/level-progression system exists yet. Level-ups happen
    # automatically on room transitions. Wire this up if an XP system is added.
    xp: int = 0
    money: int = 0
    story_info: Optional[str] = None
    door_reveal: bool = False


class QuestFailurePenalty(BaseModel):
    hp_damage: int = 0
    stamina_damage: int = 0


class Quest(BaseModel):
    """Base quest model."""

    id: int
    type: str  # "fetch" | "escort" | "delivery" | "dialogue" | "combat" | "multi_step"
    title: str
    description: str
    giver_npc_id: int
    room_id: str = ""
    is_story_quest: bool = False
    reward: QuestReward = Field(default_factory=QuestReward)
    failure_penalty: QuestFailurePenalty = Field(default_factory=QuestFailurePenalty)
    prerequisite_quest_id: Optional[int] = None
    status: str = "not_started"  # "not_started" | "active" | "completed" | "failed"
    time_gate: Optional[str] = None  # "night" | "day" | None
    portrait_prompt: Optional[str] = None
    profile_image: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

    def apply_failure_penalty(self, player) -> str:
        """Apply failure penalties to the player. Returns description of what happened."""
        msgs = []
        if self.failure_penalty.hp_damage > 0:
            player.health = max(0, player.health - self.failure_penalty.hp_damage)
            msgs.append(f"Lost {self.failure_penalty.hp_damage} HP")
        if self.failure_penalty.stamina_damage > 0:
            player.stamina = max(0, player.stamina - self.failure_penalty.stamina_damage)
            msgs.append(f"Lost {self.failure_penalty.stamina_damage} stamina")
        return ", ".join(msgs) if msgs else ""


class FetchQuest(Quest):
    type: str = "fetch"
    target_items: List[dict] = Field(default_factory=list)  # [{"item_id": 201, "count": 2}]

    def check_completion(self, player) -> bool:
        for req in self.target_items:
            item_id = req["item_id"]
            count = req.get("count", 1)
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
    destination_room: int = 0  # 0 = same room, 1 = next room

    def check_completion(self, player_x: int, player_y: int) -> bool:
        zone_x, zone_y = self.target_zone
        return zone_x - 2 <= player_x <= zone_x + 2 and zone_y - 2 <= player_y <= zone_y + 2


class DeliveryQuest(Quest):
    type: str = "delivery"
    delivery_item_id: int = 0
    target_npc_id: int = 0
    destination_room: int = 0

    def check_completion(self, talking_to_npc_id: int, player) -> bool:
        if talking_to_npc_id != self.target_npc_id:
            return False
        for item in player.inventory.values():
            from src.registry import registry

            for rid, ritem in registry.item_registry.items():
                if rid == self.delivery_item_id and ritem.name == item.name:
                    return True
        return False


class DialogueQuest(Quest):
    type: str = "dialogue"
    dc: int = 10  # CHA check difficulty class
    dialogue_tree: dict = Field(default_factory=dict)
    can_retry: bool = True
    can_fail: bool = True

    def check_completion_cha(self, player, roll: int) -> bool:
        """CHA-based DC check. roll = 1d20 + CHA modifier."""
        cha_mod = player.get_stat_modifier("CHA") if hasattr(player, "get_stat_modifier") else 0
        return (roll + cha_mod) >= self.dc

    def check_completion(self, dialogue_result: str) -> bool:
        return dialogue_result == "success"


class CombatQuest(Quest):
    type: str = "combat"
    target_event_id: int = 0
    target_monster_name: Optional[str] = None

    def check_completion(self, event_resolved: bool) -> bool:
        return event_resolved

    def check_already_cleared(self, resolved_events: dict) -> bool:
        """Kill quests are completable out of order — if encounter already cleared."""
        event = resolved_events.get(self.target_event_id)
        if event and getattr(event, "resolved", False):
            return True
        return False


class MultiStepQuest(Quest):
    type: str = "multi_step"
    sub_quest_ids: List[int] = Field(default_factory=list)
    current_step: int = 0

    def get_current_sub_quest_id(self) -> Optional[int]:
        if self.current_step < len(self.sub_quest_ids):
            return self.sub_quest_ids[self.current_step]
        return None

    def advance_step(self) -> bool:
        """Advance to next sub-quest. Returns True if all steps complete."""
        self.current_step += 1
        return self.current_step >= len(self.sub_quest_ids)

    def check_completion(self) -> bool:
        return self.current_step >= len(self.sub_quest_ids)


QUEST_TYPE_MAP = {
    "fetch": FetchQuest,
    "escort": EscortQuest,
    "delivery": DeliveryQuest,
    "dialogue": DialogueQuest,
    "dialogue_gated": DialogueQuest,
    "combat": CombatQuest,
    "solve": CombatQuest,
    "multi_step": MultiStepQuest,
    # Legacy aliases
    "fetch_item": FetchQuest,
    "combat_event": CombatQuest,
    "combat_npc": CombatQuest,
    "solve_puzzle": CombatQuest,
    "solve_event": CombatQuest,
    "follower_same": EscortQuest,
    "follower_next": EscortQuest,
}


def create_quest_from_data(data: dict) -> Quest:
    """Construct the appropriate Quest subclass from a data dict."""
    quest_type = data.get("type", "fetch")
    cls = QUEST_TYPE_MAP.get(quest_type, Quest)
    data = dict(data)
    if "reward" in data and isinstance(data["reward"], dict):
        data["reward"] = QuestReward(**data["reward"])
    if "failure_penalty" in data and isinstance(data["failure_penalty"], dict):
        data["failure_penalty"] = QuestFailurePenalty(**data["failure_penalty"])
    return cls(**data)
