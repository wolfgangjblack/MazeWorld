import random
import pygame
from src.views.gameplay_view import GameView
from src.views.shop_view import ShopView
from src.models.npc import RandomNPC, AggressiveNPC, MerchantNPC
from src.models.items import EscortItem
from src.models.follower import Follower
from src.registry import registry
from src.utils.conversation_utils import has_dialogue_choices
from src.systems.survival import SurvivalSystem


class GameController:
    def __init__(self, screen, font, maze, player, npcs, dialogue_box,
                 events=None, quests=None):
        self.screen = screen
        self.font = font
        self.maze = maze
        self.player = player
        self.npcs = npcs
        self.dialogue_box = dialogue_box
        self.events = events or {}
        self.quests = quests or {}

        # Build a lookup from grid position to event id
        self.event_position_map: dict[tuple[int, int], str] = {}
        self._build_event_position_map()

        # Check for kill quests already cleared at startup
        self._check_kill_quests_already_cleared()

        # Survival system
        self.survival = SurvivalSystem()

        # UI / State variables
        self.inventory_active = False
        self.item_detail_active = False
        self.quest_log_active = False
        self.item_message_active = False
        self.item_message = None
        self.player_at_item = False
        self.current_npc = None
        self.running = True
        self.debug_reveal = False

        # Shop state
        self.shop_active = False
        self.shop_npc = None
        self.shop_view = None

        # Combat target selection
        self.combat_target_index = 0

        # Player menu / save-load state
        self.player_menu_active = False
        self.pending_action = None  # Set to "save", "load", "quit", "open_pause", "open_menu" to signal main loop

        self.game_view = GameView(screen, font, dialogue_box)

    def _build_event_position_map(self):
        """Map event tile positions to event IDs using maze data."""
        if not self.events:
            return
        try:
            from src.utils.dataloader_utils import load_json_data
            import os
            if os.path.exists("data/maze/maze.json"):
                maze_data = load_json_data("data/maze/maze.json")
                for ep in maze_data.get("event_positions", []):
                    self.event_position_map[(ep["x"], ep["y"])] = ep["event_id"]
        except Exception:
            pass

    def _check_kill_quests_already_cleared(self):
        """Kill quests are completable out of order — if encounter already cleared."""
        for qid, quest in self.quests.items():
            if quest.type != "combat" or quest.status != "not_started":
                continue
            target_eid = getattr(quest, 'target_event_id', '')
            if target_eid:
                event = self.events.get(target_eid)
                if event and getattr(event, 'resolved', False):
                    quest.status = "completed"
                    self.player.complete_quest(qid)

    @property
    def has_active_overlay(self) -> bool:
        """True if any modal UI is open (dialogue, event, or shop)."""
        return (
            self.dialogue_box.event_active
            or self.dialogue_box.dialogue_active
            or self.shop_active
        )

    def run(self) -> str | None:
        """Main game loop. Returns 'open_menu' when the player opens the menu, or None on window close."""
        clock = pygame.time.Clock()

        while self.running:
            current_time = pygame.time.get_ticks()
            self.handle_events()
            self.update(current_time)
            self.draw(current_time)
            pygame.display.flip()
            clock.tick(60)

            # Check if game controller wants to hand control back
            if self.pending_action:
                action = self.pending_action
                self.pending_action = None
                return action

        return None

    def handle_events(self):
        """Handle all pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN:
                self.handle_keydown(event)

    def _get_event_at_player(self):
        """Return the Event object at the player's position, or None."""
        pos = (self.player.x, self.player.y)
        event_id = self.event_position_map.get(pos)
        if event_id:
            return self.events.get(event_id)
        return None

    def after_move_check(self):
        if self.player.is_on_event_tile(self.maze):
            event = self._get_event_at_player()
            if event and not event.resolved:
                self.dialogue_box.start_event(event)
            else:
                self.maze.grid[self.player.y][self.player.x] = 0
        else:
            self.player_at_item = self.player.is_item_at_player_position(self.maze)
            self.current_npc = self.player.get_nearby_npc(self.npcs)

        self._check_escort_completion()

    def handle_keydown(self, event):
        # 0. If an event is active
        if self.dialogue_box.event_active:
            self._handle_event_input(event)
            return

        # 0.5. If shop is active
        if self.shop_active:
            self._handle_shop_input(event)
            return

        # 1. If an item message is active
        if self.item_message_active:
            if event.key == pygame.K_RETURN:
                self.item_message_active = False
                self.dialogue_box.clear_item_message()
                return
            if event.key == pygame.K_ESCAPE:
                return
            return

        # 2. If inventory is active
        if self.inventory_active:
            if self.item_detail_active:
                if event.key in (pygame.K_ESCAPE, pygame.K_d):
                    self.item_detail_active = False
                return
            if event.key == pygame.K_ESCAPE:
                self.inventory_active = False
                self.item_detail_active = False
                return
            else:
                self.handle_inventory_input(event)
                return

        # 3. If dialogue is active (NPC conversation)
        if self.dialogue_box.dialogue_active:
            if event.key == pygame.K_ESCAPE:
                self.dialogue_box.end_dialogue()
                self.current_npc = None
                return
            if event.key == pygame.K_UP:
                self.dialogue_box.scroll_up()
                return
            if event.key == pygame.K_DOWN:
                self.dialogue_box.scroll_down()
                return
            if self.dialogue_box.generating:
                return
            if event.key == pygame.K_RETURN and self.dialogue_box.input_active:
                self.dialogue_box.update_dialogue(self.dialogue_box.user_message)
                return
            if self.dialogue_box.input_active:
                # Numeric selection for offline_static dialogue choices
                if has_dialogue_choices(self.current_npc):
                    tree = self.current_npc.dialogue_tree
                    nodes = tree.get("nodes", {})
                    current_id = tree.get("_current", "start")
                    node = nodes.get(current_id, nodes.get("start", {}))
                    choices = node.get("choices", [])
                    # Keys 1-9 only; pygame has no K_10+ constants
                    for i in range(min(len(choices), 9)):
                        if event.key == getattr(pygame, f'K_{i+1}', None):
                            self.dialogue_box.update_dialogue(str(i + 1))
                            return
                    if event.key != pygame.K_ESCAPE:
                        return
                if event.key == pygame.K_BACKSPACE:
                    self.dialogue_box.user_message = self.dialogue_box.user_message[:-1]
                else:
                    self.dialogue_box.user_message += event.unicode
                return
            return

        # 4. Normal gameplay
        if event.key in [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN]:
            dx, dy = 0, 0
            if event.key == pygame.K_LEFT:
                dx, dy = -1, 0
            elif event.key == pygame.K_RIGHT:
                dx, dy = 1, 0
            elif event.key == pygame.K_UP:
                dx, dy = 0, -1
            elif event.key == pygame.K_DOWN:
                dx, dy = 0, 1
            self.player.move(dx=dx, dy=dy, maze=self.maze, survival_system=self.survival)
            # Check for game over from starvation
            if self.player.health <= 0:
                self.pending_action = "game_over"
                return
            self.after_move_check()
            return

        if event.key == pygame.K_RETURN:
            if self.player_at_item:
                item_message = self.player.pick_up_item(self.maze)
                self.item_message_active = True
                self.player_at_item = False
                self.dialogue_box.set_item_message(item_message)
                return
            if self.current_npc:
                self._handle_npc_interaction(self.current_npc)
                return

        if event.key == pygame.K_s:
            if self.current_npc and isinstance(self.current_npc, MerchantNPC):
                self._open_shop(self.current_npc)
                return

        if event.key == pygame.K_i:
            self.inventory_active = not self.inventory_active
            self.quest_log_active = False
            return

        if event.key == pygame.K_q:
            self.quest_log_active = not self.quest_log_active
            self.inventory_active = False
            return

        if event.key == pygame.K_t:
            self._talk_to_follower()
            return

        # Player menu (save/load)
        if event.key == pygame.K_TAB:
            self.pending_action = "open_menu"
            return

        # Available in all builds (including packaged exe) for troubleshooting
        if event.key == pygame.K_F1:
            self.debug_reveal = not self.debug_reveal
            return

        if event.key == pygame.K_ESCAPE:
            if self.quest_log_active:
                self.quest_log_active = False
                return
            # Esc opens pause menu in normal gameplay
            self.pending_action = "open_pause"
            return

        # M key opens full tabbed menu
        if event.key == pygame.K_m:
            self.pending_action = "open_full_menu"
            return

    def _handle_event_input(self, event):
        """Handle keyboard input during an active event.

        TODO Phase 8: Check time_gate before triggering encounters.
        Changes needed:
          - DayNightCycle system must be instantiated and tracked in GameController
          - In _handle_event_input: skip trigger if event.time_gate doesn't match current period
          - In _handle_npc_interaction: skip quest offer if quest.time_gate doesn't match
          - EventChoice.time_gate should gate individual choices within events
          - Encounters with time_gate set should remain invisible when walked over at wrong time
          - See PDR sections 4.3 (Encounters) and 4.11 (Day/Night) for full spec
        """
        current_event = self.dialogue_box.current_event
        if not current_event:
            return

        # Multi-turn combat
        if self.dialogue_box.combat_active:
            self._handle_combat_input(event)
            return

        # Legacy/simple event handling
        if self.dialogue_box.awaiting_roll:
            if event.key == pygame.K_r:
                dice_roll = random.randint(1, 20)
                if current_event.type == "combat":
                    result = current_event.resolve(dice_roll, self.player)
                elif current_event.type == "puzzle":
                    choice_idx = self.dialogue_box.event_context.get("selected_choice", 0)
                    result = current_event.resolve(choice_idx, dice_roll, self.player)
                elif current_event.type == "event":
                    choice_idx = self.dialogue_box.event_context.get("selected_choice", 0)
                    result = current_event.resolve(choice_idx, dice_roll, self.player)
                else:
                    result = {"success": False, "message": "Unknown event type."}

                self.dialogue_box.event_context["result"] = result
                self.dialogue_box.event_context["dice_roll"] = dice_roll
                self.dialogue_box.awaiting_roll = False

                if result.get("success"):
                    if result.get("reward_item_id"):
                        reward_item = registry.get_item(result["reward_item_id"])
                        if reward_item:
                            self.player.add_to_inventory(reward_item.clone())
                    # Handle loot drops from combat
                    for loot_id in result.get("loot_item_ids", []):
                        loot_item = registry.get_item(loot_id)
                        if loot_item:
                            self.player.add_to_inventory(loot_item.clone())

                # Walk-away for event encounters: don't resolve
                if result.get("walked_away"):
                    pass  # Event stays active
                elif current_event.resolved:
                    self.maze.grid[self.player.y][self.player.x] = 0

                    for qid, quest in self.quests.items():
                        if (quest.type == "combat"
                                and getattr(quest, 'target_event_id', '') == current_event.id
                                and quest.status == "active"):
                            quest.status = "completed"
                            self.player.complete_quest(qid)
                return

            if event.key == pygame.K_ESCAPE:
                self.dialogue_box.end_event()
                return

        elif current_event.type in ("puzzle", "event") and not self.dialogue_box.event_context.get("result"):
            choices = getattr(current_event, 'choices', [])
            if choices:
                for i in range(len(choices)):
                    if event.key == getattr(pygame, f'K_{i+1}', None):
                        self.dialogue_box.event_context["selected_choice"] = i
                        self.dialogue_box.awaiting_roll = True
                        if choices[i].auto_success:
                            result = current_event.resolve(i, 0, self.player)
                            self.dialogue_box.event_context["result"] = result
                            self.dialogue_box.awaiting_roll = False
                        return

            if event.key == pygame.K_ESCAPE:
                self.dialogue_box.end_event()
                return
        else:
            if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self.dialogue_box.end_event()
                return

    def _handle_combat_input(self, event):
        """Handle input during multi-turn combat."""
        combat_event = self.dialogue_box.current_event
        phase = self.dialogue_box.combat_phase

        if phase == "initiative":
            # Press Enter or Space to roll initiative
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                init_result = combat_event.start_combat(self.player)
                self.dialogue_box.start_combat_turns(init_result)
                self.dialogue_box.combat_log = list(combat_event.combat_log)
                self.combat_target_index = 0
                self._advance_combat_to_next_turn(combat_event)
            elif event.key == pygame.K_ESCAPE:
                self.dialogue_box.end_event()
            return

        if phase == "player_turn":
            if self.dialogue_box.player_stunned_turns > 0:
                # Stunned: any key skips turn
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.dialogue_box.player_stunned_turns -= 1
                    self.dialogue_box.add_combat_log("You shake off the stun.")
                    combat_event.advance_turn()
                    self._advance_combat_to_next_turn(combat_event)
                return

            # A = Attack, F = Flee, I = use Item, Up/Down = select target
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
                # Apply poison damage before player acts
                self._apply_player_poison()

                result = combat_event.player_attack(self.player, self.combat_target_index)
                self.dialogue_box.combat_log = list(combat_event.combat_log)

                outcome = combat_event.is_combat_over()
                if outcome == "victory":
                    self._handle_combat_victory(combat_event)
                    return
                combat_event.advance_turn()
                self._advance_combat_to_next_turn(combat_event)
                return

            if event.key == pygame.K_f:
                result = combat_event.try_flee(self.player)
                self.dialogue_box.combat_log = list(combat_event.combat_log)

                if result["success"]:
                    self.dialogue_box.set_combat_phase("fled")
                    return

                # Flee failed — monsters still get their turns
                combat_event.advance_turn()
                self._advance_combat_to_next_turn(combat_event)
                return

            if event.key == pygame.K_i:
                # Use selected item in combat
                message = self.player.use_item()
                self.dialogue_box.add_combat_log(f"Item: {message}")
                combat_event.combat_log.append(f"Item: {message}")
                combat_event.advance_turn()
                self._advance_combat_to_next_turn(combat_event)
                return

            return

        if phase == "monster_turn":
            # Auto-advance monster turns on any keypress (or auto in update)
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._execute_monster_turn(combat_event)
            return

        if phase in ("victory", "defeat", "fled"):
            if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self._finalize_combat(combat_event)
            return

    def _advance_combat_to_next_turn(self, combat_event):
        """Set the phase based on whose turn it is."""
        outcome = combat_event.is_combat_over()
        if outcome == "victory":
            self._handle_combat_victory(combat_event)
            return
        if self.player.health <= 0:
            self.dialogue_box.set_combat_phase("defeat")
            self.dialogue_box.add_combat_log("You have been defeated...")
            return

        turn = combat_event.get_current_turn()
        if not turn:
            return

        if turn["type"] == "player":
            self.dialogue_box.set_combat_phase("player_turn")
            # Auto-select first alive target
            alive = [i for i, m in enumerate(combat_event.monsters) if m.is_alive]
            if alive and self.combat_target_index not in alive:
                self.combat_target_index = alive[0]
        else:
            self.dialogue_box.set_combat_phase("monster_turn")
            # Auto-execute monster turn after brief display
            self._execute_monster_turn(combat_event)

    def _execute_monster_turn(self, combat_event):
        """Execute the current monster's turn."""
        turn = combat_event.get_current_turn()
        if not turn or turn["type"] != "monster":
            combat_event.advance_turn()
            self._advance_combat_to_next_turn(combat_event)
            return

        monster_idx = turn["index"]
        result = combat_event.monster_turn(monster_idx, self.player)
        self.dialogue_box.combat_log = list(combat_event.combat_log)

        # Track stun/poison on player
        if result.get("effect") == "stun":
            self.dialogue_box.player_stunned_turns = 1
        if result.get("effect") == "poison":
            self.dialogue_box.player_poison_turns = result.get("duration", 2)

        if self.player.health <= 0:
            self.dialogue_box.set_combat_phase("defeat")
            self.dialogue_box.add_combat_log("You have been defeated...")
            return

        combat_event.advance_turn()
        self._advance_combat_to_next_turn(combat_event)

    def _apply_player_poison(self):
        """Apply poison damage to player if poisoned."""
        if self.dialogue_box.player_poison_turns > 0:
            poison_dmg = random.randint(1, 4)
            self.player.health = max(0, self.player.health - poison_dmg)
            self.dialogue_box.add_combat_log(f"Poison deals {poison_dmg} damage to you!")
            self.dialogue_box.player_poison_turns -= 1

    def _handle_combat_victory(self, combat_event):
        """Handle victory: collect loot, mark resolved."""
        self.dialogue_box.set_combat_phase("victory")
        combat_event.resolved = True
        self.dialogue_box.add_combat_log("Victory!")

        # Collect loot
        loot_ids = combat_event.collect_loot()
        for item_id in loot_ids:
            item = registry.get_item(item_id)
            if item:
                self.player.add_to_inventory(item.clone())
                self.dialogue_box.add_combat_log(f"Loot: {item.name}")

    def _finalize_combat(self, combat_event):
        """Clean up after combat ends."""
        if combat_event.resolved:
            self.maze.grid[self.player.y][self.player.x] = 0
            # Check quest completion
            for qid, quest in self.quests.items():
                if (quest.type == "combat"
                        and getattr(quest, 'target_event_id', '') == combat_event.id
                        and quest.status == "active"):
                    quest.status = "completed"
                    self.player.complete_quest(qid)

        self.dialogue_box.end_event()

        # Check for player death after combat
        if self.player.health <= 0:
            self.pending_action = "game_over"

    def _handle_npc_interaction(self, npc):
        """Start dialogue with an NPC, handling quest offers and completions."""
        self._check_quest_turn_in(npc)

        self.dialogue_box.start_dialogue(npc)

        if npc.quest_id and npc.quest_id in self.quests:
            quest = self.quests[npc.quest_id]
            if quest.status == "not_started":
                prereq = quest.prerequisite_quest_id
                if not prereq or self.player.has_completed(prereq):
                    quest.status = "active"
                    self.player.accept_quest(quest.id)

                    # Also activate first sub-quest for multi-step
                    if quest.type == "multi_step":
                        first_sub = quest.get_current_sub_quest_id()
                        if first_sub and first_sub in self.quests:
                            sub = self.quests[first_sub]
                            if sub.status == "not_started":
                                sub.status = "active"
                                self.player.accept_quest(sub.id)

                    if quest.type == "escort" and hasattr(quest, 'escort_npc_id'):
                        self._start_follower_escort(quest, npc)

                    # Check if kill quest target already cleared
                    if quest.type == "combat":
                        target_eid = getattr(quest, 'target_event_id', '')
                        event = self.events.get(target_eid)
                        if event and getattr(event, 'resolved', False):
                            self._complete_quest(quest)

    def _check_quest_turn_in(self, npc):
        """Check if any active quests can be completed by talking to this NPC."""
        for qid, quest in list(self.quests.items()):
            if quest.status != "active" or qid not in self.player.active_quests:
                continue

            if quest.type == "fetch" and quest.giver_npc_id == npc.id:
                completed = True
                for req in getattr(quest, 'target_items', []):
                    item_id = req["item_id"]
                    count = req.get("count", 1)
                    item_obj = registry.get_item(item_id)
                    if item_obj and item_obj.name in self.player.inventory:
                        if self.player.inventory[item_obj.name].quantity >= count:
                            continue
                    completed = False
                    break
                if completed:
                    for req in getattr(quest, 'target_items', []):
                        item_obj = registry.get_item(req["item_id"])
                        if item_obj:
                            for _ in range(req.get("count", 1)):
                                self.player.remove_from_inventory(item_obj.name)
                    self._complete_quest(quest)

            elif quest.type == "delivery" and getattr(quest, 'target_npc_id', None) == npc.id:
                delivery_item = registry.get_item(getattr(quest, 'delivery_item_id', 0))
                if delivery_item and delivery_item.name in self.player.inventory:
                    self.player.remove_from_inventory(delivery_item.name)
                    self._complete_quest(quest)

    def _complete_quest(self, quest):
        """Mark quest as completed and grant reward."""
        quest.status = "completed"
        self.player.complete_quest(quest.id)
        reward_msg = f"Quest completed: {quest.title}!"
        if quest.reward:
            if quest.reward.item_id:
                reward = registry.get_item(quest.reward.item_id)
                if reward:
                    self.player.add_to_inventory(reward.clone())
            money = getattr(quest.reward, 'money', 0)
            if money > 0:
                self.player.add_money(money)
                reward_msg += f" +{money} gold!"

        # Remove follower if escort quest
        if quest.type == "escort":
            follower = self.player.get_follower_by_quest(quest.id)
            if follower:
                farewell = follower.farewell_text
                self.player.remove_follower(follower.npc_id)
                self.dialogue_box.set_item_message(
                    f"{reward_msg} {follower.name}: {farewell}")
                self.item_message_active = True
                self._check_multi_step_progress(quest.id)
                return

        self.dialogue_box.set_item_message(reward_msg)
        self.item_message_active = True
        self._check_multi_step_progress(quest.id)

    def _check_escort_completion(self):
        """Check if any active escort quest target zone has been reached."""
        for item_name, item in list(self.player.inventory.items()):
            if isinstance(item, EscortItem):
                tx, ty = item.target_zone
                if abs(self.player.x - tx) <= 2 and abs(self.player.y - ty) <= 2:
                    self.player.remove_from_inventory(item_name)
                    for qid, quest in self.quests.items():
                        if (quest.type == "escort"
                                and getattr(quest, 'escort_npc_id', None) == item.npc_id
                                and quest.status == "active"):
                            quest.status = "completed"
                            self.player.complete_quest(qid)
                            if quest.reward and quest.reward.item_id:
                                reward = registry.get_item(quest.reward.item_id)
                                if reward:
                                    self.player.add_to_inventory(reward.clone())
                    self.dialogue_box.set_item_message("Your escort has arrived safely!")
                    self.item_message_active = True

    def _talk_to_follower(self):
        """Talk to the first follower for hints/personality."""
        if not self.player.followers:
            self.dialogue_box.set_item_message("No followers to talk to.")
            self.item_message_active = True
            return
        follower = self.player.followers[0]
        hint = follower.get_hint()
        self.dialogue_box.set_item_message(f"{follower.name}: {hint}")
        self.item_message_active = True

    def _start_follower_escort(self, quest, npc):
        """Start an escort quest by adding the NPC as a follower."""
        escort_npc_id = getattr(quest, 'escort_npc_id', None)
        if not escort_npc_id:
            return
        npc_to_escort = None
        for n in self.npcs:
            if n.id == escort_npc_id:
                npc_to_escort = n
                break
        if not npc_to_escort:
            return

        follower = Follower(
            npc_id=escort_npc_id,
            name=npc_to_escort.name or f"NPC_{escort_npc_id}",
            quest_id=quest.id,
            joined_in_room=1,
            destination_room=getattr(quest, 'destination_room', 1),
            personality=getattr(npc_to_escort, 'personality', ''),
            farewell_text="Thank you for escorting me. Farewell!",
            dialogue_hints=[
                "I think we need to keep moving...",
                "Be careful, I've heard rumors of danger ahead.",
                "I appreciate your help, adventurer.",
            ],
        )

        if self.player.add_follower(follower):
            self.npcs.remove(npc_to_escort)
            self.dialogue_box.set_item_message(f"{follower.name} is now following you!")
            self.item_message_active = True

            from src.models.items import EscortItem, ItemStats
            escort_item = EscortItem(
                category="escort",
                name=f"{npc_to_escort.name} (escort)",
                desc=f"Escorting {npc_to_escort.name} to safety.",
                item_stats=ItemStats(),
                npc_id=escort_npc_id,
                target_zone=tuple(getattr(quest, 'target_zone', [0, 0])),
            )
            self.player.add_to_inventory(escort_item)
        else:
            self.dialogue_box.set_item_message("You already have the maximum number of followers!")
            self.item_message_active = True

    def _fail_quest(self, quest):
        """Fail a quest and apply penalties."""
        quest.status = "failed"
        self.player.fail_quest(quest.id)
        penalty_msg = quest.apply_failure_penalty(self.player)
        msg = f"Quest failed: {quest.title}!"
        if penalty_msg:
            msg += f" ({penalty_msg})"
        self.dialogue_box.set_item_message(msg)
        self.item_message_active = True

        if quest.type == "escort":
            follower = self.player.get_follower_by_quest(quest.id)
            if follower:
                self.player.remove_follower(follower.npc_id)

    def _check_multi_step_progress(self, completed_quest_id: str):
        """Check if completing a sub-quest advances any multi-step quest."""
        for qid, quest in self.quests.items():
            if quest.type != "multi_step" or quest.status != "active":
                continue
            current_sub = quest.get_current_sub_quest_id()
            if current_sub == completed_quest_id:
                all_done = quest.advance_step()
                if all_done:
                    self._complete_quest(quest)
                else:
                    next_sub = quest.get_current_sub_quest_id()
                    if next_sub and next_sub in self.quests:
                        next_q = self.quests[next_sub]
                        if next_q.status == "not_started":
                            next_q.status = "active"
                            self.player.accept_quest(next_q.id)
                    self.dialogue_box.set_item_message(
                        f"Quest progress: {quest.title} — step {quest.current_step}/{len(quest.sub_quest_ids)}")
                    self.item_message_active = True

    def get_quest_log(self) -> dict:
        """Return quests organized by status for the quest log view."""
        active = []
        completed = []
        failed = []
        for qid, quest in self.quests.items():
            entry = {
                "id": qid,
                "title": quest.title,
                "description": quest.description,
                "type": quest.type,
                "is_story_quest": getattr(quest, 'is_story_quest', False),
            }
            if quest.type == "multi_step":
                entry["current_step"] = getattr(quest, 'current_step', 0)
                entry["total_steps"] = len(getattr(quest, 'sub_quest_ids', []))
            if quest.status == "active":
                active.append(entry)
            elif quest.status == "completed":
                completed.append(entry)
            elif quest.status == "failed":
                failed.append(entry)
        return {"active": active, "completed": completed, "failed": failed}

    def _open_shop(self, merchant_npc):
        """Open the shop interface for a MerchantNPC."""
        self.shop_active = True
        self.shop_npc = merchant_npc
        self.shop_view = ShopView(self.screen, self.font, merchant_npc, self.player)

    def _handle_shop_input(self, event):
        """Handle keyboard input while the shop is open."""
        result = self.shop_view.handle_input(event)
        if result is None:
            return
        if result == "close":
            self.shop_active = False
            self.shop_npc = None
            self.shop_view = None
            return
        if result["action"] == "buy":
            msg = self.shop_npc.buy_from(result["index"], self.player)
            self.item_message_active = True
            self.dialogue_box.set_item_message(msg)
        elif result["action"] == "sell":
            msg = self.shop_npc.sell_to(result["item_name"], self.player)
            self.item_message_active = True
            self.dialogue_box.set_item_message(msg)

    def handle_inventory_input(self, event):
        inventory = self.player.get_inventory()
        if not inventory:
            return

        inv_length = len(inventory)
        if event.key == pygame.K_UP:
            self.player.selected_item_index = (self.player.selected_item_index - 1) % inv_length
        elif event.key == pygame.K_DOWN:
            self.player.selected_item_index = (self.player.selected_item_index + 1) % inv_length
        elif event.key == pygame.K_RETURN:
            message = self.player.use_item()
            self.item_message_active = True
            self.dialogue_box.set_item_message(message)
        elif event.key == pygame.K_u:
            message = self.player.use_item()
            self.item_message_active = True
            self.dialogue_box.set_item_message(message)
        elif event.key == pygame.K_e:
            # Equip weapon
            item_name = inventory[self.player.selected_item_index][0]
            message = self.player.equip_weapon(item_name)
            self.item_message_active = True
            self.dialogue_box.set_item_message(message)
        elif event.key == pygame.K_d:
            # Show item detail
            self.item_detail_active = True

    def update(self, current_time):
        """Update game logic (NPC movement, etc.)"""
        if self.dialogue_box.generating:
            self.dialogue_box.check_generation()

        for npc in self.npcs:
            if hasattr(npc, 'update_position'):
                if isinstance(npc, RandomNPC):
                    npc.update_position(self.maze, current_time)
                elif isinstance(npc, AggressiveNPC):
                    npc.update_position(self.maze, (self.player.x, self.player.y), current_time)

        if not self.inventory_active and not self.dialogue_box.dialogue_active:
            self.current_npc = self.player.get_nearby_npc(self.npcs)
            self.player_at_item = self.player.is_item_at_player_position(self.maze)

    def draw(self, current_time):
        """Draw the current game state."""
        if self.shop_active and self.shop_view:
            self.screen.fill((0, 0, 0))
            self.shop_view.draw()
            # Draw item messages on top of shop
            if self.item_message_active:
                self.game_view.draw_dialogue_and_messages(
                    self.player, self.maze,
                    self.item_message_active, False)
            return

        self.game_view.draw_game(
            maze=self.maze,
            player=self.player,
            npcs=self.npcs,
            inventory_active=self.inventory_active,
            item_message_active=self.item_message_active,
            current_npc=self.current_npc,
            player_at_item=self.player_at_item,
            quests=self.quests,
            debug_reveal=self.debug_reveal,
            quest_log_active=self.quest_log_active,
            quest_log=self.get_quest_log() if self.quest_log_active else None,
            followers=self.player.followers,
            item_detail_active=self.item_detail_active,
        )
