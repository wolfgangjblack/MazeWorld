"""Combat input handler — extracted from GameController.

Manages the full CombatController + CombatView combat system including
action grid navigation, spell/item/target selection sub-menus,
result display, log browsing, loot collection, and quest completion.
"""

import random

import pygame

from src.controllers.combat_controller import CombatController, CombatState
from src.registry import registry
from src.views.combat_view import CombatView


class CombatInputHandler:
    """Handles all input and state for CombatController-based combat encounters."""

    def __init__(self, gc):
        self.gc = gc
        self._reset_state()

    def _reset_state(self):
        self.combat_controller: CombatController | None = None
        self.combat_view: CombatView | None = None
        self.combat_event = None
        self.selected_action = 0
        self.selected_target = 0
        self.selecting_target = False
        self.selecting_spell = False
        self.selected_spell = 0
        self.selecting_item = False
        self.selected_item = 0
        self.highlight_all_targets = False
        self.pending_action = ""
        self.showing_result = False
        self.last_result = ""
        self.browsing_log = False
        self.log_browse_scroll = 0
        self.game_over_selection = 0
        self.loot_summary: list[str] | None = None
        self._rolled_gold = 0

    @property
    def active(self) -> bool:
        return self.combat_controller is not None

    def start(self, combat_event):
        """Initialize combat for the given event."""
        from src.models.weapon import STARTER_WEAPONS

        gc = self.gc
        if gc.player.weapon is None and gc.player.player_class:
            gc.player.weapon = STARTER_WEAPONS.get(gc.player.player_class.archetype)

        if not combat_event.monsters:
            import logging

            logging.getLogger(__name__).warning(
                "Combat event '%s' has no monsters — skipping.",
                getattr(combat_event, "name", combat_event.id),
            )
            return

        gc.day_night.pause()
        self._reset_state()
        self.combat_event = combat_event
        self.combat_controller = CombatController(gc.player, list(combat_event.monsters), survival=gc.survival)
        self.combat_view = CombatView(gc.screen, gc.font)

    def handle_input(self, event) -> None:
        """Full keyboard dispatch for combat."""
        cc = self.combat_controller
        if cc is None:
            return

        if event.key == pygame.K_PAGEUP and self.combat_view:
            self.combat_view.scroll_log(3)
            return
        if event.key == pygame.K_PAGEDOWN and self.combat_view:
            self.combat_view.scroll_log(-3)
            return

        if self.showing_result:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.showing_result = False
                self.last_result = ""
                self._run_monster_turns_and_cleanup()
            elif event.key == pygame.K_TAB:
                self.showing_result = False
                self.last_result = ""
                self._run_monster_turns_and_cleanup()
                self.browsing_log = True
                self.log_browse_scroll = 0
            return

        if self.browsing_log:
            if event.key == pygame.K_UP and self.combat_view:
                self.combat_view.scroll_log(1)
            elif event.key == pygame.K_DOWN and self.combat_view:
                self.combat_view.scroll_log(-1)
            elif event.key in (pygame.K_TAB, pygame.K_ESCAPE):
                self.browsing_log = False
                if self.combat_view:
                    self.combat_view.log_scroll = 0
            return

        if cc.state != CombatState.ONGOING:
            self._handle_combat_end_input(event)
            return

        if not cc.is_player_turn():
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                gc = self.gc
                prev_hp = gc.player.health
                cc.execute_monster_turn()
                while cc.state == CombatState.ONGOING and not cc.is_player_turn():
                    cc.execute_monster_turn()
                if gc.sfx and gc.player.health < prev_hp:
                    gc.sfx.play("player_take_damage")
                self.selecting_target = False
                self.selecting_spell = False
                self.selecting_item = False
                self.highlight_all_targets = False
                self.pending_action = ""
                self.selected_action = 0
            return

        if self.selecting_spell:
            spells = cc.player.spells
            if event.key == pygame.K_UP:
                self.selected_spell = (self.selected_spell - 1) % max(len(spells), 1)
            elif event.key == pygame.K_DOWN:
                self.selected_spell = (self.selected_spell + 1) % max(len(spells), 1)
            elif event.key == pygame.K_RETURN:
                if spells:
                    spell = spells[self.selected_spell]
                    if spell.targets == "self" or spell.spell_type in ("heal", "buff_stat", "buff_sustain"):
                        if self.gc.sfx:
                            self.gc.sfx.play_spell(spell.spell_type, "cast")
                        result = cc.player_cast_spell(self.selected_spell, 0)
                        self.selecting_spell = False
                        msg = result.get("message", "") if isinstance(result, dict) else ""
                        if msg:
                            self.last_result = msg
                            self.showing_result = True
                        else:
                            self._run_monster_turns_and_cleanup()
                    else:
                        self.selecting_spell = False
                        self.selecting_target = True
                        self.selected_target = 0
                        self.highlight_all_targets = spell.spell_type == "damage_multi"
                        self.pending_action = "Cast Spell"
            elif event.key == pygame.K_ESCAPE:
                self.selecting_spell = False
            return

        if self.selecting_item:
            consumables = self._get_consumables()
            if event.key == pygame.K_UP:
                self.selected_item = (self.selected_item - 1) % max(len(consumables), 1)
            elif event.key == pygame.K_DOWN:
                self.selected_item = (self.selected_item + 1) % max(len(consumables), 1)
            elif event.key == pygame.K_RETURN:
                if consumables:
                    item_name = consumables[self.selected_item]
                    result = cc.player_use_item(item_name)
                    self.selecting_item = False
                    msg = result.get("message", "") if isinstance(result, dict) else ""
                    if msg:
                        self.last_result = msg
                        self.showing_result = True
                    else:
                        self._run_monster_turns_and_cleanup()
            elif event.key == pygame.K_ESCAPE:
                self.selecting_item = False
            return

        if self.selecting_target:
            alive = [m for m in cc.monsters if m.is_alive]
            if event.key == pygame.K_LEFT:
                if not self.highlight_all_targets:
                    self.selected_target = (self.selected_target - 1) % max(len(alive), 1)
            elif event.key == pygame.K_RIGHT:
                if not self.highlight_all_targets:
                    self.selected_target = (self.selected_target + 1) % max(len(alive), 1)
            elif event.key == pygame.K_RETURN:
                if self.highlight_all_targets:
                    action_name = self._grid_action_name(cc)
                    if action_name == "Multi-Attack":
                        self._execute_by_name("Multi-Attack", 0)
                    elif action_name == "Cast Spell":
                        self._execute_by_name("Cast Spell", self.selected_target)
                else:
                    action_name = self._grid_action_name(cc)
                    if action_name:
                        self._execute_by_name(action_name, self.selected_target)
                self.selecting_target = False
                self.highlight_all_targets = False
                self.pending_action = ""
                self.selected_action = 0
            elif event.key == pygame.K_ESCAPE:
                self.selecting_target = False
                self.highlight_all_targets = False
                self.pending_action = ""
            return

        _gate = getattr(self.combat_event, "is_gate", False) or getattr(self.combat_event, "is_climax_boss", False)
        cur = self.selected_action
        row = cur // CombatView.GRID_COLS
        col = cur % CombatView.GRID_COLS

        if event.key == pygame.K_UP:
            row = (row - 1) % CombatView.GRID_ROWS
            self.selected_action = row * CombatView.GRID_COLS + col
        elif event.key == pygame.K_DOWN:
            row = (row + 1) % CombatView.GRID_ROWS
            self.selected_action = row * CombatView.GRID_COLS + col
        elif event.key == pygame.K_LEFT:
            col = (col - 1) % CombatView.GRID_COLS
            self.selected_action = row * CombatView.GRID_COLS + col
        elif event.key == pygame.K_RIGHT:
            col = (col + 1) % CombatView.GRID_COLS
            self.selected_action = row * CombatView.GRID_COLS + col
        elif event.key == pygame.K_RETURN:
            action_name = self._grid_action_name(cc)
            if not action_name:
                return
            if action_name == "Cast Spell":
                if cc.player.spells:
                    self.selecting_spell = True
                    self.selected_spell = 0
            elif action_name == "Item":
                consumables = self._get_consumables()
                if consumables:
                    self.selecting_item = True
                    self.selected_item = 0
            elif action_name == "Attack":
                self.selecting_target = True
                self.selected_target = 0
                self.pending_action = "Attack"
            elif action_name == "Multi-Attack":
                self.selecting_target = True
                self.highlight_all_targets = True
                self.selected_target = 0
                self.pending_action = "Multi-Attack"
            elif action_name == "Weapons":
                self._execute_by_name("Swap Weapon", 0)
            elif action_name == "Flee":
                if _gate:
                    return
                self._execute_by_name("Flee", 0)
            elif action_name == "Gamble":
                self._execute_by_name("Gamble", 0)
        elif event.key == pygame.K_TAB:
            self.browsing_log = True
            self.log_browse_scroll = 0

    def handle_mousewheel(self, event):
        if self.active and self.combat_view:
            self.combat_view.scroll_log(-event.y * 3)

    def draw(self):
        if not self.active or not self.combat_view or not self.combat_controller:
            return
        _gate_fight = getattr(self.combat_event, "is_gate", False) or getattr(
            self.combat_event, "is_climax_boss", False
        )
        self.combat_view.draw(
            self.combat_controller,
            selected_action=self.selected_action,
            selected_target=self.selected_target,
            selecting_target=self.selecting_target,
            selecting_spell=self.selecting_spell,
            selected_spell=self.selected_spell,
            selecting_item=self.selecting_item,
            selected_item=self.selected_item,
            game_over_selection=self.game_over_selection,
            is_gate_fight=_gate_fight,
            highlight_all_targets=self.highlight_all_targets,
            loot_summary=self.loot_summary,
            pending_action=self.pending_action,
            pending_spell_index=self.selected_spell,
            showing_result=self.showing_result,
            result_text=self.last_result,
            browsing_log=self.browsing_log,
            log_browse_scroll=self.log_browse_scroll,
        )

    def _grid_action_name(self, cc: CombatController) -> str | None:
        _gate = getattr(self.combat_event, "is_gate", False) or getattr(self.combat_event, "is_climax_boss", False)
        grid = CombatView.get_action_grid(cc, is_gate_fight=_gate)
        row = self.selected_action // CombatView.GRID_COLS
        col = self.selected_action % CombatView.GRID_COLS
        if row < len(grid) and col < len(grid[row]):
            return grid[row][col]
        return None

    def _get_consumables(self) -> list[str]:
        from src.models.items import Drink, Food

        cc = self.combat_controller
        if cc is None:
            return []
        return [name for name, item in cc.player.inventory.items() if isinstance(item, (Food, Drink))]

    def _execute_by_name(self, action_name: str, target_index: int):
        cc = self.combat_controller
        gc = self.gc
        if cc is None:
            return

        result = {"success": False, "message": ""}

        if action_name == "Attack":
            if gc.sfx:
                gc.sfx.play("dice_roll")
                wt = gc.player.weapon.weapon_type if gc.player.weapon else "simple"
                gc.sfx.play_weapon_swing(wt)
            result = cc.player_attack(target_index)
            if gc.sfx and result.get("success"):
                wt = gc.player.weapon.weapon_type if gc.player.weapon else "simple"
                gc.sfx.play_weapon_hit(wt)
        elif action_name == "Multi-Attack":
            if gc.sfx:
                wt = gc.player.weapon.weapon_type if gc.player.weapon else "simple"
                gc.sfx.play_weapon_swing(wt)
            result = cc.player_multi_attack()
        elif action_name == "Cast Spell":
            if cc.player.spells:
                spell = cc.player.spells[self.selected_spell]
                if gc.sfx:
                    gc.sfx.play_spell(spell.spell_type, "cast")
                result = cc.player_cast_spell(self.selected_spell, target_index)
                if gc.sfx and result.get("total_damage", 0) > 0:
                    gc.sfx.play_spell(spell.spell_type, "impact")
        elif action_name == "Item":
            consumables = self._get_consumables()
            if consumables:
                result = cc.player_use_item(consumables[self.selected_item])
        elif action_name == "Flee":
            if gc.sfx:
                gc.sfx.play("dice_roll")
            result = cc.player_flee()
        elif action_name == "Gamble":
            if gc.sfx:
                gc.sfx.play("dice_roll")
            result = cc.player_gamble()
        elif action_name == "Swap Weapon":
            result = cc.player_swap_weapon()

        msg = result.get("message", "") if isinstance(result, dict) else str(result or "")
        if msg:
            self.last_result = msg
            self.showing_result = True
        else:
            self._run_monster_turns_and_cleanup()

    def _run_monster_turns_and_cleanup(self):
        cc = self.combat_controller
        gc = self.gc
        if cc is None:
            return
        prev_hp = gc.player.health

        while cc.state == CombatState.ONGOING and not cc.is_player_turn():
            cc.execute_monster_turn()

        if gc.sfx and gc.player.health < prev_hp:
            gc.sfx.play("player_take_damage")

        self.selected_action = 0

        if cc.state == CombatState.VICTORY and self.loot_summary is None:
            self._build_loot_summary()

    def _build_loot_summary(self):
        cc = self.combat_controller
        combat_event = self.combat_event
        if not cc or not combat_event:
            return
        summary: list[str] = []
        loot_ids = cc.collect_loot()
        for item_id in loot_ids:
            item = registry.get_item(item_id)
            if item:
                summary.append(item.name)
        self._rolled_gold = 0
        if hasattr(combat_event, "money_drop") and combat_event.money_drop[1] > 0:
            lo, hi = combat_event.money_drop
            killed = sum(1 for m in combat_event.monsters if not m.is_alive)
            base = random.randint(lo, hi) if hi > 0 else 0
            self._rolled_gold = base * max(killed, 1)
            if self._rolled_gold > 0:
                summary.append(f"+{self._rolled_gold} gold")
        self.loot_summary = summary if summary else None

    def _handle_combat_end_input(self, event):
        cc = self.combat_controller
        gc = self.gc

        if cc.state == CombatState.DEFEAT:
            if event.key == pygame.K_UP:
                self.game_over_selection = (self.game_over_selection - 1) % 2
            elif event.key == pygame.K_DOWN:
                self.game_over_selection = (self.game_over_selection + 1) % 2
            elif event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                if self.game_over_selection == 0:
                    gc.pending_action = "load"
                else:
                    gc.pending_action = "quit"
                self.end()
            return

        if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
            self._finalize()

    def _finalize(self):
        cc = self.combat_controller
        gc = self.gc
        combat_event = self.combat_event

        if cc.state == CombatState.VICTORY:
            combat_event.resolved = True
            loot_ids = cc.collect_loot()
            for item_id in loot_ids:
                item = registry.get_item(item_id)
                if item:
                    gc.player.add_to_inventory(item.clone())
            money = self._rolled_gold
            if not money and hasattr(combat_event, "money_drop") and combat_event.money_drop[1] > 0:
                money = random.randint(combat_event.money_drop[0], combat_event.money_drop[1])
            if money > 0:
                gc.player.add_money(money)

            gc.maze.grid[gc.player.y][gc.player.x] = 0

            killed = sum(1 for m in combat_event.monsters if not m.is_alive)
            gc.stats["monsters_killed"] += killed
            gc.player.combat_record["monsters_killed"] += killed
            gc.player.combat_record["combats_won"] += 1

            is_gate = getattr(combat_event, "is_gate", False)
            if not is_gate:
                gc.resolved_encounters += 1
                gc._check_door_reveal()
            else:
                gc.gate_cleared = True
                if gc.maze.door_position:
                    gc.maze.place_door_tile()
                gc.dialogue_box.set_item_message("The guardian falls! The exit door appears!")
                gc.item_message_active = True
                if gc.sfx:
                    gc.sfx.play("door_open")
            gc.quest_manager.on_event_resolved(combat_event.id, gc.player)

            npc_source = gc._npc_combat_map.pop(combat_event.id, None)
            if npc_source:
                npc_source.combat_defeated = True
                npc_source.color = (0, 255, 255)
                for qid, quest in gc.quests.items():
                    if getattr(quest, "target_npc_id", None) == npc_source.id and quest.status == "active":
                        gc.quest_manager.complete_quest(quest, gc.player)
                        break

        self.end()

    def end(self):
        self.combat_controller = None
        self.combat_view = None
        self.combat_event = None
        if hasattr(self.gc, "day_night"):
            self.gc.day_night.resume()
