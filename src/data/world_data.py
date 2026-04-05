"""Centralized environment data for MazeWorld.

Single source of truth for environment types, NPC names, personalities,
jobs, and hobbies. All modules that need environment-keyed lookups
should import from here.
"""

ENVIRONMENT_TYPES = ["forest", "cave", "dungeon", "castle", "house", "city"]

NAMES = [
    'Arin', 'Belinda', 'Corwin', 'Daphne', 'Eldon', 'Fiona',
    'Gareth', 'Helena', 'Isolde', 'Jareth', 'Kira', 'Lucan',
    'Maren', 'Nolan', 'Orin', 'Petra', 'Quinn', 'Roslyn',
    'Soren', 'Thalia', 'Ulric', 'Vera', 'Wren', 'Yara',
]

PERSONALITIES = [
    'cheerful', 'grumpy', 'mysterious', 'friendly',
    'suspicious', 'stoic', 'cunning', 'gentle',
    'boisterous', 'melancholic', 'sarcastic', 'earnest',
]

JOBS = {
    'forest': ['hunter', 'herbalist', 'ranger', 'woodcutter'],
    'cave': ['miner', 'spelunker', 'geologist', 'mushroom farmer'],
    'dungeon': ['jailer', 'torturer', 'dungeon keeper', 'escaped prisoner'],
    'castle': ['knight', 'scribe', 'steward', 'herald'],
    'house': ['cook', 'servant', 'caretaker', 'landlord'],
    'city': ['merchant', 'artist', 'guard', 'street performer'],
}

HOBBIES = {
    'forest': ['collecting herbs', 'bird watching', 'tracking animals', 'foraging'],
    'cave': ['mining rare ores', 'exploring caverns', 'studying geology', 'carving stone'],
    'dungeon': ['picking locks', 'mapping passages', 'collecting relics', 'eavesdropping'],
    'castle': ['jousting', 'calligraphy', 'falconry', 'chess'],
    'house': ['cooking', 'gardening', 'sewing', 'reading'],
    'city': ['trading goods', 'playing music', 'studying art', 'people watching'],
}
