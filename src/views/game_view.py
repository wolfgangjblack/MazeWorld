import pygame
from config import BLACK, WHITE, SCREEN_WIDTH, SCREEN_HEIGHT
from src.views.npc_view import NPCView
from src.views.player_view import PlayerView
from src.utils.item_utils import ENTITY_IDS

class GameView:
    def __init__(self, screen, font, dialogue_box):
        self.screen = screen
        self.font = font
        self.dialogue_box = dialogue_box
        self.npc_view = NPCView()
        self.player_view = PlayerView()

    def draw_game(self, maze, player, npcs, inventory_active, item_message_active, current_npc, player_at_item):
        self.screen.fill(BLACK)
        if inventory_active:
            self.draw_inventory(player)
        else:
            maze.draw(self.screen)

            for npc in npcs:
                self.npc_view.draw_npc(self.screen, npc)

            self.player_view.draw_player(self.screen, player)
            self.player_view.draw_hud(self.screen, player)

        # If player is near NPC and no item message, prompt to talk
        if (current_npc and not item_message_active and
            not inventory_active and not self.dialogue_box.dialogue_active):
            text_surface = self.font.render("Press Enter to talk", True, WHITE)
            self.screen.blit(text_surface, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 50))

        self.draw_dialogue_and_messages(player, maze, inventory_active, item_message_active, player_at_item)

    def draw_inventory(self, player):
        pygame.draw.rect(self.screen,
                         (200, 200, 200),
                         pygame.Rect(100, 100, SCREEN_WIDTH - 200, SCREEN_HEIGHT - 200))
        inventory = player.get_inventory()
        for index, (item, quantity) in enumerate(inventory):
            color = (255, 0, 0) if index == player.selected_item_index else (0, 0, 0)
            item_text = f"{quantity}x {item}"
            text_surface = self.font.render(item_text, True, color)
            self.screen.blit(text_surface, (150, 150 + index * 40))

        exit_text = self.font.render("Press 'Esc' to exit", True, (0, 0, 0))
        self.screen.blit(exit_text, (150, SCREEN_HEIGHT - 150))

    def draw_dialogue_and_messages(self, player, maze, inventory_active, item_message_active, player_at_item):
        if item_message_active or self.dialogue_box.dialogue_active:
            self.dialogue_box.draw()
        elif player_at_item:
            # Show prompt to pick up item
            item_id = maze.grid[player.y][player.x]
            item = ENTITY_IDS[item_id]
            prompt = f"Press 'Enter' to pick up {item}"
            self.dialogue_box.set_item_message(prompt)
            self.dialogue_box.draw()
        else:
            self.dialogue_box.clear_item_message()
