import os
from src.utils.dataloader_utils import load_json_data, create_item_from_data


class GameRegistry:
    """Singleton registry for all game data -- items, NPCs, starter inventory,
    plus pre-generated events, quests, and manifest from world_gen.

    Loads once from JSON files and provides lookup methods so no other module
    needs to touch the raw data files directly.
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
        path = "data/manifest.json"
        if os.path.exists(path):
            self.manifest = load_json_data(path)

    def has_manifest(self) -> bool:
        return self.manifest is not None

    def manifest_matches_seed(self, seed: int) -> bool:
        if not self.manifest:
            return False
        return self.manifest.get("seed", self.manifest.get("world_seed")) == seed

    # -- items ---------------------------------------------------------------

    def _load_items(self):
        items_data = load_json_data('data/items/items.json')
        self.item_registry: dict = {}
        for item_id_str, item_info in items_data.items():
            item_id = int(item_id_str)
            self.item_registry[item_id] = create_item_from_data(item_id, item_info)

    def get_item(self, item_id: int):
        return self.item_registry.get(item_id)

    def get_item_name(self, item_id: int) -> str:
        item = self.item_registry.get(item_id)
        return item.name if item else ""

    def is_item(self, cell_value: int) -> bool:
        return cell_value in self.item_registry

    def item_ids(self) -> list:
        return list(self.item_registry.keys())

    def items_by_class(self, cls) -> dict:
        return {k: v for k, v in self.item_registry.items() if isinstance(v, cls)}

    # -- npcs ----------------------------------------------------------------

    def _load_npcs(self):
        self.npc_templates: list = load_json_data('data/npcs/npcs.json')

    def get_active_npcs(self) -> list[dict]:
        """Return only the NPC dicts that are selected (active) for this world."""
        return [n for n in self.npc_templates if n.get("selected", True)]

    # -- events --------------------------------------------------------------

    def _load_events(self):
        self.event_registry: dict = {}
        path = "data/events/events.json"
        if os.path.exists(path):
            from src.models.encounter import create_event_from_data
            events_data = load_json_data(path)
            for evt in events_data:
                event_obj = create_event_from_data(evt)
                self.event_registry[event_obj.id] = event_obj

    def get_event(self, event_id: str):
        return self.event_registry.get(event_id)

    # -- quests --------------------------------------------------------------

    def _load_quests(self):
        self.quest_registry: dict = {}
        path = "data/quests/quests.json"
        if os.path.exists(path):
            from src.models.quest import create_quest_from_data
            quests_data = load_json_data(path)
            for qd in quests_data:
                quest_obj = create_quest_from_data(qd)
                self.quest_registry[quest_obj.id] = quest_obj

    def get_quest(self, quest_id: str):
        return self.quest_registry.get(quest_id)

    # -- classes -------------------------------------------------------------

    def _load_classes(self):
        self.class_options: list = []
        path = "data/classes/classes.json"
        if os.path.exists(path):
            from src.models.player import PlayerClass
            classes_data = load_json_data(path)
            if isinstance(classes_data, list):
                for cd in classes_data:
                    try:
                        self.class_options.append(PlayerClass(**cd))
                    except Exception:
                        pass

    def get_class_options(self):
        return self.class_options

    # -- story ---------------------------------------------------------------

    def _load_story(self):
        self.story = None
        path = "data/story/story.json"
        if os.path.exists(path):
            from src.models.story import OverarchingStory
            story_data = load_json_data(path)
            if isinstance(story_data, dict):
                try:
                    self.story = OverarchingStory(**story_data)
                except Exception:
                    pass

    def get_story(self):
        return self.story

    # -- starter inventory ---------------------------------------------------

    def _load_starter_inventory(self):
        starter_data = load_json_data('data/player/starter_inventory.json')
        self.starter_inventory: dict = {}
        for item_name, data in starter_data.items():
            self.starter_inventory[item_name] = create_item_from_data(0, data)


registry = GameRegistry()
