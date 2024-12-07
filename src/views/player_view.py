import pygame
from config import GRID_SIZE, HUD_HEIGHT, SCREEN_WIDTH
from src.utils.display_utils import game_to_screen

class PlayerView:
    def draw_player(screen, player):
        screen_x, screen_y = game_to_screen(player.x, player.y)
        player_rect = pygame.Rect(screen_x, screen_y, GRID_SIZE, GRID_SIZE)
        pygame.draw.rect(screen, player.color, player_rect)
        
    def draw_hud(screen, player):
        bar_width = (SCREEN_WIDTH - 80) // 3
        bar_height = 20
        spacing = 20
        hud_y = (HUD_HEIGHT - bar_height) // 2
        
        hunger_x = 20
        thirst_x = hunger_x + bar_width + spacing
        health_x = thirst_x + bar_width + spacing
        
        # Draw hunger bar
        hunger_ratio = player.hunger / player.max_hunger
        hunger_rect = pygame.Rect(hunger_x, hud_y, bar_width * hunger_ratio, bar_height)
        pygame.draw.rect(screen, (255, 165, 0), hunger_rect)
        pygame.draw.rect(screen, (255, 255, 255), (hunger_x, hud_y, bar_width, bar_height), 2)
        
        # Draw thirst bar
        thirst_ratio = player.thirst / player.max_thirst
        thirst_rect = pygame.Rect(thirst_x, hud_y, bar_width * thirst_ratio, bar_height)
        pygame.draw.rect(screen, (65, 105, 225), thirst_rect)
        pygame.draw.rect(screen, (255, 255, 255), (thirst_x, hud_y, bar_width, bar_height), 2)

        # Draw health bar
        health_ratio = player.health / player.max_health
        health_rect = pygame.Rect(health_x, hud_y, bar_width * health_ratio, bar_height)
        pygame.draw.rect(screen, (255, 0, 0), health_rect)
        pygame.draw.rect(screen, (255, 255, 255), (health_x, hud_y, bar_width, bar_height), 2)

        font = pygame.font.SysFont(None, 24)
        hunger_label = font.render("Hunger", True, (255, 255, 255))
        hunger_label_rect = hunger_label.get_rect(center=(hunger_x + bar_width // 2, hud_y - 15))
        screen.blit(hunger_label, hunger_label_rect)

        hunger_value = font.render(f"{int(player.hunger)} / {player.max_hunger}", True, (255, 255, 255))
        hunger_value_rect = hunger_value.get_rect(center=(hunger_x + bar_width // 2, hud_y + bar_height + 15))
        screen.blit(hunger_value, hunger_value_rect)

        thirst_label = font.render("Thirst", True, (255, 255, 255))
        thirst_label_rect = thirst_label.get_rect(center=(thirst_x + bar_width // 2, hud_y - 15))
        screen.blit(thirst_label, thirst_label_rect)

        thirst_value = font.render(f"{int(player.thirst)} / {player.max_thirst}", True, (255, 255, 255))
        thirst_value_rect = thirst_value.get_rect(center=(thirst_x + bar_width // 2, hud_y + bar_height + 15))
        screen.blit(thirst_value, thirst_value_rect)

        health_label = font.render("Health", True, (255, 255, 255))
        health_label_rect = health_label.get_rect(center=(health_x + bar_width // 2, hud_y - 15))
        screen.blit(health_label, health_label_rect)

        health_value = font.render(f"{int(player.health)} / {player.max_health}", True, (255, 255, 255))
        health_value_rect = health_value.get_rect(center=(health_x + bar_width // 2, hud_y + bar_height + 15))
        screen.blit(health_value, health_value_rect)