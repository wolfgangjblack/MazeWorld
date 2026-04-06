import random
import pygame
from src.views.gameplay_view import GameView
from src.models.npc import RandomNPC, AggressiveNPC, MerchantNPC
from src.registry import registry
from src.utils.conversation_utils import has_dialogue_choices
from src.systems.quest_manager import QuestManager
from src.systems.follower_manager import FollowerManager


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

        # Managers
        self.quest_manager = QuestManager(self.quests, self.events)
        self.follower_manager = FollowerManager(self.player, self.npcs, self.quests)

        # Build a lookup from grid position to event id
        self.event_position_map: dict[tuple[int, int], str] = {}
        self._build_event_position_map()

        # Check for kill quests already cleared at startup
        self.quest_manager.check_kill_quests_already_cleared(self.player)

        # Inject story context into dialogue box
        story = registry.get_story()
        if story:
            self.dialogue_box.story_context = self._build_story_context(story)

        # UI / State variables
        self.inventory_active = False
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
        self.shop_mode = "buy"  # "buy" or "sell"
        self.shop_selected_index = 0

        # Combat target selection
        self.combat_target_index = 0

        # Player menu / save-load state
        self.player_menu_active = False
        self.pending_action = None  # Set to "save", "load", "quit" to signal main loop

        self.game_view = GameView(screen, font, dialogue_box)

    @staticmethod
    def _build_story_context(story) -> str:
        """Build a concise story summary for NPC dialogue flavoring."""
        parts = []
        if story.title:
            parts.append(f"The overarching story is '{story.title}'.")
        if story.synopsis:
            parts.append(story.synopsis)
        if story.faction:
            parts.append(
                f"A faction called '{story.faction.name}' is active: "
                f"{story.faction.description}")
            if story.faction.leader:
                parts.append(f"Their leader is {story.faction.leader}.")
        if story.final_boss_name:
            parts.append(
                f"Rumors speak of a powerful being called {story.final_boss_name}.")
        # Include the most recent beat for immediacy
        if story.beats:
            last_beat = story.beats[-1]
            if last_beat.summary:
                parts.append(f"Recent events: {last_beat.summary}")
        return " ".join(parts)

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

        # Check escort zone completion
        completed_escort = self.quest_manager.check_escort_zone(self.player)
        if completed_escort:
            farewell = self.follower_manager.remove_follower_for_quest(completed_escort.id)
            msg = "Your escort has arrived safely!"
            if farewell:
                msg += f" {farewell}"
            self.dialogue_box.set_item_message(msg)
            self.item_message_active = True

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
            if event.key == pygame.K_ESCAPE:
                self.inventory_active = False
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
            self.player.move(dx=dx, dy=dy, maze=self.maze)
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
            # Esc also opens menu in normal gameplay
            self.pending_action = "open_menu"
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
                    self.quest_manager.on_event_resolved(current_event.id, self.player)
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
            self.quest_manager.on_event_resolved(combat_event.id, self.player)

        self.dialogue_box.end_event()

    def _handle_npc_interaction(self, npc):
        """Start dialogue with an NPC, handling quest offers and completions."""
        # Check quest turn-in first
        turned_in = self.quest_manager.check_turn_in(npc, self.player)
        if turned_in:
            msg = f"Quest completed: {turned_in.title}!"
            if turned_in.reward and turned_in.reward.money:
                msg += f" +{turned_in.reward.money} gold!"
            # Handle escort follower removal on turn-in
            if turned_in.type == "escort":
                farewell = self.follower_manager.remove_follower_for_quest(turned_in.id)
                if farewell:
                    msg += f" {farewell}"
            self.dialogue_box.set_item_message(msg)
            self.item_message_active = True
            return

        self.dialogue_box.start_dialogue(npc)

        # Try to offer quest
        offered = self.quest_manager.try_offer_quest(npc, self.player)
        if offered and offered.type == "escort":
            escort_msg = self.follower_manager.start_escort(offered, npc)
            if escort_msg:
                self.dialogue_box.set_item_message(escort_msg)
                self.item_message_active = True

    def _talk_to_follower(self):
        """Talk to the first follower for hints/personality."""
        msg = self.follower_manager.talk_to_follower()
        self.dialogue_box.set_item_message(msg)
        self.item_message_active = True

    def get_quest_log(self) -> dict:
        """Return quests organized by status for the quest log view."""
        return self.quest_manager.get_quest_log()

    def get_follower_info(self) -> list[dict]:
        """Return follower info for the player menu."""
        return self.follower_manager.get_follower_info()

    def _open_shop(self, merchant_npc):
        """Open the shop interface for a MerchantNPC."""
        self.shop_active = True
        self.shop_npc = merchant_npc
        self.shop_mode = "buy"
        self.shop_selected_index = 0

    def _handle_shop_input(self, event):
        """Handle keyboard input while the shop is open."""
        if event.key == pygame.K_ESCAPE:
            self.shop_active = False
            self.shop_npc = None
            return

        if event.key == pygame.K_b:
            self.shop_mode = "buy"
            self.shop_selected_index = 0
            return
        if event.key == pygame.K_s:
            self.shop_mode = "sell"
            self.shop_selected_index = 0
            return

        if self.shop_mode == "buy":
            available = self.shop_npc.get_shop_items()
            max_idx = len(available) - 1
        else:
            max_idx = len(self.player.get_inventory()) - 1

        if max_idx < 0:
            return

        if event.key == pygame.K_UP:
            self.shop_selected_index = max(0, self.shop_selected_index - 1)
        elif event.key == pygame.K_DOWN:
            self.shop_selected_index = min(max_idx, self.shop_selected_index + 1)
        elif event.key == pygame.K_RETURN:
            if self.shop_mode == "buy":
                msg = self.shop_npc.buy_from(self.shop_selected_index, self.player)
            else:
                inventory = self.player.get_inventory()
                if self.shop_selected_index < len(inventory):
                    item_name = inventory[self.shop_selected_index][0]
                    msg = self.shop_npc.sell_to(item_name, self.player)
                else:
                    msg = "Nothing to sell."
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
            shop_active=self.shop_active,
            shop_npc=self.shop_npc,
            shop_mode=self.shop_mode,
            shop_selected_index=self.shop_selected_index,
            quest_log_active=self.quest_log_active,
            quest_log=self.get_quest_log() if self.quest_log_active else None,
            followers=self.player.followers,
        )
