"""Player Guide Builder — generates a strategy-guide-style Markdown (+ optional PDF).

Reads all post-generation JSON data and portrait assets to produce a single
PLAYER_GUIDE.md modeled after classic game guides, with PNG dungeon maps,
entity cards, bestiary, and full quest walkthroughs.

Usage:
    python -m src.generate.guide_builder           # Markdown only
    python -m src.generate.guide_builder --pdf      # Markdown + PDF
"""

from __future__ import annotations

import json
import logging
import os
import re
import textwrap

from config import DATA_DIR, WORLD_SEED

logger = logging.getLogger(__name__)
GUIDE_OUTPUT_DIR = "docs"
MAP_OUTPUT_DIR = os.path.join(DATA_DIR, "portraits", "maps")

_IMG_PREFIX = ".."


def _safe_filename(title: str) -> str:
    """Sanitize a title for use in filenames."""
    clean = re.sub(r"[^\w\s-]", "", title).strip()
    return re.sub(r"[\s]+", "_", clean)


# Map renderer constants
TILE_SIZE = 16
MAP_COLORS = {
    "wall": (40, 40, 50),
    "path": (200, 200, 180),
    "event": (180, 50, 50),
    "boss": (140, 20, 20),
    "gate": (180, 140, 30),
    "item": (220, 180, 50),
    "npc": (50, 100, 200),
    "player_start": (50, 200, 80),
    "door": (50, 200, 200),
}
LEGEND_HEIGHT = 40


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------


def _load_json(path: str) -> dict | list | None:
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning("Could not load %s: %s", path, e)
        return None


def _discover_rooms(data_dir: str = DATA_DIR) -> list[str]:
    """Return sorted list of room directory names like ['room_0', 'room_1', ...]."""
    rooms_dir = os.path.join(data_dir, "rooms")
    if not os.path.isdir(rooms_dir):
        return []
    entries = sorted(
        d for d in os.listdir(rooms_dir) if os.path.isdir(os.path.join(rooms_dir, d)) and d.startswith("room_")
    )
    return entries


def _load_room_data(room_id: str, data_dir: str = DATA_DIR) -> dict:
    """Load all JSON files for a single room."""
    room_dir = os.path.join(data_dir, "rooms", room_id)
    return {
        "maze": _load_json(os.path.join(room_dir, "maze.json")) or {},
        "npcs": _load_json(os.path.join(room_dir, "npcs.json")) or [],
        "events": _load_json(os.path.join(room_dir, "events.json")) or [],
        "quests": _load_json(os.path.join(room_dir, "quests.json")) or [],
        "items": _load_json(os.path.join(room_dir, "items.json")) or {},
    }


def _img(rel_path: str) -> str:
    """Convert a project-relative image path to a guide-relative path."""
    return f"{_IMG_PREFIX}/{rel_path}"


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def _dedup_monsters(events: list[dict], room_id: str, monster_db: dict[int, dict] | None = None) -> list[dict]:
    """Extract unique monsters from combat events, tracking encounter counts.

    Resolves monster data from monster_db using monster_ids on each event.
    """
    seen: dict[str, dict] = {}
    db = monster_db or {}
    for evt in events:
        if evt.get("type") != "combat":
            continue
        for mid in evt.get("monster_ids", []):
            mon = db.get(mid, {})
            name = mon.get("name", f"Monster #{mid}")
            if name not in seen:
                entry = dict(mon)
                entry["_encounter_count"] = 1
                entry["_rooms"] = {room_id}
                entry["_event_portrait"] = evt.get("portrait_prompt", "")
                seen[name] = entry
            else:
                seen[name]["_encounter_count"] += 1
                seen[name]["_rooms"].add(room_id)
    return list(seen.values())


def _dedup_events(events: list[dict], room_id: str) -> list[dict]:
    """Deduplicate events by (name, type), tracking occurrence counts."""
    seen: dict[tuple[str, str], dict] = {}
    for evt in events:
        key = (evt.get("name", ""), evt.get("type", ""))
        if key not in seen:
            entry = dict(evt)
            entry["_occurrence_count"] = 1
            entry["_rooms"] = {room_id}
            seen[key] = entry
        else:
            seen[key]["_occurrence_count"] += 1
            seen[key]["_rooms"].add(room_id)
    return list(seen.values())


def _merge_deduped(existing: list[dict], new_entries: list[dict], key_field: str = "name") -> list[dict]:
    """Merge new deduped entries into an existing list, combining counts and rooms."""
    index: dict[str, dict] = {}
    for e in existing:
        k = e.get(key_field, "")
        index[k] = e

    for entry in new_entries:
        k = entry.get(key_field, "")
        if k in index:
            index[k]["_encounter_count"] = index[k].get("_encounter_count", 1) + entry.get("_encounter_count", 1)
            index[k]["_rooms"] = index[k].get("_rooms", set()) | entry.get("_rooms", set())
        else:
            index[k] = entry

    return list(index.values())


# ---------------------------------------------------------------------------
# Map renderer
# ---------------------------------------------------------------------------


def _render_maze_png(
    maze_data: dict,
    room_id: str,
    room_idx: int,
    npcs: list[dict],
    events: list[dict] | None = None,
    output_dir: str = MAP_OUTPUT_DIR,
) -> str | None:
    """Render a maze grid to a color-coded PNG and return the output path."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        logger.warning("Pillow not installed — skipping map generation.")
        return None

    grid = maze_data.get("grid", [])
    if not grid:
        return None

    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0
    img_w = cols * TILE_SIZE
    img_h = rows * TILE_SIZE + LEGEND_HEIGHT

    img = Image.new("RGB", (img_w, img_h), MAP_COLORS["wall"])
    draw = ImageDraw.Draw(img)

    npc_positions = maze_data.get("npc_positions", {})
    npc_pos_set: dict[tuple[int, int], str] = {}
    npc_name_lookup = {str(n["id"]): n.get("name", f"NPC {n['id']}") for n in npcs}
    for npc_id, pos in npc_positions.items():
        xy = (int(pos[0]), int(pos[1]))
        npc_pos_set[xy] = npc_name_lookup.get(str(npc_id), f"NPC {npc_id}")

    player_start = maze_data.get("player_start")
    door_pos = maze_data.get("door_position")

    item_positions = set()
    for ip in maze_data.get("item_placements", []):
        item_positions.add((int(ip["x"]), int(ip["y"])))

    event_flag_pos: dict[tuple[int, int], str] = {}
    for ep in maze_data.get("event_positions", []):
        eid = ep.get("event_id", "")
        epos = (int(ep["x"]), int(ep["y"]))
        if events:
            for evt in events:
                if evt.get("id") == eid:
                    if evt.get("is_climax_boss"):
                        event_flag_pos[epos] = "boss"
                    elif evt.get("is_gate"):
                        event_flag_pos[epos] = "gate"
                    break

    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            px, py = x * TILE_SIZE, y * TILE_SIZE
            pos = (x, y)

            if player_start and pos == (int(player_start[0]), int(player_start[1])):
                color = MAP_COLORS["player_start"]
            elif door_pos and pos == (int(door_pos[0]), int(door_pos[1])):
                color = MAP_COLORS["door"]
            elif pos in npc_pos_set:
                color = MAP_COLORS["npc"]
            elif pos in item_positions:
                color = MAP_COLORS["item"]
            elif cell == -1:
                flag = event_flag_pos.get(pos, "")
                if flag == "boss":
                    color = MAP_COLORS["boss"]
                elif flag == "gate":
                    color = MAP_COLORS["gate"]
                else:
                    color = MAP_COLORS["event"]
            elif cell == 1:
                color = MAP_COLORS["wall"]
            elif cell == 0:
                color = MAP_COLORS["path"]
            else:
                color = MAP_COLORS["item"] if cell > 1 else MAP_COLORS["path"]

            draw.rectangle([px, py, px + TILE_SIZE - 1, py + TILE_SIZE - 1], fill=color)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 9)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 9)
        except (OSError, IOError):
            font = ImageFont.load_default()

    for (nx, ny), name in npc_pos_set.items():
        tx = nx * TILE_SIZE + TILE_SIZE + 2
        ty = ny * TILE_SIZE + 1
        short = name.split()[0] if name else "?"
        draw.text((tx, ty), short, fill=(255, 255, 255), font=font)

    legend_y = rows * TILE_SIZE + 4
    legend_items = [
        (MAP_COLORS["wall"], "Wall"),
        (MAP_COLORS["path"], "Path"),
        (MAP_COLORS["event"], "Event"),
        (MAP_COLORS["boss"], "Boss"),
        (MAP_COLORS["gate"], "Gate"),
        (MAP_COLORS["item"], "Item"),
        (MAP_COLORS["npc"], "NPC"),
        (MAP_COLORS["player_start"], "Start"),
        (MAP_COLORS["door"], "Exit"),
    ]
    lx = 8
    for color, label in legend_items:
        draw.rectangle([lx, legend_y, lx + 12, legend_y + 12], fill=color)
        draw.text((lx + 16, legend_y + 1), label, fill=(220, 220, 220), font=font)
        lx += 70

    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"room_{room_idx}_map.png")
    img.save(out_path)
    logger.info("Map saved: %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# HTML card renderers
# ---------------------------------------------------------------------------


def _card_class(cls: dict, idx: int) -> str:
    """Portrait + stats side-by-side, desc below, then abilities/spells."""
    portrait = cls.get("portrait_path", f"{DATA_DIR}/portraits/classes/class_{idx}.png")
    stats = cls.get("stats", {})
    stat_cells = " | ".join(f"**{k}** {v}" for k, v in stats.items())

    abilities = cls.get("abilities", [])
    spells = cls.get("spells", [])
    ability_pool = cls.get("ability_pool", [])
    spell_pool = cls.get("spell_pool", [])

    archetype = cls.get("archetype", "?")
    weapon_access = {
        "warrior": "simple + martial",
        "jester": "simple + martial",
        "mage": "simple only",
        "healer": "simple only",
    }.get(archetype, "simple only")

    lines = [
        "<table><tr>",
        f'<td width="220"><img src="{_img(portrait)}" width="200"/></td>',
        "<td>",
        f"<h3>{cls.get('name', 'Unknown Class')}</h3>",
        f"<b>Archetype:</b> {archetype}<br/>",
        f"<b>Starting Weapon:</b> {cls.get('starting_weapon', 'Fists')}<br/>",
        f"<b>Weapon Access:</b> {weapon_access}<br/><br/>",
        f"{stat_cells}",
        "</td>",
        "</tr></table>",
        "",
        f"> *{cls.get('flavor_text', '')}*",
        "",
    ]

    if abilities:
        lines.append("#### Abilities")
        lines.append("")
        lines.append("| Name | Description | Stat | Stamina |")
        lines.append("|------|-------------|------|---------|")
        for a in abilities:
            lines.append(
                f"| {a.get('name', '')} | {a.get('description', '')} "
                f"| {a.get('stat', '')} | {a.get('stamina_cost', 0)} |"
            )
        lines.append("")

    if spells:
        lines.append("#### Spells")
        lines.append("")
        lines.append("| Name | Type | Element | Damage | Targets | Stamina | Description |")
        lines.append("|------|------|---------|--------|---------|---------|-------------|")
        for s in spells:
            dmg = f"1d{s.get('damage_dice', 0)}" if s.get("damage_dice") else "—"
            lines.append(
                f"| {s.get('name', '')} | {s.get('spell_type', '')} "
                f"| {s.get('element', '')} | {dmg} "
                f"| {s.get('targets', '')} | {s.get('stamina_cost', 0)} "
                f"| {s.get('description', '')} |"
            )
        lines.append("")

    if ability_pool or spell_pool:
        lines.append("#### Unlockable Pool")
        lines.append("")
        if ability_pool:
            lines.append("| Name | Description | Stat | Stamina |")
            lines.append("|------|-------------|------|---------|")
            for a in ability_pool:
                lines.append(
                    f"| {a.get('name', '')} | {a.get('description', '')} "
                    f"| {a.get('stat', '')} | {a.get('stamina_cost', 0)} |"
                )
            lines.append("")
        if spell_pool:
            lines.append("| Name | Type | Element | Targets | Stamina | Description |")
            lines.append("|------|------|---------|---------|---------|-------------|")
            for s in spell_pool:
                lines.append(
                    f"| {s.get('name', '')} | {s.get('spell_type', '')} "
                    f"| {s.get('element', '')} | {s.get('targets', '')} "
                    f"| {s.get('stamina_cost', 0)} | {s.get('description', '')} |"
                )
            lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _card_monster(mon: dict) -> str:
    """Portrait + stats side-by-side for a monster, including abilities."""
    portrait = mon.get("profile_image") or ""

    rooms = mon.get("_rooms", set())
    room_str = ", ".join(sorted(rooms)) if isinstance(rooms, set) else str(rooms)
    count = mon.get("_encounter_count", 1)

    img_tag = (
        f'<img src="{_img(portrait)}" width="200"/>'
        if portrait and os.path.exists(portrait)
        else "<em>No portrait</em>"
    )

    phys_type = mon.get("physical_type", "physical")

    lines = [
        "<table><tr>",
        f'<td width="220">{img_tag}</td>',
        "<td>",
        f"<h3>{mon.get('name', 'Unknown')}</h3>",
        f"<b>Species:</b> {mon.get('species', '?')}<br/>",
        f"<b>Level:</b> {mon.get('level', '?')}<br/>",
        f"<b>HP:</b> {mon.get('hp', '?')} / {mon.get('max_hp', '?')} &nbsp; <b>AC:</b> {mon.get('ac', '?')}<br/>",
        f"<b>Damage:</b> {mon.get('damage_dice_expr', '1d6')} {mon.get('damage_type', 'physical')}<br/>",
        f"<b>Physical Type:</b> {phys_type}<br/>",
        f"<b>Element:</b> {mon.get('elemental_affinity', 'none')}<br/>",
        f"<b>Magic Resist:</b> {mon.get('magic_resistance', 0)}<br/>",
        f"<b>Encounters:</b> {count} &nbsp; <b>Rooms:</b> {room_str}",
        "</td>",
        "</tr></table>",
        "",
        f"> *{mon.get('description', '')}*",
        "",
    ]

    abilities = mon.get("abilities", [])
    if abilities:
        lines.append("**Abilities:**")
        lines.append("")
        for ab in abilities:
            effect = ab.get("effect_type", "damage")
            dice = ab.get("damage_dice", "?")
            chance = ab.get("chance", 0)
            chance_pct = int(chance * 100) if chance <= 1 else int(chance)
            duration = ab.get("duration", 0)
            ab_name = ab.get("name", effect.title())
            dur_str = f", {duration} turns" if duration else ""
            lines.append(f"- **{ab_name}** ({effect}) — {dice} dmg, {chance_pct}% chance{dur_str}")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _card_event(evt: dict, items_lookup: dict | None = None, monster_db: dict[int, dict] | None = None) -> str:
    """Centered portrait, description, choices/monsters with physical types."""
    evt_type = evt.get("type", "event")
    portrait = evt.get("profile_image") or ""
    count = evt.get("_occurrence_count", 1)

    img_tag = (
        f'<p align="center"><img src="{_img(portrait)}" width="300"/></p>'
        if portrait and os.path.exists(portrait)
        else ""
    )

    boss_label = ""
    if evt.get("is_climax_boss"):
        boss_label = " — **FINAL BOSS**"
    elif evt.get("is_gate"):
        boss_label = " — **GATE GUARDIAN**"

    lines = [
        f"#### {evt.get('name', 'Event')} ({evt_type}){boss_label}",
        "",
    ]
    if img_tag:
        lines.append(img_tag)
        lines.append("")

    lines.append(f"**Difficulty:** {evt.get('difficulty', '?')} &nbsp; **Occurrences:** {count}")
    lines.append("")
    lines.append(f"> *{evt.get('description', '')}*")
    lines.append("")

    if evt_type == "combat":
        monster_ids = evt.get("monster_ids", [])
        if monster_ids and monster_db:
            lines.append("**Monster Lineup:**")
            lines.append("")
            for mid in monster_ids:
                m = monster_db.get(mid, {})
                phys = m.get("physical_type", "physical")
                elem = m.get("elemental_affinity", "none")
                elem_str = f", element: {elem}" if elem and elem != "none" else ""
                hp_range = m.get("hp_range", ["?", "?"])
                ac_range = m.get("ac_range", ["?", "?"])
                lines.append(
                    f"- **{m.get('name', f'Monster #{mid}')}** — "
                    f"HP {hp_range[0]}-{hp_range[1]}, AC {ac_range[0]}-{ac_range[1]}, "
                    f"{m.get('damage_type', 'physical')}, "
                    f"weakness: {phys}{elem_str}"
                )
            lines.append("")

        loot = evt.get("loot_table", [])
        if loot and items_lookup:
            lines.append("**Loot:**")
            lines.append("")
            for drop in loot:
                iid = str(drop.get("item_id", ""))
                item = items_lookup.get(iid, {})
                name = item.get("name", f"Item #{iid}")
                chance = int(drop.get("drop_chance", 0) * 100)
                lines.append(f"- {name} ({chance}%)")
            lines.append("")

        money = evt.get("money_drop")
        if money:
            lines.append(f"**Gold Drop:** {money[0]}–{money[1]}g")
            lines.append("")

    elif evt_type == "puzzle":
        choices = evt.get("choices", [])
        if choices:
            lines.append("**Choices:**")
            lines.append("")
            for i, c in enumerate(choices, 1):
                auto = " *(auto-success)*" if c.get("auto_success") else ""
                dc = f" [DC {c.get('dc', '?')} {c.get('stat_check', '')}]" if c.get("dc") else ""
                lines.append(f"{i}. {c.get('text', '?')}{dc}{auto}")
            lines.append("")
        tool = evt.get("correct_tool")
        ability = evt.get("correct_ability")
        if tool:
            lines.append(f"**Correct Tool:** {tool}")
        if ability:
            lines.append(f"**Correct Ability:** {ability}")
        if tool or ability:
            lines.append("")

    elif evt_type == "event":
        choices = evt.get("choices", [])
        if choices:
            lines.append("**Choices:**")
            lines.append("")
            for i, c in enumerate(choices, 1):
                auto = " *(auto-success)*" if c.get("auto_success") else ""
                dc = f" [DC {c.get('dc', '?')} {c.get('stat_check', '')}]" if c.get("dc") else ""
                lines.append(f"{i}. {c.get('text', '?')}{dc}{auto}")
            lines.append("")
        dmg_type = evt.get("failure_damage_type")
        dmg_range = evt.get("failure_damage_range")
        if dmg_type and dmg_range:
            lines.append(f"**Failure Penalty:** {dmg_range[0]}–{dmg_range[1]} {dmg_type} damage")
            lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _card_npc(npc: dict, room_id: str, items_lookup: dict | None = None) -> str:
    """Centered portrait, description, dialogue/quest info."""
    npc_id = npc.get("id", 0)
    portrait = f"{DATA_DIR}/portraits/npcs/npc_{npc_id}.png"
    has_portrait = os.path.exists(portrait)

    lines = [
        f'<a id="npc-{npc_id}"></a>',
        "",
    ]
    if has_portrait:
        lines.append(f'<p align="center"><img src="{_img(portrait)}" width="200"/></p>')
        lines.append("")

    lines.append(f"#### {npc.get('name', 'Unknown NPC')}")
    lines.append("")
    lines.append(
        f"**Job:** {npc.get('job', '?')}<br/>"
        f"**Type:** {npc.get('type', '?')}<br/>"
        f"**Personality:** {npc.get('personality', '?')}"
    )
    lines.append("")
    lines.append(f"> *{npc.get('backstory', '')}*")
    lines.append("")

    avail = npc.get("availability", "always")
    if avail != "always":
        lines.append(f"**Available:** {avail} only")
        lines.append("")

    greeting = npc.get("opening_greeting", "")
    if greeting:
        lines.append("**Opening Greeting:**")
        lines.append(f'> "{greeting}"')
        lines.append("")

    quest_id = npc.get("quest_id")
    if quest_id:
        lines.append(f"**Quest:** [{quest_id}](#{quest_id})")
        lines.append("")

    if npc.get("type") == "MerchantNPC" and npc.get("shop_inventory"):
        lines.append("**Shop Inventory:**")
        lines.append("")
        lines.append("| Item | Price | Stock |")
        lines.append("|------|-------|-------|")
        for si in npc["shop_inventory"]:
            iid = str(si.get("item_id", ""))
            name = "Unknown"
            if items_lookup and iid in items_lookup:
                name = items_lookup[iid].get("name", f"Item #{iid}")
            lines.append(f"| {name} | {si.get('price', '?')}g | {si.get('stock', '?')} |")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _card_quest(quest: dict, npcs: list[dict], room_id: str) -> str:
    """Render a single quest entry with walkthrough for all quest types."""
    quest_id = quest.get("id", "")
    qtype = quest.get("type", "unknown")
    npc_id = quest.get("giver_npc_id")
    giver_name = "Unknown"
    for n in npcs:
        if n.get("id") == npc_id:
            giver_name = n.get("name", "Unknown")
            break

    reward = quest.get("reward", {})
    penalty = quest.get("failure_penalty", {})

    lines = [
        f'<a id="{quest_id}"></a>',
        "",
        f"#### {quest.get('title', 'Quest')}",
        f"**Type:** `{qtype}` &nbsp; **Story Quest:** {'Yes' if quest.get('is_story_quest') else 'No'}",
        "",
        f"**Quest Giver:** [{giver_name}](#npc-{npc_id})",
        "",
        f"> *{quest.get('description', '')}*",
        "",
    ]

    prereq = quest.get("prerequisite_quest_id")
    if prereq:
        lines.append(f"**Prerequisite:** Complete quest `{prereq}` first.")
        lines.append("")

    time_gate = quest.get("time_gate")
    if time_gate:
        lines.append(f"**Time Gate:** {time_gate} only")
        lines.append("")

    lines.append("**Walkthrough:**")
    lines.append("")

    if qtype == "combat_npc":
        target = quest.get("target_npc_id")
        lines.append(f"1. Speak to **{giver_name}** to accept the quest.")
        lines.append(f"2. Challenge NPC #{target} to combat.")
        lines.append("3. Defeat them to complete the quest.")
    elif qtype in ("combat_event", "combat"):
        target_evt = quest.get("target_event_id", "?")
        lines.append(f"1. Speak to **{giver_name}** to accept the quest.")
        lines.append(f"2. Find and complete combat event `{target_evt}`.")
    elif qtype in ("solve_puzzle", "solve", "solve_event"):
        target_evt = quest.get("target_event_id", "?")
        lines.append(f"1. Speak to **{giver_name}** to accept the quest.")
        lines.append(f"2. Solve event `{target_evt}`.")
    elif qtype in ("fetch_item", "fetch"):
        target_tile = quest.get("target_tile", [])
        cat = quest.get("item_category", "item")
        tile_str = f"({target_tile[0]}, {target_tile[1]})" if target_tile else "unknown"
        lines.append(f"1. Speak to **{giver_name}** to accept the quest.")
        lines.append(f"2. Find a **{cat}** item at tile {tile_str}.")
        lines.append(f"3. Return to **{giver_name}** with the item.")
    elif qtype == "delivery":
        target_npc = quest.get("target_npc_id", "?")
        item_id = quest.get("delivery_item_id", "?")
        lines.append(f"1. Speak to **{giver_name}** to accept the quest.")
        lines.append(f"2. Obtain item #{item_id} if you don't have it.")
        lines.append(f"3. Deliver the item to NPC #{target_npc}.")
    elif qtype == "escort":
        target_pos = quest.get("target_zone", [])
        pos_str = f"({target_pos[0]}, {target_pos[1]})" if target_pos else "the target zone"
        crosses = " (crosses to next room)" if quest.get("destination_room") else ""
        lines.append(f"1. Speak to **{giver_name}** to accept the escort quest.")
        lines.append("2. The escort NPC will join as a follower (max 2 followers).")
        lines.append(f"3. Escort them safely to {pos_str}{crosses}.")
        lines.append("4. Stay within 2 tiles of the target zone to complete.")
    elif qtype in ("dialogue", "dialogue_gated"):
        dc = quest.get("dc", "?")
        lines.append(f"1. Speak to **{giver_name}** to accept the quest.")
        lines.append(f"2. Navigate the conversation successfully (CHA check, DC {dc}).")
        if quest.get("can_retry"):
            lines.append("3. You can retry if you fail.")
        elif quest.get("can_fail"):
            lines.append("3. Failure is permanent — choose your words carefully.")
    elif qtype == "multi_step":
        sub_ids = quest.get("sub_quest_ids", [])
        lines.append(f"1. Speak to **{giver_name}** to accept the quest chain.")
        for i, sid in enumerate(sub_ids, 1):
            lines.append(f"{i + 1}. Complete sub-quest `{sid}`.")
    else:
        lines.append(f"1. Speak to **{giver_name}** and follow their instructions.")

    lines.append("")

    reward_parts = []
    if reward.get("money"):
        reward_parts.append(f"{reward['money']}g")
    if reward.get("item_id"):
        reward_parts.append(f"Item #{reward['item_id']}")
    if reward.get("door_reveal"):
        reward_parts.append("Reveals exit door")
    if reward.get("story_info"):
        reward_parts.append(f'Story: "{reward["story_info"]}"')
    lines.append(f"**Reward:** {', '.join(reward_parts) if reward_parts else 'None'}")
    lines.append("")

    penalty_parts = []
    if penalty.get("hp_damage"):
        penalty_parts.append(f"{penalty['hp_damage']} HP damage")
    if penalty.get("stamina_damage"):
        penalty_parts.append(f"{penalty['stamina_damage']} stamina damage")
    if penalty_parts:
        lines.append(f"**Failure Penalty:** {', '.join(penalty_parts)}")
        lines.append("")

    success = quest.get("success_dialogue", "")
    failure = quest.get("failure_dialogue", "")
    if success:
        lines.append(f'**On Success:** "{success}"')
        lines.append("")
    if failure:
        lines.append(f'**On Failure:** "{failure}"')
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def _section_title(story: dict, narrative: dict) -> str:
    """Title Page & Introduction."""
    title = story.get("title", "MazeWorld")
    synopsis = narrative.get("synopsis", story.get("synopsis", ""))
    seed = story.get("seed", "")

    cover_img = f"{DATA_DIR}/portraits/start_screen.png"
    has_cover = os.path.exists(cover_img)

    lines = [
        f"# {title}",
        "",
        "## Official Player Guide",
        "",
    ]
    if has_cover:
        lines.append(f'<p align="center"><img src="{_img(cover_img)}" width="300"/></p>')
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("### Synopsis")
    lines.append("")
    lines.append(synopsis)
    lines.append("")

    if seed:
        lines.append(f"*Story Seed: {seed}*")
        lines.append("")

    gameover_img = f"{DATA_DIR}/portraits/game_over.png"
    if os.path.exists(gameover_img):
        lines.append("---")
        lines.append("")
        lines.append(f'<p align="center"><img src="{_img(gameover_img)}" width="400"/></p>')
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _section_toc(rooms: list[str], classes: list[dict], story: dict) -> str:
    """Table of Contents with anchor links."""
    lines = [
        "## Table of Contents",
        "",
        "1. [How to Play](#how-to-play)",
        "2. [Combat Guide](#combat-guide)",
        "3. [Character Classes](#character-classes)",
        "4. [Quest Guide](#quest-guide)",
    ]

    offset = 5
    for i, room_id in enumerate(rooms):
        room_idx = int(room_id.split("_")[1])
        lines.append(f"{offset + i}. [Room {room_idx}](#room-{room_idx})")

    offset += len(rooms)
    lines.append(f"{offset}. [Appendices](#appendices)")
    lines.append(f"{offset + 1}. [Technical Details](#technical-details)")
    lines.append(f"{offset + 2}. [Credits](#credits)")

    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _section_how_to_play() -> str:
    """Gameplay manual: controls, exploration, day/night, items, save/load."""
    from config import (
        DOOR_REVEAL_THRESHOLD,
        FOG_DAWN_BONUS,
        FOG_DAY_BONUS,
        FOG_DEFAULT_RADIUS,
        FOG_DUSK_PENALTY,
        FOG_NIGHT_PENALTY,
        NIGHT_ENCOUNTER_CHANCE,
    )

    threshold_pct = int(DOOR_REVEAL_THRESHOLD * 100)
    night_pct = int(NIGHT_ENCOUNTER_CHANCE * 100)

    lines = [
        '<a id="how-to-play"></a>',
        "",
        "## How to Play",
        "",
        "### Controls",
        "",
        "#### Exploration",
        "",
        "| Key | Action |",
        "|-----|--------|",
        "| Arrow Keys | Move through the maze |",
        "| Enter | Pick up item / Talk to NPC |",
        "| S | Open shop (when adjacent to a merchant) |",
        "| I | Toggle inventory |",
        "| Q | Toggle quest log |",
        "| R | Open rest menu |",
        "| T | Talk to follower |",
        "| P | Open status screen |",
        "| B | Story recap |",
        "| Tab | Player menu (save/load/quests/followers) |",
        "| Esc | Pause menu / Close overlay |",
        "| F1 | Debug: reveal entire maze |",
        "",
        "#### Combat",
        "",
        "| Key | Action |",
        "|-----|--------|",
        "| Up / Down | Navigate menu options |",
        "| Left / Right | Switch target |",
        "| Enter | Confirm action |",
        "| Esc | Back / Cancel sub-menu |",
        "| Space | Advance after enemy turn |",
        "| Tab | Toggle combat log |",
        "",
        "#### Inventory",
        "",
        "| Key | Action |",
        "|-----|--------|",
        "| Up / Down | Select item |",
        "| Enter / U | Use item |",
        "| E | Equip weapon |",
        "| D | Item detail |",
        "| Esc | Close inventory |",
        "",
        "### Exploration & Fog of War",
        "",
        "The maze is hidden under fog of war. As you move, nearby tiles are revealed "
        "and stay visible (but dimmed) when you move away. Your visibility radius "
        "depends on your WIS stat and the time of day:",
        "",
        f"- **Base radius:** {FOG_DEFAULT_RADIUS} tiles + WIS modifier / 2",
        f"- **Dawn:** +{FOG_DAWN_BONUS} bonus",
        f"- **Day:** +{FOG_DAY_BONUS} bonus",
        f"- **Dusk:** -{FOG_DUSK_PENALTY} penalty (negated by torch)",
        f"- **Night:** -{FOG_NIGHT_PENALTY} penalty (negated by torch)",
        "",
        "### Day/Night Cycle",
        "",
        "The world cycles through four time periods:",
        "",
        "| Period | Duration | Visibility | Notes |",
        "|--------|----------|------------|-------|",
        "| Dawn | 15% of cycle | +1 bonus | Transition period |",
        "| Day | 35% of cycle | +2 bonus | Full visibility |",
        "| Dusk | 15% of cycle | -1 penalty | Torch negates |",
        "| Night | 35% of cycle | -2 penalty | Torch negates |",
        "",
        "Time advances with each move and when resting. Some events and NPCs are "
        "**time-gated** — they only appear during the day or at night. "
        f"There is a {night_pct}% chance of a random encounter per move at night.",
        "",
        "### Torches",
        "",
        "Any item with a **light** attribute acts as a torch. While you carry a lit "
        "torch, night and dusk visibility penalties are negated. Torches consume one "
        "use per move at night — keep spares in your inventory.",
        "",
        "### Resting",
        "",
        "Press **R** to open the rest menu:",
        "",
        "| Duration | Effect |",
        "|----------|--------|",
        "| 3 hours | Small HP recovery, low stamina cost |",
        "| 6 hours | Moderate HP recovery, moderate stamina cost |",
        "| 12 hours | Large HP recovery, high stamina cost |",
        "",
        "Resting advances the day/night clock. Combat also grants a small +5 HP rest without advancing time.",
        "",
        "### Interacting with NPCs",
        "",
        "- Walk adjacent to an NPC and press **Enter** to talk.",
        "- NPCs have **day/night availability** — some only appear at certain times.",
        "- Quest-giving NPCs will offer their quest during dialogue.",
        "- Merchants: press **S** when adjacent to open the shop (buy/sell items).",
        "- You cannot sell escort items to merchants.",
        "",
        "### Items & Inventory",
        "",
        "Items are found on the maze floor (press **Enter** to pick up) or bought from merchants. Item types:",
        "",
        "| Type | Effect |",
        "|------|--------|",
        "| **Food** | Restores HP (base + CON mod) and stamina (base + 2×CON mod) |",
        "| **Drink** | Same restoration formula as food |",
        "| **Tool** | Applies a stamina effect; limited uses, breaks at 0 |",
        "| **Weapon** | Equip to change your attack; see Combat Guide for categories |",
        "| **Spell Scroll** | Jesters learn the spell permanently; others get a heal/stamina boost |",
        "| **Escort Item** | Represents a follower NPC during escort quests (not consumable) |",
        "",
        "Consumable items (food, drink, tools) scale in power by room level: 1.0x → 1.3x → 1.6x → 2.0x (rooms 1–4+).",
        "",
        "### Room Progression & The Exit Door",
        "",
        f"Each room has a hidden exit door. It is revealed once you clear "
        f"**{threshold_pct}%** of the room's encounters (or a quest reward reveals "
        f"it). The door may be guarded by a **gate encounter** — a mandatory fight "
        f"you must win before proceeding.",
        "",
        "Completing all rooms wins the game. Between rooms you get a **level up**, "
        "where you choose a new ability or spell from your class's unlock pool.",
        "",
        "Story quests will warn you at the door if they're still incomplete.",
        "",
        "### Save & Load",
        "",
        "Open the **Tab** menu or **Pause** menu (Esc) to access Save/Load. "
        "Saves preserve your full game state: player, inventory, maze, fog, "
        "day/night cycle, quests, NPCs, events, and followers.",
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def _section_combat_guide() -> str:
    """Full combat mechanics reference."""
    lines = [
        '<a id="combat-guide"></a>',
        "",
        "## Combat Guide",
        "",
        "### Initiative & Turn Order",
        "",
        "When combat begins, each combatant rolls initiative:",
        "",
        "- **Player:** `1d20 + DEX modifier`",
        "- **Monsters:** `1d20 + dex_mod`",
        "",
        "Combatants are sorted highest to lowest. Ties favor the player. "
        "The turn order is shown in the top-right of the combat screen.",
        "",
        "### Melee Attacks",
        "",
        "**To-hit roll:** `1d20 + weapon_stat_bonus + (level - 1)` vs **DC:** `target AC + target DEX modifier`",
        "",
        "- The stat used depends on weapon type (see Weapon Types below).",
        "- On hit: `1d{weapon_dice} + stat_bonus` base damage.",
        "- Physical and elemental multipliers are then applied (see below).",
        "- Minimum 1 damage on a hit.",
        "",
        "**Stat bonuses by archetype:**",
        "",
        "| Archetype | Weapon Category Access | Stat Bonus Rule |",
        "|-----------|----------------------|-----------------|",
        "| Warrior | simple + martial | Full stat modifier |",
        "| Mage | simple only | Full stat modifier (0 on martial) |",
        "| Healer | simple only | Full stat modifier (0 on martial) |",
        "| Jester | simple + martial | Average of LUCK mod and weapon stat mod |",
        "",
        "Mages and healers **cannot equip** martial weapons at all.",
        "",
        "### Physical Damage Triangle",
        "",
        "Every weapon has a physical damage type, and every monster has a physical "
        "type. Damage is multiplied based on the matchup:",
        "",
        "```",
        "  Slashing  →  Piercing  →  Bludgeoning  →  Slashing",
        "     ↑              ↑              ↑",
        "   1.5x           1.5x           1.5x        (super effective)",
        "   0.5x ←         0.5x ←         0.5x ←      (resisted)",
        "```",
        "",
        "| Attack Type | Strong Against | Weak Against |",
        "|-------------|---------------|--------------|",
        "| Slashing | Piercing (1.5x) | Bludgeoning (0.5x) |",
        "| Piercing | Bludgeoning (1.5x) | Slashing (0.5x) |",
        "| Bludgeoning | Slashing (1.5x) | Piercing (0.5x) |",
        "",
        "Monsters also attack the player using this triangle — a monster's "
        "physical type is compared against your weapon's damage type to determine "
        "damage dealt to you.",
        "",
        "### Elemental Advantage Chart",
        "",
        "Spells and magic weapons have an element. Elemental matchups use the same 1.5x / 0.5x multipliers:",
        "",
        "```",
        "  Fire  →  Forest  →  Water  →  Fire",
        "",
        "  Light  ↔  Dark   (mutual advantage: both deal 1.5x to each other)",
        "```",
        "",
        "| Attack Element | Strong Against | Weak Against |",
        "|---------------|---------------|--------------|",
        "| Fire | Forest (1.5x) | Water (0.5x) |",
        "| Forest | Water (1.5x) | Fire (0.5x) |",
        "| Water | Fire (1.5x) | Forest (0.5x) |",
        "| Light | Dark (1.5x) | Dark (1.5x) |",
        "| Dark | Light (1.5x) | Light (1.5x) |",
        "",
        "Weapons with a `magic_element` apply **both** the physical and elemental multipliers on a single attack.",
        "",
        "### Weapon Types",
        "",
        "| Type | Scaling Stat | Notes |",
        "|------|-------------|-------|",
        "| Heavy | STR | Warrior primary; high dice (1d8–1d10) |",
        "| Light | DEX | Fast; lower dice (1d4–1d6) |",
        "| Simple | STR or INT | Mage/healer weapons (1d4–1d6) |",
        "| Wild | Random (STR/DEX/INT) | Jester weapons; stat re-rolls each attack |",
        "",
        "**Weapon categories:** `simple` (any class) vs `martial` (warrior/jester only). "
        "Mages and healers get **0 stat bonus** and cannot equip martial weapons.",
        "",
        "Combat UI shows weapon tags like `[slashing]` or `[slashing + fire]` on "
        "attack previews so you can see your damage types at a glance.",
        "",
        "### Spells",
        "",
        "| Spell Type | Effect | Cost |",
        "|------------|--------|------|",
        "| `heal` | Restores HP (heal_amount or random 4–12) | 5 stamina |",
        "| `buff_stat` | Buffs a stat for 1d4 + INT_mod/2 turns (min 1) | 3 stamina |",
        "| `buff_sustain` | Restores +3 stamina immediately | 2 stamina |",
        "| `damage_single` | Magic damage to one target | Varies by dice |",
        "| `damage_multi` | Magic damage to all targets | 2x single cost (max 10) |",
        "",
        "**Damage spell cost by dice:** d4 = 2, d6 = 4, d8 = 5, d10 = 7 stamina.",
        "",
        "**Magic attack roll:** Player rolls `magic attack` vs DC `10 + target magic_resistance`. "
        "Damage is `1d{spell_dice}` × elemental multiplier.",
        "",
        "### Class-Specific Combat Actions",
        "",
        "#### Warrior: Multi-Attack",
        "",
        "- Costs **6 stamina**.",
        "- Rolls one attack against **every living monster**.",
        "- Uses stepped-down weapon dice (e.g. 1d8 → 1d6) for balance.",
        "- Physical and elemental multipliers still apply to each hit.",
        "",
        "#### Jester: Gamble",
        "",
        "A LUCK-weighted random outcome. Higher LUCK shifts odds toward good results:",
        "",
        "- Random damage to a monster",
        "- Self-heal",
        "- Random stat buff",
        "- Self-damage (bad luck!)",
        "- Enemy AC debuff (−2 for 3 turns)",
        "- Nothing happens",
        "- Wild elemental damage",
        "",
        "#### Weapon Swap",
        "",
        "Uses your turn. Swaps to the first other weapon in your inventory. "
        "Category restrictions apply (mages/healers cannot swap to martial weapons).",
        "",
        "### Fleeing",
        "",
        "- Roll: `1d20 + DEX` vs `12 + highest monster level`",
        "- **Success:** You escape combat.",
        "- **Failure:** The strongest monster gets a **free attack** on you.",
        "- You **cannot flee** from gate encounters or climax bosses.",
        "",
        "### Items in Combat",
        "",
        "Only **food** and **drink** can be used during combat. Using an item consumes your turn.",
        "",
        "### Monster Abilities",
        "",
        "Some monsters (especially in gate encounters) have special abilities:",
        "",
        "| Ability Type | Effect |",
        "|-------------|--------|",
        "| Damage | Extra damage on top of normal attack |",
        "| Poison | Damage over time for several turns |",
        "| Stun | Skip the player's next turn |",
        "",
        "Each ability has a **chance** to activate and a **duration** for "
        "ongoing effects. Check the Bestiary for each monster's abilities.",
        "",
        "### Player AC",
        "",
        "Your armor class: `10 + armor + DEX modifier`. Buffs to DEX from "
        "spells are included. Monsters must beat your AC to hit you.",
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def _section_quest_guide() -> str:
    """Quest types, followers, and progression mechanics."""
    lines = [
        '<a id="quest-guide"></a>',
        "",
        "## Quest Guide",
        "",
        "### Quest Types",
        "",
        "| Type | Objective |",
        "|------|-----------|",
        "| Fetch | Find an item at a specific tile and return it to the quest giver |",
        "| Delivery | Carry a specific item to a target NPC |",
        "| Escort | Escort a follower NPC safely to a target zone |",
        "| Combat | Defeat a specific combat encounter |",
        "| Solve | Complete a specific puzzle or event |",
        "| Dialogue | Pass a CHA-based conversation challenge |",
        "| Multi-Step | Complete an ordered chain of sub-quests |",
        "",
        "### Accepting & Completing Quests",
        "",
        "1. Walk to the quest-giving NPC and press **Enter** to talk.",
        "2. The quest is offered during dialogue — accept to activate it.",
        "3. Complete the objective (see type-specific details in each room's Quest Walkthrough section).",
        "4. For fetch and delivery quests, return to the appropriate NPC to turn in.",
        "5. Combat and solve quests complete automatically when the linked event resolves.",
        "",
        "### Prerequisites",
        "",
        "Some quests require completing a previous quest before they become available. "
        "The quest giver won't offer the quest until the prerequisite is done.",
        "",
        "### Story Quests",
        "",
        "Quests marked as **story quests** are tied to the overarching narrative. "
        "If you try to leave a room with an incomplete story quest, you'll get a "
        "warning at the exit door.",
        "",
        "### Followers & Escort Quests",
        "",
        "- You can have up to **2 followers** at a time.",
        "- When you accept an escort quest, the NPC joins as a follower and an "
        "**escort item** is added to your inventory.",
        "- Guide the follower to within **2 tiles** of the target zone to complete.",
        "- Press **T** at any time to talk to your follower for a hint.",
        "- **Warning:** If you advance past a follower's destination room, "
        "they leave and the quest **fails** with a penalty.",
        "",
        "### Rewards & Penalties",
        "",
        "**Possible rewards:**",
        "",
        "- Items (added to inventory)",
        "- Gold",
        "- Story information",
        "- Exit door reveal",
        "",
        "**Failure penalties:**",
        "",
        "- HP damage",
        "- Stamina damage",
        "",
        "Completing or failing a quest changes the giver NPC's dialogue to reflect the outcome.",
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def _section_classes(classes: list[dict]) -> str:
    """Character Classes section."""
    lines = [
        '<a id="character-classes"></a>',
        "",
        "## Character Classes",
        "",
        "There are four archetypes, each with a 95-point stat budget distributed "
        "across STR, DEX, CON, INT, WIS, CHA, and LUCK. At level up (between rooms), "
        "you choose a new ability or spell from your class's unlock pool.",
        "",
    ]
    for i, cls in enumerate(classes):
        lines.append(_card_class(cls, i))
    return "\n".join(lines)


def _section_room(
    room_id: str,
    room_idx: int,
    room_data: dict,
    story: dict,
    narrative: dict,
    all_items_lookup: dict,
    monster_db: dict[int, dict] | None = None,
) -> str:
    """Per-room chapter."""
    maze = room_data["maze"]
    npcs = room_data["npcs"]
    events = room_data["events"]
    quests = room_data["quests"]
    items = room_data["items"]

    env_name = maze.get("environment_name", f"Room {room_idx}")
    env_type = maze.get("environment", "unknown")

    beats = story.get("beats", [])
    beat = beats[room_idx] if room_idx < len(beats) else {}

    room_intro_key = f"room_intro_{room_id}"
    intro_text = narrative.get(room_intro_key, "")

    lines = [
        f'<a id="room-{room_idx}"></a>',
        "",
        f"## Room {room_idx}: {env_name}",
        f"*Environment: {env_type} — Level {room_idx + 1}*",
        "",
    ]

    env_portrait = f"{DATA_DIR}/portraits/environment_{room_idx}.png"
    if os.path.exists(env_portrait):
        lines.append(f'<p align="center"><img src="{_img(env_portrait)}" width="500"/></p>')
        lines.append("")

    if intro_text:
        lines.append("### Room Introduction")
        lines.append("")
        lines.append(intro_text)
        lines.append("")

    if beat.get("summary"):
        lines.append("### Story Beat")
        lines.append("")
        lines.append(beat["summary"])
        lines.append("")

    if beat.get("faction_presence"):
        lines.append("### Faction Presence")
        lines.append("")
        lines.append(beat["faction_presence"])
        lines.append("")

    if beat.get("boss_name"):
        lines.append(f"### Boss: {beat['boss_name']}")
        lines.append("")
        if beat.get("boss_lore"):
            lines.append(f"> *{beat['boss_lore']}*")
            lines.append("")

    map_path = _render_maze_png(maze, room_id, room_idx, npcs, events=events)
    if map_path:
        lines.append("### Level Map")
        lines.append("")
        lines.append(f'<p align="center"><img src="{_img(map_path)}" /></p>')
        lines.append("")

    if items:
        lines.append("### Item Catalog")
        lines.append("")
        lines.append("| ID | Name | Category | Description | Stats |")
        lines.append("|----|------|----------|-------------|-------|")
        for item_id, item in sorted(items.items(), key=lambda x: int(x[0])):
            st = item.get("item_stats", {})
            stat_parts = []
            if st.get("stamina_value"):
                stat_parts.append(f"+{st['stamina_value']} stamina")
            if st.get("health_value"):
                stat_parts.append(f"+{st['health_value']} HP")
            if st.get("uses"):
                stat_parts.append(f"{st['uses']} uses")
            if st.get("attack_dice"):
                stat_parts.append(f"{st['attack_dice']} dmg")
            if st.get("price"):
                stat_parts.append(f"{st['price']}g")
            stat_str = ", ".join(stat_parts) if stat_parts else "—"
            lines.append(
                f"| {item_id} | {item.get('name', '?')} "
                f"| {item.get('category', '?')} "
                f"| {item.get('desc', '')} | {stat_str} |"
            )
        lines.append("")

    if npcs:
        lines.append("### NPC Directory")
        lines.append("")
        for npc in npcs:
            lines.append(_card_npc(npc, room_id, items_lookup=all_items_lookup))

    room_monsters = _dedup_monsters(events, room_id, monster_db=monster_db)
    if room_monsters:
        lines.append("### Monster Bestiary")
        lines.append("")
        for mon in sorted(room_monsters, key=lambda m: m.get("name", "")):
            lines.append(_card_monster(mon))

    deduped_events = _dedup_events(events, room_id)
    puzzles = [e for e in deduped_events if e.get("type") == "puzzle"]
    env_events = [e for e in deduped_events if e.get("type") == "event"]
    combats = [e for e in deduped_events if e.get("type") == "combat"]

    if puzzles or env_events or combats:
        lines.append("### Event Guide")
        lines.append("")

    if puzzles:
        lines.append("#### Puzzles")
        lines.append("")
        for evt in puzzles:
            lines.append(_card_event(evt, all_items_lookup))

    if env_events:
        lines.append("#### Environmental Events")
        lines.append("")
        for evt in env_events:
            lines.append(_card_event(evt, all_items_lookup))

    if combats:
        lines.append("#### Combat Encounters")
        lines.append("")
        lines.append(f"*{len(combats)} unique combat encounters in this room.*")
        lines.append("")
        for evt in sorted(combats, key=lambda e: e.get("difficulty", 0)):
            lines.append(_card_event(evt, all_items_lookup, monster_db=monster_db))

    if quests:
        lines.append("### Quest Walkthrough")
        lines.append("")
        for quest in quests:
            lines.append(_card_quest(quest, npcs, room_id))

    gate_id = maze.get("gate_encounter_id")
    if gate_id:
        lines.append(
            f"> **Gate Encounter:** This room's exit is guarded by event `{gate_id}`. You must defeat it to proceed."
        )
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _section_appendices(
    all_monsters: list[dict], all_npcs: list[dict], all_items: dict, story: dict, narrative: dict
) -> str:
    """Appendices with full indexes."""
    lines = [
        '<a id="appendices"></a>',
        "",
        "## Appendices",
        "",
    ]

    lines.append("### A. Monster Index")
    lines.append("")
    lines.append("| Name | Species | Level | HP | AC | Damage | Phys. Type | Element | Rooms |")
    lines.append("|------|---------|-------|----|----|--------|-----------|---------|-------|")
    for mon in sorted(all_monsters, key=lambda m: m.get("name", "")):
        rooms = mon.get("_rooms", set())
        room_str = ", ".join(sorted(rooms)) if isinstance(rooms, set) else str(rooms)
        lines.append(
            f"| {mon.get('name', '?')} | {mon.get('species', '?')} "
            f"| {mon.get('level', '?')} | {mon.get('hp', '?')} "
            f"| {mon.get('ac', '?')} "
            f"| {mon.get('damage_dice_expr', '1d6')} {mon.get('damage_type', '')} "
            f"| {mon.get('physical_type', 'physical')} "
            f"| {mon.get('elemental_affinity', 'none')} | {room_str} |"
        )
    lines.append("")

    lines.append("### B. NPC Directory")
    lines.append("")
    lines.append("| Name | Job | Type | Room | Quest | Available |")
    lines.append("|------|-----|------|------|-------|-----------|")
    for npc in sorted(all_npcs, key=lambda n: n.get("name", "")):
        quest = npc.get("quest_id", "—") or "—"
        room = npc.get("_room_id", "?")
        avail = npc.get("availability", "always")
        lines.append(
            f"| {npc.get('name', '?')} | {npc.get('job', '?')} | {npc.get('type', '?')} | {room} | {quest} | {avail} |"
        )
    lines.append("")

    lines.append("### C. Master Item List")
    lines.append("")
    lines.append("| ID | Name | Category | Description | Stats | Rooms |")
    lines.append("|----|------|----------|-------------|-------|-------|")
    sorted_items = sorted(all_items.items(), key=lambda x: (x[1].get("category", ""), x[1].get("name", "")))
    for item_id, item in sorted_items:
        st = item.get("item_stats", {})
        stat_parts = []
        if st.get("stamina_value"):
            stat_parts.append(f"+{st['stamina_value']} stam")
        if st.get("health_value"):
            stat_parts.append(f"+{st['health_value']} HP")
        if st.get("attack_dice"):
            stat_parts.append(f"{st['attack_dice']} dmg")
        if st.get("price"):
            stat_parts.append(f"{st['price']}g")
        stat_str = ", ".join(stat_parts) if stat_parts else "—"
        rooms = item.get("_rooms", set())
        room_str = ", ".join(sorted(rooms)) if isinstance(rooms, set) else str(rooms)
        lines.append(
            f"| {item_id} | {item.get('name', '?')} "
            f"| {item.get('category', '?')} "
            f"| {item.get('desc', '')} | {stat_str} | {room_str} |"
        )
    lines.append("")

    lines.append("### D. Damage Type Quick Reference")
    lines.append("")
    lines.append("**Physical Triangle** (1.5x super effective / 0.5x resisted):")
    lines.append("")
    lines.append("`Slashing → Piercing → Bludgeoning → Slashing`")
    lines.append("")
    lines.append("**Elemental Triangle** (1.5x / 0.5x):")
    lines.append("")
    lines.append("`Fire → Forest → Water → Fire` &nbsp; | &nbsp; `Light ↔ Dark` (mutual 1.5x)")
    lines.append("")

    faction = story.get("faction")
    if faction:
        lines.append("### E. Faction Dossier")
        lines.append("")
        lines.append(f"**{faction.get('name', 'Unknown Faction')}**")
        lines.append("")
        lines.append(faction.get("description", ""))
        lines.append("")
        if faction.get("history"):
            lines.append("**History:**")
            lines.append("")
            lines.append(faction["history"])
            lines.append("")
        if faction.get("leader"):
            lines.append(f"**Leader:** {faction['leader']}")
            lines.append("")

    lines.append("### F. Game Over & Victory")
    lines.append("")
    gameover = narrative.get("game_over", "")
    victory = narrative.get("victory", "")
    if gameover:
        lines.append("**Game Over:**")
        lines.append("")
        lines.append(f"> *{gameover}*")
        lines.append("")
    if victory:
        lines.append("**Victory:**")
        lines.append("")
        lines.append(f"> *{victory}*")
        lines.append("")

    climax = story.get("climax", "")
    if climax:
        lines.append("**Climax:**")
        lines.append("")
        lines.append(climax)
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _section_technical(gen_stats: dict | None) -> str:
    """Technical Details — world config and generation stats (no controls)."""
    from config import (
        ANTHROPIC_MODEL,
        COMBAT_CHANCE,
        EVENT_CHANCE,
        EVENT_DENSITY,
        FAL_MODEL,
        GAME_MODE,
        IMAGE_BACKEND,
        ITEM_DENSITY,
        LLM_BACKEND,
        LLM_MODEL_PATH,
        MAZE_HEIGHT,
        MAZE_WIDTH,
        MUSIC_BACKEND,
        NPC_DENSITY,
        NUM_ROOMS,
        PUZZLE_CHANCE,
        STORY_SEED,
        WORLD_SEED,
    )

    lines = [
        '<a id="technical-details"></a>',
        "",
        "## Technical Details",
        "",
        "### Running the Game",
        "",
        "```bash",
        "# Generate a new world",
        "python -m src.generate.pipeline",
        "",
        "# Play the game",
        "python main.py",
        "```",
        "",
        "### World Configuration",
        "",
        "| Setting | Value |",
        "|---------|-------|",
        f"| World Seed | `{WORLD_SEED}` |",
        f"| Story Seed | `{STORY_SEED or '(auto-generated)'}` |",
        f"| Game Mode | `{GAME_MODE}` |",
        f"| Rooms | {NUM_ROOMS} |",
        f"| Maze Size | {MAZE_WIDTH} x {MAZE_HEIGHT} |",
        f"| LLM Backend | `{LLM_BACKEND}` |",
        f"| Image Backend | `{IMAGE_BACKEND}` |",
        f"| Music Backend | `{MUSIC_BACKEND}` |",
        f"| Event Density | {EVENT_DENSITY} |",
        f"| Item Density | {ITEM_DENSITY} |",
        f"| NPC Density | {NPC_DENSITY} |",
        f"| Combat/Puzzle/Event Mix | {COMBAT_CHANCE}/{PUZZLE_CHANCE}/{EVENT_CHANCE} |",
        "",
    ]

    if LLM_BACKEND == "api":
        lines.append(f"**LLM Model:** `{ANTHROPIC_MODEL}`")
    else:
        lines.append(f"**LLM Model:** `{LLM_MODEL_PATH}`")
    lines.append("")
    if IMAGE_BACKEND == "api":
        lines.append(f"**Image Model:** `{FAL_MODEL}`")
    lines.append("")

    if gen_stats:
        lines.append("### Generation Statistics")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Generation Time | {gen_stats.get('generation_time_human', '?')} |")
        lines.append(f"| LLM Calls | {gen_stats.get('llm_calls', 0)} |")
        lines.append(
            f"| Tokens | {gen_stats.get('total_tokens', 0):,} "
            f"({gen_stats.get('input_tokens', 0):,} in / "
            f"{gen_stats.get('output_tokens', 0):,} out) |"
        )
        lines.append(f"| Images | {gen_stats.get('images_succeeded', 0)}/{gen_stats.get('images_attempted', 0)} |")
        lines.append(f"| Music | {gen_stats.get('music_succeeded', 0)}/{gen_stats.get('music_attempted', 0)} tracks |")
        lines.append(f"| SFX | {gen_stats.get('sfx_succeeded', 0)}/{gen_stats.get('sfx_attempted', 0)} effects |")

        total_cost = gen_stats.get("total_cost_usd")
        if total_cost is not None:
            lines.append(f"| **Total Cost** | **${total_cost:.4f}** |")
            llm_cost = gen_stats.get("llm_cost_usd") or 0.0
            img_cost = gen_stats.get("image_cost_usd") or 0.0
            audio_cost = gen_stats.get("audio_cost_usd") or 0.0
            lines.append(f"| LLM Cost | ${llm_cost:.4f} |")
            lines.append(f"| Image Cost | ${img_cost:.4f} |")
            lines.append(f"| Audio Cost | ${audio_cost:.4f} |")
        else:
            lines.append("| Cost | Local generation (no API charges) |")

        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*This guide was auto-generated by MazeWorld's guide builder.*")
    lines.append("")
    return "\n".join(lines)


def _section_credits() -> str:
    """Credits section."""
    from src.views.credits_view import build_credits_lines

    credit_lines = build_credits_lines()
    lines = [
        '<a id="credits"></a>',
        "",
        "## Credits",
        "",
    ]
    for text, style in credit_lines:
        if style == "blank":
            lines.append("")
        elif style == "heading":
            lines.append(f"### {text}")
            lines.append("")
        elif style == "role":
            lines.append(f"**{text}**")
        elif style == "name":
            lines.append(f"  {text}")
            lines.append("")
        else:
            lines.append(text)

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# PDF conversion
# ---------------------------------------------------------------------------


def _convert_to_pdf(md_path: str, pdf_path: str) -> bool:
    """Convert a Markdown file to PDF via markdown + weasyprint."""
    try:
        import markdown as md_lib
        from weasyprint import HTML
    except ImportError as e:
        logger.warning(
            "PDF conversion requires 'markdown' and 'weasyprint': %s. Install with: pip install markdown weasyprint", e
        )
        return False
    except OSError as e:
        logger.warning(
            "PDF conversion unavailable: %s. On macOS run with: DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib", e
        )
        return False

    with open(md_path, encoding="utf-8") as f:
        md_text = f.read()

    html_body = md_lib.markdown(
        md_text,
        extensions=["tables", "md_in_html", "fenced_code"],
    )

    guide_dir = os.path.dirname(os.path.abspath(md_path))

    css = textwrap.dedent("""\
        @page {
            size: A4;
            margin: 2cm;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 11pt;
            line-height: 1.5;
            color: #222;
            max-width: 100%;
        }
        h1 { page-break-before: always; color: #8B0000; }
        h1:first-of-type { page-break-before: avoid; }
        h2 { page-break-before: always; color: #333; border-bottom: 2px solid #8B0000; }
        h3 { color: #555; }
        h4 { color: #666; }
        table { border-collapse: collapse; width: 100%; margin: 0.5em 0; }
        th, td {
            border: 1px solid #ccc;
            padding: 4px 8px;
            text-align: left;
            font-size: 10pt;
        }
        th { background-color: #f0f0f0; }
        img { max-width: 100%; height: auto; }
        blockquote {
            border-left: 3px solid #8B0000;
            margin: 0.5em 0;
            padding: 0.3em 1em;
            color: #555;
            font-style: italic;
        }
        code {
            background-color: #f5f5f5;
            padding: 2px 4px;
            border-radius: 3px;
            font-size: 10pt;
        }
        hr { border: none; border-top: 1px solid #ddd; margin: 1em 0; }
    """)

    full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <style>{css}</style>
</head>
<body>
{html_body}
</body>
</html>"""

    try:
        HTML(string=full_html, base_url=guide_dir).write_pdf(pdf_path)
        logger.info("PDF generated: %s", pdf_path)
        return True
    except Exception as e:
        logger.error("PDF generation failed: %s", e)
        return False


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def build_guide(data_dir: str = DATA_DIR, output_dir: str = GUIDE_OUTPUT_DIR, generate_pdf: bool = False) -> str:
    """Build the full player guide from post-generation data.

    Returns the path to the generated Markdown file.
    """
    logger.info("=== Building Player Guide ===")

    os.makedirs(output_dir, exist_ok=True)

    story = _load_json(os.path.join(data_dir, "story", "story.json")) or {}
    narrative = _load_json(os.path.join(data_dir, "narrative.json")) or {}
    classes = _load_json(os.path.join(data_dir, "classes", "classes.json")) or []
    gen_stats = _load_json(os.path.join(data_dir, "generation_stats.json"))

    rooms = _discover_rooms(data_dir)
    logger.info("Found %d rooms: %s", len(rooms), rooms)

    all_items_lookup: dict[str, dict] = {}
    all_npcs: list[dict] = []
    all_monsters: list[dict] = []

    monster_db_path = os.path.join(data_dir, "monsters", "monsters.json")
    raw_monster_db = _load_json(monster_db_path) or {}
    monster_db: dict[int, dict] = {int(k): v for k, v in raw_monster_db.items()}

    room_data_cache: dict[str, dict] = {}
    for room_id in rooms:
        rd = _load_room_data(room_id, data_dir)
        room_data_cache[room_id] = rd

        for item_id, item in rd["items"].items():
            if item_id not in all_items_lookup:
                entry = dict(item)
                entry["_rooms"] = {room_id}
                all_items_lookup[item_id] = entry
            else:
                all_items_lookup[item_id]["_rooms"].add(room_id)

        for npc in rd["npcs"]:
            npc_copy = dict(npc)
            npc_copy["_room_id"] = room_id
            all_npcs.append(npc_copy)

        room_monsters = _dedup_monsters(rd["events"], room_id, monster_db=monster_db)
        all_monsters = _merge_deduped(all_monsters, room_monsters)

    # Assemble guide sections in order
    sections: list[str] = []

    # 1. Title
    sections.append(_section_title(story, narrative))

    # 2. Table of Contents
    sections.append(_section_toc(rooms, classes, story))

    # 3. How to Play
    sections.append(_section_how_to_play())

    # 4. Combat Guide
    sections.append(_section_combat_guide())

    # 5. Character Classes
    if classes:
        sections.append(_section_classes(classes))

    # 6. Quest Guide
    sections.append(_section_quest_guide())

    # 7. Room chapters
    for room_id in rooms:
        room_idx = int(room_id.split("_")[1])
        sections.append(
            _section_room(
                room_id, room_idx, room_data_cache[room_id], story, narrative, all_items_lookup, monster_db=monster_db
            )
        )

    # 8. Appendices
    sections.append(_section_appendices(all_monsters, all_npcs, all_items_lookup, story, narrative))

    # 9. Technical
    sections.append(_section_technical(gen_stats))

    # 10. Credits
    sections.append(_section_credits())

    title = story.get("title", "Untitled")
    base_name = f"PLAYER_GUIDE_{_safe_filename(title)}_{WORLD_SEED}"

    md_path = os.path.join(output_dir, f"{base_name}.md")
    full_md = "\n".join(sections)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(full_md)
    logger.info("Guide written: %s (%d characters)", md_path, len(full_md))

    if generate_pdf:
        pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
        _convert_to_pdf(md_path, pdf_path)

    logger.info("=== Guide Complete ===")
    return md_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Generate MazeWorld Player Guide")
    parser.add_argument("--pdf", action="store_true", help="Also generate PDF")
    parser.add_argument("--data-dir", default=DATA_DIR, help="Data directory")
    parser.add_argument("--output-dir", default=GUIDE_OUTPUT_DIR, help="Output directory")
    args = parser.parse_args()

    build_guide(data_dir=args.data_dir, output_dir=args.output_dir, generate_pdf=args.pdf)


if __name__ == "__main__":
    main()
