import os
import torch
import pygame
import random
from typing import Optional
from config import GRID_SIZE, LLM_MODEL_PATH, HF_ENV
from pydantic import BaseModel
from utils.display_utils import game_to_screen
from transformers import AutoTokenizer, AutoModelForCausalLM


hf_token = os.getenv(HF_ENV)

tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL_PATH)
model = AutoModelForCausalLM.from_pretrained(LLM_MODEL_PATH,
                                             token = hf_token)
model.to('cuda')

if torch.cuda.is_available():
    device = torch.device('cuda')
elif torch.backends.mps.is_available():
    device = torch.device('mps')
    
model.to(device)

class NPC(BaseModel):
    """Base NPC class with behavior, image, and color."""
    x: int
    y: int
    image_path: Optional[str] = None
    name : Optional[str] = None
    job: Optional[str] = None
    hobby: Optional[str] = None
    personality: Optional[str] = None
    environment: Optional[str] = None
    interaction_history: list = []
    color: tuple = (0, 255, 0)  # Green by default
    move_interval: int = 10000  # Move every 10 seconds
    last_move_time: int = 0 #to track the last time an npc moved

    class Config:
        arbitrary_types_allowed = True

    def draw(self, screen):
        """Draw the NPC at the specified position."""
        screen_x, screen_y = game_to_screen(self.x, self.y)
        rect = pygame.Rect(screen_x,screen_y, GRID_SIZE, GRID_SIZE)
        pygame.draw.rect(screen, self.color, rect)

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

        # Generate environment if not provided
        if not self.environment:
            self.environment = random.choice(['forest', 'cave', 'plain', 'city'])

        # Populate missing fields
        self.name = self.name or random.choice(names)
        self.personality = self.personality or random.choice(personalities)
        self.job = self.job or random.choice(jobs[self.environment])
        self.hobby = self.hobby or random.choice(hobbies[self.environment])
        
    def can_move(self):
        """check if the NPC can move based on the move interval"""
        current_time = pygame.time.get_ticks()
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
    
    def generate_response(self, player_input) -> str:
        """Generate a response using the LLM."""
        
        # Tokenize the prompt
        history = self.construct_chat_history(player_input)
        inputs = tokenizer("\n#################\n".join(history),
                   return_tensors='pt',
                   truncation=True,
                   max_length=1024)
        
        if torch.cuda.is_available():
            inputs = {k: v.to('cuda') for k, v in inputs.items()}
            
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=150,
                pad_token_id=tokenizer.eos_token_id,
                temperature=1.0
            )

        response = tokenizer.decode(outputs[0], 
                    skip_special_tokens=True)
        
        self.interaction_history[-1] = response.split("\n#################\n")[-1]
        
        if self.is_appropriate(response):
            return f"{self.name}:{response.split(':')[-1]}"
        else:
            return self.get_fallback_response()
            
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
    color: tuple = (0, 255, 255)
    home_x: int
    home_y: int
    movement_range: int = 2
    
    def prepare(self):
        self.generate_personality_document()
        self.system_instruct()
    
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
    
    def prepare(self):
        self.generate_personality_document()
        self.system_instruct()
    
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
                
    def in_line_of_sight(self, maze, player_pos, dist:int=5):
        """Check if the player is within {dist} squares and there are no walls in between."""
        dx = abs(player_pos[0] - self.x)
        dy = abs(player_pos[1] - self.y)

        # Check if the player is in the same row or column within 5 squares
        if dx <= dist and dy == 0:
            # Player is in the same row, check for walls between NPC and player
            x_step = 1 if player_pos[0] > self.x else -1
            for i in range(1, dx + 1):
                if maze.is_wall(self.x + i * x_step, self.y):
                    return False
            return True
        elif dy <= dist and dx == 0:
            # Player is in the same column, check for walls between NPC and player
            y_step = 1 if player_pos[1] > self.y else -1
            for i in range(1, dy + 1):
                if maze.is_wall(self.x, self.y + i * y_step):
                    return False
            return True

        # If the player is not in the same row/column within range
        return False