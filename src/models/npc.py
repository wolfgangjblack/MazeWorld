import random
from pydantic import BaseModel
from typing import Optional, List, Tuple

from src.prompts import get_prompt_set


class NPC(BaseModel):
    """Base NPC class with behavior, image, and color."""
    x: int
    y: int
    id: int
    profile_image: Optional[str] = None
    name: Optional[str] = None
    job: Optional[str] = None
    hobby: Optional[str] = None
    personality: Optional[str] = None
    description: Optional[str] = None
    environment: Optional[str] = None
    identity: Optional[str] = None
    interaction_history: List[dict] = []
    has_met_player: bool = False
    color: Tuple[int, int, int] = (0, 255, 0)
    move_interval: int = 5000
    last_move_time: int = 0

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__(**data)
        self.generate_personality_document()

    def generate_personality_document(self):
        """Generate personality attributes for the NPC."""
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

        if not self.environment:
            self.environment = random.choice(['forest', 'cave', 'plain', 'city'])

        self.name = self.name or random.choice(names)
        self.personality = self.personality or random.choice(personalities)
        self.job = self.job or random.choice(jobs[self.environment])
        self.hobby = self.hobby or random.choice(hobbies[self.environment])

    def build_identity(self):
        """Build the conversation identity using the prompt library."""
        prompts = get_prompt_set()
        self.identity = prompts.conversation_identity(
            name=self.name,
            job=self.job,
            personality=self.personality,
            hobby=self.hobby,
            env=self.environment,
            env_name=self.environment or "Unknown",
        )

    def add_turn(self, role: str, content: str):
        self.interaction_history.append({"role": role, "content": content})

    def get_recent_history(self, max_turns: int = 6) -> list[dict]:
        if len(self.interaction_history) <= max_turns:
            return list(self.interaction_history)
        return self.interaction_history[-max_turns:]

    def can_move(self, current_time: int) -> bool:
        if current_time - self.last_move_time >= self.move_interval:
            self.last_move_time = current_time
            return True
        return False

    def is_appropriate(self, response: str) -> bool:
        banned_words = ['chibi', 'loli', 'shota', 'nsfw']
        for word in banned_words:
            if word in response.lower():
                return False
        return True

    def get_fallback_response(self) -> str:
        fallback_responses = [
            "I'm not sure how to respond to that.",
            "Let's talk about something else.",
            "I don't have anything to say about that."
        ]
        return random.choice(fallback_responses)


class StaticNPC(NPC):
    """NPC that doesn't move."""
    color: tuple = (0, 255, 0)

    def prepare(self):
        self.generate_personality_document()
        self.build_identity()


class RandomNPC(NPC):
    """NPC that moves randomly around a fixed point."""
    color: Tuple[int, int, int] = (0, 255, 255)
    home_x: int
    home_y: int
    movement_range: int = 2

    def prepare(self):
        self.generate_personality_document()
        self.build_identity()

    def update_position(self, maze, current_time: int):
        if not self.can_move(current_time):
            return

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
        self.build_identity()

    def update_position(self, maze, player_pos, current_time):
        if not self.can_move(current_time):
            return

        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        if self.in_line_of_sight(maze, player_pos):
            if player_pos[0] > self.x and not maze.is_wall(self.x + 1, self.y):
                self.x += 1
            elif player_pos[0] < self.x and not maze.is_wall(self.x - 1, self.y):
                self.x -= 1
            elif player_pos[1] > self.y and not maze.is_wall(self.x, self.y + 1):
                self.y += 1
            elif player_pos[1] < self.y and not maze.is_wall(self.x, self.y - 1):
                self.y -= 1
        else:
            direction = random.choice(directions)
            new_x = self.x + direction[0]
            new_y = self.y + direction[1]

            if not maze.is_wall(new_x, new_y):
                self.x, self.y = new_x, new_y

    def in_line_of_sight(self, maze, player_pos):
        """Check if the player is within {dist} squares and there are no walls in between."""
        dx = abs(player_pos[0] - self.x)
        dy = abs(player_pos[1] - self.y)

        if dx <= self.dist and dy == 0:
            x_step = 1 if player_pos[0] > self.x else -1
            for i in range(1, dx + 1):
                if maze.is_wall(self.x + i * x_step, self.y):
                    return False
            return True
        elif dy <= self.dist and dx == 0:
            y_step = 1 if player_pos[1] > self.y else -1
            for i in range(1, dy + 1):
                if maze.is_wall(self.x, self.y + i * y_step):
                    return False
            return True

        return False
