import random
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field

from src.data.world_data import ENVIRONMENT_TYPES, HOBBIES, JOBS, NAMES, PERSONALITIES
from src.prompts import get_prompt_set


class NPC(BaseModel):
    """Base NPC class with behavior, image, and color."""

    x: int
    y: int
    id: int
    profile_image: Optional[str] = None
    portrait_prompt: Optional[str] = None
    name: Optional[str] = None
    job: Optional[str] = None
    hobby: Optional[str] = None
    personality: Optional[str] = None
    description: Optional[str] = None
    backstory: Optional[str] = None  # Full lore paragraph referencing Bible lore
    environment: Optional[str] = None
    environment_name: Optional[str] = None
    identity: Optional[str] = None
    opening_greeting: Optional[str] = None
    dialogue_tree: Optional[dict] = None
    dialogue_tree_incomplete: Optional[dict] = None
    dialogue_tree_complete: Optional[dict] = None
    dialogue_tree_failed: Optional[dict] = None
    quest_id: Optional[int] = None
    current_dc: int = 10
    zone: Optional[List[int]] = None
    selected: bool = True
    interaction_history: List[dict] = Field(default_factory=list)
    has_met_player: bool = False
    exhausted_dialogue: str = "I have nothing more to say."  # mid-conversation exhaustion (pipeline)
    finished_dialogue: str = "I have nothing more to say."  # post-quest completion (QuestManager)
    dialogue_exhausted: bool = False
    personality_notes: List[str] = Field(default_factory=list)
    max_dialogue_turns: int = 10
    availability: Optional[str] = None  # "day" | "night" | "always" | None
    color: Tuple[int, int, int] = (0, 255, 0)
    move_interval: int = 5000
    last_move_time: int = 0

    class Config:
        arbitrary_types_allowed = True

    def generate_personality_document(self, maze_environment: str | None = None):
        """Generate personality attributes for the NPC.

        Args:
            maze_environment: The environment of the maze this NPC belongs to.
                NPCs inherit their maze's environment rather than picking randomly.
        """
        if maze_environment:
            self.environment = maze_environment
        if not self.environment:
            # Last resort — should not happen in normal gameplay since NPCs
            # are always placed inside a maze with a known environment.
            self.environment = random.choice(ENVIRONMENT_TYPES)

        self.name = self.name or random.choice(NAMES)
        self.personality = self.personality or random.choice(PERSONALITIES)
        self.job = self.job or random.choice(JOBS[self.environment])
        self.hobby = self.hobby or random.choice(HOBBIES[self.environment])

    def build_identity(self):
        """Build the conversation identity using the prompt library."""
        if self.identity:
            return
        prompts = get_prompt_set()
        self.identity = prompts.conversation_identity(
            name=self.name,
            job=self.job,
            personality=self.personality,
            hobby=self.hobby,
            env=self.environment,
            env_name=self.environment_name or self.environment or "Unknown",
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
        banned_words = ["chibi", "loli", "shota", "nsfw"]
        for word in banned_words:
            if word in response.lower():
                return False
        return True

    def get_fallback_response(self) -> str:
        fallback_responses = [
            "I'm not sure how to respond to that.",
            "Let's talk about something else.",
            "I don't have anything to say about that.",
        ]
        return random.choice(fallback_responses)


class StaticNPC(NPC):
    """NPC that doesn't move."""

    color: tuple = (0, 255, 0)

    def prepare(self, maze_environment: str | None = None):
        self.generate_personality_document(maze_environment)
        self.build_identity()


class RandomNPC(NPC):
    """NPC that moves randomly around a fixed point."""

    color: Tuple[int, int, int] = (0, 255, 255)
    home_x: int = 0
    home_y: int = 0
    movement_range: int = 2

    def prepare(self, maze_environment: str | None = None):
        self.generate_personality_document(maze_environment)
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


class MerchantNPC(NPC):
    """NPC that sells items. Stays in place like a StaticNPC."""

    color: Tuple[int, int, int] = (255, 215, 0)  # gold
    shop_inventory: List[dict] = Field(default_factory=list)
    # Each entry: {"item_id": int, "price": int, "stock": int}

    def prepare(self, maze_environment: str | None = None):
        self.generate_personality_document(maze_environment)
        self.build_identity()

    def get_shop_items(self) -> list[dict]:
        """Return available shop items (stock > 0)."""
        return [entry for entry in self.shop_inventory if entry.get("stock", 0) > 0]

    def buy_from(self, item_index: int, player) -> str:
        """Player buys an item from this merchant. Returns message."""
        available = self.get_shop_items()
        if item_index < 0 or item_index >= len(available):
            return "Invalid selection."
        entry = available[item_index]
        price = entry["price"]
        if not player.spend_money(price):
            return "You don't have enough money."
        from src.registry import registry

        item_template = registry.get_item(entry["item_id"])
        if not item_template:
            player.add_money(price)  # refund
            return "Item not available."
        player.add_to_inventory(item_template.clone())
        entry["stock"] -= 1
        return f"Bought {item_template.name} for {price} gold."

    def sell_to(self, item_name: str, player) -> str:
        """Player sells an item to this merchant. Returns message."""
        if item_name not in player.inventory:
            return "You don't have that item."
        from src.models.items import EscortItem

        item = player.inventory[item_name]
        if isinstance(item, EscortItem):
            return "You can't sell that."
        sell_price = max(1, item.item_stats.price // 2)
        player.add_money(sell_price)
        player.remove_from_inventory(item_name)
        if player.equipped_weapon == item_name:
            player.equipped_weapon = None
        return f"Sold {item_name} for {sell_price} gold."


class AggressiveNPC(NPC):
    """NPC that moves randomly until the player is within 5 squares and in line of sight.
    After combat_defeated is set, reverts to random wandering."""

    color: Tuple[int, int, int] = (255, 0, 0)
    dist: int = 5
    combat_defeated: bool = False
    npc_monster: Optional[dict] = None

    def prepare(self, maze_environment: str | None = None):
        self.generate_personality_document(maze_environment)
        self.build_identity()

    def update_position(self, maze, player_pos, current_time):
        if not self.can_move(current_time):
            return

        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        if not self.combat_defeated and self.in_line_of_sight(maze, player_pos):
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
