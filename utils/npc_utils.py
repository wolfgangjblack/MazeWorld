from pydantic import BaseModel
import random
from config import GRID_SIZE
import pygame

class NPC(BaseModel):
    """Base NPC class with behavior, image, and color."""
    x: int
    y: int
    # image_path: str
    color: tuple = (0, 255, 0)  # Green by default
    move_interval: int = 10000  # Move every 10 seconds
    last_move_time: int = 0 #to track the last time an npc moved

    def draw(self, screen):
        """Draw the NPC at the specified position."""
        rect = pygame.Rect(self.x * GRID_SIZE, self.y * GRID_SIZE, GRID_SIZE, GRID_SIZE)
        pygame.draw.rect(screen, self.color, rect)

    def can_move(self):
        """check if the NPC can move based on the move interval"""
        current_time = pygame.time.get_ticks()
        if current_time - self.last_move_time >= self.move_interval:
            self.last_move_time = current_time
            return True
        return False

    def npc_chat(self) -> str:
        """Placeholder for NPC chat using a locally hosted LLM."""
        # You can replace this with the actual LLM call
        return "hello"

class StaticNPC(NPC):
    color: tuple = (0, 255, 0)
    """NPC that doesn't move."""
    
    def update(self):
        pass

class RandomNPC(NPC):
    """NPC that moves randomly around a fixed point."""
    color: tuple = (0, 255, 255)
    home_x: int
    home_y: int
    movement_range: int = 2
    
    def update(self, maze):
        
        if not self.can_move():
            return
        
        """Move randomly within a fixed range."""
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        direction = random.choice(directions)
        new_x = self.x + direction[0]
        new_y = self.y + direction[1]

        if (
            self.home_x - self.movement_range <= new_x <= self.home_x + self.movement_range
            and self.home_y - self.movement_range <= new_y <= self.home_y + self.movement_range
            and not maze.is_wall(new_x, new_y)
        ):
            self.x, self.y = new_x, new_y

class AggressiveNPC(NPC):
    """NPC that moves randomly until the player is within 5 squares and in line of sight."""
    color:tuple = (255, 0, 0)
    
    def update(self, maze, player_pos):
        """Move randomly or move toward player if within range and in line of sight."""
        if not self.can_move():
            return

        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        # Check if the player is within 5 squares in line of sight
        if self.in_line_of_sight(maze, player_pos):
            # Move toward the player
            if player_pos[0] > self.x and not maze.is_wall(self.x + 1, self.y):
                self.x += 1
            elif player_pos[0] < self.x and not maze.is_wall(self.x - 1, self.y):
                self.x -= 1
            elif player_pos[1] > self.y and not maze.is_wall(self.x, self.y + 1):
                self.y += 1
            elif player_pos[1] < self.y and not maze.is_wall(self.x, self.y - 1):
                self.y -= 1
        else:
            # Move randomly
            direction = random.choice(directions)
            new_x = self.x + direction[0]
            new_y = self.y + direction[1]

            if not maze.is_wall(new_x, new_y):
                self.x, self.y = new_x, new_y
                
    def in_line_of_sight(self, maze, player_pos):
        """Check if the player is within 5 squares and there are no walls in between."""
        dx = abs(player_pos[0] - self.x)
        dy = abs(player_pos[1] - self.y)

        # Check if the player is in the same row or column within 5 squares
        if dx <= 5 and dy == 0:
            # Player is in the same row, check for walls between NPC and player
            x_step = 1 if player_pos[0] > self.x else -1
            for i in range(1, dx + 1):
                if maze.is_wall(self.x + i * x_step, self.y):
                    return False
            return True
        elif dy <= 5 and dx == 0:
            # Player is in the same column, check for walls between NPC and player
            y_step = 1 if player_pos[1] > self.y else -1
            for i in range(1, dy + 1):
                if maze.is_wall(self.x, self.y + i * y_step):
                    return False
            return True

        # If the player is not in the same row/column within range
        return False