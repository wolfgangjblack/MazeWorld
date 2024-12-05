import pygame
from config import SCREEN_WIDTH, SCREEN_HEIGHT, BLACK, WHITE

def draw_dialogue_box(screen, font, current_npc = None, npc_message = "", user_message = "", item_message=None):
    """Draw the dialogue box at the bottom of the screen."""
    dialogue_box_rect = pygame.Rect(0, SCREEN_HEIGHT - 100, SCREEN_WIDTH, 100)
    pygame.draw.rect(screen, WHITE, dialogue_box_rect)

    # If there is an item message, show it at the top of the box
    if item_message:
        item_text_surface = font.render(f"{item_message}", True, BLACK)
        screen.blit(item_text_surface, (10, SCREEN_HEIGHT - 90))
    elif current_npc:
        # NPC message
        npc_text_surface = font.render(f"{npc_message}", True, BLACK)
        screen.blit(npc_text_surface, (10, SCREEN_HEIGHT - 90))

        # User message
        user_text_surface = font.render(f"You: {user_message}", True, BLACK)
        screen.blit(user_text_surface, (10, SCREEN_HEIGHT - 60))
    else:
        pass

def player_near_npc(player_pos, npc):
    """Check if the player is within 1 square of the NPC."""
    return abs(player_pos[0] - npc.x) <= 1 and abs(player_pos[1] - npc.y) <= 1

def handle_npc_response(npc, user_input):
    if npc:
        npc_message = npc.generate_response(user_input)
        return npc_message
    else:
        return "There is no one here to talk too..."