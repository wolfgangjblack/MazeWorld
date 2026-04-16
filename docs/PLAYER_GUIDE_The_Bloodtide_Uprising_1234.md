# The Bloodtide Uprising

## Official Player Guide

<p align="center"><img src="../data/portraits/start_screen.png" width="300"/></p>

---

### Synopsis

The savage Bloodtide Clan has erupted from the depths of the sea caves, their crimson-painted warriors overwhelming the peaceful village of Saltwind Harbor with relentless fury. These aquatic goblins, twisted by generations in the underwater darkness, serve the ancient sea demon Kraken-Maw and seek to drown the entire coastline in blood and brine. You must venture into their flooded warren beneath the waves, navigating treacherous tidal chambers where seawater and shadow reign supreme. Only by confronting Tide-Caller Grix in the demon's unholy shrine can you end this aquatic nightmare before the Bloodtide's crimson tide consumes all.

*Story Seed: A local seaside village is under siege by a goblin horde*

---

<p align="center"><img src="../data/portraits/game_over.png" width="400"/></p>

---

## Table of Contents

1. [How to Play](#how-to-play)
2. [Combat Guide](#combat-guide)
3. [Character Classes](#character-classes)
4. [Quest Guide](#quest-guide)
5. [Room 0](#room-0)
6. [Room 1](#room-1)
7. [Damage Scaling](#scaling)
8. [Available Spell Pools](#spell-pools)
9. [Appendices](#appendices)
10. [Technical Details](#technical-details)
11. [Credits](#credits)

---

<a id="how-to-play"></a>

## How to Play

### Controls

#### Exploration

| Key | Action |
|-----|--------|
| Arrow Keys | Move through the maze |
| Enter | Pick up item / Talk to NPC |
| S | Open shop (when adjacent to a merchant) |
| I | Toggle inventory |
| Q | Toggle quest log |
| R | Open rest menu |
| T | Talk to follower |
| P | Open status screen |
| B | Story recap |
| Tab | Player menu (save/load/quests/followers) |
| Esc | Pause menu / Close overlay |
| F1 | Debug: reveal entire maze |

#### Combat

| Key | Action |
|-----|--------|
| Up / Down | Navigate menu options |
| Left / Right | Switch target |
| Enter | Confirm action |
| Esc | Back / Cancel sub-menu |
| Space | Advance after enemy turn |
| Tab | Toggle combat log |

#### Inventory

| Key | Action |
|-----|--------|
| Up / Down | Select item |
| Enter / U | Use item |
| E | Equip weapon |
| D | Item detail |
| Esc | Close inventory |

### Exploration & Fog of War

The maze is hidden under fog of war. As you move, nearby tiles are revealed and stay visible (but dimmed) when you move away. Your visibility radius depends on your WIS stat and the time of day:

- **Base radius:** 3 tiles + WIS modifier / 2
- **Dawn:** +1 bonus
- **Day:** +2 bonus
- **Dusk:** -1 penalty (negated by torch)
- **Night:** -2 penalty (negated by torch)

### Day/Night Cycle

The world cycles through four time periods:

| Period | Duration | Visibility | Notes |
|--------|----------|------------|-------|
| Dawn | 15% of cycle | +1 bonus | Transition period |
| Day | 35% of cycle | +2 bonus | Full visibility |
| Dusk | 15% of cycle | -1 penalty | Torch negates |
| Night | 35% of cycle | -2 penalty | Torch negates |

Time advances with each move and when resting. Some events and NPCs are **time-gated** — they only appear during the day or at night. There is a 8% chance of a random encounter per move at night.

### Torches

Any item with a **light** attribute acts as a torch. While you carry a lit torch, night and dusk visibility penalties are negated. Torches consume one use per move at night — keep spares in your inventory.

### Resting

Press **R** to open the rest menu:

| Duration | Effect |
|----------|--------|
| 3 hours | Small HP recovery, low stamina cost |
| 6 hours | Moderate HP recovery, moderate stamina cost |
| 12 hours | Large HP recovery, high stamina cost |

Resting advances the day/night clock. Combat also grants a small +5 HP rest without advancing time.

### Interacting with NPCs

- Walk adjacent to an NPC and press **Enter** to talk.
- NPCs have **day/night availability** — some only appear at certain times.
- Quest-giving NPCs will offer their quest during dialogue.
- Merchants: press **S** when adjacent to open the shop (buy/sell items).
- You cannot sell escort items to merchants.

### Items & Inventory

Items are found on the maze floor (press **Enter** to pick up) or bought from merchants. Item types:

| Type | Effect |
|------|--------|
| **Food** | Restores HP (base + CON mod) and stamina (base + 2×CON mod) |
| **Drink** | Same restoration formula as food |
| **Tool** | Applies a stamina effect; limited uses, breaks at 0 |
| **Weapon** | Equip to change your attack; see Combat Guide for categories |
| **Spell Scroll** | Jesters learn the spell permanently; others get a heal/stamina boost |
| **Escort Item** | Represents a follower NPC during escort quests (not consumable) |

Consumable items (food, drink, tools) scale in power by room level: 1.0x → 1.3x → 1.6x → 2.0x (rooms 1–4+).

### Room Progression & The Exit Door

Each room has a hidden exit door. It is revealed once you clear **40%** of the room's encounters (or a quest reward reveals it). The door may be guarded by a **gate encounter** — a mandatory fight you must win before proceeding.

Completing all rooms wins the game. Between rooms you get a **level up**, where you choose a new ability or spell from your class's unlock pool.

Story quests will warn you at the door if they're still incomplete.

### Save & Load

Open the **Tab** menu or **Pause** menu (Esc) to access Save/Load. Saves preserve your full game state: player, inventory, maze, fog, day/night cycle, quests, NPCs, events, and followers.

---

<a id="combat-guide"></a>

## Combat Guide

### Initiative & Turn Order

When combat begins, each combatant rolls initiative:

- **Player:** `1d20 + DEX modifier`
- **Monsters:** `1d20 + dex_mod`

Combatants are sorted highest to lowest. Ties favor the player. The turn order is shown in the top-right of the combat screen.

### Melee Attacks

**To-hit roll:** `1d20 + weapon_stat_bonus + (level - 1)` vs **DC:** `target AC + target DEX modifier`

- The stat used depends on weapon type (see Weapon Types below).
- On hit: `1d{weapon_dice} + stat_bonus` base damage.
- Physical and elemental multipliers are then applied (see below).
- Minimum 1 damage on a hit.

**Stat bonuses by archetype:**

| Archetype | Weapon Category Access | Stat Bonus Rule |
|-----------|----------------------|-----------------|
| Warrior | simple + martial | Full stat modifier |
| Mage | simple only | Full stat modifier (0 on martial) |
| Healer | simple only | Full stat modifier (0 on martial) |
| Jester | simple + martial | Average of LUCK mod and weapon stat mod |

Mages and healers **cannot equip** martial weapons at all.

### Physical Damage Triangle

Every weapon has a physical damage type, and every monster has a physical type. Damage is multiplied based on the matchup:

```
  Slashing  →  Piercing  →  Bludgeoning  →  Slashing
     ↑              ↑              ↑
   1.5x           1.5x           1.5x        (super effective)
   0.5x ←         0.5x ←         0.5x ←      (resisted)
```

| Attack Type | Strong Against | Weak Against |
|-------------|---------------|--------------|
| Slashing | Piercing (1.5x) | Bludgeoning (0.5x) |
| Piercing | Bludgeoning (1.5x) | Slashing (0.5x) |
| Bludgeoning | Slashing (1.5x) | Piercing (0.5x) |

Monsters also attack the player using this triangle — a monster's physical type is compared against your weapon's damage type to determine damage dealt to you.

### Elemental Advantage Chart

Spells and magic weapons have an element. Elemental matchups use the same 1.5x / 0.5x multipliers:

```
  Fire  →  Forest  →  Water  →  Fire

  Light  ↔  Dark   (mutual advantage: both deal 1.5x to each other)
```

| Attack Element | Strong Against | Weak Against |
|---------------|---------------|--------------|
| Fire | Forest (1.5x) | Water (0.5x) |
| Forest | Water (1.5x) | Fire (0.5x) |
| Water | Fire (1.5x) | Forest (0.5x) |
| Light | Dark (1.5x) | Dark (1.5x) |
| Dark | Light (1.5x) | Light (1.5x) |

Weapons with a `magic_element` apply **both** the physical and elemental multipliers on a single attack.

### Weapon Types

| Type | Scaling Stat | Notes |
|------|-------------|-------|
| Heavy | STR | Warrior primary; high dice (1d8–1d10) |
| Light | DEX | Fast; lower dice (1d4–1d6) |
| Simple | STR or INT | Mage/healer weapons (1d4–1d6) |
| Wild | Random (STR/DEX/INT) | Jester weapons; stat re-rolls each attack |

**Weapon categories:** `simple` (any class) vs `martial` (warrior/jester only). Mages and healers get **0 stat bonus** and cannot equip martial weapons.

Combat UI shows weapon tags like `[slashing]` or `[slashing + fire]` on attack previews so you can see your damage types at a glance.

### Spells

| Spell Type | Effect | Cost |
|------------|--------|------|
| `heal` | Restores HP (heal_amount or random 4–12) | 5 stamina |
| `buff_stat` | Buffs a stat for 1d4 + INT_mod/2 turns (min 1) | 3 stamina |
| `buff_sustain` | Restores +3 stamina immediately | 2 stamina |
| `damage_single` | Magic damage to one target | Varies by dice |
| `damage_multi` | Magic damage to all targets | 2x single cost (max 10) |

**Damage spell cost by dice:** d4 = 2, d6 = 4, d8 = 5, d10 = 7 stamina.

**Magic attack roll:** Player rolls `magic attack` vs DC `10 + target magic_resistance`. Damage is `1d{spell_dice}` × elemental multiplier.

### Class-Specific Combat Actions

#### Warrior: Multi-Attack

- Costs **6 stamina**.
- Rolls one attack against **every living monster**.
- Uses stepped-down weapon dice (e.g. 1d8 → 1d6) for balance.
- Physical and elemental multipliers still apply to each hit.

#### Jester: Gamble

A LUCK-weighted random outcome. Higher LUCK shifts odds toward good results:

- Random damage to a monster
- Self-heal
- Random stat buff
- Self-damage (bad luck!)
- Enemy AC debuff (−2 for 3 turns)
- Nothing happens
- Wild elemental damage

#### Weapon Swap

Uses your turn. Swaps to the first other weapon in your inventory. Category restrictions apply (mages/healers cannot swap to martial weapons).

### Fleeing

- Roll: `1d20 + DEX` vs `12 + highest monster level`
- **Success:** You escape combat.
- **Failure:** The strongest monster gets a **free attack** on you.
- You **cannot flee** from gate encounters or climax bosses.

### Items in Combat

Only **food** and **drink** can be used during combat. Using an item consumes your turn.

### Monster Abilities

Some monsters (especially in gate encounters) have special abilities:

| Ability Type | Effect |
|-------------|--------|
| Damage | Extra damage on top of normal attack |
| Poison | Damage over time for several turns |
| Stun | Skip the player's next turn |

Each ability has a **chance** to activate and a **duration** for ongoing effects. Check the Bestiary for each monster's abilities.

### Player AC

Your armor class: `10 + armor + DEX modifier`. Buffs to DEX from spells are included. Monsters must beat your AC to hit you.

---

<a id="character-classes"></a>

## Character Classes

There are four archetypes, each with a 95-point stat budget distributed across STR, DEX, CON, INT, WIS, CHA, and LUCK. At level up (between rooms), you choose a new ability or spell from your class's unlock pool.

<table><tr>
<td width="220"><img src="../data/portraits/classes/class_0.png" width="200"/></td>
<td>
<h3>Harbor Guard</h3>
<b>Archetype:</b> warrior<br/>
<b>Starting Weapon:</b> Iron Cutlass<br/>
<b>Weapon Access:</b> simple + martial<br/><br/>
**STR** 18 | **DEX** 14 | **CON** 16 | **INT** 10 | **WIS** 11 | **CHA** 16 | **LUCK** 10
</td>
</tr></table>

> *Seasoned defenders of Saltwind Harbor's docks and gates. They've weathered countless storms and repelled raiders with unwavering courage.*

#### Abilities

| Name | Description | Stat | Stamina |
|------|-------------|------|---------|
| Shatter Defense | Channel fiery determination to break through enemy armor, doors, or barriers with devastating force. | STR | 8 |
| Dock Brawler's Glare | Strike fear into opponents with the hardened stare of someone who's survived countless waterfront fights. | CHA | 3 |
| Burning Bash | Deliver a crushing blow infused with inner fire, stunning enemies with both impact and searing heat. | STR | 5 |
| Harbor's Call | Inspire allies with the rallying cry that has defended Saltwind Harbor through its darkest hours. | CHA | 5 |

#### Unlockable Pool

| Name | Description | Stat | Stamina |
|------|-------------|------|---------|
| Rigging Climb | Scale masts, walls, and cliffs with the expertise gained from years working harbor rigging. | STR | 4 |
| Storm Sense | Detect approaching danger with the intuition of one who watches the harbor's horizon. | WIS | 3 |
| Anchor Hold | Grapple enemies with the unbreakable grip of someone who secures heavy ship anchors. | STR | 6 |
| Beacon's Roar | Release a thunderous battle cry that cuts through wind and wave to inspire all who hear it. | CHA | 7 |


<table><tr>
<td width="220"><img src="../data/portraits/classes/class_1.png" width="200"/></td>
<td>
<h3>Grove Keeper</h3>
<b>Archetype:</b> mage<br/>
<b>Starting Weapon:</b> Thornwood Staff<br/>
<b>Weapon Access:</b> simple only<br/><br/>
**STR** 11 | **DEX** 16 | **CON** 12 | **INT** 18 | **WIS** 16 | **CHA** 11 | **LUCK** 11
</td>
</tr></table>

> *Guardians of the ancient woodlands surrounding Saltwind Harbor. They commune with forest spirits to protect both nature and the village from harm.*

#### Spells

| Name | Type | Element | Damage | Targets | Stamina | Description |
|------|------|---------|--------|---------|---------|-------------|
| Thorn Bolt | damage_single | forest | 1d6 | single | 4 | Launch a sharp projectile of hardened thorns at a single enemy. |
| Vine Lash | damage_single | forest | 1d6 | single | 4 | Command forest vines to strike out and wound a target. |
| Bramble Burst | damage_multi | forest | 1d4 | multi | 6 | Summon an explosion of thorny brambles that damages all nearby enemies. |
| Bark Skin | buff_stat | forest | — | self | 2 | Harden your skin like tree bark, increasing your natural defenses. |

#### Unlockable Pool

| Name | Type | Element | Targets | Stamina | Description |
|------|------|---------|---------|---------|-------------|
| Root Spear | damage_single | forest | single | 4 | Cause a massive root to erupt from the ground and impale a single target. |
| Forest's Wrath | damage_multi | forest | multi | 8 | Unleash the fury of the woodland, striking multiple enemies with nature's vengeance. |
| Photosynthesis | buff_stat | forest | self | 2 | Draw energy from sunlight and earth to enhance your magical abilities. |
| Woodland Ward | buff_sustain | forest | self | 2 | Surround yourself with protective forest magic that deflects attacks over time. |


<table><tr>
<td width="220"><img src="../data/portraits/classes/class_2.png" width="200"/></td>
<td>
<h3>Tide Caller</h3>
<b>Archetype:</b> healer<br/>
<b>Starting Weapon:</b> Coral Trident<br/>
<b>Weapon Access:</b> simple only<br/><br/>
**STR** 11 | **DEX** 11 | **CON** 16 | **INT** 12 | **WIS** 18 | **CHA** 16 | **LUCK** 11
</td>
</tr></table>

> *Blessed servants of the sea who channel the healing power of ocean tides. They ensure Saltwind Harbor's fishermen and sailors return safely from their voyages.*

#### Spells

| Name | Type | Element | Damage | Targets | Stamina | Description |
|------|------|---------|--------|---------|---------|-------------|
| Soothing Waves | heal | water | 1d6 | self | 5 | Channel gentle ocean currents to heal your wounds and restore vitality. |
| Sea Blessing | buff_stat | water | — | self | 2 | Invoke the ocean's favor to temporarily enhance your natural abilities. |
| Crushing Depth | damage_single | water | 1d6 | single | 4 | Strike an enemy with the overwhelming pressure of deep ocean waters. |
| Tidal Shield | buff_sustain | water | — | self | 2 | Surround yourself with a protective barrier of swirling seawater. |

#### Unlockable Pool

| Name | Type | Element | Targets | Stamina | Description |
|------|------|---------|---------|---------|-------------|
| Healing Tsunami | heal | water | self | 6 | Summon a powerful wave of restorative energy to mend severe injuries. |
| Maelstrom Strike | damage_single | water | single | 5 | Unleash a devastating whirlpool of water magic against a single foe. |
| Ocean's Embrace | buff_stat | water | self | 2 | Draw upon the sea's endless strength to bolster your inner power. |
| Tempest's Fury | damage_multi | water | multi | 12 | Call forth a raging storm that batters all enemies with torrential force. |


<table><tr>
<td width="220"><img src="../data/portraits/classes/class_3.png" width="200"/></td>
<td>
<h3>Tavern Fool</h3>
<b>Archetype:</b> jester<br/>
<b>Starting Weapon:</b> Jester's Bell Mace<br/>
<b>Weapon Access:</b> simple + martial<br/><br/>
**STR** 13 | **DEX** 13 | **CON** 14 | **INT** 12 | **WIS** 13 | **CHA** 15 | **LUCK** 15
</td>
</tr></table>

> *Wandering entertainers who bring laughter to Saltwind Harbor's taverns and festivals. Their unpredictable nature often leads to surprising victories in the most unlikely situations.*

#### Abilities

| Name | Description | Stat | Stamina |
|------|-------------|------|---------|
| Burning Bash | Deliver a crushing blow infused with inner fire, stunning enemies with both impact and searing heat. | STR | 5 |

#### Spells

| Name | Type | Element | Damage | Targets | Stamina | Description |
|------|------|---------|--------|---------|---------|-------------|
| Bramble Burst | damage_multi | forest | 1d4 | multi | 6 | Summon an explosion of thorny brambles that damages all nearby enemies. |
| Sea Blessing | buff_stat | water | — | self | 2 | Invoke the ocean's favor to temporarily enhance your natural abilities. |


<a id="quest-guide"></a>

## Quest Guide

### Quest Types

| Type | Objective |
|------|-----------|
| Fetch | Find an item at a specific tile and return it to the quest giver |
| Delivery | Carry a specific item to a target NPC |
| Escort | Escort a follower NPC safely to a target zone |
| Combat | Defeat a specific combat encounter |
| Solve | Complete a specific puzzle or event |
| Dialogue | Pass a CHA-based conversation challenge |
| Multi-Step | Complete an ordered chain of sub-quests |

### Accepting & Completing Quests

1. Walk to the quest-giving NPC and press **Enter** to talk.
2. The quest is offered during dialogue — accept to activate it.
3. Complete the objective (see type-specific details in each room's Quest Walkthrough section).
4. For fetch and delivery quests, return to the appropriate NPC to turn in.
5. Combat and solve quests complete automatically when the linked event resolves.

### Prerequisites

Some quests require completing a previous quest before they become available. The quest giver won't offer the quest until the prerequisite is done.

### Story Quests

Quests marked as **story quests** are tied to the overarching narrative. If you try to leave a room with an incomplete story quest, you'll get a warning at the exit door.

### Followers & Escort Quests

- You can have up to **2 followers** at a time.
- When you accept an escort quest, the NPC joins as a follower and an **escort item** is added to your inventory.
- Guide the follower to within **2 tiles** of the target zone to complete.
- Press **T** at any time to talk to your follower for a hint.
- **Warning:** If you advance past a follower's destination room, they leave and the quest **fails** with a penalty.

### Rewards & Penalties

**Possible rewards:**

- Items (added to inventory)
- Gold
- Story information
- Exit door reveal

**Failure penalties:**

- HP damage
- Stamina damage

Completing or failing a quest changes the giver NPC's dialogue to reflect the outcome.

---

<a id="room-0"></a>

## Room 0: Saltwind Harbor
*Environment: village — Level 1*

<p align="center"><img src="../data/portraits/environment_0.png" width="500"/></p>

### Room Introduction

You emerge into chaos as crimson-painted goblins swarm through Saltwind Harbor like a living tide, their webbed claws scraping against cobblestones slick with seawater and blood. The acrid stench of brine and terror fills the air while panicked screams echo from the moonlit docks, where families flee desperately toward the lighthouse's beckoning beam. Behind you, the crash of waves mingles with inhuman shrieks as more Bloodtide raiders surge from storm drains and tidal pools, their gill-slits fluttering with savage hunger.

### Story Beat

Saltwind Harbor is under siege as Bloodtide goblins pour from storm drains and tide pools throughout the village, their crimson-painted bodies glistening in the moonlight. Captain Merrick rallies the town guard at the harbor's edge while Elder Thessa barricades survivors in the lighthouse, but the goblins' amphibious assault has caught everyone off-guard. Scout Finwick has just returned with horrifying news: the raids are coordinated, emerging from a vast underwater warren beneath the cliffs. As screams echo from the docks where families are being dragged into the churning waters, the village's fate hangs by a thread.

### Faction Presence

The Bloodtide Clan has emerged from hidden tide pools and storm drains throughout the village, using their amphibious nature to appear where least expected. They are systematically capturing villagers and dragging them toward the water while establishing staging points near any connection to the sea.

### Boss: Bloodsurge Krex

> *A hulking goblin champion whose gills flap wetly as he breathes, wielding a trident crackling with electric energy. Barnacle growths cover his shoulders like armor plates.*

### Level Map

<p align="center"><img src="../data/portraits/maps/room_0_map.png" /></p>

### Item Catalog

| ID | Name | Category | Description | Stats |
|----|------|----------|-------------|-------|
| 2000 | salted cod strips | food | Dried fish prepared for the harbor watch's long shifts. | +8 stamina, +1 HP, 1 uses, 12g |
| 2001 | kelp bread | food | Dense bread made with seaweed flour, a village staple. | +8 stamina, +5 HP, 1 uses, 6g |
| 2002 | storm rations | food | Hard biscuits packed for siege conditions. | +13 stamina, +6 HP, 1 uses, 8g |
| 2003 | tide pool mussels | food | Shellfish harvested before the goblin raids began. | +5 stamina, +3 HP, 1 uses, 10g |
| 2004 | harbor grog | drink | Strong rum mixed by dockworkers to ward off sea chills. | +10 stamina, +2 HP, 1 uses, 12g |
| 2005 | lighthouse brew | drink | Elder Thessa's bitter tea, said to sharpen night vision. | +15 stamina, +1 HP, 1 uses, 5g |
| 2006 | rainwater | drink | Fresh water collected from the storm that preceded the attack. | +9 stamina, +6 HP, 1 uses, 12g |
| 2007 | medicinal kelp wine | drink | Fermented seaweed drink used to treat wounds. | +12 stamina, +3 HP, 1 uses, 10g |
| 2008 | dock hook | tool | Iron hook used to pull nets and boats from Kraken-Maw's depths. | +-5 stamina, 3 uses, 19g |
| 2009 | rope and grapnel | tool | Climbing gear salvaged from Captain Merrick's ship. | +-5 stamina, 3 uses, 19g |
| 2010 | tide scraper | tool | Tool for harvesting barnacles, now weaponized against invaders. | +-5 stamina, 3 uses, 21g |
| 2011 | tide-touched trident | weapon | A ceremonial spear that sparks with residual sea magic. | 1d4 dmg, arcane, piercing, INT, 11g |
| 2012 | driftwood cudgel | weapon | Makeshift club carved from storm-tossed wood. | 1d6 dmg, wild, bludgeoning, LUCK, 20g |
| 2013 | harbor guard cutlass | weapon | Standard-issue blade of Saltwind's coastal defenders. | 1d8 dmg, heavy, slashing, STR, 35g |
| 2014 | fisherman's gutting knife | weapon | A curved blade designed for cleaning the day's catch. | 1d6 dmg, light, piercing, DEX, 18g |
| 2015 | lighthouse keeper's blessed mace | weapon | Elder Thessa's ritual weapon, inscribed with protective wards. | 1d6 dmg, sacred, bludgeoning, CON, 17g |
| 2016 | storm caller's rod | weapon | A barnacle-encrusted staff that hums with electric potential. | 1d4 dmg, arcane, piercing, INT, 8g |
| 2017 | scroll of tidal ward | spell_scroll | Creates a barrier of churning seawater around the caster. | 31g |
| 2018 | scroll of deep sight | spell_scroll | Grants vision through murky water and goblin illusions. | 37g |

### NPC Directory

<a id="room_0-npc-1000"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1000.png" width="200"/></p>

#### Corwin Saltbeard

**Job:** fisherman hiding behind overturned boat<br/>**Type:** StaticNPC<br/>**Personality:** shell-shocked and trembling, keeps muttering about his missing nets

> *Corwin was hauling in his evening catch when the first wave of Bloodtide goblins erupted from the tidal pools near his mooring. He watched in horror as they dragged his boat partner Jem screaming into the surf before scrambling to safety behind his overturned dinghy. The old fisherman has been paralyzed with fear ever since, clutching a bloodied gaff hook and jumping at every sound of splashing water.*

**Opening Greeting:**
> "My nets... they took my nets! Twenty years I've been casting those waters, and now... now they're all gone!"


<a id="room_0-npc-1001"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1001.png" width="200"/></p>

#### Mira Tidecaller

**Job:** village healer trapped with wounded<br/>**Type:** RandomNPC<br/>**Personality:** desperately trying to keep panic at bay while tending to goblin attack victims

> *Mira was in her seaside clinic when the attack began, treating a fisherman's infected cut. When the goblins smashed through her window, she barely managed to drag her patients into the back room and barricade the door. She's been using her last supplies to keep the wounded stable, but knows they'll die if they don't reach the safety of the lighthouse soon. The healer has seen the goblin's barnacle-encrusted claws and knows their wounds will fester without proper treatment.*

**Opening Greeting:**
> "Thank the tides you're here! I've got three people with goblin bites and the bleeding won't stop - something's wrong with their claws!"

**Quest:** [4000](#4000)


<a id="room_0-npc-1002"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1002.png" width="200"/></p>

#### Scout Finwick

**Job:** village scout with crucial intelligence<br/>**Type:** RandomNPC<br/>**Personality:** urgent and breathless, desperate to share what he's discovered

> *Finwick was investigating reports of missing fishing boats when he discovered the entrance to the Bloodtide warren during low tide. He spent hours crawling through partially flooded tunnels, witnessing their preparation chambers where goblins daub themselves in crimson algae before raids. Deep in the complex, he glimpsed an ancient shrine where something massive stirred in the darkness. He barely escaped with his life when the tide turned, and now realizes the village faces more than just raiders - they're dealing with an organized army serving something ancient and terrible.*

**Opening Greeting:**
> "Listen to me - this isn't just a raid! I've seen their warren beneath the cliffs, it's massive! They've been planning this for months!"

**Quest:** [4001](#4001)


<a id="room_0-npc-1003"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1003.png" width="200"/></p>

#### Captain Merrick

**Job:** town guard captain organizing the defense<br/>**Type:** AggressiveNPC<br/>**Personality:** battle-hardened but overwhelmed, shouting orders while fighting on two fronts

> *Merrick has defended Saltwind Harbor from pirates and sea monsters for fifteen years, but nothing prepared him for amphibious raiders emerging from every storm drain and tide pool simultaneously. He's watched half his guard dragged screaming into the surf while trying to establish a defensive line at the docks. The captain knows from Finwick's report that this is just the first wave, and he needs heroes to strike at their source before the entire warren empties into his village.*

**Opening Greeting:**
> "Form ranks on me! We hold this harbor or the whole village falls! You there - can you fight?"

**Quest:** [4002](#4002)


<a id="room_0-npc-1004"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1004.png" width="200"/></p>

#### Tam Reefsong

**Job:** tavern keeper guarding supplies<br/>**Type:** RandomNPC<br/>**Personality:** protective of his ale stores, suspicious of anyone approaching his cellar

> *Tam barricaded himself in the Salty Dog tavern when the goblins attacked, but several of the creatures forced their way up through his cellar drain. He managed to trap them in the lower level, but they're still down there making awful gurgling sounds among his beer barrels. The tavern keeper has food and medical supplies the defenders desperately need, but won't risk opening his cellar until someone deals with the goblin infiltrators.*

**Opening Greeting:**
> "Stay back from my cellar! I've got supplies down there that'll keep us alive when this madness ends!"

**Quest:** [4003](#4003)


<a id="room_0-npc-1005"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1005.png" width="200"/></p>

#### Nessa Driftwood

**Job:** rope maker whose workshop overlooks the harbor<br/>**Type:** StaticNPC<br/>**Personality:** sharp-eyed and practical, has been watching the battle unfold

> *Nessa was working late in her rope workshop when the attack began, giving her a perfect view of the harbor from her second-story window. She's been tracking the goblins' movements and noticed they're not randomly attacking - they seem to be targeting village leaders and skilled craftsmen for capture rather than killing. She's counted at least six prominent citizens dragged toward what appears to be a staging area near the old sea wall.*

**Opening Greeting:**
> "From up here I can see the whole battle - those crimson devils are coming from everywhere! The storm drains, the tide pools, even the old pier supports!"


<a id="room_0-npc-1006"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1006.png" width="200"/></p>

#### Elder Thessa

**Job:** village elder coordinating the lighthouse evacuation<br/>**Type:** RandomNPC<br/>**Personality:** calm under pressure but urgently protective of the survivors under her care

> *Thessa was lighting the evening beacon when the Bloodtide assault began, immediately recognizing that the lighthouse's elevated position made it the safest refuge in the village. She's managed to evacuate thirty-seven people so far, including several children whose parents were taken by the goblins. The elder knows the lighthouse stores could sustain her group for days, but she's tormented by the survivors still trapped in the lower village who need someone to guide them to safety.*

**Opening Greeting:**
> "Blessed be, another soul reaches safety! Quickly now - help me get these children up the lighthouse stairs before the next wave hits!"

**Quest:** [4004](#4004)


<a id="room_0-npc-1007"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1007.png" width="200"/></p>

#### Young Willem

**Job:** baker's apprentice separated from his master<br/>**Type:** RandomNPC<br/>**Personality:** frightened but trying to be brave, clutching a rolling pin as a weapon

> *Willem was closing the bakery for the night when Bloodtide goblins crashed through the front window, seizing his master and dragging the struggling baker toward the waterfront. The apprentice managed to hide among the grain sacks until the creatures left, emerging to find the shop destroyed and his mentor gone. He's been clutching his rolling pin like a club ever since, desperate to help rescue Master Aldric but too frightened to venture toward the warehouse district alone.*

**Opening Greeting:**
> "Have you seen Master Orin? The goblins came through the bakery window and I... I lost him in the smoke!"

**Quest:** [4005](#4005)


<a id="room_0-npc-1008"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1008.png" width="200"/></p>

#### Granny Saltborn

**Job:** elderly net mender who saw the first emergence<br/>**Type:** StaticNPC<br/>**Personality:** cantankerous but sharp-minded, claims she predicted this disaster

> *Granny Saltborn was mending nets on her porch when she witnessed the first goblins emerge from the storm drains just after sunset. She's spent fifty years reading the signs - unusual tides, dead fish washing ashore with strange bite marks, and the way her nets kept coming back shredded from the deep water. The old woman has been predicting some kind of underwater threat for months, and now takes grim satisfaction in being proven right even as her village burns around her.*

**Opening Greeting:**
> "I told 'em this would happen! Sixty years I've been warning about stirring up the deep waters, but did anyone listen?"


<a id="room_0-npc-1009"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1009.png" width="200"/></p>

#### Kael Bonecaster

**Job:** shipwright trapped in his workshop<br/>**Type:** StaticNPC<br/>**Personality:** methodical and stubborn, refuses to abandon his life's work

> *Kael was fitting new rigging on a fishing vessel when the Bloodtide goblins swarmed his shipyard, immediately setting fires to several boats with their crude torches. He managed to barricade himself in his workshop with his most valuable tools, but the goblins keep probing his defenses, drawn by the scent of fresh timber and tar. The shipwright knows his yard represents the village's entire maritime economy, and he's determined to protect what he can even if it costs him his life.*

**Opening Greeting:**
> "You want me to abandon my workshop? Thirty years I've built ships here - I'm not running from some overgrown fish-goblins!"


<a id="room_0-npc-1010"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1010.png" width="200"/></p>

#### Senna Pearlsight

**Job:** pearl diver who knows the underwater caves<br/>**Type:** StaticNPC<br/>**Personality:** breathless with terror from her narrow escape, but possesses crucial knowledge

> *Senna barely escaped with her life when she encountered Bloodtide scouts in the underwater caves during her morning pearl dive. She discovered fresh excavations in passages she'd explored for years, with walls covered in disturbing carvings that seemed to writhe when viewed directly. The pearl diver realizes her intimate knowledge of the cave system could be crucial for any attempt to attack the goblins' warren, but she's still shaking from the memory of webbed hands grasping for her in the murky depths.*

**Opening Greeting:**
> "I barely escaped their caves alive! The tunnels go deeper than anyone imagined, and there's something ancient down there... something hungry!"


<a id="room_0-npc-1011"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1011.png" width="200"/></p>

#### Marcus Ironstock

**Job:** weapons merchant selling to desperate defenders<br/>**Type:** MerchantNPC<br/>**Personality:** opportunistic but not cruel, genuinely wants the village to survive

> *Marcus was preparing to leave Saltwind Harbor with the morning tide when the Bloodtide assault trapped him in the village. His cart is loaded with weapons intended for the markets in Westport, but he's decided to arm the defenders at cost rather than watch the village fall. The merchant has extensive experience with maritime conflicts and recognizes the quality of the goblins' coral weapons, realizing this isn't a random raid but a coordinated military action.*

**Opening Greeting:**
> "Weapons! Get your weapons here! Special rate for the emergency - only twice the usual price!"

**Shop Inventory:**

| Item | Price | Stock |
|------|-------|-------|
| tide pool mussels | 10g | 1 |
| rope and grapnel | 19g | 4 |
| rainwater | 12g | 1 |
| lighthouse brew | 5g | 3 |
| scroll of deep sight | 37g | 3 |
| salted cod strips | 12g | 2 |
| harbor grog | 12g | 4 |


<a id="room_0-npc-1012"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1012.png" width="200"/></p>

#### Father Tiderick

**Job:** village priest tending to the wounded in the chapel<br/>**Type:** StaticNPC<br/>**Personality:** steady presence trying to maintain hope while secretly terrified

> *Father Tiderick was conducting evening prayers when the first screams echoed from the harbor. He immediately opened the chapel as a sanctuary, but several of the refugees he's sheltering have severe wounds from goblin attacks. The priest has done what he can with basic first aid, but knows his flock needs a real healer and protection from the increasingly bold raiders who keep testing his barricaded doors.*

**Opening Greeting:**
> "Come, my child, take shelter in the chapel. The blessed walls still offer some protection against these cursed creatures."


<a id="room_0-npc-1013"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1013.png" width="200"/></p>

#### Ivy Stormwatch

**Job:** herbalist and potion maker<br/>**Type:** MerchantNPC<br/>**Personality:** businesslike even in crisis, has useful supplies but expects fair payment

> *Ivy was gathering night-blooming kelp from the tidal pools when she spotted the first goblin raiders emerging from deeper waters. She managed to retreat to her shop with a warning, and has since been brewing healing potions as fast as her supplies allow. The herbalist knows her remedies are essential for treating the infected wounds caused by goblin claws, but she's also practical enough to charge fair prices even during the crisis.*

**Opening Greeting:**
> "Healing potions, antidotes, and blade oils - all still available despite the circumstances! Coin or valuable trade only."

**Shop Inventory:**

| Item | Price | Stock |
|------|-------|-------|
| salted cod strips | 12g | 1 |
| dock hook | 19g | 4 |
| tide scraper | 21g | 3 |
| lighthouse brew | 5g | 3 |
| kelp bread | 6g | 4 |
| tide-touched trident | 11g | 1 |
| fisherman's gutting knife | 18g | 3 |


<a id="room_0-npc-1014"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1014.png" width="200"/></p>

#### Old Henrik

**Job:** lighthouse keeper's assistant who lost his lantern<br/>**Type:** StaticNPC<br/>**Personality:** guilt-ridden over his failure, desperate to make amends somehow

> *Henrik was carrying oil to refuel the lighthouse beacon when he witnessed Bloodtide goblins scaling the sea cliffs with impossible agility. The sight so unnerved him that he dropped his oil cask, causing the beacon to flicker out just as ships were trying to navigate away from the harbor. The assistant keeper blames himself for any vessels that might have run aground in the darkness, and is consumed with guilt over his moment of panic.*

**Opening Greeting:**
> "The lantern... I dropped the lighthouse lantern when they came up from the water! Without it, ships won't see the warning!"


<a id="room_0-npc-1015"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1015.png" width="200"/></p>

#### Jora Saltmane

**Job:** stable master worried about her horses<br/>**Type:** StaticNPC<br/>**Personality:** fierce protector of her animals, speaks to them more easily than people

> *Jora was bedding down her horses when the Bloodtide assault began, and the animals immediately began showing extreme distress at scents carried on the sea wind. She's managed to keep most of her stock calm through soothing words and familiar routines, but knows the horses will be essential for evacuation or carrying messages to neighboring settlements. The stable master has spent her life reading animal behavior and recognizes that her horses' terror goes beyond simple fear - they're reacting to something primal and wrong about the goblin presence.*

**Opening Greeting:**
> "My horses are going mad with terror - they can smell those creatures' stench on the wind and I can barely keep them from breaking down their stall doors."


### Monster Bestiary

<table><tr>
<td width="220"><img src="../data/portraits/monsters/mon_bloodsurge_krex.png" width="200"/></td>
<td>
<h3>Bloodsurge Krex</h3>
<b>Species:</b> goblin champion<br/>
<b>Level:</b> 1<br/>
<b>HP:</b> 32-42 &nbsp; <b>AC:</b> 14-16<br/>
<b>Damage:</b> 1d4/1d6 water<br/>
<b>Physical Type:</b> piercing<br/>
<b>Element:</b> water<br/>
<b>Weakness:</b> forest<br/>
<b>Magic Resist:</b> 0<br/>
<b>Encounters:</b> 1 &nbsp; <b>Rooms:</b> room_0
</td>
</tr></table>

> *A towering goblin whose barrel chest heaves as gills flutter along his thick neck. Barnacle clusters form natural armor across his shoulders while electricity arcs between his trident's prongs.*

**Abilities:**

- **Lightning Trident** (damage) — 1d8 dmg, 40% chance
- **Tidal Slam** (stun) — 1d4 dmg, 30% chance
- **Kraken's Wrath** (damage) — 1d6 dmg, 20% chance


<table><tr>
<td width="220"><img src="../data/portraits/monsters/mon_bloodtide_raider.png" width="200"/></td>
<td>
<h3>Bloodtide Raider</h3>
<b>Species:</b> amphibious goblin<br/>
<b>Level:</b> 1<br/>
<b>HP:</b> 6-10 &nbsp; <b>AC:</b> 11-13<br/>
<b>Damage:</b> 1d4/1d6 physical<br/>
<b>Physical Type:</b> slashing<br/>
<b>Element:</b> water<br/>
<b>Weakness:</b> fire<br/>
<b>Magic Resist:</b> 0<br/>
<b>Encounters:</b> 15 &nbsp; <b>Rooms:</b> room_0
</td>
</tr></table>

> *A lean goblin with gills behind pointed ears and webbed fingers, body painted with crimson algae. Water drips constantly from its scaled skin as it screeches battle cries.*

**Abilities:**

- **Tide Rush** (damage) — 1d4 dmg, 30% chance


<table><tr>
<td width="220"><img src="../data/portraits/monsters/mon_cave_crawler.png" width="200"/></td>
<td>
<h3>Cave Crawler</h3>
<b>Species:</b> deep spider<br/>
<b>Level:</b> 1<br/>
<b>HP:</b> 10-14 &nbsp; <b>AC:</b> 12-14<br/>
<b>Damage:</b> 1d4/1d6 physical<br/>
<b>Physical Type:</b> piercing<br/>
<b>Element:</b> None<br/>
<b>Weakness:</b> fire<br/>
<b>Magic Resist:</b> 0<br/>
<b>Encounters:</b> 10 &nbsp; <b>Rooms:</b> room_0
</td>
</tr></table>

> *A massive spider with a wet, glistening carapace that reflects moonlight. Its legs end in sharp points that click against stone as it moves through the flooded passages.*

**Abilities:**

- **Web Spray** (stun) — 0d0 dmg, 30% chance
- **Venom Bite** (poison) — 1d4 dmg, 20% chance


<table><tr>
<td width="220"><img src="../data/portraits/monsters/mon_coral-crusted_shambler.png" width="200"/></td>
<td>
<h3>Coral-Crusted Shambler</h3>
<b>Species:</b> corrupted villager<br/>
<b>Level:</b> 1<br/>
<b>HP:</b> 12-16 &nbsp; <b>AC:</b> 9-11<br/>
<b>Damage:</b> 1d4/1d6 water<br/>
<b>Physical Type:</b> bludgeoning<br/>
<b>Element:</b> water<br/>
<b>Weakness:</b> fire<br/>
<b>Magic Resist:</b> 0<br/>
<b>Encounters:</b> 9 &nbsp; <b>Rooms:</b> room_0
</td>
</tr></table>

> *A bloated human figure encrusted with barnacles and sea anemones. Saltwater pours from its mouth as it lurches forward, coral growths sprouting from its joints.*

**Abilities:**

- **Brine Spit** (poison) — 1d3 dmg, 40% chance


<table><tr>
<td width="220"><img src="../data/portraits/monsters/mon_tidecaller_grunt.png" width="200"/></td>
<td>
<h3>Tidecaller Grunt</h3>
<b>Species:</b> goblin cultist<br/>
<b>Level:</b> 1<br/>
<b>HP:</b> 8-12 &nbsp; <b>AC:</b> 10-12<br/>
<b>Damage:</b> 1d4/1d6 water<br/>
<b>Physical Type:</b> bludgeoning<br/>
<b>Element:</b> water<br/>
<b>Weakness:</b> light<br/>
<b>Magic Resist:</b> 0<br/>
<b>Encounters:</b> 9 &nbsp; <b>Rooms:</b> room_0
</td>
</tr></table>

> *A goblin adorned with shells and seaweed, chanting in gurgling tones while clutching a staff topped with a pulsing sea urchin. Bioluminescent algae glows faintly along its arms.*

**Abilities:**

- **Tidal Burst** (damage) — 1d6 dmg, 30% chance
- **Kelp Bind** (stun) — 0d0 dmg, 20% chance


### Event Guide

#### Puzzles

#### The Burning Tavern Seal (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3035.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *The Rusty Anchor tavern burns fiercely as Bloodtide goblins flee through its back entrance, but a massive iron seal blocks the doorway—forged by the original harbor founders to contain something ancient beneath. Strange runes glow red-hot around its edges, and acrid smoke pours from gaps where the metal has warped from the intense heat.*

**Choices:**

1. Endure the searing heat and push through the scalding metal barrier [DC 18 CON]
2. Hack through the warped iron hinges with sharp tools [DC 18 CON]
3. Channel inner fire to bash through the weakened seal with explosive force
4. Summon thorny vines to crack the ancient stonework around the seal
5. Walk away *(auto-success)*

**Correct Tool:** cutting
**Correct Ability:** Burning Bash


#### The Lighthouse Beacon Mechanism (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3036.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Elder Thessa's lighthouse beacon has gone dark just when the evacuees need its guiding light most. The ancient brass mechanism is seized with corrosion and barnacle growth, its massive lens assembly tilted at a dangerous angle. Below, Bloodtide goblins circle the lighthouse base like sharks, waiting for their chance to strike.*

**Choices:**

1. Study the intricate gear patterns and ancient maritime engineering [DC 16 WIS]
2. Scale the lens assembly to manually adjust the beacon's angle [DC 16 WIS]
3. Sense the storm patterns to align the beacon with wind currents
4. Invoke natural magic to cleanse the mechanism of sea corruption
5. Walk away *(auto-success)*

**Correct Tool:** climbing
**Correct Ability:** Storm Sense


#### The Goblin Warren Access (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3037.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Scout Finwick's intelligence leads to a concealed storm drain entrance that connects to the Bloodtide warren beneath the cliffs. The heavy iron grate is locked with an intricate mechanism bearing the crest of ancient Saltwind Harbor, designed by the town's founders who clearly knew of the threat below. Fresh goblin slime still drips from the bars, and distant chittering echoes from the depths.*

**Choices:**

1. Decipher the founder's locking mechanism using historical knowledge [DC 14 INT]
2. Cut through the ornate iron bars with precise tool work [DC 14 INT]
3. Rally courage with a thunderous battle cry that resonates through the grate
4. Summon protective water barriers around the entrance
5. Walk away *(auto-success)*

**Correct Tool:** cutting
**Correct Ability:** Beacon's Roar


#### The Collapsing Fish Market (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3038.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *The market's wooden supports groan ominously as Bloodtide goblins have undermined its foundations from below, creating a treacherous maze of tilting stalls and dangling nets. Barrels of salted fish roll wildly across the slanted floor while the structure threatens to collapse entirely into the goblin tunnels beneath. The air reeks of brine and terror.*

**Choices:**

1. Command attention and rally the panicked civilians with authoritative presence [DC 19 CHA]
2. Hack through the tangled nets and debris blocking the exit [DC 19 CHA]
3. Bellow a lighthouse-keeper's warning call to guide people to safety
4. Unleash nature's fury to clear the path of obstacles
5. Walk away *(auto-success)*

**Correct Tool:** cutting
**Correct Ability:** Beacon's Roar


#### The Slippery Dock Planks (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3039.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *The main pier glistens with goblin slime and seawater as Bloodtide raiders have coated the wooden planks with their acidic secretions. Several boards have already rotted through completely, creating deadly gaps above the churning harbor waters where more goblins lurk below. Families huddle at the far end, trapped between the treacherous walkway and the sea.*

**Choices:**

1. Dance across the treacherous planks with cat-like agility [DC 17 DEX]
2. Use climbing gear to traverse the pier's support beams below [DC 17 DEX]
3. Shatter the weakened boards to create a new path
4. Call forth healing waters to wash away the corrosive slime
5. Walk away *(auto-success)*

**Correct Tool:** climbing
**Correct Ability:** Shatter Defense


#### The Barnacle-Crusted Sea Wall (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3040.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Generations of marine growth have turned the harbor's protective sea wall into a razor-sharp obstacle course of barnacles and sharp coral. The Bloodtide goblins have deliberately cultivated these growths as a natural fortress, and now escaping civilians must somehow navigate the cutting edges to reach the boats beyond. Blood already stains the encrusted stone from those who tried and failed.*

**Choices:**

1. Grit your teeth and power through the cutting edges with raw endurance [DC 13 CON]
2. Scale the wall using climbing equipment to find handholds between the growths [DC 13 CON]
3. Smash through the barnacle clusters with devastating defensive strikes
4. Invoke the sea's blessing to safely part the marine growth
5. Walk away *(auto-success)*

**Correct Tool:** climbing
**Correct Ability:** Shatter Defense


#### The Moonlit Crane Mechanism (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3041.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Under the pale moonlight, the harbor's massive loading crane hangs at a perilous angle, its counterweight chains tangled by goblin sabotage. The mechanism once lifted cargo from the deepest merchant vessels, but now its boom threatens to crash down onto the crowded evacuation boats below. The bronze gears shine wetly in the darkness as seawater drips from the damaged housing.*

**Choices:**

1. Use brute strength to force the counterweight back into position [DC 19 STR]
2. Bludgeon the seized gears until they move freely again [DC 19 STR]
3. Navigate the rigging with practiced seafarer's skill
4. Drive wooden stakes into the crane's housing to secure it
5. Walk away *(auto-success)*

**Correct Tool:** bludgeon
**Correct Ability:** Rigging Climb


#### The Tide Pool Observatory (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3042.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *The harbor master's tide pool observatory, built into the cliff face to monitor goblin activity, has become a death trap as rising waters flood the chamber. Ancient climbing anchors dot the walls—installed by the original builders who clearly expected such emergencies. The only escape leads up through a narrow chimney in the rock, but the holds are slick with sea spray and time.*

**Choices:**

1. Study the positioning of the ancient anchors to plan the safest route [DC 20 WIS]
2. Use modern climbing gear to supplement the old anchor points [DC 20 WIS]
3. Apply rigging expertise to navigate the vertical escape route
4. Summon vines to create additional handholds in the rock cracks
5. Walk away *(auto-success)*

**Correct Tool:** climbing
**Correct Ability:** Rigging Climb


#### The Flooding Foundation Chamber (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3043.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Deep beneath the harbor master's office, a foundation chamber built by Saltwind's founders is rapidly flooding as goblin tunnels breach its walls. Ancient maritime charts and warning documents about the "depths below" float in the rising brine, while a massive stone seal bears carved warnings in the old tongue. The chamber's only exit requires navigating crumbling stonework as water rises to neck level.*

**Choices:**

1. Hold your breath and endure the crushing pressure of the rising waters [DC 22 CON]
2. Scale the chamber walls using ancient carved handholds [DC 22 CON]
3. Rally your spirit with a beacon-keeper's cry that echoes off the stone
4. Invoke crushing deep-sea magic to hold back the flood temporarily
5. Walk away *(auto-success)*

**Correct Tool:** climbing
**Correct Ability:** Beacon's Roar


#### The Sealed Storm Cellar (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3044.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A storm cellar beneath the harbormaster's quarters contains vital supplies for the siege defense, but its entrance is secured by an ancient ward scroll that recognizes only those who carry the proper maritime blessing. The ward glows with tidal energy that pulses in rhythm with the harbor's waters, and strange oceanic runes shift across its surface like living things.*

**Choices:**

1. Study the shifting rune patterns to understand their tidal significance [DC 19 WIS]
2. Strike the ward seal with blunt force to break its magical binding [DC 19 WIS]
3. Hold firm against the crushing pressure as the ward tests your resolve
4. Channel maelstrom magic to overwhelm the ancient protections
5. Walk away *(auto-success)*

**Correct Tool:** bludgeon
**Correct Ability:** Anchor Hold


#### Collapsing Harbor Bell Tower (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3045.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *The ancient harbor bell tower groans ominously as its foundation, weakened by goblin tunneling, begins to give way. Built by the village founders to warn of storms, the massive bronze bell still hangs precariously above while chunks of masonry crash into the courtyard below. If the tower falls completely, it will crush the nearby evacuation route and silence Saltwind Harbor's voice forever.*

**Choices:**

1. Rally the survivors with inspiring words to form a human chain up the tower [DC 21 CHA]
2. Use climbing gear to scale the unstable exterior walls [DC 21 CHA]
3. Channel the Harbor's Call to awaken the tower's protective spirits
4. Cast Sea Blessing to stabilize the foundation with tidal magic
5. Walk away *(auto-success)*

**Correct Tool:** climbing
**Correct Ability:** Rigging Climb


#### Flooded Merchant Quarter Maze (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3046.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Rising seawater has transformed the merchant quarter's narrow alleys into a treacherous maze of floating debris and hidden sinkholes. The old marketplace, once the heart of Saltwind Harbor's trade, now resembles a partially submerged labyrinth where goblin war-parties lurk behind overturned stalls. Desperate voices echo from upper windows as trapped families wait for rescue.*

**Choices:**

1. Use commanding presence to coordinate with trapped survivors for safe passage [DC 19 CHA]
2. Dig channels to drain water toward the harbor [DC 19 CHA]
3. Channel Harbor's Call to part the floodwaters temporarily
4. Cast Forest's Wrath to create wooden bridges from floating debris
5. Walk away *(auto-success)*

**Correct Tool:** digging
**Correct Ability:** Harbor's Call


#### Unstable Cliff-Face Watchtower (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3047.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *The watchtower perched on Saltwind Harbor's eastern cliff face teeters on the edge of collapse after goblin sappers undermined its foundations. Built generations ago to spot approaching storms, the tower now houses the village's signal fire that could summon aid from neighboring settlements. One wrong move could send the entire structure tumbling into the churning waves below.*

**Choices:**

1. Inspire confidence in others to help stabilize the structure [DC 20 CHA]
2. Scale the cliff face using climbing equipment [DC 20 CHA]
3. Channel Harbor's Call to commune with the tower's ancient purpose
4. Cast Woodland Ward to reinforce the structure with magical barriers
5. Walk away *(auto-success)*

**Correct Tool:** climbing
**Correct Ability:** Harbor's Call


#### Bloodtide Warren Entrance (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3048.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Hidden beneath the old fisherman's shrine lies a natural cave entrance that Scout Finwick discovered leads directly into the Bloodtide warren. The opening is sealed by an ancient stone slab carved with primitive goblin warnings and sea-demon sigils. Recent claw marks and crimson algae stains suggest this passage has been recently used by goblin raiding parties.*

**Choices:**

1. Use wisdom to decipher the ancient warning runes [DC 11 WIS]
2. Excavate around the stone seal to create an opening [DC 11 WIS]
3. Channel Burning Bash to shatter the seal with righteous fury
4. Cast Woodland Ward to protect against any magical traps on the seal
5. Walk away *(auto-success)*

**Correct Tool:** digging
**Correct Ability:** Burning Bash


#### Moonlit Rope Bridge Trap (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3049.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A makeshift rope bridge spans between the harbor's twin jetties, but goblin saboteurs have frayed the support ropes under cover of darkness. The bridge sways dangerously in the night wind, its planks already beginning to separate. Below, the churning harbor waters reflect the moon's pale light while echoing with goblin war-cries from the depths.*

**Choices:**

1. Dance across the failing planks with perfect balance [DC 21 DEX]
2. Use a heavy tool to anchor new support points [DC 21 DEX]
3. Channel Anchor Hold to bind yourself safely to the bridge
4. Cast Healing Tsunami to repair the damaged ropes
5. Walk away *(auto-success)*

**Correct Tool:** bludgeon
**Correct Ability:** Anchor Hold


#### Buried Warning Bell Chamber (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3050.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *The old harbor master's emergency warning system lies buried beneath collapsed timber and rubble from goblin tunnel excavations. The brass bell mechanism, installed decades ago to alert the village of sea dangers, could still sound across the entire harbor if properly unearthed. Time is running short as more sections of the wharf continue to sink into the goblin-carved hollows below.*

**Choices:**

1. Rally others with inspiring words to help clear the debris [DC 20 CHA]
2. Dig systematically through the rubble to reach the mechanism [DC 20 CHA]
3. Channel Rigging Climb to navigate through the tangled wreckage above
4. Cast Root Spear to pierce through and lift away the heaviest obstacles
5. Walk away *(auto-success)*

**Correct Tool:** digging
**Correct Ability:** Rigging Climb


#### Corrupted Tide Pool Passage (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3051.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A natural tide pool passage between the harbor rocks has been corrupted by goblin rituals, its water now glowing with sickly bioluminescence. Ancient offerings to sea spirits lie scattered around the edges, but goblin totems made of bone and barnacles have been thrust into the sacred pools. The passage leads to higher ground, but the corrupted waters seem to writhe with unnatural life.*

**Choices:**

1. Use wisdom to understand the original purification rituals [DC 21 WIS]
2. Dig out the goblin totems desecrating the sacred pools [DC 21 WIS]
3. Channel Beacon's Roar to drive out the corruption with lighthouse-blessed sound
4. Cast Forest's Wrath to destroy the unnatural growths in the pools
5. Walk away *(auto-success)*

**Correct Tool:** digging
**Correct Ability:** Beacon's Roar


#### Damaged Harbor Gate Mechanism (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3052.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *The great harbor gate that protects the inner docks from rough seas has been damaged by goblin sabotage, its massive gears jammed with debris and algae. Originally designed to close during storms, the gate now hangs partially open, allowing the enemy easy access to the heart of Saltwind Harbor. The mechanism's bronze wheels still gleam in the moonlight, waiting for someone skilled enough to restore their function.*

**Choices:**

1. Study the mechanism carefully to understand its proper operation [DC 10 WIS]
2. Use a heavy tool to clear the jammed gears by force [DC 10 WIS]
3. Channel Anchor Hold to stabilize yourself while working on the underwater components
4. Cast Thorn Bolt to precisely dislodge debris from the delicate mechanisms
5. Walk away *(auto-success)*

**Correct Tool:** bludgeon
**Correct Ability:** Anchor Hold


#### Tilting Fisherman's Wharf (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3053.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *The old fisherman's wharf has been undermined by goblin tunneling, causing the entire structure to tilt precariously toward the harbor. Weathered fishing boats still hang from the tilted framework like trapped birds, their hulls creaking ominously. The wharf's collapse would not only destroy valuable escape vessels but also create a barrier blocking access to the deeper harbor channels.*

**Choices:**

1. Endure the strain of manually holding key support beams in place [DC 17 CON]
2. Use cutting tools to remove damaged sections and redistribute weight [DC 17 CON]
3. Channel Rigging Climb to repositioning the hanging boats safely
4. Cast Soothing Waves to support the structure from below with cushioning water
5. Walk away *(auto-success)*

**Correct Tool:** cutting
**Correct Ability:** Rigging Climb


#### Moonlit Beacon Prism Array (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3054.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *The lighthouse's auxiliary beacon system uses an array of carefully positioned crystal prisms to amplify its warning light across the harbor during emergencies. Goblin infiltrators have deliberately misaligned the crystals under cover of darkness, scattering the light and rendering the beacon useless. The intricate array must be realigned precisely, as even the slightest error could shatter the irreplaceable focusing crystals.*

**Choices:**

1. Use wisdom and patience to calculate the proper crystal alignments [DC 20 WIS]
2. Carefully adjust the prism mounts using precise tools [DC 20 WIS]
3. Channel Rigging Climb to access and adjust the highest prism positions
4. Cast Bramble Burst to create gentle vine supports that guide the crystals into position
5. Walk away *(auto-success)*

**Correct Tool:** bludgeon
**Correct Ability:** Rigging Climb


#### The Shattered Fishmonger's Vault (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3055.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *The old fishmonger's shop has collapsed into its own storage cellar, creating a treacherous pit filled with broken barrels and splintered wood. The cellar's stone vault still contains emergency supplies, but the floor above has caved in completely, leaving only precarious ledges and dangling rope nets. Bloodtide goblins can be heard chittering in the storm drains below, their claws scraping against stone.*

**Choices:**

1. Leap between the unstable wooden ledges jutting from the cellar walls [DC 16 DEX]
2. Use climbing gear to rappel down the rope nets and scale back up safely [DC 16 DEX]
3. Channel Harbor's Call to sense the safest path through the debris
4. Cast Bramble Burst to create handholds from thorny vines
5. Walk away *(auto-success)*

**Correct Tool:** climbing
**Correct Ability:** Harbor's Call


#### The Buried Archive Chamber (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3056.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *The village record hall has been buried under a massive rockslide triggered by the goblin tunneling beneath. Only a small gap remains between the fallen stones and the chamber's iron door, which bears the town seal and likely contains maps of the old storm drain system. The rocks shift ominously with each distant goblin roar, and seawater is beginning to seep through the gaps.*

**Choices:**

1. Squeeze through the narrow gap between the crushing stones [DC 17 DEX]
2. Dig a wider passage through the loose rubble and debris [DC 17 DEX]
3. Use Burning Bash to shatter the blocking stones with explosive force
4. Cast Bark Skin to protect yourself while crawling through the jagged opening
5. Walk away *(auto-success)*

**Correct Tool:** digging
**Correct Ability:** Burning Bash


#### The Moonlit Rope Bridge Trap (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3057.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A heavy cargo net hangs between two warehouse rooftops, but goblin saboteurs have woven razor-sharp shells and broken glass throughout the ropes during their nighttime raid. The net sways dangerously in the harbor wind, and below it, a pack of Bloodtide goblins waits in the alley shadows. Getting across requires navigating the lethal trap while the moonlight reveals every glinting shard.*

**Choices:**

1. Use raw strength to tear through the net despite the cutting obstacles [DC 17 STR]
2. Carefully cut away the razor traps to clear a safe passage [DC 17 STR]
3. Employ Rigging Climb to navigate the net like a ship's rigging master
4. Cast Maelstrom Strike to blast the dangerous debris from the ropes
5. Walk away *(auto-success)*

**Correct Tool:** cutting
**Correct Ability:** Rigging Climb


#### The Siren's Bell Chamber (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3058.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *High atop the customs house, an ancient warning bell sits within a ornate bronze chamber decorated with sea serpent motifs. The chamber's heavy doors have warped shut from years of salt air, and the bell rope has rotted away completely. The mechanism requires both the proper maritime blessing and physical manipulation to function, while goblin war cries grow louder from the harbor below.*

**Choices:**

1. Use pure charisma to invoke the ancient maritime rights and open the sacred chamber [DC 19 CHA]
2. Scale the chamber walls to find an alternate entrance from above [DC 19 CHA]
3. Channel Storm Sense to understand the bell's mystical requirements
4. Cast Vine Lash to manipulate the bell mechanism from a distance
5. Walk away *(auto-success)*

**Correct Tool:** climbing
**Correct Ability:** Storm Sense


#### Environmental Events

#### The Merchant's Dilemma (event)

<p align="center"><img src="../data/portraits/events/evt_3059.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Trader Gareth clutches a heavy coinpurse while his wife Mira pleads with him to help wounded villagers instead of loading their cart with valuables. Their teenage son Tam stands between them, torn as goblin war cries grow closer to their shop.*

**Choices:**

1. Endure the family's heated argument and mediate a solution [DC 12 CON]
2. Scale the shop's roof to scout escape routes for the family [DC 12 CON]
3. Sense the approaching storm's effect on goblin movements
4. Ward the shop with protective forest magic
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 health damage


#### Night Vigil Corruption (event)

<p align="center"><img src="../data/portraits/events/evt_3060.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Brother Aldwin tends to the village shrine when crimson algae begins seeping through the stone floor. The young priest's hands shake as unholy whispers emanate from the spreading corruption, while villager Nessa begs him to consecrate her dying husband.*

**Choices:**

1. Steel yourself against the shrine's corrupting influence [DC 15 CON]
2. Dig trenches to redirect the algae flow away from the altar [DC 15 CON]
3. Channel burning power to cleanse the corruption
4. Summon healing waters to counter the dark influence
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 health damage


#### Barricade Breakthrough (event)

<p align="center"><img src="../data/portraits/events/evt_3061.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Fisherman Korven and blacksmith Hulda argue over reinforcing the tavern's barricade as goblin claws scratch against the windows. Young barmaid Sera points to a weak spot in the wall where crimson-painted fingers are already poking through.*

**Choices:**

1. Force the beam into place with raw strength [DC 11 STR]
2. Slice rope and wood to create better binding materials [DC 11 STR]
3. Unleash burning energy to drive back the probing goblins
4. Grow protective thorns to seal the breach
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### The Captain's Burden (event)

<p align="center"><img src="../data/portraits/events/evt_3062.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Captain Merrick clutches a bloodied letter while Sergeant Kale demands to know about the missing patrol. The captain's daughter Lysa has discovered the letter reveals her brother was in the doomed scouting party, and she demands answers her father cannot give.*

**Choices:**

1. Physically support the captain as he breaks down [DC 13 STR]
2. Cut through the emotional tension with decisive action planning [DC 13 STR]
3. Shatter the family's denial with hard truths about war
4. Channel nature's wrath to give the captain strength for revenge
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### The Healer's Choice (event)

<p align="center"><img src="../data/portraits/events/evt_3063.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Village healer Marta faces an impossible decision as wounded villager Beck bleeds out beside injured Bloodtide scout Slix. Her apprentice Jorin argues for letting the goblin die, while Beck's wife Elena begs her to save her husband first.*

**Choices:**

1. Observe the goblin's wounds to determine its intelligence value [DC 11 WIS]
2. Use cutting tools to perform emergency field surgery [DC 11 WIS]
3. Pierce through deceptions with an intimidating stare
4. Embrace healing waters to save both patients simultaneously
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### Dock Runner's Gambit (event)

<p align="center"><img src="../data/portraits/events/evt_3064.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Young dock worker Pip has discovered Bloodtide goblins using the old smuggling tunnels beneath the warehouse. He's cornered by harbor master Dench and fisherwoman Coral, who suspect him of collaborating with the enemy after seeing him emerge from the tunnel entrance.*

**Choices:**

1. Move with agile precision to demonstrate your innocence [DC 14 DEX]
2. Excavate evidence from the tunnel to prove your story [DC 14 DEX]
3. Call upon the harbor's power to reveal the truth
4. Protect yourself with woodland magic while explaining
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 health damage


#### Lighthouse Keeper's Stand (event)

<p align="center"><img src="../data/portraits/events/evt_3065.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Elder Thessa's granddaughter Wynn refuses to abandon the lighthouse beacon while her grandmother tries to bar the door against approaching goblins. Lighthouse keeper Old Salt insists the light must stay on to guide fleeing boats, even as barnacle-crusted claws scrape at the tower's base.*

**Choices:**

1. Endure the physical strain of manually operating the beacon [DC 16 CON]
2. Cut defensive positions in the lighthouse structure [DC 16 CON]
3. Anchor your resolve to hold the lighthouse at all costs
4. Channel soothing magic to calm the panicked defenders
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### The Smuggler's Bargain (event)

<p align="center"><img src="../data/portraits/events/evt_3066.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Notorious smuggler 'Black Tide' Garrett offers his hidden boat to ferry villagers to safety, but demands his captured partner Senna be released from the village jail first. Constable Reed refuses to free a criminal while families drown in the harbor.*

**Choices:**

1. Convince both sides with passionate negotiation [DC 19 CHA]
2. Dig out an alternative solution to the prisoner problem [DC 19 CHA]
3. Use harbor magic to reveal the truth behind their conflict
4. Protect negotiations with defensive tree magic
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### Fisher's Last Catch (event)

<p align="center"><img src="../data/portraits/events/evt_3067.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Veteran fisher Tam Breakwater refuses to abandon his nets full of the day's catch while his crew - young Sal and veteran Cord - beg him to flee as goblin war-rafts approach their position. The fish represent the village's only food stores for winter, but the goblins will be on them within minutes.*

**Choices:**

1. Rally the crew with inspiring words about sacrifice and duty [DC 13 CHA]
2. Smash through the boat's rail to drop nets faster [DC 13 CHA]
3. Climb the rigging to spot the fastest escape route
4. Ward the area with protective forest magic
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### The Tide Pool Oracle (event)

<p align="center"><img src="../data/portraits/events/evt_3068.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Strange hermit Naia claims the tide pools speak of an ancient pact that could end the goblin assault. Village elder Marcus dismisses her as mad, while desperate mother Vera begs him to listen as her children hide in the tide pools behind them.*

**Choices:**

1. Study the tide pools for signs of truth in her words [DC 13 WIS]
2. Cut through superstition with practical blade work [DC 13 WIS]
3. Shatter the elder's skepticism with forceful argument
4. Channel healing waters to test her mystical claims
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 health damage


#### The Refugee Standoff (event)

<p align="center"><img src="../data/portraits/events/evt_3069.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Captain Yorick blocks the inn's entrance, refusing to let dozens of terrified refugees inside while his own wounded soldiers need the space. Inn-keeper Marta pleads that the families have children who will freeze in the streets, but Yorick insists his men fought for the village and deserve priority treatment.*

**Choices:**

1. Convince Captain Yorick that protecting civilians is a soldier's highest duty [DC 22 CHA]
2. Smash down the inn's back door to create another entrance for the refugees [DC 22 CHA]
3. Scale the inn's exterior to open upper windows for the families
4. Channel nature's fury to overwhelm Yorick with primal intimidation
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### The Poisoned Well (event)

<p align="center"><img src="../data/portraits/events/evt_3070.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Village elder Gareth collapses beside the town well, foam on his lips after drinking the water. Young healer Nessa accuses visiting merchant Crow of poisoning the supply to weaken defenders, while Crow claims the goblins contaminated it from below.*

**Choices:**

1. Push through the poison's effects to examine the well yourself [DC 16 CON]
2. Cut open the well's covering to inspect for goblin tampering [DC 16 CON]
3. Climb down the rope to investigate the water source directly
4. Use nature's power to purify any corruption in the water
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### The Bloodtide Informant (event)

<p align="center"><img src="../data/portraits/events/evt_3071.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Dock worker Lars drags a captured goblin scout toward Captain Merrick's position, insisting the creature knows about planned reinforcements from the underwater warren. The scout chatters desperately in broken Common, offering to reveal the clan's weakness in exchange for safe passage back to the sea.*

**Choices:**

1. Quickly extract information before the scout's gills dry out completely [DC 11 DEX]
2. Use a digging tool to sketch the warren layout as the goblin describes it [DC 11 DEX]
3. Break through the scout's mental defenses with overwhelming force
4. Grow protective bark to shield yourself while negotiating with the dangerous creature
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### The Dawn Patrol (event)

<p align="center"><img src="../data/portraits/events/evt_3072.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Sergeant Klass argues with exhausted guard Tomlin about maintaining the morning watch rotation. Klass insists fresh eyes are needed to spot goblin movement, but Tomlin claims his men haven't slept in two days and will collapse at their posts.*

**Choices:**

1. Endure the exhaustion yourself to take the watch and settle the dispute [DC 11 CON]
2. Strike the watchtower bell to rally volunteers for the patrol [DC 11 CON]
3. Project your voice across the harbor to inspire the weary defenders
4. Draw strength from nature to restore your own energy for the watch
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### The Tribute Collector (event)

<p align="center"><img src="../data/portraits/events/evt_3073.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Tavern keeper Magnus confronts his brother Willem about hiding a chest of silver beneath the floorboards. Magnus wants to use the treasure to buy safe passage from goblin raiders, while Willem argues they should use it to hire mercenaries and fight back.*

**Choices:**

1. Persuade them that the village's survival depends on united action [DC 15 CHA]
2. Smash through their stubbornness with direct confrontation [DC 15 CHA]
3. Scale the tavern's rafters to get their attention and mediate
4. Use thorny vines to physically separate the feuding brothers
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 health damage


#### The Fever Ship (event)

<p align="center"><img src="../data/portraits/events/evt_3074.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Harbor master Quinn discovers that merchant vessel 'Sea Rose' carries both refugees and several crew members burning with fever. Captain Darcy begs to dock and treat her sick, but Quinn fears the illness will spread through the already vulnerable village population.*

**Choices:**

1. Push through your own discomfort to board and assess the sick personally [DC 18 CON]
2. Use a cutting tool to create an isolated docking area away from the village [DC 18 CON]
3. Burn away the fever's corruption with cleansing flames
4. Channel healing energy to strengthen yourself while treating the afflicted
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 health damage


#### The Tide Pool Witness (event)

<p align="center"><img src="../data/portraits/events/evt_3075.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Young fisherman Tam trembles as he tells dock foreman Bass about seeing goblins emerge from the tide pools near Gull's Rest. Bass dismisses the boy's story as fear-induced fantasy, but Tam insists he counted at least thirty crimson-painted forms rising from the churning water during high tide.*

**Choices:**

1. Use your intimidating presence to make Bass take the warning seriously [DC 10 CHA]
2. Cut through Bass's skepticism with sharp questions about the timeline [DC 10 CHA]
3. Employ your dock fighting experience to command respect from both men
4. Call upon sea blessings to reveal the truth of Tam's claims
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### The Healing Crisis (event)

<p align="center"><img src="../data/portraits/events/evt_3076.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Village healer Ruth faces an impossible choice as both Captain Merrick's lieutenant and a goblin prisoner lie dying before her. Lieutenant Brass took a trident to the chest defending the harbor, while the captured goblin scout succumbed to wounds during interrogation.*

**Choices:**

1. Convince Ruth to prioritize the lieutenant while you handle the goblin [DC 10 CHA]
2. Cut bandages and supplies to treat both patients simultaneously [DC 10 CHA]
3. Use your intimidating glare to cow the goblin into cooperation
4. Channel a healing tsunami to restore both the dying men
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### The Midnight Saboteur (event)

<p align="center"><img src="../data/portraits/events/evt_3077.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Night watchman Pike catches apprentice smith Jana near the weapon cache, claiming she was checking the locks for security. Pike suspects she's been weakening the defenses, pointing to recent tool failures during goblin attacks as evidence of sabotage.*

**Choices:**

1. Demonstrate your strength by testing the supposedly sabotaged weapons yourself [DC 11 STR]
2. Dig through the weapon cache to find evidence of actual tampering [DC 11 STR]
3. Use your rope-climbing skills to check for goblin infiltration routes above
4. Summon thorny brambles to test Jana's reactions and reveal the truth
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### The Rope Bridge Gambit (event)

<p align="center"><img src="../data/portraits/events/evt_3078.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 2

> *Engineer Cord argues with Captain Voss about cutting the rope bridges connecting the harbor's elevated walkways. Cord insists destroying the bridges will stop goblin advancement, but Voss worries about trapping civilians who might need the escape routes.*

**Choices:**

1. Endure the physical strain to reinforce the bridges instead of destroying them [DC 18 CON]
2. Use climbing expertise to create alternative routes before cutting the bridges [DC 18 CON]
3. Scale the support posts to reach the best vantage point for the decision
4. Channel crushing ocean depths to test the bridge's true structural integrity
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 health damage


#### The Matron's Last Stand (event)

<p align="center"><img src="../data/portraits/events/evt_3079.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Old Matron Kelara clutches a bloodied cleaver as she defends three terrified children behind overturned barrels near the fish market. Two crimson-painted Bloodtide goblins circle her, their gills fluttering as they hiss threats in their guttural tongue. The matron's weathered hands shake, but her eyes burn with maternal fury.*

**Choices:**

1. Read the goblins' movements and anticipate their attack patterns [DC 13 WIS]
2. Smash a barrel to create debris and distraction [DC 13 WIS]
3. Use your intimidating dock fighter presence to make them think twice
4. Summon crushing water pressure to drive them back
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### The Bell Ringer's Dilemma (event)

<p align="center"><img src="../data/portraits/events/evt_3081.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Young bellkeeper Tam cowers in the lighthouse bell tower as crimson goblins scale the outside walls with barnacle-encrusted claws. Elder Thessa shouts from below to ring the warning bell, but Tam fears the sound will draw every goblin in the harbor to their position. His hand trembles on the bell rope.*

**Choices:**

1. Time the bell perfectly to disorient the climbing goblins [DC 10 DEX]
2. Smash the bell mechanism to create a different kind of distraction [DC 10 DEX]
3. Let loose a thunderous roar that echoes through the lighthouse
4. Protect the area with natural magical barriers
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 health damage


#### Scout Finwick's Urgent Report (event)

<p align="center"><img src="../data/portraits/events/evt_3082.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Scout Finwick bursts into Captain Merrick's makeshift command post, his face pale with terror as he describes the vast underwater warren beneath the cliffs. Captain Merrick demands immediate action, but Finwick insists they need to evacuate everyone now before the main goblin force emerges. The captain's hand hovers over his sword as tension crackles between duty and survival.*

**Choices:**

1. Convince both men to find a compromise between fighting and fleeing [DC 14 CHA]
2. Slam your fist on the table to demand they focus on the real threat [DC 14 CHA]
3. Use your sailing expertise to suggest tactical positioning
4. Call upon the sea's power to demonstrate the goblins' aquatic advantage
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### The Chandler's Last Candles (event)

<p align="center"><img src="../data/portraits/events/evt_3083.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Chandler Mira frantically lights every candle in her shop as Bloodtide goblins pound on her shuttered windows, their webbed claws scraping against the wood. She believes the light will keep them at bay, but her supply is nearly exhausted and the flames are attracting more attention. Smoke billows from overturned wax as she works with desperate speed.*

**Choices:**

1. Help her arrange the candles more strategically to maximize their effect [DC 15 DEX]
2. Smash through the back wall to create an escape route [DC 15 DEX]
3. Use your rope skills to help her reach the high shelves safely
4. Launch magical thorns through the shutters to drive the goblins back
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### The Barrel Maker's Stand (event)

<p align="center"><img src="../data/portraits/events/evt_3084.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Cooper Aldwin has barricaded himself in his workshop using every barrel and cask he owns, but the Bloodtide goblins are systematically smashing through his defenses with coral clubs. His teenage apprentice Jess cowers behind him, clutching a barrel hoop as a makeshift weapon. Aldwin grimly declares he won't let them take another child from this village.*

**Choices:**

1. Endure the assault and help them maintain their defensive position [DC 12 CON]
2. Smash the remaining barrels to create improvised weapons [DC 12 CON]
3. Break through their defenses with overwhelming force to scatter the goblins
4. Summon thorny growths to reinforce their barricade
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 health damage


#### The Tide Pool Observatory (event)

<p align="center"><img src="../data/portraits/events/evt_3085.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Scholar Erasmus huddles in his clifftop observatory, frantically scribbling notes about the goblins' emergence patterns while his assistant pleads with him to flee. Through his telescope, he's discovered that the attacks follow the ancient tidal charts, but he insists on gathering more data despite the approaching dawn bringing the highest tide. His obsession with knowledge may doom them both.*

**Choices:**

1. Help him analyze the complex tidal patterns and goblin movements [DC 19 INT]
2. Smash his equipment to force him to face reality [DC 19 INT]
3. Use your sailing knowledge to help him understand the maritime tactics
4. Create magical protection around the observatory
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 health damage


#### The Harbor Pilot's Knowledge (event)

<p align="center"><img src="../data/portraits/events/evt_3086.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Grizzled harbor pilot Captain Senna recognizes the goblin war chants from her years sailing these waters and knows they're preparing for a massive dawn assault. She tries to convince the other survivors that the old lighthouse keeper's manual contains charts of every underwater cave, but the others dismiss her as a superstitious old salt. Time runs short as the first rays of dawn appear.*

**Choices:**

1. Study the ancient maritime charts to verify her claims [DC 10 INT]
2. Support her authority with your own seafaring knowledge [DC 10 INT]
3. Use crushing magical force to demonstrate the truth
4. Call upon the harbor's power to prove the connection between tides and goblin strength
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### The Fisherman's Net Trap (event)

<p align="center"><img src="../data/portraits/events/evt_3087.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Old fisherman Garrett has stretched his massive fishing nets across the harbor entrance, hoping to entangle the goblin raiders when they retreat to the caves. His son Willem argues it will only anger them more and bring worse retaliation, while Garrett insists it's their only chance to capture some alive for information. The nets strain under the current as shapes move beneath the water.*

**Choices:**

1. Help them reinforce the nets with superior materials and technique [DC 17 STR]
2. Dig anchor points to better secure the net trap [DC 17 STR]
3. Use your intimidating presence to convince them of the best course
4. Enhance the nets with magical crushing power
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 health damage


#### The Lighthouse Keeper's Secret (event)

<p align="center"><img src="../data/portraits/events/evt_3088.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Ancient lighthouse keeper Morwyn reveals to Elder Thessa that the beacon's crystal can be overcharged to create a blinding flash that will disorient the goblins, but doing so will likely destroy the lighthouse forever. Thessa hesitates, knowing the lighthouse has guided ships safely for generations, while goblin war-cries grow louder outside. Morwyn's gnarled hands shake as he reaches for the crystal controls.*

**Choices:**

1. Help them find a way to modify the beacon without destroying it [DC 17 WIS]
2. Use your climbing skills to access the beacon's upper mechanisms [DC 17 WIS]
3. Contribute your rope expertise to create alternative lighthouse rigging
4. Channel crushing magical energy to amplify the crystal's power safely
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### The Tidepool Prophet's Warning (event)

<p align="center"><img src="../data/portraits/events/evt_3089.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Old Marta the tidereader kneels beside a churning tidepool, her weathered hands tracing ancient symbols in the sand while crimson-painted goblins circle closer. She claims the pool's movements reveal the exact timing of the next Bloodtide assault wave, but her arcane predictions require immediate action. Captain Vorren demands she abandon her 'superstitious nonsense' and help with the evacuation.*

**Choices:**

1. Decipher the tidepool's cryptic patterns to predict the goblin assault timing [DC 20 INT]
2. Use a blade to carve protective runes around the tidepool's edge [DC 20 INT]
3. Channel mystical energy to shatter the goblins' formation with devastating force
4. Cast nature magic to accelerate the tidepool's revelatory properties
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### The Midnight Rope Walk (event)

<p align="center"><img src="../data/portraits/events/evt_3090.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Young sailmaker Pip has rigged rope lines between the harbor's tallest masts, creating an escape route above the goblin-infested streets below. Elder Grimm refuses to risk the dangerous crossing, arguing they should wait for dawn reinforcements. Meanwhile, wet goblin claws scrape against the warehouse walls as the creatures begin their climb upward.*

**Choices:**

1. Assess wind patterns and rope tension to guide the safest crossing route [DC 10 WIS]
2. Use climbing gear to secure additional anchor points for the rope bridge [DC 10 WIS]
3. Unleash fiery power to drive back the climbing goblins below
4. Summon thorny vines to create handholds along the treacherous rope span
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 health damage


#### The Barnacle Harvester's Gambit (event)

<p align="center"><img src="../data/portraits/events/evt_3091.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Dock worker Kellan has discovered that the goblins recoil from certain barnacle species growing on the pier posts, but harvesting enough requires venturing into goblin-controlled waters. His sister Nessa fears the risk isn't worth the potential protection, while desperate refugees watch their makeshift barricades crumble. The crimson-painted raiders grow bolder with each passing hour.*

**Choices:**

1. Time the goblin patrol patterns to find the safest harvesting windows [DC 19 DEX]
2. Use digging tools to extract barnacles quickly from underwater pier foundations [DC 19 DEX]
3. Unleash devastating attacks to clear the goblins from the harvesting area
4. Weave natural magic to accelerate barnacle growth and enhance their protective properties
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### The Negotiator's Last Stand (event)

<p align="center"><img src="../data/portraits/events/evt_3092.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Merchant prince Aldric steps forward to parley with the goblin war-chief Scar-Gill, offering tribute in exchange for safe passage for the villagers. The scarred goblin leader seems intrigued but demands proof of Aldric's sincerity through a dangerous ritual combat. Captain Thorne warns that any failed negotiation will doom the remaining defenders to a hopeless final battle.*

**Choices:**

1. Appeal to the goblin's pride and honor with carefully chosen words and gestures [DC 21 CHA]
2. Use a ceremonial blade to perform the ritual combat with proper form and respect [DC 21 CHA]
3. Channel explosive power to demonstrate strength worthy of the goblin chief's respect
4. Cast healing magic to show peaceful intentions while proving magical prowess
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 stamina damage


#### The Storm Drain Saboteurs (event)

<p align="center"><img src="../data/portraits/events/evt_3093.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Engineer Mira has identified the main storm drain that serves as the goblins' primary invasion route, but sealing it requires someone to venture deep into the flooded tunnels while Bloodtide raiders patrol the waters above. Her apprentice Willem volunteers despite his fear of drowning, knowing that blocking this passage could save dozens of families. Scout reports suggest the goblins are planning to flood the entire lower district within the hour.*

**Choices:**

1. Calculate the precise explosive placement needed to collapse the tunnel without flooding the district [DC 14 INT]
2. Use digging tools to create a controlled cave-in that blocks the passage permanently [DC 14 INT]
3. Summon the harbor's protective power to aid in the dangerous underwater sabotage mission
4. Launch piercing projectiles to precisely damage the tunnel's structural weak points
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 health damage


#### The Codebook Cipher (event)

<p align="center"><img src="../data/portraits/events/evt_3094.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Harbor clerk Tobias has intercepted a waterlogged goblin message written in strange tidal symbols, claiming it contains their invasion timeline and target priorities. Quartermaster Dana insists the symbols are meaningless scrawl, but Tobias believes cracking the code could reveal which districts the Bloodtide Clan plans to hit next. Time runs short as goblin war-horns echo from three different directions, suggesting the coordinated assault is about to begin.*

**Choices:**

1. Apply pattern recognition and linguistic analysis to decode the tidal symbol cipher [DC 22 INT]
2. Use specialized tools to reveal hidden layers of the water-damaged message [DC 22 INT]
3. Channel mystical lighthouse energy to illuminate the message's true meaning
4. Cast thorny magic to draw out the symbols' natural essence and reveal their secrets
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 health damage


#### The Rigging Artist's Trap (event)

<p align="center"><img src="../data/portraits/events/evt_3095.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Master rigger Senna has devised a plan to use the harbor's ship rigging as a massive web to entangle the goblin assault boats, but it requires cutting loose valuable vessels and risking the harbor's entire fishing fleet. Ship owner Captain Brass opposes the plan, arguing they'll starve without their boats even if they survive the attack. Goblin vessels can be seen approaching through the morning mist, their crimson sails billowing ominously.*

**Choices:**

1. Calculate the optimal rigging configuration to maximize entanglement while minimizing vessel loss [DC 16 DEX]
2. Use climbing equipment to quickly position the rigging trap before the goblins arrive [DC 16 DEX]
3. Sense the approaching storm patterns to time the trap perfectly with natural wind assistance
4. Summon root magic to strengthen and extend the rope network into an unbreakable web
5. Walk away *(auto-success)*

**Failure Penalty:** 4–10 health damage


#### Combat Encounters

*23 unique combat encounters in this room.*

#### Encounter: Tidecaller Grunt (combat)

<p align="center"><img src="../data/portraits/events/evt_3000.png" width="300"/></p>

**Difficulty:** 1 &nbsp; **Occurrences:** 4

> *A goblin adorned with shells and seaweed, chanting in gurgling tones while clutching a staff topped with a pulsing sea urchin. Bioluminescent algae glows faintly along its arms.*

**Monster Lineup:**

- **Tidecaller Grunt** — HP 8-12, AC 10-12, atk: bludgeoning, element: water, weakness: light

**Loot:**

- kraken kelp strips (30%)

**Gold Drop:** 2–8g


#### Hostile Coral-Crusted Shambler (combat)

<p align="center"><img src="../data/portraits/events/evt_3002.png" width="300"/></p>

**Difficulty:** 1 &nbsp; **Occurrences:** 1

> *A bloated human figure encrusted with barnacles and sea anemones. Saltwater pours from its mouth as it lurches forward, coral growths sprouting from its joints.*

**Monster Lineup:**

- **Coral-Crusted Shambler** — HP 12-16, AC 9-11, atk: bludgeoning, element: water, weakness: fire

**Loot:**

- kraken-bone maul (16%)

**Gold Drop:** 2–8g


#### Hostile Cave Crawler (combat)

<p align="center"><img src="../data/portraits/events/evt_3004.png" width="300"/></p>

**Difficulty:** 1 &nbsp; **Occurrences:** 1

> *A massive spider with a wet, glistening carapace that reflects moonlight. Its legs end in sharp points that click against stone as it moves through the flooded passages.*

**Monster Lineup:**

- **Cave Crawler** — HP 10-14, AC 12-14, atk: piercing, weakness: fire

**Loot:**

- fisherman's gutting knife (28%)
- kelp bread (25%)
- scroll of tidal ward (32%)

**Gold Drop:** 2–8g


#### Hostile Tidecaller Grunt (combat)

<p align="center"><img src="../data/portraits/events/evt_3006.png" width="300"/></p>

**Difficulty:** 1 &nbsp; **Occurrences:** 2

> *A goblin adorned with shells and seaweed, chanting in gurgling tones while clutching a staff topped with a pulsing sea urchin. Bioluminescent algae glows faintly along its arms.*

**Monster Lineup:**

- **Tidecaller Grunt** — HP 8-12, AC 10-12, atk: bludgeoning, element: water, weakness: light

**Loot:**

- chaos trident (36%)
- gill-rope (15%)
- coral fungus (32%)

**Gold Drop:** 2–8g


#### Cult Enforcers: Cave Crawler (combat)

<p align="center"><img src="../data/portraits/events/evt_3007.png" width="300"/></p>

**Difficulty:** 1 &nbsp; **Occurrences:** 1

> *A massive spider with a wet, glistening carapace that reflects moonlight. Its legs end in sharp points that click against stone as it moves through the flooded passages.*

**Monster Lineup:**

- **Cave Crawler** — HP 10-14, AC 12-14, atk: piercing, weakness: fire

**Loot:**

- lighthouse keeper's blessed mace (11%)
- rainwater (19%)

**Gold Drop:** 2–8g


#### Encounter: Cave Crawler (combat)

<p align="center"><img src="../data/portraits/events/evt_3008.png" width="300"/></p>

**Difficulty:** 1 &nbsp; **Occurrences:** 4

> *A massive spider with a wet, glistening carapace that reflects moonlight. Its legs end in sharp points that click against stone as it moves through the flooded passages.*

**Monster Lineup:**

- **Cave Crawler** — HP 10-14, AC 12-14, atk: piercing, weakness: fire

**Loot:**

- kraken kelp strips (22%)

**Gold Drop:** 2–8g


#### Bloodtide Raider Attack (combat)

<p align="center"><img src="../data/portraits/events/evt_3009.png" width="300"/></p>

**Difficulty:** 1 &nbsp; **Occurrences:** 1

> *A lean goblin with gills behind pointed ears and webbed fingers, body painted with crimson algae. Water drips constantly from its scaled skin as it screeches battle cries.*

**Monster Lineup:**

- **Bloodtide Raider** — HP 6-10, AC 11-13, atk: slashing, element: water, weakness: fire

**Loot:**

- depth-caller staff (35%)

**Gold Drop:** 2–8g


#### Encounter: Bloodtide Raider (combat)

<p align="center"><img src="../data/portraits/events/evt_3010.png" width="300"/></p>

**Difficulty:** 1 &nbsp; **Occurrences:** 4

> *A lean goblin with gills behind pointed ears and webbed fingers, body painted with crimson algae. Water drips constantly from its scaled skin as it screeches battle cries.*

**Monster Lineup:**

- **Bloodtide Raider** — HP 6-10, AC 11-13, atk: slashing, element: water, weakness: fire

**Loot:**

- kelp bread (14%)
- barnacle scraper (36%)
- chaos trident (30%)

**Gold Drop:** 2–8g


#### Cave Crawler (faction scouts) (combat)

<p align="center"><img src="../data/portraits/events/evt_3016.png" width="300"/></p>

**Difficulty:** 1 &nbsp; **Occurrences:** 1

> *A massive spider with a wet, glistening carapace that reflects moonlight. Its legs end in sharp points that click against stone as it moves through the flooded passages.*

**Monster Lineup:**

- **Cave Crawler** — HP 10-14, AC 12-14, atk: piercing, weakness: fire

**Loot:**

- salted cod strips (24%)

**Gold Drop:** 2–8g


#### Hostile Bloodtide Raider (combat)

<p align="center"><img src="../data/portraits/events/evt_3018.png" width="300"/></p>

**Difficulty:** 1 &nbsp; **Occurrences:** 3

> *A lean goblin with gills behind pointed ears and webbed fingers, body painted with crimson algae. Water drips constantly from its scaled skin as it screeches battle cries.*

**Monster Lineup:**

- **Bloodtide Raider** — HP 6-10, AC 11-13, atk: slashing, element: water, weakness: fire

**Loot:**

- storm rations (25%)

**Gold Drop:** 2–8g


#### Encounter: Bloodsurge Krex (combat) — **GATE GUARDIAN**

<p align="center"><img src="../data/portraits/events/evt_3023.png" width="300"/></p>

**Difficulty:** 1 &nbsp; **Occurrences:** 1

> *A towering goblin whose barrel chest heaves as gills flutter along his thick neck. Barnacle clusters form natural armor across his shoulders while electricity arcs between his trident's prongs.*

**Monster Lineup:**

- **Bloodsurge Krex** — HP 32-42, AC 14-16, atk: piercing, element: water, weakness: forest

**Loot:**

- coral fungus (16%)
- dock hook (38%)
- rope and grapnel (37%)

**Gold Drop:** 2–8g


#### Ambush: Bloodtide Raider (combat)

<p align="center"><img src="../data/portraits/events/evt_3025.png" width="300"/></p>

**Difficulty:** 1 &nbsp; **Occurrences:** 1

> *A lean goblin with gills behind pointed ears and webbed fingers, body painted with crimson algae. Water drips constantly from its scaled skin as it screeches battle cries.*

**Monster Lineup:**

- **Bloodtide Raider** — HP 6-10, AC 11-13, atk: slashing, element: water, weakness: fire

**Loot:**

- barnacle clusters (25%)

**Gold Drop:** 2–8g


#### Cave Crawler Attack (combat)

<p align="center"><img src="../data/portraits/events/evt_3026.png" width="300"/></p>

**Difficulty:** 1 &nbsp; **Occurrences:** 1

> *A massive spider with a wet, glistening carapace that reflects moonlight. Its legs end in sharp points that click against stone as it moves through the flooded passages.*

**Monster Lineup:**

- **Cave Crawler** — HP 10-14, AC 12-14, atk: piercing, weakness: fire

**Loot:**

- lighthouse keeper's blessed mace (27%)
- scroll of kraken's sight (14%)
- tide-touched trident (24%)

**Gold Drop:** 2–8g


#### Coral-Crusted Shambler Attack (combat)

<p align="center"><img src="../data/portraits/events/evt_3027.png" width="300"/></p>

**Difficulty:** 1 &nbsp; **Occurrences:** 1

> *A bloated human figure encrusted with barnacles and sea anemones. Saltwater pours from its mouth as it lurches forward, coral growths sprouting from its joints.*

**Monster Lineup:**

- **Coral-Crusted Shambler** — HP 12-16, AC 9-11, atk: bludgeoning, element: water, weakness: fire

**Loot:**

- harbor grog (16%)

**Gold Drop:** 2–8g


#### Ambush: Coral-Crusted Shambler (combat)

<p align="center"><img src="../data/portraits/events/evt_3029.png" width="300"/></p>

**Difficulty:** 1 &nbsp; **Occurrences:** 1

> *A bloated human figure encrusted with barnacles and sea anemones. Saltwater pours from its mouth as it lurches forward, coral growths sprouting from its joints.*

**Monster Lineup:**

- **Coral-Crusted Shambler** — HP 12-16, AC 9-11, atk: bludgeoning, element: water, weakness: fire

**Loot:**

- storm rations (19%)
- warren shiv (32%)

**Gold Drop:** 2–8g


#### Ambush: Cave Crawler (combat)

<p align="center"><img src="../data/portraits/events/evt_3030.png" width="300"/></p>

**Difficulty:** 1 &nbsp; **Occurrences:** 1

> *A massive spider with a wet, glistening carapace that reflects moonlight. Its legs end in sharp points that click against stone as it moves through the flooded passages.*

**Monster Lineup:**

- **Cave Crawler** — HP 10-14, AC 12-14, atk: piercing, weakness: fire

**Loot:**

- chaos trident (28%)
- salted cod strips (34%)
- barnacle clusters (12%)

**Gold Drop:** 2–8g


#### Encounter: Coral-Crusted Shambler (combat)

<p align="center"><img src="../data/portraits/events/evt_3031.png" width="300"/></p>

**Difficulty:** 1 &nbsp; **Occurrences:** 1

> *A bloated human figure encrusted with barnacles and sea anemones. Saltwater pours from its mouth as it lurches forward, coral growths sprouting from its joints.*

**Monster Lineup:**

- **Coral-Crusted Shambler** — HP 12-16, AC 9-11, atk: bludgeoning, element: water, weakness: fire

**Loot:**

- rainwater (20%)
- gill-rope (39%)
- driftwood cudgel (38%)

**Gold Drop:** 2–8g


#### Ambush: Tidecaller Grunt (combat)

<p align="center"><img src="../data/portraits/events/evt_3033.png" width="300"/></p>

**Difficulty:** 1 &nbsp; **Occurrences:** 1

> *A goblin adorned with shells and seaweed, chanting in gurgling tones while clutching a staff topped with a pulsing sea urchin. Bioluminescent algae glows faintly along its arms.*

**Monster Lineup:**

- **Tidecaller Grunt** — HP 8-12, AC 10-12, atk: bludgeoning, element: water, weakness: light

**Loot:**

- kraken kelp strips (36%)
- harbor grog (35%)

**Gold Drop:** 2–8g


#### Hostile Tidecaller Grunt, Bloodtide Raider (combat)

<p align="center"><img src="../data/portraits/events/evt_3001.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 1

> *A goblin adorned with shells and seaweed, chanting in gurgling tones while clutching a staff topped with a pulsing sea urchin. Bioluminescent algae glows faintly along its arms.*

**Monster Lineup:**

- **Tidecaller Grunt** — HP 8-12, AC 10-12, atk: bludgeoning, element: water, weakness: light
- **Bloodtide Raider** — HP 6-10, AC 11-13, atk: slashing, element: water, weakness: fire
- **Bloodtide Raider** — HP 6-10, AC 11-13, atk: slashing, element: water, weakness: fire

**Loot:**

- harbor grog (26%)
- medicinal kelp wine (32%)

**Gold Drop:** 4–16g


#### Encounter: Coral-Crusted Shambler, Bloodtide Raider (combat)

<p align="center"><img src="../data/portraits/events/evt_3005.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 1

> *A bloated human figure encrusted with barnacles and sea anemones. Saltwater pours from its mouth as it lurches forward, coral growths sprouting from its joints.*

**Monster Lineup:**

- **Coral-Crusted Shambler** — HP 12-16, AC 9-11, atk: bludgeoning, element: water, weakness: fire
- **Bloodtide Raider** — HP 6-10, AC 11-13, atk: slashing, element: water, weakness: fire
- **Bloodtide Raider** — HP 6-10, AC 11-13, atk: slashing, element: water, weakness: fire

**Loot:**

- gulpfin's brew (19%)
- scroll of deep sight (36%)

**Gold Drop:** 4–16g


#### Coral-Crusted Shambler, Cave Crawler Attack (combat)

<p align="center"><img src="../data/portraits/events/evt_3011.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 1

> *A bloated human figure encrusted with barnacles and sea anemones. Saltwater pours from its mouth as it lurches forward, coral growths sprouting from its joints.*

**Monster Lineup:**

- **Coral-Crusted Shambler** — HP 12-16, AC 9-11, atk: bludgeoning, element: water, weakness: fire
- **Cave Crawler** — HP 10-14, AC 12-14, atk: piercing, weakness: fire

**Loot:**

- kraken-bone maul (24%)

**Gold Drop:** 4–16g


#### Ambush: Coral-Crusted Shambler, Bloodtide Raider (combat)

<p align="center"><img src="../data/portraits/events/evt_3014.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 1

> *A bloated human figure encrusted with barnacles and sea anemones. Saltwater pours from its mouth as it lurches forward, coral growths sprouting from its joints.*

**Monster Lineup:**

- **Coral-Crusted Shambler** — HP 12-16, AC 9-11, atk: bludgeoning, element: water, weakness: fire
- **Bloodtide Raider** — HP 6-10, AC 11-13, atk: slashing, element: water, weakness: fire
- **Bloodtide Raider** — HP 6-10, AC 11-13, atk: slashing, element: water, weakness: fire
- **Coral-Crusted Shambler** — HP 12-16, AC 9-11, atk: bludgeoning, element: water, weakness: fire

**Loot:**

- brine essence (40%)
- barnacle scraper (26%)
- tide scraper (36%)

**Gold Drop:** 4–16g


#### Tidecaller Grunt, Coral-Crusted Shambler (faction scouts) (combat)

<p align="center"><img src="../data/portraits/events/evt_3032.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 1

> *A goblin adorned with shells and seaweed, chanting in gurgling tones while clutching a staff topped with a pulsing sea urchin. Bioluminescent algae glows faintly along its arms.*

**Monster Lineup:**

- **Tidecaller Grunt** — HP 8-12, AC 10-12, atk: bludgeoning, element: water, weakness: light
- **Coral-Crusted Shambler** — HP 12-16, AC 9-11, atk: bludgeoning, element: water, weakness: fire

**Loot:**

- tide-striker (18%)
- coral fungus (12%)

**Gold Drop:** 4–16g


### Quest Walkthrough

<a id="4000"></a>

#### Mira's Request
**Type:** `escort` &nbsp; **Story Quest:** No

**Quest Giver:** [Mira Tidecaller](#room_0-npc-1001)

> *Mira Tidecaller needs your help.*

**Walkthrough:**

1. Speak to **Mira Tidecaller** to accept the escort quest.
2. The escort NPC will join as a follower (max 2 followers).
3. Escort them safely to (29, 7).
4. Stay within 2 tiles of the target zone to complete.

**Reward:** None

**Failure Penalty:** 2 HP damage

**On Success:** "We made it. I'm safe now, thanks to you. Take this for your bravery."

**On Failure:** "I... I can't go on. Leave me here."


<a id="4001"></a>

#### Scout's Request
**Type:** `solve` &nbsp; **Story Quest:** No

**Quest Giver:** [Scout Finwick](#room_0-npc-1002)

> *Scout Finwick needs your help.*

**Walkthrough:**

1. Speak to **Scout Finwick** to accept the quest.
2. Solve event `3068`.

**Reward:** None

**Failure Penalty:** 2 HP damage

**On Success:** "I knew you could handle it. Take this for your trouble."

**On Failure:** "It's still unresolved. Come back when you're ready."


<a id="4002"></a>

#### Captain's Request
**Type:** `combat` &nbsp; **Story Quest:** Yes

**Quest Giver:** [Captain Merrick](#room_0-npc-1003)

> *Captain Merrick needs your help.*

**Walkthrough:**

1. Speak to **Captain Merrick** to accept the quest.
2. Find and complete combat event `?`.

**Reward:** None

**Failure Penalty:** 2 HP damage

**On Success:** "You bested them. A deal is a deal — take your prize."

**On Failure:** "They were too strong. I'm sorry, I have nothing left to give."


<a id="4003"></a>

#### Tam's Request
**Type:** `fetch` &nbsp; **Story Quest:** Yes

**Quest Giver:** [Tam Reefsong](#room_0-npc-1004)

> *Tam Reefsong needs your help.*

**Walkthrough:**

1. Speak to **Tam Reefsong** to accept the quest.
2. Find a **drink** item at tile (37, 13).
3. Return to **Tam Reefsong** with the item.

**Reward:** None

**Failure Penalty:** 2 HP damage

**On Success:** "You found it! This means more to me than you know. Please, take this."

**On Failure:** "Without it, I can't help you. Maybe another time."


<a id="4004"></a>

#### Elder's Request
**Type:** `escort` &nbsp; **Story Quest:** Yes

**Quest Giver:** [Elder Thessa](#room_0-npc-1006)

> *Elder Thessa needs your help.*

**Walkthrough:**

1. Speak to **Elder Thessa** to accept the escort quest.
2. The escort NPC will join as a follower (max 2 followers).
3. Escort them safely to (29, 7).
4. Stay within 2 tiles of the target zone to complete.

**Reward:** None

**Failure Penalty:** 2 HP damage

**On Success:** "We made it. I'm safe now, thanks to you. Take this for your bravery."

**On Failure:** "I... I can't go on. Leave me here."


<a id="4005"></a>

#### Young's Request
**Type:** `escort` &nbsp; **Story Quest:** Yes

**Quest Giver:** [Young Willem](#room_0-npc-1007)

> *Young Willem needs your help.*

**Walkthrough:**

1. Speak to **Young Willem** to accept the escort quest.
2. The escort NPC will join as a follower (max 2 followers).
3. Escort them safely to (29, 7).
4. Stay within 2 tiles of the target zone to complete.

**Reward:** None

**Failure Penalty:** 2 HP damage

**On Success:** "We made it. I'm safe now, thanks to you. Take this for your bravery."

**On Failure:** "I... I can't go on. Leave me here."


> **Gate Encounter:** This room's exit is guarded by event `3023`. You must defeat it to proceed.

---

<a id="room-1"></a>

## Room 1: Goblin Warren
*Environment: cave — Level 2*

<p align="center"><img src="../data/portraits/environment_1.png" width="500"/></p>

### Room Introduction

The cavern opens before you like the maw of some primordial beast, its walls alive with hundreds of crimson-daubed goblins that cling to the stone like living barnacles, their gills pulsing wetly in the fetid air. Sickly green bioluminescence from corrupted algae casts writhing shadows across the flooded passages, while the rhythmic splash of rising seawater mingles with distant, guttural chanting that seems to pulse through your very bones. The stench of salt, decay, and ancient evil fills your nostrils as you realize the true scope of the Bloodtide Clan's infestation—this warren extends far deeper

### Story Beat

Deep within the flooded Goblin Warren, the true horror of the Bloodtide Clan's stronghold becomes apparent as heroes descend into chambers where seawater and darkness converge. The clan's numbers have swollen beyond imagination - hundreds of goblins cling to the cavern walls like crimson barnacles, their gills fluttering in the humid air. Shaman Gulpfin conducts a grotesque ritual over captured villagers suspended above tidal pools, preparing them as offerings for Kraken-Maw's shrine. The warren pulses with unnatural life as bioluminescent algae paint the walls in sickly green light, and somewhere deeper, the rhythmic chanting of Tide-Caller Grix echoes through the flooded passages, growing stronger with each sacrifice.

### Faction Presence

The Bloodtide Clan has transformed the natural cave system into a sprawling underwater fortress. They have carved worship alcoves into the walls, created tidal pools for their young, and established a breeding ground where their numbers multiply exponentially. The clan uses the flooded passages to move unseen throughout their domain while preparing for their final assault on the surface.

### Boss: Depthcrawler Vex, the Warren's Heart-Keeper

> *A grotesquely swollen goblin whose body has partially merged with the cavern's coral growths. Tentacle-like appendages writhe from his back while his eyes glow with bioluminescent fury. He guards the warren's central chamber with fanatical devotion.*

### Level Map

<p align="center"><img src="../data/portraits/maps/room_1_map.png" /></p>

### Item Catalog

| ID | Name | Category | Description | Stats |
|----|------|----------|-------------|-------|
| 2019 | kraken kelp strips | food | Chewy seaweed harvested from Bloodtide feeding grounds. | +14 stamina, +7 HP, 1 uses, 7g |
| 2020 | barnacle clusters | food | Sharp-shelled crustaceans pried from warren walls. | +14 stamina, +6 HP, 1 uses, 10g |
| 2021 | tide pool gruel | food | Murky stew of cave fish and crimson algae. | +7 stamina, +3 HP, 1 uses, 18g |
| 2022 | coral fungus | food | Bioluminescent mushrooms grown on dead coral. | +15 stamina, +6 HP, 1 uses, 11g |
| 2023 | brackish seep | drink | Salty water dripping from limestone formations. | +5 stamina, +3 HP, 1 uses, 10g |
| 2024 | gulpfin's brew | drink | Fermented algae drink blessed by clan shamans. | +13 stamina, +7 HP, 1 uses, 16g |
| 2025 | tidal draught | drink | Ceremonial mixture of seawater and goblin blood. | +16 stamina, +3 HP, 1 uses, 13g |
| 2026 | brine essence | drink | Concentrated saltwater infused with dark magic. | +19 stamina, +7 HP, 1 uses, 7g |
| 2027 | coral chisel | tool | Sharpened coral fragment for carving ritual marks. | +-5 stamina, 3 uses, 31g |
| 2028 | gill-rope | tool | Woven kelp strands slick with goblin mucus. | +-5 stamina, 3 uses, 15g |
| 2029 | barnacle scraper | tool | Curved shell tool for harvesting cave growths. | +-5 stamina, 3 uses, 24g |
| 2030 | kraken-bone maul | weapon | Massive club carved from ancient sea demon remains. | 1d10 dmg, heavy, bludgeoning, STR, 45g |
| 2031 | tide-striker | weapon | Swift coral blade that drips with seawater. | 1d8 dmg, light, bludgeoning, DEX, 28g |
| 2032 | chaos trident | weapon | Three-pronged spear crackling with unpredictable energy. | 1d8 dmg, wild, piercing, LUCK, 37g |
| 2033 | depth-caller staff | weapon | Twisted driftwood staff crowned with pulsing algae. | 1d6 dmg, arcane, slashing, INT, 23g |
| 2034 | warren shiv | weapon | Razor-sharp blade knapped from volcanic glass. | 1d8 dmg, light, piercing, DEX, 45g |
| 2035 | bloodtide cleaver | weapon | Runic machete etched with tidal prophecies. | 1d6 dmg, enchanted, slashing, WIS, 17g |
| 2036 | scroll of crimson ward | spell_scroll | Algae-painted script that hardens skin like coral. | 39g |
| 2037 | scroll of kraken's sight | spell_scroll | Reveals hidden passages through bioluminescent vision. | 35g |

### NPC Directory

<a id="room_1-npc-1016"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1016.png" width="200"/></p>

#### Skritt Bloodbrine

**Job:** warren guard who questions the endless sacrifices<br/>**Type:** StaticNPC<br/>**Personality:** restless and increasingly horrified by the escalating brutality, torn between clan loyalty and moral disgust

> *Skritt has guarded these tunnels since the clan first discovered Kraken-Maw's shrine, but lately the rituals have grown more frequent and more vicious. He remembers when they only took offerings during the dark moon, now Gulpfin demands fresh victims every tide cycle. The captured villagers remind him too much of the surface-dwellers who once showed his wounded cousin mercy years ago. He knows speaking against the rituals means death, but watching children lowered into the sacrifice pools is breaking something inside him that even Kraken-Maw's corruption cannot touch.*

**Opening Greeting:**
> "*shifts nervously, crimson algae paint streaking down his face* Another batch for the pools... I've lost count of how many we've taken. You're not here for the ritual, are you?"


<a id="room_1-npc-1017"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1017.png" width="200"/></p>

#### Glurp Tidegnaw

**Job:** tunnel maintenance goblin<br/>**Type:** StaticNPC<br/>**Personality:** simple-minded but observant, notices patterns others miss

> *Glurp maintains the warren's drainage channels and has noticed that each major ritual causes the seawater levels to rise throughout the cavern system. The bioluminescent algae grows brighter after every sacrifice, and strange new passages keep opening deeper in the rock. He cannot understand the magical forces at work, but his intimate knowledge of the warren's water flow makes him invaluable to anyone trying to navigate or escape the flooded tunnels.*

**Opening Greeting:**
> "*looks up from scraping barnacles off tunnel walls* Eh? More water coming in from the deep tunnels lately. More sounds too. Big sounds."


<a id="room_1-npc-1018"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1018.png" width="200"/></p>

#### Razz Coralpeddler

**Job:** merchant selling ritual components and warren supplies<br/>**Type:** MerchantNPC<br/>**Personality:** opportunistic and amoral, thrives on the clan's dark prosperity

> *Razz arrived at the warren just as the sacrificial rituals intensified, drawn by the profit potential of supplying Gulpfin's increasingly elaborate ceremonies. She trades with surface smugglers who slip into the lower caves during high tide, exchanging stolen goods for the exotic components the shaman demands. Her inventory includes rope woven from giant kelp, ceremonial daggers carved from whale bone, and various salves made from deep-sea creatures. She has no moral qualms about profiting from murder, viewing the captive villagers as simply another commodity in her gruesome trade.*

**Opening Greeting:**
> "*grins widely, displaying rows of filed teeth* Welcome, welcome! Looking for ritual supplies? Fresh coral dust, blessed barnacles? Business has never been better!"

**Shop Inventory:**

| Item | Price | Stock |
|------|-------|-------|
| chaos trident | 37g | 1 |
| tide-striker | 28g | 4 |
| tide scraper | 21g | 3 |
| bloodtide cleaver | 17g | 3 |
| kraken kelp strips | 7g | 4 |
| tide pool gruel | 18g | 5 |
| barnacle scraper | 24g | 2 |
| scroll of crimson ward | 39g | 1 |


<a id="room_1-npc-1019"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1019.png" width="200"/></p>

#### Finn Saltweep

**Job:** captured fisherman from Saltwind Harbor<br/>**Type:** RandomNPC<br/>**Personality:** desperate but resourceful, knows the coastal waters better than anyone

> *Finn was captured three weeks ago when his fishing boat ventured too close to the hidden cave entrance during a fog bank. The Bloodtide goblins killed his two crew members immediately but kept him alive when they learned of his extensive knowledge of the coastal currents and tide schedules. He has overheard enough of Gulpfin's rituals to understand that the shaman is using the natural tide cycles to amplify Kraken-Maw's power, and he believes disrupting the timing could weaken the demon's hold on the clan. He knows exactly when the next major ebb tide will expose the shrine's foundation stones.*

**Opening Greeting:**
> "*looks up with haunted eyes, seaweed rope binding his wrists* You're not one of them... please, I know these waters like my own blood. I can help you if you help me."

**Quest:** [4006](#4006)


<a id="room_1-npc-1020"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1020.png" width="200"/></p>

#### Kelp-Eye Vrex

**Job:** shrine tender who feeds the sacrifice pools<br/>**Type:** RandomNPC<br/>**Personality:** fanatically devoted to Kraken-Maw, believes suffering purifies the offerings

> *Vrex tends the tidal pools where victims are prepared for sacrifice, believing that their fear and pain make them more acceptable to Kraken-Maw. He was one of the first goblins to witness the demon's shrine when it was discovered, and the experience left him completely transformed—both physically and mentally. Strange kelp-like growths now sprout from his skull, and he claims they allow him to hear Kraken-Maw's whispers directly. He needs someone to help him retrieve a sacred conch shell from the deepest flooded chamber, believing it will amplify the demon's power during the next major ritual.*

**Opening Greeting:**
> "*bows deeply, eyes reflecting bioluminescent algae* Blessed visitor to Kraken-Maw's sacred pools! The offerings grow stronger with each tide. Do you bring tribute for the depths?"

**Quest:** [4007](#4007)


<a id="room_1-npc-1021"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1021.png" width="200"/></p>

#### Sprat Quickgill

**Job:** young goblin scout who brings news from the surface raids<br/>**Type:** RandomNPC<br/>**Personality:** eager to prove himself but secretly terrified of the escalating violence

> *Sprat is barely past adolescence and joined the warren scouts hoping to earn his place in the clan through daring surface raids. However, the increasing brutality of the attacks has left him shaken, especially after witnessing the massacre of an entire fishing family last week. He has critical intelligence about a counter-attack being organized by the surviving villagers of Saltwind Harbor, but he is too low in the clan hierarchy to reach Grix directly. He needs someone to help him navigate the warren's political structure and get his warning to the Tide-Caller before the villagers launch their desperate assault.*

**Opening Greeting:**
> "*salutes shakily* Just back from surface patrol! The raids... they're getting bigger. Gulpfin wants more prisoners for the deep ritual."

**Quest:** [4008](#4008)


<a id="room_1-npc-1022"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1022.png" width="200"/></p>

#### Murg the Wallcrawler

**Job:** tunnel digger who maintains the warren's upper passages<br/>**Type:** StaticNPC<br/>**Personality:** paranoid and obsessive, convinced the walls are listening

> *Murg digs and maintains the warren's network of passages, but lately he has noticed disturbing changes in the cavern structure itself. The stone has become soft and organic in places, almost flesh-like to the touch, and he swears he can hear a massive heartbeat echoing through the deepest tunnels. His paranoia is actually well-founded—the warren is slowly transforming into something alive under Kraken-Maw's influence. He spends his time frantically carving protective wards into any surface he can reach, convinced that the demon's corruption is spreading through the very rock. Other goblins think he has gone mad, but his intimate knowledge of the warren's changing layout makes him invaluable.*

**Opening Greeting:**
> "*whispers while constantly glancing at the walls* Shh! Keep your voice down! The walls... they pulse now. They hear everything since the deep digging began."


<a id="room_1-npc-1023"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1023.png" width="200"/></p>

#### Bubble-Throat Nix

**Job:** messenger who carries word between the warren levels<br/>**Type:** StaticNPC<br/>**Personality:** chatty gossip who knows everyone's business but lacks discretion

> *Nix swims through the flooded passages carrying messages between the warren's different levels, and her routes take her past every important conversation in the complex. She has overheard heated arguments between Gulpfin and Grix about the pace of the sacrifices—the shaman wants to accelerate the rituals but the Tide-Caller fears they are drawing too much attention from the surface world. Nix loves to gossip and will eagerly share what she has heard with anyone who shows interest, though she rarely understands the significance of the information she passes along.*

**Opening Greeting:**
> "*makes gurgling greeting sounds* Oh! A newcomer! I carry messages all through the warren - I know everything that happens! Want to hear the latest gossip?"


<a id="room_1-npc-1024"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1024.png" width="200"/></p>

#### Ebb-Tooth Grak

**Job:** veteran raider who trains the younger goblins<br/>**Type:** StaticNPC<br/>**Personality:** old and battle-scarred, growing weary of the endless bloodshed

> *Grak has led surface raids for decades and remembers when the Bloodtide Clan took only what they needed to survive. The discovery of Kraken-Maw's shrine changed everything, transforming practical raids into religious massacres that serve no purpose beyond feeding the demon's hunger. He is too loyal to openly rebel but increasingly questions orders that send his young raiders to their deaths in pointless attacks. His experience makes him a valuable trainer, but his growing dissatisfaction with the clan's direction puts him at odds with the younger, more fanatical goblins.*

**Opening Greeting:**
> "*spits into the tidal pool* Another day, another batch of younglings to train in the old ways. Though these days, the ways get bloodier with each tide."


<a id="room_1-npc-1025"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1025.png" width="200"/></p>

#### Tide-Pool Yara

**Job:** captured village healer held as a 'special offering'<br/>**Type:** StaticNPC<br/>**Personality:** defiant despite captivity, still trying to help other prisoners

> *Yara was the village healer in a coastal settlement destroyed by the Bloodtide Clan two months ago. Instead of immediate sacrifice, Gulpfin has kept her alive, believing that prolonged suffering will make her death more pleasing to Kraken-Maw. During her captivity she has treated the wounds of other prisoners and observed the goblins' behavior patterns. She has noticed that several goblins show signs of poisoning from the corrupted algae they consume, and she believes she could create an antidote from seaweed found in the lower pools—if she could gather enough without being detected. Her medical knowledge makes her invaluable to any rescue or resistance effort.*

**Opening Greeting:**
> "*looks up with defiant eyes despite her bonds* I won't bow to your sea demon, and neither should you. These people still have hope if someone fights for them."


<a id="room_1-npc-1026"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1026.png" width="200"/></p>

#### Kraken-Kiss Blix

**Job:** shrine guardian who has been partially transformed by demon magic<br/>**Type:** StaticNPC<br/>**Personality:** eerily calm and detached, speaks in riddles about the deep mysteries

> *Blix guards the approaches to Kraken-Maw's shrine and has been exposed to the demon's influence longer than most. Tentacle-like growths have begun replacing his arms, and his eyes now glow with the same bioluminescent fury as the algae. Despite his transformation, some fragment of his original personality remains, creating an unsettling combination of goblin cunning and eldritch wisdom. He speaks in metaphors about currents and depths that few can understand, but his words often contain valuable information about the warren's defenses and the demon's weaknesses.*

**Opening Greeting:**
> "*speaks in an eerily calm voice, tentacle-like growths swaying* The depths call to all things eventually. You walk paths that spiral ever downward, seeker of truths."


<a id="room_1-npc-1027"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1027.png" width="200"/></p>

#### Gulpfin

**Job:** chief shaman conducting the sacrifice rituals<br/>**Type:** RandomNPC<br/>**Personality:** brilliantly cunning but completely insane, devoted to Kraken-Maw above all else

> *Gulpfin discovered Kraken-Maw's shrine during a deep diving expedition and immediately fell under the demon's influence. He has since orchestrated the clan's transformation from simple raiders into fanatical cultists, interpreting every success as proof of the demon's favor. His rituals have grown increasingly elaborate and frequent as he seeks to fully awaken Kraken-Maw's power, but the magical energies involved are beyond his complete understanding. He needs someone to help him decipher ancient runes around the shrine that he believes will unlock the demon's true potential, unaware that doing so would likely destroy the warren and everyone in it.*

**Opening Greeting:**
> "*raises his gnarled staff dripping with seaweed* Kraken-Maw hungers, and the tide brings fresh offerings! Do you come to witness the glory of the depths?"

**Quest:** [4009](#4009)


<a id="room_1-npc-1028"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1028.png" width="200"/></p>

#### Shipwreck Salla

**Job:** merchant dealing in salvaged goods from surface raids<br/>**Type:** MerchantNPC<br/>**Personality:** pragmatic businesswoman who treats horror as just another commodity

> *Salla operates a grotesque marketplace in one of the warren's side chambers, selling items looted from the Bloodtide Clan's increasingly violent raids. She has no interest in the religious aspects of the clan's transformation, viewing the escalating brutality simply as good for business. Her inventory includes weapons, coins, jewelry, and personal items taken from destroyed villages, all organized with meticulous care. She maintains detailed records of every raid and knows exactly which items came from which settlements, making her a valuable source of information about the clan's recent activities and the fate of specific captives.*

**Opening Greeting:**
> "Welcome to my collection! Fresh goods from the latest surface raids - weapons, jewelry, family heirlooms still warm from their owners' hands!"

**Shop Inventory:**

| Item | Price | Stock |
|------|-------|-------|
| scroll of crimson ward | 39g | 2 |
| brackish seep | 10g | 3 |
| tidal draught | 13g | 2 |
| salted cod strips | 12g | 3 |
| warren shiv | 45g | 1 |
| kraken-bone maul | 45g | 2 |
| rainwater | 12g | 3 |
| dock hook | 19g | 4 |


<a id="room_1-npc-1029"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1029.png" width="200"/></p>

#### Captain Daven Stormwright

**Job:** captured ship captain who knows secret routes through the coastal caves<br/>**Type:** RandomNPC<br/>**Personality:** proud naval officer struggling to maintain dignity in captivity

> *Captain Stormwright was captured when his patrol ship was ambushed by Bloodtide raiders near the hidden cave entrance. His knowledge of naval tactics and coastal geography makes him too valuable for immediate sacrifice, so Gulpfin has kept him alive for interrogation about surface defenses. Stormwright has hidden emergency supplies in a sea cave accessible only during low tide, including weapons, rope, and signal flares that could aid in a mass escape. He needs someone to help him reach the cache and coordinate with the other prisoners, but the window of opportunity only occurs during the brief periods when the warren's water level drops.*

**Opening Greeting:**
> "Help me reach my ship's emergency cache, and I can get us all out of here when the tide turns!"

**Quest:** [4010](#4010)


<a id="room_1-npc-1030"></a>

<p align="center"><img src="../data/portraits/npcs/npc_1030.png" width="200"/></p>

#### Drip-Eye Zeff

**Job:** cook who prepares meals from captured surface provisions<br/>**Type:** StaticNPC<br/>**Personality:** nervous wreck who jumps at every sound, terrified of being noticed

> *Zeff cooks for the warren using provisions looted from surface raids, but the job has made him intimately familiar with the clan's food stores and supply routes. He knows exactly how much food comes from which raids and can tell when major attacks are being planned by the sudden influx of provisions. His kitchen is also where he overhears conversations between returning raiders, giving him knowledge of failed attacks, casualties, and changes in surface defenses. He is terrified of being dragged into the political struggles within the warren and desperately wants to remain invisible, but his information could be crucial to understanding the clan's current capabilities and future plans.*

**Opening Greeting:**
> "Kitchen duties, just kitchen duties! Don't tell Gulpfin I talked to surface folk, please!"


### Monster Bestiary

<table><tr>
<td width="220"><img src="../data/portraits/monsters/mon_barnacle_warrior.png" width="200"/></td>
<td>
<h3>Barnacle Warrior</h3>
<b>Species:</b> corrupted bloodtide goblin<br/>
<b>Level:</b> 2<br/>
<b>HP:</b> 20-28 &nbsp; <b>AC:</b> 13-15<br/>
<b>Damage:</b> 1d6/1d8 physical<br/>
<b>Physical Type:</b> piercing<br/>
<b>Element:</b> water<br/>
<b>Weakness:</b> light<br/>
<b>Magic Resist:</b> 0<br/>
<b>Encounters:</b> 9 &nbsp; <b>Rooms:</b> room_1
</td>
</tr></table>

> *A heavily mutated goblin whose skin has hardened into barnacle-like growths. Coral spikes jut from its knuckles as it scuttles across wet stone with unnatural speed.*

**Abilities:**

- **Coral Spike** (damage) — 1d6 dmg, 30% chance
- **Barnacle Burst** (poison) — 1d4 dmg, 25% chance


<table><tr>
<td width="220"><img src="../data/portraits/monsters/mon_crimson_tidecaller.png" width="200"/></td>
<td>
<h3>Crimson Tidecaller</h3>
<b>Species:</b> bloodtide goblin<br/>
<b>Level:</b> 2<br/>
<b>HP:</b> 15-22 &nbsp; <b>AC:</b> 11-13<br/>
<b>Damage:</b> 1d6/1d8 water<br/>
<b>Physical Type:</b> bludgeoning<br/>
<b>Element:</b> water<br/>
<b>Weakness:</b> fire<br/>
<b>Magic Resist:</b> 0<br/>
<b>Encounters:</b> 10 &nbsp; <b>Rooms:</b> room_1
</td>
</tr></table>

> *A lithe goblin with webbed fingers and gills along its neck, painted in crimson algae. It chants in guttural tones while manipulating water currents with ritual gestures.*

**Abilities:**

- **Tide Surge** (damage) — 1d8 dmg, 40% chance
- **Kraken's Whisper** (stun) — 0d0 dmg, 20% chance


<table><tr>
<td width="220"><img src="../data/portraits/monsters/mon_depth_stalker.png" width="200"/></td>
<td>
<h3>Depth Stalker</h3>
<b>Species:</b> bloodtide goblin hunter<br/>
<b>Level:</b> 2<br/>
<b>HP:</b> 12-18 &nbsp; <b>AC:</b> 12-14<br/>
<b>Damage:</b> 1d6/1d8 physical<br/>
<b>Physical Type:</b> piercing<br/>
<b>Element:</b> dark<br/>
<b>Weakness:</b> light<br/>
<b>Magic Resist:</b> 0<br/>
<b>Encounters:</b> 5 &nbsp; <b>Rooms:</b> room_1
</td>
</tr></table>

> *A sleek goblin with enlarged gills and luminescent eyes that pierce the darkness. It moves silently through the flooded passages, ambushing intruders with bone harpoons.*

**Abilities:**

- **Bone Harpoon** (damage) — 1d8 dmg, 35% chance
- **Shadow Strike** (damage) — 1d6 dmg, 30% chance


<table><tr>
<td width="220"><img src="../data/portraits/monsters/mon_depthcrawler_vex,_the_warren's_heart-keeper.png" width="200"/></td>
<td>
<h3>Depthcrawler Vex, the Warren's Heart-Keeper</h3>
<b>Species:</b> corrupted bloodtide chieftain<br/>
<b>Level:</b> 2<br/>
<b>HP:</b> 45-60 &nbsp; <b>AC:</b> 15-17<br/>
<b>Damage:</b> 1d6/1d8 dark<br/>
<b>Physical Type:</b> bludgeoning<br/>
<b>Element:</b> dark<br/>
<b>Weakness:</b> light<br/>
<b>Magic Resist:</b> 0<br/>
<b>Encounters:</b> 1 &nbsp; <b>Rooms:</b> room_1
</td>
</tr></table>

> *A massively swollen goblin whose lower body has merged with living coral. Tentacles writhe from his back while his eyes burn with bioluminescent fury and ancient malice.*

**Abilities:**

- **Tentacle Lash** (damage) — 2d6 dmg, 40% chance
- **Kraken's Embrace** (stun) — 0d0 dmg, 25% chance
- **Coral Eruption** (damage) — 1d10 dmg, 30% chance


<table><tr>
<td width="220"><img src="../data/portraits/monsters/mon_tidepool_spawn.png" width="200"/></td>
<td>
<h3>Tidepool Spawn</h3>
<b>Species:</b> kraken-touched abomination<br/>
<b>Level:</b> 2<br/>
<b>HP:</b> 18-25 &nbsp; <b>AC:</b> 10-12<br/>
<b>Damage:</b> 1d6/1d8 water<br/>
<b>Physical Type:</b> bludgeoning<br/>
<b>Element:</b> water<br/>
<b>Weakness:</b> fire<br/>
<b>Magic Resist:</b> 0<br/>
<b>Encounters:</b> 10 &nbsp; <b>Rooms:</b> room_1
</td>
</tr></table>

> *A writhing mass of goblin flesh merged with sea anemones and kelp. Multiple eyes blink from its translucent body as acidic secretions drip from its tendrils.*

**Abilities:**

- **Acid Tendril** (damage) — 1d6 dmg, 40% chance
- **Toxic Cloud** (poison) — 1d4 dmg, 30% chance


### Event Guide

#### Puzzles

#### Kraken-Maw's Ceremonial Seal (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3127.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A massive stone disc blocks the passage deeper into the warren, carved with writhing tentacle patterns that seem to move in the flickering bioluminescent light. Ancient goblin runes spiral around its edge, and dark water seeps from its cracks. This is clearly a sacred barrier protecting Shaman Gulpfin's ritual chamber beyond.*

**Choices:**

1. Speak the ancient words of command etched around the seal's perimeter [DC 19 CHA]
2. Excavate around the seal's base to find the hidden release mechanism [DC 19 CHA]
3. Channel fiery energy to shatter the corrupted stone
4. Call upon the sea's blessing to cleanse the dark magic binding it
5. Walk away *(auto-success)*

**Correct Tool:** digging
**Correct Ability:** Burning Bash


#### The Tidal Mechanism (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3128.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A complex array of barnacle-encrusted gears and pulleys controls the water level in this chamber, clearly designed by goblin engineers to flood or drain passages at will. Chunks of coral jam the mechanism while acidic algae has corroded several key components. The system must be restored to access the flooded tunnel ahead.*

**Choices:**

1. Analyze the gear ratios and rotational sequences to restore proper function [DC 22 INT]
2. Clear away the coral blockages from the main drive system [DC 22 INT]
3. Anchor yourself and manually force the corroded gears into alignment
4. Summon thorned vines to clear obstructions from the delicate mechanism
5. Walk away *(auto-success)*

**Correct Tool:** digging
**Correct Ability:** Anchor Hold


#### The Sacrificial Platform (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3129.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A grotesque altar rises from a tidal pool, constructed from fused goblin skulls and draped with still-writhing kelp. Captured villagers hang in bone cages above the churning water, while pressure plates around the platform's edge suggest a deadly trap. The altar must be dismantled to free the prisoners before the tide rises further.*

**Choices:**

1. Deduce the safe path across the pressure plates by studying their patterns [DC 19 INT]
2. Dig beneath the altar's foundation to collapse it safely [DC 19 INT]
3. Ignite the kelp bindings with controlled bursts of flame
4. Summon healing waters to dissolve the bone cage locks
5. Walk away *(auto-success)*

**Correct Tool:** digging
**Correct Ability:** Burning Bash


#### The Collapsed Passage (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3130.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A recent cave-in has sealed this tunnel with tons of coral debris and loose stone, likely triggered by the goblins to slow pursuit. Skeletal remains of ancient sea creatures jut from the blockage, and the sound of rushing water beyond suggests an urgent need for passage. The debris field stretches from floor to ceiling.*

**Choices:**

1. Apply brute force to punch through the weakest section of debris [DC 16 STR]
2. Slice through the tangled mess of coral and bone with precision cuts [DC 16 STR]
3. Rally the team with a commanding shout to coordinate the clearing effort
4. Summon a protective barrier to prevent further collapse during excavation
5. Walk away *(auto-success)*

**Correct Tool:** cutting
**Correct Ability:** Harbor's Call


#### The Bloodtide Conduit (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3131.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Tide-Caller Grix has carved channels throughout this chamber to amplify his ritual magic, with crimson water flowing in precise geometric patterns. The conduit system focuses dark energy toward the shrine deeper in the warren, growing stronger with each pulse. Ancient stone valves control the flow, but they're protected by writhing coral growths.*

**Choices:**

1. Calculate which valve combinations will disrupt the energy pattern most effectively [DC 19 INT]
2. Cut away the protective coral growths from the valve mechanisms [DC 19 INT]
3. Use seafaring knowledge to redirect the flow toward harmless channels
4. Unleash a tempest to overwhelm and destroy the entire conduit system
5. Walk away *(auto-success)*

**Correct Tool:** cutting
**Correct Ability:** Rigging Climb


#### The Hanging Garden of Kelp (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3132.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Massive curtains of kelp hang from the cavern ceiling, forming a living maze that shifts with each tidal current. Bioluminescent polyps within the kelp pulse in hypnotic patterns, clearly enchanted to disorient intruders. The path through this organic labyrinth leads to critical passages, but the kelp responds aggressively to disturbance.*

**Choices:**

1. Study the polyp patterns to determine the safe path through the maze [DC 22 INT]
2. Scale the cavern walls to find handholds above the kelp canopy [DC 22 INT]
3. Shatter through the kelp barriers with overwhelming force
4. Launch thorned projectiles to cut strategic pathways through the growth
5. Walk away *(auto-success)*

**Correct Tool:** climbing
**Correct Ability:** Shatter Defense


#### The Breathing Chamber (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3133.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *This spherical chamber fills and empties with each tide cycle, designed as a natural airlock for the deeper warren. Currently half-flooded, it requires precise timing to navigate as poisonous gases vent from holes near the ceiling when the water recedes. The exit tunnel sits just above the current water line.*

**Choices:**

1. Observe the timing patterns to predict the safest moment for passage [DC 15 WIS]
2. Excavate a drain channel to control the water level manually [DC 15 WIS]
3. Channel flame energy to burn away the toxic gases
4. Create thorned barriers to seal the gas vents temporarily
5. Walk away *(auto-success)*

**Correct Tool:** digging
**Correct Ability:** Burning Bash


#### The Midnight Feeding Pit (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3134.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A vertical shaft drops into black water where something massive stirs in the depths, visible only by night when bioluminescent plankton reveal its outline. Goblin feeding platforms ring the pit's edge, connected by rotting rope bridges that sway precariously over the abyss. The only exit lies on the far side of this nightmarish chasm.*

**Choices:**

1. Endure the toxic cave gases to cross quickly before succumbing [DC 21 CON]
2. Cut new rope handholds to reinforce the failing bridge structure [DC 21 CON]
3. Use climbing techniques to traverse the pit walls instead of the bridges
4. Summon protective woodland magic to shield against the pit's corruption
5. Walk away *(auto-success)*

**Correct Tool:** cutting
**Correct Ability:** Rigging Climb


#### The Barnacle Lock (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3135.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A living door of giant barnacles seals this passage, their shells opening and closing in a complex rhythm. Each barnacle must be triggered in the correct sequence to unlock the way forward, but touching them wrong causes acidic spray that has already scarred the surrounding stone. Climbing gear hangs abandoned nearby from previous failed attempts.*

**Choices:**

1. Recognize the natural rhythm patterns in the barnacles' movement cycles [DC 13 WIS]
2. Use climbing equipment to approach from angles that avoid the acid spray [DC 13 WIS]
3. Navigate the barnacle maze using rope work and precise positioning
4. Call upon forest magic to communicate with and calm the living door
5. Walk away *(auto-success)*

**Correct Tool:** climbing
**Correct Ability:** Rigging Climb


#### The Offering Bowl (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3136.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A massive conch shell, carved with intricate spiral patterns, sits in a shallow pool fed by a trickling waterfall. The shell must be filled to the exact waterline indicated by ancient goblin markings to open a hidden passage behind the falls. However, the pool constantly drains through cracks in its coral basin.*

**Choices:**

1. Calculate the optimal flow rate to overcome the drainage and reach the target level [DC 12 WIS]
2. Dig out the cracks and repair the basin to stop the constant drainage [DC 12 WIS]
3. Rally your voice to call upon ancient maritime blessing for the offering
4. Channel healing magic to seal the coral cracks and restore the basin
5. Walk away *(auto-success)*

**Correct Tool:** digging
**Correct Ability:** Beacon's Roar


#### The Kraken-Maw Pressure Valve (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3137.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A massive organic valve, crafted from fused goblin bones and giant sea urchin spines, blocks the passage ahead. The valve throbs with a sickly pulse, responding to pressure changes in the flooded chambers beyond. Ancient goblin runes carved around its rim suggest this mechanism regulates the warren's tidal flow, but it has sealed itself shut in response to intruders.*

**Choices:**

1. Study the tidal patterns and pressure changes to time the valve's natural cycle [DC 10 WIS]
2. Strike the pressure points with precise blows to force the mechanism open [DC 10 WIS]
3. Anchor yourself against the current and manually hold the valve steady
4. Channel healing energy to restore the valve's corrupted bio-rhythm
5. Walk away *(auto-success)*

**Correct Tool:** bludgeon
**Correct Ability:** Anchor Hold


#### The Barnacle Chimney Climb (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3138.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A near-vertical shaft rises through the warren's heart, its walls encrusted with razor-sharp barnacles that weep acidic brine. Goblin claw marks score the walls where countless clan members have climbed to reach the upper warrens. The shaft echoes with distant chanting from above, and phosphorescent slime provides the only light in the treacherous ascent.*

**Choices:**

1. Power through the climb using pure muscular strength and endurance [DC 16 STR]
2. Use climbing gear to navigate safely between the barnacle clusters [DC 16 STR]
3. Swing on goblin-made rope handholds to avoid the sharp edges
4. Call upon sea blessings to neutralize the acidic secretions
5. Walk away *(auto-success)*

**Correct Tool:** climbing
**Correct Ability:** Rigging Climb


#### The Coral Spire Obstruction (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3139.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A massive coral spire has grown across the tunnel, its living branches pulsing with dark energy fed by goblin blood sacrifices. The coral writhes when approached, its polyps snapping hungrily at any movement. Behind its twisted form, the sound of rushing water suggests it's blocking a crucial drainage channel that could flood the entire section.*

**Choices:**

1. Force your way through the coral's grip with overwhelming strength [DC 21 STR]
2. Use climbing techniques to scale over the coral mass safely [DC 21 STR]
3. Unleash a thunderous roar to shatter the coral's dark energy matrix
4. Strengthen your skin to resist the coral's acidic touch
5. Walk away *(auto-success)*

**Correct Tool:** climbing
**Correct Ability:** Beacon's Roar


#### The Bloodtide Clan's Tidal Lock (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3140.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *An ingenious goblin mechanism controls water flow between chambers, built from driftwood, bone, and scavenged ship parts. The lock responds to the clan's ritual chanting, but without proper coordination, it remains sealed. Carved goblin faces around the mechanism's rim seem to watch intruders, their empty eye sockets weeping seawater in an endless stream.*

**Choices:**

1. Endure the mechanism's toxic fumes while operating its complex gears [DC 12 CON]
2. Use climbing skills to reach and manipulate the overhead controls [DC 12 CON]
3. Channel the harbor's call to synchronize with the clan's ritual frequency
4. Shield yourself from the mechanism's harmful emanations
5. Walk away *(auto-success)*

**Correct Tool:** climbing
**Correct Ability:** Harbor's Call


#### The Deepwatch Sentry Post (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3141.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A narrow ledge spirals around a deep shaft where goblin sentries once kept watch over the warren's depths. The path has partially collapsed, leaving treacherous gaps where ancient support beams have rotted away. Far below, the sound of massive tentacles moving through dark water echoes upward, suggesting something enormous lurks in the depths.*

**Choices:**

1. Read the structural stability and plan the safest route across [DC 22 WIS]
2. Anchor yourself securely before attempting each dangerous crossing [DC 22 WIS]
3. Surge with healing energy to strengthen the weakened supports
4. Cast Healing Tsunami
5. Walk away *(auto-success)*

**Correct Tool:** climbing
**Correct Ability:** Anchor Hold


#### The Spine Coral Garden (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3142.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A chamber filled with towering spine coral formations creates a maze of needle-sharp obstacles. The coral has been cultivated by goblins as a defensive barrier, with some spines coated in paralytic toxins. Phosphorescent fish dart between the formations, their light revealing safe passages through the deadly garden.*

**Choices:**

1. Study the fish patterns to understand the safe pathways through [DC 10 WIS]
2. Carefully cut a direct route through the coral obstacles [DC 10 WIS]
3. Climb up and swing through the coral canopy above
4. Call forth forest magic to command the coral to part
5. Walk away *(auto-success)*

**Correct Tool:** cutting
**Correct Ability:** Rigging Climb


#### The Gruel Feeding Chamber (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3143.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A grotesque feeding chamber where goblins consume their tide pool gruel has become sealed by hardened algae deposits. The chamber reeks of fermented seaweed and worse things, but it contains the only passage forward. Goblin feeding implements hang from the ceiling like macabre wind chimes, clicking together in the stagnant air.*

**Choices:**

1. Use your charisma to commune with the chamber's lingering goblin spirits [DC 12 CHA]
2. Cut through the hardened algae seal with careful blade work [DC 12 CHA]
3. Sense the chamber's natural rhythm to find the optimal entry time
4. Protect yourself while breaking through the toxic barrier
5. Walk away *(auto-success)*

**Correct Tool:** cutting
**Correct Ability:** Storm Sense


#### The Mudskipper Nest Tunnel (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3144.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A low tunnel has become the nesting ground for giant mudskippers that serve as goblin guardians. The creatures have built elaborate mud dams that block passage, and their territorial nature makes them aggressive to intruders. Their eggs glow faintly in the darkness, creating an eerie constellation across the tunnel floor.*

**Choices:**

1. Navigate precisely through the nest without disturbing the sleeping creatures [DC 16 DEX]
2. Excavate an alternate route around the most heavily defended areas [DC 16 DEX]
3. Intimidate the mudskippers with an aggressive display
4. Use nature magic to calm and redirect the territorial creatures
5. Walk away *(auto-success)*

**Correct Tool:** digging
**Correct Ability:** Dock Brawler's Glare


#### The Blood Kelp Harvesting Station (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3145.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A goblin kelp harvesting operation has left twisted machinery half-submerged in crimson-stained water. The cutting apparatus has jammed with overgrown kelp, and toxic spores drift in the stagnant air. Goblin work songs still echo faintly from enchanted conch shells mounted around the chamber, their melody both haunting and maddening.*

**Choices:**

1. Use precise movements to clear the kelp without triggering the toxic release [DC 20 DEX]
2. Cut through the tangled kelp mass systematically [DC 20 DEX]
3. Channel burning energy to incinerate the kelp blockage
4. Summon a tempest to blast the obstruction clear
5. Walk away *(auto-success)*

**Correct Tool:** cutting
**Correct Ability:** Burning Bash


#### The Ritual Speaker's Podium (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3146.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A carved platform where goblin speakers address the warren rises from a tidal pool, connected only by narrow stone walkways. The podium itself pulses with dark energy, and goblin totems arranged around its base create a ward that must be disrupted. Ancient acoustics amplify any sound made here, threatening to alert the entire warren to intruders.*

**Choices:**

1. Use your natural charisma to speak the proper ritual words and gain passage [DC 19 CHA]
2. Carefully dismantle the totem ward using precise cutting techniques [DC 19 CHA]
3. Call upon the harbor's power to override the goblin ward magic
4. Embrace the ocean's protection while dismantling the dark totems
5. Walk away *(auto-success)*

**Correct Tool:** cutting
**Correct Ability:** Harbor's Call


#### The Crimson Communion Chamber (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3147.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A circular chamber carved from living rock pulses with bioluminescent veins that throb in rhythm with distant chanting. At its center, a massive conch shell sits atop a pedestal of fused coral and bone, its spiral chambers echoing with the whispers of ancient sea spirits. The goblin shamans once used this sacred horn to commune with Kraken-Maw during daylight hours when the demon's power waned, but now its mouth is sealed with hardened crimson algae.*

**Choices:**

1. Rally your voice to shatter the algae seal with commanding words [DC 17 CHA]
2. Scrape away the hardened algae barrier with careful excavation [DC 17 CHA]
3. Channel burning energy to melt through the ritual seal
4. Summon nature's fury to tear apart the corrupted growth
5. Walk away *(auto-success)*

**Correct Tool:** digging
**Correct Ability:** Burning Bash


#### The Webbed Gallery (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3148.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A narrow gallery stretches between two chambers, its walls honeycombed with goblin sleeping alcoves that drip with moisture from the high tide mark. Thick strands of bio-luminescent webbing span the passage at shoulder height, woven by the clan's deep-sea spiders and reinforced with kelp fibers. The sticky strands pulse with trapped nutrients from passing creatures, creating a living barrier that strengthens with each struggle.*

**Choices:**

1. Force your way through the webbing with brute strength [DC 15 STR]
2. Scale the walls above the web barrier using climbing techniques [DC 15 STR]
3. Sense the storm currents to predict the web's weak points
4. Raise a protective barrier while pushing through the strands
5. Walk away *(auto-success)*

**Correct Tool:** climbing
**Correct Ability:** Storm Sense


#### The Bone Siphon Lock (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3149.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A grotesque mechanism of fused whale ribs and goblin skulls blocks a crucial passage, its hollow chambers designed to filter seawater through a maze of bone channels. The Bloodtide engineers built this lock to keep their deepest secrets safe, requiring precise manipulation to align the bone chambers and allow passage. Green algae has grown thick in the channels, and the sound of trickling water echoes from within the macabre construction.*

**Choices:**

1. Study the bone arrangement to understand the mechanism's logic [DC 20 WIS]
2. Slice through the algae clogging the water channels [DC 20 WIS]
3. Hold your position steady while manipulating the delicate components
4. Pierce the blockage with conjured thorns to clear the channels
5. Walk away *(auto-success)*

**Correct Tool:** cutting
**Correct Ability:** Anchor Hold


#### The Putrid Breath Chamber (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3150.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *This claustrophobic chamber reeks of decay and stagnant seawater, its floor carpeted with rotting kelp and fish bones that release toxic gases with every step. The Bloodtide clan used this space to cure their catches, but the ritual corruption has turned it into a noxious trap that burns the lungs and clouds the mind. A narrow path of stable stones leads across the fetid bog, but one wrong step means sinking into the poisonous mire.*

**Choices:**

1. Endure the toxic fumes through sheer physical resilience [DC 21 CON]
2. Dig a drainage channel to reduce the gas buildup [DC 21 CON]
3. Use intimidating presence to cow the toxic spirits dwelling here
4. Unleash nature's wrath to purify the corrupted chamber
5. Walk away *(auto-success)*

**Correct Tool:** digging
**Correct Ability:** Dock Brawler's Glare


#### The Sacrificial Ledges (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3151.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A vertical shaft opens before you, its walls carved with hundreds of small ledges where the goblins once displayed the bones of their victims like grisly trophies. The ledges form a treacherous climbing route to the chamber above, but many are slick with moisture and others have cracked under the weight of their macabre burden. Fragments of bone and ritual trinkets rain down with each disturbance, threatening to knock climbers from their precarious holds.*

**Choices:**

1. Leap nimbly between the most stable ledges with perfect timing [DC 22 DEX]
2. Cut away the loose debris before attempting each handhold [DC 22 DEX]
3. Glare menacingly to intimidate the restless spirits guarding this place
4. Call down a tempest to clear the shaft of dangerous debris
5. Walk away *(auto-success)*

**Correct Tool:** cutting
**Correct Ability:** Dock Brawler's Glare


#### The Tidal Memory Pool (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3152.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *An ancient pool of perfectly still water reflects the chamber's bioluminescent ceiling like a mirror of stars, its surface unmarked by the chaos surrounding it. The goblin elders once gazed into these sacred waters to receive visions from Kraken-Maw, but the pool now holds memories of every atrocity committed in the warren. Approaching the water's edge causes ghostly images to dance across its surface, threatening to trap viewers in an endless cycle of the clan's darkest moments.*

**Choices:**

1. Perceive the true nature of the visions to resist their pull [DC 22 WIS]
2. Use climbing techniques to approach from above without gazing directly [DC 22 WIS]
3. Feel the storm's clarity to pierce through the illusions
4. Burst thorny brambles into the pool to disrupt its hypnotic surface
5. Walk away *(auto-success)*

**Correct Tool:** climbing
**Correct Ability:** Storm Sense


#### The Fossil Gate Seal (puzzle)

<p align="center"><img src="../data/portraits/events/evt_3153.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A magnificent archway of fossilized sea creatures blocks the deepest passage, its surface embedded with ancient shells, coral formations, and the petrified remains of deep-sea leviathans. This masterwork was created by goblin artisans over decades, but the gate will only open when the proper ritual pattern is carved into its base with tools blessed by forest magic. Without the correct approach, the fossil matrix remains as hard as steel, protecting the clan's most sacred chambers.*

**Choices:**

1. Analyze the fossil patterns to understand the required ritual sequence [DC 17 INT]
2. Excavate carefully around the base to prepare for the opening ritual [DC 17 INT]
3. Climb to rigging height to examine the gate's construction from above
4. Channel forest magic to awaken the ancient power within the fossils
5. Walk away *(auto-success)*

**Correct Tool:** digging
**Correct Ability:** Rigging Climb


#### Environmental Events

#### Gulpfin's Final Ritual (event)

<p align="center"><img src="../data/portraits/events/evt_3154.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Shaman Gulpfin stands over three captured villagers suspended by kelp ropes above a bubbling tidal pool, chanting in ancient goblin tongue as crimson algae swirls in the water below. His coral-encrusted staff glows with eldritch energy as dozens of Bloodtide goblins watch from the shadows, their gills fluttering in anticipation. The ritual must be stopped before the villagers are lowered into the sacrificial pool.*

**Choices:**

1. Time a perfect leap between the swaying prisoners to cut their bonds [DC 21 DEX]
2. Smash the ritual braziers with a heavy blow to disrupt the ceremony [DC 21 DEX]
3. Use Anchor Hold to freeze the sacrificial platform in place
4. Unleash Maelstrom Strike to scatter the gathered goblins with chaotic water
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 health damage


#### The Tide-Caller's Demand (event)

<p align="center"><img src="../data/portraits/events/evt_3155.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Tide-Caller Grix emerges from the flooded passages, his barnacle-crusted form towering over a group of cowering goblin scouts who failed to secure the upper tunnels. His voice booms with the authority of Kraken-Maw as he demands to know who dares enter the sacred warren. The scouts point trembling claws in your direction, terror evident in their bulging eyes.*

**Choices:**

1. Read Grix's body language to anticipate his next move [DC 14 WIS]
2. Smash the cavern ceiling to cause a distraction [DC 14 WIS]
3. Use Storm Sense to detect the safest path through this confrontation
4. Cast Thorn Bolt to wound Grix before he can rally his forces
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 health damage


#### Nest of Desperate Mothers (event)

<p align="center"><img src="../data/portraits/events/evt_3156.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A cluster of female goblins huddle protectively around their eggs in a shallow alcove, their eyes wild with maternal fury. Mother Kelpwhisper hisses warnings as you approach, brandishing a jagged coral shard while her sisters form a defensive circle. The eggs glow faintly with the same bioluminescent algae that covers the warren walls.*

**Choices:**

1. Observe their defensive patterns to find a peaceful passage [DC 13 WIS]
2. Scale the alcove walls to bypass the nest entirely [DC 13 WIS]
3. Use Storm Sense to detect if the eggs pose any supernatural threat
4. Cast Tempest's Fury to intimidate the mothers into submission
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 stamina damage


#### The Coral Garden Prisoners (event)

<p align="center"><img src="../data/portraits/events/evt_3157.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Several villagers from Saltwind Harbor are trapped within living coral growths that pulse with malevolent life, their arms and legs partially encased in the calcified prison. Fisherman Gareth calls out weakly for help while merchant Elena struggles against the tightening coral bonds. The growths seem to respond to movement, constricting tighter when the prisoners struggle.*

**Choices:**

1. Endure the coral's acidic secretions while you work to free them [DC 13 CON]
2. Dig carefully around the coral's base to weaken its hold [DC 13 CON]
3. Use Beacon's Roar to rally the prisoners' strength for a coordinated escape
4. Cast Root Spear to pierce and weaken the coral prison
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 health damage


#### Warren's Memory Keeper (event)

<p align="center"><img src="../data/portraits/events/evt_3158.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Ancient goblin elder Memoryscale sits hunched over a collection of carved whale bones, each etched with the clan's history in crude pictographs. His blind eyes weep saltwater as he recites the tale of their transformation, speaking of the day his people first heard Kraken-Maw's call. He seems unaware of your presence, lost in the memories of better times.*

**Choices:**

1. Use your wisdom to understand the deeper meaning in his tales [DC 20 WIS]
2. Scale nearby formations to observe his ritual from above [DC 20 WIS]
3. Channel Shatter Defense to break through his mental barriers
4. Cast Crushing Depth to compel him to share crucial information
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 stamina damage


#### The Kelp Garden Diplomats (event)

<p align="center"><img src="../data/portraits/events/evt_3159.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A delegation of surface-dwelling merfolk led by Ambassador Pearlsong have been captured and bound with kelp ropes in an underwater chamber. The proud sea-elves maintain their dignity despite their predicament, and Pearlsong offers valuable information about secret passages through the warren in exchange for freedom. Several Bloodtide guards watch nearby, unsure of their prisoners' value.*

**Choices:**

1. Use your natural charisma to convince the guards to release the diplomats [DC 17 CHA]
2. Climb to an advantageous position to cut the merfolk free [DC 17 CHA]
3. Employ Storm Sense to read the currents and find the best negotiating approach
4. Cast Ocean's Embrace to demonstrate kinship with the sea-folk
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 health damage


#### Barnacle Brothers' Territory War (event)

<p align="center"><img src="../data/portraits/events/evt_3160.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Two goblin brothers, Scrape and Crust, are locked in a violent dispute over a prime section of the warren wall where the largest barnacles grow. Their followers circle each other with crude weapons while the brothers hurl insults and threats. Elder Shellback watches from the shadows, clearly enjoying the chaos that weakens potential rivals.*

**Choices:**

1. Use quick reflexes to dodge between the feuding factions [DC 12 DEX]
2. Scale the disputed wall section to claim it yourself [DC 12 DEX]
3. Fix an intimidating glare on both brothers to cow them into submission
4. Cast Tempest's Fury to scatter both sides with a show of power
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 health damage


#### The Confessor's Guilt (event)

<p align="center"><img src="../data/portraits/events/evt_3161.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Brother Gurglemouth, a goblin convert to Kraken-Maw's faith, writhes in anguish over the growing pile of human bones in his chamber. His faith wavers as he questions whether the endless sacrifices truly honor their sea demon master, and he mutters prayers for forgiveness. Several younger goblins watch him with confusion, their own faith beginning to crack.*

**Choices:**

1. Appeal to his remaining conscience with words of redemption [DC 21 CHA]
2. Smash the bone altar to break his psychological chains [DC 21 CHA]
3. Use Burning Bash to destroy the symbols of his dark faith
4. Cast Bark Skin to protect yourself while approaching the unstable priest
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 health damage


#### The Algae Cultivators' Secret (event)

<p align="center"><img src="../data/portraits/events/evt_3162.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A group of scholarly goblins led by Researcher Slimewing tend to vast pools of bioluminescent algae that provide light throughout the warren. Slimewing nervously guards a particular strain that glows brighter than the rest, hinting that it might be the key to the clan's supernatural transformations. His assistants whisper urgently about the algae's dangerous properties.*

**Choices:**

1. Use your intelligence to understand the algae cultivation process [DC 14 INT]
2. Climb above the pools to observe their cultivation methods [DC 14 INT]
3. Employ Shatter Defense to break through their research materials
4. Cast Tempest's Fury to threaten them into revealing their secrets
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 stamina damage


#### The Drowned Merchant's Plea (event)

<p align="center"><img src="../data/portraits/events/evt_3163.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Merchant Captain Redbeard, thought lost at sea months ago, emerges from a tidal pool with gills carved into his neck and barnacles growing from his flesh. His crew of transformed sailors follows behind, all begging for death rather than continued service to Kraken-Maw. Redbeard explains that the demon keeps them conscious throughout their horrific transformation.*

**Choices:**

1. Move swiftly to grant them the mercy they seek [DC 17 DEX]
2. Smash their cursed restraints to break Kraken-Maw's hold [DC 17 DEX]
3. Use Beacon's Roar to give them strength to break free themselves
4. Cast Forest's Wrath to purge the sea demon's influence from their bodies
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 stamina damage


#### The Feeding Chain (event)

<p align="center"><img src="../data/portraits/events/evt_3164.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Goblin younglings cower in a tidal pool as their guardian, a scarred veteran named Ripjaw, blocks your path with a rusted trident. Behind him, phosphorescent fish dart between the children's gills - their only source of food. Ripjaw's eyes burn with desperate hunger as he weighs protecting his charges against his own starvation.*

**Choices:**

1. Slip past Ripjaw's guard with careful footwork to avoid the confrontation entirely [DC 12 DEX]
2. Slice open nearby kelp bundles to reveal hidden food stores for the children [DC 12 DEX]
3. Use Anchor Hold to create a barrier that protects both you and the younglings
4. Cast Root Spear to block the pool's exit, trapping the fish for the children
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 stamina damage


#### The Blood Painter (event)

<p align="center"><img src="../data/portraits/events/evt_3165.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Crimson-stained goblin artist Splotch frantically paints ritual symbols on unconscious villagers while muttering prayers to Kraken-Maw. Her brushes drip with bioluminescent algae as she prepares the captives for tonight's ceremony. She spots you but continues her grisly work, torn between duty and the growing doubt in her eyes.*

**Choices:**

1. Overpower Splotch and smash her paint pots to ruin the ritual preparation [DC 11 STR]
2. Destroy her brushes and painting tools with heavy strikes [DC 11 STR]
3. Call upon Harbor's power to wash away the ritual markings with summoned waves
4. Unleash Crushing Depth to collapse the painting chamber and end the ritual
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 stamina damage


#### The Tide Reader (event)

<p align="center"><img src="../data/portraits/events/evt_3166.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Elder mystic Shellwhisper crouches over ancient bone charts, interpreting tidal patterns that will determine the clan's next raid. Her webbed fingers trace prophetic symbols as she calculates when Saltwind Harbor's defenses will be weakest. She offers to share her knowledge in exchange for her life, claiming she knows secrets that could save hundreds.*

**Choices:**

1. Study her charts and calculations to understand the tidal patterns yourself [DC 17 INT]
2. Use digging tools to unearth more of her buried prophecies and charts [DC 17 INT]
3. Channel Harbor's Call to interpret the mystical tidal language she speaks
4. Cast Thorn Bolt to destroy her charts and prevent future raid coordination
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 stamina damage


#### The Mutation Chamber (event)

<p align="center"><img src="../data/portraits/events/evt_3167.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Goblin flesh-shaper Bubblegut tends to writhing transformation cocoons where clan members undergo horrific changes to better serve Kraken-Maw. Twisted limbs and gills sprout from the organic pods as she injects them with concentrated algae essence. She pleads that stopping her will doom her patients to death mid-transformation.*

**Choices:**

1. Endure the toxic fumes and carefully extract the subjects from their cocoons [DC 16 CON]
2. Smash the alchemical equipment to halt the transformation process [DC 16 CON]
3. Use Anchor Hold to stabilize the mutation process and save the subjects
4. Cast Healing Tsunami to purge the corruption from the transforming goblins
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 stamina damage


#### The Kelp Throne (event)

<p align="center"><img src="../data/portraits/events/evt_3168.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Juvenile prince Tentaclefin sits upon a throne of living kelp that whispers dark promises from Kraken-Maw directly into his mind. The young goblin's eyes glow with unnatural intelligence as he offers to spare your life if you kneel and accept the demon's mark. His courtiers watch nervously, unsure if they should support their mad prince or flee.*

**Choices:**

1. Convince the courtiers that their prince has been corrupted beyond redemption [DC 17 CHA]
2. Destroy the kelp throne with crushing blows to break the demon's influence [DC 17 CHA]
3. Use Storm Sense to detect and disrupt the demonic whispers corrupting the prince
4. Cast Forest's Wrath to overwhelm the kelp throne with purifying nature magic
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 stamina damage


#### The Pearl Divers (event)

<p align="center"><img src="../data/portraits/events/evt_3169.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A team of goblin pearl divers led by Deeplung emerge from a flooded shaft, their nets heavy with glowing pearls that pulse with Kraken-Maw's power. They argue fiercely about whether to deliver their harvest to the shrine or use the pearls to buy their freedom from the clan. Deeplung notices your approach and realizes these pearls could be your ticket to escape or the key to stopping the demon.*

**Choices:**

1. Negotiate with the conflicted divers to secure their magical pearls [DC 16 CHA]
2. Scale the cave walls to position yourself above their treasure haul [DC 16 CHA]
3. Use Shatter Defense to protect yourself while confronting the pearl keepers
4. Cast Tidal Shield to block their escape route and force a negotiation
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 health damage


#### The Coral Garden (event)

<p align="center"><img src="../data/portraits/events/evt_3170.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Master gardener Polyp tends to a vast coral farm where imprisoned merfolk are slowly being transformed into living reef structures. Their anguished songs echo through the chamber as she feeds them sedatives mixed with growth hormones. Polyp claims this is mercy - allowing them to become beautiful instead of dying as sacrifices.*

**Choices:**

1. Convince Polyp that her actions are torture disguised as mercy [DC 22 CHA]
2. Smash the coral growths to free the trapped merfolk before transformation completes [DC 22 CHA]
3. Use Shatter Defense to create chaos in the garden while searching for survivors
4. Cast Maelstrom Strike to devastate the coral farm and halt all transformations
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 stamina damage


#### The Archive Keeper (event)

<p align="center"><img src="../data/portraits/events/evt_3171.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Goblin scholar Scrollfin hunches over ancient texts in a waterproof vault, desperately copying the clan's historical records before the rising tides destroy them forever. He reveals that these documents contain the original binding ritual that created Kraken-Maw's hold over the clan - and possibly the key to breaking it.*

**Choices:**

1. Help decipher the ancient ritual texts to find the binding's weakness [DC 18 INT]
2. Dig channels to divert the water threatening to flood the archive [DC 18 INT]
3. Use Shatter Defense to protect the vault from rising water pressure
4. Cast Bramble Burst to create organic barriers that keep the flood at bay
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 stamina damage


#### The Birthing Pools (event)

<p align="center"><img src="../data/portraits/events/evt_3172.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Midwife Spawnsister oversees the clan's nursery where goblin eggs float in tidal pools heated by geothermal vents. She notices several eggs showing signs of mutation from Kraken-Maw's influence - tentacles and gills already forming before hatching. She begs for help deciding whether these changed offspring should live or die.*

**Choices:**

1. Study the mutation patterns to understand which eggs might produce normal offspring [DC 13 INT]
2. Carefully extract the healthiest eggs using cutting tools to separate them from corrupted ones [DC 13 INT]
3. Use Shatter Defense to create safe zones around the uncorrupted egg pools
4. Cast Healing Tsunami to purify the corrupted eggs and restore them to normal
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 health damage


#### The Memory Keeper (event)

<p align="center"><img src="../data/portraits/events/evt_3173.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Ancient goblin sage Thoughtkeeper sits before a wall of memory crystals that hold the preserved experiences of every clan member who has died in service to Kraken-Maw. She offers to show you their final moments - revealing the demon's true plans - but warns that witnessing such horror might drive you mad. The crystals pulse with the anguish of hundreds of souls.*

**Choices:**

1. Steel your mind to endure the visions and extract Kraken-Maw's secrets from the crystals [DC 14 CON]
2. Use climbing gear to reach the highest crystals that contain the oldest and most important memories [DC 14 CON]
3. Call upon Beacon's Roar to announce your presence and demand the sage share her knowledge willingly
4. Cast Crushing Depth to shatter select crystals and release their knowledge directly into your mind
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 health damage


#### The Tide Pool Trial (event)

<p align="center"><img src="../data/portraits/events/evt_3174.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Elder Kelpfin presides over a goblin court where accused clan members face trial by drowning in sacred tide pools. The condemned goblin Snapjaw pleads innocence while his accusers demand justice for stealing ritual kelp. The trial's outcome will determine clan unity or division.*

**Choices:**

1. Judge the goblin's innocence through careful observation of the evidence [DC 10 WIS]
2. Slice through the ceremonial bindings to free the accused [DC 10 WIS]
3. Stand firm against the crowd's bloodthirsty demands
4. Entangle the accusers in thorny vines to disrupt the trial
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 stamina damage


#### The Climbing Contest (event)

<p align="center"><img src="../data/portraits/events/evt_3175.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Captain Reefback challenges visiting warriors to scale the warren's treacherous vertical shaft, where barnacle-encrusted walls hide deadly sea urchins. His elite climbers Razorfin and Slipscale have never been defeated, and the captain's pride rides on maintaining their record.*

**Choices:**

1. Overpower the veteran climbers through sheer physical strength [DC 18 STR]
2. Use climbing expertise to navigate the safest route up the treacherous walls [DC 18 STR]
3. Execute a rigging maneuver to swing past the most dangerous sections
4. Surround yourself with protective magical barriers for the ascent
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 stamina damage


#### The Treasure Dispute (event)

<p align="center"><img src="../data/portraits/events/evt_3176.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Tunneler Grimdig and his rival Moldclaw argue violently over a cache of sunken treasure they unearthed together. Their shouting match threatens to collapse the unstable cavern ceiling, while other goblins scramble to claim the scattered coins and gems.*

**Choices:**

1. Assess the structural damage to determine the safest course of action [DC 14 WIS]
2. Dig a support beam slot to shore up the collapsing ceiling [DC 14 WIS]
3. Project an intimidating glare to freeze both goblins in place
4. Create a wall of thorns to separate the fighting miners
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 stamina damage


#### The Midnight Feeding (event)

<p align="center"><img src="../data/portraits/events/evt_3177.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Night-tender Gloomfin oversees the clan's nocturnal feeding ritual, where goblins consume living plankton to maintain their bioluminescence. However, the plankton supply is contaminated with foreign parasites that cause painful mutations in those who eat it.*

**Choices:**

1. Endure the contaminated feeding to gain the goblins' trust [DC 19 CON]
2. Use climbing skills to reach the pure plankton reserves in the upper pools [DC 19 CON]
3. Call upon the harbor's voices to command the contaminated creatures away
4. Create protective thorny barriers around the healthy food sources
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 health damage


#### The Diplomat's Gambit (event)

<p align="center"><img src="../data/portraits/events/evt_3178.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Ambassador Sleekscale attempts to broker peace between the Bloodtide Clan and surface dwellers, but hardliner War-chief Bonecrusher disrupts the negotiations. The ambassador's life hangs in the balance as clan politics threaten to turn violent.*

**Choices:**

1. Win over the war chief through diplomatic charm and persuasion [DC 16 CHA]
2. Slash through the war chief's weapon to disarm the threat [DC 16 CHA]
3. Use mystical harbor knowledge to reveal ancient peace accords
4. Lash the aggressive goblins with magical vines to restore order
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 stamina damage


#### The Coral Garden Crisis (event)

<p align="center"><img src="../data/portraits/events/evt_3179.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Gardener Polypseed tends to the clan's precious coral farms when a magical blight begins killing the organisms. Without these corals, the goblins will lose their primary source of calcium for shell-hardening, leaving them defenseless against deep-sea predators.*

**Choices:**

1. Use persuasive speech to rally the gardeners into coordinated action [DC 18 CHA]
2. Smash the infected coral sections with precise blunt force to stop the spread [DC 18 CHA]
3. Channel harbor mysticism to communicate with the dying coral organisms
4. Unleash nature's wrath to burn away the blight with controlled magical force
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 stamina damage


#### The Warren's Foundation (event)

<p align="center"><img src="../data/portraits/events/evt_3180.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Chief Engineer Stonecarver discovers that Kraken-Maw's influence has corrupted the warren's structural foundations, causing them to pulse with demonic energy. The ancient support pillars are slowly transforming into tentacle-like appendages that threaten to reshape the entire stronghold according to the demon's will.*

**Choices:**

1. Use raw strength to tear away the corrupted stone before it spreads further [DC 16 STR]
2. Dig reinforcement channels to redirect the corruption into harmless areas [DC 16 STR]
3. Rally the clan with a thunderous call to resist the demonic influence
4. Channel pure life energy to cleanse the corrupted foundation stones
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 health damage


#### The Ancient Compact (event)

<p align="center"><img src="../data/portraits/events/evt_3181.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Lorekeeper Deepwhisper reveals that the original goblin leaders made a bargain with Kraken-Maw that can only be broken by fulfilling an impossible condition. The document is written in ancient script that none can read, but breaking it requires the consent of both the demon and the clan's purest heart.*

**Choices:**

1. Use compelling rhetoric to convince the lorekeeper to reveal hidden knowledge [DC 22 CHA]
2. Carefully cut away the stone overlay to reveal the contract's original text [DC 22 CHA]
3. Channel mystical anchor power to hold fast against the document's protective magic
4. Summon root magic to pierce through the earth and uncover buried contract clauses
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 health damage


#### The Tidal Calendar (event)

<p align="center"><img src="../data/portraits/events/evt_3182.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Timekeeper Currentwatch maintains the clan's sacred tidal calendar, but discovers that someone has altered the ritual dates to accelerate Kraken-Maw's manifestation. The goblin suspects his apprentice Spillwater of treachery, but fears that accusations without proof will destroy their ancient astronomical knowledge.*

**Choices:**

1. Use wisdom to analyze the astronomical calculations and identify the alterations [DC 10 WIS]
2. Employ rope and climbing skills to examine the high wall carvings for tampering [DC 10 WIS]
3. Focus your anchoring power to stabilize the original temporal calculations
4. Cast nature magic to grow new calendar markers from living root systems
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 health damage


#### The Healing Pool (event)

<p align="center"><img src="../data/portraits/events/evt_3183.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Medic Saltmender tends to wounded goblins in the warren's healing pools, but discovers that the water has been tainted with addictive substances by Corrupted-fin, a goblin seeking to create dependent patients. The medic must choose between exposing the corruption and losing his primary healing resource.*

**Choices:**

1. Use physical strength to forcibly drain and refill the contaminated pools [DC 17 STR]
2. Employ blunt tools to smash the corruption source and destroy the tainted supply [DC 17 STR]
3. Sense approaching storms in the patterns to predict where clean water will flow
4. Channel healing tsunami magic to purify the pools with pure oceanic energy
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 health damage


#### The Coral Sculptor's Dilemma (event)

<p align="center"><img src="../data/portraits/events/evt_3184.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Master sculptor Kelpweave carves a massive statue of Kraken-Maw from living coral, but the work is driving her mad with visions of drowning cities. Her apprentices beg you to intervene as she prepares to complete the final ritual that will give the statue terrible life. The coral writhes and pulses with each chisel strike, and Kelpweave's eyes glow with the same bioluminescent fury as her creation.*

**Choices:**

1. Study the ritual carefully to understand the corruption's pattern and find a way to break it [DC 10 WIS]
2. Scale the statue's surface to reach and destroy the focal points of the enchantment [DC 10 WIS]
3. Use explosive force to shatter the statue before the ritual can be completed
4. Channel oceanic power to turn the coral against itself and halt the transformation
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 health damage


#### The Chronicler's Last Stand (event)

<p align="center"><img src="../data/portraits/events/evt_3185.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Ancient chronicler Shellscribe guards the warren's memory chamber where the true history of Kraken-Maw's binding is recorded in shell-script. Tide-Caller Grix's enforcers arrive to destroy the records that could reveal the demon's weakness, while Shellscribe prepares to die defending the truth. The chronicler clutches a razor-sharp coral quill, ready to fight for the knowledge that could free his people.*

**Choices:**

1. Quickly decipher the shell-script to learn the demon's weakness before the enforcers arrive [DC 15 INT]
2. Use a cutting tool to carve through the chamber's coral barriers and create an escape route [DC 15 INT]
3. Sense the approaching storm of violence and position yourself to protect the chronicler
4. Cast healing magic to strengthen Shellscribe for the battle to come
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 stamina damage


#### The Driftwood Oracle (event)

<p align="center"><img src="../data/portraits/events/evt_3186.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Blind oracle Tidereader sits surrounded by floating driftwood that moves in impossible patterns, predicting the outcomes of battles yet to come. Her prophecies reveal that one among your party will betray the others when faced with Kraken-Maw's final temptation. The driftwood pieces suddenly align to spell out a name, and Tidereader's sightless eyes begin to weep saltwater as she speaks of inevitable doom.*

**Choices:**

1. Move swiftly to rearrange the driftwood and alter the prophecy before it becomes fixed [DC 16 DEX]
2. Scale the chamber walls to reach the source of the oracle's power and understand its nature [DC 16 DEX]
3. Use intimidating presence to demand the oracle reveal how to prevent the foretold betrayal
4. Cast protective magic to shield your party from the prophecy's influence
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 stamina damage


#### The Barnacle Farmer's Burden (event)

<p align="center"><img src="../data/portraits/events/evt_3187.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Crustback tends vast beds of carnivorous barnacles that feed on captured surface dwellers, their shells growing larger with each meal. The farmer has grown sick of the endless feeding but fears the creatures will turn on the clan if starved. As you watch, a group of terrified fishermen are lowered toward the snapping shells, and Crustback hesitates at the feeding lever. His weathered hands shake as he weighs duty against conscience.*

**Choices:**

1. Analyze the barnacles' behavior to find a way to redirect their hunger without harming anyone [DC 20 INT]
2. Burrow quickly through the soft chamber floor to reach the barnacles' root system [DC 20 INT]
3. Destroy the feeding mechanism with overwhelming force to prevent the sacrifice
4. Use calming magic to pacify the aggressive barnacles temporarily
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 health damage


#### The Midnight Treasure Hunt (event)

<p align="center"><img src="../data/portraits/events/evt_3188.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *During the darkest hour, treasure hunter Goldgill leads a desperate raid into Depthcrawler Vex's personal hoard, seeking ancient coins that could buy safe passage from the warren. Her crew of young goblins clutch makeshift weapons as bioluminescent guardians patrol the treasure chamber. The heist turns deadly when Goldgill triggers a coral trap, leaving her hanging over a pit of hungry sea anemones while her followers panic.*

**Choices:**

1. Move with silent precision to disable the trap mechanism without alerting the guardians [DC 11 DEX]
2. Smash through the coral barriers to reach Goldgill before the anemones can strike [DC 11 DEX]
3. Rally the scattered treasure hunters with a commanding battle cry
4. Cast protective magic to shield Goldgill from the anemones' poison
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 stamina damage


#### The Kelp Surgeon's Choice (event)

<p align="center"><img src="../data/portraits/events/evt_3189.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *Master surgeon Seamend operates on a dying goblin warrior using living kelp as surgical thread, but the patient is revealed to be Tide-Caller Grix's own son, captured after attempting to defect to the surface world. Seamend must choose between saving the life of a potential ally or allowing him to die and weakening Grix's resolve. The kelp writhes in her hands as she hesitates, while the young goblin's breathing grows shallow.*

**Choices:**

1. Deduce the complex political implications and advise the surgeon on the wisest course of action [DC 11 INT]
2. Use climbing skills to quickly gather the rarest healing kelp from the chamber's upper reaches [DC 11 INT]
3. Employ acrobatic reflexes to assist with the delicate surgery requiring perfect precision
4. Cast nature magic to enhance the kelp's healing properties and save the patient
5. Walk away *(auto-success)*

**Failure Penalty:** 5–12 stamina damage


#### Combat Encounters

*20 unique combat encounters in this room.*

#### Hostile Crimson Tidecaller (combat)

<p align="center"><img src="../data/portraits/events/evt_3096.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 3

> *A lithe goblin with webbed fingers and gills along its neck, painted in crimson algae. It chants in guttural tones while manipulating water currents with ritual gestures.*

**Monster Lineup:**

- **Crimson Tidecaller** — HP 15-22, AC 11-13, atk: bludgeoning, element: water, weakness: fire

**Loot:**

- rope and grapnel (47%)
- chaos trident (28%)
- tide-striker (42%)

**Gold Drop:** 4–16g


#### Ambush: Crimson Tidecaller (combat)

<p align="center"><img src="../data/portraits/events/evt_3097.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 1

> *A lithe goblin with webbed fingers and gills along its neck, painted in crimson algae. It chants in guttural tones while manipulating water currents with ritual gestures.*

**Monster Lineup:**

- **Crimson Tidecaller** — HP 15-22, AC 11-13, atk: bludgeoning, element: water, weakness: fire

**Loot:**

- kelp bread (30%)

**Gold Drop:** 4–16g


#### Crimson Tidecaller Attack (combat)

<p align="center"><img src="../data/portraits/events/evt_3098.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 2

> *A lithe goblin with webbed fingers and gills along its neck, painted in crimson algae. It chants in guttural tones while manipulating water currents with ritual gestures.*

**Monster Lineup:**

- **Crimson Tidecaller** — HP 15-22, AC 11-13, atk: bludgeoning, element: water, weakness: fire

**Loot:**

- rope and grapnel (33%)

**Gold Drop:** 4–16g


#### Ambush: Depth Stalker (combat)

<p align="center"><img src="../data/portraits/events/evt_3099.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 1

> *A sleek goblin with enlarged gills and luminescent eyes that pierce the darkness. It moves silently through the flooded passages, ambushing intruders with bone harpoons.*

**Monster Lineup:**

- **Depth Stalker** — HP 12-18, AC 12-14, atk: piercing, element: dark, weakness: light

**Loot:**

- barnacle clusters (47%)
- fisherman's gutting knife (27%)

**Gold Drop:** 4–16g


#### Encounter: Depth Stalker (combat)

<p align="center"><img src="../data/portraits/events/evt_3100.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 2

> *A sleek goblin with enlarged gills and luminescent eyes that pierce the darkness. It moves silently through the flooded passages, ambushing intruders with bone harpoons.*

**Monster Lineup:**

- **Depth Stalker** — HP 12-18, AC 12-14, atk: piercing, element: dark, weakness: light

**Loot:**

- bloodtide cleaver (27%)

**Gold Drop:** 4–16g


#### Ambush: Barnacle Warrior (combat)

<p align="center"><img src="../data/portraits/events/evt_3102.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 1

> *A heavily mutated goblin whose skin has hardened into barnacle-like growths. Coral spikes jut from its knuckles as it scuttles across wet stone with unnatural speed.*

**Monster Lineup:**

- **Barnacle Warrior** — HP 20-28, AC 13-15, atk: piercing, element: water, weakness: light

**Loot:**

- storm caller's rod (21%)
- fisherman's gutting knife (18%)
- coral fungus (42%)

**Gold Drop:** 4–16g


#### Faction Patrol: Crimson Tidecaller (combat)

<p align="center"><img src="../data/portraits/events/evt_3103.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 1

> *A lithe goblin with webbed fingers and gills along its neck, painted in crimson algae. It chants in guttural tones while manipulating water currents with ritual gestures.*

**Monster Lineup:**

- **Crimson Tidecaller** — HP 15-22, AC 11-13, atk: bludgeoning, element: water, weakness: fire

**Loot:**

- dock hook (26%)
- chaos trident (34%)

**Gold Drop:** 4–16g


#### Depth Stalker Attack (combat)

<p align="center"><img src="../data/portraits/events/evt_3104.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 2

> *A sleek goblin with enlarged gills and luminescent eyes that pierce the darkness. It moves silently through the flooded passages, ambushing intruders with bone harpoons.*

**Monster Lineup:**

- **Depth Stalker** — HP 12-18, AC 12-14, atk: piercing, element: dark, weakness: light

**Loot:**

- scroll of deep sight (16%)
- fisherman's gutting knife (42%)
- tide pool gruel (36%)

**Gold Drop:** 4–16g


#### Cult Enforcers: Crimson Tidecaller (combat)

<p align="center"><img src="../data/portraits/events/evt_3106.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 1

> *A lithe goblin with webbed fingers and gills along its neck, painted in crimson algae. It chants in guttural tones while manipulating water currents with ritual gestures.*

**Monster Lineup:**

- **Crimson Tidecaller** — HP 15-22, AC 11-13, atk: bludgeoning, element: water, weakness: fire

**Loot:**

- warren shiv (17%)
- salted cod strips (12%)
- lighthouse brew (40%)

**Gold Drop:** 4–16g


#### Encounter: Tidepool Spawn (combat)

<p align="center"><img src="../data/portraits/events/evt_3107.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 4

> *A writhing mass of goblin flesh merged with sea anemones and kelp. Multiple eyes blink from its translucent body as acidic secretions drip from its tendrils.*

**Monster Lineup:**

- **Tidepool Spawn** — HP 18-25, AC 10-12, atk: bludgeoning, element: water, weakness: fire

**Loot:**

- dock hook (30%)
- rope and grapnel (14%)
- tidal draught (28%)

**Gold Drop:** 4–16g


#### Hostile Tidepool Spawn (combat)

<p align="center"><img src="../data/portraits/events/evt_3110.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 1

> *A writhing mass of goblin flesh merged with sea anemones and kelp. Multiple eyes blink from its translucent body as acidic secretions drip from its tendrils.*

**Monster Lineup:**

- **Tidepool Spawn** — HP 18-25, AC 10-12, atk: bludgeoning, element: water, weakness: fire

**Loot:**

- tidal draught (40%)
- harbor guard cutlass (34%)

**Gold Drop:** 4–16g


#### Hostile Barnacle Warrior (combat)

<p align="center"><img src="../data/portraits/events/evt_3112.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 1

> *A heavily mutated goblin whose skin has hardened into barnacle-like growths. Coral spikes jut from its knuckles as it scuttles across wet stone with unnatural speed.*

**Monster Lineup:**

- **Barnacle Warrior** — HP 20-28, AC 13-15, atk: piercing, element: water, weakness: light

**Loot:**

- tide-striker (19%)
- tide pool mussels (21%)

**Gold Drop:** 4–16g


#### Barnacle Warrior Attack (combat)

<p align="center"><img src="../data/portraits/events/evt_3114.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 4

> *A heavily mutated goblin whose skin has hardened into barnacle-like growths. Coral spikes jut from its knuckles as it scuttles across wet stone with unnatural speed.*

**Monster Lineup:**

- **Barnacle Warrior** — HP 20-28, AC 13-15, atk: piercing, element: water, weakness: light

**Loot:**

- kraken-bone maul (30%)

**Gold Drop:** 4–16g


#### Encounter: Depthcrawler Vex, the Warren's Heart-Keeper (combat) — **FINAL BOSS**

<p align="center"><img src="../data/portraits/events/evt_3120.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 1

> *A massively swollen goblin whose lower body has merged with living coral. Tentacles writhe from his back while his eyes burn with bioluminescent fury and ancient malice.*

**Monster Lineup:**

- **Depthcrawler Vex, the Warren's Heart-Keeper** — HP 45-60, AC 15-17, atk: bludgeoning, element: dark, weakness: light

**Loot:**

- scroll of crimson ward (46%)
- scroll of tidal ward (45%)

**Gold Drop:** 4–16g


#### Cult Enforcers: Tidepool Spawn (combat)

<p align="center"><img src="../data/portraits/events/evt_3123.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 1

> *A writhing mass of goblin flesh merged with sea anemones and kelp. Multiple eyes blink from its translucent body as acidic secretions drip from its tendrils.*

**Monster Lineup:**

- **Tidepool Spawn** — HP 18-25, AC 10-12, atk: bludgeoning, element: water, weakness: fire

**Loot:**

- scroll of crimson ward (33%)

**Gold Drop:** 4–16g


#### Tidepool Spawn Attack (combat)

<p align="center"><img src="../data/portraits/events/evt_3124.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 1

> *A writhing mass of goblin flesh merged with sea anemones and kelp. Multiple eyes blink from its translucent body as acidic secretions drip from its tendrils.*

**Monster Lineup:**

- **Tidepool Spawn** — HP 18-25, AC 10-12, atk: bludgeoning, element: water, weakness: fire

**Loot:**

- salted cod strips (35%)
- barnacle clusters (22%)
- brackish seep (14%)

**Gold Drop:** 4–16g


#### Encounter: Barnacle Warrior (combat)

<p align="center"><img src="../data/portraits/events/evt_3126.png" width="300"/></p>

**Difficulty:** 2 &nbsp; **Occurrences:** 1

> *A heavily mutated goblin whose skin has hardened into barnacle-like growths. Coral spikes jut from its knuckles as it scuttles across wet stone with unnatural speed.*

**Monster Lineup:**

- **Barnacle Warrior** — HP 20-28, AC 13-15, atk: piercing, element: water, weakness: light

**Loot:**

- kraken-bone maul (24%)
- lighthouse brew (16%)
- scroll of tidal ward (36%)

**Gold Drop:** 4–16g


#### Cult Enforcers: Tidepool Spawn, Crimson Tidecaller, Barnacle Warrior (combat)

<p align="center"><img src="../data/portraits/events/evt_3101.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A writhing mass of goblin flesh merged with sea anemones and kelp. Multiple eyes blink from its translucent body as acidic secretions drip from its tendrils.*

**Monster Lineup:**

- **Tidepool Spawn** — HP 18-25, AC 10-12, atk: bludgeoning, element: water, weakness: fire
- **Crimson Tidecaller** — HP 15-22, AC 11-13, atk: bludgeoning, element: water, weakness: fire
- **Barnacle Warrior** — HP 20-28, AC 13-15, atk: piercing, element: water, weakness: light

**Loot:**

- scroll of kraken's sight (21%)
- tide-touched trident (24%)

**Gold Drop:** 6–24g


#### Encounter: Tidepool Spawn, Crimson Tidecaller (combat)

<p align="center"><img src="../data/portraits/events/evt_3109.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A writhing mass of goblin flesh merged with sea anemones and kelp. Multiple eyes blink from its translucent body as acidic secretions drip from its tendrils.*

**Monster Lineup:**

- **Tidepool Spawn** — HP 18-25, AC 10-12, atk: bludgeoning, element: water, weakness: fire
- **Crimson Tidecaller** — HP 15-22, AC 11-13, atk: bludgeoning, element: water, weakness: fire

**Loot:**

- salted cod strips (47%)

**Gold Drop:** 6–24g


#### Encounter: Barnacle Warrior, Tidepool Spawn (combat)

<p align="center"><img src="../data/portraits/events/evt_3111.png" width="300"/></p>

**Difficulty:** 3 &nbsp; **Occurrences:** 1

> *A heavily mutated goblin whose skin has hardened into barnacle-like growths. Coral spikes jut from its knuckles as it scuttles across wet stone with unnatural speed.*

**Monster Lineup:**

- **Barnacle Warrior** — HP 20-28, AC 13-15, atk: piercing, element: water, weakness: light
- **Tidepool Spawn** — HP 18-25, AC 10-12, atk: bludgeoning, element: water, weakness: fire

**Loot:**

- rope and grapnel (20%)
- gulpfin's brew (32%)

**Gold Drop:** 6–24g


### Quest Walkthrough

<a id="4006"></a>

#### Finn's Request
**Type:** `solve` &nbsp; **Story Quest:** No

**Quest Giver:** [Finn Saltweep](#room_1-npc-1019)

> *Finn Saltweep needs your help.*

**Walkthrough:**

1. Speak to **Finn Saltweep** to accept the quest.
2. Solve event `3097`.

**Reward:** None

**Failure Penalty:** 4 HP damage

**On Success:** "I knew you could handle it. Take this for your trouble."

**On Failure:** "It's still unresolved. Come back when you're ready."


<a id="4007"></a>

#### Kelp-Eye's Request
**Type:** `fetch` &nbsp; **Story Quest:** Yes

**Quest Giver:** [Kelp-Eye Vrex](#room_1-npc-1020)

> *Kelp-Eye Vrex needs your help.*

**Walkthrough:**

1. Speak to **Kelp-Eye Vrex** to accept the quest.
2. Find a **weapon** item at tile (1, 29).
3. Return to **Kelp-Eye Vrex** with the item.

**Reward:** None

**Failure Penalty:** 4 HP damage

**On Success:** "You found it! This means more to me than you know. Please, take this."

**On Failure:** "Without it, I can't help you. Maybe another time."


<a id="4008"></a>

#### Sprat's Request
**Type:** `solve` &nbsp; **Story Quest:** No

**Quest Giver:** [Sprat Quickgill](#room_1-npc-1021)

> *Sprat Quickgill needs your help.*

**Walkthrough:**

1. Speak to **Sprat Quickgill** to accept the quest.
2. Solve event `3129`.

**Reward:** None

**Failure Penalty:** 4 HP damage

**On Success:** "I knew you could handle it. Take this for your trouble."

**On Failure:** "It's still unresolved. Come back when you're ready."


<a id="4009"></a>

#### Gulpfin's Request
**Type:** `solve` &nbsp; **Story Quest:** Yes

**Quest Giver:** [Gulpfin](#room_1-npc-1027)

> *Gulpfin needs your help.*

**Walkthrough:**

1. Speak to **Gulpfin** to accept the quest.
2. Solve event `3161`.

**Reward:** None

**Failure Penalty:** 4 HP damage

**On Success:** "I knew you could handle it. Take this for your trouble."

**On Failure:** "It's still unresolved. Come back when you're ready."


<a id="4010"></a>

#### Captain's Request
**Type:** `escort` &nbsp; **Story Quest:** Yes

**Quest Giver:** [Captain Daven Stormwright](#room_1-npc-1029)

> *Captain Daven Stormwright needs your help.*

**Walkthrough:**

1. Speak to **Captain Daven Stormwright** to accept the escort quest.
2. The escort NPC will join as a follower (max 2 followers).
3. Escort them safely to (2, 5).
4. Stay within 2 tiles of the target zone to complete.

**Reward:** None

**Failure Penalty:** 4 HP damage

**On Success:** "We made it. I'm safe now, thanks to you. Take this for your bravery."

**On Failure:** "I... I can't go on. Leave me here."


> **Gate Encounter:** This room's exit is guarded by event `3120`. You must defeat it to proceed.

---

<a id="scaling"></a>

## Damage Scaling

### Weapon Damage by Room

| Room | Heavy | Light | Sacred | Arcane | Enchanted | Wild |
|------|------|------|------|------|------|------|
| 1    | 1d8 | 1d6 | 1d6 | 1d4 | 1d4 | 1d6 |
| 2    | 1d10 | 1d8 | 1d8 | 1d6 | 1d6 | 1d8 |

### Spell Damage by Room (at acquisition)

| Room | Damage Single | Damage Multi | Heal |
|------|------|------|------|
| 1    | 1d8 | 1d6 | 1d8 |
| 2    | 1d10 | 1d8 | 1d10 |

*Spell dice are locked when the spell is learned. A damage_single spell learned at room 3 keeps its room-3 dice forever.*

---

<a id="spell-pools"></a>

## Available Spell Pools

These spells become available at level-up. Dice scale to the room you learn them in.

### Mage Damage Spells

| Name | Type | Element | Targets | Description |
|------|------|---------|---------|-------------|
| Strangling Roots | damage_single | forest | single | Gnarled tree roots burst from the ground to wrap around enemies, crushing them with inexorable wooden strength. |
| Spore Cloud | damage_single | forest | single | A toxic cloud of fungal spores erupts from rotting logs, poisoning all who breathe the fetid air. |
| Oakenheart Strike | damage_multi | forest | multi | The concentrated essence of ancient oak trees manifests as a crushing blow that splinters bone like brittle wood. |
| Predator's Snare | damage_single | forest | single | Carnivorous vines burst forth to entangle and devour flesh with razor-sharp thorns and acidic sap. |
| Withering Blight | damage_multi | forest | multi | A wave of forest decay spreads outward, causing enemies to wither and rot as if consumed by centuries of entropy. |
| Greenwood Fury | damage_single | forest | single | The righteous anger of the forest manifests as a barrage of hardened acorns, pinecones, and wooden splinters. |
| Dryad's Vengeance | damage_single | forest | single | Spectral tree spirits emerge to claw at enemies with ethereal branches wreathed in emerald fire. |
| Entangling Grove | damage_multi | forest | multi | A miniature forest springs up instantly around foes, its dense growth crushing and piercing with supernatural speed. |
| Mossheart Corruption | damage_single | forest | single | Parasitic moss spreads across an enemy's body, draining life force while causing excruciating pain as it burrows beneath skin. |
| Wildwood Tempest | damage_single | forest | single | A whirlwind of leaves, branches, and forest debris tears through enemies with the savage fury of a hurricane. |

### Healer Damage Spells

| Name | Type | Element | Targets | Description |
|------|------|---------|---------|-------------|
| Tide Rip | damage_single | water | single | A concentrated jet of crushing seawater tears through the target with the force of a riptide. |
| Brine Lash | damage_single | water | single | Acidic saltwater whips across the enemy, burning flesh and leaving stinging welts. |
| Pressure Wave | damage_single | water | single | The weight of the deep ocean compresses around the target in a devastating implosion. |
| Coral Spike | damage_single | water | single | A jagged spear of razor-sharp coral erupts from beneath the enemy's feet. |
| Drowning Grasp | damage_single | water | single | Phantom waters surge into the target's lungs, causing them to choke and gasp for air. |
| Abyssal Chill | damage_single | water | single | Bone-numbing cold from the deepest trenches freezes the target's blood in their veins. |
| Kraken's Lash | damage_single | water | single | A spectral tentacle of churning water slams into the enemy with crushing force. |
| Saltblade | damage_single | water | single | Crystallized salt forms a cutting edge that slices through armor and flesh alike. |
| Whirlpool Spin | damage_single | water | single | The target is caught in a violent vortex of water that batters them mercilessly. |
| Tsunami Fist | damage_single | water | single | A towering wave crashes down upon the enemy with the fury of an unstoppable flood. |

### Healing Spells

| Name | Type | Element | Targets | Description |
|------|------|---------|---------|-------------|
| Tide Pool Restoration | heal | water | self | Gentle waters from sacred tide pools flow around the target, mending wounds with the rhythm of eternal waves. |
| Saltwater Cleansing | heal | water | self | Purifying brine washes over injuries, drawing out corruption while replenishing the body's vital essence. |
| Coral Reef Embrace | heal | water | self | Living coral energy spreads across wounds, slowly rebuilding damaged tissue like a reef growing in clear waters. |
| Deep Current Mending | heal | water | self | Ancient oceanic currents carry healing power from the depths, restoring vitality with primordial force. |
| Pearl Essence Recovery | heal | water | self | Luminous pearl dust dissolves into healing light, coating injuries with the ocean's treasured gift of renewal. |
| Kelp Forest Regeneration | heal | water | self | Verdant underwater fronds wrap around the wounded, channeling the sea's endless cycle of growth and healing. |
| Monsoon's Grace | heal | water | self | Life-giving rains from distant storms cascade over the target, washing away pain while nourishing their recovery. |
| Nautilus Shell Shelter | heal | water | self | A spiraling shell of protective water forms around wounds, creating a perfect healing chamber within its curved embrace. |
| Whirlpool Vitality | heal | water | self | A miniature vortex of healing energy spins around injuries, drawing pain away while infusing fresh life force. |
| Lighthouse Beacon Heal | heal | water | self | Radiant waters illuminated like a beacon's glow flow through the target, guiding their body back to wholeness. |

### Buff Spells

| Name | Type | Element | Targets | Description |
|------|------|---------|---------|-------------|
| Moss-Touched Vigor | buff_stat | forest | self | Ancient forest moss spreads across your skin, slowly regenerating wounds and revitalizing your weary muscles. |
| Ironbark Resilience | buff_sustain | forest | self | Your flesh hardens like the weathered bark of ancient oaks, turning aside blows that would fell lesser warriors. |
| Fern Frond Grace | buff_stat | forest | self | Delicate fern patterns dance across your form, making your movements as fluid and nimble as wind through leaves. |
| Canopy's Embrace | buff_sustain | forest | self | The protective spirit of towering trees envelops you, shielding you from harm like branches sheltering forest floor. |
| Root Network Stability | buff_stat | forest | self | Invisible tendrils of forest magic anchor your feet to the earth, granting unshakeable balance and sure footing. |
| Wildflower Bloom | buff_sustain | forest | self | Tiny luminous flowers blossom around you, their gentle glow healing minor wounds and soothing battle fatigue. |
| Verdant Renewal | buff_stat | forest | self | The endless cycle of forest growth courses through your veins, rapidly restoring your vital energy. |
| Oakenheart Fortitude | buff_sustain | forest | self | Your heart beats with the steady rhythm of ancient trees, granting endurance that outlasts the longest storms. |
| Dryad's Blessing | buff_stat | forest | self | Sylvan spirits whisper encouragement in your ears, filling you with the timeless wisdom and strength of the deep woods. |
| Thornguard Ward | buff_sustain | forest | self | Spectral thorns spiral around your body, creating a protective barrier that punishes those who dare strike you. |

---

<a id="appendices"></a>

## Appendices

### A. Monster Index

| Name | Species | Level | HP | AC | Damage | Phys. Type | Element | Weakness | Rooms |
|------|---------|-------|----|----|--------|-----------|---------|----------|-------|
| Barnacle Warrior | corrupted bloodtide goblin | 2 | 20-28 | 13-15 | 1d6/1d8 physical | piercing | water | light | room_1 |
| Bloodsurge Krex | goblin champion | 1 | 32-42 | 14-16 | 1d4/1d6 water | piercing | water | forest | room_0 |
| Bloodtide Raider | amphibious goblin | 1 | 6-10 | 11-13 | 1d4/1d6 physical | slashing | water | fire | room_0 |
| Cave Crawler | deep spider | 1 | 10-14 | 12-14 | 1d4/1d6 physical | piercing | None | fire | room_0 |
| Coral-Crusted Shambler | corrupted villager | 1 | 12-16 | 9-11 | 1d4/1d6 water | bludgeoning | water | fire | room_0 |
| Crimson Tidecaller | bloodtide goblin | 2 | 15-22 | 11-13 | 1d6/1d8 water | bludgeoning | water | fire | room_1 |
| Depth Stalker | bloodtide goblin hunter | 2 | 12-18 | 12-14 | 1d6/1d8 physical | piercing | dark | light | room_1 |
| Depthcrawler Vex, the Warren's Heart-Keeper | corrupted bloodtide chieftain | 2 | 45-60 | 15-17 | 1d6/1d8 dark | bludgeoning | dark | light | room_1 |
| Tidecaller Grunt | goblin cultist | 1 | 8-12 | 10-12 | 1d4/1d6 water | bludgeoning | water | light | room_0 |
| Tidepool Spawn | kraken-touched abomination | 2 | 18-25 | 10-12 | 1d6/1d8 water | bludgeoning | water | fire | room_1 |

### B. NPC Directory

| Name | Job | Type | Room | Quest | Available |
|------|-----|------|------|-------|-----------|
| Bubble-Throat Nix | messenger who carries word between the warren levels | StaticNPC | room_1 | — | always |
| Captain Daven Stormwright | captured ship captain who knows secret routes through the coastal caves | RandomNPC | room_1 | 4010 | always |
| Captain Merrick | town guard captain organizing the defense | AggressiveNPC | room_0 | 4002 | always |
| Corwin Saltbeard | fisherman hiding behind overturned boat | StaticNPC | room_0 | — | always |
| Drip-Eye Zeff | cook who prepares meals from captured surface provisions | StaticNPC | room_1 | — | always |
| Ebb-Tooth Grak | veteran raider who trains the younger goblins | StaticNPC | room_1 | — | always |
| Elder Thessa | village elder coordinating the lighthouse evacuation | RandomNPC | room_0 | 4004 | always |
| Father Tiderick | village priest tending to the wounded in the chapel | StaticNPC | room_0 | — | always |
| Finn Saltweep | captured fisherman from Saltwind Harbor | RandomNPC | room_1 | 4006 | always |
| Glurp Tidegnaw | tunnel maintenance goblin | StaticNPC | room_1 | — | always |
| Granny Saltborn | elderly net mender who saw the first emergence | StaticNPC | room_0 | — | always |
| Gulpfin | chief shaman conducting the sacrifice rituals | RandomNPC | room_1 | 4009 | always |
| Ivy Stormwatch | herbalist and potion maker | MerchantNPC | room_0 | — | always |
| Jora Saltmane | stable master worried about her horses | StaticNPC | room_0 | — | always |
| Kael Bonecaster | shipwright trapped in his workshop | StaticNPC | room_0 | — | always |
| Kelp-Eye Vrex | shrine tender who feeds the sacrifice pools | RandomNPC | room_1 | 4007 | always |
| Kraken-Kiss Blix | shrine guardian who has been partially transformed by demon magic | StaticNPC | room_1 | — | always |
| Marcus Ironstock | weapons merchant selling to desperate defenders | MerchantNPC | room_0 | — | always |
| Mira Tidecaller | village healer trapped with wounded | RandomNPC | room_0 | 4000 | always |
| Murg the Wallcrawler | tunnel digger who maintains the warren's upper passages | StaticNPC | room_1 | — | always |
| Nessa Driftwood | rope maker whose workshop overlooks the harbor | StaticNPC | room_0 | — | always |
| Old Henrik | lighthouse keeper's assistant who lost his lantern | StaticNPC | room_0 | — | always |
| Razz Coralpeddler | merchant selling ritual components and warren supplies | MerchantNPC | room_1 | — | always |
| Scout Finwick | village scout with crucial intelligence | RandomNPC | room_0 | 4001 | always |
| Senna Pearlsight | pearl diver who knows the underwater caves | StaticNPC | room_0 | — | always |
| Shipwreck Salla | merchant dealing in salvaged goods from surface raids | MerchantNPC | room_1 | — | always |
| Skritt Bloodbrine | warren guard who questions the endless sacrifices | StaticNPC | room_1 | — | always |
| Sprat Quickgill | young goblin scout who brings news from the surface raids | RandomNPC | room_1 | 4008 | always |
| Tam Reefsong | tavern keeper guarding supplies | RandomNPC | room_0 | 4003 | always |
| Tide-Pool Yara | captured village healer held as a 'special offering' | StaticNPC | room_1 | — | always |
| Young Willem | baker's apprentice separated from his master | RandomNPC | room_0 | 4005 | always |

### C. Master Item List

| ID | Name | Category | Description | Stats | Rooms |
|----|------|----------|-------------|-------|-------|
| 2023 | brackish seep | drink | Salty water dripping from limestone formations. | +5 stam, +3 HP, 10g | room_1 |
| 2026 | brine essence | drink | Concentrated saltwater infused with dark magic. | +19 stam, +7 HP, 7g | room_1 |
| 2024 | gulpfin's brew | drink | Fermented algae drink blessed by clan shamans. | +13 stam, +7 HP, 16g | room_1 |
| 2004 | harbor grog | drink | Strong rum mixed by dockworkers to ward off sea chills. | +10 stam, +2 HP, 12g | room_0 |
| 2005 | lighthouse brew | drink | Elder Thessa's bitter tea, said to sharpen night vision. | +15 stam, +1 HP, 5g | room_0 |
| 2007 | medicinal kelp wine | drink | Fermented seaweed drink used to treat wounds. | +12 stam, +3 HP, 10g | room_0 |
| 2006 | rainwater | drink | Fresh water collected from the storm that preceded the attack. | +9 stam, +6 HP, 12g | room_0 |
| 2025 | tidal draught | drink | Ceremonial mixture of seawater and goblin blood. | +16 stam, +3 HP, 13g | room_1 |
| 2020 | barnacle clusters | food | Sharp-shelled crustaceans pried from warren walls. | +14 stam, +6 HP, 10g | room_1 |
| 2022 | coral fungus | food | Bioluminescent mushrooms grown on dead coral. | +15 stam, +6 HP, 11g | room_1 |
| 2001 | kelp bread | food | Dense bread made with seaweed flour, a village staple. | +8 stam, +5 HP, 6g | room_0 |
| 2019 | kraken kelp strips | food | Chewy seaweed harvested from Bloodtide feeding grounds. | +14 stam, +7 HP, 7g | room_1 |
| 2000 | salted cod strips | food | Dried fish prepared for the harbor watch's long shifts. | +8 stam, +1 HP, 12g | room_0 |
| 2002 | storm rations | food | Hard biscuits packed for siege conditions. | +13 stam, +6 HP, 8g | room_0 |
| 2021 | tide pool gruel | food | Murky stew of cave fish and crimson algae. | +7 stam, +3 HP, 18g | room_1 |
| 2003 | tide pool mussels | food | Shellfish harvested before the goblin raids began. | +5 stam, +3 HP, 10g | room_0 |
| 2036 | scroll of crimson ward | spell_scroll | Algae-painted script that hardens skin like coral. | 39g | room_1 |
| 2018 | scroll of deep sight | spell_scroll | Grants vision through murky water and goblin illusions. | 37g | room_0 |
| 2037 | scroll of kraken's sight | spell_scroll | Reveals hidden passages through bioluminescent vision. | 35g | room_1 |
| 2017 | scroll of tidal ward | spell_scroll | Creates a barrier of churning seawater around the caster. | 31g | room_0 |
| 2029 | barnacle scraper | tool | Curved shell tool for harvesting cave growths. | +-5 stam, 24g | room_1 |
| 2027 | coral chisel | tool | Sharpened coral fragment for carving ritual marks. | +-5 stam, 31g | room_1 |
| 2008 | dock hook | tool | Iron hook used to pull nets and boats from Kraken-Maw's depths. | +-5 stam, 19g | room_0 |
| 2028 | gill-rope | tool | Woven kelp strands slick with goblin mucus. | +-5 stam, 15g | room_1 |
| 2009 | rope and grapnel | tool | Climbing gear salvaged from Captain Merrick's ship. | +-5 stam, 19g | room_0 |
| 2010 | tide scraper | tool | Tool for harvesting barnacles, now weaponized against invaders. | +-5 stam, 21g | room_0 |
| 2035 | bloodtide cleaver | weapon | Runic machete etched with tidal prophecies. | 1d6 dmg, enchanted, slashing, WIS, 17g | room_1 |
| 2032 | chaos trident | weapon | Three-pronged spear crackling with unpredictable energy. | 1d8 dmg, wild, piercing, LUCK, 37g | room_1 |
| 2033 | depth-caller staff | weapon | Twisted driftwood staff crowned with pulsing algae. | 1d6 dmg, arcane, slashing, INT, 23g | room_1 |
| 2012 | driftwood cudgel | weapon | Makeshift club carved from storm-tossed wood. | 1d6 dmg, wild, bludgeoning, LUCK, 20g | room_0 |
| 2014 | fisherman's gutting knife | weapon | A curved blade designed for cleaning the day's catch. | 1d6 dmg, light, piercing, DEX, 18g | room_0 |
| 2013 | harbor guard cutlass | weapon | Standard-issue blade of Saltwind's coastal defenders. | 1d8 dmg, heavy, slashing, STR, 35g | room_0 |
| 2030 | kraken-bone maul | weapon | Massive club carved from ancient sea demon remains. | 1d10 dmg, heavy, bludgeoning, STR, 45g | room_1 |
| 2015 | lighthouse keeper's blessed mace | weapon | Elder Thessa's ritual weapon, inscribed with protective wards. | 1d6 dmg, sacred, bludgeoning, CON, 17g | room_0 |
| 2016 | storm caller's rod | weapon | A barnacle-encrusted staff that hums with electric potential. | 1d4 dmg, arcane, piercing, INT, 8g | room_0 |
| 2031 | tide-striker | weapon | Swift coral blade that drips with seawater. | 1d8 dmg, light, bludgeoning, DEX, 28g | room_1 |
| 2011 | tide-touched trident | weapon | A ceremonial spear that sparks with residual sea magic. | 1d4 dmg, arcane, piercing, INT, 11g | room_0 |
| 2034 | warren shiv | weapon | Razor-sharp blade knapped from volcanic glass. | 1d8 dmg, light, piercing, DEX, 45g | room_1 |

### D. Damage Type Quick Reference

**Physical Triangle** (1.5x super effective / 0.5x resisted):

`Slashing → Piercing → Bludgeoning → Slashing`

**Elemental Triangle** (1.5x / 0.5x):

`Fire → Forest → Water → Fire` &nbsp; | &nbsp; `Light ↔ Dark` (mutual 1.5x)

### E. Faction Dossier

**Bloodtide Clan**

A ferocious goblin horde that has spent generations dwelling in the underwater caves and tidal chambers beneath the coast. These goblins have adapted to their aquatic environment, developing gills and webbed extremities, while their culture revolves around the worship of Kraken-Maw, an ancient sea demon. They paint themselves with crimson algae and barnacle dust, believing it grants them the fury of the endless tide. The clan raids coastal settlements during high tide when their cave networks flood, allowing them to emerge from unexpected locations.

**History:**

Once a scattered tribe of surface goblins, they were driven into the sea caves centuries ago by human expansion. Over generations, they adapted to the tidal environment and discovered an ancient shrine to Kraken-Maw deep in the flooded caverns. The demon's influence corrupted them, granting them amphibious abilities but binding them to its will. Now they seek to claim the surface world as tribute to their dark patron.

**Leader:** Tide-Caller Grix

### F. Game Over & Victory

**Game Over:**

> *The crushing waters of the deep cavern claim you as Tide-Caller Grix's triumphant roar echoes through the flooded chambers. Your lifeless form sinks into the abyss as crimson algae swirls around you like blood in the tide. Without a champion to stop them, the Bloodtide Clan surges forth from their warren, and coastal settlements from here to the far shores will soon know the fury of Kraken-Maw's endless hunger.*

**Victory:**

> *With a final, thunderous crash, Tide-Caller Grix collapses into the churning waters of the shrine chamber, his connection to Kraken-Maw severed forever. The ancient demon's visage writhes in fury before dissolving into the cavern walls, its hold over the Bloodtide Clan broken as the remaining goblins flee in terror back to the deepest reaches of their flooded warrens. The crimson tide that threatened to drown the coastline recedes, and Saltwind Harbor—along with countless other settlements—is saved from the ravenous hunger of the sea demon's influence.*

**Climax:**

In the deepest chamber of the goblin warren, where seawater and darkness converge, heroes face Tide-Caller Grix before the massive shrine of Kraken-Maw. The demon's tentacled visage writhes in the cavern walls as Grix channels its power, summoning crushing waves and calling forth the most elite Bloodtide warriors. The battle determines whether the clan's rampage ends here or spreads to consume the entire coastline under the demon's influence.

---

<a id="technical-details"></a>

## Technical Details

### Running the Game

```bash
# Generate a new world
python -m src.generate.pipeline

# Play the game
python main.py
```

### World Configuration

| Setting | Value |
|---------|-------|
| World Seed | `1234` |
| Story Seed | `A local seaside village is under siege by a goblin horde` |
| Game Mode | `online` |
| Rooms | 2 |
| Maze Size | 40 x 30 |
| LLM Backend | `api` |
| Image Backend | `api` |
| Music Backend | `api` |
| Event Density | 0.1 |
| Item Density | 0.1 |
| NPC Density | 0.02 |
| Combat/Puzzle/Event Mix | 0.4/0.3/0.3 |

**LLM Model:** `claude-sonnet-4-20250514`

**Image Model:** `fal-ai/nano-banana`

### Generation Statistics

| Metric | Value |
|--------|-------|
| Generation Time | 42m 17s |
| LLM Calls | 94 |
| Tokens | 240,294 (140,640 in / 99,654 out) |
| Images | 280/280 |
| Music | 6/7 tracks |
| SFX | 25/25 effects |
| **Total Cost** | **$14.5007** |
| LLM Cost | $1.9167 |
| Image Cost | $11.1440 |
| Audio Cost | $1.4400 |

---

*This guide was auto-generated by MazeWorld's guide builder.*

<a id="credits"></a>

## Credits

### MazeWorld


**Game Creator**
  Wolfgang Black


**Director**
  Wolfgang Black


**Producer**
  Wolfgang Black



### — Technology —


**Game Engine**
  Pygame


**Story & Content Generation**
  Anthropic Claude (claude-sonnet-4-20250514)


**Portrait & Image Generation**
  fal.ai (fal-ai/nano-banana)


**Music Generation**
  Google Lyria 3


**Sound Effects**
  ElevenLabs



### — Runtime —


**Game Mode**
  Online (Live AI)


**Runtime Dialogue**
  Anthropic Claude



### Thank you for playing!


---
