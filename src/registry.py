from src.utils.dataloader_utils import load_json_data, create_item_from_data


class GameRegistry:
    """Singleton registry for all game data -- items, NPCs, starter inventory.

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
        self._loaded = True

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

    # -- starter inventory ---------------------------------------------------

    def _load_starter_inventory(self):
        starter_data = load_json_data('data/player/starter_inventory.json')
        self.starter_inventory: dict = {}
        for item_name, data in starter_data.items():
            self.starter_inventory[item_name] = create_item_from_data(0, data)


registry = GameRegistry()
