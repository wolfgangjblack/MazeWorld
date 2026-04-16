import pygame

from src.controllers.combat_input_handler import CombatInputHandler
from src.controllers.event_input_handler import EventInputHandler
from src.models.npc import AggressiveNPC, MerchantNPC, RandomNPC
from src.models.time import DayNightCycle
from src.registry import registry
from src.systems.day_night import (
    apply_rest,
    consume_torch_use,
    get_night_overlay_alpha,
    is_event_active_at_time,
    is_npc_available,
    player_has_torch,
)
from src.systems.fog_of_war import FogOfWar
from src.systems.follower_manager import FollowerManager
from src.systems.quest_manager import QuestManager
from src.systems.survival import SurvivalSystem
from src.utils.conversation_utils import has_dialogue_choices
from src.views.gameplay_view import GameView
from src.views.shop_view import ShopView

PERIOD_TRANSITION_MESSAGES = {
    "dawn": "The sun begins to rise. Dawn breaks.",
    "day": "Daylight fills the area.",
    "dusk": "The light fades. Dusk approaches.",
    "night": "Night falls. Beware of creatures in the dark.",
}


class GameController:
    def __init__(
        self,
        screen,
        font,
        maze,
        player,
        npcs,
        dialogue_box,
        events=None,
        quests=None,
        fog=None,
        day_night=None,
        current_room=0,
        total_rooms=1,
        sfx=None,
    ):
        self.screen = screen
        self.font = font
        self.maze = maze
        self.player = player
        self.npcs = npcs
        self.dialogue_box = dialogue_box
        self.events = events or {}
        self.quests = quests or {}
        self.sfx = sfx
        self.current_room = current_room
        self.total_rooms = total_rooms

        # Fog of War
        self.fog = fog or FogOfWar()
        # Day/Night Cycle
        self.day_night = day_night or DayNightCycle()
        from config import DAY_NIGHT_REAL_TIME, DAY_NIGHT_REAL_TIME_SECONDS

        if DAY_NIGHT_REAL_TIME and not self.day_night.real_time:
            self.day_night.real_time_seconds_per_cycle = DAY_NIGHT_REAL_TIME_SECONDS
            self.day_night.enable_real_time()

        # Managers
        self.quest_manager = QuestManager(self.quests, self.events, self.npcs)
        self.quest_manager.door_reveal_callback = self.reveal_door_from_quest
        self.follower_manager = FollowerManager(self.player, self.npcs, self.quests)

        # Build a lookup from grid position to event id
        self.event_position_map: dict[tuple[int, int], int] = {}
        self._build_event_position_map()

        # Build event type/flag maps for rendering
        self._event_type_map: dict[tuple[int, int], str] = {}
        self._event_flag_map: dict[tuple[int, int], str] = {}
        self.rebuild_event_maps()

        self.quest_manager.check_kill_quests_already_cleared(self.player)

        story = registry.get_story()
        if story:
            self.dialogue_box.story_context = self._build_story_context(story)

        self._update_fog()

        self.survival = SurvivalSystem()

        # Input handlers (extracted subsystems)
        self.combat_handler = CombatInputHandler(self)
        self.event_handler = EventInputHandler(self)

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
        self.dialogue_choice_index = 0

        self.rest_menu_active = False

        self.shop_active = False
        self.shop_npc = None
        self.shop_view = None

        self.player_menu_active = False
        self.pending_action = None

        self.gate_cleared = False
        self._npc_combat_map: dict[int, object] = {}
        self._pending_npc_combat = None
        self._count_total_encounters()

        self.stats = {
            "monsters_killed": 0,
            "items_used": 0,
            "rooms_cleared": 0,
        }

        self.dialogue_box.player = self.player
        self.game_view = GameView(screen, font, dialogue_box)

    @staticmethod
    def _build_story_context(story) -> str:
        parts = []
        if story.title:
            parts.append(f"The overarching story is '{story.title}'.")
        if story.synopsis:
            parts.append(story.synopsis)
        if story.faction:
            parts.append(f"A faction called '{story.faction.name}' is active: {story.faction.description}")
            if story.faction.leader:
                parts.append(f"Their leader is {story.faction.leader}.")
        if story.final_boss_name:
            parts.append(f"Rumors speak of a powerful being called {story.final_boss_name}.")
        if story.beats:
            last_beat = story.beats[-1]
            if last_beat.summary:
                parts.append(f"Recent events: {last_beat.summary}")
        return " ".join(parts)

    def _count_total_encounters(self):
        self.total_encounters = sum(
            1
            for e in self.events.values()
            if not getattr(e, "is_gate", False) and not getattr(e, "is_climax_boss", False)
        )
        self.resolved_encounters = sum(
            1
            for e in self.events.values()
            if e.resolved and not getattr(e, "is_gate", False) and not getattr(e, "is_climax_boss", False)
        )

    @property
    def encounter_clear_fraction(self) -> float:
        if self.total_encounters == 0:
            return 1.0
        return self.resolved_encounters / self.total_encounters

    def _check_door_reveal(self):
        from config import DOOR_REVEAL_THRESHOLD

        if (
            self.maze.door_position
            and not self.maze.door_revealed
            and self.total_rooms > 1
            and self.encounter_clear_fraction >= DOOR_REVEAL_THRESHOLD
        ):
            self.maze.reveal_door()
            self.dialogue_box.set_item_message("A powerful presence stirs near the exit...")
            self.item_message_active = True
            if self.sfx:
                self.sfx.play("door_reveal")

    def reveal_door_from_quest(self):
        if self.maze.door_position and not self.maze.door_revealed:
            self.maze.reveal_door()
            self.dialogue_box.set_item_message("A powerful presence stirs near the exit...")
            self.item_message_active = True
            if self.sfx:
                self.sfx.play("door_reveal")

    def _build_event_position_map(self):
        if not self.events:
            return
        import logging
        import os

        from src.utils.dataloader_utils import load_json_data

        _log = logging.getLogger(__name__)

        from config import DATA_DIR

        room_maze = os.path.join(DATA_DIR, "rooms", f"room_{self.current_room}", "maze.json")
        maze_path = room_maze

        try:
            if os.path.exists(maze_path):
                maze_data = load_json_data(maze_path)
                for ep in maze_data.get("event_positions", []):
                    if "x" in ep and "y" in ep and "event_id" in ep:
                        self.event_position_map[(ep["x"], ep["y"])] = ep["event_id"]
        except Exception as exc:
            _log.warning("Failed to load event positions from %s: %s", maze_path, exc)

        if self.event_position_map:
            return

        for eid, event in self.events.items():
            ex = getattr(event, "x", None)
            ey = getattr(event, "y", None)
            if ex is not None and ey is not None:
                self.event_position_map[(ex, ey)] = eid

        if not self.event_position_map:
            _log.warning("Could not build event position map for room %d.", self.current_room)

    def rebuild_event_maps(self):
        self._event_type_map = {}
        self._event_flag_map = {}
        for pos, eid in self.event_position_map.items():
            evt = self.events.get(eid)
            if evt:
                self._event_type_map[pos] = getattr(evt, "type", "")
                if getattr(evt, "is_climax_boss", False):
                    self._event_flag_map[pos] = "climax_boss"
                elif getattr(evt, "is_gate", False):
                    self._event_flag_map[pos] = "gate"

    @property
    def has_active_overlay(self) -> bool:
        return (
            self.combat_handler.active
            or self.dialogue_box.event_active
            or self.dialogue_box.dialogue_active
            or self.shop_active
        )

    # --- Fog of War & Day/Night helpers ---

    def _get_visibility_radius(self) -> int:
        period = self.day_night.current_period
        return self.fog.get_visibility_radius(
            self.player,
            is_night=self.day_night.is_night,
            has_torch=player_has_torch(self.player),
            time_period=period.value if hasattr(period, "value") else str(period),
        )

    def _update_fog(self):
        radius = self._get_visibility_radius()
        self.fog.update(self.player.x, self.player.y, self.maze, radius)

    def run(self) -> str | None:
        clock = pygame.time.Clock()

        while self.running:
            current_time = pygame.time.get_ticks()
            self.handle_events()
            self.update(current_time)
            self.draw(current_time)
            pygame.display.flip()
            clock.tick(60)

            if self.pending_action:
                action = self.pending_action
                self.pending_action = None
                return action

        return None

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN:
                self.handle_keydown(event)
            elif event.type == pygame.MOUSEWHEEL:
                self._handle_mousewheel(event)

    def _handle_mousewheel(self, event):
        if self.dialogue_box.event_active:
            self.game_view.encounter_view.scroll_content(-event.y)
        elif self.combat_handler.active:
            self.combat_handler.handle_mousewheel(event)

    def _get_event_at_player(self):
        pos = (self.player.x, self.player.y)
        event_id = self.event_position_map.get(pos)
        if event_id:
            return self.events.get(event_id)
        return None

    def after_move_check(self):
        self.day_night.advance(1)
        self._update_fog()
        if self.day_night.is_night and player_has_torch(self.player):
            consume_torch_use(self.player)

        if self.player.is_on_event_tile(self.maze):
            event = self._get_event_at_player()
            if event and not event.resolved:
                if is_event_active_at_time(event, self.day_night.current_period):
                    if event.type == "combat":
                        self.combat_handler.start(event)
                    else:
                        self.day_night.pause()
                        self.game_view.encounter_view.reset_scroll()
                        self.dialogue_box.start_event(event)
                else:
                    time_gate = getattr(event, "time_gate", "always")
                    if time_gate == "day":
                        self.dialogue_box.set_item_message("This area stirs only during daylight...")
                        self.item_message_active = True
                    elif time_gate == "night":
                        self.dialogue_box.set_item_message("Something lurks here... but only at night.")
                        self.item_message_active = True
            else:
                self.maze.grid[self.player.y][self.player.x] = 0
        elif self._is_on_door_tile():
            self._handle_door_interaction()
        else:
            self.player_at_item = self.player.is_item_at_player_position(self.maze)
            self.current_npc = self.player.get_nearby_npc(self.npcs)

        completed_escort = self.quest_manager.check_escort_zone(self.player)
        if completed_escort:
            farewell = self.follower_manager.remove_follower_for_quest(completed_escort.id)
            msg = "Your escort has arrived safely!"
            if farewell:
                msg += f" {farewell}"
            self.dialogue_box.set_item_message(msg)
            self.item_message_active = True

    def _is_on_door_tile(self) -> bool:
        if self.maze.door_position is None or not self.maze.door_revealed:
            return False
        px, py = self.player.x, self.player.y
        if (px, py) != self.maze.door_position:
            return False
        return self.maze.grid[py][px] == self.maze.door_tile_id

    def _handle_door_interaction(self):
        self._signal_room_transition()

    def _signal_room_transition(self):
        if self.sfx:
            self.sfx.play("door_open")
        if self.current_room >= self.total_rooms - 1:
            self.pending_action = "victory"
            return
        undone = [
            q
            for q in self.quests.values()
            if getattr(q, "is_story_quest", False) and q.status in ("not_started", "active")
        ]
        if undone:
            titles = ", ".join(q.title for q in undone[:3])
            self.dialogue_box.set_item_message(
                f"Things left undone: {titles}. Press Enter at the door again to continue anyway."
            )
            self.item_message_active = True
            if not hasattr(self, "_undone_warned"):
                self._undone_warned = True
                return
        self.stats["rooms_cleared"] += 1
        self.pending_action = "room_transition"

    # ------------------------------------------------------------------
    # Input dispatch
    # ------------------------------------------------------------------

    def handle_keydown(self, event):
        if self.combat_handler.active:
            self.combat_handler.handle_input(event)
            return

        if self.dialogue_box.event_active:
            self.event_handler.handle_input(event)
            return

        if self.rest_menu_active:
            self._handle_rest_input(event)
            return

        if self.shop_active:
            self._handle_shop_input(event)
            return

        if self.item_message_active:
            if event.key == pygame.K_RETURN:
                self.item_message_active = False
                self.dialogue_box.clear_item_message()
                if self._pending_npc_combat:
                    npc = self._pending_npc_combat
                    self._pending_npc_combat = None
                    self._start_npc_combat(npc)
                return
            if event.key == pygame.K_ESCAPE:
                return
            return

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

        if self.dialogue_box.dialogue_active:
            if event.key == pygame.K_ESCAPE:
                self.dialogue_box.end_dialogue()
                self.current_npc = None
                self.dialogue_choice_index = 0
                return
            if self.dialogue_box.generating:
                return
            if has_dialogue_choices(self.current_npc):
                tree = self.current_npc.dialogue_tree
                nodes = tree.get("nodes", {})
                current_id = tree.get("_current", "start")
                node = nodes.get(current_id, nodes.get("start", {}))
                choices = node.get("choices", [])
                num_choices = len(choices)
                if event.key == pygame.K_UP:
                    self.dialogue_choice_index = (self.dialogue_choice_index - 1) % max(num_choices, 1)
                    return
                if event.key == pygame.K_DOWN:
                    self.dialogue_choice_index = (self.dialogue_choice_index + 1) % max(num_choices, 1)
                    return
                if event.key == pygame.K_RETURN and self.dialogue_box.input_active:
                    self.dialogue_box.update_dialogue(str(self.dialogue_choice_index + 1))
                    self.dialogue_choice_index = 0
                    return
                for i in range(min(num_choices, 9)):
                    if event.key == getattr(pygame, f"K_{i + 1}", None):
                        self.dialogue_choice_index = i
                        self.dialogue_box.update_dialogue(str(i + 1))
                        self.dialogue_choice_index = 0
                        return
                if event.key == pygame.K_PAGEUP:
                    self.dialogue_box.scroll_up()
                    return
                if event.key == pygame.K_PAGEDOWN:
                    self.dialogue_box.scroll_down()
                    return
                return
            if event.key == pygame.K_UP:
                self.dialogue_box.scroll_up()
                return
            if event.key == pygame.K_DOWN:
                self.dialogue_box.scroll_down()
                return
            if event.key == pygame.K_RETURN and self.dialogue_box.input_active:
                self.dialogue_box.update_dialogue(self.dialogue_box.user_message)
                return
            if self.dialogue_box.input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.dialogue_box.user_message = self.dialogue_box.user_message[:-1]
                else:
                    self.dialogue_box.user_message += event.unicode
                return
            return

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
            if self.player.health <= 0:
                if self.sfx:
                    self.sfx.play("player_death")
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
                if self.sfx:
                    self.sfx.play("item_pickup")
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
            self.dialogue_box.set_item_message("Rest: 1=3hr  2=6hr  3=12hr  Esc=Cancel")
            self.item_message_active = True
            return

        if event.key == pygame.K_TAB:
            self.pending_action = "open_menu"
            return

        if event.key == pygame.K_F1:
            self.debug_reveal = not self.debug_reveal
            return

        if event.key == pygame.K_F2:
            if self.maze.door_position and not self.maze.door_revealed:
                self.maze.reveal_door()
                self.dialogue_box.set_item_message("DEBUG: Boss revealed.")
                self.item_message_active = True
            return

        if event.key == pygame.K_F3:
            if self.maze.door_position:
                self.gate_cleared = True
                self.maze.door_revealed = True
                self.maze.place_door_tile()
                self.dialogue_box.set_item_message("DEBUG: Door forced open.")
                self.item_message_active = True
            return

        if event.key == pygame.K_ESCAPE:
            if self.quest_log_active:
                self.quest_log_active = False
                return
            self.pending_action = "open_pause"
            return

        if event.key == pygame.K_p:
            self.pending_action = "open_status"
            return

        if event.key == pygame.K_b:
            self.pending_action = "open_story"
            return

    # ------------------------------------------------------------------
    # NPC, Shop, Inventory, Rest
    # ------------------------------------------------------------------

    def _build_quest_context(self, npc) -> dict | None:
        quest_id = getattr(npc, "quest_id", None)
        if quest_id is None or quest_id not in self.quests:
            return None
        q = self.quests[quest_id]
        return {
            "quest_id": q.id,
            "title": q.title,
            "type": q.type,
            "status": q.status,
            "description": q.description,
            "dc": getattr(q, "dc", 10),
        }

    def _start_npc_combat(self, npc):
        """Start combat against an AggressiveNPC using their stored monster template."""
        from src.models.encounter import CombatEvent
        from src.models.monster import instantiate_monster

        monster_data = getattr(npc, "npc_monster", None)
        if not monster_data:
            monster_data = {
                "name": npc.name or "Hostile NPC",
                "species": "npc",
                "hp_range": [15, 20],
                "ac_range": [10, 12],
                "damage_type": "physical",
            }
        monster = instantiate_monster(monster_data, self.current_room + 1)

        taunt = ""
        tree = getattr(npc, "dialogue_tree_incomplete", None) or getattr(npc, "dialogue_tree", None)
        if tree and "nodes" in tree:
            start_node = tree["nodes"].get("start", {})
            taunt = start_node.get("prompt", f"{npc.name} attacks!")

        event_id = -(npc.id)
        combat_event = CombatEvent(
            id=event_id,
            name=f"Fight: {npc.name}",
            description=taunt or f"{npc.name} attacks!",
            monsters=[monster],
            room_level=self.current_room + 1,
        )
        self._npc_combat_map[event_id] = npc
        self.combat_handler.start(combat_event)

    def _show_npc_taunt(self, npc):
        """Show the NPC's taunt dialogue before starting combat."""
        taunt = ""
        tree = getattr(npc, "dialogue_tree_incomplete", None) or getattr(npc, "dialogue_tree", None)
        if tree and "nodes" in tree:
            start_node = tree["nodes"].get("start", {})
            taunt = start_node.get("prompt", "")
        if not taunt:
            taunt = f"{npc.name} challenges you to fight!"
        self._pending_npc_combat = npc
        self.dialogue_box.set_item_message(f"{npc.name}: \"{taunt}\"")
        self.item_message_active = True

    def _handle_npc_interaction(self, npc):
        if self.combat_handler.active:
            return

        if isinstance(npc, AggressiveNPC) and not npc.combat_defeated:
            self._show_npc_taunt(npc)
            return

        if not is_npc_available(npc, self.day_night.current_period):
            self.dialogue_box.set_item_message(f"{npc.name or 'NPC'} is not available right now.")
            self.item_message_active = True
            return

        turned_in = self.quest_manager.check_turn_in(npc, self.player)
        if turned_in:
            if getattr(npc, "quest_id", None) == turned_in.id and npc.dialogue_tree:
                self.dialogue_box.quest_context = self._build_quest_context(npc)
                self.dialogue_box.start_dialogue(npc)
                return
            msg = f"Quest completed: {turned_in.title}!"
            if turned_in.reward and turned_in.reward.money:
                msg += f" +{turned_in.reward.money} gold!"
            if turned_in.type == "escort":
                farewell = self.follower_manager.remove_follower_for_quest(turned_in.id)
                if farewell:
                    msg += f" {farewell}"
            self.dialogue_box.set_item_message(msg)
            self.item_message_active = True
            return

        qctx = self._build_quest_context(npc)
        self.dialogue_box.quest_context = qctx
        if qctx:
            npc.current_dc = qctx.get("dc", 10)
        self.dialogue_box.start_dialogue(npc)

        offered = self.quest_manager.try_offer_quest(npc, self.player)
        if offered and offered.type == "escort":
            escort_msg = self.follower_manager.start_escort(offered, npc)
            if escort_msg:
                self.dialogue_box.set_item_message(escort_msg)
                self.item_message_active = True

    def _handle_rest_input(self, event):
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
        msg = self.follower_manager.talk_to_follower()
        self.dialogue_box.set_item_message(msg)
        self.item_message_active = True

    def get_quest_log(self) -> dict:
        log = self.quest_manager.get_quest_log()
        log["combat_stats"] = dict(self.player.combat_record)
        log["encounter_stats"] = dict(self.player.encounter_record)
        log["encounters_cleared"] = self.resolved_encounters
        log["total_encounters"] = self.total_encounters
        log["encounter_clear_fraction"] = self.encounter_clear_fraction
        from config import DOOR_REVEAL_THRESHOLD

        log["door_reveal_threshold"] = DOOR_REVEAL_THRESHOLD
        return log

    def get_follower_info(self) -> list[dict]:
        return self.follower_manager.get_follower_info()

    def _open_shop(self, merchant_npc):
        self.shop_active = True
        self.shop_npc = merchant_npc
        self.shop_view = ShopView(self.screen, self.font, merchant_npc, self.player)

    def _handle_shop_input(self, event):
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
            self._sync_inv_scroll(inv_length)
        elif event.key == pygame.K_DOWN:
            self.player.selected_item_index = (self.player.selected_item_index + 1) % inv_length
            self._sync_inv_scroll(inv_length)
        elif event.key in (pygame.K_RETURN, pygame.K_u):
            if self.sfx:
                self._play_item_use_sfx()
            message = self.player.use_item()
            self.item_message_active = True
            self.dialogue_box.set_item_message(message)
        elif event.key == pygame.K_e:
            item_name = inventory[self.player.selected_item_index][0]
            message = self.player.equip_weapon(item_name)
            self.item_message_active = True
            self.dialogue_box.set_item_message(message)
        elif event.key == pygame.K_d:
            self.item_detail_active = True

    def _sync_inv_scroll(self, inv_length):
        from config import SCREEN_HEIGHT

        M, title_h, detail_h, ctrl_h = 20, 40, 155, 25
        list_top = M + title_h + 5
        list_bottom = SCREEN_HEIGHT - M - detail_h - ctrl_h - 10
        stride = 26 + 8
        visible = max(1, (list_bottom - list_top) // stride)
        scroll = getattr(self.player, "_inv_scroll", 0)
        idx = self.player.selected_item_index
        if idx < scroll:
            scroll = idx
        elif idx >= scroll + visible:
            scroll = idx - visible + 1
        self.player._inv_scroll = max(0, min(scroll, inv_length - visible))

    # ------------------------------------------------------------------
    # Update & Draw
    # ------------------------------------------------------------------

    def update(self, current_time):
        self.day_night.update_realtime(current_time)
        prev_period = self.day_night.current_period
        self.day_night.update()

        if self.day_night.real_time and self.day_night.current_period != prev_period:
            new_period = self.day_night.current_period
            self._update_fog()
            if not self.has_active_overlay and not self.item_message_active:
                msg = PERIOD_TRANSITION_MESSAGES.get(new_period.value, "")
                if msg:
                    self.dialogue_box.set_item_message(msg)
                    self.item_message_active = True

        if hasattr(self, "_last_survival_ms"):
            delta = current_time - self._last_survival_ms
        else:
            delta = 0
        self._last_survival_ms = current_time
        if delta > 0:
            warnings = self.survival.on_time_update(self.player, delta)
            for w in warnings:
                if not self.has_active_overlay and not self.item_message_active:
                    self.dialogue_box.set_item_message(w)
                    self.item_message_active = True

        if self.dialogue_box.generating:
            self.dialogue_box.check_generation()

        for npc in self.npcs:
            if hasattr(npc, "update_position"):
                if isinstance(npc, RandomNPC):
                    npc.update_position(self.maze, current_time)
                elif isinstance(npc, AggressiveNPC):
                    npc.update_position(self.maze, (self.player.x, self.player.y), current_time)

        if (
            not self.combat_handler.active
            and not self.dialogue_box.event_active
            and not self.item_message_active
        ):
            for npc in self.npcs:
                if (
                    isinstance(npc, AggressiveNPC)
                    and not npc.combat_defeated
                    and npc.x == self.player.x
                    and npc.y == self.player.y
                ):
                    self._show_npc_taunt(npc)
                    break

        if not self.inventory_active and not self.dialogue_box.dialogue_active:
            self.current_npc = self.player.get_nearby_npc(self.npcs)
            self.player_at_item = self.player.is_item_at_player_position(self.maze)

    def _play_item_use_sfx(self):
        if not self.sfx:
            return
        from src.models.items import Drink, Food

        inv = self.player.get_inventory()
        if not inv:
            return
        idx = self.player.selected_item_index
        if idx >= len(inv):
            return
        _, item = inv[idx]
        if isinstance(item, Food):
            self.sfx.play("item_food")
        elif isinstance(item, Drink):
            self.sfx.play("item_drink")
        else:
            self.sfx.play("item_tool")

    def draw(self, current_time):
        if self.combat_handler.active:
            self.combat_handler.draw()
            return

        if self.shop_active and self.shop_view:
            self.screen.fill((0, 0, 0))
            self.shop_view.draw()
            if self.item_message_active:
                self.game_view.draw_dialogue_and_messages(self.player, self.maze, self.item_message_active, False)
            return

        period = self.day_night.current_period
        night_alpha = get_night_overlay_alpha(period, self.day_night.period_progress)

        dlg_choices = None
        if has_dialogue_choices(self.current_npc):
            tree = self.current_npc.dialogue_tree
            nodes = tree.get("nodes", {})
            current_id = tree.get("_current", "start")
            node = nodes.get(current_id, nodes.get("start", {}))
            dlg_choices = node.get("choices")

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
            period_progress=self.day_night.period_progress,
            item_detail_active=self.item_detail_active,
            event_type_map=self._event_type_map if self.debug_reveal else None,
            event_flag_map=self._event_flag_map,
            dialogue_choices=dlg_choices,
            dialogue_choice_index=self.dialogue_choice_index,
        )
