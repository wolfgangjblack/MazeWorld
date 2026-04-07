import random
import pygame
from src.controllers.combat_controller import CombatController, CombatState
from src.views.combat_view import CombatView
from src.views.gameplay_view import GameView
from src.views.shop_view import ShopView
from src.models.npc import RandomNPC, AggressiveNPC, MerchantNPC
from src.models.time import DayNightCycle
from src.systems.fog_of_war import FogOfWar
from src.systems.day_night import (
    apply_rest, apply_combat_rest, player_has_torch,
    consume_torch_use, is_event_active_at_time, is_npc_available,
    get_night_overlay_alpha, spawn_night_encounter,
)
from src.registry import registry
from src.utils.conversation_utils import has_dialogue_choices
from src.systems.survival import SurvivalSystem
from src.systems.quest_manager import QuestManager
from src.systems.follower_manager import FollowerManager

PERIOD_TRANSITION_MESSAGES = {
    "dawn": "The sun begins to rise. Dawn breaks.",
    "day": "Daylight fills the area.",
    "dusk": "The light fades. Dusk approaches.",
    "night": "Night falls. Beware of creatures in the dark.",
}


class GameController:
    def __init__(self, screen, font, maze, player, npcs, dialogue_box,
                 events=None, quests=None, fog=None, day_night=None,
                 current_room=0, total_rooms=1):
        self.screen = screen
        self.font = font
        self.maze = maze
        self.player = player
        self.npcs = npcs
        self.dialogue_box = dialogue_box
        self.events = events or {}
        self.quests = quests or {}

        # Fog of War
        self.fog = fog or FogOfWar()
        # Day/Night Cycle
        self.day_night = day_night or DayNightCycle()
        # Enable real-time day cycle from config
        from config import DAY_NIGHT_REAL_TIME, DAY_NIGHT_REAL_TIME_SECONDS
        if DAY_NIGHT_REAL_TIME and not self.day_night.real_time:
            self.day_night.real_time_seconds_per_cycle = DAY_NIGHT_REAL_TIME_SECONDS
            self.day_night.enable_real_time()

        # Managers
        self.quest_manager = QuestManager(self.quests, self.events)
        self.quest_manager.door_reveal_callback = self.reveal_door_from_quest
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

        # Initial fog reveal at player start position
        self._update_fog()

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

        # Rest menu state
        self.rest_menu_active = False

        # Shop state
        self.shop_active = False
        self.shop_npc = None
        self.shop_view = None

        # Combat target selection
        self.combat_target_index = 0

        # Full combat system (CombatController + CombatView)
        self.combat_controller: CombatController | None = None
        self.combat_view: CombatView | None = None
        self.combat_event = None  # The CombatEvent that triggered combat
        self.combat_selected_action = 0
        self.combat_selected_target = 0
        self.combat_selecting_target = False
        self.combat_selecting_spell = False
        self.combat_selected_spell = 0
        self.combat_selecting_item = False
        self.combat_selected_item = 0
        self.combat_game_over_selection = 0

        # Player menu / save-load state
        self.player_menu_active = False
        self.pending_action = None  # Signals main loop: "save", "load", "quit", "open_pause", "open_full_menu", "open_story", "game_over", "victory", "room_transition"

        # Room progression state
        self.current_room = current_room
        self.total_rooms = total_rooms
        self.gate_cleared = False
        self._count_total_encounters()

        # Stats tracking for victory screen
        self.stats = {
            "monsters_killed": 0,
            "items_used": 0,
            "rooms_cleared": 0,
        }

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

    def _count_total_encounters(self):
        """Count total and resolved encounters for door reveal tracking."""
        self.total_encounters = sum(
            1 for e in self.events.values()
            if not getattr(e, 'is_gate', False)
            and not getattr(e, 'is_climax_boss', False)
        )
        self.resolved_encounters = sum(
            1 for e in self.events.values()
            if e.resolved
            and not getattr(e, 'is_gate', False)
            and not getattr(e, 'is_climax_boss', False)
        )

    @property
    def encounter_clear_fraction(self) -> float:
        if self.total_encounters == 0:
            return 1.0
        return self.resolved_encounters / self.total_encounters

    def _check_door_reveal(self):
        """Reveal the exit door if encounter clear threshold met."""
        from config import DOOR_REVEAL_THRESHOLD
        if (self.maze.door_position
                and not self.maze.door_revealed
                and self.total_rooms > 1
                and self.current_room < self.total_rooms - 1
                and self.encounter_clear_fraction >= DOOR_REVEAL_THRESHOLD):
            self.maze.reveal_door()
            self.dialogue_box.set_item_message(
                "An exit door has appeared! A gate guardian blocks the way.")
            self.item_message_active = True

    def reveal_door_from_quest(self):
        """Called when a quest reward reveals the door."""
        if self.maze.door_position and not self.maze.door_revealed:
            self.maze.reveal_door()
            self.dialogue_box.set_item_message(
                "A quest has revealed the exit door!")
            self.item_message_active = True

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
        """True if any modal UI is open (dialogue, event, shop, or combat)."""
        return (
            self._in_full_combat
            or self.dialogue_box.event_active
            or self.dialogue_box.dialogue_active
            or self.shop_active
        )

    # --- Fog of War & Day/Night helpers ---

    def _get_visibility_radius(self) -> int:
        """Calculate current visibility radius (fog + night + torch)."""
        return self.fog.get_visibility_radius(
            self.player,
            is_night=self.day_night.is_night,
            has_torch=player_has_torch(self.player),
        )

    def _update_fog(self):
        """Reveal tiles around the player's current position."""
        radius = self._get_visibility_radius()
        self.fog.update(self.player.x, self.player.y, self.maze, radius)

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
        # Advance time on movement
        self.day_night.advance(1)
        # Update fog of war
        self._update_fog()
        # Consume torch use only on movement (not rest or startup)
        if self.day_night.is_night and player_has_torch(self.player):
            consume_torch_use(self.player)

        if self.player.is_on_event_tile(self.maze):
            event = self._get_event_at_player()
            if event and not event.resolved:
                # Time-gated events: only trigger at correct time
                if is_event_active_at_time(event, self.day_night.current_period):
                    if event.type == "combat":
                        self._start_full_combat(event)
                    else:
                        self.dialogue_box.start_event(event)
                # Wrong time: silently pass over (event stays)
            else:
                self.maze.grid[self.player.y][self.player.x] = 0
        elif self._is_on_door_tile():
            self._handle_door_interaction()
        else:
            self.player_at_item = self.player.is_item_at_player_position(self.maze)
            self.current_npc = self.player.get_nearby_npc(self.npcs)

        # Random night encounter check — only when walking on open tiles at night
        if (self.day_night.is_night
                and not self._in_full_combat
                and not self.dialogue_box.event_active
                and not self.dialogue_box.dialogue_active):
            night_event = spawn_night_encounter(
                self.maze, self.player, self.day_night, self.current_room + 1)
            if night_event:
                self.total_encounters += 1
                self._start_full_combat(night_event)

        # Check escort zone completion
        completed_escort = self.quest_manager.check_escort_zone(self.player)
        if completed_escort:
            farewell = self.follower_manager.remove_follower_for_quest(completed_escort.id)
            msg = "Your escort has arrived safely!"
            if farewell:
                msg += f" {farewell}"
            self.dialogue_box.set_item_message(msg)
            self.item_message_active = True

    def _start_full_combat(self, combat_event):
        """Initialize CombatController + CombatView for a multi-turn combat encounter."""
        # Resolve player weapon for combat
        from src.models.weapon import STARTER_WEAPONS
        if self.player.weapon is None and self.player.player_class:
            self.player.weapon = STARTER_WEAPONS.get(self.player.player_class.archetype)

        # Ensure monsters exist — generate fallback if empty
        if not combat_event.monsters:
            from src.models.monster import generate_encounter_monsters
            env = getattr(self.maze, 'environment', 'dungeon')
            room_level = getattr(combat_event, 'room_level', 1)
            combat_event.monsters = generate_encounter_monsters(env, room_level)

        self.combat_event = combat_event
        self.combat_controller = CombatController(self.player, list(combat_event.monsters))
        self.combat_view = CombatView(self.screen, self.font)
        self.combat_selected_action = 0
        self.combat_selected_target = 0
        self.combat_selecting_target = False
        self.combat_selecting_spell = False
        self.combat_selected_spell = 0
        self.combat_selecting_item = False
        self.combat_selected_item = 0
        self.combat_game_over_selection = 0

    @property
    def _in_full_combat(self) -> bool:
        return self.combat_controller is not None

    def _is_on_door_tile(self) -> bool:
        """Check if the player is standing on the revealed door tile."""
        return (self.maze.door_position is not None
                and self.maze.door_revealed
                and (self.player.x, self.player.y) == self.maze.door_position)

    def _handle_door_interaction(self):
        """Handle player stepping on the exit door."""
        gate_id = self.maze.gate_encounter_id
        if gate_id and not self.gate_cleared:
            gate_event = self.events.get(gate_id)
            if gate_event and not gate_event.resolved:
                # Trigger gate encounter
                self.dialogue_box.start_event(gate_event)
                return
            else:
                self.gate_cleared = True

        # Gate cleared or no gate — check for undone quests and transition
        self._signal_room_transition()

    def _signal_room_transition(self):
        """Signal the main loop to transition to the next room."""
        if self.current_room >= self.total_rooms - 1:
            self.pending_action = "victory"
            return
        # Check for incomplete story quests
        undone = [q for q in self.quests.values()
                  if getattr(q, 'is_story_quest', False)
                  and q.status in ("not_started", "active")]
        if undone:
            titles = ", ".join(q.title for q in undone[:3])
            self.dialogue_box.set_item_message(
                f"Things left undone: {titles}. "
                "Press Enter at the door again to continue anyway.")
            self.item_message_active = True
            # Mark that we've warned — next door step will proceed
            if not hasattr(self, '_undone_warned'):
                self._undone_warned = True
                return
        self.stats["rooms_cleared"] += 1
        self.pending_action = "room_transition"

    def handle_keydown(self, event):
        # 0. Full combat system active
        if self._in_full_combat:
            self._handle_full_combat_input(event)
            return

        # 0.5. If an event is active (legacy/puzzle/event)
        if self.dialogue_box.event_active:
            self._handle_event_input(event)
            return

        # 0.25. If rest menu is active
        if self.rest_menu_active:
            self._handle_rest_input(event)
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

        if event.key == pygame.K_r:
            self.rest_menu_active = True
            self.dialogue_box.set_item_message(
                "Rest: 1=3hr  2=6hr  3=12hr  Esc=Cancel")
            self.item_message_active = True
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

        # B key opens story recap
        if event.key == pygame.K_b:
            self.pending_action = "open_story"
            return

    # ------------------------------------------------------------------
    # Full Combat System (CombatController + CombatView)
    # ------------------------------------------------------------------

    def _handle_full_combat_input(self, event):
        """Handle input while the full CombatController combat is active."""
        cc = self.combat_controller
        if cc is None:
            return

        # Combat is over — handle end-screen input
        if cc.state != CombatState.ONGOING:
            self._handle_combat_end_input(event)
            return

        # Monster turn — auto-execute on any key
        if not cc.is_player_turn():
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                cc.execute_monster_turn()
                # Continue executing monster turns until it's the player's turn or combat ends
                while cc.state == CombatState.ONGOING and not cc.is_player_turn():
                    cc.execute_monster_turn()
                self.combat_selecting_target = False
                self.combat_selecting_spell = False
                self.combat_selecting_item = False
                self.combat_selected_action = 0
            return

        # Player turn — spell selection sub-menu
        if self.combat_selecting_spell:
            spells = cc.player.spells
            if event.key == pygame.K_UP:
                self.combat_selected_spell = (self.combat_selected_spell - 1) % max(len(spells), 1)
            elif event.key == pygame.K_DOWN:
                self.combat_selected_spell = (self.combat_selected_spell + 1) % max(len(spells), 1)
            elif event.key == pygame.K_RETURN:
                if spells:
                    spell = spells[self.combat_selected_spell]
                    if spell.targets == "self" or spell.spell_type in ("heal", "buff_stat", "buff_sustain"):
                        cc.player_cast_spell(self.combat_selected_spell, 0)
                        while cc.state == CombatState.ONGOING and not cc.is_player_turn():
                            cc.execute_monster_turn()
                        self.combat_selecting_spell = False
                        self.combat_selected_action = 0
                    else:
                        self.combat_selecting_spell = False
                        self.combat_selecting_target = True
                        self.combat_selected_target = 0
            elif event.key == pygame.K_ESCAPE:
                self.combat_selecting_spell = False
            return

        # Player turn — item selection sub-menu
        if self.combat_selecting_item:
            consumables = self._get_combat_consumables()
            if event.key == pygame.K_UP:
                self.combat_selected_item = (self.combat_selected_item - 1) % max(len(consumables), 1)
            elif event.key == pygame.K_DOWN:
                self.combat_selected_item = (self.combat_selected_item + 1) % max(len(consumables), 1)
            elif event.key == pygame.K_RETURN:
                if consumables:
                    item_name = consumables[self.combat_selected_item]
                    cc.player_use_item(item_name)
                    while cc.state == CombatState.ONGOING and not cc.is_player_turn():
                        cc.execute_monster_turn()
                    self.combat_selecting_item = False
                    self.combat_selected_action = 0
            elif event.key == pygame.K_ESCAPE:
                self.combat_selecting_item = False
            return

        # Player turn — target selection mode
        if self.combat_selecting_target:
            alive = [m for m in cc.monsters if m.is_alive]
            if event.key == pygame.K_UP:
                self.combat_selected_target = (self.combat_selected_target - 1) % max(len(alive), 1)
            elif event.key == pygame.K_DOWN:
                self.combat_selected_target = (self.combat_selected_target + 1) % max(len(alive), 1)
            elif event.key == pygame.K_RETURN:
                self._execute_player_combat_action(self.combat_selected_action,
                                                   self.combat_selected_target)
                self.combat_selecting_target = False
                self.combat_selected_action = 0
            elif event.key == pygame.K_ESCAPE:
                self.combat_selecting_target = False
            return

        # Player turn — action menu
        actions = self._get_combat_actions()
        if event.key == pygame.K_UP:
            self.combat_selected_action = (self.combat_selected_action - 1) % len(actions)
        elif event.key == pygame.K_DOWN:
            self.combat_selected_action = (self.combat_selected_action + 1) % len(actions)
        elif event.key == pygame.K_RETURN:
            action_name = actions[self.combat_selected_action]
            if action_name == "Cast Spell":
                if cc.player.spells:
                    self.combat_selecting_spell = True
                    self.combat_selected_spell = 0
            elif action_name == "Use Item":
                consumables = self._get_combat_consumables()
                if consumables:
                    self.combat_selecting_item = True
                    self.combat_selected_item = 0
            elif action_name == "Attack":
                self.combat_selecting_target = True
                self.combat_selected_target = 0
            else:
                self._execute_player_combat_action(self.combat_selected_action, 0)

    def _get_combat_actions(self) -> list[str]:
        """Return the list of available combat actions for the current player."""
        actions = list(CombatView.ACTIONS)  # ["Attack", "Multi-Attack", ...]
        cc = self.combat_controller
        if not cc or not cc.player.player_class or cc.player.player_class.archetype != "jester":
            actions = [a for a in actions if a != "Gamble"]
        return actions

    def _get_combat_consumables(self) -> list[str]:
        """Return names of consumable items usable in combat."""
        from src.models.items import Food, Drink
        cc = self.combat_controller
        if cc is None:
            return []
        return [
            name for name, item in cc.player.inventory.items()
            if isinstance(item, (Food, Drink))
        ]

    def _execute_player_combat_action(self, action_index: int, target_index: int):
        """Execute the selected player action through CombatController."""
        cc = self.combat_controller
        if cc is None:
            return

        actions = self._get_combat_actions()
        action_name = actions[action_index] if action_index < len(actions) else "Attack"

        if action_name == "Attack":
            cc.player_attack(target_index)
        elif action_name == "Multi-Attack":
            cc.player_multi_attack()
        elif action_name == "Cast Spell":
            if cc.player.spells:
                cc.player_cast_spell(self.combat_selected_spell, target_index)
        elif action_name == "Use Item":
            consumables = self._get_combat_consumables()
            if consumables:
                cc.player_use_item(consumables[self.combat_selected_item])
        elif action_name == "Flee":
            cc.player_flee()
        elif action_name == "Gamble":
            cc.player_gamble()
        elif action_name == "Swap Weapon":
            cc.player_swap_weapon()

        # After player action, auto-execute monster turns
        while cc.state == CombatState.ONGOING and not cc.is_player_turn():
            cc.execute_monster_turn()

        self.combat_selected_action = 0

    def _handle_combat_end_input(self, event):
        """Handle input on the combat end screen (victory/defeat/fled)."""
        cc = self.combat_controller

        if cc.state == CombatState.DEFEAT:
            if event.key == pygame.K_UP:
                self.combat_game_over_selection = (self.combat_game_over_selection - 1) % 2
            elif event.key == pygame.K_DOWN:
                self.combat_game_over_selection = (self.combat_game_over_selection + 1) % 2
            elif event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                if self.combat_game_over_selection == 0:
                    self.pending_action = "load"
                else:
                    self.pending_action = "quit"
                self._end_full_combat()
            return

        if event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
            self._finalize_full_combat()

    def _finalize_full_combat(self):
        """Handle loot, quest completion, and cleanup after combat victory/fled."""
        cc = self.combat_controller
        combat_event = self.combat_event

        if cc.state == CombatState.VICTORY:
            combat_event.resolved = True
            # Collect loot from CombatController
            loot_ids = cc.collect_loot()
            for item_id in loot_ids:
                item = registry.get_item(item_id)
                if item:
                    self.player.add_to_inventory(item.clone())
            # Money drop from event
            if hasattr(combat_event, 'money_drop') and combat_event.money_drop[1] > 0:
                money = random.randint(combat_event.money_drop[0], combat_event.money_drop[1])
                if money > 0:
                    self.player.add_money(money)

            # Clear tile
            self.maze.grid[self.player.y][self.player.x] = 0

            # Stats tracking
            self.stats["monsters_killed"] += sum(
                1 for m in combat_event.monsters if not m.is_alive)

            # Quest and encounter tracking
            is_gate = getattr(combat_event, 'is_gate', False)
            if not is_gate:
                self.resolved_encounters += 1
                self._check_door_reveal()
            else:
                self.gate_cleared = True
            self.quest_manager.on_event_resolved(combat_event.id, self.player)

            # Check quest completion
            for qid, quest in self.quests.items():
                if (quest.type == "combat"
                        and getattr(quest, 'target_event_id', '') == combat_event.id
                        and quest.status == "active"):
                    quest.status = "completed"
                    self.player.complete_quest(qid)

        self._end_full_combat()

    def _end_full_combat(self):
        """Clean up combat state."""
        self.combat_controller = None
        self.combat_view = None
        self.combat_event = None

    def _handle_event_input(self, event):
        """Handle keyboard input during an active event."""
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
                    self.resolved_encounters += 1
                    self._check_door_reveal()
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
                # Advance time on combat action
                self.day_night.advance(1)

                result = combat_event.player_attack(self.player, self.combat_target_index)
                self.dialogue_box.combat_log = list(combat_event.combat_log)

                outcome = combat_event.is_combat_over()
                if outcome == "victory":
                    self._handle_combat_victory(combat_event)
                    return
                combat_event.advance_turn()
                self._advance_combat_to_next_turn(combat_event)
                return

            if event.key == pygame.K_r:
                # Rest in combat: skip turn for small HP recovery
                self._apply_player_poison()
                self.day_night.advance(1)
                msg = apply_combat_rest(self.player)
                self.dialogue_box.add_combat_log(msg)
                combat_event.combat_log.append(msg)
                combat_event.advance_turn()
                self._advance_combat_to_next_turn(combat_event)
                return

            if event.key == pygame.K_f:
                result = combat_event.try_flee(self.player)
                self.dialogue_box.combat_log = list(combat_event.combat_log)

                if result["success"]:
                    self.player.combat_record["combats_fled"] += 1
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

        # Track stats
        if hasattr(combat_event, 'monsters'):
            killed = sum(1 for m in combat_event.monsters if not m.is_alive)
            self.stats["monsters_killed"] += killed
            self.player.combat_record["monsters_killed"] += killed
        self.player.combat_record["combats_won"] += 1
        if getattr(combat_event, 'is_climax_boss', False):
            self.resolved_encounters += 1
            self.gate_cleared = True
            self.pending_action = "victory"
        elif not getattr(combat_event, 'is_gate', False):
            self.resolved_encounters += 1
            self._check_door_reveal()
        else:
            self.gate_cleared = True

        # Collect loot
        loot_ids = combat_event.collect_loot()
        for item_id in loot_ids:
            item = registry.get_item(item_id)
            if item:
                self.player.add_to_inventory(item.clone())
                self.dialogue_box.add_combat_log(f"Loot: {item.name}")

    def _finalize_combat(self, combat_event):
        """Clean up after combat ends."""
        is_gate = getattr(combat_event, 'is_gate', False)

        if combat_event.resolved:
            self.maze.grid[self.player.y][self.player.x] = 0
            self.quest_manager.on_event_resolved(combat_event.id, self.player)
        elif is_gate and getattr(combat_event, 'player_fled', False):
            # Gate failure: player flees — pass through with heavy survival penalty
            penalty_hp = 20 + self.current_room * 10
            penalty_hunger = 25
            penalty_thirst = 25
            self.player.health = max(1, self.player.health - penalty_hp)
            self.player.hunger = max(0, self.player.hunger - penalty_hunger)
            self.player.thirst = max(0, self.player.thirst - penalty_thirst)
            self.gate_cleared = True
            self.dialogue_box.set_item_message(
                f"You flee the gate guardian! Penalty: -{penalty_hp} HP, "
                f"-{penalty_hunger} hunger, -{penalty_thirst} thirst. "
                "The door is now open.")
            self.item_message_active = True

        self.dialogue_box.end_event()

        # Check for player death after combat
        if self.player.health <= 0:
            self.pending_action = "game_over"

    def _handle_npc_interaction(self, npc):
        """Start dialogue with an NPC, handling quest offers and completions."""
        # Check NPC availability by time of day
        if not is_npc_available(npc, self.day_night.current_period):
            self.dialogue_box.set_item_message(
                f"{npc.name or 'NPC'} is not available right now.")
            self.item_message_active = True
            return

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

    def _handle_rest_input(self, event):
        """Handle input while rest menu is active."""
        hour_map = {pygame.K_1: 3, pygame.K_2: 6, pygame.K_3: 12}
        if event.key in hour_map:
            hours = hour_map[event.key]
            msg = apply_rest(self.player, hours, self.day_night)
            self._update_fog()
            self.dialogue_box.set_item_message(msg)
            self.rest_menu_active = False
            return
        if event.key == pygame.K_ESCAPE:
            self.rest_menu_active = False
            self.item_message_active = False
            self.dialogue_box.clear_item_message()
            return

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
        """Update game logic (NPC movement, real-time day cycle, etc.)"""
        # Advance real-time day/night cycle
        self.day_night.update_realtime(current_time)
        prev_period = self.day_night.current_period
        self.day_night.update()

        # Notify player on period transitions (real-time driven)
        if self.day_night.real_time and self.day_night.current_period != prev_period:
            new_period = self.day_night.current_period
            self._update_fog()
            if not self.has_active_overlay and not self.item_message_active:
                msg = PERIOD_TRANSITION_MESSAGES.get(new_period.value, "")
                if msg:
                    self.dialogue_box.set_item_message(msg)
                    self.item_message_active = True

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
        if self._in_full_combat and self.combat_view and self.combat_controller:
            self.combat_view.draw(
                self.combat_controller,
                selected_action=self.combat_selected_action,
                selected_target=self.combat_selected_target,
                selecting_target=self.combat_selecting_target,
                selecting_spell=self.combat_selecting_spell,
                selected_spell=self.combat_selected_spell,
                selecting_item=self.combat_selecting_item,
                selected_item=self.combat_selected_item,
                game_over_selection=self.combat_game_over_selection,
            )
            return

        if self.shop_active and self.shop_view:
            self.screen.fill((0, 0, 0))
            self.shop_view.draw()
            # Draw item messages on top of shop
            if self.item_message_active:
                self.game_view.draw_dialogue_and_messages(
                    self.player, self.maze,
                    self.item_message_active, False)
            return

        period = self.day_night.current_period
        night_alpha = get_night_overlay_alpha(period, self.day_night.period_progress)

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
            fog=self.fog,
            visibility_radius=self._get_visibility_radius(),
            night_alpha=night_alpha,
            time_period=period,
            day_number=self.day_night.day_number,
            item_detail_active=self.item_detail_active,
        )
