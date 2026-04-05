import random
from pydantic import BaseModel, Field
from typing import Optional, List

from src.models.monster import Monster, _roll_dice


class EventChoice(BaseModel):
    """A single choice in a puzzle or event encounter."""
    text: str
    stat_check: Optional[str] = None
    tool_attribute: Optional[str] = None
    dc: int = 10
    auto_success: bool = False
    time_gate: Optional[str] = None  # "day" | "night" | None


class Event(BaseModel):
    """Base event model placed on event tiles in the maze."""
    id: str
    type: str  # "combat" | "puzzle" | "event"
    name: str
    description: str
    portrait_prompt: Optional[str] = None
    profile_image: Optional[str] = None
    difficulty: int = 3
    resolved: bool = False

    class Config:
        arbitrary_types_allowed = True


class CombatEvent(Event):
    """Multi-turn combat encounter with 1-N monsters."""
    type: str = "combat"
    monsters: List[Monster] = Field(default_factory=list)
    room_level: int = 1

    # Legacy fields for backwards compat with old single-roll combat
    damage_type: str = "health"
    damage_range: List[int] = Field(default_factory=lambda: [5, 15])
    reward_item_id: Optional[int] = None

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
        player_init = random.randint(1, 20) + (player.health // 20)  # DEX proxy
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
        # Skip dead monsters
        while self.current_turn_index < len(self.turn_order):
            entry = self.turn_order[self.current_turn_index]
            if entry["type"] == "monster":
                monster = self.monsters[entry["index"]]
                if not monster.is_alive:
                    self.current_turn_index = (self.current_turn_index + 1) % len(self.turn_order)
                    continue
            return entry
        return self.turn_order[self.current_turn_index % len(self.turn_order)]

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

        # Roll: 1d20 + level proxy (health//20) vs DC: 10 + monster AC + monster dex_mod
        attack_roll = random.randint(1, 20) + (player.health // 20)
        defense_dc = 10 + monster.ac + monster.dex_mod

        if attack_roll >= defense_dc:
            # Hit: base damage 1d6 + modifier
            damage = max(1, random.randint(1, 6) + (player.health // 25))
            # Check for tool bonus
            for item in player.inventory.values():
                stats = getattr(item, 'item_stats', None)
                if stats and getattr(stats, 'attribute', None) == 'bludgeon':
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

        # Tick status effects (poison damage, etc.)
        poison_msg = ""
        if "poison" in monster.status_effects:
            # Poison damages the player on the monster's turn? No — poison on monsters.
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
                return {"success": True, "message": msg, "damage": damage, "effect": "poison", "duration": ability.duration}
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
        defense_dc = 10 + (player.health // 20)  # AC proxy for player

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
        avg_level = sum(m.level for m in self.monsters if m.is_alive) / max(1, sum(1 for m in self.monsters if m.is_alive))
        flee_dc = int(12 + avg_level)
        roll = random.randint(1, 20) + (player.health // 20)

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
        """Legacy single-roll resolution for backwards compatibility."""
        if self.monsters:
            # Use new multi-turn system — this shouldn't be called directly
            return {"success": False, "message": "Use combat system for multi-turn fights."}

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
    """Puzzle encounter requiring specific tool/ability.

    Correct tool = solved + reward.
    Wrong tool = consumed + warning + puzzle remains.
    No tool = can leave and return.
    """
    type: str = "puzzle"
    choices: List[EventChoice] = Field(default_factory=list)
    reward_item_id: Optional[int] = None
    required_tools: List[str] = Field(default_factory=list)  # Valid tool attributes that solve it

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
            # Wrong tool consumed if tool_attribute was specified
            consumed_tool = None
            if choice.tool_attribute:
                for item_name, item in list(player.inventory.items()):
                    stats = getattr(item, 'item_stats', None)
                    if stats and getattr(stats, 'attribute', None) == choice.tool_attribute:
                        consumed_tool = item_name
                        player.remove_from_inventory(item_name)
                        break

            msg = f"You failed to overcome the {self.name}. (Rolled {total} vs DC {choice.dc})"
            if consumed_tool:
                msg = f"This doesn't seem right... Your {consumed_tool} was consumed. " + msg
            return {
                "success": False,
                "message": msg,
                "consumed_tool": consumed_tool,
            }


class EventEncounter(Event):
    """Multi-choice event encounter with dice checks.

    Each option may require a tool/ability/stat check.
    Roll 1d20 + stat mod (+ tool/ability bonus).
    Pass DC = reward. Fail = consequence.
    Walk away always available.
    """
    type: str = "event"
    choices: List[EventChoice] = Field(default_factory=list)
    reward_item_id: Optional[int] = None

    # Consequences on failure
    failure_damage_type: str = "health"  # "health" | "hunger" | "thirst"
    failure_damage_range: List[int] = Field(default_factory=lambda: [3, 10])

    def resolve(self, choice_index: int, dice_roll: int, player) -> dict:
        """Resolve the chosen option with dice + modifiers."""
        if choice_index < 0 or choice_index >= len(self.choices):
            return {"success": False, "message": "Invalid choice."}

        choice = self.choices[choice_index]

        if choice.auto_success:
            # Walk away — no penalty, event stays active
            return {
                "success": True,
                "message": "You walk away carefully.",
                "reward_item_id": None,
                "walked_away": True,
            }

        modifier = 0
        # Stat check bonus
        if choice.stat_check:
            stat_val = getattr(player, choice.stat_check, 50)
            modifier = stat_val // 20

        # Tool/ability bonus
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
                "message": f"Success! {choice.text} worked perfectly.",
                "reward_item_id": self.reward_item_id,
            }
        else:
            # Apply consequence
            damage = random.randint(self.failure_damage_range[0], self.failure_damage_range[1])
            if self.failure_damage_type == "health":
                player.health = max(0, player.health - damage)
            elif self.failure_damage_type == "hunger":
                player.hunger = max(0, player.hunger - damage)
            elif self.failure_damage_type == "thirst":
                player.thirst = max(0, player.thirst - damage)

            return {
                "success": False,
                "message": f"You failed! Took {damage} {self.failure_damage_type} damage. (Rolled {total} vs DC {choice.dc})",
                "damage": damage,
                "damage_type": self.failure_damage_type,
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
        data["choices"] = [
            EventChoice(**c) if isinstance(c, dict) else c
            for c in data["choices"]
        ]

    if event_type == "combat" and "monsters" in data:
        data["monsters"] = [
            Monster.from_dict(m) if isinstance(m, dict) else m
            for m in data["monsters"]
        ]

    return cls(**data)
