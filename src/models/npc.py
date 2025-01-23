import random
from pydantic import BaseModel
from typing import Optional, List, Tuple

class NPC(BaseModel):
    """Base NPC class with behavior, image, and color."""
    x: int
    y: int
    id: int ##ids are always unique and in the 100s
    profile_image: Optional[str] = None
    name : Optional[str] = None
    job: Optional[str] = None
    hobby: Optional[str] = None
    personality: Optional[str] = None
    description: Optional[str] = None
    environment: Optional[str] = None
    interaction_history: List[str] = []
    color: Tuple[int, int, int] = (0, 255, 0)  # Green by default
    move_interval: int = 5000  # Move every 5 seconds
    last_move_time: int = 0 #track the last time an npc moved (ms)

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__(**data)
        self.generate_personality_document()
        
    def generate_personality_document(self):
        """Generate personality attributes for the NPC."""
        # Define possible options
        names = ['Arin', 'Belinda', 'Corwin', 'Daphne', 'Eldon', 'Fiona', 'Gareth', 'Helena']
        personalities = ['cheerful', 'grumpy', 'mysterious', 'friendly', 'suspicious', 'stoic']
        hobbies = {
            'forest': ['collecting herbs', 'bird watching', 'tracking animals'],
            'cave': ['mining rare ores', 'exploring caverns', 'studying geology'],
            'plain': ['farming', 'stargazing', 'herding livestock'],
            'city': ['trading goods', 'playing music', 'studying art']
        }
        jobs = {
            'forest': ['hunter', 'herbalist', 'ranger'],
            'cave': ['miner', 'spelunker', 'geologist'],
            'plain': ['farmer', 'shepherd', 'blacksmith'],
            'city': ['merchant', 'artist', 'guard']
        }

        # Generate environment if not provided
        if not self.environment:
            self.environment = random.choice(['forest', 'cave', 'plain', 'city'])

        # Populate missing fields
        self.name = self.name or random.choice(names)
        self.personality = self.personality or random.choice(personalities)
        self.job = self.job or random.choice(jobs[self.environment])
        self.hobby = self.hobby or random.choice(hobbies[self.environment])
        
    def can_move(self, current_time: int) -> bool:
        """check if the NPC can move based on the move interval"""
        if current_time - self.last_move_time >= self.move_interval:
            self.last_move_time = current_time
            return True
        return False

    def system_instruct(self) -> str:
        instructions = f"""'sys': You are playing a video game character. You are {self.name},a {self.job} in a {self.environment}. This environment is in a fantasy
            setting, so limit discussions to the environment, the npc's job, and the npc's hobbies. 
            The npc's personality is {self.personality}. The npc's hobbies are {self.hobby}.
            
            Always follow these rules:
            1. do not speak for the player
            2. do not Roleplay heavily
            3. do not break the fourth wall
            4. do not hallucinate
            5. converse with the NPC but maintain conversational context            
            """
        
        self.interaction_history.append(instructions)
        
        return instructions
    
    def construct_chat_history(self, player_input: str = "") -> str:
        if len(self.interaction_history) == 1:
    
            self.interaction_history.append(f"player input: walks up and greets {self.name}")
            self.interaction_history.append(f"sys: This is the first time you are meeting the player character in this {self.environment}. Greet them according to your personal details. Do not continue the conversation by yourself.")
            self.interaction_history.append(f"{self.name} response:")
            history = self.interaction_history
            
        elif len(self.interaction_history) > 5:
            history = [self.interaction_history[0]]
            self.interaction_history.append(f'player: {player_input}')
            self.interaction_history.append(f"{self.name} response:")
            history.extend(self.interaction_history[-6:])
            
        else:
            self.interaction_history.append(f'player: {player_input}')
            self.interaction_history.append(f"{self.name} response:")
            history = self.interaction_history
            
        return history
            
    def is_appropriate(self, response: str) -> bool:
        """Check if the response is appropriate."""
        # Simple keyword-based filtering
        banned_words = ['chibi', 'loli', 'shota', 'nsfw']
        for word in banned_words:
            if word in response.lower():
                return False
        return True
    
    def get_fallback_response(self) -> str:
        """Get a fallback response."""
        fallback_responses = [
            "I'm not sure how to respond to that.",
            "Let's talk about something else.",
            "I don't have anything to say about that."
        ]
        return random.choice(fallback_responses)
    
    
class StaticNPC(NPC):
    color: tuple = (0, 255, 0)
    """NPC that doesn't move."""

    def prepare(self):
        self.generate_personality_document()
        self.system_instruct()

class RandomNPC(NPC):
    """NPC that moves randomly around a fixed point."""
    color: Tuple[int, int, int] = (0, 255, 255)
    home_x: int
    home_y: int
    movement_range: int = 2
    
    def prepare(self):
        self.generate_personality_document()
        self.system_instruct()
    
    def update_position(self, maze, current_time: int):
        """Update the NPC's position randomly"""
        if not self.can_move(current_time):
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
    color: Tuple[int, int, int] = (255, 0, 0)
    dist: int = 5
    
    def prepare(self):
        self.generate_personality_document()
        self.system_instruct()
    
    def update_position(self, maze, player_pos, current_time):
        """Move randomly or move toward player if within range and in line of sight."""
        if not self.can_move(current_time):
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
        """Check if the player is within {dist} squares and there are no walls in between."""
        dx = abs(player_pos[0] - self.x)
        dy = abs(player_pos[1] - self.y)

        # Check if the player is in the same row or column within 5 squares
        if dx <= self.dist and dy == 0:
            # Player is in the same row, check for walls between NPC and player
            x_step = 1 if player_pos[0] > self.x else -1
            for i in range(1, dx + 1):
                if maze.is_wall(self.x + i * x_step, self.y):
                    return False
            return True
        elif dy <= self.dist and dx == 0:
            # Player is in the same column, check for walls between NPC and player
            y_step = 1 if player_pos[1] > self.y else -1
            for i in range(1, dy + 1):
                if maze.is_wall(self.x, self.y + i * y_step):
                    return False
            return True

        # If the player is not in the same row/column within range
        return False