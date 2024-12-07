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

    def handle_keydown(self, event):
        """Handle key presses."""
        
        # Movement keys (Handled only if no dialogue, no inventory, no item message)
        if event.key in [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN]:
            if not self.dialogue_box.dialogue_active and not self.inventory_active and not self.item_message_active:
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

                # After moving, check for items/events/NPCs
                if self.player.is_on_event_tile(self.maze):
                    self.dialogue_box.start_event(self.maze)
                    self.maze.grid[self.player.y][self.player.x] = 0
                else:
                    self.player_at_item = self.player.is_item_at_player_position(self.maze)
                    self.current_npc = self.player.get_nearby_npc(self.npcs)

        # Close item message box
        if (event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE) and self.item_message_active:
            self.item_message = None
            self.item_message_active = False
            self.dialogue_box.clear_item_message()

        # Inventory usage (not implemented details here, just placeholder)
        if self.inventory_active and not self.item_message_active:
            # Handle inventory navigation and usage
            if self.inventory_active and not self.item_message_active:
                self.handle_inventory_input(event)
                return

        # Interact (Enter key actions)
        if event.key == pygame.K_RETURN:
            self.handle_enter_key()

        # Dialogue input
        if self.dialogue_box.input_active and event.key != pygame.K_RETURN:
            self.handle_dialogue_input(event)

        # Dialogue scrolling
        if self.dialogue_box.dialogue_active:
            self.handle_dialogue_scrolling(event)

        # Escape key actions
        if event.key == pygame.K_ESCAPE:
            self.handle_escape_key()

        # Toggle inventory
        if event.key == pygame.K_i and not self.dialogue_box.dialogue_active:
            self.inventory_active = not self.inventory_active

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
        """Handle navigation and usage of the player's inventory."""
        inventory = self.player.get_inventory()
        inventory_length = len(inventory)
        
        if inventory_length == 0:
            return
            
        if event.key == pygame.K_UP:
            # Move selection up
            self.player.selected_item_index = (self.player.selected_item_index - 1) % inventory_length
        elif event.key == pygame.K_DOWN:
            # Move selection down
            self.player.selected_item_index = (self.player.selected_item_index + 1) % inventory_length
        elif event.key == pygame.K_RETURN:
            # Use the currently selected item
            message = self.player.use_item()
            # If you want to show a message when item is used:
            self.item_message_active = True
            self.dialogue_box.set_item_message(message)
        elif event.key == pygame.K_u:
            # Another key (like 'U') to use the currently selected item if you don't want to tie it to Enter
            message = self.player.use_item()
            self.item_message_active = True
            self.dialogue_box.set_item_message(message)
        elif event.key == pygame.K_ESCAPE:
            # Close inventory
            self.inventory_active = False
            
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
