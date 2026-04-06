import random
import pygame
from src.views.gameplay_view import GameView
from src.models.npc import RandomNPC, AggressiveNPC, MerchantNPC
from src.models.items import EscortItem
from src.registry import registry


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

        # UI / State variables
        self.inventory_active = False
        self.item_message_active = False
        self.item_message = None
        self.player_at_item = False
        self.current_npc = None
        self.running = True

        # Shop state
        self.shop_active = False
        self.shop_npc = None
        self.shop_mode = "buy"  # "buy" or "sell"
        self.shop_selected_index = 0

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

    def run(self):
        """Main game loop."""
        clock = pygame.time.Clock()

        while self.running:
            current_time = pygame.time.get_ticks()
            self.handle_events()
            self.update(current_time)
            self.draw(current_time)
            pygame.display.flip()
            clock.tick(60)

        pygame.quit()

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
            return

        if event.key == pygame.K_ESCAPE:
            return

    def _handle_event_input(self, event):
        """Handle keyboard input during an active event."""
        current_event = self.dialogue_box.current_event
        if not current_event:
            return

        if self.dialogue_box.awaiting_roll:
            if event.key == pygame.K_r:
                dice_roll = random.randint(1, 20)
                if current_event.type == "combat":
                    result = current_event.resolve(dice_roll, self.player)
                elif current_event.type == "puzzle":
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

                if current_event.resolved:
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

        elif current_event.type == "puzzle" and not self.dialogue_box.event_context.get("result"):
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

                    if quest.type == "escort" and hasattr(quest, 'escort_npc_id'):
                        self._start_escort(quest)

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
        self.dialogue_box.set_item_message(reward_msg)
        self.item_message_active = True

    def _start_escort(self, quest):
        """Remove the escort NPC from the world and add them to inventory."""
        escort_npc_id = getattr(quest, 'escort_npc_id', None)
        if not escort_npc_id:
            return
        npc_to_escort = None
        for npc in self.npcs:
            if npc.id == escort_npc_id:
                npc_to_escort = npc
                break
        if npc_to_escort:
            self.npcs.remove(npc_to_escort)
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
            shop_active=self.shop_active,
            shop_npc=self.shop_npc,
            shop_mode=self.shop_mode,
            shop_selected_index=self.shop_selected_index,
        )
