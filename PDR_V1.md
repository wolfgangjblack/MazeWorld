# MazeWorld V1.0 — Project Design Review

## 1. Overview

MazeWorld V1.0 is a procedurally generated 2D overhead RPG where players navigate interconnected maze environments, interact with LLM-driven NPCs, engage in turn-based combat, and complete quests. All game content — NPCs, items, events, quests, portraits, and music — is generated via GenAI pipelines at build time or runtime, depending on the selected mode (static, local LLM, or online API).

**Goal:** Evolve the current prototype (single maze, basic survival mechanics, simple dice-check combat) into a complete, playable game loop with class-based characters, real combat, multi-room exploration, proper UI screens, and a distributable executable.

**Core Pillars:**
- **Generative-first**: Primitives (portraits, maps, dialogue, classes, quests, events, monsters, music) are GenAI-produced, themed to the environment
- **Three-mode architecture**: Static (fully offline — dice rolls and multichoice dialogue), Local LLM (starting dialogue with conversational quests), Online API (starting dialogue, faster Claude-supported LLMs) — all share the same game systems
- **Complete game loop**: Start screen → class selection → explore → combat → quests → progression across rooms → end state

---

## 2. Current State

### What Exists & Works
- **Maze generation**: Recursive backtracking with variable hallway widths (40x25 cells, configurable)
- **Player movement**: Arrow-key navigation with hunger/thirst/health decay per step
- **Three NPC types**: Static (green, stationary), Random (cyan, wanders), Aggressive (red, chases)
- **NPC dialogue**: All three modes functional — pre-baked dialogue trees, local Llama 3.2-3B, Claude API
- **LLM personality generation**: Name, job, personality, hobbies, opening greeting generated at build time
- **Image generation**: NPC portraits via local Diffusers (FLUX.1-schnell / SDXL Turbo) or fal.ai API
- **Items**: 12 items across Food (4), Drink (4), Tool (4) with stat effects
- **Events**: Combat (DC dice roll, damage on fail) and Puzzle (multi-choice with tool/stat modifiers)
- **Quests**: 5 types (fetch, escort, delivery, dialogue-gated, combat) with validation
- **Inventory**: Pick up, swap, use, give items to NPCs
- **World gen pipeline**: 12-phase `world_gen.py` orchestrator writes all content to `data/`
- **Registry**: Singleton pattern for centralized data loading
- **Tests**: 12 unit test files, CI runs lint + pytest on Python 3.11/3.12

### What's Broken or Incomplete
- **No player classes** — no class system, stats, or character creation
- **No real combat** — events are single dice rolls, no turns, no weapons, no magic
- **No monsters** — combat events are abstract, not creature-based
- **Single maze only** — no portals, no multi-room progression
- **No start/load/save screens** — game launches directly into gameplay
- **No music or sound**
- **Survival is too punishing** — hunger/thirst drain too fast, too easy to die
- **Items are hardcoded** — 12 static items; not environment-themed, not randomly generated. V1 wants items (food, drink, tools, weapons, spells) generated per environment (e.g., forest -> bread/saw, rice-field -> riceballs, desert -> rope/pickaxe)
- **NPC environment bug** — NPCs get random environments instead of inheriting from their maze
- **No fog of war or day/night**
- **No exe packaging** — PyInstaller is a dependency but not wired up
- **No agentic validation** — generated content isn't checked against requirements

---

## 3. Scope

### In Scope (V1.0)

| Area | What's Included |
|---|---|
| **Player Classes** | 4 GenAI-generated classes per environment (warrior, mage, healer, joker/jester); class selection at game start; class-specific stats, weapons, spells/abilities |
| **Combat — Melee** | Turn-based; initiative (1d20+dex); attack rolls vs AC; weapon damage dice + modifier; per-class weapons |
| **Combat — Magic** | 5 elements (fire, water, forest, light, dark) with rock-paper-scissors relationships; healing, buff, and damage spells; mage/healer each pick 1 element + 2 spells; jester gets random assignment |
| **Encounters (overhaul)** | 4 types: combat (monsters), puzzle (tool-based), event (tool/ability/dice check + multiple choice), quest (NPC-driven) |
| **Monsters** | Environment-themed enemies generated per maze; used in combat encounters and combat quests |
| **Multi-Room Exploration** | Multiple interconnected mazes; doors unlock via quest/puzzle/event completion; configurable max rooms; overarching story across rooms |
| **Items (expanded)** | GenAI-generated per environment — food, drink, tools, weapons, spells; environment-themed; events/quests reward items |
| **Followers** | NPCs can join party as non-combatants; player can talk to followers to understand their quest; followers travel with player across maps |
| **Connected Quests** | Quest chains spanning multiple maps — escort follower to another map, slay a specific monster (completable out of order), fetch specific items; quest state persists across rooms |
| **Overarching Story** | Fully GenAI-generated narrative thread across all maps (e.g., faction to defeat across N maps); configurable 1-liner story seed in config; quests, dialogue, and NPC knowledge tie back to this theme |
| **Screens & UX** | Start screen (new game, load, tutorial, story); class selection screen; player menu (inventory, stats, spells, abilities); stat screen (buffs, progress, combat numbers, followers, title); quick story screen; save/load |
| **Save / Load / New Game** | Full game state serialization and restore |
| **Survival Rebalance** | Reduce hunger/thirst drain; events/quests can reward or damage survival stats; challenging but not a grind |
| **Fog of War** | Unexplored areas hidden; revealed as player moves |
| **Day/Night Cycle** | Time-of-day affects events, quests, NPC availability, and encounters |
| **Music Generation** | DEFERRED — requires research spike; game ships playable without music; interface built for future plug-in |
| **Generation Validation** | Agentic flow that compares generated content against requirements before accepting |
| **Config** | Player-settable: seed, number of maps, map size, event percent, map colors, story seed |
| **Packaging** | Distributable exe via PyInstaller; labeled by seed |

### Out of Scope (Post-V1)
- Combatant party members / follower combat AI
- Multiplayer
- Procedural narrative beyond the overarching story + connected quests
- Advanced NPC AI beyond the 3 behavior types
- Mobile / web ports
- Mac MPS optimization for local generation
- Build size optimization for local mode model weights
- World gen GUI
- Music generation (research item — interface built, implementation deferred)

---

## 4. Feature Specs

### 4.1 Player Classes

**Overview**: At game start, the LLM generates 4 class options themed to the starting environment. The player selects one (or picks jester blind) and begins with that class's stats, weapon, and abilities.

**Class Archetypes:**

| Archetype | Role | Weapon | Magic | Special |
|---|---|---|---|---|
| Warrior | Frontline melee | Primary weapon (sword, axe, etc.) + optional shield | None | Utility abilities (e.g., break door, intimidate) |
| Mage | Ranged magic damage | Simple weapon (staff, wand) | 1 element, 4 spells (2 damage, 2 utility) | Utility spells useful for quests/puzzles |
| Healer | Support / sustain | Simple weapon (staff, mace) | 1 element, 4 spells (1 healing, 1 buff, 1 damage, 1 utility) | Utility spells useful for quests/puzzles |
| Joker/Jester | Wildcard | Random weapon | Random (may get 0-3 spells/abilities from other classes) | Gamble ability: random effect each turn if used; spells/abilities from other classes are randomly assigned |

**Stats (per class):**

| Stat | Use |
|---|---|
| STR | Melee attack modifier, carry capacity |
| DEX | Initiative, AC bonus, ranged modifier |
| CON | Max HP, survival drain resistance |
| INT | Magic attack modifier, puzzle bonuses |
| WIS | Healing modifier, event perception |
| CHA | Dialogue checks, NPC disposition |
| LUCK | Jester's Gamble ability; the higher the luck, the better the chance of a good effect |

**Stat Guardrails (LLM-generated within ranges):**

| Archetype | Primary (14-18) | Secondary (11-14) | Dump (6-10) |
|---|---|---|---|
| Warrior | STR, CON | DEX, CHA | INT, WIS |
| Mage | INT | WIS, DEX | STR, CON, CHA |
| Healer | WIS | CHA, CON | STR, DEX, INT |
| Jester | LUCK | STR, DEX, CON, INT, WIS, CHA (all secondary) | 1 random dump stat |

Total point budget: 72 points across 7 stats so no class is strictly better.

**Level-Up (room progression):**
- When player enters a new room (level up), they select 1 new ability/spell from their class's starting pool
- Generation pipeline produces more abilities than the player starts with (e.g., generate 6-8 per class, player starts with 2-4, picks 1 per level)
- Warrior picks from utility abilities (break door, intimidate, bash, rally)
- Mage/Healer pick a new spell from their element
- Jester is randomly assigned from other class pools
- Jester modifier rule: for any ability borrowed from another class, Jester uses `avg(LUCK modifier, normal stat modifier)` instead of just the normal stat modifier

**Generation Flow:**
1. `world_gen` passes environment type + story seed to LLM
2. LLM returns 4 classes with: name, flavor text, stat array, starting weapon, spells/abilities list, portrait prompt
3. Image gen produces a portrait per class
4. Jester is generated but displayed as a black silhouette with "???" until selected

**Environment Theming Examples:**
- Forest -> Ranger (warrior), Druid (mage), Shaman (healer), Trickster (jester)
- City -> Knight (warrior), Court Wizard (mage), Priest (healer), Fool (jester)
- Desert -> Berserker (warrior), Sand Mage (mage), Sun Cleric (healer), Mirage (jester)

**Design Principle — Solvable by Construction:**
- Generation validation must ensure every quest/event has at least one path to completion using items and abilities that exist in the world
- Does NOT guarantee the player will have the right resources at the right time — player choices (class selection, ability picks, item usage) create real consequences
- Tools/items are consumable or limited-use, so spending them elsewhere can block a quest
- Wrong ability picks at level-up can make certain quests harder (but not impossible — dice rolls still allow low-odds completion)

---

### 4.2 Combat

**Overview**: Turn-based combat triggered by encounter tiles or quest objectives. Players fight environment-themed monsters using melee weapons and/or magic. Combat should feel meaningful and dice-driven, not grindy.

**Initiative:**
- Both sides roll 1d20 + DEX modifier
- Highest goes first; ties favor the player

**Turn Structure:**
1. Active character selects action: Attack, Multi-Attack, Cast Spell, Use Item, Flee, Rest
2. Resolve action
3. Turn passes to next character

**Turn Actions:**

| Action | Target | Cost | Notes |
|---|---|---|---|
| Attack | Single target melee | Free | Basic attack, always available |
| Multi-Attack | 2+ targets | Hunger | Warrior ability (cleave, whirlwind) |
| Cast Spell | Single or multi-target | Hunger and/or thirst | Element-based, type varies |
| Use Item | Self | Free | Consume food/drink/tool mid-combat |
| Flee | N/A | N/A | 1d20 + DEX vs DC 12 + monster level |
| Rest | Self | 1 turn (skip action) | Small HP/hunger/thirst recovery |

**Melee Attack:**
- Roll: 1d20 + weapon stat modifier + level modifier
- Target DC: 10 + target armor + target DEX modifier
- Hit -> roll weapon damage dice + weapon stat modifier
- Miss -> turn ends

**Magic Attack:**
- Roll: 1d20 + INT modifier (mage) or WIS modifier (healer) + level modifier
- Target DC: 10 + target magic resistance (if any)
- Hit -> roll spell damage/effect
- Elemental advantage: super effective (fire>forest>water>fire, light<>dark) = 1.5x damage
- Elemental disadvantage: resisted = 0.5x damage

**Healing/Buff Spells (no roll needed):**
- Healing spells restore **HP only**
- Buff spells: temporary stat boost for N turns (e.g., +2 AC, +2 STR)
- Buff spells can include thirst/hunger recovery as an option (e.g., "Nourish" buff restores hunger over N turns)

**Spell Cost (hunger/thirst based):**
- Each spell consumes hunger and/or thirst on cast
- Higher potency spells cost more
- Ties magic directly into the survival system — eat/drink to keep casting

| Spell Type | Costs | Effect |
|---|---|---|
| Damage (single) | 5 hunger | Deal damage to 1 target |
| Damage (multi) | 10 hunger | Deal damage to all targets |
| Healing | 8 thirst | Restore HP to self |
| Buff (stat) | 5 thirst | +2 to a stat for N turns |
| Buff (sustain) | 5 hunger | Restore thirst/hunger over time |
| Warrior multi-hit | 8 hunger | Hit 2+ targets |
| Warrior utility | 5 hunger | Break, intimidate, etc. |

(Numbers are illustrative — tuned during playtesting.)

**Jester's Gamble (combat action):**
- Roll on a random effect table; LUCK modifier influences the outcome distribution
- Possible effects: damage enemy, heal self, buff self, damage self, debuff enemy, nothing happens, wild magic (random spell from any element)

**Flee:**
- Roll 1d20 + DEX modifier vs DC 12 + monster level
- Success -> exit combat, monster remains on tile
- Fail -> monster gets a free attack, combat continues

**Weapons:**

| Type | Stat | Example Dice | Notes |
|---|---|---|---|
| Heavy (sword, axe, hammer) | STR | 1d8, 1d10 | Warrior primary |
| Light (dagger, short sword) | DEX | 1d4, 1d6 | Fast, lower damage |
| Simple (staff, mace) | STR or INT | 1d4, 1d6 | Mage/Healer weapons, can channel spells |
| Random (jester) | varies | varies | Assigned at generation |

**Monster Stats:**
- Status effects (poison, stun, elemental) are **battle-scoped only** — do not carry over to other battles

**Encounter Composition:**
- Solo: 1 monster (can be weak or strong; mini-bosses only show up to block the door to the next room)
- Pack: 2-4 weaker monsters of same type
- Mixed: 1-2 strong + 2-3 weak (e.g., alpha wolf + wolf pack)
- Composition generated per encounter, scaled to room level
- Turn order: all combatants (player + all monsters) roll initiative, act in order

**Monster Loot:**
- Monsters can drop items on death — food, drink, tools, money, or environment-themed gear
- Drop table generated per monster type at build time
- Not guaranteed — probability-based (e.g., 40-60% chance to drop something)

**Death:**
- Player HP hits 0 -> game over screen with option to load save or quit
- No respawn mechanic in V1

---

### 4.3 Encounters

**Overview**: Encounters are **invisible** — triggered when a player steps on a hidden marker tile. On trigger, an encounter screen appears with an image and dialogue/options. Once resolved, the tile is cleared permanently (no respawn).

**Encounter Types:**

#### Combat Encounter
- Player enters combat with 1-N environment-themed monsters
- Uses the full combat system from 4.2
- Monsters and composition scaled to room level
- On victory: encounter cleared, loot drop possible but not guaranteed
- On flee: tile remains active, monsters retain damage taken

#### Puzzle Encounter
- Requires a specific tool, ability, or spell to solve
- Presented as: encounter image + description + prompt
- Player selects tool/ability from inventory to attempt
- Correct tool/ability -> solved, reward given
- Wrong tool -> "This doesn't seem right..." warning, tool consumed, puzzle remains
- No suitable tool/ability -> player can leave and return later
- Multiple valid solutions possible (e.g., pickaxe OR earth spell OR STR ability)
- **Solvability rule**: at least one solution must be achievable with tools/abilities available in the world and selectable by the player

#### Event Encounter
- Multi-choice scenario with dice checks
- Each option may require: a tool, a utility ability/spell, or a stat check
- Roll: 1d20 + relevant stat modifier (+ tool/ability bonus if applicable)
- Pass DC -> success, reward
- Fail DC -> consequence (HP/hunger/thirst damage, item loss, etc.)
- Walk away is always available, no penalty, event remains active for later
- Some events are **time-gated** — only available during certain times of day (day/night system)

#### Quest Encounter
- **Not tile-triggered** — initiated by talking to an NPC
- NPC dialogue introduces the quest, provides objectives
- Quest types detailed in 4.7 (Connected Quests)

**Encounter Generation:**
- Generated at build time per room by `world_gen`
- Type distribution configurable (e.g., 40% combat, 20% puzzle, 20% event, 20% quest)
- Must pass solvability validation
- Difficulty scales with room level

**Encounter Tiles:**
- Invisible to the player (no visual indicator on the map)
- Fog of war hides the surrounding area; once explored, map/paths/NPCs are revealed but encounter tiles remain hidden
- Density configurable via `config.py`
- Placed on open maze cells, not on walls or NPC spawn points

**On Trigger:**
1. Game pauses movement
2. Encounter image displayed (generated at build time)
3. Encounter type determines UI: combat screen, puzzle prompt, event choices
4. On resolution: reward/consequence applied, tile cleared (except flee from combat)

**Time of Day:**
- Player should have a visible time-of-day indicator (HUD or status screen)
- Some events only trigger during day or night
- Time-gated encounters remain hidden until correct time — player walks over them with no effect

---

### 4.4 Monsters

**Overview**: Monsters are environment-themed enemies generated at build time. They appear in combat encounters and combat quests. Each monster has stats, a portrait, and an optional loot table.

**Monster Stats:**

| Stat | Description |
|---|---|
| Name | GenAI-generated, environment-themed |
| HP | Scales with room level |
| AC | 10 + armor + DEX modifier |
| STR/DEX | Determines attack modifier and initiative |
| Attack | Weapon/natural attack with damage dice |
| Damage Type | Physical, or elemental (fire, water, forest, light, dark) |
| Elemental Affinity | Optional — determines weakness/resistance |
| Level | Matches room level |
| Abilities | Optional — poison, stun, elemental attack (battle-scoped only) |
| Loot Table | List of possible drops with probability |
| Portrait Prompt | Used for image generation |

**Environment Theming Examples:**

| Environment | Monsters |
|---|---|
| Forest | Wolves, treants, giant spiders, bandits |
| Desert | Scorpions, sand wurms, dust elementals, raiders |
| City | Thugs, rats, sewer creatures, corrupt guards |
| Cave | Bats, slimes, rock golems, cave trolls |
| Castle | Undead knights, gargoyles, cursed servants |

**Encounter Composition:**
- Solo: 1 monster — can sometimes be weak, sometimes be strong. Mini-bosses only show up to block the door to the next room.
- Pack: 2-4 weaker monsters of same type
- Mixed: 1-2 strong + 2-3 weak (e.g., alpha wolf + wolf pack)
- Composition generated per encounter, scaled to room level

**Level Scaling:**

| Room Level | Monster HP Range | Monster AC Range | Damage Dice |
|---|---|---|---|
| 1 | 8-12 | 10-12 | 1d4 - 1d6 |
| 2 | 12-20 | 11-13 | 1d6 - 1d8 |
| 3 | 18-25 | 12-15 | 1d6 - 1d10 |
| 4+ | 25-30 | 13-16 | 1d8 - 1d12 |

Numbers are illustrative — tuned during playtesting.

**Room Gate Boss:**
- Each room has a guaranteed boss encounter blocking the door to the next room, tied to the overarching story
- Gate encounter options: strong boss monster OR multi-step encounter
- Failing the multi-step encounter still lets the player through but with heavy survival penalties (HP/hunger/thirst damage)

**Elemental Multipliers:**
- Super effective (magic vs weak type) = 1.5x damage
- Resisted (magic vs strong type) = 0.5x damage
- Fire > Forest > Water > Fire; Light <> Dark

**Quest Monsters:**
- "Kill X" quests point to a specific combat encounter tile (can be time-gated)
- Not a generic "kill any wolf" — it's a placed, named encounter
- If player already cleared that encounter before getting the quest, NPC recognizes it and completes the quest immediately

**Overarching Story Monsters:**
- The story seed generates a faction/threat (e.g., "seed gang")
- Each room has faction-related monsters alongside generic environment monsters
- Boss encounters (quest-driven) feature named faction members with unique stats and portraits

**Generation Flow:**
1. `world_gen` passes environment type + room level + story seed to LLM
2. LLM generates a monster pool per room (e.g., 5-8 monster types)
3. Each combat encounter tile draws from that pool to compose its group
4. Image gen produces a portrait per unique monster type
5. Validation: monster stats checked against level scaling guardrails

---

### 4.5 Multi-Room Exploration & Portals

**Overview**: The game world consists of multiple interconnected maze rooms, each with its own environment, NPCs, items, encounters, and monsters. Players progress by clearing the gate encounter to unlock the door to the next room. The number of rooms is configurable and tied to the overarching story.

**Room Structure:**
- Each room is a fully generated maze (size configurable, same as current system)
- Each room has its own environment type (forest, desert, cave, city, castle, etc.)
- Environment type is GenAI-selected to fit the overarching story
- Room level = room number (room 1 = level 1, room 2 = level 2, etc.)

**Room Contents (generated per room):**
- Maze layout
- NPCs (themed to environment)
- Items (themed to environment)
- Encounter tiles (combat, puzzle, event — scaled to room level)
- Monsters (pool generated per environment + level)
- 1 gate boss / multi-step gate encounter blocking the exit
- Quest NPCs with room-local and cross-room quests
- Story-related faction presence (escalates per room)

**No Backtracking:**
- Progression is one-way only. Once you enter a new room, previous rooms are gone.
- Cross-room quests must be designed so the required action is always in the current room or the next room (max 1 room ahead)
- Follower escort quests go forward only

**Door Discovery:**
- Exit doors are **hidden by default**
- Doors reveal when either:
  - Player has cleared 40% of encounters in the room, OR
  - An NPC quest reveals the door location
- Once revealed, the door is visible on the map but still blocked by the gate encounter
- Door reveal threshold (40%) is configurable in `config.py`

**Room Transition:**
1. Player clears gate encounter (or fails multi-step with heavy penalty)
2. Transition screen: GenAI-generated portrait of the new environment
3. Dialogue box overlays the portrait with the story of the new room (what's happening here, faction presence, hints)
4. Player enters the new room

**New Game Start:**
- Same flow — starting environment portrait + story intro dialogue before gameplay begins

**Story Quest Warning:**
- On entering next room after skipping story content: dialogue prompt — "You feel some things were left undone. Continue anyway?"
- Soft warning, not a blocker — player can always move forward

**Overarching Story Progression:**
- Room 1: Introduction — player learns about the threat, early faction presence
- Rooms 2 to N-1: Escalation — faction grows stronger, quests reveal more story, connected quests span rooms
- Room N: Climax — final boss encounter, story resolution

**Endgame:**
- Final boss defeated -> ending screen
- Stats summary: quests completed/failed, monsters killed, items used, rooms cleared, time played, class, level
- Option to start new game

**Day/Night Across Rooms:**
- Time persists across rooms — entering a new room doesn't reset the clock
- Time advances with player actions (movement, rest, combat turns)

**No Room Transition Restoration:**
- Entering a new room gives nothing — player must manage resources to arrive in good shape

**Generation Flow:**
1. `world_gen` generates overarching story from story seed + room count
2. For each room: LLM selects environment type that fits the story arc
3. Each room is generated independently but with shared story context (faction names, key NPCs, quest chains)
4. Gate encounters generated with story-relevant bosses
5. Cross-room quests validated for completability
6. Each room gets a portrait prompt -> image gen produces environment portrait
7. Each room gets a story text blurb for the transition dialogue

---

### 4.6 Items (Expanded)

**Overview**: All items are GenAI-generated per environment at build time. Items are themed to the room's environment and cover five categories: food, drink, tools, weapons, and spell scrolls. Items exist as pickups in the maze, quest/event rewards, and monster loot drops.

**Item Categories:**

#### Food
- Restores hunger
- Some restore small HP
- Environment-themed (forest -> bread, berries; desert -> dried meat, dates; rice-field -> riceballs; city -> stew, pastries)

#### Drink
- Restores thirst
- Some restore small HP
- Environment-themed (forest -> spring water, herbal tea; desert -> cactus juice; city -> ale, coffee; cave -> mushroom broth)

#### Tools
- Used to solve puzzles and events
- Have limited uses (e.g., 3 uses)
- Each tool has an attribute (cutting, climbing, digging, bludgeon, etc.)
- Environment-themed (forest -> saw, rope; desert -> pickaxe, rope; cave -> torch, pickaxe; city -> lockpick, crowbar)
- Consumed on wrong puzzle attempt

#### Weapons
- Used in combat, determines attack dice and stat modifier
- Weapon types: heavy (STR), light (DEX), simple (STR or INT)
- Environment-themed (forest -> hunting bow, woodcutter's axe; desert -> scimitar, spear; city -> short sword, dagger; castle -> longsword, mace)
- Player starts with class weapon; can find/swap better weapons in later rooms

#### Spell Scrolls
- **Consumable items**, like tools
- Used to solve events, quests, and puzzles (e.g., fire scroll to burn through a barrier)
- **Jester exception**: Jesters can learn from spell scrolls instead of consuming them, adding the spell to their spell list permanently
- All other classes consume scrolls on use

**Currency & Shops:**
- **Money** is a new resource (not an inventory item — tracked as a counter)
- Sources: monster drops, event/quest rewards, selling items to shops
- **NPC shops**: Some NPCs are merchants with a buy/sell interface
  - Shops stock environment-themed items (food, drink, tools, weapons, scrolls)
  - Prices scale with room level
  - Player can sell unwanted items for money
- Shop NPCs generated at build time with inventory and price lists

**Inventory:**
- **No size limit** — player can carry as many items as they want
- All items stack by type
- Multiple weapons can be carried; player can swap equipped weapon anytime (including mid-combat)

**Item Stats (generated per item):**

| Field | Description |
|---|---|
| Name | GenAI-generated, environment-themed |
| Category | food, drink, tool, weapon, spell_scroll |
| Effect | Stat restoration, damage dice, attribute, spell effect |
| Uses | Limited for tools; single-use for food/drink/scrolls; durable for weapons |
| Description | Flavor text for inventory display |
| Portrait Prompt | Used for image generation |

**Item Categories Summary:**

| Category | Stackable | Consumable | Notes |
|---|---|---|---|
| Food | Yes | Yes | Restores hunger, sometimes HP |
| Drink | Yes | Yes | Restores thirst, sometimes HP |
| Tool | Yes | Yes (limited uses) | Puzzle/event solving, consumed on wrong attempt |
| Weapon | Yes | No (durable) | Equip one, carry many, swap anytime |
| Spell Scroll | Yes | Yes (single use) | Solve events/puzzles; Jester can learn instead |
| Money | N/A (counter) | N/A | Used at NPC shops |

**Item Generation Flow:**
1. `world_gen` passes environment type + room level to LLM
2. LLM generates an item pool per room (e.g., 4 food, 4 drink, 3 tools, 2-3 weapons, 1-2 spell scrolls)
3. Items placed in maze, assigned to monster loot tables, and set as quest/event rewards
4. Image gen produces portrait per unique item type
5. Validation: puzzles/events reference tools that exist in the item pool; weapons scale with room level

**Item Scaling:**
- Higher-level rooms produce better items (more restoration, higher damage dice, rarer tools)
- Weapon damage scales with room level (room 1: 1d4-1d6 weapons, room 4: 1d8-1d12)
- Food/drink restoration scales similarly

---

### 4.7 Connected Quests & Overarching Story

**Overview**: Quests are NPC-driven tasks that range from simple room-local fetch quests to multi-room chains tied to the overarching story. The story itself is fully GenAI-generated from a configurable story seed and spans all rooms.

**Overarching Story:**
- Generated at build time from the story seed (1-liner in config, e.g., "A cult of fire mages is corrupting the land")
- LLM generates: faction name, faction leader, faction presence per room, escalation arc, climax
- All rooms, NPCs, quests, and gate bosses reference the story
- NPC dialogue is flavored by story context — even non-quest NPCs may gossip about the faction, warn the player, or share rumors
- Final room contains the story climax and final boss

**Story Generation Flow:**
1. `world_gen` passes story seed + room count + environment list to LLM
2. LLM returns: faction details, per-room story beats, key NPC names, final boss identity
3. Per-room generation uses story beat as context for quest/NPC/encounter generation
4. Validation: story references (named NPCs, faction members) are cross-checked against generated content

**Quest Types:**

#### Fetch Quest
- NPC asks player to find and return a specific item
- Item exists somewhere in the current room (or in a shop)
- Reward: money, item, story info, or door reveal

#### Kill Quest
- NPC asks player to defeat a specific named monster
- Points to a specific combat encounter tile in the current room
- Can be time-gated (day/night)
- If player already cleared that encounter before getting the quest, NPC recognizes it and completes the quest immediately
- Reward: money, item, story info

#### Escort Quest (Follower)
- NPC joins the player as a non-combatant follower
- Player must guide them to a specific location in the current room or the next room (max 1 room ahead)
- Follower is managed via the player menu (not visible on the map)
- Player can talk to follower to learn more about their quest and get hints
- Follower is immune to combat AOE — they're abstracted, not physically present
- On arrival: follower leaves party, quest complete
- Quest can only fail if the player moves forward in the dungeon to a new room past the drop-off point
- Reward: money, item, story info, or door reveal

#### Delivery Quest
- NPC gives player an item to deliver to another NPC
- Target NPC can be in the current room or the next room (max 1 room ahead)
- Item occupies inventory space until delivered
- Reward: money, item, story info

#### Dialogue Quest
- NPC requires the player to pass a dialogue check (CHA-based DC)
- Offline static mode: multiple-choice with a correct answer
- Local/online mode: free-text, LLM evaluates response quality
- Can fail and retry (costs time, advances day/night)
- Reward: story info, door reveal, NPC becomes shop or follower

#### Multi-Step Quest
- Chain of 2-3 sub-quests that must be completed in sequence
- Example: "Talk to the informant (dialogue) -> Find the hideout key (fetch) -> Clear the hideout (kill)"
- Sub-quests can span rooms — e.g., step 1 in room 2, steps 2-3 in room 3 (max 1 room ahead)
- Quest log tracks current step
- Tied to overarching story — these are the main story quests

**Connected Quest Rules:**
- Cross-room quests always point **forward** (never to a previous room, since no backtracking) and **max 1 room ahead**
- If a quest references the next room, the quest stays active in the quest log until the player reaches that room
- Kill quests can be completed out of order — if the encounter is cleared before the quest is given, it still counts
- Fetch/delivery quests reference items that exist or are obtainable in the world (solvability guarantee)

**Quest State:**
- `not_started` -> `active` -> `completed` or `failed`
- Multi-step: each sub-quest tracks independently, parent completes when all subs complete
- Failed quests: escort follower's destination is passed, or player progresses to next room without completing a room-local quest
- Quest failure penalties: HP/hunger/thirst damage (beyond losing the reward)
- Quest log accessible from player menu

**Quest Generation Flow:**
1. Per room: LLM generates 3x quest density per room (overproduction pool)
2. Quests are randomly selected from the pool for inclusion in the room
3. When being assigned: at least 1 quest per room is story-related, at least 1 multi-step quest, and at least 1 kill quest targeting faction
4. Remaining quests are room-local (fetch, dialogue, delivery within the room)
5. Escort and delivery quests that span rooms are generated with awareness of future room environments
6. Validation: all referenced items, NPCs, encounters, and locations exist; cross-room targets are in the next room only

**Story Quests — Optional but Consequential:**
- Player can progress by clearing 40% of room encounters (the door reveal threshold)
- Skipping story quests means missing story beats, NPC connections, and potentially useful rewards
- On entering next room after skipping story content: "You feel some things were left undone. Continue anyway?"
- Soft warning, not a blocker

**Followers (detail):**
- Max 2 followers at a time
- Followers do NOT appear on the map — managed entirely through the player menu
- Talk to follower from the player menu: opens dialogue about their quest, hints, personality
- Followers react to story events via dialogue ("This must be the place they told me about...") accessible from the player menu
- If follower's quest fails (player passes the drop-off room), they leave the party with a farewell line
- If follower's quest completes, reward + farewell

---

### 4.8 Screens & UX

**Overview**: V1 needs a full screen flow replacing the current "launch directly into gameplay" experience. Screens are managed by a state machine — each screen is a distinct game state with its own input handling and rendering.

**Screen Flow:**

```
Start Screen
  +-- New Game -> Class Selection -> Room Intro -> Gameplay
  +-- Load Game -> Gameplay (restored state)
  +-- Tutorial / Controls -> Start Screen
  +-- Quit

Gameplay
  +-- Player Menu (Tab or Esc key)
  |   +-- Inventory tab (can also open directly with I key)
  |   +-- Stats tab
  |   +-- Spells / Abilities tab
  |   +-- Followers tab
  |   +-- Quest Log tab
  |   +-- Back to Gameplay
  +-- Shop Screen (talk to merchant NPC)
  +-- Encounter Screen (step on hidden tile — all have GenAI art)
  |   +-- Combat Screen
  |   +-- Puzzle Screen
  |   +-- Event Screen
  +-- NPC Dialogue Screen (talk to NPC — shows GenAI portrait + dialogue box)
  +-- Room Transition -> Room Intro -> Gameplay
  +-- Pause (Esc)
      +-- Resume
      +-- Save Game
      +-- Controls
      +-- Quit to Start Screen

Game Over (HP = 0)
  +-- Load Game
  +-- Quit to Start Screen

Victory (final boss defeated)
  +-- Stats Summary -> Start Screen
```

**Esc Key Behavior:**
- In gameplay: opens pause/player menu
- In any submenu/screen (player menu tabs, shop, encounter, dialogue, etc.): closes/backs out to previous screen
- Stacks naturally: Esc from inventory tab -> player menu -> gameplay

**Screen Details:**

#### Start Screen
- Game title + GenAI-generated title art
- Menu options: New Game, Load Game, Tutorial, Quit
- If save files exist, Load Game is highlighted
- Background: environment portrait or stylized maze art

#### Class Selection Screen
- Shows 4 class options with: name, portrait, flavor text, stat array, starting weapon, spells/abilities
- Jester shown as black silhouette with "???" — stats and abilities hidden until selected
- Player selects with arrow keys + enter
- Allows player to name their character
- On select: confirmation prompt — "Will you be [Character Name] the [Class Name]?"
- Then transition to Room 1 intro

#### Room Intro Screen
- Full-screen GenAI-generated environment portrait
- Dialogue box overlay with story text for the room
- Player presses enter to proceed into gameplay
- Shown on new game start and every room transition

#### Gameplay HUD
- **Top bar**: HP, hunger, thirst (bars), money, time of day indicator
- **Mini info**: Current room name, room level, environment type
- **Notification area**: Quest updates, item pickups, door reveals — brief text that fades after a few seconds
- Maze + player + NPCs rendered as current system (with fog of war applied)

#### Player Menu (tabbed)

**Inventory tab:**
- Scrollable list of all items grouped by category (weapons, food, drink, tools, scrolls)
- Shows stack count, item name, brief effect
- Select item: use, equip (weapon), drop, or view detail
- View detail shows GenAI item portrait + item description + stats + modifier if applicable
- Equipped weapon marked

**Stats tab:**
- Class name, level, environment of origin, current room
- Full stat array (STR, DEX, CON, INT, WIS, CHA, LUCK)
- Derived stats: AC, attack modifier, spell modifier
- Survival stats: HP/hunger/thirst current and max
- Combat record: monsters killed, damage dealt/taken
- Quest record: completed, failed, active count
- Title (if earned through story events)

**Spells / Abilities tab:**
- List of all known spells and abilities
- Shows: name, type (damage/heal/buff/utility), cost (hunger/thirst), effect description
- Elemental type indicated
- Jester's learned spells marked as "(Learned)"

**Followers tab:**
- List of current followers (max 2)
- Select follower -> talk to them (opens dialogue about their quest, hints, personality reactions)
- Shows portrait, follower name, quest summary, destination

**Quest Log tab:**
- Active quests with current objective highlighted
- Multi-step quests show progress (step 2/3)
- Completed quests section (collapsed)
- Failed quests section (collapsed)
- Story quests visually distinct from side quests

#### Shop Screen
- Triggered by talking to a merchant NPC — shows GenAI merchant portrait + dialogue box
- Two columns: Buy (NPC inventory) and Sell (player inventory)
- Each item shows portrait, name, effect, price
- Player money displayed at top
- Confirm purchase/sale prompt

#### Encounter Screens

**Combat Screen:**
- Monster portrait(s) displayed
- Monster HP bars visible
- Turn order indicator
- Action menu: Attack, Multi-Attack, Cast Spell, Use Item, Flee
- Spell/ability submenu when Cast Spell selected
- Combat log showing recent actions ("You hit the wolf for 6 damage")
- Player HP/hunger/thirst visible

**Puzzle Screen:**
- Puzzle image + description text
- Player selects from inventory (tools, scrolls, abilities)
- Feedback: success or "This doesn't seem right..." on failure
- Option to leave and return later

**Event Screen:**
- Event image + description text
- Multiple choice options displayed with hints (e.g., "[STR check]", "[requires saw]")
- Dice roll animation on selection
- Result: success/failure + consequence

#### NPC Dialogue Screen
- NPC portrait displayed
- Dialogue text in box
- Mode-dependent input:
  - Offline static: multiple choice options
  - Local/online: free text input
- Conversation history scrollable
- Quest offer highlighted distinctly

#### Pause Screen
- Overlay on gameplay
- Resume, Save Game, Controls, Quit to Start Screen
- Save Game writes full game state

#### Game Over Screen
- "Game Over" message
- GenAI game over portrait + dialogue box
- Stats summary (brief)
- Options: Load Game, Quit to Start Screen

#### Victory Screen
- Story conclusion text
- Full stats summary: class, level reached, rooms cleared, quests completed/failed, monsters killed, items used, money earned, time played, followers escorted
- Option: Start New Game, Quit

#### Tutorial Screen
- Controls reference card — keybindings and basic mechanics

#### Quick Story Screen
- Accessible from player menu
- Overarching story summary and Room 1 intro
- No map screen for V1

---

### 4.9 Save / Load

**Overview**: Players can save their game from the pause menu and load from the start screen or game over screen. Save files capture the full game state so players can resume exactly where they left off.

**Save State (what's serialized):**

| Category | Data |
|---|---|
| Player | Name, class, stats, level, HP/hunger/thirst, inventory, equipped weapon, spells/abilities, money, position |
| Room | Current room number, maze layout, fog of war map (explored tiles), environment type |
| Encounters | Which tiles are cleared, which are active, combat encounter damage state (partially damaged monsters) |
| NPCs | All NPC states per room — position, dialogue history, shop inventory, quest-giver status |
| Quests | Full quest log — active, completed, failed; multi-step progress; cross-room quest state |
| Followers | Current followers, their quest state, dialogue history |
| Story | Overarching story data, per-room story beats (seen/unseen), story choices made |
| Time | Current time of day |
| Stats | Combat record, quest record (for victory screen) |
| World | All pre-generated room data for future rooms (so world_gen doesn't need to re-run) |

**Save Mechanics:**
- Save triggered from pause menu only (no autosave in V1)
- Each **playthrough** gets one save slot (no save scumming)
- Multiple playthroughs can exist for the same generated world (same seed, different class/character)
- Save file keyed by: seed + character name + class (e.g., `save_1234_gandalf_ranger.json`)
- Save file written to `saves/` directory as JSON
- Confirmation prompt before overwriting existing save
- Saving mid-combat: not allowed — save option grayed out during encounters

**Seed Clarification:**
- Seed controls world generation (`world_gen` / exe creation) — maze layouts, NPCs, items, encounters, story
- Same seed = same world, but multiple players can exist in that world independently
- Post-generation, the seed is baked in and doesn't affect gameplay

**Load Mechanics:**
- Load from start screen: shows list of all save files across all seeds/playthroughs
- Each save file displays: character name, class, seed/world name, room level, time played, last save date
- Load from game over screen: loads most recent save
- Loading restores full state — player is placed exactly where they saved

**Edge Cases:**
- Corrupted save: validate on load, show error if invalid, don't crash
- No save exists: Load Game option disabled on start screen

---

### 4.10 Survival Rebalance

**Overview**: Current system is too punishing — hunger/thirst drain too fast, making the game feel like a resource management grind rather than an RPG. V1 rebalances survival to be a meaningful constraint that rewards smart play without constant death.

**Design Goals:**
- Survival should create tension, not frustration
- Players should think about resources but not be constantly starving
- Spellcasters need enough hunger/thirst budget to actually cast spells
- Combat/quests/events should feed back into the survival loop (rewards restore stats)

**Drain Rates (reduced):**
- Movement drain: reduce to ~1/3 of current rate
- Drain scales with CON — higher CON = slower drain (CON modifier reduces drain per step, minimum 1 drain)
- No drain while stationary (talking to NPCs, browsing menus, etc.)
- Combat actions that cost hunger/thirst are the primary drain in mid-to-late game

**Thresholds (more forgiving):**

| Stat | Warning | Penalty | Critical |
|---|---|---|---|
| Hunger | < 30 | < 15 (reduced spell effectiveness) | 0 (slow HP drain, can't cast) |
| Thirst | < 30 | < 15 (reduced movement speed) | 0 (slow HP drain, can't cast) |
| HP | < 30% | < 15% (screen visual warning) | 0 (game over) |

**Starvation/Dehydration HP Drain:**
- At 0 hunger or 0 thirst: slow HP drain (e.g., 1 HP per 5 steps)
- Gives the player a window to find food/drink, reach a shop, or use Rest
- Not instant death, but a ticking clock

**Recovery Sources:**
- Food/drink items (primary)
- Quest/event rewards can include food, drink, or direct stat restoration
- Monster loot drops include food/drink
- NPC shops sell food/drink
- Rest action (see below)
- No restoration on room transition — player must manage resources to arrive in good shape

**Rest Mechanic:**

| Rest Duration | Time Advanced | HP Recovery | Hunger Recovery | Thirst Recovery |
|---|---|---|---|---|
| 3 hours | 3 hrs | Small | Small | Small |
| 6 hours | 6 hrs | Moderate | Moderate (cap) | Moderate (cap) |
| 12 hours | 12 hrs | Large | Moderate (same as 6hr) | Moderate (same as 6hr) |

- Hunger/thirst recovery caps at the 6-hour level — sleeping longer doesn't make you less hungry
- HP continues to benefit from longer rest
- Rest advances time of day — creates a real trade-off (time-gated events may become unavailable, day/night shift)
- In combat: Rest skips a turn, small HP/hunger/thirst recovery
- Outside combat: player selects duration from a submenu

**CON Integration:**
- CON modifier directly reduces hunger/thirst drain per step
- Example: CON 14 (+2 modifier) -> drain reduced by 2 per step (minimum 1 drain)
- Makes CON a meaningful stat choice, especially for spellcasters

**Scaling with Progression:**
- Room 1: generous food/drink placement, low drain — tutorial-friendly
- Later rooms: food/drink is less freely placed but available through shops, loot, and quest rewards
- Spell costs remain constant, but player has more recovery options in later rooms

---

### 4.11 Fog of War & Day/Night

**Overview**: Two systems that add exploration depth and time-based decision making. Fog of war hides unexplored areas. Day/night cycles affect what's available and create urgency around the Rest trade-off.

#### Fog of War

**Mechanics:**
- All maze tiles start hidden (black/dark overlay)
- Player reveals tiles within a visibility radius as they move
- Once revealed, tiles stay revealed permanently (no re-fogging)
- Revealed areas show: walls, paths, items, NPCs, doors (if discovered)
- Encounter tiles remain invisible even in revealed areas (by design — encounters are always hidden)

**Visibility Radius:**
- Default: 3-4 tiles in each direction from player
- Walls block line of sight — can't see around corners (raycasting)
- WIS modifier can increase radius (+1 tile per 2 WIS modifier points)

**What's Hidden vs Revealed:**

| Element | Fogged | Revealed |
|---|---|---|
| Walls / paths | Hidden | Visible |
| Items on ground | Hidden | Visible |
| NPCs | Hidden | Visible (with portrait dot) |
| Encounter tiles | Hidden | Still invisible (always hidden) |
| Doors | Hidden | Visible only after door reveal (40% encounters or quest) |
| Shop NPCs | Hidden | Visible (distinct color/marker) |

#### Day/Night Cycle

**Time System:**
- Time is action-based, not real-time
- Time advances with: movement steps, combat turns, Rest action
- Full day/night cycle = configurable number of actions (e.g., 200 actions = 1 full cycle)
- HUD shows current time: Dawn -> Day -> Dusk -> Night -> Dawn

**Time Periods:**

| Period | Duration (% of cycle) | Effects |
|---|---|---|
| Dawn | 15% | Transition period, all events available |
| Day | 35% | Standard — most events/NPCs active |
| Dusk | 15% | Transition period, some night events begin |
| Night | 35% | Night-only events active, some NPCs unavailable, some shops closed |

**Time Effects:**
- **Events**: Some encounter tiles are time-gated — only trigger during specific periods. Walking over them at the wrong time does nothing.
- **NPCs**: Some NPCs only appear during day or night. Night NPCs may offer different quests, shadier shops, or story-specific dialogue.
- **Monsters**: Night encounters can have different/harder monster pools. Night monsters may have dark elemental affinity.
- **Visibility**: Night reduces fog of war visibility radius by 1-2 tiles. Dawn/dusk normal. Day full radius.
- **Visual**: Night applies a dark/blue overlay on the entire gameplay screen.
- **Rest**: Advancing time via rest can shift from night to day (or vice versa) — strategic choice.

**Torch/Lantern:**
- Tool item, environment-themed (torch, lantern, glowing crystal, etc.)
- Restores full visibility radius at night
- Consumable with limited uses (like other tools)
- Available in shops, loot drops, and maze placement

**Generation:**
- Time-gated encounters tagged at build time with their active period(s)
- NPCs tagged with availability schedule (day, night, always)
- Monster pools generated with day/night variants per room
- Validation: time-gated content must be completable — quests that reference time-gated content include time hints in their description
- Time-gated quests/NPCs CAN be part of quest chains — the quest should clearly communicate the time requirement (e.g., "Take me there at night")

---

### 4.12 Music Generation — DEFERRED

**Status**: Requires research spike to identify viable music gen models (HuggingFace) or APIs.

**Target Design (for when implemented):**
- GenAI music per environment with separate themes for combat, dialogue/quests, map exploration, boss encounters
- ~2 minute tracks, seamless loop
- Start screen, victory, and game over themes
- Day/night variant via filter (not separate tracks)
- Crossfade transitions between tracks
- Volume configurable

**V1 Approach:**
- Game ships playable without music (silent)
- Music interface built into the game (play track, crossfade, volume control) for future plug-in
- Placeholder/royalty-free tracks can be dropped into `data/music/` if desired

---

### 4.13 Generation Validation (Agentic Flow)

**Overview**: Generation uses a parallel pipeline with three roles per content type: **Generator**, **Checker/Editor**, and **Validator**. A **World Editor** coordinates cross-content dependencies using a **World Bible** — a living document of all confirmed content and references.

**Pipeline Architecture:**

```
Phase 1 (Parallel):
+-------------------------------------------------------------+
|  Maze Generator -> Checker -> Validator    --> Maze Layout    |
|  Item Generator -> Checker -> Validator    --> Item Pool      |
|  Monster Generator -> Checker -> Validator --> Monster Pool   |
|  NPC Generator -> Checker -> Validator     --> NPC Pool       |
|  Encounter Generator -> Checker -> Validator -> Encounter Pool|
|  Quest Generator -> Checker -> Validator   --> Quest Pool     |
|  Class Generator -> Checker -> Validator   --> Class Options  |
+-------------------------------------------------------------+
                          | all pools ready
Phase 2 (Sequential):
+-------------------------------------------------------------+
|  World Editor                                               |
|  - Builds World Bible from all validated pools              |
|  - Reviews cross-content references (quests <-> NPCs <->   |
|    items <-> monsters <-> encounters)                       |
|  - Validates story quests, multi-step chains, follower      |
|    destinations                                             |
|  - Places content on the maze map                           |
|  - Confirms everything is closed (all references resolve)   |
|  - Approves or sends back for regeneration                  |
+-------------------------------------------------------------+
                          | approved
Phase 3:
+-------------------------------------------------------------+
|  Write to data/ + manifest.json                             |
+-------------------------------------------------------------+
```

**Three Roles per Content Type:**

| Role | Responsibility | Implementation |
|---|---|---|
| Generator | Produces content from environment + level + story seed | LLM generation call |
| Checker/Editor | Reviews output for theme, coherence, quality; edits if needed | Separate LLM review call (avoids blind spots) |
| Validator | Checks hard rules (stat ranges, required fields, valid references); pass/fail | Rule-based + LLM call for subjective quality |

**Retry Strategy:**
- Each content type gets up to 3 regeneration attempts
- On retry, the validation failure reason is passed back to the LLM as context ("Previous generation failed because: quest references NPC 'Garak' who doesn't exist in room 2. Fix this.")
- LLM self-corrects with the feedback

**Fallback Strategy:**
- If retries exhausted, use a template-based fallback (hardcoded safe defaults)
- Flag the failure in `manifest.json` so it's visible
- Game is still playable with fallback content

**World Bible:**
- Central data structure built by the World Editor after Phase 1
- Contains all confirmed content with cross-references
- Every entity has an ID and a list of what references it
- World Editor confirms: every reference resolves to an existing entity, no dangling pointers

```
World Bible:
  story: { faction, arc, final_boss, per_room_beats }
  rooms:
    room_1:
      maze: { layout_ref, environment, doors }
      npcs: [ { id, name, type, shop?, quests_given: [quest_ids] } ]
      items: [ { id, name, category, placed_at, referenced_by: [quest_ids, encounter_ids] } ]
      monsters: [ { id, name, placed_in: [encounter_ids] } ]
      encounters: [ { id, type, tile_pos, requires: [item_ids, ability_ids] } ]
      quests: [ { id, type, giver_npc, targets: [npc_ids, item_ids, monster_ids, room_ids] } ]
```

**World Editor Checks:**

| Check | Rule |
|---|---|
| Quest completability | All referenced items/monsters/NPCs exist and are reachable |
| Cross-room quests | Point forward, max 1 room ahead |
| Story presence | Each room has at least 1 story quest, 1 multi-step, 1 faction kill |
| Gate encounter | Every room has a gate boss/encounter blocking the door |
| Encounter solvability | Every puzzle/event has at least 1 solution achievable with available items/abilities |
| NPC references | Quest-giver NPCs exist in the correct room |
| Time-gated clarity | Time-gated quests/encounters include time hints in their description |
| Map placement | All content placed on valid open tiles, no overlaps, NPCs not on walls |
| Item coverage | Puzzles/events don't require tools that don't exist in the world |

**What the World Editor does NOT check (runtime concerns):**
- Max follower count — enforced by gameplay, not generation
- Player inventory state — that's a runtime problem
- Whether the player picked the "right" class — solvability assumes tools/abilities exist, not that the player has them

**Failure Handling:**

| Severity | Examples | Action |
|---|---|---|
| Critical | No gate encounter, story has no final boss, quest references nonexistent NPC | Block build, retry generation |
| Major | Puzzle has no valid solution, item pool missing a required tool | Retry generation with feedback |
| Minor | NPC name slightly off-theme, monster flavor text is generic | Accept with warning in manifest |

**World Bible & Databases — Persistent Artifacts:**
- World Bible (`data/world_bible.json`) persists as the cross-reference index
- All content databases (`data/npcs/`, `data/items/`, `data/quests/`, etc.) persist as generated
- Runtime reads from these — NPC dialogue uses World Bible for context, quest log pulls from quest database, shops reference item database
- Save files reference World Bible entity IDs, not duplicated data

**Prompt Stack Architecture:**
- Each role (Generator, Checker, Validator, World Editor) has its own prompt template
- Prompts are modular — stored in `src/prompts/` alongside existing prompt sets
- Each prompt receives structured context (environment, level, story seed, World Bible excerpt)
- Output is structured (JSON schema enforced) so databases are machine-readable
- Same prompt stack works across all three modes — just dispatched to different backends

**API Mode Parallelism:**
- Phase 1 runs all generators in parallel (async API calls)
- Each generator -> checker -> validator chain runs as its own pipeline
- Phase 2 (World Editor) waits for all Phase 1 pipelines to complete
- Significantly faster than sequential generation

**Manifest Validation Report:**
```json
{
  "validation": {
    "status": "passed",
    "rooms_validated": 5,
    "critical_failures": 0,
    "major_retries": 2,
    "minor_warnings": 4,
    "details": []
  }
}
```

---

### 4.14 Config & Packaging

**Overview**: Players configure world generation settings before building. The build process generates all content, validates it, and packages a distributable executable.

**Config Settings:**

| Setting | Description | Default |
|---|---|---|
| `SEED` | World generation seed (-1 for random) | 1234 |
| `STORY_SEED` | 1-liner story prompt (e.g., "A fire cult corrupts the land") | "" (LLM generates freely) |
| `NUM_ROOMS` | Number of maze rooms | 5 |
| `MAZE_WIDTH` | Maze width in cells | 40 |
| `MAZE_HEIGHT` | Maze height in cells | 25 |
| `EVENT_DENSITY` | Percentage of open tiles with encounters | 10% |
| `QUEST_DENSITY` | Quests per room (multiplied by 3x for generation pool) | 5 |
| `MAP_COLORS` | Color scheme for maze rendering | default |
| `GAME_MODE` | offline_static, offline_local, online | online |
| `LLM_BACKEND` | local, api | api |
| `IMAGE_BACKEND` | local, api | api |
| `MUSIC_BACKEND` | local, api, none | none |
| `ANTHROPIC_API_KEY` | Claude API key | .env |
| `FAL_KEY` | fal.ai image API key | .env |
| `MASTER_VOLUME` | Master volume (0-100) | 80 |
| `MUSIC_VOLUME` | Music volume (0-100) | 60 |

**Config Sources (priority order):**
1. CLI arguments (`python main.py --seed 42 --num-rooms 3`)
2. `.env` file
3. `config.py` defaults

**Single Entry Point — `main.py`:**

```
python main.py                  -> Generate world + package exe
python main.py --dev            -> Generate world + run game directly (no packaging)
python main.py --dev --skip-gen -> Skip generation, run from existing data/ (fastest dev loop)
```

- Default behavior: generate everything, package `mazeworld_{seed}.exe`
- `--dev` skips packaging, launches the game directly after generation
- `--dev --skip-gen` skips generation entirely, uses existing `data/`, launches game
- Any config change = full regeneration from scratch (no partial regeneration)

**Manifest (`data/manifest.json`):**
```json
{
  "seed": 1234,
  "story_seed": "A fire cult corrupts the land",
  "game_mode": "online",
  "num_rooms": 5,
  "environments": ["forest", "cave", "city", "desert", "volcano"],
  "generated_at": "2026-04-05T12:00:00Z",
  "validation": {},
  "content_index": {
    "rooms": 5,
    "npcs": 47,
    "items": 62,
    "quests": 23,
    "encounters": 89,
    "monsters": 34,
    "images": 112,
    "music_tracks": 0
  }
}
```

**Staleness Check:**
- On `main.py --dev` launch, compare config against manifest
- If seed or key settings differ, prompt user to regenerate
- If `data/` is missing, force generation

---

## 5. Technical Design

### 5.1 Architecture Overview

```
main.py (entry point)
  |
  +-- --default  -> Generation Pipeline -> PyInstaller Packaging -> exe
  +-- --dev      -> Generation Pipeline -> Game Runtime (direct)
  +-- --dev --skip-gen -> Game Runtime (from existing data/)

Generation Pipeline:
  config.py -> Prompt Stack -> Parallel Generators -> World Editor -> data/ + World Bible

Game Runtime:
  data/ + World Bible -> Registry -> Screen State Machine -> Gameplay Loop
```

### 5.2 Directory Structure

```
MazeWorld/
+-- main.py                     # Single entry point
+-- config.py                   # All config settings + CLI arg parsing
+-- src/
|   +-- models/                 # Pydantic data models
|   |   +-- player.py           # Player, PlayerClass, Stats, Abilities
|   |   +-- combat.py           # CombatState, TurnOrder, Action
|   |   +-- monster.py          # Monster, MonsterPool, LootTable
|   |   +-- maze.py             # Maze (existing, extended with doors/fog)
|   |   +-- npc.py              # NPC (existing, extended with shop/schedule)
|   |   +-- quest.py            # Quest, QuestChain, QuestLog
|   |   +-- encounter.py        # Encounter, CombatEncounter, PuzzleEncounter, EventEncounter
|   |   +-- items.py            # Item, Weapon, Food, Drink, Tool, SpellScroll
|   |   +-- follower.py         # Follower
|   |   +-- story.py            # OverarchingStory, RoomStoryBeat, Faction
|   |   +-- world_bible.py      # WorldBible, EntityReference, cross-ref index
|   |   +-- time.py             # DayNightCycle, TimePeriod
|   |   +-- save.py             # SaveState serialization
|   |
|   +-- generate/               # Generation pipeline
|   |   +-- pipeline.py         # Orchestrator — parallel Phase 1, sequential Phase 2
|   |   +-- generator.py        # Base Generator class
|   |   +-- checker.py          # Base Checker/Editor class
|   |   +-- validator.py        # Base Validator class (rule-based + LLM)
|   |   +-- world_editor.py     # World Editor — cross-content validation, placement, Bible
|   |   +-- generators/         # Per-content-type generators
|   |   |   +-- maze_gen.py
|   |   |   +-- class_gen.py
|   |   |   +-- item_gen.py
|   |   |   +-- monster_gen.py
|   |   |   +-- npc_gen.py
|   |   |   +-- encounter_gen.py
|   |   |   +-- quest_gen.py
|   |   |   +-- story_gen.py
|   |   +-- llm_client.py       # Unified LLM interface (existing, extended)
|   |   +-- image_client.py     # Image generation interface (existing, refactored)
|   |   +-- music_client.py     # Music generation interface (stub for now)
|   |
|   +-- prompts/                # Prompt templates per role per content type
|   |   +-- base.py             # Abstract PromptSet (existing)
|   |   +-- generator_prompts/  # Generator role prompts
|   |   +-- checker_prompts/    # Checker/Editor role prompts
|   |   +-- validator_prompts/  # Validator role prompts (subjective checks)
|   |   +-- world_editor_prompts/ # World Editor prompts
|   |
|   +-- controllers/            # Game runtime controllers
|   |   +-- game_controller.py  # Main game loop (existing, heavily refactored)
|   |   +-- combat_controller.py # Turn-based combat loop
|   |   +-- screen_controller.py # Screen state machine
|   |   +-- input_controller.py  # Input routing per screen state
|   |
|   +-- views/                  # Pygame rendering per screen
|   |   +-- start_view.py
|   |   +-- class_select_view.py
|   |   +-- room_intro_view.py
|   |   +-- gameplay_view.py    # HUD + maze + fog of war
|   |   +-- menu_view.py        # Tabbed player menu
|   |   +-- combat_view.py
|   |   +-- encounter_view.py   # Puzzle + event screens
|   |   +-- dialogue_view.py    # NPC dialogue (existing, extended)
|   |   +-- shop_view.py
|   |   +-- pause_view.py
|   |   +-- gameover_view.py
|   |   +-- victory_view.py
|   |
|   +-- systems/                # Gameplay systems
|   |   +-- survival.py         # Hunger/thirst/HP drain, rest, recovery
|   |   +-- fog_of_war.py       # Visibility, reveal, line of sight
|   |   +-- day_night.py        # Time tracking, period transitions, effects
|   |   +-- quest_manager.py    # Quest state tracking, completion, failure
|   |   +-- follower_manager.py # Follower state, dialogue, quest tracking
|   |   +-- inventory.py        # Item management, stacking, equipping
|   |   +-- save_manager.py     # Save/load serialization
|   |
|   +-- data/                   # Static data (existing)
|   |   +-- world_data.py
|   |
|   +-- utils/                  # Helpers (existing, cleaned up)
|   |   +-- conversation_utils.py
|   |   +-- dataloader_utils.py
|   |   +-- display_utils.py
|   |
|   +-- registry.py             # Singleton registry (existing, extended to load World Bible)
|
+-- data/                       # Generated content (output of pipeline)
|   +-- world_bible.json
|   +-- manifest.json
|   +-- rooms/
|   |   +-- room_1/
|   |   |   +-- maze.json
|   |   |   +-- npcs.json
|   |   |   +-- items.json
|   |   |   +-- monsters.json
|   |   |   +-- encounters.json
|   |   |   +-- quests.json
|   |   +-- room_2/ ...
|   +-- story/
|   |   +-- story.json
|   |   +-- classes.json
|   +-- images/
|   |   +-- portraits/
|   |   +-- environments/
|   |   +-- monsters/
|   |   +-- items/
|   |   +-- encounters/
|   +-- music/                  # Stub — populated when music gen implemented
|   +-- saves/
|
+-- tests/
+-- requirements.txt
+-- .github/workflows/ci.yml
```

### 5.3 Key Data Models

**PlayerClass:**
```python
class PlayerClass(BaseModel):
    name: str                    # "Ranger"
    archetype: str               # "warrior" | "mage" | "healer" | "jester"
    flavor_text: str
    environment: str
    stats: Stats                 # STR, DEX, CON, INT, WIS, CHA, LUCK
    starting_weapon: str         # item_id reference
    abilities: list[Ability]
    spells: list[Spell]
    portrait_path: str
```

**Stats:**
```python
class Stats(BaseModel):
    STR: int
    DEX: int
    CON: int
    INT: int
    WIS: int
    CHA: int
    LUCK: int

    def modifier(self, stat: str) -> int:
        return (getattr(self, stat) - 10) // 2
```

**Monster:**
```python
class Monster(BaseModel):
    id: str
    name: str
    environment: str
    level: int
    hp: int
    ac: int
    STR: int
    DEX: int
    attack_name: str            # "bite", "slash"
    damage_dice: str            # "1d6"
    damage_type: str            # "physical", "fire", "dark", etc.
    elemental_affinity: str | None
    abilities: list[str]        # "poison", "stun"
    loot_table: list[LootDrop]
    portrait_path: str
```

**Quest:**
```python
class Quest(BaseModel):
    id: str
    type: str                   # fetch, kill, escort, delivery, dialogue, multi_step
    title: str
    description: str
    giver_npc_id: str
    room_id: str
    is_story_quest: bool
    targets: list[QuestTarget]  # what needs to be done
    rewards: list[QuestReward]
    status: str                 # not_started, active, completed, failed
    sub_quests: list[str]       # quest_ids for multi-step
    time_gate: str | None       # "night", "day", None
```

**WorldBible:**
```python
class WorldBible(BaseModel):
    story: OverarchingStory
    rooms: dict[str, RoomBible]
    entity_index: dict[str, EntityRef]  # global ID -> type + location

class RoomBible(BaseModel):
    environment: str
    level: int
    story_beat: str
    maze_ref: str
    npcs: list[str]             # npc_ids
    items: list[str]            # item_ids
    monsters: list[str]         # monster_ids
    encounters: list[str]       # encounter_ids
    quests: list[str]           # quest_ids
    gate_encounter_id: str
```

### 5.4 Screen State Machine

```python
class ScreenState(Enum):
    START = "start"
    CLASS_SELECT = "class_select"
    ROOM_INTRO = "room_intro"
    GAMEPLAY = "gameplay"
    PLAYER_MENU = "player_menu"
    COMBAT = "combat"
    ENCOUNTER = "encounter"
    DIALOGUE = "dialogue"
    SHOP = "shop"
    PAUSE = "pause"
    GAME_OVER = "game_over"
    VICTORY = "victory"

class ScreenController:
    state: ScreenState
    state_stack: list[ScreenState]  # for nested screens

    def push(self, state): ...      # open a new screen on top
    def pop(self): ...              # Esc — return to previous
    def replace(self, state): ...   # transition (room intro -> gameplay)
```

- Esc always calls `pop()` — context-sensitive close
- Push/pop enables nesting (gameplay -> pause -> controls -> back -> back)
- Replace for non-reversible transitions (class select -> room intro -> gameplay)

### 5.5 Combat System

```python
class CombatController:
    participants: list[Combatant]   # player + monsters, sorted by initiative
    current_turn: int
    combat_log: list[str]

    def roll_initiative(self): ...
    def execute_action(self, action: CombatAction): ...
    def check_victory(self) -> bool: ...
    def check_defeat(self) -> bool: ...
    def attempt_flee(self) -> bool: ...
```

- Runs as its own loop within the combat screen state
- Returns result to encounter controller (victory, defeat, fled)
- Player HP/hunger/thirst modifications applied in real-time

### 5.6 Generation Pipeline

```python
class GenerationPipeline:
    config: Config
    llm_client: LLMClient
    image_client: ImageClient

    async def run(self):
        # Phase 0: Generate overarching story
        story = await self.generate_story()

        # Phase 1: Parallel per-room generation
        rooms = await asyncio.gather(*[
            self.generate_room(room_num, story)
            for room_num in range(config.NUM_ROOMS)
        ])

        # Phase 2: World Editor
        bible = WorldEditor.build_bible(story, rooms)
        bible = WorldEditor.validate_and_fix(bible)

        # Phase 3: Image generation (parallel)
        await self.generate_all_images(bible)

        # Phase 4: Write to data/
        self.write_output(bible, rooms)

    async def generate_room(self, room_num, story):
        # Parallel generators within room
        maze, items, monsters, npcs, encounters, quests = await asyncio.gather(
            MazeGenerator.run(room_num, story),
            ItemGenerator.run(room_num, story),
            MonsterGenerator.run(room_num, story),
            NPCGenerator.run(room_num, story),
            EncounterGenerator.run(room_num, story),
            QuestGenerator.run(room_num, story),
        )
        return RoomData(maze, items, monsters, npcs, encounters, quests)
```

- Phase 0 (story) runs first — everything else depends on it
- Phase 1 runs rooms in parallel, and within each room, content types in parallel
- Phase 2 (World Editor) is sequential — needs all content to cross-validate
- Phase 3 (images) parallelized after Bible is confirmed
- API mode benefits most from parallelism; local mode limited by GPU

### 5.7 Fog of War System

```python
class FogOfWar:
    revealed: set[tuple[int, int]]  # set of revealed tile coordinates
    visibility_radius: int          # base + WIS modifier

    def update(self, player_pos, maze): ...  # reveal tiles within radius, blocked by walls
    def is_visible(self, pos) -> bool: ...
    def apply_night(self, period): ...       # reduce radius at night
    def apply_torch(self): ...               # restore full radius
```

- Line-of-sight raycasting from player position
- Walls block visibility
- Stores revealed set, persisted in save file

### 5.8 Day/Night System

```python
class DayNightCycle:
    total_actions: int              # actions in a full cycle
    current_action: int             # current position in cycle

    def advance(self, actions: int): ...
    def get_period(self) -> TimePeriod: ...  # dawn, day, dusk, night
    def get_visual_overlay(self) -> tuple: ...  # RGBA for screen overlay
```

- Advances on movement, combat turns, rest
- Period boundaries calculated from configurable cycle length
- Night overlay applied by the gameplay view

### 5.9 Save System

```python
class SaveState(BaseModel):
    # Metadata
    seed: int
    character_name: str
    class_name: str
    save_date: str

    # Player
    player: PlayerState
    inventory: list[ItemStack]
    quest_log: QuestLog
    followers: list[FollowerState]

    # World
    current_room: int
    fog_map: set                    # explored tiles for current room
    encounter_states: dict[str, str] # encounter_id -> cleared/active/fled
    npc_states: dict[str, NPCState] # dialogue history, shop inventory
    time: int                       # current action count

    # Reference
    world_bible_hash: str           # verify save matches world
```

- Single save slot per playthrough (seed + character name + class)
- Saved to `data/saves/save_{seed}_{name}_{class}.json`
- World Bible hash ensures save isn't loaded against a different world

---

## 6. Dependencies & Risks

### Dependencies

| Dependency | What Needs It | Risk Level | Mitigation |
|---|---|---|---|
| **Anthropic Claude API** | Online mode LLM generation, agentic validation pipeline | Medium | Local mode fallback (Llama); API key required in config |
| **fal.ai API** | Online mode image generation | Medium | Local mode fallback (Diffusers); API key required in config |
| **HuggingFace / Llama 3.2** | Local mode LLM generation | Low | Already working; needs testing with expanded prompt stack |
| **Diffusers (FLUX/SDXL)** | Local mode image generation | Low | Already working; volume of images increases significantly |
| **Pygame** | All game rendering and input | Low | Stable, already in use |
| **PyInstaller** | Exe packaging | Medium | Not yet wired up; bundling data/ + models could be complex |
| **Music gen model/API** | Music generation (deferred) | High | No solution identified yet; research item |
| **GPU (CUDA/MPS)** | Local mode LLM + image generation | Medium | CPU fallback exists but is slow |
| **Pydantic** | All data models | Low | Already in use; V1 adds many new models |
| **asyncio** | Parallel generation pipeline | Low | Standard library |

### Risks

#### High Risk

**Image generation volume**
- Current: ~40 images per world
- V1: potentially 200+ images per world (NPCs, monsters, items, encounters, environments, classes, game over, victory)
- API cost scales linearly; local generation time scales linearly
- **Mitigation**: batch generation, parallel API calls, consider lower-res images for less critical assets, configurable image quality setting

**Generation pipeline complexity**
- The agentic flow (generator -> checker -> validator -> world editor) is the most complex new system
- Cross-content validation is hard to get right — subtle reference bugs
- **Mitigation**: build incrementally; get single-room generation working first; add cross-room and World Editor after; comprehensive integration tests

**LLM output reliability**
- LLMs don't always produce valid JSON or respect stat guardrails
- Structured output can still be malformed or logically inconsistent
- **Mitigation**: Pydantic validation on all LLM output; checker/editor catches logical issues; retry with feedback; template fallbacks

#### Medium Risk

**Combat balance**
- Many tuning variables: hunger/thirst costs, elemental multipliers, multi-target, level scaling
- Risk of combat being too easy, too hard, or tedious
- **Mitigation**: playtest early; make all combat numbers configurable; dedicated balance pass before release

**Save file size**
- World Bible + all future room data stored in save
- Large worlds could produce multi-MB save files
- **Mitigation**: save references (entity IDs), not duplicated data; images stay in data/images/

**Scope creep during implementation**
- V1 is already ambitious — 14 feature specs
- Risk of "just one more thing" extending indefinitely
- **Mitigation**: strict adherence to scope section; anything not in the PDR is post-V1

**Incremental refactor stability**
- Refactoring existing code while adding new features risks breaking what works
- **Mitigation**: keep game runnable throughout; CI runs tests on every push; refactor one module at a time with tests

#### Low Risk

**Pygame limitations for UI**
- Building tabbed menus, scrollable lists, shop screens requires custom widget code
- **Mitigation**: keep UI simple; no animations beyond crossfade and dice roll; consider a lightweight Pygame UI library if needed

**Three-mode parity**
- Static mode needs all content pre-generated including dialogue trees and multiple choice options
- Risk of static mode feeling significantly worse than online mode
- **Mitigation**: invest in quality dialogue tree generation; static mode is the baseline, not an afterthought

**PyInstaller bundling**
- Bundling local mode (torch + transformers + diffusers) will produce a very large exe
- **Mitigation**: may need separate exe configs per mode; defer local mode packaging if needed

---

## 7. Phased Delivery Plan

**Principles:**
- Game stays runnable after every phase
- Tests written alongside features, not after
- Incremental refactor — port existing code into new structure before building new features on top
- Each phase has a clear "done" definition

---

### Phase 1 — Foundation & Restructure

**Goal**: New project structure in place, existing functionality preserved, core data models defined.

**Work:**
- Restructure directory layout per 5.2 (models/, generate/, controllers/, views/, systems/)
- Migrate existing models (maze, NPC, player, items, quest, event) into new structure
- Define new Pydantic models: Stats, PlayerClass, Monster, WorldBible, OverarchingStory, SaveState
- Refactor `main.py` as single entry point with `--dev` and `--dev --skip-gen` flags
- Fold `world_gen.py` into `main.py` orchestration
- Implement screen state machine (ScreenController with push/pop/replace)
- Build start screen (New Game, Load Game, Tutorial, Quit — Load/Tutorial can be stubs)
- Fix NPC environment bug (inherit from maze)
- Add `__init__.py` files, clean up imports

**Tests:**
- All existing tests pass against new structure
- Unit tests for new data models
- Unit test for screen state machine (push, pop, replace, Esc behavior)

**Done when:** `python main.py --dev` launches start screen -> enters existing gameplay with current functionality intact.

---

### Phase 2 — Player Classes & Stats

**Goal**: Player creates a character with a class, stats, and abilities. Class selection screen functional.

**Work:**
- Implement class generation pipeline (generator -> checker -> validator) for 4 archetypes
- Stats system with modifiers (STR, DEX, CON, INT, WIS, CHA, LUCK)
- Stat guardrails per archetype (primary/secondary/dump ranges, total budget)
- Ability and spell data models
- Class selection screen: 4 options with portrait, stats, flavor text; Jester as black box
- Character naming with confirmation ("Will you be [Name] the [Class]?")
- Room intro screen with generated environment portrait + story text
- Player model refactored to use new Stats, equipped weapon, ability list
- Image generation for class portraits

**Tests:**
- Class generation produces valid stat arrays within guardrails
- All 4 archetypes generated with correct spell/ability counts
- Stat modifier calculation
- Class selection screen state transitions

**Done when:** Player can start a new game, name their character, select a class, see the room intro, and enter gameplay with their class stats applied.

---

### Phase 3 — Combat System

**Goal**: Turn-based combat fully functional with melee, magic, items, and flee.

**Work:**
- CombatController: initiative, turn order, action resolution
- Melee attack: roll to hit vs AC, damage dice + modifier
- Magic system: 5 elements, elemental advantage (1.5x/0.5x), hunger/thirst cost per spell
- Multi-target attacks and spells
- Jester's Gamble ability with LUCK-influenced random effects
- Jester modifier rule: avg(LUCK mod, normal stat mod) for borrowed abilities
- Use Item in combat (food/drink for recovery)
- Flee mechanic (1d20 + DEX vs DC 12 + monster level, free attack on fail)
- Combat view: monster portraits, HP bars, turn order, action menu, combat log
- Monster data model with stats, damage type, elemental affinity, abilities (battle-scoped)
- Death -> game over screen

**Tests:**
- Initiative ordering
- Attack roll vs AC resolution (hit/miss)
- Elemental multiplier calculations
- Spell hunger/thirst cost deduction
- Multi-target damage distribution
- Flee success/failure
- Jester Gamble effect distribution influenced by LUCK
- Combat ends correctly on victory/defeat/flee

**Done when:** Player can enter combat, take turns, attack, cast spells, use items, flee, and win or die.

---

### Phase 4 — Items, Inventory & Shops

**Goal**: GenAI items per environment, expanded inventory, weapon swapping, NPC shops, money system.

**Work:**
- Item generation pipeline: food, drink, tools, weapons, spell scrolls per environment
- Environment-themed item pools
- Unlimited inventory with stacking
- Weapon equipping and mid-combat swapping
- Spell scrolls: consumable for all classes, learnable by Jester
- Money as a tracked resource
- Monster loot drops with probability-based drop tables
- NPC shop system: merchant NPCs with buy/sell interface
- Shop view: two-column buy/sell, item portraits, prices
- Item detail view: portrait + description + stats
- Item scaling with room level

**Tests:**
- Item generation produces valid categories and environment-themed names
- Inventory stacking, equipping, swapping
- Shop buy/sell transactions
- Loot drop probability
- Spell scroll consumption vs Jester learning

**Done when:** Player finds environment-themed items, manages inventory, equips weapons, buys/sells at shops, and monsters drop loot.

---

### Phase 5 — Encounters & Monsters

**Goal**: Full encounter system with invisible tiles, combat/puzzle/event types, and generated monsters.

**Work:**
- Encounter tile system: invisible placement, trigger on step
- Encounter screen: image + type-specific UI
- Combat encounters: generate monster compositions (solo, pack, mixed) per room level
- Monster generation pipeline: environment-themed pools with level scaling
- Monster abilities (poison, stun, elemental — battle-scoped only)
- Puzzle encounters: tool/ability/spell solutions, wrong tool warning + consumption, leave and return
- Event encounters: multi-choice with stat/tool/ability checks, dice rolls, walk away option
- Encounter solvability validation in generation
- Encounter density configurable

**Tests:**
- Encounter tile triggers correctly (invisible, one-time)
- Monster composition scales with room level
- Monster stats within level scaling guardrails
- Puzzle solvability validation catches unsolvable puzzles
- Event dice roll + modifier resolution
- Wrong tool consumed with warning

**Done when:** Player walks through the maze, hits invisible encounter tiles, fights generated monsters, solves puzzles, and resolves events.

---

### Phase 6 — Quests, Story & Followers

**Goal**: Connected quest system, overarching story, followers, and quest log.

**Work:**
- Overarching story generation from story seed + room count
- Per-room story beats, faction presence, escalation arc
- Quest generation pipeline: 3x density pool -> random selection with minimums (1 story, 1 multi-step, 1 faction kill)
- All quest types: fetch, kill, escort (follower), delivery, dialogue, multi-step
- Cross-room quests (forward only, max 1 room ahead)
- Kill quests completable out of order
- Follower system: max 2, managed via player menu, not visible on map
- Follower dialogue (quest hints, story reactions)
- Follower quest failure (player passes drop-off room)
- Quest log in player menu (active, completed, failed, story vs side)
- NPC dialogue flavored by story context
- Quest failure penalties (HP/hunger/thirst damage)
- Dialogue quests: CHA check (offline static = multiple choice, online = free text + LLM eval)

**Tests:**
- Story generation produces faction, arc, final boss
- Quest validation: all references resolve
- Cross-room quests only point forward, max 1 room
- Kill quest completes when encounter already cleared
- Follower joins/leaves correctly
- Follower quest fails on room progression past destination
- Quest log state transitions

**Done when:** Player receives quests from NPCs, follows multi-step story chains, escorts followers, and sees the overarching story unfold.

---

### Phase 7 — Multi-Room & Progression

**Goal**: Multiple interconnected rooms with doors, gate encounters, level-up, and room transitions.

**Work:**
- Multi-room maze generation (N rooms, each with own environment)
- Door discovery: hidden until 40% encounters cleared or NPC quest reveals
- Gate encounters: story boss or multi-step encounter blocking each door
- Gate failure: player passes through with heavy survival penalty
- Room transitions: environment portrait + story dialogue screen
- Level-up on room entry: player selects new ability from class pool
- Jester level-up: randomly assigned from other class pools
- Monster/item/encounter scaling per room level
- Story escalation across rooms
- Final room: climax boss + victory screen with stats summary
- "Things left undone" warning when entering next room with incomplete story quests

**Tests:**
- Door reveals at 40% encounter threshold
- Gate encounter blocks progression until resolved
- Gate failure applies survival penalty
- Level-up offers correct ability pool per class
- Room transition renders portrait + story text
- Final boss victory triggers victory screen
- Stats summary accurate

**Done when:** Player progresses through multiple rooms, levels up, faces gate bosses, and can complete the full game loop from start to victory.

---

### Phase 8 — Fog of War & Day/Night

**Goal**: Exploration and time systems add depth to gameplay.

**Work:**
- Fog of war: all tiles start hidden, reveal within visibility radius
- Line-of-sight raycasting blocked by walls
- WIS modifier increases radius
- Fog persists (revealed tiles stay revealed)
- Day/night cycle: action-based time advancement
- Time periods: dawn, day, dusk, night with configurable cycle length
- Night visual overlay (dark/blue tint)
- Night reduces visibility radius
- Torch/lantern item restores full radius at night
- Time-gated encounters: only trigger during correct period
- Time-gated NPCs: availability schedule (day, night, always)
- Night monster variants (harder, dark elemental)
- Rest mechanic: 3/6/12 hour options, HP/hunger/thirst recovery with caps, advances time
- HUD time-of-day indicator

**Tests:**
- Fog reveals correctly within radius
- Walls block line of sight
- WIS modifier extends radius
- Time advances on movement, combat, rest
- Period transitions at correct thresholds
- Night overlay applied
- Night reduces visibility
- Torch restores radius
- Time-gated encounters only trigger in correct period
- Rest recovery amounts and caps correct

**Done when:** Player explores through fog, time passes with actions, night changes the experience, and rest is a meaningful trade-off.

---

### Phase 9 — Survival Rebalance & Screens

**Goal**: Survival feels fair, all screens complete, full UX flow polished.

**Work:**
- Survival rebalance: reduced drain rates, CON modifier reduces drain
- Thresholds adjusted (warning at 30, penalty at 15, critical at 0)
- Slow HP drain at 0 hunger/thirst (1 HP per 5 steps)
- Spell/ability costs balanced against new drain rates
- Room 1 generous placement, later rooms rely on shops/loot/quests
- Player menu complete: all tabs (inventory, stats, spells, followers, quest log)
- Stats tab: full stat display, combat record, quest record, title
- Tutorial/controls screen (reference card)
- Quick story screen (overarching story summary + current room intro)
- Pause screen: resume, save, controls, quit
- Save/load fully functional (single slot per playthrough, multiple playthroughs)
- Game over screen with GenAI portrait
- All Esc-to-close behavior working throughout

**Tests:**
- Drain rates at various CON levels
- Starvation HP drain rate
- Spell cost + drain doesn't kill player in 3 casts
- Save/load round-trip (save -> quit -> load -> state matches)
- Multiple playthroughs for same seed
- All screen transitions tested

**Done when:** Full playable game with balanced survival, all screens functional, save/load working. This is the **feature-complete milestone**.

---

### Phase 10 — Generation Pipeline & Validation

**Goal**: Full agentic generation pipeline with parallel execution and World Bible.

**Work:**
- Async generation pipeline with parallel Phase 1 (per-room, per-content-type)
- Generator -> Checker/Editor -> Validator chain per content type
- Prompt stack: all prompts for all roles stored in `src/prompts/`
- World Editor: builds World Bible, cross-validates all references, places content on map
- World Bible persisted to `data/world_bible.json`
- Retry with feedback (up to 3 retries, failure reason passed to LLM)
- Template fallbacks for critical failures
- Validation report in manifest.json
- Critical failures block build; minor issues accepted with warnings
- All three modes tested: offline_static, offline_local, online

**Tests:**
- Pipeline produces valid World Bible with all cross-references resolved
- Retry produces corrected output when given failure feedback
- Fallback triggers on exhausted retries
- Validation catches: missing gate encounter, dangling quest reference, unsolvable puzzle
- Manifest validation report accurate
- All three modes produce playable output

**Done when:** `python main.py` runs the full agentic pipeline, produces validated content, and the game is playable from generated output. This is the **generation-complete milestone**.

---

### Phase 11 — Packaging & Release

**Goal**: Distributable exe, final polish, release.

**Work:**
- PyInstaller config: bundle game + `data/` into `mazeworld_{seed}.exe`
- Test exe on clean machine (no Python installed)
- Config via CLI args (`--seed`, `--num-rooms`, etc.)
- Final balance pass: combat numbers, survival drain, encounter density, quest rewards
- Playtest full game loop: start -> class select -> all rooms -> victory
- Bug fixes from playtesting
- CI updated for new structure and expanded tests
- Tag release: MazeWorld V1.0

**Tests:**
- Exe launches and runs correctly
- Full integration test: generate -> play -> save -> load -> complete
- All three modes produce a complete game

**Done when:** `mazeworld_{seed}.exe` is a distributable, self-contained game that a player can download and play from start to finish.

---

### Phase Summary

| Phase | Name | Key Milestone |
|---|---|---|
| 1 | Foundation & Restructure | New structure, start screen, existing features intact |
| 2 | Player Classes & Stats | Character creation, class selection |
| 3 | Combat System | Turn-based combat functional |
| 4 | Items, Inventory & Shops | GenAI items, shops, money |
| 5 | Encounters & Monsters | Full encounter system with generated monsters |
| 6 | Quests, Story & Followers | Connected quests, overarching story, followers |
| 7 | Multi-Room & Progression | Room transitions, level-up, gate bosses, endgame |
| 8 | Fog of War & Day/Night | Exploration and time systems |
| 9 | Survival Rebalance & Screens | Balanced gameplay, all UI complete, save/load |
| 10 | Generation Pipeline & Validation | Agentic flow, World Bible, parallel generation |
| 11 | Packaging & Release | Exe bundling, final polish, V1.0 release |

**Deferred (post-V1):**
- Music generation (requires research spike)
- World gen GUI
- Mac MPS optimization
- Local mode exe size optimization

---

## 8. Success Criteria

**V1.0 is done when a player can:**

1. Launch `mazeworld_{seed}.exe` on a clean machine
2. See a start screen with New Game, Load Game, Tutorial, Quit
3. Start a new game, name their character, and select from 4 GenAI-generated classes themed to the environment
4. Enter the first room with an environment portrait and story introduction
5. Explore a fog-of-war maze, revealing paths, NPCs, and items as they move
6. Find and pick up environment-themed items (food, drink, tools, weapons, spell scrolls)
7. Talk to NPCs with GenAI dialogue that references the overarching story
8. Buy and sell items at NPC shops using money
9. Trigger invisible encounters: combat, puzzle, and event types
10. Fight environment-themed monsters in turn-based combat using melee, magic, items, and flee
11. Solve puzzles with tools/abilities and resolve events with stat checks
12. Accept and complete quests: fetch, kill, escort, delivery, dialogue, and multi-step chains
13. Manage followers via the player menu and complete escort quests
14. Experience day/night cycles that affect visibility, encounters, and NPC availability
15. Rest to recover stats at the cost of advancing time
16. Discover the exit door after clearing 40% of encounters or completing a revealing quest
17. Defeat a story-tied gate boss (or fail the gate with heavy penalty) to progress
18. Level up on room entry and select a new ability
19. Progress through N configurable rooms with escalating difficulty, different environments, and an overarching story
20. Defeat the final boss and see a victory screen with full stats summary
21. Save from the pause menu and load from the start screen or game over screen
22. Die and see a game over screen with option to load

**Generation criteria:**

23. `python main.py` generates a complete world using the agentic pipeline (generator -> checker -> validator -> world editor)
24. All three modes produce a playable game: offline_static, offline_local, online
25. World Bible is generated with all cross-references resolved and validated
26. No critical validation failures in the manifest
27. Generation runs with parallel API calls in online mode
28. Config settings (seed, story seed, room count, maze size, event density) all respected

**Quality criteria:**

29. Survival is challenging but not a grind — a competent player can complete the game without starving
30. Combat feels dice-driven and meaningful — not every encounter is trivial, not every encounter is deadly
31. The overarching story is coherent across all rooms — NPCs reference it, quests tie into it, the climax pays it off
32. Items, monsters, and NPCs feel themed to their environment — not generic
33. All existing tests pass plus new tests for every feature phase
34. CI runs lint + tests on every push
