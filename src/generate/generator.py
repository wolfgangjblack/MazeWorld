"""Base Generator class and concrete generators for content generation.

Each generator encapsulates the Gen -> Check -> Validate chain for a
specific content type.  Generators read the WorldBible for lore context
so that generated content is narratively coherent.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from src.generate.checker import (
    BaseChecker, EventChecker, ItemChecker, NPCChecker, QuestChecker,
)
from src.generate.validator import (
    BaseValidator, EventValidator, ItemValidator, NPCValidator, QuestValidator, ValidationReport,
)

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


@dataclass
class GenerationResult:
    """Outcome of a full Gen -> Check -> Validate cycle."""
    content: object
    passed: bool
    used_fallback: bool = False
    attempts: int = 1
    issues: list[str] = field(default_factory=list)


class BaseGenerator(ABC):
    """Abstract generator with built-in Gen -> Check -> Validate chain.

    Subclasses implement:
    - ``_generate()``: produce raw content from LLM or static fallback
    - ``_fallback()``: return safe static content when retries are exhausted
    - ``checker``: a BaseChecker instance for structural checking
    - ``validator``: a BaseValidator instance for logic validation
    """

    checker: BaseChecker | None = None
    validator: BaseValidator | None = None
    max_retries: int = MAX_RETRIES

    @abstractmethod
    def _generate(self, context: dict, feedback: list[str] | None = None) -> object:
        """Produce raw content. *feedback* contains reasons from prior failures."""
        ...

    @abstractmethod
    def _fallback(self, context: dict) -> object:
        """Return safe fallback content when all retries are exhausted."""
        ...

    def generate(
        self,
        context: dict,
        report: ValidationReport | None = None,
        label: str = "content",
    ) -> GenerationResult:
        """Run the full Gen -> Check -> Validate chain with retries."""
        feedback: list[str] | None = None
        all_issues: list[str] = []

        for attempt in range(1, self.max_retries + 1):
            try:
                content = self._generate(context, feedback=feedback)
            except Exception as e:
                logger.warning("[%s] attempt %d generation error: %s", label, attempt, e)
                feedback = [str(e)]
                all_issues.append(str(e))
                if report:
                    report.add_major(
                        f"{label} generation error attempt {attempt}: {e}",
                        phase=label,
                    )
                continue

            # --- Check phase ---
            issues: list[str] = []
            if self.checker is not None:
                check_result = self.checker.check(content, context)
                if not check_result.passed:
                    issues.extend(check_result.issues)
                if check_result.data is not None:
                    content = check_result.data

            # --- Validate phase ---
            if self.validator is not None and not issues:
                val_result = self.validator.validate(content, context)
                if not val_result.passed:
                    issues.extend(val_result.reasons)
                if val_result.data is not None:
                    content = val_result.data

            if not issues:
                logger.info("[%s] passed on attempt %d.", label, attempt)
                return GenerationResult(
                    content=content, passed=True, attempts=attempt,
                )

            logger.warning("[%s] attempt %d issues: %s", label, attempt, issues)
            all_issues.extend(issues)
            feedback = issues
            if report:
                report.add_major(
                    f"{label} failed validation attempt {attempt}: {'; '.join(issues)}",
                    phase=label,
                )

        # Exhausted retries — use fallback
        logger.warning("[%s] exhausted %d retries, using fallback.", label, self.max_retries)
        fallback = self._fallback(context)
        if report:
            report.add_warning(
                f"{label} used fallback after {self.max_retries} retries",
                phase=label,
            )
        return GenerationResult(
            content=fallback, passed=True, used_fallback=True,
            attempts=self.max_retries, issues=all_issues,
        )


class EventGenerator(BaseGenerator):
    """Generates events (combat/puzzle/event) with check + validate."""

    def __init__(self):
        self.checker = EventChecker()
        self.validator = EventValidator()

    def _generate(self, context: dict, feedback: list[str] | None = None) -> dict:
        from src.generate.generators.llm_primitives import generate_event_primitive
        env_ctx = {"environment": {
            "type": context.get("env_type", "forest"),
            "name": context.get("env_name", "Unknown"),
        }}
        if feedback:
            env_ctx["retry_feedback"] = "; ".join(feedback)
        if context.get("bible_context"):
            env_ctx["bible_context"] = context["bible_context"]
        event_type = context.get("event_type", "combat")
        result = generate_event_primitive(env_ctx, event_type)
        if "error" in result:
            raise ValueError(result["error"])
        result.setdefault("type", event_type)
        return result

    def _fallback(self, context: dict) -> dict:
        import random
        event_type = context.get("event_type", "combat")
        if event_type == "combat":
            return {
                "name": random.choice(["Goblin", "Giant Rat", "Skeleton", "Slime", "Bandit"]),
                "description": "A hostile creature attacks!",
                "type": "combat",
                "difficulty": random.randint(2, 4),
                "damage_type": random.choice(["health", "hunger", "thirst"]),
                "damage_range": [5, 15],
            }
        return {
            "name": random.choice(["Locked Chest", "Crumbling Bridge", "Strange Rune", "Trapped Door"]),
            "description": "A mysterious obstacle blocks your path...",
            "type": event_type,
            "difficulty": random.randint(1, 3),
            "choices": [
                {"text": "Try to force through", "stat_check": "health", "dc": 12, "auto_success": False},
                {"text": "Walk away", "auto_success": True},
            ],
        }


class NPCGenerator(BaseGenerator):
    """Generates NPC personality + greeting with check + validate."""

    def __init__(self):
        self.checker = NPCChecker()
        self.validator = NPCValidator()

    def _generate(self, context: dict, feedback: list[str] | None = None) -> dict:
        from src.generate.generators.llm_primitives import (
            generate_personality_primitive, generate_npc_convo,
            generate_image_description,
        )
        env_type = context.get("env_type", "forest")
        env_name = context.get("env_name", "Unknown")
        npc_type = context.get("npc_type", "StaticNPC")

        personality = generate_personality_primitive({
            "environment": {"type": env_type, "name": env_name},
        })
        if "error" in personality:
            raise ValueError(personality["error"])

        greeting = generate_npc_convo(personality)
        portrait_prompt = generate_image_description(personality)

        return {
            "name": personality.get("name", "Unknown"),
            "type": npc_type,
            "job": personality.get("job", "peasant"),
            "personality": personality.get("personality", "stoic"),
            "hobby": personality.get("hobby", "walking"),
            "environment": env_type,
            "environment_name": env_name,
            "description": personality.get("description", ""),
            "opening_greeting": greeting,
            "portrait_prompt": portrait_prompt,
        }

    def _fallback(self, context: dict) -> dict:
        import random
        from src.data.world_data import NAMES, PERSONALITIES, JOBS, HOBBIES
        env_type = context.get("env_type", "city")
        return {
            "name": random.choice(NAMES),
            "type": context.get("npc_type", "StaticNPC"),
            "job": random.choice(JOBS.get(env_type, JOBS["city"])),
            "personality": random.choice(PERSONALITIES),
            "hobby": random.choice(HOBBIES.get(env_type, HOBBIES["city"])),
            "environment": env_type,
            "environment_name": context.get("env_name", "Unknown"),
            "description": "",
            "opening_greeting": "Greetings, traveler.",
            "portrait_prompt": "a fantasy character portrait, pixel art",
        }


class QuestGenerator(BaseGenerator):
    """Generates quests with check + validate."""

    def __init__(self):
        self.checker = QuestChecker()
        self.validator = QuestValidator()

    def _generate(self, context: dict, feedback: list[str] | None = None) -> dict:
        from src.generate.generators.llm_primitives import generate_quest_primitive
        env_ctx = {"environment": {
            "type": context.get("env_type", "forest"),
            "name": context.get("env_name", "Unknown"),
        }}
        if feedback:
            env_ctx["retry_feedback"] = "; ".join(feedback)
        quest_type = context.get("quest_type", "fetch")
        npcs = context.get("npcs", [])
        items = context.get("items", [])
        events = context.get("events", [])
        result = generate_quest_primitive(env_ctx, npcs, items, events, quest_type)
        if "error" in result:
            raise ValueError(result["error"])
        return result

    def _fallback(self, context: dict) -> dict:
        return {
            "title": f"A {context.get('quest_type', 'fetch')} quest",
            "description": "Complete this task for a reward.",
        }


class ItemGenerator(BaseGenerator):
    """Generates environment-themed items with check + validate."""

    def __init__(self):
        self.checker = ItemChecker()
        self.validator = ItemValidator()

    def _generate(self, context: dict, feedback: list[str] | None = None) -> dict:
        from src.generate.generators.llm_primitives import generate_item_primitive
        env_ctx = {"environment": {
            "type": context.get("env_type", "forest"),
            "name": context.get("env_name", "Unknown"),
        }}
        room_level = context.get("room_level", 1)
        result = generate_item_primitive(env_ctx, room_level)
        if "error" in result:
            raise ValueError(result["error"])
        return result

    def _fallback(self, context: dict) -> dict:
        return {
            "food": [{"name": "Bread", "nutrition_value": 15}],
            "drink": [{"name": "Water", "hydration_value": 15}],
            "tools": [{"name": "Hammer", "attribute": "bludgeon"}],
            "weapons": [{"name": "Dagger", "attack_dice": "1d4", "stat_modifier": "DEX"}],
            "spell_scrolls": [],
        }


class StoryGenerator(BaseGenerator):
    """Generates the overarching story."""

    def _generate(self, context: dict, feedback: list[str] | None = None) -> dict:
        from src.generate.generators.llm_primitives import generate_story_primitive
        story_seed = context.get("story_seed", "A dark force threatens the land.")
        room_count = context.get("room_count", 1)
        environments = context.get("environments", ["forest"])
        result = generate_story_primitive(story_seed, room_count, environments)
        if "error" in result:
            raise ValueError(result["error"])
        return result

    def _fallback(self, context: dict) -> dict:
        return {
            "title": "The Shadow's Grasp",
            "synopsis": "A dark cult spreads corruption through the land.",
            "faction": {
                "name": "The Shadow Cult",
                "description": "A secretive order seeking to plunge the world into darkness.",
                "leader": "The Faceless One",
            },
            "escalation_arc": ["Whispers of darkness", "The cult reveals itself"],
            "climax": "Face the cult leader in a final showdown.",
            "final_boss_name": "The Faceless One",
            "key_npc_names": ["The Faceless One"],
            "beats": [],
        }
