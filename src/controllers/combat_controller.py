"""Turn-based combat controller.

Handles initiative, turn order, action resolution for all combat actions:
Attack, Multi-Attack, Cast Spell, Use Item, Flee, and Jester's Gamble.
"""

import random
from typing import List, Optional

from src.models.combat import CombatState
from src.models.monster import Monster
from src.models.spell import Spell, elemental_multiplier


def roll_buff_duration(caster) -> int:
    """Roll buff duration: 1d4 + (caster INT modifier // 2), minimum 1."""
    int_mod = caster.get_stat_mod("INT")
    return max(1, random.randint(1, 4) + int_mod // 2)


# Jester Gamble effect table.  Weights shift with LUCK modifier.
GAMBLE_EFFECTS = [
    ("damage_enemy", "Deal 1d10 damage to a random enemy"),
    ("heal_self", "Heal 1d8 HP"),
    ("buff_self", "Gain +2 to a random stat for 3 turns"),
    ("damage_self", "Take 1d6 damage"),
    ("debuff_enemy", "Lower a random enemy's AC by 2 for 3 turns"),
    ("nothing", "Nothing happens..."),
    ("wild_magic", "Cast a random elemental spell"),
]


class Combatant:
    """Wrapper around player or monster to unify turn-order handling."""

    def __init__(self, entity, is_player: bool = False):
        self.entity = entity
        self.is_player = is_player
        self.initiative: int = 0
        # Monster-scoped debuffs (ac penalty, etc.)
        self.ac_penalty: int = 0
        self.ac_penalty_turns: int = 0

    @property
    def name(self) -> str:
        return "Player" if self.is_player else self.entity.name

    @property
    def is_alive(self) -> bool:
        return self.entity.is_alive

    def tick_debuffs(self):
        if self.ac_penalty_turns > 0:
            self.ac_penalty_turns -= 1
            if self.ac_penalty_turns <= 0:
                self.ac_penalty = 0


class CombatController:
    """Orchestrates a single combat encounter."""

    def __init__(self, player, monsters: List[Monster]):
        self.player = player
        self.monsters = list(monsters)
        self.log: List[str] = []
        self.state: CombatState = CombatState.ONGOING
        self.turn_index: int = 0

        # Build combatant list and roll initiative
        self.player_combatant = Combatant(player, is_player=True)
        self.combatants: List[Combatant] = [self.player_combatant]
        for m in self.monsters:
            self.combatants.append(Combatant(m))

        self._roll_initiative()

    # ------------------------------------------------------------------
    # Initiative
    # ------------------------------------------------------------------

    def _roll_initiative(self):
        """Roll initiative for all combatants and sort descending. Ties favor player."""
        for c in self.combatants:
            if c.is_player:
                c.initiative = self.player.roll_initiative()
            else:
                c.initiative = c.entity.roll_initiative()

        # Stable sort descending; player wins ties (is_player=True sorts before False
        # when we negate, because True=1 > False=0, so -True < -False)
        self.combatants.sort(key=lambda c: (-c.initiative, not c.is_player))
        self.turn_index = 0

    def get_turn_order(self) -> List[str]:
        """Return ordered list of combatant names."""
        return [c.name for c in self.combatants if c.is_alive]

    def current_combatant(self) -> Combatant:
        return self.combatants[self.turn_index]

    # ------------------------------------------------------------------
    # Turn management
    # ------------------------------------------------------------------

    def advance_turn(self):
        """Move to the next living combatant."""
        if self.state != CombatState.ONGOING:
            return

        # Check victory / defeat
        if not self.player.is_alive:
            self.state = CombatState.DEFEAT
            self.log.append("You have been slain!")
            return

        alive_monsters = [m for m in self.monsters if m.is_alive]
        if not alive_monsters:
            self.state = CombatState.VICTORY
            self.log.append("All enemies defeated!")
            return

        # Advance index, skipping dead combatants
        for _ in range(len(self.combatants)):
            self.turn_index = (self.turn_index + 1) % len(self.combatants)
            if self.combatants[self.turn_index].is_alive:
                break

    def is_player_turn(self) -> bool:
        return self.current_combatant().is_player

    # ------------------------------------------------------------------
    # Player actions
    # ------------------------------------------------------------------

    def player_attack(self, target_index: int = 0) -> dict:
        """Basic melee attack against a single monster."""
        target = self._get_alive_monster(target_index)
        if target is None:
            return {"success": False, "message": "No valid target."}

        attack_roll = self.player.roll_attack()
        target_combatant = self._combatant_for(target)
        target_ac = target.ac - (target_combatant.ac_penalty if target_combatant else 0)
        dc = target_ac + target.dex_mod

        if attack_roll >= dc:
            damage = self.player.roll_weapon_damage()
            target.take_damage(damage)
            self.player.combat_record["damage_dealt"] += damage
            msg = f"You hit {target.name} for {damage} damage! (roll {attack_roll} vs AC {dc})"
            if not target.is_alive:
                msg += f" {target.name} is slain!"
            self.log.append(msg)
            result = {"success": True, "message": msg, "damage": damage}
        else:
            msg = f"You miss {target.name}. (roll {attack_roll} vs AC {dc})"
            self.log.append(msg)
            result = {"success": False, "message": msg}

        self.player.tick_buffs()
        self.advance_turn()
        return result

    def player_multi_attack(self, target_indices: Optional[List[int]] = None) -> dict:
        """Multi-target melee attack (warrior ability). Costs 8 hunger."""
        cost = 8
        if self.player.hunger < cost:
            msg = "Not enough hunger to multi-attack!"
            self.log.append(msg)
            return {"success": False, "message": msg}

        self.player.hunger = max(0, self.player.hunger - cost)
        alive = self._alive_monsters()
        if target_indices is None:
            targets = alive
        else:
            targets = [alive[i] for i in target_indices if i < len(alive)]

        messages = []
        total_damage = 0
        for target in targets:
            attack_roll = self.player.roll_attack()
            target_combatant = self._combatant_for(target)
            target_ac = target.ac - (target_combatant.ac_penalty if target_combatant else 0)
            dc = target_ac + target.dex_mod
            if attack_roll >= dc:
                damage = self.player.roll_weapon_damage()
                target.take_damage(damage)
                total_damage += damage
                hit_msg = f"Hit {target.name} for {damage}!"
                if not target.is_alive:
                    hit_msg += f" {target.name} is slain!"
                messages.append(hit_msg)
            else:
                messages.append(f"Miss {target.name}.")

        msg = "Multi-Attack: " + " ".join(messages)
        self.log.append(msg)
        self.player.combat_record["damage_dealt"] += total_damage
        self.player.tick_buffs()
        self.advance_turn()
        return {"success": True, "message": msg, "total_damage": total_damage}

    def player_cast_spell(self, spell_index: int, target_index: int = 0) -> dict:
        """Cast a spell from the player's spell list."""
        if spell_index < 0 or spell_index >= len(self.player.spells):
            return {"success": False, "message": "Invalid spell."}

        spell: Spell = self.player.spells[spell_index]

        if not self.player.can_afford_spell(spell):
            msg = f"Not enough resources to cast {spell.name}!"
            self.log.append(msg)
            return {"success": False, "message": msg}

        self.player.pay_spell_cost(spell)

        # --- Healing / buff (no roll needed) ---
        if spell.spell_type == "heal":
            heal = spell.heal_amount if spell.heal_amount else random.randint(4, 12)
            self.player.health = min(self.player.max_health, self.player.health + heal)
            msg = f"You cast {spell.name} and heal {heal} HP!"
            self.log.append(msg)
            self.player.tick_buffs()
            self.advance_turn()
            return {"success": True, "message": msg, "heal": heal}

        if spell.spell_type == "buff_stat":
            stat = spell.buff_stat or "STR"
            duration = roll_buff_duration(self.player)
            self.player.apply_buff(stat, spell.buff_value, duration)
            msg = f"You cast {spell.name}! +{spell.buff_value} {stat} for {duration} turns."
            self.log.append(msg)
            self.player.tick_buffs()
            self.advance_turn()
            return {"success": True, "message": msg}

        if spell.spell_type == "buff_sustain":
            # Restore some hunger/thirst each turn — apply immediate small boost
            restore = 3
            self.player.hunger = min(self.player.max_hunger, self.player.hunger + restore)
            self.player.thirst = min(self.player.max_thirst, self.player.thirst + restore)
            msg = f"You cast {spell.name}! Sustenance flows through you (+{restore} hunger/thirst)."
            self.log.append(msg)
            self.player.tick_buffs()
            self.advance_turn()
            return {"success": True, "message": msg}

        # --- Damage spells (require attack roll) ---
        targets: List[Monster] = []
        if spell.targets == "multi" or spell.spell_type == "damage_multi":
            targets = self._alive_monsters()
        else:
            t = self._get_alive_monster(target_index)
            if t:
                targets = [t]

        if not targets:
            msg = "No valid targets for spell."
            self.log.append(msg)
            self.player.tick_buffs()
            self.advance_turn()
            return {"success": False, "message": msg}

        messages = []
        total_damage = 0
        for target in targets:
            magic_roll = self.player.roll_magic_attack()
            # Jester uses averaged modifier
            if self.player.player_class and self.player.player_class.archetype == "jester":
                normal_stat = spell.stat  # "INT" or "WIS"
                jester_mod = self.player.get_jester_mod(normal_stat)
                # Recalculate: base roll was with INT/WIS, adjust with jester rule
                magic_roll = random.randint(1, 20) + jester_mod + (self.player.level - 1)

            dc = 10 + target.magic_resistance
            if magic_roll >= dc:
                base_damage = spell.roll_damage()
                mult = elemental_multiplier(spell.element, target.elemental_affinity)
                damage = max(1, int(base_damage * mult))
                target.take_damage(damage)
                total_damage += damage
                eff = ""
                if mult > 1.0:
                    eff = " (super effective!)"
                elif mult < 1.0:
                    eff = " (resisted)"
                hit_msg = f"{spell.name} hits {target.name} for {damage}{eff}!"
                if not target.is_alive:
                    hit_msg += f" {target.name} is slain!"
                messages.append(hit_msg)
            else:
                messages.append(f"{spell.name} misses {target.name}. (roll {magic_roll} vs DC {dc})")

        msg = " ".join(messages)
        self.log.append(msg)
        self.player.combat_record["damage_dealt"] += total_damage
        self.player.tick_buffs()
        self.advance_turn()
        return {"success": True, "message": msg, "total_damage": total_damage}

    def player_use_item(self, item_name: str) -> dict:
        """Use an inventory item mid-combat (food/drink for recovery)."""
        if item_name not in self.player.inventory:
            return {"success": False, "message": f"You don't have {item_name}."}

        item = self.player.inventory[item_name]
        message = item.use(self.player)
        self.player.remove_from_inventory(item_name)
        self.log.append(message)
        self.player.tick_buffs()
        self.advance_turn()
        return {"success": True, "message": message}

    def player_flee(self) -> dict:
        """Attempt to flee: 1d20 + DEX vs DC 12 + max monster level."""
        max_level = max(m.level for m in self.monsters if m.is_alive)
        flee_roll = random.randint(1, 20) + self.player.get_stat_mod("DEX")
        dc = 12 + max_level

        if flee_roll >= dc:
            self.state = CombatState.FLED
            msg = f"You flee successfully! (roll {flee_roll} vs DC {dc})"
            self.log.append(msg)
            return {"success": True, "message": msg}
        else:
            # Fail — strongest alive monster gets a free attack
            attacker = max(
                (m for m in self.monsters if m.is_alive),
                key=lambda m: m.level,
            )
            damage = self._monster_attack_player(attacker)
            msg = (
                f"Flee failed! (roll {flee_roll} vs DC {dc}) "
                f"{attacker.name} strikes you for {damage} damage!"
            )
            self.log.append(msg)
            self.player.tick_buffs()
            self.advance_turn()
            return {"success": False, "message": msg, "damage": damage}

    def player_swap_weapon(self) -> dict:
        """Swap the player's equipped weapon mid-combat (costs the turn)."""
        from src.models.items import Weapon as ShopWeapon
        available = {}
        for name, item in self.player.inventory.items():
            if isinstance(item, ShopWeapon) and name != self.player.equipped_weapon:
                available[name] = item

        if not available:
            msg = "No other weapons in inventory to swap to!"
            self.log.append(msg)
            return {"success": False, "message": msg}

        # Swap to the first available weapon that isn't currently equipped
        weapon_name = next(iter(available))
        old_name = self.player.equipped_weapon or "fists"
        self.player.equipped_weapon = weapon_name
        # Also update the weapon instance used for combat rolls
        weapon_item = available[weapon_name]
        if hasattr(weapon_item, 'item_stats') and hasattr(weapon_item.item_stats, 'stat_modifier'):
            from src.models.weapon import Weapon
            self.player.weapon = Weapon(
                name=weapon_name,
                weapon_type=getattr(weapon_item, 'weapon_type', 'simple'),
                stat=weapon_item.item_stats.stat_modifier or "STR",
                damage_dice=getattr(weapon_item.item_stats, 'damage_dice', 6),
            )

        msg = f"Swapped weapon: {old_name} → {weapon_name}!"
        self.log.append(msg)
        self.player.tick_buffs()
        self.advance_turn()
        return {"success": True, "message": msg}

    def player_gamble(self) -> dict:
        """Jester's Gamble: roll on random effect table, LUCK influences distribution."""
        if not self.player.player_class or self.player.player_class.archetype != "jester":
            return {"success": False, "message": "Only jesters can gamble!"}

        luck_mod = self.player.get_stat_mod("LUCK")

        # Base weights: [damage_enemy, heal_self, buff_self, damage_self, debuff_enemy, nothing, wild_magic]
        weights = [15, 15, 10, 15, 10, 25, 10]
        # Positive LUCK shifts weight from bad outcomes to good
        shift = luck_mod * 3
        # Increase good (indices 0,1,2,4,6), decrease bad (indices 3,5)
        for i in [0, 1, 2, 4, 6]:
            weights[i] = max(1, weights[i] + shift)
        for i in [3, 5]:
            weights[i] = max(1, weights[i] - shift)

        effect_key, effect_desc = random.choices(GAMBLE_EFFECTS, weights=weights, k=1)[0]
        msg = f"Jester's Gamble: {effect_desc}"

        alive = self._alive_monsters()
        if effect_key == "damage_enemy" and alive:
            target = random.choice(alive)
            damage = random.randint(1, 10)
            target.take_damage(damage)
            msg += f" — {target.name} takes {damage} damage!"
            if not target.is_alive:
                msg += f" {target.name} is slain!"
        elif effect_key == "heal_self":
            heal = random.randint(1, 8)
            self.player.health = min(self.player.max_health, self.player.health + heal)
            msg += f" — You heal {heal} HP!"
        elif effect_key == "buff_self":
            stat = random.choice(["STR", "DEX", "CON", "INT", "WIS"])
            duration = roll_buff_duration(self.player)
            self.player.apply_buff(stat, 2, duration)
            msg += f" — +2 {stat} for {duration} turns!"
        elif effect_key == "damage_self":
            damage = random.randint(1, 6)
            self.player.health = max(0, self.player.health - damage)
            msg += f" — You take {damage} damage!"
        elif effect_key == "debuff_enemy" and alive:
            target = random.choice(alive)
            combatant = self._combatant_for(target)
            if combatant:
                combatant.ac_penalty = 2
                combatant.ac_penalty_turns = 3
            msg += f" — {target.name}'s AC lowered by 2 for 3 turns!"
        elif effect_key == "wild_magic" and alive:
            elements = ["fire", "water", "forest", "light", "dark"]
            elem = random.choice(elements)
            target = random.choice(alive)
            damage = random.randint(3, 12)
            mult = elemental_multiplier(elem, target.elemental_affinity)
            damage = max(1, int(damage * mult))
            target.take_damage(damage)
            eff = ""
            if mult > 1.0:
                eff = " (super effective!)"
            elif mult < 1.0:
                eff = " (resisted)"
            msg += f" — Wild {elem} magic hits {target.name} for {damage}{eff}!"
            if not target.is_alive:
                msg += f" {target.name} is slain!"
        else:
            msg += " — The magic fizzles."

        self.log.append(msg)
        self.player.tick_buffs()
        self.advance_turn()
        return {"success": True, "message": msg, "effect": effect_key}

    # ------------------------------------------------------------------
    # Monster turn
    # ------------------------------------------------------------------

    def execute_monster_turn(self) -> dict:
        """Execute the current monster's turn (AI: attack player)."""
        combatant = self.current_combatant()
        if combatant.is_player:
            return {"success": False, "message": "It's the player's turn."}

        monster: Monster = combatant.entity
        if not monster.is_alive:
            self.advance_turn()
            return {"success": True, "message": f"{monster.display_name} is dead, skipping."}

        damage = self._monster_attack_player(monster)
        combatant.tick_debuffs()

        if damage > 0:
            msg = f"{monster.display_name} attacks you for {damage} damage!"
            if not self.player.is_alive:
                msg += " You have been slain!"
                self.state = CombatState.DEFEAT
        else:
            msg = f"{monster.display_name} misses!"

        self.log.append(msg)
        self.advance_turn()
        return {"success": True, "message": msg, "damage": damage}

    # ------------------------------------------------------------------
    # Loot
    # ------------------------------------------------------------------

    def collect_loot(self) -> List[int]:
        """Roll loot for all dead monsters. Returns list of item_ids."""
        all_loot: List[int] = []
        for m in self.monsters:
            if not m.is_alive:
                all_loot.extend(m.roll_loot())
        return all_loot

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _alive_monsters(self) -> List[Monster]:
        return [m for m in self.monsters if m.is_alive]

    def _get_alive_monster(self, index: int) -> Optional[Monster]:
        alive = self._alive_monsters()
        if 0 <= index < len(alive):
            return alive[index]
        return alive[0] if alive else None

    def _combatant_for(self, monster: Monster) -> Optional[Combatant]:
        for c in self.combatants:
            if not c.is_player and c.entity is monster:
                return c
        return None

    def _monster_attack_player(self, monster: Monster) -> int:
        """Monster attacks the player. Returns damage dealt (0 on miss)."""
        attack_roll = monster.roll_attack()
        player_ac = self.player.get_ac()

        if attack_roll >= player_ac:
            damage = monster.roll_damage()
            self.player.health = max(0, self.player.health - damage)
            self.player.combat_record["damage_taken"] += damage
            return damage
        return 0
