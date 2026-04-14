# The Crimson Tide Siege

## Official Player Guide

<p align="center"><img src="../data/portraits/start_screen.png" width="300"/></p>

---

### Synopsis

The once-peaceful fishing village of Saltwind Harbor burns under the relentless assault of the Crimson Tide, a massive goblin horde that has swept across the coastlands like a blood-red plague. Led by the savage Warchief Skarfang the Tide-Bringer, these organized raiders have transformed from scattered tribal threats into a disciplined war machine that shows no mercy to those who stand in their path. As one of the last defenders, you must fight through the burning streets to drive back the goblin invaders, then pursue them into the dark depths of their underground warren. Only by facing Skarfang himself in his bone-strewn throne room can you end the Crimson Tide's reign of terror and restore peace to the shattered coastlands.

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
7. [Appendices](#appendices)
8. [Technical Details](#technical-details)
9. [Credits](#credits)

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
**STR** 18 | **DEX** 14 | **CON** 16 | **INT** 10 | **WIS** 11 | **CHA** 15 | **LUCK** 11
</td>
</tr></table>

> *Stalwart protectors of Saltwind Harbor's docks and streets. These seasoned fighters know every alley and understand the rhythm of port life.*

#### Abilities

| Name | Description | Stat | Stamina |
|------|-------------|------|---------|
| Break Barricade | Smash through wooden obstacles and doors with brute force | STR | 0 |
| Port Authority | Intimidate smugglers and troublemakers with official presence | CHA | 0 |
| Shield Bash | Stun enemies with a powerful shield strike | STR | 0 |
| Rally the Watch | Inspire nearby allies with courage and determination | CHA | 0 |

#### Unlockable Pool

| Name | Description | Stat | Stamina |
|------|-------------|------|---------|
| Crowd Control | Efficiently manage large groups of people | CHA | 0 |
| Maritime Knowledge | Navigate harbor dangers and identify ships | WIS | 0 |
| Dock Worker's Strength | Lift and move heavy cargo with ease | STR | 0 |
| Sailor's Balance | Maintain footing on unstable surfaces | DEX | 0 |

---

<table><tr>
<td width="220"><img src="../data/portraits/classes/class_1.png" width="200"/></td>
<td>
<h3>Sea Witch</h3>
<b>Archetype:</b> mage<br/>
<b>Starting Weapon:</b> Driftwood Staff<br/>
<b>Weapon Access:</b> simple only<br/><br/>
**STR** 11 | **DEX** 15 | **CON** 12 | **INT** 18 | **WIS** 16 | **CHA** 11 | **LUCK** 12
</td>
</tr></table>

> *Mysterious practitioners who draw power from the endless ocean. They speak in whispers of storms and tides, wielding water's fury and grace.*

#### Spells

| Name | Type | Element | Damage | Targets | Stamina | Description |
|------|------|---------|--------|---------|---------|-------------|
| Tidal Bolt | damage_single | water | 1d6 | single | 4 | Launch a concentrated blast of seawater at a foe |
| Whirlpool | damage_single | water | 1d6 | multi | 8 | Create a spinning vortex that damages multiple enemies |
| Fog Bank | buff_sustain | water | 1d6 | multi | 2 | Summon thick mist to obscure vision and provide cover |
| Saltwater Purge | buff_sustain | water | 1d6 | single | 2 | Cleanse poisons and diseases with purified seawater |

#### Unlockable Pool

| Name | Type | Element | Targets | Stamina | Description |
|------|------|---------|---------|---------|-------------|
| Tsunami | damage_single | water | multi | 8 | Unleash a devastating wave that crashes over all enemies |
| Water Walking | buff_sustain | water | multi | 2 | Allow allies to walk on water surfaces |
| Siren's Call | buff_sustain | water | multi | 2 | Entrance enemies with an otherworldly song |
| Maelstrom | damage_single | water | multi | 8 | Create a massive whirling storm of water and wind |

---

<table><tr>
<td width="220"><img src="../data/portraits/classes/class_2.png" width="200"/></td>
<td>
<h3>Harbor Chaplain</h3>
<b>Archetype:</b> healer<br/>
<b>Starting Weapon:</b> Blessed Anchor Pendant<br/>
<b>Weapon Access:</b> simple only<br/><br/>
**STR** 11 | **DEX** 12 | **CON** 16 | **INT** 11 | **WIS** 18 | **CHA** 16 | **LUCK** 11
</td>
</tr></table>

> *Blessed servants who tend to the spiritual needs of sailors and merchants. They offer comfort to the grieving and guidance to the lost.*

#### Spells

| Name | Type | Element | Damage | Targets | Stamina | Description |
|------|------|---------|--------|---------|---------|-------------|
| Healing Tide | heal | light | 1d6 | single | 5 | Channel divine energy to restore health and vitality |
| Beacon's Blessing | buff_stat | light | 1d6 | single | 3 | Grant an ally enhanced accuracy and protection |
| Divine Radiance | damage_single | light | 1d6 | single | 4 | Smite the wicked with pure holy light |
| Safe Harbor | buff_sustain | light | 1d6 | multi | 2 | Create a sanctuary that repels hostile forces |

#### Unlockable Pool

| Name | Type | Element | Targets | Stamina | Description |
|------|------|---------|---------|---------|-------------|
| Mass Healing | heal | light | multi | 5 | Restore health to multiple allies simultaneously |
| Guardian's Ward | buff_stat | light | multi | 3 | Protect all allies with a powerful defensive barrier |
| Purifying Light | damage_single | light | multi | 8 | Banish darkness and evil from a large area |
| Sanctuary | buff_sustain | light | multi | 2 | Create an area where no violence can occur |

---

<table><tr>
<td width="220"><img src="../data/portraits/classes/class_3.png" width="200"/></td>
<td>
<h3>Dock Rat</h3>
<b>Archetype:</b> jester<br/>
<b>Starting Weapon:</b> Lucky Sling<br/>
<b>Weapon Access:</b> simple + martial<br/><br/>
**STR** 13 | **DEX** 14 | **CON** 13 | **INT** 12 | **WIS** 12 | **CHA** 14 | **LUCK** 17
</td>
</tr></table>

> *Scrappy survivors who know every secret passage and hidden cache in the harbor. They live by their wits and an uncanny ability to be in the right place at the right time.*

#### Abilities

| Name | Description | Stat | Stamina |
|------|-------------|------|---------|
| Crowd Control | Efficiently manage large groups of people | CHA | 0 |
| Fog Bank | Summon thick mist to obscure vision and provide cover | WIS | 0 |

#### Spells

| Name | Type | Element | Damage | Targets | Stamina | Description |
|------|------|---------|--------|---------|---------|-------------|
| Healing Tide | heal | light | 1d6 | single | 5 | Channel divine energy to restore health and vitality |

#### Unlockable Pool

| Name | Description | Stat | Stamina |
|------|-------------|------|---------|
| Pickpocket | Stealthily acquire items from unsuspecting targets | DEX | 0 |
| Lucky Find | Discover useful items in unexpected places | LUCK | 0 |
| Street Smarts | Navigate urban environments with ease | WIS | 0 |
| Fast Talk | Convince others through quick wit and charm | CHA | 0 |

| Name | Type | Element | Targets | Stamina | Description |
|------|------|---------|---------|---------|-------------|
| Tidal Bolt | damage_single | water | single | 4 | Launch a concentrated blast of seawater at a foe |
| Divine Radiance | damage_single | light | single | 4 | Smite the wicked with pure holy light |
| Safe Harbor | buff_sustain | light | multi | 2 | Create a sanctuary that repels hostile forces |
| Saltwater Purge | buff_sustain | water | single | 2 | Cleanse poisons and diseases with purified seawater |

---

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

Smoke and ash fill your lungs as you step into the chaos of Saltwind Harbor, where orange flames dance across cobblestone streets slick with blood and seawater. The acrid stench of burning thatch mingles with the metallic tang of spilled blood, while the guttural war-cries of goblin raiders echo off stone walls painted crimson in the firelight. Through the haze, you glimpse the desperate flash of steel as survivors make their final stands against the relentless tide of red-bannered invaders.

### Story Beat

Saltwind Harbor burns as Crimson Tide raiders swarm through the cobblestone streets, their blood-painted weapons gleaming in the firelight. Captain Aldric Saltbeard has barricaded himself and a group of survivors in the lighthouse, desperately holding off goblin attackers who are trying to break down the heavy oak doors with stolen fishing axes. Meanwhile, Scout Kessa Nightwatch races through the smoky alleyways, attempting to evacuate terrified villagers to the harbor's edge where fishing boats wait to carry them to safety. The goblin raiding party grows bolder by the moment, led by a scarred veteran who bellows orders in the guttural Crimson Tide war-tongue, coordinating pincer attacks on the remaining pockets of resistance.

### Faction Presence

The Crimson Tide has deployed two dozen raiders throughout the village streets, using overturned carts and burning debris as cover while systematically looting homes and shops. They have established a command post in the village square where they pile stolen goods and prepare to torch the granary, cutting off the settlement's food stores.

### Boss: Bloodclaw Grimjaw, Pack Alpha of the Harbor Raid

> *A hulking goblin warrior with ritual scars covering his arms and a necklace of human teeth. He wields a massive two-handed club studded with iron nails and painted crimson.*

### Level Map

<p align="center"><img src="../data/portraits/maps/room_0_map.png" /></p>

> **Gate Encounter:** This room's exit is guarded by event `3009`. You must defeat it to proceed.

---

<a id="room-1"></a>

## Room 1: Goblin Warren
*Environment: cave — Level 2*

<p align="center"><img src="../data/portraits/environment_1.png" width="500"/></p>

### Room Introduction

The acrid stench of molten metal and spilled blood assaults your senses as you step into the heart of the Goblin Warren, where the rhythmic pounding of crude hammers echoes through the cavernous chamber like a hellish heartbeat. Shadows dance wildly across the walls as crimson-painted goblins scurry between forge fires, their war-chants rising to a fever pitch while the massive silhouette of Warchief Skarfang looms in the flickering orange glow. Above the din, you hear a familiar voice crying out in defiance—Captain Saltbeard hangs suspended over a pit of gleaming spear points, bloodied

### Story Beat

Deep within the twisting tunnels of the Goblin Warren, the retreating Crimson Tide has regrouped with frightening efficiency. Warchief Skarfang himself stalks the central chamber, his massive frame silhouetted against the glow of molten metal as goblin smiths forge weapons from stolen harbor chains and fishing boat anchors. The warchief roars commands in the war-tongue, preparing his elite guard for the final confrontation while hobgoblin shamans paint fresh blood runes on the cavern walls. Captain Aldric Saltbeard, who survived the lighthouse siege, has been dragged here in chains and now hangs suspended over a pit of sharpened stakes - bait to draw the heroes into Skarfang's trap. The air thrums with goblin war-chants as hundreds of crimson-painted warriors emerge from side tunnels, ready to defend their leader's throne room to the death.

### Faction Presence

The Crimson Tide has transformed the natural cave system into a fortified stronghold, with barricades made from ship debris blocking major passages and archer posts carved into the upper galleries. The central chamber houses Skarfang's makeshift throne room, built from the wreckage of Saltwind Harbor's fishing fleet, while deeper tunnels serve as weapon forges and prisoner holding areas.

### Boss: Gorethirst Mauler, Skarfang's Right Claw

> *A battle-scarred hobgoblin who towers over his goblin kin, wielding twin axes dripping with the blood of Saltwind Harbor's defenders. His armor is crafted from fish scales and boat planking.*

### Level Map

<p align="center"><img src="../data/portraits/maps/room_1_map.png" /></p>

> **Gate Encounter:** This room's exit is guarded by event `3116`. You must defeat it to proceed.

---

<a id="appendices"></a>

## Appendices

### A. Monster Index

| Name | Species | Level | HP | AC | Damage | Phys. Type | Element | Rooms |
|------|---------|-------|----|----|--------|-----------|---------|-------|

### B. NPC Directory

| Name | Job | Type | Room | Quest | Available |
|------|-----|------|------|-------|-----------|

### C. Master Item List

| ID | Name | Category | Description | Stats | Rooms |
|----|------|----------|-------------|-------|-------|

### D. Damage Type Quick Reference

**Physical Triangle** (1.5x super effective / 0.5x resisted):

`Slashing → Piercing → Bludgeoning → Slashing`

**Elemental Triangle** (1.5x / 0.5x):

`Fire → Forest → Water → Fire` &nbsp; | &nbsp; `Light ↔ Dark` (mutual 1.5x)

### E. Faction Dossier

**The Crimson Tide**

A vast goblin horde united under blood-red banners, the Crimson Tide is known for their savage raids and merciless conquest of coastal settlements. Unlike typical disorganized goblin tribes, they operate with military precision, using crude but effective siege weapons, coordinated pack tactics, and an unwavering loyalty to their brutal hierarchy. They paint their weapons and armor with the blood of their enemies, believing it grants them strength and strikes fear into their foes.

**History:**

Once scattered tribes fighting amongst themselves, the goblins were united five years ago by the charismatic and ruthless Warchief Skarfang after he claimed to receive visions from an ancient goblin war-god. Under his leadership, they began systematically conquering coastal villages, growing stronger with each victory and adding the survivors to their ranks as slaves or fodder.

**Leader:** Warchief Skarfang the Tide-Bringer

### F. Game Over & Victory

**Game Over:**

> *The crimson darkness closes around you as Warchief Skarfang's jagged cleaver finds its mark, your lifeblood joining the countless stains upon his bone throne. With your fall, the last hope for Saltwind Harbor dies—the Crimson Tide will surge forth unchecked, painting the entire coastline in blood and terror. The screams of a thousand fishing villages yet to burn echo through the goblin warrens as Skarfang raises your broken weapon high, a new trophy for his dark god's endless hunger.*

**Victory:**

> *With a final, thunderous crash, Warchief Skarfang's massive form crumples atop his grotesque throne of broken boats and bones, his crimson-painted cleaver clattering uselessly to the stone floor as the light fades from his savage eyes. The terrifying roar that once rallied thousands of goblins to bloody conquest falls silent forever, and across the warren, the remaining Crimson Tide warriors flee in terror, their unbreakable loyalty shattered with their master's death. Saltwind Harbor is free at last, and the coastal settlements can rest easy knowing that the most feared goblin horde in generations has been scattered to the winds, never again to*

**Climax:**

Deep in the heart of the Goblin Warren, heroes face Warchief Skarfang in his blood-soaked throne room, surrounded by the bones of his conquered enemies and the treasures looted from a dozen coastal settlements. The massive goblin warlord, scarred from countless battles and wielding a jagged cleaver dripping with crimson paint, makes his final stand atop a throne built from the wreckage of fishing boats, swearing that even in death he will drag the heroes down to join the countless souls he has claimed for his dark god.

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
| Generation Time | 27m 50s |
| LLM Calls | 57 |
| Tokens | 168,341 (107,189 in / 61,152 out) |
| Images | 214/214 |
| Music | 7/7 tracks |
| SFX | 25/25 effects |
| **Total Cost** | **$10.2760** |
| LLM Cost | $1.2388 |
| Image Cost | $8.5172 |
| Audio Cost | $0.5200 |

---

*This guide was auto-generated by MazeWorld's guide builder.*

<a id="credits"></a>

## Credits

### MazeWorld


**Game Creator**
  Wolfgang Black


**Writer**
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
