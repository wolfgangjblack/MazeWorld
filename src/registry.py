import logging
import os
import warnings

from config import DATA_DIR
from src.utils.dataloader_utils import create_item_from_data, load_json_data

_log = logging.getLogger(__name__)


class GameRegistry:
    """Singleton registry for all game data -- items, NPCs, monsters, events,
    quests, classes, story, and manifest.

    All entity databases are loaded once from global JSON files at startup.
    Room-specific filtering is done by setup_game using maze.json position maps.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def load(self):
        if self._loaded:
            return
        self._load_items()
        self._load_npcs()
        self._load_monsters()
        self._load_starter_inventory()
        self._load_manifest()
        self._load_events()
        self._load_quests()
        self._load_classes()
        self._load_story()
        self._loaded = True

    def reload(self):
        """Force-reload all data (e.g. after world_gen runs)."""
        self._loaded = False
        self.load()

    # -- manifest ------------------------------------------------------------

    def _load_manifest(self):
        self.manifest = None
        path = os.path.join(DATA_DIR, "manifest.json")
        if os.path.exists(path):
            self.manifest = load_json_data(path)

    def has_manifest(self) -> bool:
        return self.manifest is not None

    def manifest_matches_seed(self, seed: int) -> bool:
        if not self.manifest:
            return False
        manifest_seed = self.manifest.get("seed")
        if manifest_seed is None:
            manifest_seed = self.manifest.get("world_seed")
            if manifest_seed is not None:
                warnings.warn(
                    "Manifest uses deprecated 'world_seed' key; regenerate to update to 'seed'.",
                    DeprecationWarning,
                    stacklevel=2,
                )
        return manifest_seed == seed

    # -- items ---------------------------------------------------------------

    def _load_items(self):
        self._load_items_from(os.path.join(DATA_DIR, "items", "items.json"))

    def _load_items_from(self, path: str):
        """Load items from a specific JSON file, merging into the existing registry."""
        if not os.path.exists(path):
            if not hasattr(self, "item_registry"):
                self.item_registry = {}
            return
        items_data = load_json_data(path)
        if not hasattr(self, "item_registry"):
            self.item_registry = {}
        for item_id_str, item_info in items_data.items():
            item_id = int(item_id_str)
            self.item_registry[item_id] = create_item_from_data(item_id, item_info)

    def get_item(self, item_id: int):
        return self.item_registry.get(item_id)

    def get_item_name(self, item_id: int) -> str:
        item = self.item_registry.get(item_id)
        return item.name if item else ""

    def get_item_by_name(self, name: str):
        """Look up an item by its display name. Returns the first match or None."""
        for item in self.item_registry.values():
            if item.name == name:
                return item
        return None

    def is_item(self, cell_value: int) -> bool:
        return cell_value in self.item_registry

    def item_ids(self) -> list:
        return list(self.item_registry.keys())

    def items_by_class(self, cls) -> dict:
        return {k: v for k, v in self.item_registry.items() if isinstance(v, cls)}

    # -- npcs ----------------------------------------------------------------

    def _load_npcs(self):
        path = os.path.join(DATA_DIR, "npcs", "npcs.json")
        if os.path.exists(path):
            self.npc_templates: list = load_json_data(path)
        else:
            self.npc_templates: list = []

    def get_active_npcs(self) -> list[dict]:
        """Return only the NPC dicts that are selected (active) for this world."""
        return [n for n in self.npc_templates if n.get("selected", True)]

    def get_npcs_by_ids(self, npc_ids: set[int]) -> list[dict]:
        """Return NPC templates whose id is in npc_ids."""
        return [n for n in self.npc_templates if n.get("id") in npc_ids]

    # -- monsters ------------------------------------------------------------

    def _load_monsters(self):
        self.monster_registry: dict[int, dict] = {}
        path = os.path.join(DATA_DIR, "monsters", "monsters.json")
        if os.path.exists(path):
            data = load_json_data(path)
            for k, v in data.items():
                self.monster_registry[int(k)] = v

    def get_monster_template(self, monster_id: int) -> dict | None:
        return self.monster_registry.get(monster_id)

    # -- events --------------------------------------------------------------

    def _load_events(self):
        self.event_registry: dict = {}
        path = os.path.join(DATA_DIR, "events", "events.json")
        if os.path.exists(path):
            from src.models.encounter import create_event_from_data

            events_data = load_json_data(path)
            for evt in events_data:
                event_obj = create_event_from_data(evt)
                self.event_registry[event_obj.id] = event_obj

    def get_event(self, event_id: int):
        return self.event_registry.get(event_id)

    def get_events_by_ids(self, event_ids: set[int]) -> dict:
        """Return event registry filtered to given IDs."""
        return {eid: evt for eid, evt in self.event_registry.items() if eid in event_ids}

    # -- quests --------------------------------------------------------------

    def _load_quests(self):
        self.quest_registry: dict = {}
        path = os.path.join(DATA_DIR, "quests", "quests.json")
        if os.path.exists(path):
            from src.models.quest import create_quest_from_data

            quests_data = load_json_data(path)
            for qd in quests_data:
                quest_obj = create_quest_from_data(qd)
                self.quest_registry[quest_obj.id] = quest_obj

    def get_quest(self, quest_id: int):
        return self.quest_registry.get(quest_id)

    def get_quests_by_ids(self, quest_ids: set[int]) -> dict:
        """Return quest registry filtered to given IDs."""
        return {qid: q for qid, q in self.quest_registry.items() if qid in quest_ids}

    # -- classes -------------------------------------------------------------

    def _load_classes(self):
        self.class_options: list = []
        path = os.path.join(DATA_DIR, "classes", "classes.json")
        if os.path.exists(path):
            from src.models.player import PlayerClass

            classes_data = load_json_data(path)
            if isinstance(classes_data, list):
                for cd in classes_data:
                    try:
                        self.class_options.append(PlayerClass(**cd))
                    except Exception as exc:
                        _log.warning("Failed to load class data: %s", exc)

    def get_class_options(self):
        return self.class_options

    # -- story ---------------------------------------------------------------

    def _load_story(self):
        self.story = None
        path = os.path.join(DATA_DIR, "story", "story.json")
        if os.path.exists(path):
            from src.models.story import OverarchingStory

            story_data = load_json_data(path)
            if isinstance(story_data, dict):
                try:
                    self.story = OverarchingStory(**story_data)
                except Exception as exc:
                    _log.warning("Failed to load story data: %s", exc)

    def get_story(self):
        return self.story

    # -- room loading --------------------------------------------------------

    def load_room(self, room_index: int):
        """Verify room directory exists. Entity data is loaded globally, not per-room."""
        room_dir = os.path.join(DATA_DIR, "rooms", f"room_{room_index}")
        if not os.path.isdir(room_dir):
            return False
        return True

    def get_room_dir(self, room_index: int) -> str:
        return os.path.join(DATA_DIR, "rooms", f"room_{room_index}")

    # -- starter inventory ---------------------------------------------------

    def _load_starter_inventory(self):
        path = os.path.join(DATA_DIR, "player", "starter_inventory.json")
        self.starter_inventory: dict = {}
        if not os.path.exists(path):
            return
        starter_data = load_json_data(path)
        for item_name, data in starter_data.items():
            self.starter_inventory[item_name] = create_item_from_data(0, data)


registry = GameRegistry()
