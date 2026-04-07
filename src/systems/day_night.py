"""Day/night system — manages time advancement and period effects.

Time advances with movement, combat turns, and rest actions.
Night reduces fog of war visibility. Torch/lantern negates this.
Rest recovers HP with hunger/thirst caps.
Night encounters spawn randomly when the player moves at night.
"""

import random
from typing import Optional

from src.models.time import DayNightCycle, TimePeriod


# Rest duration options (in-game hours) and their effects
REST_OPTIONS = {
    3:  {"hp_recovery": 15, "hunger_cost": 5,  "thirst_cost": 5},
    6:  {"hp_recovery": 30, "hunger_cost": 10, "thirst_cost": 10},
    12: {"hp_recovery": 50, "hunger_cost": 10, "thirst_cost": 10},
}

# Combat rest (skip turn): small recovery
COMBAT_REST_HP = 5


def apply_rest(player, hours: int, cycle: DayNightCycle) -> str:
    """Apply rest effects and advance time.

    HP recovery scales with duration. Hunger/thirst costs are capped
    at 6hr level for 12hr rest (strategic trade-off: time vs resources).
    Returns a message describing the result.
    """
    if hours not in REST_OPTIONS:
        return "Invalid rest duration."

    effects = REST_OPTIONS[hours]
    hp_gain = effects["hp_recovery"]
    hunger_cost = effects["hunger_cost"]
    thirst_cost = effects["thirst_cost"]

    player.health = min(player.max_health, player.health + hp_gain)
    player.hunger = max(0, player.hunger - hunger_cost)
    player.thirst = max(0, player.thirst - thirst_cost)

    cycle.advance_hours(hours)

    period = cycle.current_period.value
    return (f"Rested {hours}h: +{hp_gain} HP, -{hunger_cost} hunger, "
            f"-{thirst_cost} thirst. It is now {period}.")


def apply_combat_rest(player) -> str:
    """In-combat rest: skip a turn for small HP recovery."""
    player.health = min(player.max_health, player.health + COMBAT_REST_HP)
    return f"You rest briefly and recover {COMBAT_REST_HP} HP."


def player_has_torch(player) -> bool:
    """Check if the player has an active torch/lantern in inventory."""
    for item in player.inventory.values():
        stats = getattr(item, 'item_stats', None)
        if stats and getattr(stats, 'attribute', None) == 'light':
            if stats.uses > 0:
                return True
    return False


def consume_torch_use(player) -> None:
    """Decrement one use from the player's torch/lantern."""
    for item in player.inventory.values():
        stats = getattr(item, 'item_stats', None)
        if stats and getattr(stats, 'attribute', None) == 'light':
            if stats.uses > 0:
                stats.uses -= 1
                return


def is_event_active_at_time(event, period: TimePeriod) -> bool:
    """Check if an event/encounter should trigger at the current time period.

    Events without time_gate are always active.
    Events with time_gate="day" only trigger during dawn/day.
    Events with time_gate="night" only trigger during dusk/night.
    """
    time_gate = getattr(event, 'time_gate', None)
    if not time_gate or time_gate == "always":
        return True
    if time_gate == "day":
        return period in (TimePeriod.DAWN, TimePeriod.DAY)
    if time_gate == "night":
        return period in (TimePeriod.DUSK, TimePeriod.NIGHT)
    return True


def is_npc_available(npc, period: TimePeriod) -> bool:
    """Check if an NPC is available at the current time period.

    NPCs without availability are always available.
    """
    availability = getattr(npc, 'availability', None)
    if not availability or availability == "always":
        return True
    if availability == "day":
        return period in (TimePeriod.DAWN, TimePeriod.DAY)
    if availability == "night":
        return period in (TimePeriod.DUSK, TimePeriod.NIGHT)
    return True


def get_night_overlay_alpha(period: TimePeriod, progress: float) -> int:
    """Return alpha value (0-255) for the night/dusk overlay.

    - Day/Dawn: 0 (no overlay)
    - Dusk: gradually increases (0 -> 80)
    - Night: 80 (dark blue tint)
    """
    if period == TimePeriod.DAY or period == TimePeriod.DAWN:
        return 0
    if period == TimePeriod.DUSK:
        return int(80 * progress)
    if period == TimePeriod.NIGHT:
        return 80
    return 0


def spawn_night_encounter(maze, player, cycle: DayNightCycle,
                          room_level: int = 1) -> Optional[object]:
    """Roll for a random night encounter when the player moves at night.

    Returns a CombatEvent if an encounter spawns, or None.
    Only triggers on open tiles (not event tiles, doors, etc.).
    """
    if not cycle.is_night:
        return None

    from config import NIGHT_ENCOUNTER_CHANCE
    if random.random() > NIGHT_ENCOUNTER_CHANCE:
        return None

    # Only spawn on walkable open tiles (value 0)
    if maze.grid[player.y][player.x] != 0:
        return None

    from src.models.monster import generate_night_encounter_monsters
    from src.models.encounter import CombatEvent
    import uuid

    env = getattr(maze, 'environment', 'dungeon')
    monsters = generate_night_encounter_monsters(env, room_level)

    return CombatEvent(
        id=f"night_{uuid.uuid4().hex[:8]}",
        name="Night Ambush",
        description="Creatures of the night emerge from the shadows!",
        monsters=monsters,
        room_level=room_level,
        time_gate="night",
        money_drop=[5 * room_level, 15 * room_level],
    )
