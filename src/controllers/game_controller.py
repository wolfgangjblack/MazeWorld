import pygame
from src.views.game_view import GameView
from src.models.npc import RandomNPC, AggressiveNPC

class GameController:
    def __init__(self, screen, font, maze, player, npcs, dialogue_box):
        self.screen = screen
        self.font = font
        self.maze = maze
        self.player = player
        self.npcs = npcs
        self.dialogue_box = dialogue_box

        # UI / State variables
        self.inventory_active = False
        self.item_message_active = False
        self.item_message = None
        self.player_at_item = False
        self.current_npc = None
        self.running = True

        # Initialize the main GameView
        self.game_view = GameView(screen, font, dialogue_box)
        

    def run(self):
        """Main game loop."""
        clock = pygame.time.Clock()

        while self.running:
            current_time = pygame.time.get_ticks()
            self.handle_events()
            self.update(current_time)
            self.draw(current_time)
            pygame.display.flip()
            clock.tick(60)  # Limit FPS

        pygame.quit()

    def handle_events(self):
        """Handle all pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN:
                self.handle_keydown(event)

    def after_move_check(self):
        # After the player moves, check for events, items, NPCs
        if self.player.is_on_event_tile(self.maze):
            self.dialogue_box.start_event(self.maze)
            self.maze.grid[self.player.y][self.player.x] = 0
        else:
            self.player_at_item = self.player.is_item_at_player_position(self.maze)
            self.current_npc = self.player.get_nearby_npc(self.npcs)

    def handle_keydown(self, event):
        # 1. If an item message is active, handle that first and exclusively.
        if self.item_message_active:
            if event.key == pygame.K_RETURN:
                # Clear the item message
                self.item_message_active = False
                self.dialogue_box.clear_item_message()
                return
            if event.key == pygame.K_ESCAPE:
                return
            return

        # 2. If inventory is active (and we know item_message_active is false here).
        if self.inventory_active:
            if event.key == pygame.K_ESCAPE:
                self.inventory_active = False
                return
            else:
                # Handle inventory navigation and item usage (Up/own/Enter)
                self.handle_inventory_input(event)
                return

        # 3. If dialogue is active (NPC conversation)
        if self.dialogue_box.dialogue_active:
            if event.key == pygame.K_UP:
                self.dialogue_box.scroll_up()
                return
            elif event.key == pygame.K_DOWN:
                self.dialogue_box.scroll_down()
                return
            elif event.key == pygame.K_ESCAPE:
                self.dialogue_box.end_dialogue()
                self.current_npc = None
                return
            elif event.key == pygame.K_RETURN and self.dialogue_box.input_active:
                self.dialogue_box.update_dialogue(self.dialogue_box.user_message)
                return
            elif self.dialogue_box.input_active:
                if event.key == pygame.K_BACKSPACE:
                    self.dialogue_box.user_message = self.dialogue_box.user_message[:-1]
                else:
                    self.dialogue_box.user_message += event.unicode
                return

            return

        # 4. No dialogue, no inventory, no item message active: handle normal gameplay
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

        # Interact key when no inventory/dialogue/item message
        if event.key == pygame.K_RETURN:
            # If player at item
            if self.player_at_item:
                item_message = self.player.pick_up_item(self.maze)
                self.item_message_active = True
                self.player_at_item = False
                self.dialogue_box.set_item_message(item_message)
                return
            # If player near NPC
            if self.current_npc:
                self.dialogue_box.start_dialogue(self.current_npc)
                return

        # Toggle inventory
        if event.key == pygame.K_i:
            self.inventory_active = not self.inventory_active
            return

        # Escape key in normal state does nothing or can be assigned a function
        if event.key == pygame.K_ESCAPE:
            # If you want Escape to do something here, do it. Otherwise, no action.
            return

    def handle_enter_key(self):
        """Handle actions triggered by pressing Enter."""
        if not self.inventory_active and not self.item_message_active:
            if self.player_at_item:
                # Player picks up item
                item_message = self.player.pick_up_item(self.maze)
                self.item_message_active = True
                self.player_at_item = False
                self.dialogue_box.set_item_message(item_message)
            elif self.current_npc and not self.dialogue_box.dialogue_active:
                # Start NPC conversation
                self.dialogue_box.start_dialogue(self.current_npc)
            elif self.dialogue_box.dialogue_active and self.dialogue_box.input_active:
                # Player responds in dialogue
                self.dialogue_box.update_dialogue(self.dialogue_box.user_message)

    def handle_dialogue_input(self, event):
        """Handle typing input for NPC dialogue."""
        if event.key == pygame.K_BACKSPACE:
            self.dialogue_box.user_message = self.dialogue_box.user_message[:-1]
        else:
            self.dialogue_box.user_message += event.unicode

    def handle_dialogue_scrolling(self, event):
        """Handle scrolling through dialogue history."""
        if event.key == pygame.K_UP:
            self.dialogue_box.scroll_up()
        elif event.key == pygame.K_DOWN:
            self.dialogue_box.scroll_down()

    def handle_escape_key(self):
        """Handle actions triggered by pressing Escape."""
        if self.dialogue_box.dialogue_active:
            self.dialogue_box.end_dialogue()
            self.current_npc = None
        elif self.inventory_active:
            self.inventory_active = False
            
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
            # Use the currently selected item
            message = self.player.use_item()
            self.item_message_active = True
            self.dialogue_box.set_item_message(message)
        elif event.key == pygame.K_u:
            message = self.player.use_item()
            self.item_message_active = True
            self.dialogue_box.set_item_message(message)

            
    def update(self, current_time):
        """Update game logic (NPC movement, etc.)"""
        # Update NPC positions
        for npc in self.npcs:
            if hasattr(npc, 'update_position'):
                if isinstance(npc, RandomNPC):
                    npc.update_position(self.maze, current_time)
                elif isinstance(npc, AggressiveNPC):
                    npc.update_position(self.maze, (self.player.x, self.player.y), current_time)

        # If no dialogue and inventory closed, update current npc & item info
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
            player_at_item=self.player_at_item
        )
