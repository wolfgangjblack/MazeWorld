import random
from typing import List, Optional

from pydantic import BaseModel, Field

from src.models.monster import Monster, _roll_dice


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
    """Multi-turn combat encounter with 1-N monsters."""

    type: str = "combat"
    monster_ids: List[int] = Field(default_factory=list)
    monsters: List[Monster] = Field(default_factory=list)
    room_level: int = 1
    is_gate: bool = False
    is_climax_boss: bool = False

    # Legacy fields for backwards compat with old single-roll combat
    damage_type: str = "health"
    damage_range: List[int] = Field(default_factory=lambda: [5, 15])
    reward_item_id: Optional[int] = None
    loot_table: List[LootEntry] = Field(default_factory=list)
    money_drop: List[int] = Field(default_factory=lambda: [0, 0])  # [min, max]

    # Combat state
    turn_order: List[dict] = Field(default_factory=list)  # [{"type":"player"|"monster","index":int,"initiative":int}]
    current_turn_index: int = 0
    combat_log: List[str] = Field(default_factory=list)
    combat_started: bool = False
    player_fled: bool = False

    def start_combat(self, player) -> dict:
        """Roll initiative for all combatants and set turn order."""
        self.combat_started = True
        self.combat_log = []

        entries = []
        # Player initiative
        dex_mod = player.get_stat_mod("DEX") if hasattr(player, "get_stat_mod") else 0
        player_init = random.randint(1, 20) + dex_mod
        entries.append({"type": "player", "index": -1, "initiative": player_init})
        self.combat_log.append(f"You roll initiative: {player_init}")

        # Monster initiatives
        for i, monster in enumerate(self.monsters):
            if monster.is_alive:
                init = monster.roll_initiative()
                entries.append({"type": "monster", "index": i, "initiative": init})
                self.combat_log.append(f"{monster.name} rolls initiative: {init}")

        # Sort descending by initiative, player wins ties
        entries.sort(key=lambda e: (e["initiative"], 1 if e["type"] == "player" else 0), reverse=True)
        self.turn_order = entries
        self.current_turn_index = 0

        return {
            "message": "Combat begins!",
            "turn_order": self.turn_order,
            "first": self.turn_order[0] if self.turn_order else None,
        }

    def get_current_turn(self) -> Optional[dict]:
        """Return current combatant entry, or None if combat is over."""
        if not self.turn_order:
            return None
        checked = 0
        while checked < len(self.turn_order):
            entry = self.turn_order[self.current_turn_index]
            if entry["type"] == "monster":
                monster = self.monsters[entry["index"]]
                if not monster.is_alive:
                    self.current_turn_index = (self.current_turn_index + 1) % len(self.turn_order)
                    checked += 1
                    continue
            return entry
        return None

    def advance_turn(self):
        """Move to the next combatant."""
        self.current_turn_index = (self.current_turn_index + 1) % len(self.turn_order)

    def player_attack(self, player, target_index: int) -> dict:
        """Player attacks a monster. Returns result dict."""
        if target_index < 0 or target_index >= len(self.monsters):
            return {"success": False, "message": "Invalid target."}

        monster = self.monsters[target_index]
        if not monster.is_alive:
            return {"success": False, "message": f"{monster.name} is already defeated."}

        str_mod = player.get_stat_mod("STR") if hasattr(player, "get_stat_mod") else 0
        attack_roll = random.randint(1, 20) + str_mod
        defense_dc = 10 + monster.ac + monster.dex_mod

        if attack_roll >= defense_dc:
            damage = max(1, random.randint(1, 6) + str_mod)
            # Check for tool bonus
            for item in player.inventory.values():
                stats = getattr(item, "item_stats", None)
                if stats and getattr(stats, "attribute", None) == "bludgeon":
                    damage += 2
                    break

            monster.take_damage(damage)
            msg = f"You hit {monster.name} for {damage} damage! (Roll: {attack_roll} vs DC {defense_dc})"
            if not monster.is_alive:
                msg += f" {monster.name} is defeated!"
            self.combat_log.append(msg)
            return {"success": True, "message": msg, "damage": damage, "roll": attack_roll}
        else:
            msg = f"You miss {monster.name}. (Roll: {attack_roll} vs DC {defense_dc})"
            self.combat_log.append(msg)
            return {"success": False, "message": msg, "roll": attack_roll}

    def monster_turn(self, monster_index: int, player) -> dict:
        """A monster attacks the player. Returns result dict."""
        monster = self.monsters[monster_index]
        if not monster.is_alive or monster.is_stunned():
            if monster.is_stunned():
                msg = f"{monster.name} is stunned and cannot act!"
                monster.tick_status_effects()
                self.combat_log.append(msg)
                return {"success": False, "message": msg, "stunned": True}
            return {"success": False, "message": ""}

        # Tick status effects (poison on monsters is tracked but not damaging here)
        if "poison" in monster.status_effects:
            pass

        # Choose action
        action = monster.choose_action()

        if action["type"] == "ability":
            ability = action["ability"]
            if ability.effect_type == "poison":
                # Poison the player: deal initial damage + lingering
                damage = _roll_dice(ability.damage_dice)
                player.health = max(0, player.health - damage)
                msg = f"{monster.name} uses {ability.name}! You take {damage} poison damage and are poisoned for {ability.duration} turns."
                self.combat_log.append(msg)
                return {
                    "success": True,
                    "message": msg,
                    "damage": damage,
                    "effect": "poison",
                    "duration": ability.duration,
                }
            elif ability.effect_type == "stun":
                msg = f"{monster.name} uses {ability.name}! You are stunned for 1 turn!"
                self.combat_log.append(msg)
                return {"success": True, "message": msg, "damage": 0, "effect": "stun"}
            elif ability.effect_type == "damage":
                damage = _roll_dice(ability.damage_dice)
                player.health = max(0, player.health - damage)
                msg = f"{monster.name} uses {ability.name}! You take {damage} {ability.damage_type} damage."
                self.combat_log.append(msg)
                return {"success": True, "message": msg, "damage": damage}

        # Basic attack
        attack_roll = monster.roll_attack()
        dex_mod = player.get_stat_mod("DEX") if hasattr(player, "get_stat_mod") else 0
        defense_dc = 10 + dex_mod

        if attack_roll >= defense_dc:
            damage = monster.roll_damage()
            player.health = max(0, player.health - damage)
            msg = f"{monster.name} {monster.attack_name}s you for {damage} damage! (Roll: {attack_roll} vs DC {defense_dc})"
            self.combat_log.append(msg)
            return {"success": True, "message": msg, "damage": damage, "roll": attack_roll}
        else:
            msg = f"{monster.name} misses! (Roll: {attack_roll} vs DC {defense_dc})"
            self.combat_log.append(msg)
            return {"success": False, "message": msg, "roll": attack_roll}

    def try_flee(self, player) -> dict:
        """Player attempts to flee. 1d20 + DEX vs DC 12 + avg monster level."""
        avg_level = sum(m.level for m in self.monsters if m.is_alive) / max(
            1, sum(1 for m in self.monsters if m.is_alive)
        )
        flee_dc = int(12 + avg_level)
        dex_mod = player.get_stat_mod("DEX") if hasattr(player, "get_stat_mod") else 0
        roll = random.randint(1, 20) + dex_mod

        if roll >= flee_dc:
            self.player_fled = True
            msg = f"You flee successfully! (Roll: {roll} vs DC {flee_dc})"
            self.combat_log.append(msg)
            return {"success": True, "message": msg}
        else:
            msg = f"Failed to flee! (Roll: {roll} vs DC {flee_dc})"
            self.combat_log.append(msg)
            return {"success": False, "message": msg}

    def is_combat_over(self) -> Optional[str]:
        """Return 'victory', 'defeat', 'fled', or None if combat continues."""
        if self.player_fled:
            return "fled"
        if all(not m.is_alive for m in self.monsters):
            return "victory"
        return None  # Defeat is checked externally via player.health

    def collect_loot(self) -> List[int]:
        """Roll loot from all defeated monsters."""
        all_loot = []
        for monster in self.monsters:
            if not monster.is_alive:
                all_loot.extend(monster.roll_loot())
        return all_loot

    def resolve(self, dice_roll: int, player) -> dict:
        """Roll vs difficulty. Win -> reward + loot. Lose -> take damage.
        If player has an equipped weapon, add its damage roll as a modifier.
        For multi-turn combat (monsters populated), callers should use the
        combat system instead of this legacy path.
        """
        if self.monsters:
            return {"success": False, "message": "Use combat system for multi-turn fights."}

        threshold = self.difficulty * 3
        weapon_bonus = 0
        weapon = player.get_equipped_weapon() if hasattr(player, "get_equipped_weapon") else None
        if weapon and weapon.item_stats.stat_modifier:
            weapon_bonus = (
                player.get_stat_mod(weapon.item_stats.stat_modifier) if hasattr(player, "get_stat_mod") else 0
            )

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
            elif self.damage_type == "stamina":
                player.stamina = max(0, player.stamina - damage)
            return {
                "success": False,
                "message": f"The {self.name} hits you for {damage} {self.damage_type} damage!",
                "damage": damage,
                "damage_type": self.damage_type,
            }


class PuzzleEvent(Event):
    """Puzzle encounter — environmental/physical obstacles.

    Player chooses: use a tool (consumed, auto-success), use an ability
    (costs stamina, auto-success), or roll dice on a stat-check choice.
    Walk away is always available.
    """

    type: str = "puzzle"
    choices: List[EventChoice] = Field(default_factory=list)
    reward_item_id: Optional[int] = None
    required_tools: List[str] = Field(default_factory=list)
    correct_tool: Optional[str] = None
    correct_ability: Optional[str] = None

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
        return {
            "success": True,
            "message": f"You use {ability.name}{cost_msg} to overcome the {self.name}!",
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
                **reward,
            }
        else:
            msg = f"You failed to overcome the {self.name}. (Rolled {total} vs DC {effective_dc})"
            if consumed_tool:
                msg = f"Your {consumed_tool} was consumed in the attempt. " + msg
            return {
                "success": False,
                "message": msg,
                "consumed_tool": consumed_tool,
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
                **reward,
            }
        else:
            damage = random.randint(self.failure_damage_range[0], self.failure_damage_range[1])
            if self.failure_damage_type == "health":
                player.health = max(0, player.health - damage)
            elif self.failure_damage_type == "stamina":
                player.stamina = max(0, player.stamina - damage)

            msg = f"You failed! Took {damage} {self.failure_damage_type} damage. (Rolled {total} vs DC {effective_dc})"
            if consumed_tool:
                msg = f"Your {consumed_tool} was consumed. " + msg
            return {
                "success": False,
                "message": msg,
                "damage": damage,
                "damage_type": self.failure_damage_type,
                "consumed_tool": consumed_tool,
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

    if event_type == "event" and "choices" in data:
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
