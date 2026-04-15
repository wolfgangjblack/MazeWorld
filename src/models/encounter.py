import random
from typing import List, Optional

from pydantic import BaseModel, Field

from src.models.monster import Monster


class EventChoice(BaseModel):
    """A single choice in a puzzle or event encounter."""

    text: str
    stat_check: Optional[str] = None
    tool_attribute: Optional[str] = None
    dc: Optional[int] = 10
    auto_success: bool = False
    success_text: Optional[str] = None
    time_gate: Optional[str] = None  # "day" | "night" | None


class Event(BaseModel):
    """Base event model placed on event tiles in the maze."""

    id: int
    type: str  # "combat" | "puzzle" | "event"
    name: str
    description: str
    portrait_prompt: Optional[str] = None
    profile_image: Optional[str] = None
    difficulty: int = 3
    resolved: bool = False
    time_gate: Optional[str] = None  # "day" | "night" | "always" | None

    class Config:
        arbitrary_types_allowed = True


class LootEntry(BaseModel):
    """A single entry in a loot table."""

    item_id: int
    drop_chance: float = 0.5  # 0.0 to 1.0


def _encounter_stat_mod(player, stat_name: str) -> int:
    """Return the stat modifier for an encounter check.

    Jesters silently use whichever is higher: the required stat or LUCK.
    """
    if not hasattr(player, "get_stat_mod"):
        return 0
    mod = player.get_stat_mod(stat_name)
    pc = getattr(player, "player_class", None)
    if pc and getattr(pc, "archetype", "") == "jester" and stat_name != "LUCK":
        luck_mod = player.get_stat_mod("LUCK")
        mod = max(mod, luck_mod)
    return mod


def _roll_reward(
    player,
    money_drop: List[int],
    loot_table: List[LootEntry],
    reward_chance: float,
    consumed_tool_attr: Optional[str] = None,
) -> dict:
    """Single reward roll: either gold OR item, never both. Chance of nothing.

    Returns dict with ``money_dropped`` (int) and ``loot_item_ids`` (list[int]).
    """
    result = {"money_dropped": 0, "loot_item_ids": []}

    if random.random() > reward_chance:
        return result

    luck_mod = player.get_stat_mod("LUCK") if hasattr(player, "get_stat_mod") else 0

    # 60 % gold, 40 % item
    if not loot_table or random.random() < 0.6:
        if money_drop[1] > 0:
            result["money_dropped"] = max(0, random.randint(money_drop[0], money_drop[1]) + luck_mod)
        return result

    eligible = [e for e in loot_table if not (consumed_tool_attr and _loot_matches_tool(e, consumed_tool_attr))]
    if not eligible:
        if money_drop[1] > 0:
            result["money_dropped"] = max(0, random.randint(money_drop[0], money_drop[1]) + luck_mod)
        return result

    entry = random.choice(eligible)
    if random.random() <= entry.drop_chance:
        result["loot_item_ids"] = [entry.item_id]
    else:
        if money_drop[1] > 0:
            result["money_dropped"] = max(0, random.randint(money_drop[0], money_drop[1]) + luck_mod)
    return result


def _loot_matches_tool(entry: LootEntry, tool_attr: str) -> bool:
    """Check if a loot entry's item has the same attribute as the consumed tool."""
    try:
        from src.registry import registry

        item = registry.get_item(entry.item_id)
        if item:
            stats = getattr(item, "item_stats", None)
            if stats and getattr(stats, "attribute", None) == tool_attr:
                return True
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning("Failed loot-tool check for item %d: %s", entry.item_id, exc)
    return False


class CombatEvent(Event):
    """Combat encounter with 1-N monsters.

    Combat logic lives in ``CombatController``; this model only stores the
    encounter definition and monster list.
    """

    type: str = "combat"
    monster_ids: List[int] = Field(default_factory=list)
    monsters: List[Monster] = Field(default_factory=list)
    room_level: int = 1
    is_gate: bool = False
    is_climax_boss: bool = False

    loot_table: List[LootEntry] = Field(default_factory=list)
    money_drop: List[int] = Field(default_factory=lambda: [0, 0])  # [min, max]


class PuzzleEvent(Event):
    """Puzzle encounter — environmental/physical obstacles.

    Player chooses: use a tool (+5 modifier, consumed on roll), use an ability
    (costs stamina, auto-success), use a spell (costs stamina, auto-success),
    or roll dice on a stat-check choice. Walk away is always available.
    """

    type: str = "puzzle"
    choices: List[EventChoice] = Field(default_factory=list)
    reward_item_id: Optional[int] = None
    required_tools: List[str] = Field(default_factory=list)
    correct_tool: Optional[str] = None
    correct_ability: Optional[str] = None
    correct_spell: Optional[str] = None
    ability_text: Optional[str] = None
    ability_success_text: Optional[str] = None
    spell_text: Optional[str] = None
    spell_success_text: Optional[str] = None

    failure_damage_type: str = "health"
    failure_damage_range: List[int] = Field(default_factory=lambda: [3, 10])

    money_drop: List[int] = Field(default_factory=lambda: [0, 0])
    loot_table: List[LootEntry] = Field(default_factory=list)
    reward_chance: float = 0.6

    def _find_matching_ability(self, player):
        if not self.correct_ability:
            return None
        for ability in getattr(player, "abilities", []):
            if getattr(ability, "name", "") == self.correct_ability:
                cost = getattr(ability, "stamina_cost", 0)
                if player.stamina >= cost:
                    return ability
        return None

    def _find_spell(self, player):
        if not self.correct_spell:
            return None
        for spell in getattr(player, "spells", []):
            if getattr(spell, "name", "") == self.correct_spell:
                cost = getattr(spell, "stamina_cost", 0)
                if player.stamina >= cost:
                    return spell
        return None

    def find_tool_item(self, player) -> tuple:
        """Return (item_name, item) matching correct_tool, or (None, None)."""
        if not self.correct_tool:
            return None, None
        for item_name, item in player.inventory.items():
            stats = getattr(item, "item_stats", None)
            if stats and getattr(stats, "attribute", None) == self.correct_tool:
                return item_name, item
        return None, None

    def resolve_with_tool(self, player) -> dict:
        """Player opts to use the correct tool — consumed, auto-success."""
        tool_name, _ = self.find_tool_item(player)
        if not tool_name:
            return {"success": False, "message": "You don't have the right tool."}
        player.remove_from_inventory(tool_name)
        self.resolved = True
        reward = _roll_reward(player, self.money_drop, self.loot_table, self.reward_chance, self.correct_tool)
        return {
            "success": True,
            "message": f"Your {tool_name} makes short work of the {self.name}! (consumed)",
            "reward_item_id": self.reward_item_id,
            "auto_solved": True,
            "consumed_tool": tool_name,
            **reward,
        }

    def resolve_with_ability(self, player) -> dict:
        """Player opts to use the correct ability — costs stamina, auto-success."""
        ability = self._find_matching_ability(player)
        if not ability:
            return {"success": False, "message": "You can't use that ability right now."}
        cost = getattr(ability, "stamina_cost", 0)
        player.stamina = max(0, player.stamina - cost)
        self.resolved = True
        reward = _roll_reward(player, self.money_drop, self.loot_table, self.reward_chance)
        cost_msg = f" (-{cost} stamina)" if cost else ""
        msg = self.ability_success_text or f"You use {ability.name}{cost_msg} to overcome the {self.name}!"
        return {
            "success": True,
            "message": msg,
            "reward_item_id": self.reward_item_id,
            "auto_solved": True,
            **reward,
        }

    def resolve_with_spell(self, player) -> dict:
        """Player opts to use the correct spell — costs stamina, auto-success."""
        spell = self._find_spell(player)
        if not spell:
            return {"success": False, "message": "You can't cast that spell right now."}
        cost = getattr(spell, "stamina_cost", 0)
        player.stamina = max(0, player.stamina - cost)
        self.resolved = True
        reward = _roll_reward(player, self.money_drop, self.loot_table, self.reward_chance)
        cost_msg = f" (-{cost} stamina)" if cost else ""
        msg = self.spell_success_text or f"You cast {spell.name}{cost_msg} to overcome the {self.name}!"
        return {
            "success": True,
            "message": msg,
            "reward_item_id": self.reward_item_id,
            "auto_solved": True,
            **reward,
        }

    def resolve(self, choice_index: int, dice_roll: int, player) -> dict:
        """Dice-roll path for stat-check choices."""
        if choice_index < 0 or choice_index >= len(self.choices):
            return {"success": False, "message": "Invalid choice."}

        choice = self.choices[choice_index]

        if choice.auto_success:
            return {
                "success": True,
                "message": "You walk away safely.",
                "reward_item_id": None,
                "walked_away": True,
            }

        modifier = 0
        if choice.stat_check:
            modifier = _encounter_stat_mod(player, choice.stat_check)

        consumed_tool = None
        if choice.tool_attribute:
            for item_name, item in list(player.inventory.items()):
                stats = getattr(item, "item_stats", None)
                if stats and getattr(stats, "attribute", None) == choice.tool_attribute:
                    consumed_tool = item_name
                    player.remove_from_inventory(item_name)
                    modifier += 5
                    break

        total = dice_roll + modifier
        effective_dc = choice.dc or 10
        if total >= effective_dc:
            self.resolved = True
            reward = _roll_reward(
                player,
                self.money_drop,
                self.loot_table,
                self.reward_chance,
                choice.tool_attribute if consumed_tool else None,
            )
            msg = f"Success! You overcame the {self.name}."
            if consumed_tool:
                msg += f" (Your {consumed_tool} was consumed.)"
            return {
                "success": True,
                "message": msg,
                "reward_item_id": self.reward_item_id,
                "consumed_tool": consumed_tool,
                "roll_dc": effective_dc,
                "roll_total": total,
                **reward,
            }
        else:
            damage = random.randint(self.failure_damage_range[0], self.failure_damage_range[1])
            if self.failure_damage_type == "health":
                player.health = max(0, player.health - damage)
            elif self.failure_damage_type == "stamina":
                player.stamina = max(0, player.stamina - damage)
            msg = f"You failed! Took {damage} {self.failure_damage_type} damage."
            if consumed_tool:
                msg = f"Your {consumed_tool} was consumed. " + msg
            return {
                "success": False,
                "message": msg,
                "consumed_tool": consumed_tool,
                "damage": damage,
                "damage_type": self.failure_damage_type,
                "roll_dc": effective_dc,
                "roll_total": total,
            }


class EventEncounter(Event):
    """People/narrative event with 5 structured choice slots.

    Slot structure:
      0 — stat check (1d20 + stat mod vs DC)
      1 — ability  (auto-success if player has it, costs stamina)
      2 — spell    (auto-success if player has it, costs stamina)
      3 — item/tool (consume item, +5 to roll vs DC)
      4 — walk away (auto_success, event stays active)
    """

    type: str = "event"
    choices: List[EventChoice] = Field(default_factory=list)
    reward_item_id: Optional[int] = None

    correct_ability: Optional[str] = None
    correct_spell: Optional[str] = None
    ability_text: Optional[str] = None
    ability_success_text: Optional[str] = None
    spell_text: Optional[str] = None
    spell_success_text: Optional[str] = None

    failure_damage_type: str = "health"
    failure_damage_range: List[int] = Field(default_factory=lambda: [3, 10])

    money_drop: List[int] = Field(default_factory=lambda: [0, 0])
    loot_table: List[LootEntry] = Field(default_factory=list)
    reward_chance: float = 0.6

    def _find_ability(self, player):
        if not self.correct_ability:
            return None
        for ability in getattr(player, "abilities", []):
            if getattr(ability, "name", "") == self.correct_ability:
                cost = getattr(ability, "stamina_cost", 0)
                if player.stamina >= cost:
                    return ability
        return None

    def _find_spell(self, player):
        if not self.correct_spell:
            return None
        for spell in getattr(player, "spells", []):
            if getattr(spell, "name", "") == self.correct_spell:
                cost = getattr(spell, "stamina_cost", 0)
                if player.stamina >= cost:
                    return spell
        return None

    def resolve_with_ability(self, player) -> dict:
        """Slot 1 — ability use: auto-success, costs stamina."""
        ability = self._find_ability(player)
        if not ability:
            return {"success": False, "message": "You can't use that ability right now."}
        cost = getattr(ability, "stamina_cost", 0)
        player.stamina = max(0, player.stamina - cost)
        self.resolved = True
        reward = _roll_reward(player, self.money_drop, self.loot_table, self.reward_chance)
        cost_msg = f" (-{cost} stamina)" if cost else ""
        msg = self.ability_success_text or f"You use {ability.name}{cost_msg} and resolve the situation!"
        return {
            "success": True,
            "message": msg,
            "reward_item_id": self.reward_item_id,
            "auto_solved": True,
            **reward,
        }

    def resolve_with_spell(self, player) -> dict:
        """Slot 2 — spell use: auto-success, costs stamina."""
        spell = self._find_spell(player)
        if not spell:
            return {"success": False, "message": "You can't cast that spell right now."}
        cost = getattr(spell, "stamina_cost", 0)
        player.stamina = max(0, player.stamina - cost)
        self.resolved = True
        reward = _roll_reward(player, self.money_drop, self.loot_table, self.reward_chance)
        cost_msg = f" (-{cost} stamina)" if cost else ""
        msg = self.spell_success_text or f"You cast {spell.name}{cost_msg} and turn the tide!"
        return {
            "success": True,
            "message": msg,
            "reward_item_id": self.reward_item_id,
            "auto_solved": True,
            **reward,
        }

    def resolve(self, choice_index: int, dice_roll: int, player) -> dict:
        """Resolve stat-check (slot 0) or item/tool (slot 3) choices via dice roll."""
        if choice_index < 0 or choice_index >= len(self.choices):
            return {"success": False, "message": "Invalid choice."}

        choice = self.choices[choice_index]

        if choice.auto_success:
            return {
                "success": True,
                "message": "You slip away quietly.",
                "reward_item_id": None,
                "walked_away": True,
            }

        modifier = 0
        if choice.stat_check:
            modifier = _encounter_stat_mod(player, choice.stat_check)

        consumed_tool = None
        if choice.tool_attribute:
            for item_name, item in list(player.inventory.items()):
                stats = getattr(item, "item_stats", None)
                if stats and getattr(stats, "attribute", None) == choice.tool_attribute:
                    consumed_tool = item_name
                    player.remove_from_inventory(item_name)
                    modifier += 5
                    break

        total = dice_roll + modifier
        effective_dc = choice.dc or 10

        if total >= effective_dc:
            self.resolved = True
            reward = _roll_reward(
                player,
                self.money_drop,
                self.loot_table,
                self.reward_chance,
                choice.tool_attribute if consumed_tool else None,
            )
            msg = f"Success! {choice.text}"
            if consumed_tool:
                msg += f" (Your {consumed_tool} was consumed.)"
            return {
                "success": True,
                "message": msg,
                "reward_item_id": self.reward_item_id,
                "consumed_tool": consumed_tool,
                "roll_dc": effective_dc,
                "roll_total": total,
                **reward,
            }
        else:
            damage = random.randint(self.failure_damage_range[0], self.failure_damage_range[1])
            if self.failure_damage_type == "health":
                player.health = max(0, player.health - damage)
            elif self.failure_damage_type == "stamina":
                player.stamina = max(0, player.stamina - damage)

            msg = f"You failed! Took {damage} {self.failure_damage_type} damage."
            if consumed_tool:
                msg = f"Your {consumed_tool} was consumed. " + msg
            return {
                "success": False,
                "message": msg,
                "damage": damage,
                "damage_type": self.failure_damage_type,
                "consumed_tool": consumed_tool,
                "roll_dc": effective_dc,
                "roll_total": total,
            }


EVENT_TYPE_MAP = {
    "combat": CombatEvent,
    "puzzle": PuzzleEvent,
    "event": EventEncounter,
}


def create_event_from_data(data: dict) -> Event:
    """Construct the appropriate Event subclass from a data dict."""
    event_type = data.get("type", "combat")
    cls = EVENT_TYPE_MAP.get(event_type, CombatEvent)

    data = dict(data)

    if event_type in ("puzzle", "event") and "choices" in data:
        data["choices"] = [EventChoice(**c) if isinstance(c, dict) else c for c in data["choices"]]

    if event_type in ("puzzle", "event") and "choices" in data:
        cleaned = []
        for c in data["choices"]:
            is_placeholder = not c.stat_check and not c.tool_attribute and not c.auto_success and not c.dc
            if is_placeholder:
                if data.get("correct_ability") and not data.get("ability_text"):
                    data["ability_text"] = c.text
                    data["ability_success_text"] = c.success_text
                elif data.get("correct_spell") and not data.get("spell_text"):
                    data["spell_text"] = c.text
                    data["spell_success_text"] = c.success_text
            else:
                cleaned.append(c)
        data["choices"] = cleaned

    if event_type == "combat" and "monster_ids" in data:
        from src.models.monster import instantiate_monster
        from src.registry import registry

        room_level = data.get("room_level", 1)
        data["monsters"] = [
            instantiate_monster(registry.get_monster_template(mid), room_level)
            for mid in data["monster_ids"]
            if registry.get_monster_template(mid) is not None
        ]
    elif event_type == "combat" and "monsters" in data:
        data["monsters"] = [Monster.from_dict(m) if isinstance(m, dict) else m for m in data["monsters"]]
    if "loot_table" in data:
        data["loot_table"] = [LootEntry(**e) if isinstance(e, dict) else e for e in data["loot_table"]]

    return cls(**data)
