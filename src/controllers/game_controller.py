
def player_movement(player, event, maze):
    """Handle player movement and check for wall collisions."""
    new_x, new_y = self.x, self.y

    # Check for movement key presses and update position accordingly
    if event.key == pygame.K_LEFT:
        new_x -= 1
    elif event.key == pygame.K_RIGHT:
        new_x += 1
    elif event.key == pygame.K_UP:
        new_y -= 1
    elif event.key == pygame.K_DOWN:
        new_y += 1

    # Check if the new position is a wall
    if not maze.is_wall(new_x, new_y):
        self.x, self.y = new_x, new_y  # Update the player's position if it's not a wall
        
        self.hunger -= 1
        self.thirst -= 1
        
        self.hunger = max(0, self.hunger)
        self.thirst = max(0, self.thirst)
        
        self.apply_hunger_thirst_effects()