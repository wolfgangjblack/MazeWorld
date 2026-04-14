"""Event input handler — extracted from GameController.

Manages input for puzzle, event, and legacy dialogue-box combat encounters.
"""

import random
import pygame
from src.systems.day_night import apply_combat_rest
from src.registry import registry


class EventInputHandler:
    """Handles all input for non-CombatController event encounters."""

    def __init__(self, gc):
        self.gc = gc
        self.event_selected_choice = 0
        self.combat_target_index = 0

    def handle_input(self, event) -> None:
        gc = self.gc
        current_event = gc.dialogue_box.current_event
        if not current_event:
            return

        if event.key == pygame.K_PAGEUP:
            gc.game_view.encounter_view.scroll_content(-1)
            return
        if event.key == pygame.K_PAGEDOWN:
            gc.game_view.encounter_view.scroll_content(1)
            return

        choosing = (current_event.type in ("puzzle", "event")
                    and not gc.dialogue_box.event_context.get("result")
                    and not gc.dialogue_box.awaiting_roll)
        if not choosing and event.key in (pygame.K_UP, pygame.K_DOWN):
            direction = -1 if event.key == pygame.K_UP else 1
            gc.game_view.encounter_view.scroll_content(direction)
            return

        if gc.dialogue_box.combat_active:
            self._handle_combat_input(event)
            return

        if gc.dialogue_box.awaiting_roll:
            if event.key == pygame.K_r:
                if gc.sfx:
                    gc.sfx.play("dice_roll")
                dice_roll = random.randint(1, 20)
                if current_event.type == "combat":
                    result = current_event.resolve(dice_roll, gc.player)
                elif current_event.type == "puzzle":
                    choice_idx = gc.dialogue_box.event_context.get("selected_choice", 0)
                    result = current_event.resolve(choice_idx, dice_roll, gc.player)
                elif current_event.type == "event":
                    choice_idx = gc.dialogue_box.event_context.get("selected_choice", 0)
                    result = current_event.resolve(choice_idx, dice_roll, gc.player)
                else:
                    result = {"success": False, "message": "Unknown event type."}

                self._apply_event_result(result, current_event)
                return

            if event.key == pygame.K_ESCAPE:
                self._end_event()
                return

        elif current_event.type in ("puzzle", "event") and not gc.dialogue_box.event_context.get("result"):
            rendered = gc.dialogue_box.event_context.get("rendered_choices", [])
            total_choices = len(rendered) if rendered else len(getattr(current_event, 'choices', []))

            if event.key == pygame.K_UP:
                self.event_selected_choice = (self.event_selected_choice - 1) % max(total_choices, 1)
                gc.dialogue_box.event_context["highlight"] = self.event_selected_choice
                gc.game_view.encounter_view.ensure_choice_visible(self.event_selected_choice)
                return
            if event.key == pygame.K_DOWN:
                self.event_selected_choice = (self.event_selected_choice + 1) % max(total_choices, 1)
                gc.dialogue_box.event_context["highlight"] = self.event_selected_choice
                gc.game_view.encounter_view.ensure_choice_visible(self.event_selected_choice)
                return

            if event.key == pygame.K_RETURN:
                idx = self.event_selected_choice
                if rendered and 0 <= idx < len(rendered):
                    rc = rendered[idx]
                    if not rc.get("available", True):
                        return
                    if rc["kind"] == "tool":
                        result = current_event.resolve_with_tool(gc.player)
                        self._apply_event_result(result, current_event)
                    elif rc["kind"] == "ability":
                        result = current_event.resolve_with_ability(gc.player)
                        self._apply_event_result(result, current_event)
                    elif rc["kind"] == "spell":
                        result = current_event.resolve_with_spell(gc.player)
                        self._apply_event_result(result, current_event)
                    elif rc["kind"] == "walk_away":
                        result = current_event.resolve(rc["choice_idx"], 0, gc.player)
                        self._apply_event_result(result, current_event)
                    else:
                        gc.dialogue_box.event_context["selected_choice"] = rc["choice_idx"]
                        gc.dialogue_box.awaiting_roll = True
                    self.event_selected_choice = 0
                    return
                choices = getattr(current_event, 'choices', [])
                if choices and 0 <= idx < len(choices):
                    gc.dialogue_box.event_context["selected_choice"] = idx
                    gc.dialogue_box.awaiting_roll = True
                    if choices[idx].auto_success:
                        result = current_event.resolve(idx, 0, gc.player)
                        self._apply_event_result(result, current_event)
                    self.event_selected_choice = 0
                    return

            if rendered:
                for i in range(min(len(rendered), 9)):
                    if event.key == getattr(pygame, f'K_{i+1}', None):
                        self.event_selected_choice = i
                        gc.dialogue_box.event_context["highlight"] = i
                        rc = rendered[i]
                        if not rc.get("available", True):
                            return
                        if rc["kind"] == "tool":
                            result = current_event.resolve_with_tool(gc.player)
                            self._apply_event_result(result, current_event)
                        elif rc["kind"] == "ability":
                            result = current_event.resolve_with_ability(gc.player)
                            self._apply_event_result(result, current_event)
                        elif rc["kind"] == "spell":
                            result = current_event.resolve_with_spell(gc.player)
                            self._apply_event_result(result, current_event)
                        elif rc["kind"] == "walk_away":
                            result = current_event.resolve(rc["choice_idx"], 0, gc.player)
                            self._apply_event_result(result, current_event)
                        else:
                            gc.dialogue_box.event_context["selected_choice"] = rc["choice_idx"]
                            gc.dialogue_box.awaiting_roll = True
                        self.event_selected_choice = 0
                        return

            if event.key == pygame.K_ESCAPE:
                self.event_selected_choice = 0
                self._end_event()
                return
        else:
            if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self._end_event()
                return

    def _apply_event_result(self, result: dict, current_event):
        gc = self.gc
        gc.dialogue_box.event_context["result"] = result
        gc.dialogue_box.event_context.setdefault("dice_roll", 0)
        gc.dialogue_box.awaiting_roll = False

        if result.get("success"):
            if gc.sfx:
                gc.sfx.play("event_complete")
            reward_names: list[str] = []
            if result.get("reward_item_id"):
                reward_item = registry.get_item(result["reward_item_id"])
                if reward_item:
                    gc.player.add_to_inventory(reward_item.clone())
                    reward_names.append(reward_item.name)
            for loot_id in result.get("loot_item_ids", []):
                loot_item = registry.get_item(loot_id)
                if loot_item:
                    gc.player.add_to_inventory(loot_item.clone())
                    reward_names.append(loot_item.name)
            money = result.get("money_dropped", 0)
            if money > 0:
                gc.player.add_money(money)
            msg = result.get("message", "")
            if reward_names:
                msg += f" Received: {', '.join(reward_names)}."
            if money > 0:
                msg += f" Found {money} gold."
            result["message"] = msg
        else:
            if gc.sfx and result.get("damage"):
                gc.sfx.play("player_take_damage")

        if not result.get("walked_away"):
            current_event.resolved = True
            gc.maze.grid[gc.player.y][gc.player.x] = 0
            if result.get("success"):
                gc.quest_manager.on_event_resolved(current_event.id, gc.player)
            else:
                gc.quest_manager.on_event_failed(current_event.id, gc.player)

            if current_event.type == "puzzle":
                if result.get("success"):
                    gc.player.encounter_record["puzzles_solved"] += 1
                else:
                    gc.player.encounter_record["puzzles_failed"] += 1
            elif current_event.type == "event":
                if result.get("success"):
                    gc.player.encounter_record["events_resolved"] += 1
                else:
                    gc.player.encounter_record["events_failed"] += 1

            gc.resolved_encounters += 1
            gc._check_door_reveal()

    def _end_event(self):
        gc = self.gc
        gc.dialogue_box.end_event()
        if hasattr(gc, 'day_night'):
            gc.day_night.resume()

    def _handle_combat_input(self, event):
        gc = self.gc
        combat_event = gc.dialogue_box.current_event
        phase = gc.dialogue_box.combat_phase

        if phase == "initiative":
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                init_result = combat_event.start_combat(gc.player)
                gc.dialogue_box.start_combat_turns(init_result)
                gc.dialogue_box.combat_log = list(combat_event.combat_log)
                self.combat_target_index = 0
                self._advance_combat_to_next_turn(combat_event)
            elif event.key == pygame.K_ESCAPE:
                self._end_event()
            return

        if phase == "player_turn":
            if gc.dialogue_box.player_stunned_turns > 0:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    gc.dialogue_box.player_stunned_turns -= 1
                    gc.dialogue_box.add_combat_log("You shake off the stun.")
                    combat_event.advance_turn()
                    self._advance_combat_to_next_turn(combat_event)
                return

            if event.key == pygame.K_UP:
                alive_indices = [i for i, m in enumerate(combat_event.monsters) if m.is_alive]
                if alive_indices:
                    curr = alive_indices.index(self.combat_target_index) if self.combat_target_index in alive_indices else 0
                    curr = (curr - 1) % len(alive_indices)
                    self.combat_target_index = alive_indices[curr]
                return

            if event.key == pygame.K_DOWN:
                alive_indices = [i for i, m in enumerate(combat_event.monsters) if m.is_alive]
                if alive_indices:
                    curr = alive_indices.index(self.combat_target_index) if self.combat_target_index in alive_indices else 0
                    curr = (curr + 1) % len(alive_indices)
                    self.combat_target_index = alive_indices[curr]
                return

            if event.key == pygame.K_a:
                self._apply_player_poison()
                gc.day_night.advance(1)
                result = combat_event.player_attack(gc.player, self.combat_target_index)
                gc.dialogue_box.combat_log = list(combat_event.combat_log)
                outcome = combat_event.is_combat_over()
                if outcome == "victory":
                    self._handle_combat_victory(combat_event)
                    return
                combat_event.advance_turn()
                self._advance_combat_to_next_turn(combat_event)
                return

            if event.key == pygame.K_r:
                self._apply_player_poison()
                gc.day_night.advance(1)
                msg = apply_combat_rest(gc.player)
                gc.dialogue_box.add_combat_log(msg)
                combat_event.combat_log.append(msg)
                combat_event.advance_turn()
                self._advance_combat_to_next_turn(combat_event)
                return

            if event.key == pygame.K_f:
                result = combat_event.try_flee(gc.player)
                gc.dialogue_box.combat_log = list(combat_event.combat_log)
                if result["success"]:
                    gc.player.combat_record["combats_fled"] += 1
                    gc.dialogue_box.set_combat_phase("fled")
                    return
                combat_event.advance_turn()
                self._advance_combat_to_next_turn(combat_event)
                return

            if event.key == pygame.K_i:
                message = gc.player.use_item()
                gc.dialogue_box.add_combat_log(f"Item: {message}")
                combat_event.combat_log.append(f"Item: {message}")
                combat_event.advance_turn()
                self._advance_combat_to_next_turn(combat_event)
                return

            return

        if phase == "monster_turn":
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._execute_monster_turn(combat_event)
            return

        if phase in ("victory", "defeat", "fled"):
            if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self._finalize_combat(combat_event)
            return

    def _advance_combat_to_next_turn(self, combat_event):
        gc = self.gc
        outcome = combat_event.is_combat_over()
        if outcome == "victory":
            self._handle_combat_victory(combat_event)
            return
        if gc.player.health <= 0:
            gc.dialogue_box.set_combat_phase("defeat")
            gc.dialogue_box.add_combat_log("You have been defeated...")
            return

        turn = combat_event.get_current_turn()
        if not turn:
            return

        if turn["type"] == "player":
            gc.dialogue_box.set_combat_phase("player_turn")
            alive = [i for i, m in enumerate(combat_event.monsters) if m.is_alive]
            if alive and self.combat_target_index not in alive:
                self.combat_target_index = alive[0]
        else:
            gc.dialogue_box.set_combat_phase("monster_turn")
            self._execute_monster_turn(combat_event)

    def _execute_monster_turn(self, combat_event):
        gc = self.gc
        turn = combat_event.get_current_turn()
        if not turn or turn["type"] != "monster":
            combat_event.advance_turn()
            self._advance_combat_to_next_turn(combat_event)
            return

        monster_idx = turn["index"]
        result = combat_event.monster_turn(monster_idx, gc.player)
        gc.dialogue_box.combat_log = list(combat_event.combat_log)

        if result.get("effect") == "stun":
            gc.dialogue_box.player_stunned_turns = 1
        if result.get("effect") == "poison":
            gc.dialogue_box.player_poison_turns = result.get("duration", 2)

        if gc.player.health <= 0:
            gc.dialogue_box.set_combat_phase("defeat")
            gc.dialogue_box.add_combat_log("You have been defeated...")
            return

        combat_event.advance_turn()
        self._advance_combat_to_next_turn(combat_event)

    def _apply_player_poison(self):
        gc = self.gc
        if gc.dialogue_box.player_poison_turns > 0:
            poison_dmg = random.randint(1, 4)
            gc.player.health = max(0, gc.player.health - poison_dmg)
            gc.dialogue_box.add_combat_log(f"Poison deals {poison_dmg} damage to you!")
            gc.dialogue_box.player_poison_turns -= 1

    def _handle_combat_victory(self, combat_event):
        gc = self.gc
        gc.dialogue_box.set_combat_phase("victory")
        combat_event.resolved = True
        gc.dialogue_box.add_combat_log("Victory!")
        if gc.sfx:
            gc.sfx.play("event_complete")

        if hasattr(combat_event, 'monsters'):
            killed = sum(1 for m in combat_event.monsters if not m.is_alive)
            gc.stats["monsters_killed"] += killed
            gc.player.combat_record["monsters_killed"] += killed
        gc.player.combat_record["combats_won"] += 1
        if getattr(combat_event, 'is_climax_boss', False):
            gc.resolved_encounters += 1
            gc.gate_cleared = True
            gc.pending_action = "victory"
        elif not getattr(combat_event, 'is_gate', False):
            gc.resolved_encounters += 1
            gc._check_door_reveal()
        else:
            gc.gate_cleared = True

        loot_ids = combat_event.collect_loot()
        for item_id in loot_ids:
            item = registry.get_item(item_id)
            if item:
                gc.player.add_to_inventory(item.clone())
                gc.dialogue_box.add_combat_log(f"Loot: {item.name}")

    def _finalize_combat(self, combat_event):
        gc = self.gc
        if combat_event.resolved:
            gc.maze.grid[gc.player.y][gc.player.x] = 0
            gc.quest_manager.on_event_resolved(combat_event.id, gc.player)

        self._end_event()

        if gc.player.health <= 0:
            if gc.sfx:
                gc.sfx.play("player_death")
            gc.pending_action = "game_over"
