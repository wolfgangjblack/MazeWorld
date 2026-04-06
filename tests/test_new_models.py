"""Tests for new Pydantic data models added in Phase 1."""

from src.models.player import Stats, PlayerClass, Ability, Spell
from src.models.monster import Monster, LootDrop
from src.models.story import OverarchingStory, Faction, RoomStoryBeat
from src.models.world_bible import WorldBible, RoomBible, EntityRef
from src.models.save import SaveState
from src.models.time import DayNightCycle, TimePeriod
from src.models.combat import CombatState, CombatAction
from src.models.follower import Follower


# --- Stats ---

def test_stats_defaults():
    s = Stats()
    assert s.STR == 10
    assert s.LUCK == 10


def test_stats_modifier():
    s = Stats(STR=16, DEX=8, LUCK=10)
    assert s.modifier("STR") == 3    # (16-10)//2 = 3
    assert s.modifier("DEX") == -1   # (8-10)//2 = -1
    assert s.modifier("LUCK") == 0   # (10-10)//2 = 0


def test_stats_modifier_edge():
    s = Stats(INT=11)
    assert s.modifier("INT") == 0    # (11-10)//2 = 0


# --- PlayerClass ---

def test_player_class_creation():
    pc = PlayerClass(
        name="Ranger",
        archetype="warrior",
        flavor_text="A skilled woodsman.",
        environment="forest",
        stats=Stats(STR=16, DEX=14, CON=12, INT=8, WIS=10, CHA=10, LUCK=10),
        starting_weapon="longbow",
    )
    assert pc.name == "Ranger"
    assert pc.archetype == "warrior"
    assert pc.stats.STR == 16
    assert pc.starting_weapon == "longbow"


def test_player_class_with_abilities():
    ab = Ability(name="Bash", description="Smash a door.", stat="STR", cost_hunger=5)
    sp = Spell(name="Fireball", description="Fire!", element="fire",
               stat="INT", damage_dice=6, spell_type="damage_single", hunger_cost=10)
    pc = PlayerClass(
        name="Battlemage",
        archetype="mage",
        abilities=[ab],
        spells=[sp],
    )
    assert len(pc.abilities) == 1
    assert len(pc.spells) == 1
    assert pc.spells[0].element == "fire"


# --- Monster ---

def test_monster_creation():
    m = Monster(
        species="Dire Wolf",
        level=2, hp=15, max_hp=15, ac=12, str_mod=2, dex_mod=1,
        damage_dice=8, damage_type="physical",
    )
    assert m.species == "Dire Wolf"
    assert m.name == "Dire Wolf"  # auto-populated from species by model_post_init
    assert m.display_name == "Dire Wolf"
    assert m.level == 2
    assert m.loot_table == []
    assert len(m.id) == 36  # UUID format


def test_monster_named_boss():
    m = Monster(
        species="Dragon", name="Smaug",
        level=4, hp=30, max_hp=30, ac=16,
    )
    assert m.species == "Dragon"
    assert m.name == "Smaug"
    assert m.display_name == "Smaug"


def test_monster_with_loot():
    m = Monster(
        species="Goblin",
        loot_table=[LootDrop(item_id=201, probability=0.6)],
    )
    assert len(m.loot_table) == 1
    assert m.loot_table[0].probability == 0.6


# --- Story ---

def test_overarching_story():
    faction = Faction(name="Shadow Guild", description="Dark faction", threat_level=3)
    story = OverarchingStory(
        seed="defeat the shadow guild",
        title="Rise of Shadows",
        synopsis="A dark guild threatens the land.",
        faction=faction,
        beats=[RoomStoryBeat(room_id="room_1", summary="First encounter")],
    )
    assert story.faction.name == "Shadow Guild"
    assert len(story.beats) == 1


# --- WorldBible ---

def test_world_bible():
    wb = WorldBible()
    assert wb.rooms == {}
    assert wb.entity_index == {}

    wb.rooms["room_1"] = RoomBible(environment="forest", level=1, story_beat="intro")
    wb.entity_index["npc_100"] = EntityRef(entity_type="npc", room_id="room_1", entity_id="100")
    assert wb.rooms["room_1"].environment == "forest"
    assert wb.entity_index["npc_100"].entity_type == "npc"


# --- SaveState ---

def test_save_state_defaults():
    ss = SaveState()
    assert ss.seed == -1
    assert ss.room_id == "room_1"
    assert ss.version == 1


def test_save_state_with_data():
    ss = SaveState(
        seed=1234,
        room_id="room_3",
        player_data={"x": 5, "y": 10, "health": 80},
        quest_states={"q1": {"status": "active"}, "q2": {"status": "completed"}},
    )
    assert ss.seed == 1234
    assert len(ss.quest_states) == 2


# --- DayNightCycle ---

def test_day_night_defaults():
    dnc = DayNightCycle()
    assert dnc.current_period == TimePeriod.DAY
    assert dnc.ticks == 0


def test_day_night_advance():
    dnc = DayNightCycle(ticks_per_period=10)
    # Cycle order: DAY(0) -> DUSK(1) -> NIGHT(2) -> DAWN(3)
    # 10 ticks / 10 per period = index 1 = DUSK
    dnc.advance(10)
    assert dnc.current_period == TimePeriod.DUSK

    # 20 ticks / 10 per period = index 2 = NIGHT
    dnc.advance(10)
    assert dnc.current_period == TimePeriod.NIGHT

    # 30 ticks / 10 per period = index 3 = DAWN
    dnc.advance(10)
    assert dnc.current_period == TimePeriod.DAWN


def test_day_night_full_cycle():
    dnc = DayNightCycle(ticks_per_period=5)
    periods_seen = []
    for _ in range(20):
        dnc.advance(1)
        periods_seen.append(dnc.current_period)
    # Should cycle through all 4 periods
    assert TimePeriod.DAWN in periods_seen
    assert TimePeriod.DAY in periods_seen
    assert TimePeriod.DUSK in periods_seen
    assert TimePeriod.NIGHT in periods_seen


# --- CombatState ---

def test_combat_state_values():
    assert CombatState.ONGOING.value == "ongoing"
    assert CombatState.VICTORY.value == "victory"
    assert CombatState.DEFEAT.value == "defeat"
    assert CombatState.FLED.value == "fled"


# --- CombatAction enum ---

def test_combat_actions():
    assert CombatAction.ATTACK.value == "attack"
    assert CombatAction.FLEE.value == "flee"
    assert CombatAction.GAMBLE.value == "gamble"
    assert CombatAction.SWAP_WEAPON.value == "swap_weapon"


# --- Follower ---

def test_follower():
    f = Follower(npc_id=100, name="Arin", quest_id="q_001")
    assert f.npc_id == 100
    assert f.joined_in_room == 1
